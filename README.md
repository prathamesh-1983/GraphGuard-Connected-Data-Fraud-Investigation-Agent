# GraphGuard — Graph-Powered Fraud Investigation

**GraphGuard** is a hackathon prototype that demonstrates how connected data can support explainable transaction investigations. It models accounts, transactions, and devices in a graph, then traverses their relationships to surface potentially relevant connections and produce an evidence-oriented investigation summary.

> **Responsible-use notice:** All bundled records are synthetic. A shared device, large transaction, declined transaction, or risk indicator is not proof of fraud. GraphGuard is an educational prototype, not a production fraud-detection system and must not be used to make real financial decisions.

## Table of contents

- [Problem](#problem)
- [Solution](#solution)
- [Features](#features)
- [Technology stack](#technology-stack)
- [Architecture](#architecture)
- [Graph data model](#graph-data-model)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Run locally](#run-locally)
- [Explore the demo](#explore-the-demo)
- [Example Cypher query](#example-cypher-query)
- [Run tests](#run-tests)
- [Configuration and database modes](#configuration-and-database-modes)
- [Limitations and future improvements](#limitations-and-future-improvements)
- [Privacy and responsible use](#privacy-and-responsible-use)
- [Hackathon track](#hackathon-track)
- [License](#license)

## Problem

Transaction investigations often require analysts to connect information spread across accounts, payments, recipients, and devices. Looking at each record separately can make it difficult to spot relationships that span multiple entities.

GraphGuard explores a graph-based approach: represent entities as nodes, their interactions as relationships, and investigate those connections with graph queries. The aim is to make the evidence behind a risk indicator easier to inspect.

## Solution

GraphGuard provides a small interactive dashboard for exploring a synthetic financial network. An investigator can select an account or transaction, inspect connected entities, and review transparent indicators generated from the available demo data.

The baseline uses **Cypher queries and deterministic Python rules**. It does not require an LLM API key, and it does not claim to be an autonomous or production-ready fraud agent. An LLM-based explanation or tool-selection loop could be added later, grounded only in verified query results.

## Features

- **Graph-backed investigations:** query connected accounts, transactions, and devices using FalkorDB and Cypher.
- **Account investigation:** inspect an account and related entities.
- **Transaction tracing:** explore the sender, transaction, and recipient relationship.
- **Shared-device discovery:** find other accounts connected to the same device.
- **Evidence-oriented output:** show the connections and simple indicators behind a result.
- **Interactive Streamlit dashboard:** explore the sample graph through a browser.
- **Demo fallback:** explore the interface with an in-memory data store if FalkorDB is not available.
- **Synthetic sample data:** run the project without using real customer or payment information.

## Technology stack

| Technology | Purpose |
|---|---|
| Python | Investigation logic and application backend |
| Streamlit | Interactive web dashboard |
| FalkorDB | Graph database for connected entities and relationships |
| Cypher | Query language for traversing graph relationships |
| Docker Compose | Convenient local FalkorDB startup |
| Pytest | Automated tests for investigation logic |

## Architecture

```text
User
  |
  v
Streamlit dashboard (app.py)
  |
  v
Investigation service (backend/investigation.py)
  |
  v
Graph store abstraction (backend/graph_db.py)
  |
  +---- FalkorDB + Cypher (preferred for graph demonstration)
  |
  +---- In-memory demo fallback (for local exploration)
```

The application separates the interface, graph access, sample data, and investigation rules so each part can be explored and improved independently.

## Graph data model

GraphGuard represents the demo domain using three node types.

### Nodes

- `(:Account {account_id, name, risk_score})`
- `(:Transaction {transaction_id, amount, status, timestamp})`
- `(:Device {device_id, device_type})`

### Relationships

```text
(Account)-[:SENDS]->(Transaction)
(Transaction)-[:RECEIVED_BY]->(Account)
(Account)-[:USES_DEVICE]->(Device)
(Account)-[:LINKED_TO {reason}]->(Account)
```

This model makes it possible to traverse from an account to its transactions and recipients, or from an account to a device and then to other accounts that use the same device.

## Project structure

```text
graphguard/
├── app.py                         # Streamlit user interface
├── backend/
│   ├── __init__.py
│   ├── graph_db.py                # FalkorDB connection and graph-store logic
│   ├── demo_data.py               # Synthetic sample graph data
│   └── investigation.py           # Investigation rules and evidence summaries
├── tests/
│   └── test_investigation.py      # Automated tests
├── requirements.txt               # Python dependencies
├── docker-compose.yml             # Local FalkorDB service
├── .env.example                   # Example environment configuration
├── LICENSE                        # MIT license
└── README.md
```

## Requirements

- Python 3.10 or later
- Docker Desktop or Docker Engine with Compose (recommended for FalkorDB mode)
- Git (optional, for cloning the repository)

## Run locally

### 1. Get the source code

If you have published the project on GitHub:

```bash
git clone https://github.com/prathamesh-1983/GraphGuard-Connected-Data-Fraud-Investigation-Agent
cd graphguard
```

Alternatively, extract the project ZIP and open a terminal in the `graphguard` folder.

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Start FalkorDB (recommended)

From the project directory, run:

```bash
docker compose up -d
```

The provided configuration is intended to make FalkorDB available locally on port `6379`. Check the current [FalkorDB documentation](https://docs.falkordb.com/) if your Docker image, client library, or local setup differs.

To stop the database container:

```bash
docker compose down
```

### 5. Start the dashboard

```bash
streamlit run app.py
```

Open the local URL printed in your terminal. Streamlit commonly uses:

```text
http://localhost:8501
```

If FalkorDB cannot be reached, the app can use its in-memory demo mode. Use the dashboard's database-mode setting to require a live FalkorDB connection when you want to demonstrate graph database integration.

## Explore the demo

Suggested walkthrough:

1. Start the app and load or reset the synthetic demo dataset.
2. Select account `A100` and run an investigation.
3. Inspect the related accounts, devices, transactions, and the evidence shown by the dashboard.
4. Trace transaction `T9003` to review its sender and recipient connections.
5. Open the graph explorer to inspect relationships visually.
6. Repeat the investigation after resetting the demo dataset to restore the sample state.

The exact results depend on the sample data and the current implementation. Verify the demo on your own machine before recording or publishing a walkthrough.

## Example Cypher query

The following query finds other accounts that share a device with the selected account:

```cypher
MATCH (a:Account)-[:USES_DEVICE]->(d:Device)
      <-[:USES_DEVICE]-(other:Account)
WHERE a.account_id = $account_id
  AND other.account_id <> a.account_id
RETURN other.account_id AS related_account,
       d.device_id AS shared_device
LIMIT 20
```

The `$account_id` value should be passed as a query parameter by the application. A shared device is only a relationship worth reviewing; it does **not** establish that either account has committed fraud.

## Run tests

From the project root, run:

```bash
pytest -q
```

If `pytest` is not installed in your environment, install the project dependencies first. Review any failures and resolve them before presenting the project as tested.

## Configuration and database modes

- `.env.example` contains example configuration values; copy it to `.env` if the application setup requires local environment variables.
- Do not commit real credentials, API keys, or private customer data.
- **FalkorDB mode** is recommended when demonstrating graph queries and connected-data investigation.
- **In-memory mode** is a fallback for exploring the interface when a local graph database is unavailable.

Do not put secrets into source code or upload `.env` files containing credentials to a public repository.

## Limitations and future improvements

This project is an educational baseline. Potential next steps include:

- Add more synthetic scenarios and configurable investigation rules.
- Add richer multi-hop graph traversals and graph algorithms.
- Add evidence provenance and timestamps to every investigation finding.
- Expand automated tests for graph-store behavior and failure cases.
- Improve graph visualization and exportable investigation reports.
- Add an optional LLM explanation layer that cites retrieved graph evidence and cannot invent missing facts.
- Add authentication, authorization, audit logging, monitoring, and data-retention controls before considering any real-world deployment.

The current baseline uses simple, transparent rules rather than a trained fraud model. It does not include live payment integrations, real customer data, production authentication, or a validated fraud-scoring system.

## Privacy and responsible use

- Use synthetic, public, or otherwise authorized data only.
- Do not upload personal, banking, or payment data to a public repository.
- Treat scores and indicators as prompts for human review, not as conclusions.
- Test the application and confirm its behavior before relying on screenshots, metrics, or demo claims.
- Clearly disclose AI-assisted development where required by the event or platform rules.

## Hackathon track

**Graph Hacks 2026 — Track 1: Agents That Act on Connected Data**

GraphGuard demonstrates how graph relationships can support an investigation workflow. The graph is central to the concept because relevant context is assembled by traversing account → device → other account and account → transaction → recipient relationships.

Before submitting, ensure the public repository includes the source code, setup instructions, graph model, representative Cypher queries, and a short demo video or deployment link if required by the event. Review the current rules and submission checklist at the [official hackathon page](https://www.wemakedevs.org/hackathons/falkordb).

## License

This project is released under the MIT License. See [`LICENSE`](LICENSE) for details.
