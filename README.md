# Inventory and Order Data Management System

![Tests](https://github.com/eggiecui-del/inventory-order-data-management-demo/actions/workflows/tests.yml/badge.svg)

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
- Basic local REST API endpoints with a consistent error format (see `docs/api.md`)
- Row-level locking on inventory updates to prevent lost updates under concurrent requests
- pytest suite including a real concurrency test, plus unittest smoke tests
- Structured per-request logging with a request id
- Docker Compose for local app + PostgreSQL, and GitHub Actions CI
- ERD, data dictionary, API notes, ETL notes, and schema documentation

This is a local portfolio demo, not a production deployment.

## Business Problem

Small-business product, inventory, customer, and order data often lives in
spreadsheets. That makes a few things hard: catching duplicate product codes,
knowing which products are low on stock, tracing why a quantity changed, and
answering basic reporting questions without manually combining files.

This project rebuilds that workflow as a normalized PostgreSQL schema with
validation before load, a small web/API layer for the day-to-day operations
(search, stock updates, lookups), and SQL views for the reporting questions.
It uses generated sample data, not a real business's records.

## Architecture

```text
generated sample data (Excel/CSV)
        |
        v
pandas validation (scripts/validate_sources.py)
        |
        v
PostgreSQL (sql/postgres_schema.sql)
        |
        +--> Flask pages (templates/)
        +--> REST API (app.py)
        +--> SQL reporting views (sql/reporting_views.sql)
        +--> CSV export (export_utils.py)
```

Inventory updates (`/inventory/update` and `POST /api/inventory/update`)
read the current quantity with `SELECT ... FOR UPDATE`, compute the new
quantity, reject anything that would go negative, then write the new
quantity and an `inventory_logs` row in the same transaction. The row lock
is what keeps two near-simultaneous updates to the same product from
racing on a stale quantity - see `docs/database_schema.md` for the details
and the concurrency test that checks it.

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
- Docker / Docker Compose
- GitHub Actions

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
Dockerfile                   Builds the Flask app image
docker-compose.yml           App + PostgreSQL, for local Docker use
.github/workflows/tests.yml  CI: runs pytest against a PostgreSQL service container
```

## Run With Docker Compose

```powershell
docker compose up --build
```

This starts PostgreSQL and the app together. `app` waits for `db`'s health
check to pass before it starts, so it won't try to connect before Postgres
is actually ready. Once it's up:

```text
http://localhost:5000
```

The compose file uses default local credentials (`postgres` / `postgres`)
inside its own network - that's fine for a throwaway local container, not a
real secret. The database is reachable from the host at `localhost:5433`
(mapped to 5433 instead of the usual 5432, in case something else on your
machine is already using 5432). To load sample data into the Dockerized
database, run the seed script from your host machine against that port the
same way as the non-Docker setup below.

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

## Screenshots

![Product search](screenshots/products_page.png)
![Inventory update](screenshots/inventory_update_page.png)

The API error format, from a stock-out that exceeds current inventory:

![API error format](screenshots/api_error_example.png)

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
simple foreign-key references, order item subtotal rules, and order totals
against summed item subtotals.

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

Run pytest (11 tests - product API, stock in/out/adjustment, order status
update, the unified error shape, a rejected-update-leaves-no-trace check,
the row-lock concurrency test, low-stock helper, CSV export, and source
validation):

```powershell
py -m pytest
```

If `TEST_DATABASE_URL` is not set, the database/API smoke tests are skipped and
the source validation tests still run. `basic_tests.py` and `test_app_pytest.py`
now cover mostly the same things - see `docs/test_report.md`.

GitHub Actions runs `pytest` against a PostgreSQL service container on every
push and pull request - see `.github/workflows/tests.yml`.

## Logging

The app logs one line per request (request id, method, path, status code,
response time) to stdout, and returns the same request id in an
`X-Request-ID` response header. No passwords or connection strings are
logged.

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

## Known Limitations

Things that were attempted but aren't fully solved yet:

- `basic_tests.py` and `test_app_pytest.py` cover mostly the same ground now
  (see `docs/test_report.md`) - `basic_tests.py` should probably just be
  removed.
- The database-level `CheckViolation` backstop in `app.py` isn't hit by any
  test, since the application-level check already blocks a bad stock-out
  before the database constraint would fire.
- Row locking only covers inventory updates. Order status updates and other
  writes haven't been reviewed for the same kind of race condition.
- No authentication, no rate limiting, no OpenAPI/Swagger file (`docs/api.md`
  is a hand-written reference, not a machine-readable spec).
