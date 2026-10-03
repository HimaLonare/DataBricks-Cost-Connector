from pathlib import Path
import csv
import json

from databricks.sql import connect
from dotenv import load_dotenv
import os

from discovery import discover_system_tables, probe_table_counts
from normalizer import save_json, normalize_all

from collectors.billing_usage import collect_billing_usage
from collectors.pricing import collect_list_prices
from collectors.compute import (
    collect_warehouse_events,
    collect_warehouses,
    collect_node_types,
)
from collectors.sql import collect_query_history


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
RAW_DIR = OUTPUT_DIR / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")


# ============================================================
# VALIDATE ENVIRONMENT
# ============================================================

if not DATABRICKS_HOST:
    raise RuntimeError("DATABRICKS_HOST is missing from .env")

if not DATABRICKS_TOKEN:
    raise RuntimeError("DATABRICKS_TOKEN is missing from .env")

if not DATABRICKS_HTTP_PATH:
    raise RuntimeError("DATABRICKS_HTTP_PATH is missing from .env")


# ============================================================
# DATABASE CONNECTION
# ============================================================

connection = connect(
    server_hostname=DATABRICKS_HOST.replace("https://", "").replace(
        "http://", ""
    ),
    http_path=DATABRICKS_HTTP_PATH,
    access_token=DATABRICKS_TOKEN,
)


# ============================================================
# EXPECTED COST-RELATED SYSTEM TABLES
# ============================================================

COST_TABLES = [
    "system.billing.usage",
    "system.billing.list_prices",
    "system.billing.account_prices",
    "system.billing.attributed_usage",
    "system.billing.cloud_infra_cost",

    "system.compute.clusters",
    "system.compute.instance_events",
    "system.compute.instance_pools",
    "system.compute.node_timeline",
    "system.compute.node_types",
    "system.compute.warehouse_events",
    "system.compute.warehouses",

    "system.lakeflow.job_run_timeline",
    "system.lakeflow.job_task_run_timeline",
    "system.lakeflow.job_tasks",
    "system.lakeflow.jobs",
    "system.lakeflow.pipeline_update_timeline",
    "system.lakeflow.pipelines",

    "system.query.history",

    "system.serving.endpoint_usage",

    "system.storage.auto_upgrade_operations_history",
    "system.storage.predictive_optimization_operations_history",
    "system.storage.table_metrics_history",
]


# ============================================================
# COVERAGE HELPERS
# ============================================================

def get_timestamp_value(row, possible_keys):
    """
    Find the first timestamp-like field available in a source row.
    Returns a string representation or None.
    """

    if not isinstance(row, dict):
        return None

    for key in possible_keys:
        value = row.get(key)

        if value is not None:
            return str(value)

    return None


def get_time_range(rows):
    """
    Extract earliest/latest source timestamps where possible.

    Different Databricks system tables use different timestamp
    column names, so several common names are checked.
    """

    if not rows:
        return None, None

    timestamp_keys = [
        "usage_start_time",
        "usage_end_time",
        "start_time",
        "end_time",
        "event_time",
        "event_start_time",
        "event_end_time",
        "warehouse_start_time",
        "warehouse_end_time",
        "execution_start_time",
        "execution_end_time",
        "query_start_time",
        "query_end_time",
        "change_time",
        "update_time",
        "created_at",
        "updated_at",
        "billing_period_start",
        "billing_period_end",
    ]

    values = []

    for row in rows:
        value = get_timestamp_value(row, timestamp_keys)

        if value:
            values.append(value)

    if not values:
        return None, None

    values = sorted(values)

    return values[0], values[-1]


def status_for_count(count):
    if count > 0:
        return "collected"

    return "empty"


# ============================================================
# MAIN
# ============================================================

coverage = []

try:

    # --------------------------------------------------------
    # SYSTEM TABLE DISCOVERY
    # --------------------------------------------------------

    print("\n=== SYSTEM TABLE DISCOVERY ===")

    discovered_tables = discover_system_tables(connection)

    print(
        f"Discovered {len(discovered_tables)} system table entries"
    )


    # --------------------------------------------------------
    # COST TABLE PROBE
    # --------------------------------------------------------

    print("\n=== COST TABLE PROBE ===")

    probe_results = probe_table_counts(
        connection,
        COST_TABLES,
    )

    for result in probe_results:

        table_name = result["table"]
        status = result["status"]
        count = result["count"]

        print(
            f"{table_name} -> "
            f"{status.upper()} ({count} records)"
        )

        coverage.append(
            {
                "category": table_name,
                "dataset": table_name,
                "purpose": "Cost-related Databricks system dataset",
                "status": status,
                "record_count": count,
                "earliest_source_timestamp": "",
                "latest_source_timestamp": "",
                "required_permission": "Databricks system-table access",
                "explanation": (
                    "Records available in the trial/development workspace."
                    if status == "collected"
                    else
                    "Dataset is accessible but currently contains zero records."
                    if status == "empty"
                    else
                    "Dataset probe failed."
                ),
            }
        )


    # --------------------------------------------------------
    # BILLING USAGE
    # --------------------------------------------------------

    print("\n=== BILLING USAGE ===")

    billing_rows = collect_billing_usage(connection)

    print(
        f"Billing usage records collected: {len(billing_rows)}"
    )

    save_json(
        RAW_DIR / "billing_usage.json",
        billing_rows,
    )


    # --------------------------------------------------------
    # LIST PRICES
    # --------------------------------------------------------

    print("\n=== LIST PRICES ===")

    pricing_rows = collect_list_prices(connection)

    print(
        f"List price records collected: {len(pricing_rows)}"
    )

    save_json(
        RAW_DIR / "list_prices.json",
        pricing_rows,
    )


    # --------------------------------------------------------
    # NODE TYPES
    # --------------------------------------------------------

    print("\n=== NODE TYPES ===")

    node_type_rows = collect_node_types(connection)

    print(
        f"Node type records collected: {len(node_type_rows)}"
    )

    save_json(
        RAW_DIR / "node_types.json",
        node_type_rows,
    )


    # --------------------------------------------------------
    # WAREHOUSE EVENTS
    # --------------------------------------------------------

    print("\n=== WAREHOUSE EVENTS ===")

    warehouse_event_rows = collect_warehouse_events(connection)

    print(
        f"Warehouse event records collected: "
        f"{len(warehouse_event_rows)}"
    )

    save_json(
        RAW_DIR / "warehouse_events.json",
        warehouse_event_rows,
    )


    # --------------------------------------------------------
    # WAREHOUSES
    # --------------------------------------------------------

    print("\n=== WAREHOUSES ===")

    warehouse_rows = collect_warehouses(connection)

    print(
        f"Warehouse records collected: "
        f"{len(warehouse_rows)}"
    )

    save_json(
        RAW_DIR / "warehouses.json",
        warehouse_rows,
    )


    # --------------------------------------------------------
    # QUERY HISTORY
    # --------------------------------------------------------

    print("\n=== QUERY HISTORY ===")

    query_history_rows = collect_query_history(connection)

    print(
        f"Query history records collected: "
        f"{len(query_history_rows)}"
    )

    save_json(
        RAW_DIR / "query_history.json",
        query_history_rows,
    )


    # --------------------------------------------------------
    # NORMALIZATION
    # --------------------------------------------------------

    print("\n=== NORMALIZATION ===")

    normalized_records = normalize_all(
        billing_rows=billing_rows,
        pricing_rows=pricing_rows,
        node_type_rows=node_type_rows,
        warehouse_event_rows=warehouse_event_rows,
        warehouse_rows=warehouse_rows,
        query_history_rows=query_history_rows,
    )

    print(
        f"Normalized records created: "
        f"{len(normalized_records)}"
    )

    save_json(
        OUTPUT_DIR / "normalized.json",
        normalized_records,
    )


    # --------------------------------------------------------
    # UPDATE COVERAGE WITH SOURCE TIMESTAMPS
    # --------------------------------------------------------

    collected_dataset_rows = {
        "system.billing.usage": billing_rows,
        "system.billing.list_prices": pricing_rows,
        "system.compute.node_types": node_type_rows,
        "system.compute.warehouse_events": warehouse_event_rows,
        "system.compute.warehouses": warehouse_rows,
        "system.query.history": query_history_rows,
    }

    for item in coverage:

        dataset = item["dataset"]

        rows = collected_dataset_rows.get(dataset)

        if rows is None:
            continue

        earliest, latest = get_time_range(rows)

        item["earliest_source_timestamp"] = earliest or ""
        item["latest_source_timestamp"] = latest or ""


    # --------------------------------------------------------
    # ADD COLLECTIONS THAT WERE SUCCESSFUL BUT NOT IN PROBE
    # --------------------------------------------------------

    known_coverage_datasets = {
        item["dataset"]
        for item in coverage
    }

    collected_datasets = {
        "system.billing.usage": billing_rows,
        "system.billing.list_prices": pricing_rows,
        "system.compute.node_types": node_type_rows,
        "system.compute.warehouse_events": warehouse_event_rows,
        "system.compute.warehouses": warehouse_rows,
        "system.query.history": query_history_rows,
    }

    for dataset, rows in collected_datasets.items():

        if dataset in known_coverage_datasets:
            continue

        earliest, latest = get_time_range(rows)

        coverage.append(
            {
                "category": dataset,
                "dataset": dataset,
                "purpose": "Collected cost-related system dataset",
                "status": status_for_count(len(rows)),
                "record_count": len(rows),
                "earliest_source_timestamp": earliest or "",
                "latest_source_timestamp": latest or "",
                "required_permission": "Databricks system-table access",
                "explanation": (
                    "Collected successfully."
                    if rows
                    else
                    "Dataset is accessible but currently empty."
                ),
            }
        )


    # --------------------------------------------------------
    # SAVE COVERAGE REPORT
    # --------------------------------------------------------

    coverage_path = OUTPUT_DIR / "coverage.csv"

    coverage_columns = [
        "category",
        "dataset",
        "purpose",
        "status",
        "record_count",
        "earliest_source_timestamp",
        "latest_source_timestamp",
        "required_permission",
        "explanation",
    ]

    with open(
        coverage_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=coverage_columns,
        )

        writer.writeheader()

        for row in coverage:

            writer.writerow(
                {
                    column: row.get(column, "")
                    for column in coverage_columns
                }
            )


    print(
        f"\nCoverage report saved to: "
        f"{coverage_path}"
    )

    print(
        f"Normalized output saved to: "
        f"{OUTPUT_DIR / 'normalized.json'}"
    )

    print(
        f"Raw output saved to: "
        f"{RAW_DIR}"
    )

    print("\n=== COLLECTION COMPLETE ===")


finally:

    connection.close()

    print("\nDatabricks connection closed.")