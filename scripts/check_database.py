import argparse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from database import DATABASE_URL, get_connection


TABLES = [
    "suppliers",
    "products",
    "inventory",
    "inventory_logs",
    "customers",
    "orders",
    "order_items",
    "users",
    "audit_logs",
]

VIEWS = [
    "vw_low_stock_products",
    "vw_monthly_order_summary",
    "vw_customer_order_summary",
    "vw_product_sales_summary",
    "vw_inventory_movement_summary",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Check the PostgreSQL demo database.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", DATABASE_URL))
    return parser.parse_args()


def main():
    args = parse_args()
    with get_connection(args.database_url) as conn:
        version = conn.execute("SELECT version() AS version").fetchone()["version"]
        print("connection: ok")
        print(version.split(",")[0])

        for table_name in TABLES:
            row = conn.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()
            print(f"{table_name}: {row['total']}")

        for view_name in VIEWS:
            row = conn.execute(
                """
                SELECT 1 AS exists
                FROM information_schema.views
                WHERE table_schema = 'public' AND table_name = ?
                """,
                (view_name,),
            ).fetchone()
            print(f"{view_name}: {'ok' if row else 'missing'}")


if __name__ == "__main__":
    main()
