# Database Schema Notes

The demo uses PostgreSQL as the application database.

Related docs:

- `docs/erd.md`
- `docs/data_dictionary.md`
- `sql/postgres_schema.sql`
- `sql/reporting_views.sql`

## Main Tables

### suppliers

Stores supplier reference data. The current UI still accepts simple supplier
text on the product form, but the database includes a supplier table for a more
structured model.

### products

Stores product master data.

Main fields:

- `id`
- `product_code`
- `product_name`
- `category`
- `brand`
- `model`
- `unit`
- `cost_price`
- `sale_price`
- `supplier_id`
- `supplier_name`
- `supplier_city`
- `usage_scene`
- `remark`
- `created_at`
- `updated_at`

`supplier_name` and `supplier_city` are plain text and are the fields the
Flask product form reads and writes. `supplier_id` references the `suppliers`
table and is populated during Excel import: `import_excel.py` upserts a row
in `suppliers` and stores its id alongside the free-text columns. The Flask
app itself never sets or reads `supplier_id` when creating or editing
products through the web form, so it stays `NULL` for anything added or
edited that way, while imported products keep it populated. A follow-up
would be to move the product form onto `supplier_id` (picking an existing
supplier row) and drop the free-text columns.

Rules:

- `product_code` is unique.
- `product_code`, `product_name`, and `unit` are required.
- Price fields cannot be negative.

### inventory

Stores current stock for each product.

Main fields:

- `id`
- `product_id`
- `current_quantity`
- `location`
- `minimum_stock`
- `safety_stock`
- `last_updated_at`
- `remark`

Rules:

- One product has one inventory row.
- Current quantity cannot be negative.
- Inventory status is calculated from `current_quantity` and `safety_stock`.

Status logic:

```text
current_quantity <= 0           out_of_stock
current_quantity < safety_stock low_stock
otherwise                       normal
```

### inventory_logs

Stores stock movement history.

Main fields:

- `id`
- `product_id`
- `change_type`
- `quantity_change`
- `quantity_before`
- `quantity_after`
- `reason`
- `reference_order_id`
- `user_id`
- `note`
- `created_at`

When inventory is updated, the app updates the current stock and inserts a
movement row. This keeps a simple history of stock-in, stock-out, and adjustment
events.

### customers

Stores generated customer records.

Main fields:

- `customer_id`
- `customer_name`
- `contact_person`
- `phone`
- `email`
- `city`
- `address`
- `created_at`
- `notes`

### orders

Stores generated order header records.

Main fields:

- `order_id`
- `customer_id`
- `order_date`
- `order_status`
- `total_amount`
- `created_at`
- `notes`

### order_items

Stores generated order line records.

Main fields:

- `item_id`
- `order_id`
- `product_id`
- `quantity`
- `unit_price`
- `subtotal`

### users

Included as a basic table for role names and future user tracking. The current
demo does not include login screens.

### audit_logs

Included as a simple audit table design. The current demo does not yet write
full audit records.

## Relationships

```text
suppliers 1 --- N products
products 1 --- 1 inventory
products 1 --- N inventory_logs
customers 1 --- N orders
orders 1 --- N order_items
products 1 --- N order_items
users 1 --- N inventory_logs
users 1 --- N audit_logs
```

`orders` and `order_items` are separated because one order can contain more than
one product. If they were kept in one big table, customer and order data would
repeat on every product line.

`inventory` and `inventory_logs` are separated because the current quantity only
shows the latest state. The log table shows how the quantity changed.

## Reporting Views

The reporting views are in `sql/reporting_views.sql`.

Views included:

- `vw_low_stock_products`
- `vw_monthly_order_summary`
- `vw_customer_order_summary`
- `vw_product_sales_summary`
- `vw_inventory_movement_summary`

These are simple SQL views for reporting practice. They are not a full data
warehouse.

## Concurrency and Data Integrity

Inventory updates follow a read-check-write pattern: read the current
quantity, compute the new quantity, reject if it would go negative, then
write. Without extra care, two requests updating the *same* product at
close to the same time can both read the same "before" quantity, both pass
the negative-stock check independently, and the second write can silently
overwrite the first (a lost update), even though the database's
`CHECK (current_quantity >= 0)` constraint still guarantees no row ever
stores a negative number.

The fix is `SELECT ... FOR UPDATE` when reading the inventory row inside the
update transaction. This makes a second concurrent request wait until the
first request's transaction commits or rolls back before it can read the
row, so it always computes the new quantity from the true current value
instead of a stale one. This is why the app relies on both application
checks and database constraints, and not just one or the other:

- The `FOR UPDATE` lock plus the check inside the transaction prevents the
  lost-update race in the first place.
- The `CHECK (current_quantity >= 0)` constraint is the backstop: if any
  code path ever skips the application check, the database still refuses to
  store an invalid row.

A concurrency test covering this is in `test_app_pytest.py` -
`test_concurrent_stock_out_serializes_via_row_lock`.

## Query Performance Notes (EXPLAIN ANALYZE)

Checked against a seeded table of 2,000 products / inventory rows:

- Exact match (`WHERE product_code = 'SKU-500'`) uses `idx_products_code`:
  `Index Scan`, ~0.02ms.
- Fuzzy search (`WHERE product_name ILIKE '%Product 1%'`) does **not** use
  `idx_products_name`: a plain B-tree index can only accelerate lookups that
  start with a known prefix, not a pattern with a leading wildcard, so
  Postgres falls back to `Seq Scan`. At the current data size this is still
  well under a millisecond, so it is left as-is; if product search needed to
  scale further, the real fix is a trigram index (`pg_trgm` extension +
  `GIN` index), not a plain B-tree.
- The low-stock query (`WHERE current_quantity < safety_stock`) also does
  **not** use `idx_inventory_status`, and structurally never will: that
  index is built on `(current_quantity, safety_stock)` as two independent
  columns, but a B-tree index can only accelerate comparisons against a
  constant, not a comparison between two columns of the same row. The index
  currently does nothing useful for this query. At the current row count
  the sequential scan is still fast (well under a millisecond), so this is
  noted as a known limitation rather than "fixed" - a real fix would need a
  generated/computed column (e.g. a trigger-maintained `is_low_stock`
  boolean) with its own index, which is more machinery than this project's
  scale currently justifies.
