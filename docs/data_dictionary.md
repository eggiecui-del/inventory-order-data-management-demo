# Data Dictionary

This data dictionary summarizes the main fields used by the PostgreSQL demo.

## products

| Field | Purpose |
| --- | --- |
| `id` | Primary key |
| `product_code` | Unique product code |
| `product_name` | Product display name |
| `category` | Product category used for filtering |
| `brand` | Brand or generic label |
| `model` | Model or specification |
| `unit` | Unit of measure |
| `cost_price` | Purchase cost, non-negative |
| `sale_price` | Sale price, non-negative |
| `supplier_id` / `supplier_name` | Supplier reference or supplier text |
| `usage_scene` | Typical use case |
| `created_at`, `updated_at` | Record timestamps |

## suppliers

| Field | Purpose |
| --- | --- |
| `id` | Primary key |
| `supplier_code` | Unique supplier code |
| `supplier_name` | Supplier display name |
| `city` | Supplier city |
| `contact_note` | Optional contact note |

## inventory

| Field | Purpose |
| --- | --- |
| `id` | Primary key |
| `product_id` | Product foreign key |
| `current_quantity` | Current stock quantity, non-negative |
| `minimum_stock` | Minimum stock threshold |
| `safety_stock` | Low-stock threshold |
| `location` | Storage location |
| `last_updated_at` | Last stock update time |

## inventory_logs

| Field | Purpose |
| --- | --- |
| `id` | Primary key |
| `product_id` | Product foreign key |
| `change_type` | `stock_in`, `stock_out`, or `adjustment` |
| `quantity_change` | Quantity changed in this movement |
| `quantity_before` | Stock before the movement |
| `quantity_after` | Stock after the movement |
| `reason` | Movement reason |
| `reference_order_id` | Optional order reference |
| `user_id` | Optional user reference |
| `created_at` | Movement timestamp |

## customers

| Field | Purpose |
| --- | --- |
| `customer_id` | Primary key and generated sample customer code |
| `customer_name` | Customer display name |
| `contact_person` | Sample contact person |
| `phone`, `email` | Generated sample contact fields |
| `city`, `address` | Generated sample location fields |
| `created_at` | Record timestamp |

## orders

| Field | Purpose |
| --- | --- |
| `order_id` | Primary key and generated sample order code |
| `customer_id` | Customer foreign key |
| `order_date` | Order date |
| `order_status` | `pending`, `processing`, `shipped`, `completed`, or `cancelled` |
| `total_amount` | Order amount, non-negative |
| `created_at` | Record timestamp |

## order_items

| Field | Purpose |
| --- | --- |
| `item_id` | Primary key |
| `order_id` | Order foreign key |
| `product_id` | Product foreign key |
| `quantity` | Ordered quantity, greater than zero |
| `unit_price` | Unit price, non-negative |
| `subtotal` | Quantity multiplied by unit price |

## users

| Field | Purpose |
| --- | --- |
| `id` | Primary key |
| `username` | Unique login name |
| `display_name` | Display name |
| `role_name` | `admin`, `staff`, or `viewer` |
| `is_active` | Active flag |

## audit_logs

| Field | Purpose |
| --- | --- |
| `id` | Primary key |
| `user_id` | Optional user foreign key |
| `action_name` | Action label |
| `table_name` | Changed table name |
| `record_key` | Changed record key |
| `old_value`, `new_value` | Simple before/after values |
| `created_at` | Audit timestamp |
