from datetime import datetime

def investigate_account(store, account_id, question=""):
    data = store.account_investigation(account_id)
    if not data:
        return {"subject_id": account_id, "summary": f"No account named {account_id} was found.", "indicators": [], "evidence": []}
    indicators = []
    if int(data.get("risk_score") or 0) >= 70:
        indicators.append(f"Configured risk score is high ({data['risk_score']}/100).")
    if data["shared_devices"]:
        others = sorted({x["other_account"] for x in data["shared_devices"]})
        devices = sorted({x["device_id"] for x in data["shared_devices"]})
        indicators.append(f"Shares device(s) {', '.join(devices)} with account(s) {', '.join(others)}.")
    high_value = [t for t in data["transactions"] if float(t.get("amount") or 0) >= 5000]
    if high_value:
        indicators.append(f"{len(high_value)} outgoing transaction(s) are at least 5,000 currency units.")
    pending = [t for t in data["transactions"] if str(t.get("status", "")).lower() in ("pending_review", "declined")]
    if pending:
        indicators.append(f"{len(pending)} outgoing transaction(s) are pending review or declined.")
    if not indicators:
        indicators.append("No configured indicator triggered using the available graph data.")
    evidence = []
    for tx in data["transactions"]:
        evidence.append({"Evidence type": "Outgoing transaction", "Entity": tx["transaction_id"],
                         "Details": f"Amount: {tx.get('amount')}; status: {tx.get('status')}; receiver: {tx.get('receiver')}"})
    for item in data["shared_devices"]:
        evidence.append({"Evidence type": "Shared device", "Entity": item["device_id"],
                         "Details": f"Also connected to account {item['other_account']}"})
    evidence.append({"Evidence type": "Account profile", "Entity": data["account_id"],
                     "Details": f"Name: {data['name']}; configured risk score: {data['risk_score']}/100"})
    summary = (f"Investigation of {data['account_id']} ({data['name']}) found {len(indicators)} configured indicator(s) "
               f"and {len(evidence)} evidence record(s). These connections justify review, but do not prove fraud.")
    return {"subject_id": account_id, "summary": summary, "indicators": indicators, "evidence": evidence}

def investigate_transaction(store, transaction_id):
    data = store.transaction_investigation(transaction_id)
    if not data:
        return {"subject_id": transaction_id, "summary": f"No transaction named {transaction_id} was found.", "evidence": [], "actions": []}
    evidence = [
        {"Entity": transaction_id, "Relationship": "Transaction", "Details": f"Amount {data['amount']}; status {data['status']}; timestamp {data['timestamp']}"},
        {"Entity": data["sender"], "Relationship": "SENDS", "Details": "Sender account"},
        {"Entity": data["receiver"], "Relationship": "RECEIVED_BY", "Details": "Recipient account"},
    ]
    for item in data["shared_devices"]:
        evidence.append({"Entity": item["device_id"], "Relationship": "SHARED_DEVICE", "Details": f"Also used by account {item['other_account']}"})
    actions = ["Review transaction context and account history with an authorized analyst."]
    if float(data.get("amount") or 0) >= 5000:
        actions.append("Check whether the amount is consistent with the account's normal activity.")
    if data["shared_devices"]:
        actions.append("Review shared-device links and verify whether the accounts have a legitimate relationship.")
    if str(data.get("status", "")).lower() in ("pending_review", "declined"):
        actions.append("Inspect the existing review/decline reason before taking further action.")
    summary = (f"{transaction_id} is a {data['status']} transaction of {data['amount']} from {data['sender']} "
               f"to {data['receiver']}. The graph returned {len(data['shared_devices'])} shared-device connection(s). "
               "This is an investigation lead, not a fraud verdict.")
    return {"subject_id": transaction_id, "summary": summary, "evidence": evidence, "actions": actions}
