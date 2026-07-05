from datetime import date, datetime
from decimal import Decimal
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, url_for

from database import DATABASE_URL, get_connection, init_db
from export_utils import export_inventory_csv


ORDER_STATUSES = ["pending", "processing", "shipped", "completed", "cancelled"]
INVENTORY_CHANGE_TYPES = {"stock_in", "stock_out", "adjustment"}


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def as_text(value):
    return (value or "").strip()


def as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_nonnegative_float(value, label):
    text = as_text(value)
    if not text:
        return 0.0, None
    try:
        number = float(text)
    except ValueError:
        return 0.0, f"{label} must be a valid number"
    if number < 0:
        return number, f"{label} cannot be negative"
    return number, None


def parse_nonnegative_int(value, label):
    text = as_text(value)
    if not text:
        return 0, None
    try:
        number = int(text)
    except ValueError:
        return 0, f"{label} must be a valid integer"
    if number < 0:
        return number, f"{label} cannot be negative"
    return number, None


def row_to_dict(row):
    data = {}
    for key in row.keys():
        value = row[key]
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, (datetime, date)):
            value = value.isoformat()
        data[key] = value
    return data


def json_error(message, status_code=400):
    return jsonify({"error": message}), status_code


def safe_page_args():
    page = max(as_int(request.args.get("page"), 1), 1)
    page_size = as_int(request.args.get("page_size"), 20)
    page_size = min(max(page_size, 1), 100)
    return page, page_size, (page - 1) * page_size


def status_case_sql(alias="i"):
    return f"""
        CASE
            WHEN COALESCE({alias}.current_quantity, 0) <= 0 THEN 'out_of_stock'
            WHEN COALESCE({alias}.current_quantity, 0) < COALESCE({alias}.safety_stock, 0) THEN 'low_stock'
            ELSE 'normal'
        END
    """


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="inventory-demo-dev-key",
        DATABASE_URL=DATABASE_URL,
    )
    if test_config:
        app.config.update(test_config)

    init_db(app.config["DATABASE_URL"])

    def db_path():
        return app.config["DATABASE_URL"]

    def fetch_categories():
        with get_connection(db_path()) as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM products WHERE category <> '' ORDER BY category"
            ).fetchall()
        return [row["category"] for row in rows]

    def fetch_products_for_select():
        with get_connection(db_path()) as conn:
            return conn.execute(
                """
                SELECT
                    p.id,
                    p.product_code,
                    p.product_name,
                    COALESCE(i.current_quantity, 0) AS current_quantity
                FROM products p
                LEFT JOIN inventory i ON i.product_id = p.id
                ORDER BY p.product_code
                """
            ).fetchall()

    @app.route("/")
    def index():
        return redirect(url_for("product_list"))

    @app.route("/products")
    def product_list():
        product_code = as_text(request.args.get("product_code"))
        product_name = as_text(request.args.get("product_name"))
        category = as_text(request.args.get("category"))
        brand = as_text(request.args.get("brand"))
        supplier_name = as_text(request.args.get("supplier_name"))
        inventory_status = as_text(request.args.get("inventory_status"))
        low_stock = request.args.get("low_stock") == "1"

        conditions = []
        params = []
        if product_code:
            conditions.append("p.product_code ILIKE ?")
            params.append(f"%{product_code}%")
        if product_name:
            conditions.append("p.product_name ILIKE ?")
            params.append(f"%{product_name}%")
        if category:
            conditions.append("p.category = ?")
            params.append(category)
        if brand:
            conditions.append("p.brand ILIKE ?")
            params.append(f"%{brand}%")
        if supplier_name:
            conditions.append("p.supplier_name ILIKE ?")
            params.append(f"%{supplier_name}%")
        if low_stock:
            conditions.append("COALESCE(i.current_quantity, 0) < COALESCE(i.safety_stock, 0)")
        if inventory_status == "out_of_stock":
            conditions.append("COALESCE(i.current_quantity, 0) <= 0")
        elif inventory_status == "low_stock":
            conditions.append("COALESCE(i.current_quantity, 0) > 0 AND COALESCE(i.current_quantity, 0) < COALESCE(i.safety_stock, 0)")
        elif inventory_status == "normal":
            conditions.append("COALESCE(i.current_quantity, 0) >= COALESCE(i.safety_stock, 0)")

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with get_connection(db_path()) as conn:
            products = conn.execute(
                f"""
                SELECT
                    p.id,
                    p.product_code,
                    p.product_name,
                    p.category,
                    p.brand,
                    p.supplier_name,
                    p.model,
                    p.unit,
                    COALESCE(i.current_quantity, 0) AS current_quantity,
                    COALESCE(i.minimum_stock, 0) AS minimum_stock,
                    COALESCE(i.location, '') AS location,
                    COALESCE(i.safety_stock, 0) AS safety_stock,
                    {status_case_sql("i")} AS inventory_status
                FROM products p
                LEFT JOIN inventory i ON i.product_id = p.id
                {where_sql}
                ORDER BY p.product_code
                """,
                params,
            ).fetchall()

        return render_template(
            "products.html",
            products=products,
            categories=fetch_categories(),
            filters={
                "product_code": product_code,
                "product_name": product_name,
                "category": category,
                "brand": brand,
                "supplier_name": supplier_name,
                "inventory_status": inventory_status,
                "low_stock": low_stock,
            },
        )

    @app.route("/products/new", methods=["GET", "POST"])
    def product_new():
        form = request.form
        if request.method == "POST":
            product_code = as_text(form.get("product_code"))
            product_name = as_text(form.get("product_name"))
            unit = as_text(form.get("unit"))
            errors = []

            if not product_code:
                errors.append("Product code is required")
            if not product_name:
                errors.append("Product name is required")
            if not unit:
                errors.append("Unit is required")

            cost_price, error = parse_nonnegative_float(form.get("cost_price"), "Cost price")
            if error:
                errors.append(error)
            sale_price, error = parse_nonnegative_float(form.get("sale_price"), "Sale price")
            if error:
                errors.append(error)
            current_quantity, error = parse_nonnegative_int(form.get("current_quantity"), "Initial stock")
            if error:
                errors.append(error)
            minimum_stock, error = parse_nonnegative_int(form.get("minimum_stock"), "Minimum stock")
            if error:
                errors.append(error)
            safety_stock, error = parse_nonnegative_int(form.get("safety_stock"), "Safety stock")
            if error:
                errors.append(error)
            if safety_stock and minimum_stock > safety_stock:
                errors.append("Minimum stock cannot be higher than safety stock")

            with get_connection(db_path()) as conn:
                duplicate = conn.execute(
                    "SELECT id FROM products WHERE product_code = ?",
                    (product_code,),
                ).fetchone()
                if duplicate:
                    errors.append("Product code already exists")

                if errors:
                    for error in errors:
                        flash(error, "danger")
                    return render_template("product_form.html", form=form)

                timestamp = now_text()
                cursor = conn.execute(
                    """
                    INSERT INTO products (
                        product_code, product_name, category, brand, model, unit,
                        cost_price, sale_price, supplier_name, supplier_city,
                        usage_scene, remark, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING id
                    """,
                    (
                        product_code,
                        product_name,
                        as_text(form.get("category")),
                        as_text(form.get("brand")),
                        as_text(form.get("model")),
                        unit,
                        cost_price,
                        sale_price,
                        as_text(form.get("supplier_name")),
                        as_text(form.get("supplier_city")),
                        as_text(form.get("usage_scene")),
                        as_text(form.get("remark")),
                        timestamp,
                        timestamp,
                    ),
                )
                product_id = cursor.fetchone()["id"]
                conn.execute(
                    """
                    INSERT INTO inventory (
                        product_id, current_quantity, location, minimum_stock, safety_stock,
                        last_updated_at, remark
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product_id,
                        current_quantity,
                        as_text(form.get("location")) or "Main storage shelf",
                        minimum_stock,
                        safety_stock,
                        timestamp,
                        "Inventory row created with new product",
                    ),
                )
                conn.commit()

            flash("Product was created and an inventory row was added", "success")
            return redirect(url_for("product_detail", product_id=product_id))

        return render_template("product_form.html", form={})

    @app.route("/products/<int:product_id>")
    def product_detail(product_id):
        with get_connection(db_path()) as conn:
            product = conn.execute(
                f"""
                SELECT
                    p.*,
                    COALESCE(i.current_quantity, 0) AS current_quantity,
                    COALESCE(i.location, '') AS location,
                    COALESCE(i.minimum_stock, 0) AS minimum_stock,
                    COALESCE(i.safety_stock, 0) AS safety_stock,
                    COALESCE(TO_CHAR(i.last_updated_at, 'YYYY-MM-DD HH24:MI:SS'), '') AS last_updated_at,
                    COALESCE(i.remark, '') AS inventory_remark,
                    {status_case_sql("i")} AS inventory_status
                FROM products p
                LEFT JOIN inventory i ON i.product_id = p.id
                WHERE p.id = ?
                """,
                (product_id,),
            ).fetchone()
            if not product:
                return render_template("error.html", message="Product not found"), 404
            logs = conn.execute(
                """
                SELECT change_type, quantity_change, quantity_before, quantity_after,
                       reason, note, created_at
                FROM inventory_logs
                WHERE product_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 20
                """,
                (product_id,),
            ).fetchall()
        return render_template("product_detail.html", product=product, logs=logs)

    @app.route("/inventory/update", methods=["GET", "POST"])
    def inventory_update():
        selected_product_id = as_int(request.args.get("product_id") or request.form.get("product_id"))

        if request.method == "POST":
            product_id = as_int(request.form.get("product_id"))
            change_type = as_text(request.form.get("change_type"))
            quantity_input = as_int(request.form.get("quantity"), -1)
            reason = as_text(request.form.get("reason"))
            note = as_text(request.form.get("note"))
            errors = []

            if product_id <= 0:
                errors.append("Please choose a product")
            if change_type not in INVENTORY_CHANGE_TYPES:
                errors.append("Please choose a valid inventory change type")
            if quantity_input < 0:
                errors.append("Quantity cannot be negative")

            with get_connection(db_path()) as conn:
                product = conn.execute(
                    "SELECT id, product_code, product_name FROM products WHERE id = ?",
                    (product_id,),
                ).fetchone()
                inventory = conn.execute(
                    "SELECT * FROM inventory WHERE product_id = ?",
                    (product_id,),
                ).fetchone()

                if not product:
                    errors.append("Product not found")

                if errors:
                    for error in errors:
                        flash(error, "danger")
                    return render_template(
                        "inventory_update.html",
                        products=fetch_products_for_select(),
                        selected_product_id=product_id,
                    )

                timestamp = now_text()
                if not inventory:
                    conn.execute(
                        """
                        INSERT INTO inventory (
                            product_id, current_quantity, location, minimum_stock, safety_stock,
                            last_updated_at, remark
                        ) VALUES (?, 0, ?, 0, 0, ?, ?)
                        """,
                        (product_id, "Main storage shelf", timestamp, "Created during inventory update"),
                    )
                    inventory = conn.execute(
                        "SELECT * FROM inventory WHERE product_id = ?",
                        (product_id,),
                    ).fetchone()

                before_quantity = inventory["current_quantity"]
                if change_type == "stock_in":
                    if quantity_input <= 0:
                        flash("Stock-in quantity must be greater than zero", "danger")
                        return render_template(
                            "inventory_update.html",
                            products=fetch_products_for_select(),
                            selected_product_id=product_id,
                        )
                    quantity_change = quantity_input
                    after_quantity = before_quantity + quantity_change
                elif change_type == "stock_out":
                    if quantity_input <= 0:
                        flash("Stock-out quantity must be greater than zero", "danger")
                        return render_template(
                            "inventory_update.html",
                            products=fetch_products_for_select(),
                            selected_product_id=product_id,
                        )
                    quantity_change = quantity_input
                    after_quantity = before_quantity - quantity_change
                    if after_quantity < 0:
                        flash("Stock-out quantity is greater than current inventory", "danger")
                        return render_template(
                            "inventory_update.html",
                            products=fetch_products_for_select(),
                            selected_product_id=product_id,
                        )
                else:
                    after_quantity = quantity_input
                    quantity_change = after_quantity - before_quantity

                conn.execute(
                    """
                    UPDATE inventory
                    SET current_quantity = ?, last_updated_at = ?
                    WHERE product_id = ?
                    """,
                    (after_quantity, timestamp, product_id),
                )
                conn.execute(
                    """
                    INSERT INTO inventory_logs (
                        product_id, change_type, quantity_change, quantity_before,
                        quantity_after, reason, note, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product_id,
                        change_type,
                        quantity_change,
                        before_quantity,
                        after_quantity,
                        reason,
                        note,
                        timestamp,
                    ),
                )
                conn.commit()

            flash("Inventory was updated and a movement log was saved", "success")
            return redirect(url_for("product_detail", product_id=product_id))

        return render_template(
            "inventory_update.html",
            products=fetch_products_for_select(),
            selected_product_id=selected_product_id,
        )

    @app.route("/logs")
    def inventory_logs():
        keyword = as_text(request.args.get("keyword"))
        conditions = []
        params = []
        if keyword:
            conditions.append("(p.product_code ILIKE ? OR p.product_name ILIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with get_connection(db_path()) as conn:
            logs = conn.execute(
                f"""
                SELECT
                    l.id,
                    p.product_code,
                    p.product_name,
                    l.change_type,
                    l.quantity_change,
                    l.quantity_before,
                    l.quantity_after,
                    l.reason,
                    l.note,
                    l.created_at
                FROM inventory_logs l
                JOIN products p ON p.id = l.product_id
                {where_sql}
                ORDER BY l.created_at DESC, l.id DESC
                LIMIT 300
                """,
                params,
            ).fetchall()

        return render_template("logs.html", logs=logs, keyword=keyword)

    @app.route("/customers")
    def customers():
        keyword = as_text(request.args.get("keyword"))
        conditions = []
        params = []
        if keyword:
            conditions.append(
                "(c.customer_id ILIKE ? OR c.customer_name ILIKE ? OR c.city ILIKE ?)"
            )
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with get_connection(db_path()) as conn:
            customer_rows = conn.execute(
                f"""
                SELECT
                    c.customer_id,
                    c.customer_name,
                    c.contact_person,
                    c.phone,
                    c.email,
                    c.city,
                    COUNT(o.order_id) AS order_count,
                    COALESCE(SUM(o.total_amount), 0) AS order_amount
                FROM customers c
                LEFT JOIN orders o ON o.customer_id = c.customer_id
                {where_sql}
                GROUP BY
                    c.customer_id,
                    c.customer_name,
                    c.contact_person,
                    c.phone,
                    c.email,
                    c.city
                ORDER BY c.customer_id
                """,
                params,
            ).fetchall()

        return render_template("customers.html", customers=customer_rows, keyword=keyword)

    @app.route("/orders")
    def orders():
        keyword = as_text(request.args.get("keyword"))
        status = as_text(request.args.get("status"))
        conditions = []
        params = []
        if keyword:
            conditions.append(
                "(o.order_id ILIKE ? OR c.customer_id ILIKE ? OR c.customer_name ILIKE ?)"
            )
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if status:
            conditions.append("o.order_status = ?")
            params.append(status)
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with get_connection(db_path()) as conn:
            order_rows = conn.execute(
                f"""
                SELECT
                    o.order_id,
                    o.customer_id,
                    c.customer_name,
                    o.order_date,
                    o.order_status,
                    o.total_amount,
                    COUNT(oi.item_id) AS item_count,
                    o.notes
                FROM orders o
                JOIN customers c ON c.customer_id = o.customer_id
                LEFT JOIN order_items oi ON oi.order_id = o.order_id
                {where_sql}
                GROUP BY
                    o.order_id,
                    o.customer_id,
                    c.customer_name,
                    o.order_date,
                    o.order_status,
                    o.total_amount,
                    o.notes
                ORDER BY o.order_date DESC, o.order_id DESC
                LIMIT 200
                """,
                params,
            ).fetchall()

        return render_template(
            "orders.html",
            orders=order_rows,
            keyword=keyword,
            status=status,
            statuses=ORDER_STATUSES,
        )

    @app.route("/orders/<order_id>")
    def order_detail(order_id):
        with get_connection(db_path()) as conn:
            order = conn.execute(
                """
                SELECT
                    o.*,
                    c.customer_name,
                    c.contact_person,
                    c.phone,
                    c.email,
                    c.city,
                    c.address
                FROM orders o
                JOIN customers c ON c.customer_id = o.customer_id
                WHERE o.order_id = ?
                """,
                (order_id,),
            ).fetchone()
            if not order:
                return render_template("error.html", message="Order not found"), 404
            items = conn.execute(
                """
                SELECT
                    oi.item_id,
                    p.product_code,
                    p.product_name,
                    p.category,
                    p.brand,
                    p.model,
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
        return render_template("order_detail.html", order=order, items=items)

    @app.route("/export")
    def export_inventory():
        export_path = export_inventory_csv(db_path=db_path())
        return send_file(export_path, mimetype="text/csv", as_attachment=True, download_name=export_path.name)

    @app.route("/api/health")
    def api_health():
        return jsonify(
            {
                "status": "ok",
                "database": "postgresql",
                "version_note": "basic_flask_postgresql_demo_api",
            }
        )

    @app.route("/api/products")
    def api_products():
        page, page_size, offset = safe_page_args()
        product_code = as_text(request.args.get("product_code"))
        product_name = as_text(request.args.get("product_name"))
        category = as_text(request.args.get("category"))
        brand = as_text(request.args.get("brand"))
        supplier_name = as_text(request.args.get("supplier_name"))
        status = as_text(request.args.get("status") or request.args.get("inventory_status"))

        conditions = []
        params = []
        if product_code:
            conditions.append("p.product_code ILIKE ?")
            params.append(f"%{product_code}%")
        if product_name:
            conditions.append("p.product_name ILIKE ?")
            params.append(f"%{product_name}%")
        if category:
            conditions.append("p.category = ?")
            params.append(category)
        if brand:
            conditions.append("p.brand ILIKE ?")
            params.append(f"%{brand}%")
        if supplier_name:
            conditions.append("p.supplier_name ILIKE ?")
            params.append(f"%{supplier_name}%")
        if status == "out_of_stock":
            conditions.append("COALESCE(i.current_quantity, 0) <= 0")
        elif status == "low_stock":
            conditions.append("COALESCE(i.current_quantity, 0) > 0 AND COALESCE(i.current_quantity, 0) < COALESCE(i.safety_stock, 0)")
        elif status == "normal":
            conditions.append("COALESCE(i.current_quantity, 0) >= COALESCE(i.safety_stock, 0)")

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        base_sql = f"""
            FROM products p
            LEFT JOIN inventory i ON i.product_id = p.id
            {where_sql}
        """

        with get_connection(db_path()) as conn:
            total = conn.execute(f"SELECT COUNT(*) AS total {base_sql}", params).fetchone()["total"]
            rows = conn.execute(
                f"""
                SELECT
                    p.id,
                    p.product_code,
                    p.product_name,
                    p.category,
                    p.brand,
                    p.model,
                    p.unit,
                    p.supplier_name,
                    COALESCE(i.current_quantity, 0) AS current_quantity,
                    COALESCE(i.minimum_stock, 0) AS minimum_stock,
                    COALESCE(i.safety_stock, 0) AS safety_stock,
                    COALESCE(i.location, '') AS location,
                    {status_case_sql("i")} AS inventory_status
                {base_sql}
                ORDER BY p.product_code
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset],
            ).fetchall()

        return jsonify(
            {
                "items": [row_to_dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
            }
        )

    @app.route("/api/products/<int:product_id>")
    def api_product_detail(product_id):
        with get_connection(db_path()) as conn:
            product = conn.execute(
                f"""
                SELECT
                    p.*,
                    COALESCE(i.current_quantity, 0) AS current_quantity,
                    COALESCE(i.minimum_stock, 0) AS minimum_stock,
                    COALESCE(i.safety_stock, 0) AS safety_stock,
                    COALESCE(i.location, '') AS location,
                    COALESCE(TO_CHAR(i.last_updated_at, 'YYYY-MM-DD HH24:MI:SS'), '') AS last_updated_at,
                    {status_case_sql("i")} AS inventory_status
                FROM products p
                LEFT JOIN inventory i ON i.product_id = p.id
                WHERE p.id = ?
                """,
                (product_id,),
            ).fetchone()
            if not product:
                return json_error("product not found", 404)

            logs = conn.execute(
                """
                SELECT change_type, quantity_change, quantity_before, quantity_after,
                       reason, note, created_at
                FROM inventory_logs
                WHERE product_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 20
                """,
                (product_id,),
            ).fetchall()

        data = row_to_dict(product)
        data["recent_inventory_logs"] = [row_to_dict(row) for row in logs]
        return jsonify(data)

    @app.route("/api/inventory/low-stock")
    def api_low_stock():
        with get_connection(db_path()) as conn:
            rows = conn.execute(
                f"""
                SELECT
                    p.id,
                    p.product_code,
                    p.product_name,
                    p.category,
                    p.brand,
                    COALESCE(i.current_quantity, 0) AS current_quantity,
                    COALESCE(i.minimum_stock, 0) AS minimum_stock,
                    COALESCE(i.safety_stock, 0) AS safety_stock,
                    COALESCE(i.location, '') AS location,
                    {status_case_sql("i")} AS inventory_status
                FROM products p
                JOIN inventory i ON i.product_id = p.id
                WHERE COALESCE(i.current_quantity, 0) < COALESCE(i.safety_stock, 0)
                ORDER BY i.current_quantity ASC, p.product_code
                """
            ).fetchall()
        return jsonify({"items": [row_to_dict(row) for row in rows], "total": len(rows)})

    @app.route("/api/inventory/update", methods=["POST"])
    def api_inventory_update():
        payload = request.get_json(silent=True) or {}
        product_id = as_int(payload.get("product_id"))
        change_type = as_text(payload.get("change_type"))
        quantity = as_int(payload.get("quantity"), -1)
        reason = as_text(payload.get("reason"))
        note = as_text(payload.get("note"))

        if product_id <= 0:
            return json_error("product_id is required")
        if change_type not in INVENTORY_CHANGE_TYPES:
            return json_error("change_type must be stock_in, stock_out, or adjustment")
        if quantity < 0:
            return json_error("quantity cannot be negative")
        if change_type != "adjustment" and quantity <= 0:
            return json_error("quantity must be greater than zero")

        timestamp = now_text()
        with get_connection(db_path()) as conn:
            product = conn.execute(
                "SELECT id, product_code, product_name FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()
            if not product:
                return json_error("product not found", 404)

            inventory = conn.execute(
                "SELECT * FROM inventory WHERE product_id = ?",
                (product_id,),
            ).fetchone()
            if not inventory:
                conn.execute(
                    """
                    INSERT INTO inventory (
                        product_id, current_quantity, location, minimum_stock, safety_stock,
                        last_updated_at, remark
                    ) VALUES (?, 0, ?, 0, 0, ?, ?)
                    """,
                    (product_id, "Main storage shelf", timestamp, "created by API inventory update"),
                )
                inventory = conn.execute(
                    "SELECT * FROM inventory WHERE product_id = ?",
                    (product_id,),
                ).fetchone()

            before_quantity = inventory["current_quantity"]
            if change_type == "stock_in":
                quantity_change = quantity
                after_quantity = before_quantity + quantity
            elif change_type == "stock_out":
                quantity_change = quantity
                after_quantity = before_quantity - quantity
                if after_quantity < 0:
                    return json_error("stock_out quantity is greater than current inventory")
            else:
                after_quantity = quantity
                quantity_change = after_quantity - before_quantity

            conn.execute(
                """
                UPDATE inventory
                SET current_quantity = ?, last_updated_at = ?
                WHERE product_id = ?
                """,
                (after_quantity, timestamp, product_id),
            )
            conn.execute(
                """
                INSERT INTO inventory_logs (
                    product_id, change_type, quantity_change, quantity_before,
                    quantity_after, reason, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    change_type,
                    quantity_change,
                    before_quantity,
                    after_quantity,
                    reason,
                    note,
                    timestamp,
                ),
            )
            conn.commit()

        return jsonify(
            {
                "product_id": product_id,
                "quantity_before": before_quantity,
                "quantity_after": after_quantity,
                "quantity_change": quantity_change,
                "change_type": change_type,
            }
        )

    @app.route("/api/customers")
    def api_customers():
        page, page_size, offset = safe_page_args()
        keyword = as_text(request.args.get("keyword"))
        conditions = []
        params = []
        if keyword:
            conditions.append("(customer_id ILIKE ? OR customer_name ILIKE ? OR city ILIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with get_connection(db_path()) as conn:
            total = conn.execute(f"SELECT COUNT(*) AS total FROM customers {where_sql}", params).fetchone()["total"]
            rows = conn.execute(
                f"""
                SELECT customer_id, customer_name, contact_person, phone, email, city, address, created_at, notes
                FROM customers
                {where_sql}
                ORDER BY customer_id
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset],
            ).fetchall()
        return jsonify({"items": [row_to_dict(row) for row in rows], "page": page, "page_size": page_size, "total": total})

    @app.route("/api/orders")
    def api_orders():
        page, page_size, offset = safe_page_args()
        keyword = as_text(request.args.get("keyword"))
        status = as_text(request.args.get("status"))
        conditions = []
        params = []
        if keyword:
            conditions.append("(o.order_id ILIKE ? OR c.customer_id ILIKE ? OR c.customer_name ILIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if status:
            conditions.append("o.order_status = ?")
            params.append(status)
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        base_sql = f"""
            FROM orders o
            JOIN customers c ON c.customer_id = o.customer_id
            {where_sql}
        """
        with get_connection(db_path()) as conn:
            total = conn.execute(f"SELECT COUNT(*) AS total {base_sql}", params).fetchone()["total"]
            rows = conn.execute(
                f"""
                SELECT
                    o.order_id,
                    o.customer_id,
                    c.customer_name,
                    o.order_date,
                    o.order_status,
                    o.total_amount,
                    o.created_at,
                    o.notes
                {base_sql}
                ORDER BY o.order_date DESC, o.order_id DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset],
            ).fetchall()
        return jsonify({"items": [row_to_dict(row) for row in rows], "page": page, "page_size": page_size, "total": total})

    @app.route("/api/orders/<order_id>")
    def api_order_detail(order_id):
        with get_connection(db_path()) as conn:
            order = conn.execute(
                """
                SELECT
                    o.*,
                    c.customer_name,
                    c.contact_person,
                    c.phone,
                    c.email,
                    c.city,
                    c.address
                FROM orders o
                JOIN customers c ON c.customer_id = o.customer_id
                WHERE o.order_id = ?
                """,
                (order_id,),
            ).fetchone()
            if not order:
                return json_error("order not found", 404)
            items = conn.execute(
                """
                SELECT
                    oi.item_id,
                    p.product_code,
                    p.product_name,
                    p.category,
                    p.brand,
                    p.model,
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

        data = row_to_dict(order)
        data["items"] = [row_to_dict(row) for row in items]
        return jsonify(data)

    @app.route("/api/orders/<order_id>/status", methods=["PATCH"])
    def api_update_order_status(order_id):
        payload = request.get_json(silent=True) or {}
        status_value = as_text(payload.get("order_status"))
        if not status_value:
            return json_error("order_status is required")
        if status_value not in ORDER_STATUSES:
            return json_error("invalid order_status")

        with get_connection(db_path()) as conn:
            order = conn.execute("SELECT order_id FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            if not order:
                return json_error("order not found", 404)
            conn.execute(
                "UPDATE orders SET order_status = ? WHERE order_id = ?",
                (status_value, order_id),
            )
            conn.commit()
        return jsonify({"order_id": order_id, "order_status": status_value})

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", message="Page not found"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("error.html", message="The app hit a server error. Please check the input or database state."), 500

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    create_app().run(host="127.0.0.1", port=port, debug=False)
