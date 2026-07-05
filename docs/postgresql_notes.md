# PostgreSQL Notes

The local Flask app uses PostgreSQL through `psycopg`.

Database URL format:

```text
postgresql://username:password@localhost:5432/inventory_order_demo
```

The demo expects:

```text
POSTGRES_PASSWORD
DATABASE_URL, optional
TEST_DATABASE_URL
```

`POSTGRES_PASSWORD` is enough for the default local setup.
`DATABASE_URL` can be used if you want to provide the full app connection string.
`TEST_DATABASE_URL` is used by the database/API smoke tests.

## Basic Commands

Create the app and test databases:

```powershell
$env:POSTGRES_PASSWORD="YOUR_PASSWORD"
py scripts/create_databases.py --init-schema
```

Create the schema:

```powershell
py scripts/init_database.py
```

Create the schema and reporting views:

```powershell
py scripts/init_database.py --with-views
```

Clear generated demo data after creating the schema:

```powershell
py scripts/init_database.py --reset
```

Generate and load sample data:

```powershell
py scripts/seed_demo_data.py
```

Check connection and table row counts:

```powershell
py scripts/check_database.py
```

## Included Tables

- `suppliers`
- `products`
- `inventory`
- `inventory_logs`
- `customers`
- `orders`
- `order_items`
- `users`
- `audit_logs`

## Design Notes

Orders and order items:

`orders` stores order-level information. `order_items` stores product lines.
This avoids repeating customer and order data for every item.

Inventory and inventory logs:

`inventory` stores the latest stock quantity. `inventory_logs` stores each stock
movement. This makes stock changes easier to trace.

Users and audit logs:

These are included as simple design tables. Login and full audit writing are not
implemented in this demo.

## Constraints Used

- Primary keys for each table
- Unique product and optional supplier codes
- Foreign keys between customer, order, product, and inventory tables
- Check rules for non-negative price and stock fields
- Check rules for valid order status and inventory change type
- Indexes for product search, order lookup, low-stock checks, and movement history
