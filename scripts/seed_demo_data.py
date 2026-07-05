import argparse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from database import DATABASE_URL
from generate_mock_data import generate_mock_data
from generate_order_data import generate_order_data
from import_excel import import_workbook


def parse_args():
    parser = argparse.ArgumentParser(description="Generate and load sample demo data.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", DATABASE_URL))
    return parser.parse_args()


def main():
    args = parse_args()

    excel_result = generate_mock_data()
    import_result = import_workbook(database_url=args.database_url, reset=True)
    order_result = generate_order_data(database_url=args.database_url, reset=True)

    print("sample data loaded")
    print(f"excel file: {excel_result['output_path'].name}")
    print(f"products: {import_result['products']}")
    print(f"inventory: {import_result['inventory']}")
    print(f"inventory_logs: {import_result['inventory_logs']}")
    print(f"customers: {order_result['customers']}")
    print(f"orders: {order_result['orders']}")
    print(f"order_items: {order_result['order_items']}")


if __name__ == "__main__":
    main()
