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
