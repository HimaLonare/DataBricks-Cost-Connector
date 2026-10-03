from decimal import Decimal
from datetime import date, datetime, timezone

from src.normalizer import (
    make_json_safe,
    row_to_dict,
    rows_to_dicts,
    parse_json_object,
    first_not_none,
    normalize_billing_usage,
    normalize_list_price,
    normalize_node_type,
    normalize_warehouse_event,
    normalize_warehouse,
    normalize_query_history,
    normalize_all,
)


COLLECTION_TIME = "2026-10-03T10:00:00+00:00"


# ============================================================
# JSON / SERIALIZATION HELPERS
# ============================================================

def test_make_json_safe_decimal_preserves_precision():
    value = Decimal(
        "123.456789012345678901234567890"
    )

    result = make_json_safe(value)

    assert result == (
        "123.456789012345678901234567890"
    )


def test_make_json_safe_datetime_is_utc_iso():
    value = datetime(
        2026,
        10,
        3,
        10,
        30,
        45,
        tzinfo=timezone.utc,
    )

    result = make_json_safe(value)

    assert result == (
        "2026-10-03T10:30:45+00:00"
    )


def test_make_json_safe_naive_datetime_assumes_utc():
    value = datetime(
        2026,
        10,
        3,
        10,
        30,
        45,
    )

    result = make_json_safe(value)

    assert result == (
        "2026-10-03T10:30:45+00:00"
    )


def test_make_json_safe_date():
    value = date(2026, 10, 3)

    result = make_json_safe(value)

    assert result == "2026-10-03"


def test_make_json_safe_nested_values():
    value = {
        "amount": Decimal("12.345678"),
        "timestamp": datetime(
            2026,
            10,
            3,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        "items": [
            Decimal("1.23"),
            date(2026, 10, 3),
        ],
    }

    result = make_json_safe(value)

    assert result == {
        "amount": "12.345678",
        "timestamp": (
            "2026-10-03T10:00:00+00:00"
        ),
        "items": [
            "1.23",
            "2026-10-03",
        ],
    }


def test_row_to_dict():
    row = {
        "account_id": "account",
        "workspace_id": "workspace",
        "usage_quantity": Decimal("1.500000"),
    }

    result = row_to_dict(row)

    assert result["account_id"] == "account"
    assert result["workspace_id"] == "workspace"
    assert result["usage_quantity"] == "1.500000"


def test_rows_to_dicts():
    rows = [
        {
            "id": 1,
            "value": Decimal("1.25"),
        },
        {
            "id": 2,
            "value": Decimal("2.50"),
        },
    ]

    result = rows_to_dicts(rows)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["value"] == "1.25"
    assert result[1]["id"] == 2
    assert result[1]["value"] == "2.50"


def test_parse_json_object_valid():
    value = (
        '{"team": "data", '
        '"environment": "test"}'
    )

    result = parse_json_object(value)

    assert result == {
        "team": "data",
        "environment": "test",
    }


def test_parse_json_object_handles_malformed_json():
    value = '{"warehouse_id": '

    result = parse_json_object(value)

    assert result == {}


def test_parse_json_object_handles_none():
    result = parse_json_object(None)

    assert result == {}


def test_parse_json_object_handles_non_object_json():
    result = parse_json_object(
        '["item1", "item2"]'
    )

    assert result == {}


def test_first_not_none():
    result = first_not_none(
        None,
        None,
        "first-value",
        "second-value",
    )

    assert result == "first-value"


# ============================================================
# BILLING USAGE
# ============================================================

def test_billing_usage_normalization():
    row = {
        "account_id": "account-test",
        "workspace_id": "workspace-test",
        "record_id": "record-123",
        "sku_name": "TEST_SKU",
        "cloud": "AWS",
        "usage_start_time": (
            "2026-10-03T01:00:00+00:00"
        ),
        "usage_end_time": (
            "2026-10-03T02:00:00+00:00"
        ),
        "usage_date": "2026-10-03",
        "custom_tags": (
            '{"environment": "test"}'
        ),
        "usage_unit": "DBU",
        "usage_quantity": (
            "0.123456789012345678"
        ),
        "usage_metadata": (
            '{"warehouse_id": "warehouse-123", '
            '"job_id": null}'
        ),
        "identity_metadata": (
            '{"run_as": "test-user", '
            '"created_by": null}'
        ),
        "record_type": "ORIGINAL",
        "ingestion_date": "2026-10-03",
        "billing_origin_product": "TEST_PRODUCT",
        "product_features": (
            '{"sql_tier": "PRO"}'
        ),
        "usage_type": "COMPUTE",
    }

    result = normalize_billing_usage(
        row,
        COLLECTION_TIME,
    )

    assert result["platform"] == "databricks"
    assert result["billing_account_id"] == (
        "account-test"
    )
    assert result["workspace_id"] == (
        "workspace-test"
    )
    assert result["source_category"] == (
        "billing_usage"
    )
    assert result["source_record_id"] == (
        "record-123"
    )

    assert result["resource_workload_id"] == (
        "warehouse-123"
    )

    assert result["service_product"] == (
        "TEST_PRODUCT"
    )

    assert result["sku"] == "TEST_SKU"

    assert result["consumed_quantity"] == (
        "0.123456789012345678"
    )

    assert result["consumed_unit"] == "DBU"

    assert result[
        "user_service_principal_attribution"
    ] == "test-user"

    assert result[
        "tags_allocation_metadata"
    ] == {
        "environment": "test"
    }

    assert result["usage_start"] == (
        "2026-10-03T01:00:00+00:00"
    )

    assert result["usage_end"] == (
        "2026-10-03T02:00:00+00:00"
    )

    assert result["collection_time"] == (
        COLLECTION_TIME
    )


# ============================================================
# LIST PRICES
# ============================================================

def test_list_price_normalization():
    row = {
        "account_id": "account-test",
        "price_start_time": (
            "2026-06-05T00:00:00+00:00"
        ),
        "price_end_time": None,
        "sku_name": "TEST_SKU",
        "cloud": "AWS",
        "currency_code": "USD",
        "usage_unit": "DBU",
        "pricing": (
            '{"default": 0.9, '
            '"effective_list": '
            '{"default": 0.9}}'
        ),
    }

    result = normalize_list_price(
        row,
        COLLECTION_TIME,
    )

    assert result["source_category"] == (
        "list_prices"
    )

    assert result["sku"] == "TEST_SKU"

    assert result["currency"] == "USD"

    assert result["pricing_quantity"] == 1

    assert result["pricing_unit"] == "DBU"

    assert result["list_unit_price"] == "0.9"

    assert result["billing_period_start"] == (
        "2026-06-05T00:00:00+00:00"
    )

    assert result["billing_period_end"] is None


# ============================================================
# NODE TYPES
# ============================================================

def test_node_type_normalization():
    row = {
        "account_id": "account-test",
        "node_type": "m5d.large",
        "core_count": 2,
        "memory_mb": 8192,
        "gpu_count": 0,
    }

    result = normalize_node_type(
        row,
        COLLECTION_TIME,
    )

    assert result["platform"] == "databricks"

    assert result["billing_account_id"] == (
        "account-test"
    )

    assert result["workspace_id"] is None

    assert result["source_category"] == (
        "node_types"
    )

    assert result["source_record_id"] == (
        "m5d.large"
    )

    assert result["resource_workload_id"] == (
        "m5d.large"
    )

    assert result["resource_workload_name"] == (
        "m5d.large"
    )

    assert result["resource_workload_type"] == (
        "COMPUTE_NODE_TYPE"
    )

    # Node types are reference metadata.
    assert result["consumed_quantity"] is None
    assert result["list_unit_price"] is None
    assert result["list_cost"] is None
    assert result["effective_cost"] is None
    assert result["billed_cost"] is None

    assert result["additional_metadata"] == {
        "core_count": 2,
        "memory_mb": 8192,
        "gpu_count": 0,
    }

    assert result["collection_time"] == (
        COLLECTION_TIME
    )


def test_node_type_normalization_missing_fields():
    row = {
        "account_id": "account-test",
        "node_type": "test-node",
    }

    result = normalize_node_type(
        row,
        COLLECTION_TIME,
    )

    assert result["billing_account_id"] == (
        "account-test"
    )

    assert result["source_record_id"] == (
        "test-node"
    )

    assert result["resource_workload_id"] == (
        "test-node"
    )

    assert result["additional_metadata"] == {
        "core_count": None,
        "memory_mb": None,
        "gpu_count": None,
    }


# ============================================================
# WAREHOUSE EVENTS
# ============================================================

def test_warehouse_event_normalization():
    row = {
        "account_id": "account-test",
        "workspace_id": "workspace-test",
        "warehouse_id": "warehouse-123",
        "event_type": "SCALED_UP",
        "cluster_count": 1,
        "event_time": (
            "2026-10-03T09:16:05.947000+00:00"
        ),
    }

    result = normalize_warehouse_event(
        row,
        COLLECTION_TIME,
    )

    assert result["source_category"] == (
        "warehouse_events"
    )

    assert result["resource_workload_id"] == (
        "warehouse-123"
    )

    assert result["resource_workload_type"] == (
        "SQL_WAREHOUSE"
    )

    assert result["consumed_quantity"] == 1

    assert result["consumed_unit"] == (
        "cluster"
    )

    assert result["usage_start"] == (
        "2026-10-03T09:16:05.947000+00:00"
    )

    assert result["additional_metadata"][
        "event_type"
    ] == "SCALED_UP"


# ============================================================
# WAREHOUSES
# ============================================================

def test_warehouse_normalization():
    row = {
        "warehouse_id": "warehouse-123",
        "workspace_id": "workspace-test",
        "account_id": "account-test",
        "warehouse_name": "Test Warehouse",
        "warehouse_type": "SERVERLESS",
        "warehouse_channel": "CURRENT",
        "warehouse_size": "SMALL",
        "min_clusters": 1,
        "max_clusters": 1,
        "auto_stop_minutes": 10,
        "tags": (
            '{"environment": "test"}'
        ),
        "change_time": (
            "2026-10-02T11:44:41.249000+00:00"
        ),
        "delete_time": None,
        "created_by": "test-user",
    }

    result = normalize_warehouse(
        row,
        COLLECTION_TIME,
    )

    assert result["source_category"] == (
        "warehouses"
    )

    assert result["resource_workload_id"] == (
        "warehouse-123"
    )

    assert result["resource_workload_name"] == (
        "Test Warehouse"
    )

    assert result["resource_workload_type"] == (
        "SERVERLESS"
    )

    assert result[
        "user_service_principal_attribution"
    ] == "test-user"

    assert result[
        "tags_allocation_metadata"
    ] == {
        "environment": "test"
    }

    assert result["additional_metadata"][
        "warehouse_size"
    ] == "SMALL"


# ============================================================
# QUERY HISTORY
# ============================================================

def test_query_history_normalization():
    row = {
        "account_id": "account-test",
        "workspace_id": "workspace-test",
        "statement_id": "statement-123",
        "executed_by": "test-user",
        "executed_as": None,
        "execution_status": "FINISHED",
        "statement_type": "SELECT",
        "compute": (
            '{"type": "WAREHOUSE", '
            '"warehouse_id": "warehouse-123"}'
        ),
        "query_source": (
            '{"job_info": {}}'
        ),
        "query_tags": (
            '{"team": "data"}'
        ),
        "client_application": "pytest",
        "client_driver": "test-driver",
        "session_id": "session-123",
        "total_duration_ms": 1500,
        "execution_duration_ms": 1000,
        "compilation_duration_ms": 500,
        "read_rows": 10,
        "produced_rows": 2,
        "read_bytes": 1000,
        "written_bytes": 200,
        "start_time": (
            "2026-10-03T10:00:00+00:00"
        ),
        "end_time": (
            "2026-10-03T10:00:01+00:00"
        ),
        "update_time": (
            "2026-10-03T10:00:02+00:00"
        ),
    }

    result = normalize_query_history(
        row,
        COLLECTION_TIME,
    )

    assert result["source_category"] == (
        "query_history"
    )

    assert result["source_record_id"] == (
        "statement-123"
    )

    assert result["resource_workload_id"] == (
        "warehouse-123"
    )

    assert result["resource_workload_type"] == (
        "WAREHOUSE"
    )

    assert result["consumed_quantity"] == 1500

    assert result["consumed_unit"] == (
        "millisecond"
    )

    assert result[
        "user_service_principal_attribution"
    ] == "test-user"

    assert result[
        "tags_allocation_metadata"
    ] == '{"team": "data"}'

    assert result["usage_start"] == (
        "2026-10-03T10:00:00+00:00"
    )

    assert result["usage_end"] == (
        "2026-10-03T10:00:01+00:00"
    )


# ============================================================
# NORMALIZE ALL
# ============================================================

def test_empty_input_produces_empty_output():
    result = normalize_all(
        [],
        [],
        [],
        [],
        [],
        [],
    )

    assert result == []


def test_normalize_all_combines_all_datasets():
    billing = [
        {
            "account_id": "account",
            "workspace_id": "workspace",
            "record_id": "billing-1",
            "sku_name": "SKU",
            "cloud": "AWS",
            "usage_start_time": (
                "2026-10-03T01:00:00+00:00"
            ),
            "usage_end_time": (
                "2026-10-03T02:00:00+00:00"
            ),
            "usage_date": "2026-10-03",
            "custom_tags": "{}",
            "usage_unit": "DBU",
            "usage_quantity": (
                "1.000000000000000000"
            ),
            "usage_metadata": "{}",
            "identity_metadata": "{}",
            "record_type": "ORIGINAL",
            "ingestion_date": "2026-10-03",
            "billing_origin_product": "TEST",
            "product_features": "{}",
            "usage_type": "COMPUTE",
        }
    ]

    pricing = [
        {
            "account_id": "account",
            "price_start_time": (
                "2026-06-05T00:00:00+00:00"
            ),
            "price_end_time": None,
            "sku_name": "SKU",
            "cloud": "AWS",
            "currency_code": "USD",
            "usage_unit": "DBU",
            "pricing": (
                '{"effective_list": '
                '{"default": 1.25}}'
            ),
        }
    ]

    node_types = [
        {
            "account_id": "account",
            "node_type": "m5d.large",
            "core_count": 2,
            "memory_mb": 8192,
            "gpu_count": 0,
        }
    ]

    warehouse_events = [
        {
            "account_id": "account",
            "workspace_id": "workspace",
            "warehouse_id": "warehouse",
            "event_type": "SCALED_UP",
            "cluster_count": 1,
            "event_time": (
                "2026-10-03T01:00:00+00:00"
            ),
        }
    ]

    warehouses = [
        {
            "warehouse_id": "warehouse",
            "workspace_id": "workspace",
            "account_id": "account",
            "warehouse_name": "Test Warehouse",
            "warehouse_type": "SERVERLESS",
            "warehouse_channel": "CURRENT",
            "warehouse_size": "SMALL",
            "min_clusters": 1,
            "max_clusters": 1,
            "auto_stop_minutes": 10,
            "tags": "{}",
            "change_time": (
                "2026-10-03T01:00:00+00:00"
            ),
            "delete_time": None,
            "created_by": "test-user",
        }
    ]

    query_history = [
        {
            "account_id": "account",
            "workspace_id": "workspace",
            "statement_id": "statement",
            "executed_by": "test-user",
            "executed_as": None,
            "execution_status": "FINISHED",
            "statement_type": "SELECT",
            "compute": (
                '{"type": "WAREHOUSE", '
                '"warehouse_id": "warehouse"}'
            ),
            "query_source": "{}",
            "query_tags": "{}",
            "client_application": "pytest",
            "client_driver": "test",
            "session_id": "session",
            "total_duration_ms": 100,
            "execution_duration_ms": 90,
            "compilation_duration_ms": 10,
            "read_rows": 1,
            "produced_rows": 1,
            "read_bytes": 100,
            "written_bytes": 0,
            "start_time": (
                "2026-10-03T01:00:00+00:00"
            ),
            "end_time": (
                "2026-10-03T01:00:01+00:00"
            ),
            "update_time": (
                "2026-10-03T01:00:02+00:00"
            ),
        }
    ]

    result = normalize_all(
        billing,
        pricing,
        node_types,
        warehouse_events,
        warehouses,
        query_history,
    )

    assert len(result) == 6

    categories = [
        record["source_category"]
        for record in result
    ]

    assert "billing_usage" in categories
    assert "list_prices" in categories
    assert "node_types" in categories
    assert "warehouse_events" in categories
    assert "warehouses" in categories
    assert "query_history" in categories


# ============================================================
# EDGE CASES
# ============================================================

def test_malformed_source_record_does_not_crash():
    row = {
        "account_id": "account",
        "workspace_id": "workspace",
        "record_id": "record",
        "sku_name": "SKU",
        "usage_quantity": "not-a-number",
        "usage_metadata": "INVALID JSON",
        "identity_metadata": "INVALID JSON",
        "product_features": "INVALID JSON",
        "custom_tags": "INVALID JSON",
        "billing_origin_product": None,
        "usage_unit": None,
        "usage_start_time": None,
        "usage_end_time": None,
        "usage_date": None,
        "ingestion_date": None,
        "record_type": None,
        "usage_type": None,
    }

    result = normalize_billing_usage(
        row,
        COLLECTION_TIME,
    )

    assert result["source_category"] == (
        "billing_usage"
    )

    assert result["source_record_id"] == (
        "record"
    )

    assert result["additional_metadata"][
        "usage_metadata"
    ] == {}

    assert result["additional_metadata"][
        "identity_metadata"
    ] == {}

    assert result["additional_metadata"][
        "product_features"
    ] == {}

    assert result[
        "tags_allocation_metadata"
    ] == {}


def test_billing_usage_missing_optional_fields():
    row = {
        "account_id": "account",
        "workspace_id": "workspace",
        "record_id": "billing-1",
        "sku_name": "SKU",
        "usage_unit": "DBU",
        "usage_quantity": "2.50",
    }

    result = normalize_billing_usage(
        row,
        COLLECTION_TIME,
    )

    assert result["billing_account_id"] == (
        "account"
    )

    assert result["workspace_id"] == (
        "workspace"
    )

    assert result["source_record_id"] == (
        "billing-1"
    )

    assert result["sku"] == "SKU"

    assert result["consumed_quantity"] == (
        "2.50"
    )

    assert result["usage_start"] is None
    assert result["usage_end"] is None


def test_normalize_all_preserves_decimal_precision():
    billing = [
        {
            "account_id": "account",
            "record_id": "billing-precision",
            "usage_quantity": (
                "0.123456789012345678901234567890"
            ),
            "usage_unit": "DBU",
        }
    ]

    result = normalize_all(
        billing,
        [],
        [],
        [],
        [],
        [],
    )

    assert len(result) == 1

    assert result[0]["consumed_quantity"] == (
        "0.123456789012345678901234567890"
    )