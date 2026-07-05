# API Notes

This demo includes a few basic JSON endpoints in the existing Flask app.

The API is meant for local testing and later front-end/API practice. It does not include login, tokens, or role permissions yet.

## Health Check

```http
GET /api/health
```

Returns basic app status.

## Products

```http
GET /api/products
```

Query parameters:

- `product_code`
- `product_name`
- `category`
- `brand`
- `supplier_name`
- `status`: `normal`, `low_stock`, or `out_of_stock`
- `page`
- `page_size`

Example:

```text
/api/products?product_name=RS485&status=normal&page=1&page_size=20
```

Product detail:

```http
GET /api/products/<id>
```

Includes product fields, inventory fields, and recent inventory logs.

## Inventory

Low-stock products:

```http
GET /api/inventory/low-stock
```

Update inventory:

```http
POST /api/inventory/update
```

Example JSON:

```json
{
  "product_id": 1,
  "change_type": "stock_in",
  "quantity": 10,
  "reason": "sample API test",
  "note": "local demo"
}
```

Supported `change_type` values:

- `stock_in`
- `stock_out`
- `adjustment`

For `adjustment`, `quantity` is treated as the target quantity after adjustment.

## Customers

```http
GET /api/customers
```

Query parameters:

- `keyword`
- `page`
- `page_size`

## Orders

```http
GET /api/orders
```

Query parameters:

- `keyword`
- `status`: `pending`, `processing`, `shipped`, `completed`, or `cancelled`
- `page`
- `page_size`

Order detail:

```http
GET /api/orders/<order_id>
```

Update order status:

```http
PATCH /api/orders/<order_id>/status
```

Example JSON:

```json
{
  "order_status": "completed"
}
```

## Current Limits

- No authentication yet
- No API rate limit
- No OpenAPI file yet
- No production logging or full audit tracking in the running PostgreSQL demo
