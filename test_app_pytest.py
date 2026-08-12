import os
import threading

import pandas as pd
import psycopg
import pytest
from psycopg.rows import dict_row

from app import create_app
from database import clear_demo_data, get_connection, init_db
from scripts.validate_sources import check_order_totals, validate_source


def test_source_validation_reports_duplicate_and_bad_amounts():
    frame = pd.DataFrame(
        [
            {
                "product_code": "SKU-001",
                "product_name": "Valid Product",
                "unit": "pcs",
                "cost_price": "1.25",
                "sale_price": "2.50",
            },
            {
                "product_code": "SKU-001",
                "product_name": "Duplicate Product",
                "unit": "pcs",
                "cost_price": "-1",
                "sale_price": "bad-price",
            },
        ]
    )

    result = validate_source("products", frame)
    messages = {error["message"] for error in result.errors}

    assert result.total_rows == 2
    assert "duplicate value" in messages
    assert "cannot be negative" in messages
    assert "not a valid number" in messages


def test_order_total_cross_check_flags_mismatch():
    orders = pd.DataFrame(
        [
            {
                "order_id": "ORD-1",
                "customer_id": "C1",
                "order_date": "2026-01-01",
                "order_status": "completed",
                "total_amount": "100.00",
            },
            {
                "order_id": "ORD-2",
                "customer_id": "C1",
                "order_date": "2026-01-02",
                "order_status": "completed",
                "total_amount": "50.00",
            },
        ]
    )
    items = pd.DataFrame(
        [
            {"order_id": "ORD-1", "product_code": "SKU-1", "quantity": 2, "unit_price": 45.0, "subtotal": 90.0},
            {"order_id": "ORD-2", "product_code": "SKU-1", "quantity": 1, "unit_price": 50.0, "subtotal": 50.0},
        ]
    )

    result = validate_source("orders", orders)
    check_order_totals(orders, items, result)
    result.finish()

    mismatches = [error for error in result.errors if error["column"] == "total_amount"]
    assert len(mismatches) == 1
    assert mismatches[0]["row_number"] == 2
    assert result.invalid_rows == 1


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set")
def test_product_api_and_inventory_update():
    database_url = os.environ["TEST_DATABASE_URL"]
    init_db(database_url)
    clear_demo_data(database_url)

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": database_url,
            "SECRET_KEY": "pytest-key",
        }
    )
    client = app.test_client()

    response = client.post(
        "/products/new",
        data={
            "product_code": "SKU-PYTEST-001",
            "product_name": "Pytest RS485 Module",
            "category": "Controllers",
            "brand": "Generic",
            "model": "PY-RS485",
            "unit": "pcs",
            "cost_price": "5.50",
            "sale_price": "10.00",
            "supplier_name": "Sample Parts Store",
            "supplier_city": "Toronto",
            "usage_scene": "pytest sample",
            "current_quantity": "5",
            "minimum_stock": "1",
            "safety_stock": "2",
            "location": "Test shelf",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    product_list = client.get("/api/products?product_code=SKU-PYTEST-001")
    assert product_list.status_code == 200
    assert product_list.get_json()["total"] == 1

    with get_connection(database_url) as conn:
        product = conn.execute(
            "SELECT id FROM products WHERE product_code = ?",
            ("SKU-PYTEST-001",),
        ).fetchone()

    update = client.post(
        "/api/inventory/update",
        json={
            "product_id": product["id"],
            "change_type": "stock_out",
            "quantity": 2,
            "reason": "pytest stock-out check",
        },
    )
    assert update.status_code == 200
    assert update.get_json()["quantity_after"] == 3


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set")
def test_api_error_contract():
    database_url = os.environ["TEST_DATABASE_URL"]
    init_db(database_url)
    clear_demo_data(database_url)

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": database_url,
            "SECRET_KEY": "pytest-key",
        }
    )
    client = app.test_client()

    # missing required field -> 400 validation_error with the offending field named
    missing_field = client.post("/api/inventory/update", json={"change_type": "stock_in", "quantity": 1})
    assert missing_field.status_code == 400
    body = missing_field.get_json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["field"] == "product_id"

    # missing product -> 404 not_found, no field (it's a lookup miss, not a bad field)
    missing_product = client.post(
        "/api/inventory/update",
        json={"product_id": 999999, "change_type": "stock_in", "quantity": 1},
    )
    assert missing_product.status_code == 404
    assert missing_product.get_json()["error"]["code"] == "not_found"

    # create a product with zero stock, then try to stock_out more than available -> 409 conflict
    with get_connection(database_url) as conn:
        cursor = conn.execute(
            """
            INSERT INTO products (product_code, product_name, unit)
            VALUES (?, ?, ?)
            RETURNING id
            """,
            ("SKU-CONFLICT-001", "Conflict Test Product", "pcs"),
        )
        product_id = cursor.fetchone()["id"]
        conn.commit()

    conflict = client.post(
        "/api/inventory/update",
        json={"product_id": product_id, "change_type": "stock_out", "quantity": 5},
    )
    assert conflict.status_code == 409
    conflict_body = conflict.get_json()
    assert conflict_body["error"]["code"] == "conflict"
    assert conflict_body["error"]["field"] == "quantity"

    # unknown /api/ route -> JSON 404, not the HTML error page
    unknown_route = client.get("/api/does-not-exist")
    assert unknown_route.status_code == 404
    assert unknown_route.content_type.startswith("application/json")
    assert unknown_route.get_json()["error"]["code"] == "not_found"


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not set")
def test_concurrent_inventory_read_serializes_via_row_lock():
    """Two transactions read the same inventory row with SELECT ... FOR UPDATE,
    the same query app.py now uses before it writes. The second one must block
    until the first commits, and must then see the first transaction's write -
    never the stale value it would have seen without the lock. This is the
    exact mechanism that prevents a lost update when two stock-out requests
    for the same product arrive at close to the same time.
    """
    database_url = os.environ["TEST_DATABASE_URL"]
    init_db(database_url)
    clear_demo_data(database_url)

    with get_connection(database_url) as conn:
        cursor = conn.execute(
            "INSERT INTO products (product_code, product_name, unit) VALUES (?, ?, ?) RETURNING id",
            ("SKU-LOCK-001", "Lock Test Product", "pcs"),
        )
        product_id = cursor.fetchone()["id"]
        conn.execute(
            "INSERT INTO inventory (product_id, current_quantity, safety_stock) VALUES (?, ?, ?)",
            (product_id, 10, 0),
        )
        conn.commit()

    first_holds_lock = threading.Event()
    let_first_commit = threading.Event()
    second_thread_result = {}

    def first_transaction():
        conn = psycopg.connect(database_url, row_factory=dict_row)
        conn.execute(
            "SELECT current_quantity FROM inventory WHERE product_id = %s FOR UPDATE",
            (product_id,),
        ).fetchone()
        first_holds_lock.set()
        let_first_commit.wait(timeout=2)
        conn.execute(
            "UPDATE inventory SET current_quantity = %s WHERE product_id = %s",
            (5, product_id),
        )
        conn.commit()
        conn.close()

    def second_transaction():
        first_holds_lock.wait(timeout=2)
        conn = psycopg.connect(database_url, row_factory=dict_row)
        # Blocks here until first_transaction commits and releases the lock.
        row = conn.execute(
            "SELECT current_quantity FROM inventory WHERE product_id = %s FOR UPDATE",
            (product_id,),
        ).fetchone()
        second_thread_result["current_quantity"] = row["current_quantity"]
        conn.rollback()
        conn.close()

    t1 = threading.Thread(target=first_transaction)
    t2 = threading.Thread(target=second_transaction)
    t1.start()
    t2.start()
    # Give the second thread time to actually reach the blocking SELECT
    # before we let the first thread commit.
    first_holds_lock.wait(timeout=2)
    threading.Event().wait(0.2)
    let_first_commit.set()
    t1.join(timeout=2)
    t2.join(timeout=2)

    assert second_thread_result["current_quantity"] == 5
