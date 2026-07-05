from database import DATABASE_URL, get_connection


def query_customer_orders(customer_id, db_path=DATABASE_URL):
    with get_connection(db_path) as conn:
        return conn.execute(
            """
            SELECT order_id, customer_id, order_date, order_status, total_amount
            FROM orders
            WHERE customer_id = ?
            ORDER BY order_date DESC, order_id DESC
            """,
            (customer_id,),
        ).fetchall()


def query_order_items(order_id, db_path=DATABASE_URL):
    with get_connection(db_path) as conn:
        return conn.execute(
            """
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
            WHERE oi.order_id = ?
            ORDER BY oi.item_id
            """,
            (order_id,),
        ).fetchall()


def query_product_orders(product_code, db_path=DATABASE_URL):
    with get_connection(db_path) as conn:
        return conn.execute(
            """
            SELECT
                o.order_id,
                o.order_date,
                o.order_status,
                c.customer_name,
                oi.quantity,
                oi.unit_price,
                oi.subtotal
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            JOIN customers c ON c.customer_id = o.customer_id
            JOIN products p ON p.id = oi.product_id
            WHERE p.product_code = ?
            ORDER BY o.order_date DESC, o.order_id DESC
            """,
            (product_code,),
        ).fetchall()


def query_low_stock_products(db_path=DATABASE_URL):
    with get_connection(db_path) as conn:
        return conn.execute(
            """
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
            ORDER BY i.current_quantity ASC, p.product_code
            """
        ).fetchall()


def query_inventory_history(product_code, db_path=DATABASE_URL):
    with get_connection(db_path) as conn:
        return conn.execute(
            """
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
            WHERE p.product_code = ?
            ORDER BY l.created_at DESC, l.id DESC
            """,
            (product_code,),
        ).fetchall()


def query_order_amount_summary(db_path=DATABASE_URL):
    with get_connection(db_path) as conn:
        return conn.execute(
            """
            SELECT
                order_status,
                COUNT(*) AS order_count,
                ROUND(SUM(total_amount), 2) AS amount_total
            FROM orders
            GROUP BY order_status
            ORDER BY amount_total DESC
            """
        ).fetchall()
