# Inventory and Order Data Management System

Personal portfolio project inspired by a small-business data workflow.

The idea is simple: product, inventory, customer, and order records are often
spread across spreadsheets. This project turns that kind of sample data into a
PostgreSQL-backed demo app with basic validation, search, API endpoints, and SQL
reporting queries.

The project uses generated sample data only. It does not include real
organization data, real customer records, real phone numbers, real addresses,
real order data, or private files.

## What This Project Shows

- A basic Flask app backed by PostgreSQL
- Product search, product creation, stock updates, inventory status, inventory logs, and CSV export
- Generated customer, order, and order item sample data
- Basic customer and order lookup pages
- PostgreSQL tables for products, suppliers, customers, orders, order items, inventory, users, and audit logs
- pandas CSV/Excel validation for source data checks
- Basic local REST API endpoints
- Simple unittest and pytest smoke tests
- ERD, data dictionary, API notes, ETL notes, and schema documentation

This is a local portfolio demo, not a production deployment.

## Stack

- Python
- Flask
- PostgreSQL
- psycopg
- pandas
- HTML / Jinja templates
- Bootstrap
- openpyxl
- SQL
- unittest
- pytest

## Project Files

```text
app.py                       Flask web app and basic REST API
database.py                  PostgreSQL schema and connection helpers
generate_mock_data.py        Generates product and inventory Excel sample data
import_excel.py              Imports generated Excel data into PostgreSQL
generate_order_data.py       Generates sample customers, orders, and order items
export_utils.py              CSV export helper
order_queries.py             Common SQL query helpers
example_sql_queries.sql      SQL query examples
basic_tests.py               Basic unittest script
test_app_pytest.py           Basic pytest smoke tests
requirements.txt             Python dependencies
templates/                   Jinja pages
static/                      CSS
sql/postgres_schema.sql      PostgreSQL schema used by the demo
sql/reporting_views.sql      Simple reporting views
scripts/validate_sources.py  pandas validation script
scripts/init_database.py     Creates PostgreSQL tables and optional reporting views
scripts/create_databases.py  Creates local app/test PostgreSQL databases
scripts/seed_demo_data.py    Generates and loads sample demo data
scripts/check_database.py    Checks connection and table row counts
docs/                        ERD, data dictionary, API, ETL, tests, and future notes
```

## Setup

Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

Create a local PostgreSQL database. One simple option:

```sql
CREATE DATABASE inventory_order_demo;
CREATE DATABASE inventory_order_demo_test;
```

Or use the helper script with an admin connection URL:

```powershell
$env:POSTGRES_PASSWORD="YOUR_PASSWORD"
py scripts/create_databases.py --init-schema
```

Set the database URL for the app:

```powershell
$env:POSTGRES_PASSWORD="YOUR_PASSWORD"
```

For tests that touch the database, also set:

```powershell
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/inventory_order_demo_test"
```

The exact username, password, host, and database name can be changed. See
`.env.example` for the expected format.

Initialize the PostgreSQL schema and reporting views:

```powershell
py scripts/init_database.py --with-views
```

Generate sample product and inventory Excel data:

```powershell
py generate_mock_data.py
```

Import the generated Excel data into PostgreSQL:

```powershell
py import_excel.py
```

Generate sample customers, orders, and order items:

```powershell
py generate_order_data.py
```

Or run the simple seed script, which does the three sample-data steps above:

```powershell
py scripts/seed_demo_data.py
```

Check the database connection and row counts:

```powershell
py scripts/check_database.py
```

Run the app:

```powershell
py app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Main Pages

- `/products`
- `/products/new`
- `/inventory/update`
- `/logs`
- `/customers`
- `/orders`
- `/export`

## Basic API

Some simple API endpoints are included for local testing:

- `GET /api/health`
- `GET /api/products`
- `GET /api/products/<id>`
- `GET /api/inventory/low-stock`
- `POST /api/inventory/update`
- `GET /api/customers`
- `GET /api/orders`
- `GET /api/orders/<order_id>`
- `PATCH /api/orders/<order_id>/status`

More details are in `docs/api.md`.

## Source Data Validation

The pandas validation script checks Excel/CSV source files before loading:

```powershell
py scripts/validate_sources.py --products data\products.xlsx --customers data\customers.csv --orders data\orders.csv --order-items data\order_items.csv
```

The script checks required columns, duplicate codes, numeric fields, date fields,
simple foreign-key references, and order item subtotal rules.

Validation output is written under `reports/`:

- `reports/validation_summary.json`
- `reports/invalid_rows.csv`
- `reports/import_log.json`

Generated report files are not meant to be committed.

## SQL Files

- `sql/postgres_schema.sql`
- `sql/reporting_views.sql`
- `example_sql_queries.sql`

These files support the PostgreSQL demo schema and simple reporting examples.

## Tests

Run the basic unittest file:

```powershell
py basic_tests.py
```

Run pytest:

```powershell
py -m pytest
```

If `TEST_DATABASE_URL` is not set, the database/API smoke tests are skipped and
the source validation tests still run.

## Generated Demo Data

The scripts generate about:

- 96 products
- 96 inventory records
- 273 inventory movement records
- 30 customers
- 60 orders
- 120 order items

Generated Excel, CSV, export files, local reports, and local logs are ignored by Git.

## Not Included

These are intentionally not included:

- Real organization data
- Login and role permissions
- Complete order-entry front end
- Cloud deployment
- Full BI dashboard
- Large QA or performance testing
