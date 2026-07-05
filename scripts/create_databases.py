import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from database import init_db


DEFAULT_ADMIN_URL = os.environ.get("POSTGRES_ADMIN_URL")


def database_exists(conn, database_name):
    row = conn.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (database_name,),
    ).fetchone()
    return row is not None


def create_database(conn, database_name):
    if database_exists(conn, database_name):
        print(f"{database_name}: already exists")
        return
    conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    print(f"{database_name}: created")


def parse_args():
    parser = argparse.ArgumentParser(description="Create local PostgreSQL demo databases.")
    parser.add_argument("--admin-url", default=DEFAULT_ADMIN_URL)
    parser.add_argument("--host", default=os.environ.get("POSTGRES_HOST", "localhost"))
    parser.add_argument("--port", default=os.environ.get("POSTGRES_PORT", "5432"))
    parser.add_argument("--user", default=os.environ.get("POSTGRES_USER", "postgres"))
    parser.add_argument("--password", default=os.environ.get("POSTGRES_PASSWORD", "postgres"))
    parser.add_argument("--maintenance-db", default=os.environ.get("POSTGRES_DB", "postgres"))
    parser.add_argument("--app-db", default="inventory_order_demo")
    parser.add_argument("--test-db", default="inventory_order_demo_test")
    parser.add_argument("--init-schema", action="store_true")
    return parser.parse_args()


def build_admin_url(args):
    if args.admin_url:
        return args.admin_url
    return psycopg.conninfo.make_conninfo(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        dbname=args.maintenance_db,
    )


def db_url_from_admin(admin_url, database_name):
    parts = psycopg.conninfo.conninfo_to_dict(admin_url)
    parts["dbname"] = database_name
    return psycopg.conninfo.make_conninfo(**parts)


def main():
    args = parse_args()
    admin_url = build_admin_url(args)
    with psycopg.connect(admin_url, autocommit=True) as conn:
        create_database(conn, args.app_db)
        create_database(conn, args.test_db)

    if args.init_schema:
        init_db(db_url_from_admin(admin_url, args.app_db))
        init_db(db_url_from_admin(admin_url, args.test_db))
        print("schemas: initialized")


if __name__ == "__main__":
    main()
