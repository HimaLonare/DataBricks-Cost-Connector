from databricks.sql import connect


# ============================================================
# COST-RELATED DATASETS TO INVESTIGATE
# ============================================================

COST_DATASETS = {
    "billing_usage": "system.billing.usage",
    "list_pricing": "system.billing.list_prices",
    "account_workspace_consumption": "system.billing.account_prices",
    "cluster_compute": "system.compute.clusters",
    "compute_instance_events": "system.compute.instance_events",
    "instance_pools": "system.compute.instance_pools",
    "node_timeline": "system.compute.node_timeline",
    "node_types": "system.compute.node_types",
    "warehouse_events": "system.compute.warehouse_events",
    "warehouses": "system.compute.warehouses",
    "jobs": "system.lakeflow.jobs",
    "job_run_timeline": "system.lakeflow.job_run_timeline",
    "job_tasks": "system.lakeflow.job_tasks",
    "job_task_run_timeline": "system.lakeflow.job_task_run_timeline",
    "pipelines": "system.lakeflow.pipelines",
    "pipeline_update_timeline": "system.lakeflow.pipeline_update_timeline",
    "query_history": "system.query.history",
    "serverless_endpoint_usage": "system.serving.endpoint_usage",
    "storage_auto_upgrade": "system.storage.auto_upgrade_operations_history",
    "storage_predictive_optimization": (
        "system.storage.predictive_optimization_operations_history"
    ),
    "storage_table_metrics": "system.storage.table_metrics_history",
    "attributed_usage": "system.billing.attributed_usage",
    "cloud_infrastructure_cost": "system.billing.cloud_infra_cost",
}


# ============================================================
# SYSTEM TABLE DISCOVERY
# ============================================================

def discover_system_tables(connection):
    """
    Discover schemas and tables available under the Databricks
    system catalog.

    Returns a list of dictionaries containing:
        catalog
        schema
        table
    """

    discovered = []

    cursor = connection.cursor()

    try:
        # ----------------------------------------------------
        # Discover system schemas
        # ----------------------------------------------------

        cursor.execute("SHOW SCHEMAS IN system")

        schemas = cursor.fetchall()

        for row in schemas:

            # Databricks SQL connector rows can be accessed
            # either by position or by attribute depending on
            # connector/version.

            schema_name = None

            if hasattr(row, "databaseName"):
                schema_name = row.databaseName

            elif hasattr(row, "schemaName"):
                schema_name = row.schemaName

            elif len(row) > 0:
                schema_name = row[0]

            if not schema_name:
                continue

            # ------------------------------------------------
            # Discover tables in each schema
            # ------------------------------------------------

            schema_cursor = connection.cursor()

            try:
                schema_cursor.execute(
                    f"SHOW TABLES IN system.`{schema_name}`"
                )

                tables = schema_cursor.fetchall()

                for table_row in tables:

                    table_name = None

                    # Typical SHOW TABLES output:
                    # database, tableName, isTemporary

                    if hasattr(table_row, "tableName"):
                        table_name = table_row.tableName

                    elif len(table_row) >= 2:
                        table_name = table_row[1]

                    elif len(table_row) == 1:
                        table_name = table_row[0]

                    if not table_name:
                        continue

                    discovered.append(
                        {
                            "catalog": "system",
                            "schema": schema_name,
                            "table": table_name,
                        }
                    )

            except Exception as exc:

                # Continue discovery for other schemas.
                discovered.append(
                    {
                        "catalog": "system",
                        "schema": schema_name,
                        "table": None,
                        "status": "failed",
                        "error": str(exc),
                    }
                )

            finally:
                schema_cursor.close()

    finally:
        cursor.close()

    return discovered


# ============================================================
# TABLE COUNT PROBE
# ============================================================

def probe_table_counts(connection, tables):
    """
    Probe each requested table with SELECT COUNT(*).

    Every returned dictionary has the same core keys:

        table
        status
        count

    Status values:

        collected
        empty
        permission_denied
        unavailable_in_account
        failed

    This consistent structure is important because client.py
    expects result["count"] to exist.
    """

    results = []

    for table_name in tables:

        result = {
            "table": table_name,
            "status": "failed",
            "count": 0,
            "error": "",
        }

        cursor = connection.cursor()

        try:

            query = f"""
                SELECT COUNT(*) AS record_count
                FROM {table_name}
            """

            cursor.execute(query)

            row = cursor.fetchone()

            count = 0

            if row is not None:

                try:
                    count = int(row[0])
                except (TypeError, ValueError):
                    count = 0

            result["count"] = count

            if count > 0:
                result["status"] = "collected"
            else:
                result["status"] = "empty"

        except Exception as exc:

            error_message = str(exc)

            result["error"] = error_message

            lower_error = error_message.lower()

            # ------------------------------------------------
            # Permission / access errors
            # ------------------------------------------------

            permission_terms = [
                "permission denied",
                "not authorized",
                "unauthorized",
                "access denied",
                "insufficient privileges",
                "does not have permission",
                "privilege",
            ]

            if any(
                term in lower_error
                for term in permission_terms
            ):
                result["status"] = "permission_denied"

            # ------------------------------------------------
            # Table/account availability errors
            # ------------------------------------------------

            elif (
                "table or view not found" in lower_error
                or "table not found" in lower_error
                or "cannot be found" in lower_error
                or "does not exist" in lower_error
            ):
                result["status"] = "unavailable_in_account"

            else:
                result["status"] = "failed"

            # Keep count present even when probing fails.
            result["count"] = 0

        finally:
            cursor.close()

        results.append(result)

    return results


# ============================================================
# LOOK UP ONE DATASET
# ============================================================

def get_dataset_table(dataset_name):
    """
    Return the Databricks system table associated with a
    logical dataset name.
    """

    return COST_DATASETS.get(dataset_name)


# ============================================================
# DISCOVER WHETHER EXPECTED DATASETS EXIST
# ============================================================

def match_expected_datasets(discovered_tables):
    """
    Match the expected cost-related datasets against the tables
    discovered in the Databricks system catalog.

    Returns:

        {
            logical_dataset_name: {
                "table": "...",
                "available": True/False
            }
        }
    """

    available_tables = set()

    for item in discovered_tables:

        schema_name = item.get("schema")
        table_name = item.get("table")

        if not schema_name or not table_name:
            continue

        available_tables.add(
            f"system.{schema_name}.{table_name}"
        )

    matches = {}

    for logical_name, table_name in COST_DATASETS.items():

        matches[logical_name] = {
            "table": table_name,
            "available": table_name in available_tables,
        }

    return matches