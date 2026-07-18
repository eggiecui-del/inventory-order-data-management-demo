# ETL Validation Notes

The demo includes a small pandas script for checking source files before they are loaded into the database.

Script:

```text
scripts/validate_sources.py
```

## Why This Exists

The original data source is assumed to be Excel or CSV files. Before loading files into the database, the script checks common problems that would cause bad database records.

This is not a full ETL platform. It is a local validation step for a small demo data app.

## Example Command

```powershell
py scripts/validate_sources.py --products data\products.xlsx --customers data\customers.csv --orders data\orders.csv --order-items data\order_items.csv
```

Inventory can also be checked:

```powershell
py scripts/validate_sources.py --products data\products.xlsx --inventory data\inventory.xlsx
```

## Supported Files

- `.xlsx`
- `.xls`
- `.csv`

Source files should use the normalized English column names used by the demo
database and sample data scripts. For example:

- `product_code`
- `product_name`
- `cost_price`
- `sale_price`
- `current_quantity`
- `order_id`
- `customer_id`

## Checks

Products:

- Required fields: product code, product name, unit, cost price, sale price
- Duplicate product code
- Price fields must be valid numbers and cannot be negative

Inventory:

- Required fields: product code, current quantity
- Current quantity, minimum stock, and safety stock cannot be negative
- Product code should exist in the product source file if both files are provided

Customers:

- Required fields: customer id, customer name
- Duplicate customer id

Orders:

- Required fields: order id, customer id, order date, order status, total amount
- Duplicate order id
- Total amount cannot be negative
- Order date must be a valid date
- Customer id should exist in the customer source file if both files are provided
- Total amount should match the sum of the order's item subtotals if the order items file is also provided

Order items:

- Required fields: order id, product code, quantity, unit price, subtotal
- Quantity must be greater than zero
- Unit price and subtotal cannot be negative
- Subtotal should match quantity multiplied by unit price
- Order id and product code should exist if the related source files are provided

## Output

The script writes:

```text
reports/validation_summary.json
reports/invalid_rows.csv
reports/import_log.json
```

These output files are local reports. They are not meant to be committed to GitHub.

`import_log.json` records the run timestamp, source count, total/valid/invalid row counts, error count, and output file names. It is a small local log for checking what happened during a validation run.
