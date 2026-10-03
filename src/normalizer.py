import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional


# ============================================================
# JSON SAFE CONVERSION
# ============================================================

def make_json_safe(value: Any) -> Any:
    """
    Convert Python / Databricks values into JSON-safe values.

    Decimal values are converted to strings so that precision
    is not lost.

    Naive datetime values are assumed to be UTC.
    """

    if value is None:
        return None

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            make_json_safe(item)
            for item in value
        ]

    if isinstance(value, (str, int, float, bool)):
        return value

    # Databricks Row
    if hasattr(value, "asDict"):
        try:
            return make_json_safe(
                value.asDict(recursive=True)
            )
        except Exception:
            pass

    if hasattr(value, "_asdict"):
        try:
            return make_json_safe(
                value._asdict()
            )
        except Exception:
            pass

    return str(value)


# ============================================================
# ROW CONVERSION
# ============================================================

def row_to_dict(row: Any) -> Dict[str, Any]:
    """
    Convert a Databricks Row or dictionary into a normal
    JSON-safe dictionary.
    """

    if row is None:
        return {}

    if isinstance(row, dict):
        return make_json_safe(row)

    if hasattr(row, "asDict"):
        try:
            return make_json_safe(
                row.asDict(recursive=True)
            )
        except Exception:
            pass

    if hasattr(row, "_asdict"):
        try:
            return make_json_safe(
                row._asdict()
            )
        except Exception:
            pass

    if hasattr(row, "_fields"):
        try:
            return make_json_safe(
                dict(zip(row._fields, row))
            )
        except Exception:
            pass

    return {
        "value": make_json_safe(row)
    }


def rows_to_dicts(
    rows: Optional[List[Any]]
) -> List[Dict[str, Any]]:

    if not rows:
        return []

    return [
        row_to_dict(row)
        for row in rows
    ]


# ============================================================
# JSON OUTPUT
# ============================================================

def save_json(path: str, data: Any) -> None:

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            make_json_safe(data),
            file,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# HELPERS
# ============================================================

def parse_json_object(value: Any) -> Dict[str, Any]:
    """
    Parse a JSON object.

    Returns {} for:
    - None
    - malformed JSON
    - JSON arrays
    - non-string/non-dict values
    """

    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        return {}

    try:
        parsed = json.loads(value)
    except (
        json.JSONDecodeError,
        TypeError,
        ValueError
    ):
        return {}

    if not isinstance(parsed, dict):
        return {}

    return parsed


def first_not_none(*values):
    """
    Return the first value that is not None.
    """

    for value in values:
        if value is not None:
            return value

    return None


def normalize_timestamp(value: Any) -> Any:
    """
    Normalize datetime values.

    Naive datetime values are assumed to be UTC.
    """

    if value is None:
        return None

    if isinstance(value, datetime):

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=timezone.utc
            )

        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return value


def collection_timestamp(
    supplied_collection_time: Optional[Any]
) -> str:

    if supplied_collection_time is not None:
        return str(supplied_collection_time)

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# BILLING USAGE
# ============================================================

def normalize_billing_usage(
    row: Dict[str, Any],
    collection_time: Optional[Any] = None
) -> Dict[str, Any]:

    usage_metadata = parse_json_object(
        row.get("usage_metadata")
    )

    identity_metadata = parse_json_object(
        row.get("identity_metadata")
    )

    product_features = parse_json_object(
        row.get("product_features")
    )

    custom_tags = parse_json_object(
        row.get("custom_tags")
    )

    user_attribution = first_not_none(
        identity_metadata.get("run_as"),
        identity_metadata.get("created_by"),
        row.get("user_identity"),
        row.get("user"),
        row.get("user_name")
    )

    resource_id = first_not_none(
        usage_metadata.get("cluster_id"),
        usage_metadata.get("warehouse_id"),
        usage_metadata.get("job_id"),
        usage_metadata.get("pipeline_id"),
        usage_metadata.get("endpoint_id")
    )

    resource_name = first_not_none(
        usage_metadata.get("cluster_name"),
        usage_metadata.get("warehouse_name"),
        usage_metadata.get("job_name"),
        usage_metadata.get("pipeline_name"),
        usage_metadata.get("endpoint_name")
    )

    return {
        "platform":
            "databricks",

        "billing_account_id":
            row.get("account_id"),

        "workspace_id":
            row.get("workspace_id"),

        "source_category":
            "billing_usage",

        "source_record_id":
            row.get("record_id"),

        "resource_workload_id":
            resource_id,

        "resource_workload_name":
            resource_name,

        "resource_workload_type":
            row.get("usage_type"),

        "service_product":
            row.get("billing_origin_product"),

        "sku":
            row.get("sku_name"),

        "usage_start":
            normalize_timestamp(
                row.get("usage_start_time")
            ),

        "usage_end":
            normalize_timestamp(
                row.get("usage_end_time")
            ),

        "billing_period_start":
            None,

        "billing_period_end":
            None,

        "consumed_quantity":
            row.get("usage_quantity"),

        "consumed_unit":
            row.get("usage_unit"),

        "pricing_quantity":
            None,

        "pricing_unit":
            None,

        "list_unit_price":
            None,

        "list_cost":
            None,

        "contracted_cost":
            None,

        "effective_cost":
            None,

        "billed_cost":
            None,

        "currency":
            None,

        "user_service_principal_attribution":
            user_attribution,

        "user_service_principal":
            user_attribution,

        "tags_allocation_metadata":
            custom_tags,

        "source_update_time":
            normalize_timestamp(
                row.get("ingestion_date")
            ),

        "collection_time":
            collection_timestamp(
                collection_time
            ),

        "additional_metadata":
            make_json_safe({
                "cloud":
                    row.get("cloud"),

                "usage_date":
                    row.get("usage_date"),

                "record_type":
                    row.get("record_type"),

                "usage_metadata":
                    usage_metadata,

                "identity_metadata":
                    identity_metadata,

                "product_features":
                    product_features
            })
    }


# ============================================================
# LIST PRICES
# ============================================================

def normalize_list_price(
    row: Dict[str, Any],
    collection_time: Optional[Any] = None
) -> Dict[str, Any]:

    pricing = parse_json_object(
        row.get("pricing")
    )

    list_price = pricing.get("default")

    # Preserve price precision as a string.
    if list_price is not None:
        list_price = str(list_price)

    price_start_time = normalize_timestamp(
        row.get("price_start_time")
    )

    price_end_time = normalize_timestamp(
        row.get("price_end_time")
    )

    return {
        "platform":
            "databricks",

        "billing_account_id":
            row.get("account_id"),

        "workspace_id":
            None,

        "source_category":
            "list_prices",

        "source_record_id":
            None,

        "resource_workload_id":
            None,

        "resource_workload_name":
            None,

        "resource_workload_type":
            None,

        "service_product":
            None,

        "sku":
            row.get("sku_name"),

        "usage_start":
            price_start_time,

        "usage_end":
            price_end_time,

        "billing_period_start":
            price_start_time,

        "billing_period_end":
            price_end_time,

        "consumed_quantity":
            None,

        "consumed_unit":
            row.get("usage_unit"),

        "pricing_quantity":
            1,

        "pricing_unit":
            row.get("usage_unit"),

        "list_unit_price":
            list_price,

        "list_cost":
            None,

        "contracted_cost":
            None,

        "effective_cost":
            None,

        "billed_cost":
            None,

        "currency":
            row.get("currency_code"),

        "user_service_principal_attribution":
            None,

        "tags_allocation_metadata":
            None,

        "source_update_time":
            None,

        "collection_time":
            collection_timestamp(
                collection_time
            ),

        "additional_metadata":
            make_json_safe({
                "cloud":
                    row.get("cloud"),

                "pricing":
                    pricing
            })
    }


# ============================================================
# NODE TYPES
# ============================================================

def normalize_node_type(
    row: Dict[str, Any],
    collection_time: Optional[Any] = None
) -> Dict[str, Any]:

    node_type = row.get(
        "node_type"
    )

    return {
        "platform":
            "databricks",

        "billing_account_id":
            row.get("account_id"),

        "workspace_id":
            row.get("workspace_id"),

        "source_category":
            "node_types",

        "source_record_id":
            node_type,

        "resource_workload_id":
            node_type,

        "resource_workload_name":
            node_type,

        "resource_workload_type":
            "COMPUTE_NODE_TYPE",

        "service_product":
            None,

        "sku":
            node_type,

        "usage_start":
            None,

        "usage_end":
            None,

        "billing_period_start":
            None,

        "billing_period_end":
            None,

        "consumed_quantity":
            None,

        "consumed_unit":
            None,

        "pricing_quantity":
            None,

        "pricing_unit":
            None,

        "list_unit_price":
            None,

        "list_cost":
            None,

        "contracted_cost":
            None,

        "effective_cost":
            None,

        "billed_cost":
            None,

        "currency":
            None,

        "user_service_principal_attribution":
            None,

        "tags_allocation_metadata":
            None,

        "source_update_time":
            None,

        "collection_time":
            collection_timestamp(
                collection_time
            ),

        "additional_metadata":
            make_json_safe({
                "core_count":
                    row.get("core_count"),

                "memory_mb":
                    row.get("memory_mb"),

                "gpu_count":
                    row.get("gpu_count")
            })
    }


# ============================================================
# WAREHOUSE EVENTS
# ============================================================

def normalize_warehouse_event(
    row: Dict[str, Any],
    collection_time: Optional[Any] = None
) -> Dict[str, Any]:

    return {
        "platform":
            "databricks",

        "billing_account_id":
            row.get("account_id"),

        "workspace_id":
            row.get("workspace_id"),

        "source_category":
            "warehouse_events",

        "source_record_id":
            row.get("warehouse_id"),

        "resource_workload_id":
            row.get("warehouse_id"),

        "resource_workload_name":
            row.get("warehouse_name"),

        "resource_workload_type":
            "SQL_WAREHOUSE",

        "service_product":
            None,

        "sku":
            None,

        "usage_start":
            normalize_timestamp(
                row.get("event_time")
            ),

        "usage_end":
            None,

        "billing_period_start":
            None,

        "billing_period_end":
            None,

        "consumed_quantity":
            row.get("cluster_count"),

        "consumed_unit":
            "cluster",

        "pricing_quantity":
            None,

        "pricing_unit":
            None,

        "list_unit_price":
            None,

        "list_cost":
            None,

        "contracted_cost":
            None,

        "effective_cost":
            None,

        "billed_cost":
            None,

        "currency":
            None,

        "user_service_principal_attribution":
            None,

        "tags_allocation_metadata":
            None,

        "source_update_time":
            None,

        "collection_time":
            collection_timestamp(
                collection_time
            ),

        "additional_metadata":
            make_json_safe({
                "event_type":
                    row.get("event_type")
            })
    }


# ============================================================
# WAREHOUSES
# ============================================================

def normalize_warehouse(
    row: Dict[str, Any],
    collection_time: Optional[Any] = None
) -> Dict[str, Any]:

    user_attribution = first_not_none(
        row.get("created_by"),
        row.get("creator_name"),
        row.get("creator_user_name")
    )

    return {
        "platform":
            "databricks",

        "billing_account_id":
            row.get("account_id"),

        "workspace_id":
            row.get("workspace_id"),

        "source_category":
            "warehouses",

        "source_record_id":
            row.get("warehouse_id"),

        "resource_workload_id":
            row.get("warehouse_id"),

        "resource_workload_name":
            row.get("warehouse_name"),

        "resource_workload_type":
            row.get("warehouse_type"),

        "service_product":
            row.get("warehouse_type"),

        "sku":
            row.get("warehouse_size"),

        "usage_start":
            normalize_timestamp(
                row.get("change_time")
            ),

        "usage_end":
            normalize_timestamp(
                row.get("delete_time")
            ),

        "billing_period_start":
            None,

        "billing_period_end":
            None,

        "consumed_quantity":
            None,

        "consumed_unit":
            None,

        "pricing_quantity":
            None,

        "pricing_unit":
            None,

        "list_unit_price":
            None,

        "list_cost":
            None,

        "contracted_cost":
            None,

        "effective_cost":
            None,

        "billed_cost":
            None,

        "currency":
            None,

        "user_service_principal_attribution":
            user_attribution,

        "tags_allocation_metadata":
            parse_json_object(
                row.get("tags")
            ),

        "source_update_time":
            normalize_timestamp(
                row.get("change_time")
            ),

        "collection_time":
            collection_timestamp(
                collection_time
            ),

        "additional_metadata":
            make_json_safe({
                "warehouse_size":
                    row.get("warehouse_size"),

                "warehouse_channel":
                    row.get("warehouse_channel"),

                "warehouse_type":
                    row.get("warehouse_type"),

                "min_clusters":
                    row.get("min_clusters"),

                "max_clusters":
                    row.get("max_clusters"),

                "auto_stop_minutes":
                    row.get("auto_stop_minutes")
            })
    }


# ============================================================
# QUERY HISTORY
# ============================================================

def normalize_query_history(
    row: Dict[str, Any],
    collection_time: Optional[Any] = None
) -> Dict[str, Any]:

    compute = parse_json_object(
        row.get("compute")
    )

    query_source = parse_json_object(
        row.get("query_source")
    )

    duration = first_not_none(
        row.get("total_duration_ms"),
        row.get("execution_duration_ms")
    )

    return {
        "platform":
            "databricks",

        "billing_account_id":
            row.get("account_id"),

        "workspace_id":
            row.get("workspace_id"),

        "source_category":
            "query_history",

        "source_record_id":
            row.get("statement_id"),

        "resource_workload_id":
            compute.get("warehouse_id"),

        "resource_workload_name":
            compute.get("warehouse_name"),

        "resource_workload_type":
            compute.get("type"),

        "service_product":
            "SQL",

        "sku":
            None,

        "usage_start":
            normalize_timestamp(
                row.get("start_time")
            ),

        "usage_end":
            normalize_timestamp(
                row.get("end_time")
            ),

        "billing_period_start":
            None,

        "billing_period_end":
            None,

        "consumed_quantity":
            duration,

        "consumed_unit":
            "millisecond"
            if duration is not None
            else None,

        "pricing_quantity":
            None,

        "pricing_unit":
            None,

        "list_unit_price":
            None,

        "list_cost":
            None,

        "contracted_cost":
            None,

        "effective_cost":
            None,

        "billed_cost":
            None,

        "currency":
            None,

        "user_service_principal_attribution":
            row.get("executed_by"),

        "tags_allocation_metadata":
            row.get("query_tags"),

        "source_update_time":
            normalize_timestamp(
                row.get("update_time")
            ),

        "collection_time":
            collection_timestamp(
                collection_time
            ),

        "additional_metadata":
            make_json_safe({
                "query_source":
                    query_source,

                "compute":
                    compute,

                "statement_type":
                    row.get("statement_type"),

                "execution_status":
                    row.get("execution_status"),

                "client_application":
                    row.get("client_application"),

                "client_driver":
                    row.get("client_driver"),

                "session_id":
                    row.get("session_id"),

                "read_rows":
                    row.get("read_rows"),

                "produced_rows":
                    row.get("produced_rows"),

                "read_bytes":
                    row.get("read_bytes"),

                "written_bytes":
                    row.get("written_bytes")
            })
    }


# ============================================================
# NORMALIZE ALL
# ============================================================

def normalize_all(
    billing_rows=None,
    pricing_rows=None,
    node_type_rows=None,
    warehouse_event_rows=None,
    warehouse_rows=None,
    query_history_rows=None,
    collection_time=None
) -> List[Dict[str, Any]]:
    """
    Normalize all collected datasets.

    Parameter names intentionally match the existing client.py.
    """

    normalized = []

    # --------------------------------------------------------
    # Billing usage
    # --------------------------------------------------------

    for row in rows_to_dicts(billing_rows):
        normalized.append(
            normalize_billing_usage(
                row,
                collection_time
            )
        )

    # --------------------------------------------------------
    # List prices
    # --------------------------------------------------------

    for row in rows_to_dicts(pricing_rows):
        normalized.append(
            normalize_list_price(
                row,
                collection_time
            )
        )

    # --------------------------------------------------------
    # Node types
    # --------------------------------------------------------

    for row in rows_to_dicts(node_type_rows):
        normalized.append(
            normalize_node_type(
                row,
                collection_time
            )
        )

    # --------------------------------------------------------
    # Warehouse events
    # --------------------------------------------------------

    for row in rows_to_dicts(warehouse_event_rows):
        normalized.append(
            normalize_warehouse_event(
                row,
                collection_time
            )
        )

    # --------------------------------------------------------
    # Warehouses
    # --------------------------------------------------------

    for row in rows_to_dicts(warehouse_rows):
        normalized.append(
            normalize_warehouse(
                row,
                collection_time
            )
        )

    # --------------------------------------------------------
    # Query history
    # --------------------------------------------------------

    for row in rows_to_dicts(query_history_rows):
        normalized.append(
            normalize_query_history(
                row,
                collection_time
            )
        )

    return normalized