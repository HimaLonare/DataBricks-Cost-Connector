# Databricks Cost Connector

A Python connector for connecting to a live Databricks Trial workspace, discovering accessible cost-management and operational datasets, collecting source records, and normalizing applicable records into a common cost-oriented schema.

## Assessment

This project was developed for the **Databricks Cost Connector Assessment**.

The connector focuses on:

- Live Databricks authentication and connection
- System catalog discovery
- Cost and usage dataset discovery
- Complete collection of accessible records
- Raw record preservation
- Normalization into a common schema
- Explicit coverage and collection-status reporting
- Automated tests for normalization and failure handling

No database ingestion or persistent database writes are performed.

---

## Project Structure

```text
databricks-cost-connector/
│
├── src/
│   ├── __init__.py
│   ├── client.py
│   ├── discovery.py
│   ├── normalizer.py
│   │
│   └── collectors/
│       ├── __init__.py
│       ├── billing_usage.py
│       ├── compute.py
│       ├── pricing.py
│       └── sql.py
│
├── tests/
│   └── ...
│
├── submission/
│   ├── evidence/
│   │   └── live_run.txt
│   ├── samples/
│   │   ├── raw_billing_usage.json
│   │   ├── raw_list_prices.json
│   │   ├── raw_node_types.json
│   │   ├── raw_warehouse_events.json
│   │   ├── raw_warehouses.json
│   │   ├── raw_query_history.json
│   │   └── normalized.json
│   └── coverage.csv
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt