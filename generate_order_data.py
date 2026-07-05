from datetime import datetime, timedelta
import random

from database import DATABASE_URL, get_connection, init_db


CUSTOMER_NAMES = [
    "North Harbor Smart Device Service Center",
    "Metro Low Voltage Engineering Team",
    "Tech Park Building Automation Group",
    "Westside Equipment Maintenance Store",
    "Central Electronics Service Office",
    "Lakeside Automation Workshop",
    "Development Zone Device Support Station",
    "East Market Electronics Shop",
    "Downtown Network Engineering Office",
    "Northside Hardware Parts Store",
    "Regional Electronics Repair Center",
    "South District Smart Wiring Team",
    "Industrial Control Service Store",
    "Port Equipment Support Station",
    "Trade Center Electronics Parts Store",
    "Factory Automation Service Office",
    "Mechanical Parts Service Store",
    "Security Device Maintenance Office",
    "Industrial Repair Service Center",
    "Low Voltage Installation Team",
    "Warehouse Spare Parts Office",
    "Project Materials Station",
    "Smart Device Maintenance Office",
    "Mechanical Service Store",
    "Electronics Parts Store",
    "CCTV Support Point",
    "Hardware Lab",
    "Facility Support Team",
    "Industrial IoT Service Office",
    "Building Device Support Station",
]


CITIES = [
    "Toronto",
    "Mississauga",
    "Markham",
    "Vaughan",
    "Hamilton",
    "London",
    "Ottawa",
    "Waterloo",
    "Burlington",
    "Kitchener",
]


ORDER_STATUSES = ["pending", "processing", "shipped", "completed", "cancelled"]


SAMPLE_USERS = [
    ("admin.demo", "Demo Admin", "admin"),
    ("staff.demo", "Demo Staff", "staff"),
    ("viewer.demo", "Demo Viewer", "viewer"),
]


def sample_date(index):
    base = datetime(2026, 1, 5, 9, 30, 0)
    return base + timedelta(
        days=index % 28,
        hours=random.randint(0, 7),
        minutes=random.choice([0, 10, 15, 20, 30, 45]),
    )


def fetch_products(conn):
    return conn.execute(
        """
        SELECT id, product_code, product_name, category, sale_price
        FROM products
        ORDER BY product_code
        """
    ).fetchall()


def build_customers():
    customers = []
    for index, name in enumerate(CUSTOMER_NAMES, start=1):
        city = CITIES[(index * 3) % len(CITIES)]
        customers.append(
            {
                "customer_id": f"CUS-SAMPLE-{index:04d}",
                "customer_name": name,
                "contact_person": f"Project Contact {index:02d}",
                "phone": f"555-010-{index:04d}",
                "email": f"customer{index:03d}@example.local",
                "city": city,
                "address": f"{city} sample address {index}",
                "created_at": sample_date(index).strftime("%Y-%m-%d %H:%M:%S"),
                "notes": "Generated sample customer data for order relationship testing",
            }
        )
    return customers


def quantity_for_category(category):
    high_volume = {"Components", "Cables and Connectors", "Labels and Packaging", "ESD Supplies"}
    medium_volume = {"Soldering Supplies", "Industrial Parts"}
    if category in high_volume:
        return random.randint(10, 80)
    if category in medium_volume:
        return random.randint(3, 25)
    return random.randint(1, 8)


def seed_users_and_audit_log(conn):
    user_id = None
    for username, display_name, role_name in SAMPLE_USERS:
        row = conn.execute(
            """
            INSERT INTO users (username, display_name, role_name)
            VALUES (?, ?, ?)
            ON CONFLICT (username) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                role_name = EXCLUDED.role_name
            RETURNING id
            """,
            (username, display_name, role_name),
        ).fetchone()
        if username == "staff.demo":
            user_id = row["id"]

    conn.execute(
        """
        INSERT INTO audit_logs (user_id, action_name, table_name, record_key, new_value)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            "seed_sample_data",
            "orders",
            "sample_batch",
            "Generated customer and order sample data",
        ),
    )


def generate_order_data(database_url=DATABASE_URL, reset=True):
    random.seed(2606)
    init_db(database_url)

    with get_connection(database_url) as conn:
        products = fetch_products(conn)
        if not products:
            raise RuntimeError("Import or create product data before generating customer/order sample data.")

        if reset:
            conn.execute("DELETE FROM audit_logs")
            conn.execute("DELETE FROM order_items")
            conn.execute("DELETE FROM orders")
            conn.execute("DELETE FROM customers")

        seed_users_and_audit_log(conn)
        customers = build_customers()
        for customer in customers:
            conn.execute(
                """
                INSERT INTO customers (
                    customer_id, customer_name, contact_person, phone, email,
                    city, address, created_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(customer_id) DO UPDATE SET
                    customer_name = excluded.customer_name,
                    contact_person = excluded.contact_person,
                    phone = excluded.phone,
                    email = excluded.email,
                    city = excluded.city,
                    address = excluded.address,
                    notes = excluded.notes
                """,
                (
                    customer["customer_id"],
                    customer["customer_name"],
                    customer["contact_person"],
                    customer["phone"],
                    customer["email"],
                    customer["city"],
                    customer["address"],
                    customer["created_at"],
                    customer["notes"],
                ),
            )

        item_count = 0
        for order_index in range(1, 61):
            customer = customers[(order_index * 7) % len(customers)]
            order_id = f"ORD-SAMPLE-{order_index:04d}"
            order_at = sample_date(order_index)
            status = random.choices(ORDER_STATUSES, weights=[10, 22, 22, 38, 8], k=1)[0]
            selected_products = random.sample(products, 2)
            items = []
            total_amount = 0.0

            for product in selected_products:
                quantity = quantity_for_category(product["category"])
                base_price = float(product["sale_price"] or 0)
                unit_price = round(base_price * random.uniform(0.96, 1.04), 2)
                subtotal = round(quantity * unit_price, 2)
                total_amount += subtotal
                items.append((product["id"], quantity, unit_price, subtotal))

            conn.execute(
                """
                INSERT INTO orders (
                    order_id, customer_id, order_date, order_status,
                    total_amount, created_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    customer_id = excluded.customer_id,
                    order_date = excluded.order_date,
                    order_status = excluded.order_status,
                    total_amount = excluded.total_amount,
                    notes = excluded.notes
                """,
                (
                    order_id,
                    customer["customer_id"],
                    order_at.strftime("%Y-%m-%d"),
                    status,
                    round(total_amount, 2),
                    order_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "Generated sample order for customer, product, and order query testing",
                ),
            )

            conn.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
            for product_id, quantity, unit_price, subtotal in items:
                conn.execute(
                    """
                    INSERT INTO order_items (
                        order_id, product_id, quantity, unit_price, subtotal
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (order_id, product_id, quantity, unit_price, subtotal),
                )
                item_count += 1

        conn.commit()

    return {"customers": len(customers), "orders": 60, "order_items": item_count}


if __name__ == "__main__":
    summary = generate_order_data()
    print("Sample order data generated")
    print(f"customers: {summary['customers']}")
    print(f"orders: {summary['orders']}")
    print(f"order_items: {summary['order_items']}")
