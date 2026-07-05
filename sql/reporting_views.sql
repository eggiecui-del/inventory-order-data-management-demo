-- Simple reporting views for the PostgreSQL demo schema.

CREATE OR REPLACE VIEW vw_low_stock_products AS
SELECT
    p.product_code,
    p.product_name,
    p.category,
    p.brand,
    i.current_quantity,
    i.minimum_stock,
    i.safety_stock,
    i.location,
    CASE
        WHEN i.current_quantity <= 0 THEN 'out_of_stock'
        WHEN i.current_quantity < i.safety_stock THEN 'low_stock'
        ELSE 'normal'
    END AS inventory_status
FROM products p
JOIN inventory i ON i.product_id = p.id
WHERE i.current_quantity < i.safety_stock;

CREATE OR REPLACE VIEW vw_monthly_order_summary AS
SELECT
    DATE_TRUNC('month', o.order_date)::date AS order_month,
    COUNT(*) AS order_count,
    COUNT(DISTINCT o.customer_id) AS customer_count,
    ROUND(SUM(o.total_amount), 2) AS total_amount
FROM orders o
WHERE o.order_status <> 'cancelled'
GROUP BY DATE_TRUNC('month', o.order_date)::date;

CREATE OR REPLACE VIEW vw_customer_order_summary AS
SELECT
    c.customer_id,
    c.customer_name,
    c.city,
    COUNT(o.order_id) AS order_count,
    COALESCE(ROUND(SUM(o.total_amount), 2), 0) AS total_amount,
    MAX(o.order_date) AS last_order_date
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name, c.city;

CREATE OR REPLACE VIEW vw_product_sales_summary AS
SELECT
    p.product_code,
    p.product_name,
    p.category,
    p.brand,
    SUM(oi.quantity) AS total_quantity,
    ROUND(SUM(oi.subtotal), 2) AS total_amount,
    COUNT(DISTINCT oi.order_id) AS order_count
FROM order_items oi
JOIN products p ON p.id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status <> 'cancelled'
GROUP BY p.product_code, p.product_name, p.category, p.brand;

CREATE OR REPLACE VIEW vw_inventory_movement_summary AS
SELECT
    p.product_code,
    p.product_name,
    DATE_TRUNC('month', l.created_at)::date AS movement_month,
    SUM(CASE WHEN l.change_type = 'stock_in' THEN l.quantity_change ELSE 0 END) AS stock_in_quantity,
    SUM(CASE WHEN l.change_type = 'stock_out' THEN l.quantity_change ELSE 0 END) AS stock_out_quantity,
    COUNT(*) AS movement_count
FROM inventory_logs l
JOIN products p ON p.id = l.product_id
GROUP BY p.product_code, p.product_name, DATE_TRUNC('month', l.created_at)::date;
