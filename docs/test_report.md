# Test Notes

The project has small test scripts for the local Flask and PostgreSQL demo.

Run:

```powershell
py basic_tests.py
```

Pytest smoke tests can also be run with:

```powershell
py -m pytest
```

## Covered by `basic_tests.py`

- Product creation through the Flask form
- Basic API health check
- Product list API filter by product code
- Inventory stock-out API update
- Low-stock SQL helper after a stock-out update
- CSV export header check
- Small pandas validation check for duplicate products and invalid numbers

Database/API tests use `TEST_DATABASE_URL`. If it is not set, those smoke tests
are skipped.

The database can be checked manually with:

```powershell
py scripts/check_database.py
```

## Covered by `test_app_pytest.py`

- Product API list check
- Inventory stock-out API check
- pandas source validation for duplicates, invalid numbers, and negative amounts
- Order total vs. sum of order item subtotals cross-check

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
- Concurrent inventory updates
- Full order entry workflow
- Login and permissions
- PostgreSQL installation edge cases
- Docker deployment
- Load or performance testing
