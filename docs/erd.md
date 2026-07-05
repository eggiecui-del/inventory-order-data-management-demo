# ERD

This ERD describes the main relational design used by the PostgreSQL demo.

```mermaid
erDiagram
    suppliers ||--o{ products : supplies
    products ||--|| inventory : has
    products ||--o{ inventory_logs : moves
    products ||--o{ order_items : appears_in
    customers ||--o{ orders : places
    orders ||--o{ order_items : contains
    orders ||--o{ inventory_logs : references
    users ||--o{ inventory_logs : records
    users ||--o{ audit_logs : writes

    suppliers {
        int id PK
        string supplier_code UK
        string supplier_name
        string city
    }

    products {
        int id PK
        string product_code UK
        string product_name
        string category
        int supplier_id FK
    }

    inventory {
        int id PK
        int product_id FK
        int current_quantity
        int minimum_stock
        int safety_stock
        string location
    }

    inventory_logs {
        int id PK
        int product_id FK
        string change_type
        int quantity_change
        int quantity_before
        int quantity_after
        int reference_order_id FK
        int user_id FK
    }

    customers {
        string customer_id PK
        string customer_name
        string city
    }

    orders {
        string order_id PK
        string customer_id FK
        date order_date
        string order_status
        decimal total_amount
    }

    order_items {
        int item_id PK
        int order_id FK
        int product_id FK
        int quantity
        decimal unit_price
        decimal subtotal
    }

    users {
        int user_id PK
        string username UK
        string role_name
        bool is_active
    }

    audit_logs {
        int audit_id PK
        int user_id FK
        string action_name
        string table_name
        string record_key
    }
```

## Notes

- `orders` and `order_items` are separated because one order can contain many products.
- `inventory` stores the current quantity, while `inventory_logs` stores the movement history.
- `users` and `audit_logs` are included as basic design tables. The current demo does not include a login screen.
