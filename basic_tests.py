import os
import unittest
import csv
import tempfile

import pandas as pd

from app import create_app
from database import clear_demo_data, get_connection, init_db
from export_utils import EXPORT_HEADERS, export_inventory_csv
from order_queries import query_low_stock_products
from scripts.validate_sources import validate_source


def add_sample_product(client):
    return client.post(
        "/products/new",
        data={
            "product_code": "SKU-TEST-001",
            "product_name": "Test RS485 Module",
            "category": "Controllers",
            "brand": "Generic",
            "model": "TEST-RS485",
            "unit": "pcs",
            "cost_price": "5.50",
            "sale_price": "10.00",
            "supplier_name": "Sample Parts Store",
            "supplier_city": "Toronto",
            "usage_scene": "test record",
            "current_quantity": "5",
            "minimum_stock": "1",
            "safety_stock": "2",
            "location": "Test shelf",
        },
        follow_redirects=True,
    )


class SourceValidationTests(unittest.TestCase):
    def test_product_source_validation(self):
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

        self.assertEqual(result.total_rows, 2)
        self.assertIn("duplicate value", messages)
        self.assertIn("cannot be negative", messages)
        self.assertIn("not a valid number", messages)


class PostgresAppSmokeTests(unittest.TestCase):
    def setUp(self):
        self.database_url = os.environ.get("TEST_DATABASE_URL")
        if not self.database_url:
            self.skipTest("TEST_DATABASE_URL is not set")

        init_db(self.database_url)
        clear_demo_data(self.database_url)
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_URL": self.database_url,
                "SECRET_KEY": "test-key",
            }
        )
        self.client = self.app.test_client()

    def test_product_api_and_stock_update(self):
        response = add_sample_product(self.client)
        self.assertEqual(response.status_code, 200)

        api_health = self.client.get("/api/health")
        self.assertEqual(api_health.status_code, 200)
        self.assertEqual(api_health.get_json()["database"], "postgresql")

        with get_connection(self.database_url) as conn:
            product = conn.execute(
                "SELECT id FROM products WHERE product_code = ?",
                ("SKU-TEST-001",),
            ).fetchone()

        product_list = self.client.get("/api/products?product_code=SKU-TEST-001")
        self.assertEqual(product_list.status_code, 200)
        self.assertEqual(product_list.get_json()["total"], 1)

        stock_update = self.client.post(
            "/api/inventory/update",
            json={
                "product_id": product["id"],
                "change_type": "stock_out",
                "quantity": 2,
                "reason": "basic test",
            },
        )
        self.assertEqual(stock_update.status_code, 200)
        self.assertEqual(stock_update.get_json()["quantity_after"], 3)

        stock_update = self.client.post(
            "/api/inventory/update",
            json={
                "product_id": product["id"],
                "change_type": "stock_out",
                "quantity": 2,
                "reason": "basic test",
            },
        )
        self.assertEqual(stock_update.status_code, 200)

        low_stock_rows = query_low_stock_products(self.database_url)
        self.assertTrue(any(row["product_code"] == "SKU-TEST-001" for row in low_stock_rows))

    def test_inventory_export_headers(self):
        add_sample_product(self.client)

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = export_inventory_csv(self.database_url, output_dir=temp_dir)
            with open(csv_path, encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.reader(csv_file)
                headers = next(reader)

        self.assertEqual(headers, EXPORT_HEADERS)


if __name__ == "__main__":
    unittest.main()
