import csv
import os
from datetime import datetime


COVERAGE_OUTPUT_FILE = "output/coverage.csv"


# =========================================================
# INVESTIGATED DATASETS
# =========================================================

CATEGORIES = [
    {
        "category": "billing_usage",
        "dataset": "system.billing.usage",
        "purpose": "Detailed usage records for billing and consumption",
        "required_capability": "Workspace access to system billing usage data",
        "timestamp_fields": ["usage_start_time", "usage_end_time"],
    },
    {
        "category": "list_pricing",
        "dataset": "system.billing.list_prices",
        "purpose": "SKU list pricing",
        "required_capability": "Workspace access to system billing pricing data",
        "timestamp_fields": ["price_start_time", "price_end_time"],
    },
    {
        "category": "account_prices",
        "dataset": "system.billing.account_prices",
        "purpose": "Account-specific pricing",
        "required_capability": "Account pricing data availability",
        "timestamp_fields": [],
    },
    {
        "category": "attributed_usage",
        "dataset": "system.billing.attributed_usage",
        "purpose": "Attributed usage and workload allocation",
        "required_capability": "Attributed usage data availability",
        "timestamp_fields": [],
    },
    {
        "category": "cloud_infrastructure_cost",
        "dataset": "system.billing.cloud_infra_cost",
        "purpose": "Cloud infrastructure cost information",
        "required_capability": "Cloud infrastructure cost data availability",
        "timestamp_fields": [],
    },
    {
        "category": "cluster_compute",
        "dataset": "system.compute.clusters",
        "purpose": "Cluster and compute information",
        "required_capability": "Compute system-table access",
        "timestamp_fields": [],
    },
    {
        "category": "instance_events",
        "dataset": "system.compute.instance_events",
        "purpose": "Compute instance lifecycle events",
        "required_capability": "Compute instance event data availability",
        "timestamp_fields": [],
    },
    {
        "category": "instance_pools",
        "dataset": "system.compute.instance_pools",
        "purpose": "Instance pool information",
        "required_capability": "Compute instance pool data availability",
        "timestamp_fields": [],
    },
    {
        "category": "node_timeline",
        "dataset": "system.compute.node_timeline",
        "purpose": "Compute node timeline",
        "required_capability": "Compute node timeline data availability",
        "timestamp_fields": [],
    },
    {
        "category": "node_types",
        "dataset": "system.compute.node_types",
        "purpose": "Compute node type information",
        "required_capability": "Compute node type data availability",
        "timestamp_fields": [],
    },
    {
        "category": "sql_warehouse_events",
        "dataset": "system.compute.warehouse_events",
        "purpose": "SQL warehouse consumption events",
        "required_capability": "SQL warehouse system-table access",
        "timestamp_fields": ["event_time"],
    },
    {
        "category": "sql_warehouses",
        "dataset": "system.compute.warehouses",
        "purpose": "SQL warehouse metadata",
        "required_capability": "SQL warehouse metadata access",
        "timestamp_fields": ["change_time", "delete_time"],
    },
    {
        "category": "jobs",
        "dataset": "system.lakeflow.jobs",
        "purpose": "Job workload information",
        "required_capability": "Lakeflow job system-table access",
        "timestamp_fields": [],
    },
    {
        "category": "job_runs",
        "dataset": "system.lakeflow.job_run_timeline",
        "purpose": "Job execution timeline",
        "required_capability": "Lakeflow job-run data availability",
        "timestamp_fields": [],
    },
    {
        "category": "job_tasks",
        "dataset": "system.lakeflow.job_tasks",
        "purpose": "Job task metadata",
        "required_capability": "Lakeflow job-task data availability",
        "timestamp_fields": [],
    },
    {
        "category": "job_task_runs",
        "dataset": "system.lakeflow.job_task_run_timeline",
        "purpose": "Job task execution timeline",
        "required_capability": "Lakeflow task-run data availability",
        "timestamp_fields": [],
    },
    {
        "category": "pipelines",
        "dataset": "system.lakeflow.pipelines",
        "purpose": "Pipeline metadata",
        "required_capability": "Lakeflow pipeline data availability",
        "timestamp_fields": [],
    },
    {
        "category": "pipeline_updates",
        "dataset": "system.lakeflow.pipeline_update_timeline",
        "purpose": "Pipeline execution timeline",
        "required_capability": "Lakeflow pipeline-update data availability",
        "timestamp_fields": [],
    },
    {
        "category": "query_history",
        "dataset": "system.query.history",
        "purpose": "SQL query execution and workload history",
        "required_capability": "Query history system-table access",
        "timestamp_fields": ["start_time", "end_time", "update_time"],
    },
    {
        "category": "serverless",
        "dataset": "system.serving.endpoint_usage",
        "purpose": "Serverless serving endpoint usage",
        "required_capability": "Serving endpoint usage data availability",
        "timestamp_fields": [],
    },
    {
        "category": "storage_auto_upgrade",
        "dataset": "system.storage.auto_upgrade_operations_history",
        "purpose": "Storage auto-upgrade operations",
        "required_capability": "Storage system-table access",
        "timestamp_fields": [],
    },
    {
        "category": "storage_predictive_optimization",
        "dataset": "system.storage.predictive_optimization_operations_history",
        "purpose": "Storage predictive optimization operations",
        "required_capability": "Storage predictive optimization data availability",
        "timestamp_fields": [],
    },
    {
        "category": "storage_table_metrics",
        "dataset": "system.storage.table_metrics_history",
        "purpose": "Storage table metrics",
        "required_capability": "Storage table metrics data availability",
        "timestamp_fields": [],
    },
]


# =========================================================
# TIMESTAMP HELPERS
# =========================================================

def parse_timestamp(value):
    """
    Parse an ISO timestamp into a datetime.

    Returns None when the value is missing or invalid.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if not isinstance(value, str):
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        return None


def get_timestamp_range(rows, timestamp_fields):
    """
    Find the earliest and latest source timestamps
    across the supplied rows.
    """

    timestamps = []

    for row in rows:

        if not isinstance(row, dict):
            continue

        for field in timestamp_fields:

            value = row.get(field)

            timestamp = parse_timestamp(value)

            if timestamp is not None:
                timestamps.append(timestamp)

    if not timestamps:
        return None, None

    earliest = min(timestamps)
    latest = max(timestamps)

    return (
        earliest.isoformat(),
        latest.isoformat(),
    )


# =========================================================
# COVERAGE REPORT
# =========================================================

def build_coverage_report(
    probe_results,
    collected_data=None,
):
    """
    Build a coverage report.

    collected_data is optional and should contain raw rows
    keyed by dataset name when timestamp ranges are available.
    """

    if collected_data is None:
        collected_data = {}

    result_by_table = {
        result["table"]: result
        for result in probe_results
    }

    coverage = []

    for category in CATEGORIES:

        dataset = category["dataset"]

        probe = result_by_table.get(dataset)

        rows = collected_data.get(
            dataset,
            [],
        )

        earliest_timestamp, latest_timestamp = (
            get_timestamp_range(
                rows,
                category["timestamp_fields"],
            )
        )

        # -------------------------------------------------
        # Dataset not discovered
        # -------------------------------------------------

        if probe is None:

            coverage.append({
                "category": category["category"],
                "dataset": dataset,
                "purpose": category["purpose"],
                "status": "unavailable_in_account",
                "record_count": "",
                "earliest_source_timestamp": "",
                "latest_source_timestamp": "",
                "required_permission_or_capability":
                    category["required_capability"],
                "explanation": (
                    "Dataset was not visible during "
                    "system table discovery."
                ),
            })

            continue

        status = probe["status"]

        # -------------------------------------------------
        # Collected
        # -------------------------------------------------

        if status == "collected":

            explanation = (
                "Dataset was accessible and contained "
                "records during live collection."
            )

        # -------------------------------------------------
        # Empty
        # -------------------------------------------------

        elif status == "empty":

            explanation = (
                "Dataset was accessible but contained "
                "zero records in the trial workspace."
            )

        # -------------------------------------------------
        # Failed
        # -------------------------------------------------

        elif status == "failed":

            error = probe.get(
                "error"
            ) or ""

            error_lower = error.lower()

            if (
                "permission" in error_lower
                or "privilege" in error_lower
                or "not authorized" in error_lower
                or "access denied" in error_lower
            ):

                status = "permission_denied"

                explanation = (
                    "Dataset was discovered but the "
                    "connected identity could not access it."
                )

            else:

                explanation = (
                    "Dataset access failed during probing: "
                    + error
                )

        # -------------------------------------------------
        # Unknown
        # -------------------------------------------------

        else:

            explanation = (
                "Dataset returned an unrecognized "
                "probe status."
            )

        coverage.append({
            "category": category["category"],
            "dataset": dataset,
            "purpose": category["purpose"],
            "status": status,
            "record_count": probe.get(
                "record_count"
            ),
            "earliest_source_timestamp":
                earliest_timestamp or "",
            "latest_source_timestamp":
                latest_timestamp or "",
            "required_permission_or_capability":
                category["required_capability"],
            "explanation": explanation,
        })

    return coverage


# =========================================================
# SAVE CSV
# =========================================================

def save_coverage_report(
    coverage,
    filepath=COVERAGE_OUTPUT_FILE,
):
    """
    Save coverage report as CSV.
    """

    directory = os.path.dirname(filepath)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    fieldnames = [
        "category",
        "dataset",
        "purpose",
        "status",
        "record_count",
        "earliest_source_timestamp",
        "latest_source_timestamp",
        "required_permission_or_capability",
        "explanation",
    ]

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(coverage)