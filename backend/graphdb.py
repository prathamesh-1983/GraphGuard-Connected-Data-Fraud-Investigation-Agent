import os
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

DEMO_ACCOUNTS = []
DEMO_TRANSACTIONS = []
DEMO_DEVICES = []
DEMO_USES = []
DEMO_LINKS = []

class GraphStore:
    """FalkorDB-backed graph store with a deterministic in-memory fallback for easy demos."""
    def __init__(self, require_db=False):
        self.graph_name = os.getenv("FALKORDB_GRAPH", "graphguard")
        self.connected = False
        self.graph = None
        self.redis = None
        self.memory = {"accounts": {}, "transactions": {}, "devices": {}, "uses": [], "links": [], "sends": [], "receives": []}
        host = os.getenv("FALKORDB_HOST", "localhost")
        port = int(os.getenv("FALKORDB_PORT", "6379"))
        password = os.getenv("FALKORDB_PASSWORD") or None
        try:
            from falkordb import FalkorDB
            self.redis = FalkorDB(host=host, port=port, password=password)
            self.graph = self.redis.select_graph(self.graph_name)
            self.graph.query("RETURN 1")
            self.connected = True
        except Exception as exc:
            if require_db:
                raise RuntimeError(f"FalkorDB is required but unavailable ({exc}). Start FalkorDB and check .env.") from exc

    def query(self, cypher, params=None):
        if not self.connected:
            raise RuntimeError("Cypher query requested while in fallback mode.")
        return self.graph.query(cypher, params or {})

    def reset_graph(self):
        if self.connected:
            self.graph.query("MATCH (n) DETACH DELETE n")
        self.memory = {"accounts": {}, "transactions": {}, "devices": {}, "uses": [], "links": [], "sends": [], "receives": []}

    def add_account(self, account_id, name, risk_score=0):
        row = {"account_id": account_id, "name": name, "risk_score": int(risk_score)}
        self.memory["accounts"][account_id] = row
        if self.connected:
            self.query("MERGE (a:Account {account_id:$id}) SET a.name=$name, a.risk_score=$risk",
                       {"id": account_id, "name": name, "risk": int(risk_score)})

    def add_transaction(self, transaction_id, amount, status, timestamp, sender, receiver, device_id=None):
        row = {"transaction_id": transaction_id, "amount": float(amount), "status": status, "timestamp": timestamp,
               "sender": sender, "receiver": receiver, "device_id": device_id}
        self.memory["transactions"][transaction_id] = row
        self.memory["sends"].append((sender, transaction_id))
        self.memory["receives"].append((transaction_id, receiver))
        if self.connected:
            self.query("""
            MERGE (t:Transaction {transaction_id:$tid})
            SET t.amount=$amount, t.status=$status, t.timestamp=$timestamp
            WITH t
            MATCH (s:Account {account_id:$sender}), (r:Account {account_id:$receiver})
            MERGE (s)-[:SENDS]->(t)
            MERGE (t)-[:RECEIVED_BY]->(r)
            """, {"tid": transaction_id, "amount": float(amount), "status": status, "timestamp": timestamp,
                  "sender": sender, "receiver": receiver})
            if device_id:
                self.query("""
                MERGE (d:Device {device_id:$device})
                MERGE (s:Account {account_id:$sender})
                MERGE (s)-[:USES_DEVICE]->(d)
                """, {"device": device_id, "sender": sender})

    def add_device_use(self, account_id, device_id, device_type="unknown"):
        self.memory["devices"][device_id] = {"device_id": device_id, "device_type": device_type}
        self.memory["uses"].append((account_id, device_id))
        if self.connected:
            self.query("""
            MERGE (a:Account {account_id:$account})
            MERGE (d:Device {device_id:$device})
            SET d.device_type=$type
            MERGE (a)-[:USES_DEVICE]->(d)
            """, {"account": account_id, "device": device_id, "type": device_type})

    def add_account_link(self, a, b, reason="shared attribute"):
        self.memory["links"].append((a, b, reason))
        if self.connected:
            self.query("""
            MATCH (a:Account {account_id:$a}), (b:Account {account_id:$b})
            MERGE (a)-[r:LINKED_TO]->(b) SET r.reason=$reason
            """, {"a": a, "b": b, "reason": reason})

    def account_ids(self):
        if self.connected:
            res = self.query("MATCH (a:Account) RETURN a.account_id ORDER BY a.account_id")
            return [str(row[0]) for row in res.result_set]
        return sorted(self.memory["accounts"])

    def transaction_ids(self):
        if self.connected:
            res = self.query("MATCH (t:Transaction) RETURN t.transaction_id ORDER BY t.transaction_id")
            return [str(row[0]) for row in res.result_set]
        return sorted(self.memory["transactions"])

    def metrics(self):
        if self.connected:
            def count(label):
                r = self.query(f"MATCH (n:{label}) RETURN count(n)")
                return int(r.result_set[0][0])
            return {"accounts": count("Account"), "transactions": count("Transaction"), "devices": count("Device")}
        return {k: len(self.memory[k]) for k in ("accounts", "transactions", "devices")}

    def account_investigation(self, account_id):
        if self.connected:
            r = self.query("""
            MATCH (a:Account {account_id:$id})
            OPTIONAL MATCH (a)-[:SENDS]->(t:Transaction)
            OPTIONAL MATCH (t)-[:RECEIVED_BY]->(receiver:Account)
            OPTIONAL MATCH (a)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(other:Account)
            WHERE other IS NULL OR other.account_id <> a.account_id
            RETURN a.account_id, a.name, a.risk_score,
                   collect(DISTINCT {transaction_id:t.transaction_id, amount:t.amount, status:t.status, receiver:receiver.account_id}) AS txs,
                   collect(DISTINCT {device_id:d.device_id, other_account:other.account_id}) AS shared
            """, {"id": account_id})
            if not r.result_set:
                return None
            row = r.result_set[0]
            txs = [x for x in (row[3] or []) if x and x.get("transaction_id")]
            shared = [x for x in (row[4] or []) if x and x.get("device_id") and x.get("other_account")]
            return {"account_id": row[0], "name": row[1], "risk_score": row[2], "transactions": txs, "shared_devices": shared}
        a = self.memory["accounts"].get(account_id)
        if not a:
            return None
        txs = []
        for tx in self.memory["transactions"].values():
            if tx["sender"] == account_id:
                txs.append({"transaction_id": tx["transaction_id"], "amount": tx["amount"], "status": tx["status"], "receiver": tx["receiver"]})
        devices = {d for acc, d in self.memory["uses"] if acc == account_id}
        shared = [{"device_id": d, "other_account": other} for d in devices for other, od in self.memory["uses"] if od == d and other != account_id]
        return {"account_id": account_id, "name": a["name"], "risk_score": a["risk_score"], "transactions": txs, "shared_devices": shared}

    def transaction_investigation(self, transaction_id):
        if self.connected:
            r = self.query("""
            MATCH (s:Account)-[:SENDS]->(t:Transaction {transaction_id:$id})-[:RECEIVED_BY]->(r:Account)
            OPTIONAL MATCH (s)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(other:Account)
            WHERE other IS NULL OR other.account_id <> s.account_id
            RETURN t.transaction_id, t.amount, t.status, t.timestamp, s.account_id, r.account_id,
                   collect(DISTINCT {device_id:d.device_id, other_account:other.account_id}) AS shared
            """, {"id": transaction_id})
            if not r.result_set:
                return None
            row = r.result_set[0]
            shared = [x for x in (row[6] or []) if x and x.get("device_id") and x.get("other_account")]
            return {"transaction_id": row[0], "amount": row[1], "status": row[2], "timestamp": row[3],
                    "sender": row[4], "receiver": row[5], "shared_devices": shared}
        tx = self.memory["transactions"].get(transaction_id)
        if not tx:
            return None
        devices = {d for a, d in self.memory["uses"] if a == tx["sender"]}
        shared = [{"device_id": d, "other_account": other} for d in devices for other, od in self.memory["uses"] if od == d and other != tx["sender"]]
        return {**tx, "shared_devices": shared}

    def overview(self):
        rows = []
        if self.connected:
            r = self.query("""
            MATCH (a:Account)-[rel]->(n)
            RETURN a.account_id, type(rel), labels(n)[0],
                   coalesce(n.account_id, n.transaction_id, n.device_id, 'unknown')
            LIMIT 200
            """)
            for row in r.result_set:
                rows.append({"From account": row[0], "Relationship": row[1], "To type": row[2], "To ID": row[3]})
        else:
            for s, t in self.memory["sends"]:
                rows.append({"From account": s, "Relationship": "SENDS", "To type": "Transaction", "To ID": t})
            for a, d in self.memory["uses"]:
                rows.append({"From account": a, "Relationship": "USES_DEVICE", "To type": "Device", "To ID": d})
            for a, b, reason in self.memory["links"]:
                rows.append({"From account": a, "Relationship": "LINKED_TO", "To type": "Account", "To ID": b})
        return rows
