# Test Notes

The project has small test scripts for the local Flask and PostgreSQL demo.

Run:

```powershell
py -m pytest
```

`basic_tests.py` can still be run directly with `py basic_tests.py`, but see
the note below - it overlaps with `test_app_pytest.py` now.

Database/API tests use `TEST_DATABASE_URL`. If it is not set, those tests are
skipped, not silently counted as passing - `pytest -v` shows each one as
`SKIPPED (TEST_DATABASE_URL is not set)`. Only the pure pandas validation
tests run without a database.

The database can be checked manually with:

```powershell
py scripts/check_database.py
```

## Covered by `test_app_pytest.py` (11 tests)

Pandas source validation, no database needed:

- Duplicate product code, negative price, invalid number
- Order total vs. sum of order-item subtotals mismatch

Flask + PostgreSQL, needs `TEST_DATABASE_URL`:

- Product creation through the form, then found via `/api/products`
- Inventory `stock_out` through `/api/inventory/update`
- Inventory `stock_in` (quantity increases, before/after/change all checked)
- Inventory `adjustment` (quantity is treated as the target, not a delta)
- Unified API error shape: missing required field, resource not found,
  stock-out conflict (409), unknown `/api/...` route returns JSON not HTML
- A rejected inventory update (409) leaves the row and the log table
  completely unchanged - proves the failure did not partially write anything
- Concurrent inventory reads: two direct database connections with
  controlled timing prove `SELECT ... FOR UPDATE` makes the second
  transaction wait for the first to commit, instead of both working from a
  stale quantity
- Order status update through `/api/orders/<id>/status`: a valid
  transition, an invalid status value, and a missing order id
- Low-stock helper (`query_low_stock_products`) after two stock-outs cross
  the safety-stock threshold
- CSV export header check

## `basic_tests.py` vs `test_app_pytest.py`

These two now test mostly the same things (product validation, stock_out,
CSV export, low-stock helper). TODO: delete `basic_tests.py` and just use
pytest.

## ETL Validation Script

`scripts/validate_sources.py` is a separate data validation script. It checks source files before loading them into the database.

It covers:

- Required columns
- Required values
- Duplicate product, customer, and order codes
- Numeric conversion for prices and quantities
- Date conversion for order dates
- Non-negative amount checks
- Positive quantity checks
- Simple foreign-key checks across source files
- Order item subtotal check
- Order total vs. sum of order item subtotals check

## Current Demo Data

The generated sample data contains about:

- 96 products
- 96 inventory records
- 273 inventory transaction records
- 30 customers
- 60 orders
- 120 order items

## Not Covered Yet

- Browser compatibility testing
- Full order entry workflow (orders are only created through generated
  sample data and direct SQL in tests, not a web form)
- Login and permissions
- PostgreSQL installation edge cases
- Docker deployment
- Load or performance testing
- `CheckViolation` handling in `app.py` isn't hit by any test - the
  app-level check blocks a bad stock_out before the DB constraint would.
