import os
import streamlit as st
from dotenv import load_dotenv
from backend.graph_db import GraphStore
from backend.investigation import investigate_account, investigate_transaction
from backend.demo_data import seed_demo_data

load_dotenv()
st.set_page_config(page_title="GraphGuard | Connected-Data Investigator", page_icon="🕸️", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; max-width: 1400px;}
.hero {padding: 1.3rem 1.5rem; border-radius: 16px; background: linear-gradient(120deg,#111827,#312e81); color: white; margin-bottom: 1rem;}
.hero h1 {margin: 0; font-size: 2.2rem;}
.hero p {color:#d1d5db; margin:.35rem 0 0 0;}
.small-muted {color:#64748b;font-size:.9rem}
</style>
<div class="hero">
<h1>🕸️ GraphGuard</h1>
<p>Agents That Act on Connected Data · Explainable graph-powered fraud investigation</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Control panel")
    st.caption("Uses synthetic demo data. Alerts are investigative leads, not proof of fraud.")
    db_mode = st.selectbox("Graph database", ["Auto (FalkorDB, fallback demo mode)", "FalkorDB only"])
    st.divider()
    if st.button("Load / reset demo dataset", use_container_width=True):
        try:
            store = GraphStore(require_db=(db_mode == "FalkorDB only"))
            seed_demo_data(store)
            st.session_state["seeded"] = True
            st.success("Demo graph loaded.")
        except Exception as e:
            st.error(f"Could not load graph: {e}")
    st.markdown("**Project links**")
    st.markdown("- [FalkorDB docs](https://docs.falkordb.com/)")
    st.markdown("- [Source repository checklist](README.md)")

@st.cache_resource
def get_store(require_db=False):
    return GraphStore(require_db=require_db)

require_db = db_mode == "FalkorDB only"
try:
    store = get_store(require_db)
    if not st.session_state.get("seeded"):
        seed_demo_data(store)
        st.session_state["seeded"] = True
    db_label = "FalkorDB connected" if store.connected else "Local demo fallback"
except Exception as e:
    st.error(f"Database initialization failed: {e}")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
metrics = store.metrics()
col1.metric("Accounts", metrics["accounts"])
col2.metric("Transactions", metrics["transactions"])
col3.metric("Devices", metrics["devices"])
col4.metric("Graph engine", "FalkorDB" if store.connected else "Demo mode")
st.caption(f"Status: {db_label} · Data is synthetic and generated for demonstration.")

tab1, tab2, tab3, tab4 = st.tabs(["Investigate account", "Investigate transaction", "Graph explorer", "About"])

with tab1:
    st.subheader("Investigate a potentially risky account")
    account_ids = store.account_ids()
    default_account = "A100" if "A100" in account_ids else (account_ids[0] if account_ids else "")
    account_id = st.selectbox("Account ID", account_ids, index=account_ids.index(default_account) if default_account in account_ids else 0)
    question = st.text_input("Investigation question", "Why is this account worth reviewing?")
    if st.button("Run investigation", type="primary", key="investigate_account"):
        result = investigate_account(store, account_id, question)
        st.session_state["last_result"] = result
    result = st.session_state.get("last_result")
    if result and result.get("subject_id") == account_id:
        st.markdown("### Agent assessment")
        st.info(result["summary"])
        st.markdown("**Risk indicators found**")
        if result["indicators"]:
            for item in result["indicators"]:
                st.markdown(f"- {item}")
        else:
            st.success("No configured risk indicators were found in the available demo graph.")
        st.markdown("**Evidence trail**")
        st.dataframe(result["evidence"], use_container_width=True, hide_index=True)
        st.caption("The agent uses explicit graph evidence and transparent rules. A shared device or high-risk connection is not, by itself, proof of wrongdoing.")

with tab2:
    st.subheader("Trace a transaction through connected entities")
    tx_ids = store.transaction_ids()
    tx_id = st.selectbox("Transaction ID", tx_ids, index=tx_ids.index("T9003") if "T9003" in tx_ids else 0)
    if st.button("Trace transaction", type="primary"):
        st.session_state["tx_result"] = investigate_transaction(store, tx_id)
    tx_result = st.session_state.get("tx_result")
    if tx_result and tx_result.get("subject_id") == tx_id:
        st.info(tx_result["summary"])
        st.markdown("**Connected entities and evidence**")
        st.dataframe(tx_result["evidence"], use_container_width=True, hide_index=True)
        st.markdown("**Suggested next actions**")
        for action in tx_result["actions"]:
            st.markdown(f"- {action}")

with tab3:
    st.subheader("Connected-data overview")
    st.write("This explorer summarizes links returned by graph queries. Use the investigation tabs to inspect evidence in more detail.")
    if st.button("Refresh graph overview"):
        st.session_state["graph_overview"] = store.overview()
    overview = st.session_state.get("graph_overview") or store.overview()
    st.dataframe(overview, use_container_width=True, hide_index=True)
    st.code("(:Account)-[:SENDS]->(:Transaction)-[:RECEIVED_BY]->(:Account)\n(:Account)-[:USES_DEVICE]->(:Device)\n(:Account)-[:LINKED_TO]->(:Account)", language="text")

with tab4:
    st.subheader("What makes GraphGuard graph-native?")
    st.markdown("""
- **Connected evidence:** accounts, transactions and devices are modeled as nodes and relationships.
- **Multi-hop investigation:** the agent traces relationships to identify shared devices and connected activity.
- **Explainable outputs:** every indicator is tied to query results rather than invented by the language model.
- **Action-oriented workflow:** the agent recommends review steps and creates an evidence trail.
- **Responsible framing:** alerts are leads for human review, not automatic fraud verdicts.
""")
    st.markdown("### Architecture")
    st.code("Streamlit UI → Investigation Agent → GraphStore → FalkorDB (Cypher)\n                                      ↘ Transparent risk rules + evidence report", language="text")
    st.markdown("### Demo disclaimer")
    st.warning("This prototype uses synthetic data and simple heuristics. It is not a production fraud-detection system and should not be used to make real financial decisions.")
