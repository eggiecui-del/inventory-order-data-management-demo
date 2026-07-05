from datetime import datetime
from pathlib import Path
import csv

from database import DATABASE_URL, get_connection


BASE_DIR = Path(__file__).resolve().parent
EXPORT_DIR = BASE_DIR / "exports"


EXPORT_HEADERS = [
    "product_code",
    "product_name",
    "category",
    "brand",
    "model",
    "current_quantity",
    "minimum_stock",
    "safety_stock",
    "inventory_status",
    "location",
    "last_updated_at",
]


def fetch_inventory_rows(database_url=DATABASE_URL):
    with get_connection(database_url) as conn:
        return conn.execute(
            """
            SELECT
                p.product_code,
                p.product_name,
                p.category,
                p.brand,
                p.model,
                COALESCE(i.current_quantity, 0) AS current_quantity,
                COALESCE(i.minimum_stock, 0) AS minimum_stock,
                COALESCE(i.safety_stock, 0) AS safety_stock,
                CASE
                    WHEN COALESCE(i.current_quantity, 0) <= 0 THEN 'out_of_stock'
                    WHEN COALESCE(i.current_quantity, 0) < COALESCE(i.safety_stock, 0) THEN 'low_stock'
                    ELSE 'normal'
                END AS inventory_status,
                COALESCE(i.location, '') AS location,
                COALESCE(TO_CHAR(i.last_updated_at, 'YYYY-MM-DD HH24:MI:SS'), '') AS last_updated_at
            FROM products p
            LEFT JOIN inventory i ON i.product_id = p.id
            ORDER BY p.product_code
            """
        ).fetchall()


def export_inventory_csv(db_path=DATABASE_URL, output_dir=EXPORT_DIR):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"product_inventory_export_{timestamp}.csv"
    rows = fetch_inventory_rows(db_path)

    with output_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(EXPORT_HEADERS)
        for row in rows:
            writer.writerow(
                [
                    row["product_code"],
                    row["product_name"],
                    row["category"],
                    row["brand"],
                    row["model"],
                    row["current_quantity"],
                    row["minimum_stock"],
                    row["safety_stock"],
                    row["inventory_status"],
                    row["location"],
                    row["last_updated_at"],
                ]
            )

    return output_path
