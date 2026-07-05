-- 1. Orders for one customer.
SELECT
    order_id,
    customer_id,
    order_date,
    order_status,
    total_amount
FROM orders
WHERE customer_id = 'CUS-SAMPLE-0001'
ORDER BY order_date DESC;

-- 2. Items for one order.
SELECT
    oi.item_id,
    oi.order_id,
    p.product_code,
    p.product_name,
    oi.quantity,
    oi.unit_price,
    oi.subtotal
FROM order_items oi
JOIN products p ON p.id = oi.product_id
WHERE oi.order_id = 'ORD-SAMPLE-0001'
ORDER BY oi.item_id;

-- 3. Orders linked to one product.
SELECT
    p.product_code,
    p.product_name,
    o.order_id,
    o.order_date,
    o.order_status,
    c.customer_name,
    oi.quantity,
    oi.subtotal
FROM order_items oi
JOIN products p ON p.id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE p.product_code = 'SKU-0004'
ORDER BY o.order_date DESC;

-- 4. Low-stock products.
SELECT
    p.product_code,
    p.product_name,
    p.category,
    i.current_quantity,
    i.safety_stock,
    i.location
FROM products p
JOIN inventory i ON i.product_id = p.id
WHERE i.current_quantity < i.safety_stock
ORDER BY i.current_quantity ASC;

-- 5. Inventory movement history.
SELECT
    p.product_code,
    p.product_name,
    l.change_type,
    l.quantity_change,
    l.quantity_before,
    l.quantity_after,
    l.reason,
    l.created_at
FROM inventory_logs l
JOIN products p ON p.id = l.product_id
WHERE p.product_code = 'SKU-0004'
ORDER BY l.created_at DESC;

-- 6. Order amount summary.
SELECT
    order_status,
    COUNT(*) AS order_count,
    ROUND(SUM(total_amount), 2) AS amount_total
FROM orders
GROUP BY order_status
ORDER BY amount_total DESC;
