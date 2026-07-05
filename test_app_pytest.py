import os

import pandas as pd
import pytest

from app import create_app
from database import clear_demo_data, get_connection, init_db
from scripts.validate_sources import validate_source


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
