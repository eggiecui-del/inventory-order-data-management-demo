import argparse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from database import DATABASE_URL, clear_demo_data, get_connection, init_db


REPORTING_SQL = ROOT_DIR / "sql" / "reporting_views.sql"


def apply_sql_file(database_url, sql_path):
    sql_text = Path(sql_path).read_text(encoding="utf-8")
    with get_connection(database_url) as conn:
        for statement in sql_text.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(statement)
        conn.commit()


def parse_args():
    parser = argparse.ArgumentParser(description="Initialize the PostgreSQL demo schema.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", DATABASE_URL))
    parser.add_argument("--reset", action="store_true", help="Clear demo data after schema creation")
    parser.add_argument("--with-views", action="store_true", help="Create reporting views")
    return parser.parse_args()


def main():
    args = parse_args()
    init_db(args.database_url)

    if args.reset:
        clear_demo_data(args.database_url)

    if args.with_views:
        apply_sql_file(args.database_url, REPORTING_SQL)

    print("database initialized")
    print("schema: ok")
    print(f"views: {'ok' if args.with_views else 'skipped'}")
    print(f"reset: {'yes' if args.reset else 'no'}")


if __name__ == "__main__":
    main()
