# API Notes

This demo includes a few basic JSON endpoints in the existing Flask app.

The API is meant for local testing and later front-end/API practice. It does not include login, tokens, or role permissions yet.

## Error Format

Every `/api/*` endpoint returns errors in the same shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "product_id is required",
    "field": "product_id"
  }
}
```

`field` is only present when a single request field is at fault. `code` is one of:

| `code` | HTTP status | Meaning |
|---|---|---|
| `validation_error` | 400 | The request is missing a required field, has the wrong type, or an out-of-range/invalid value. |
| `not_found` | 404 | The URL points at a resource (product, order, ...) that does not exist, or the route itself does not exist. |
| `conflict` | 409 | The request is well-formed, but applying it would put the data in an invalid state (for example, a stock-out larger than current stock). |
| `internal_error` | 500 | An unexpected server error. |

Before this change, errors were a flat `{"error": "message"}` string with inconsistent status codes, and hitting an unknown `/api/...` route or triggering a server error returned an HTML page instead of JSON. Both are fixed now: every `/api/*` path always gets a JSON response, even for 404/500.

## Pagination

Endpoints that return lists (`/api/products`, `/api/customers`, `/api/orders`) accept:

- `page`: integer, defaults to `1`, values below `1` are treated as `1`.
- `page_size`: integer, defaults to `20`, clamped to the range `1`-`100`.

## Health Check

```http
GET /api/health
```

Returns basic app status. No parameters, no error cases.

## Products

```http
GET /api/products
```

Query parameters:

- `product_code`, `product_name`, `brand`, `supplier_name`: partial, case-insensitive match
- `category`: exact match
- `status`: `normal`, `low_stock`, or `out_of_stock`
- `page`, `page_size`: see Pagination above

Valid example:

```text
GET /api/products?product_name=RS485&status=normal&page=1&page_size=20
```

```json
{"items": [...], "page": 1, "page_size": 20, "total": 3}
```

Product detail:

```http
GET /api/products/<id>
```

Includes product fields, inventory fields, and recent inventory logs.

Invalid example (`id` does not exist):

```http
GET /api/products/999999
```

```json
{"error": {"code": "not_found", "message": "product not found"}}
```
Status: `404`

## Inventory

Low-stock products:

```http
GET /api/inventory/low-stock
```

Update inventory:

```http
POST /api/inventory/update
```

Valid example:

```json
{
  "product_id": 1,
  "change_type": "stock_in",
  "quantity": 10,
  "reason": "sample API test",
  "note": "local demo"
}
```

```json
{"product_id": 1, "quantity_before": 5, "quantity_after": 15, "quantity_change": 10, "change_type": "stock_in"}
```

Supported `change_type` values:

- `stock_in`
- `stock_out`
- `adjustment`

For `adjustment`, `quantity` is treated as the target quantity after adjustment.

Invalid example (missing required field):

```json
{"change_type": "stock_in", "quantity": 1}
```

```json
{"error": {"code": "validation_error", "message": "product_id is required", "field": "product_id"}}
```
Status: `400`

Invalid example (stock-out larger than current stock — this is a `409`, not a `400`, because the request itself is well-formed, it just conflicts with the current inventory state):

```json
{"product_id": 1, "change_type": "stock_out", "quantity": 99999}
```

```json
{"error": {"code": "conflict", "message": "stock_out quantity is greater than current inventory", "field": "quantity"}}
```
Status: `409`

## Customers

```http
GET /api/customers
```

Query parameters:

- `keyword`: matches customer id, name, or city
- `page`, `page_size`: see Pagination above

## Orders

```http
GET /api/orders
```

Query parameters:

- `keyword`: matches order id, customer id, or customer name
- `status`: `pending`, `processing`, `shipped`, `completed`, or `cancelled`
- `page`, `page_size`: see Pagination above

Order detail:

```http
GET /api/orders/<order_id>
```

Update order status:

```http
PATCH /api/orders/<order_id>/status
```

Valid example:

```json
{"order_status": "completed"}
```

```json
{"order_id": "ORD-SAMPLE-0001", "order_status": "completed"}
```

Invalid example (not one of the allowed statuses):

```json
{"order_status": "shipped_to_moon"}
```

```json
{"error": {"code": "validation_error", "message": "invalid order_status", "field": "order_status"}}
```
Status: `400`

## Unknown Routes

Any request to a path starting with `/api/` that does not match a route returns the same JSON error shape instead of an HTML page:

```http
GET /api/does-not-exist
```

```json
{"error": {"code": "not_found", "message": "resource not found"}}
```
Status: `404`

## Current Limits

- No authentication yet
- No API rate limit
- No OpenAPI/Swagger file yet - this document is the API reference
- No production logging or full audit tracking in the running PostgreSQL demo
