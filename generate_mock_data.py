from datetime import datetime, timedelta
from pathlib import Path
import random

from openpyxl import Workbook


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "sample_inventory_data.xlsx"


CATEGORIES = [
    "Components",
    "Sensor Modules",
    "Controllers",
    "Power Supplies",
    "Cables and Connectors",
    "Network Devices",
    "Industrial Parts",
    "Repair Tools",
    "Soldering Supplies",
    "ESD Supplies",
    "Testing Accessories",
    "Labels and Packaging",
]


SUPPLIERS = [
    ("North Harbor Electronics Supply", "Toronto"),
    ("Metro Smart Equipment Parts", "Mississauga"),
    ("Central Electronic Parts Center", "Markham"),
    ("High-Tech Components Store", "Waterloo"),
    ("Automation Parts Warehouse", "Vaughan"),
    ("Pacific Electronic Components", "Vancouver"),
    ("Network Equipment Supply Co.", "Ottawa"),
]


LOCATIONS = [
    "Main Warehouse A",
    "Main Warehouse B",
    "Lab Parts Cabinet",
    "Project Spare Box",
    "Repair Desk Shelf",
    "Temporary Project Shelf",
    "Office Electronics Cabinet",
    "Test Bench Spare Box",
]


REASONS = [
    "supplier delivery",
    "project site usage",
    "repair spare part usage",
    "lab testing",
    "prototype build",
    "low voltage installation",
    "stock count adjustment",
    "loss registration",
    "returned material",
    "temporary project reserve",
]


PRODUCT_TEMPLATES = [
    ("DC 12V 2A Power Adapter", "Power Supplies", "Generic", "12V-2A", "pcs", 18.5, 32.0),
    ("ESP32-WROOM-32 Dev Module", "Controllers", "Espressif", "ESP32-WROOM-32", "pcs", 24.0, 42.0),
    ("STM32F103C8T6 Minimum Board", "Controllers", "ST", "STM32F103C8T6", "pcs", 16.5, 30.0),
    ("RS485 to USB Converter Module", "Controllers", "Generic", "USB-RS485", "pcs", 28.0, 52.0),
    ("PIR Motion Sensor HC-SR501", "Sensor Modules", "Generic", "HC-SR501", "pcs", 5.2, 10.0),
    ("SHT30 Temperature Humidity Module", "Sensor Modules", "Sensirion", "SHT30", "pcs", 18.0, 35.0),
    ("5V Single Relay Module", "Components", "Generic", "5V-1CH", "pcs", 3.5, 7.0),
    ("Industrial Shielded CAT6 Cable", "Cables and Connectors", "Choseal", "CAT6-SHIELD", "meter", 3.2, 6.0),
    ("Phoenix Terminal 2P 5.08mm", "Cables and Connectors", "Generic", "2P-5.08", "pcs", 0.45, 1.0),
    ("Dupont Wire 20cm Male to Female", "Cables and Connectors", "Generic", "20CM-MF", "pcs", 0.18, 0.5),
    ("Heat Shrink Tube 6mm Black", "Cables and Connectors", "Generic", "6MM-BK", "meter", 0.8, 1.6),
    ("Anti-static Wrist Strap", "ESD Supplies", "Generic", "ESD-STRAP", "pcs", 6.0, 12.0),
    ("60W Temperature Control Soldering Iron", "Repair Tools", "Quick", "60W-TC", "pcs", 68.0, 118.0),
    ("Lead-free Solder Wire 0.8mm", "Soldering Supplies", "Mechanic", "0.8MM", "roll", 52.0, 88.0),
    ("Digital Multimeter Test Lead", "Testing Accessories", "Generic", "TL-1000", "pair", 9.0, 18.0),
    ("Equipment Label Paper 50x30mm", "Labels and Packaging", "Generic", "50X30", "roll", 12.0, 25.0),
    ("8-Port PoE Switch", "Network Devices", "TP-Link", "POE-8P", "pcs", 185.0, 320.0),
    ("Photoelectric Switch E3F-DS30C4", "Industrial Parts", "Omron", "E3F-DS30C4", "pcs", 36.0, 68.0),
    ("DIN Rail Power Supply 24V 5A", "Power Supplies", "Mean Well", "24V-5A", "pcs", 85.0, 150.0),
]


def product_quantity_range(category):
    if category in {"Components", "Cables and Connectors", "Labels and Packaging", "ESD Supplies"}:
        return 80, 500
    if category in {"Controllers", "Sensor Modules", "Power Supplies", "Industrial Parts", "Testing Accessories"}:
        return 8, 80
    return 5, 60


def build_products(count=96):
    rows = []
    for index in range(1, count + 1):
        template = PRODUCT_TEMPLATES[(index - 1) % len(PRODUCT_TEMPLATES)]
        supplier_name, supplier_city = SUPPLIERS[(index * 3) % len(SUPPLIERS)]
        product_name, category, brand, model, unit, cost_price, sale_price = template
        variant = "" if index <= len(PRODUCT_TEMPLATES) else f" Batch {index // len(PRODUCT_TEMPLATES) + 1}"
        rows.append(
            {
                "product_code": f"SKU-{index:04d}",
                "product_name": f"{product_name}{variant}",
                "category": category,
                "brand": brand,
                "model": model,
                "unit": unit,
                "cost_price": round(cost_price * random.uniform(0.95, 1.08), 2),
                "sale_price": round(sale_price * random.uniform(0.96, 1.10), 2),
                "supplier_name": supplier_name,
                "supplier_city": supplier_city,
                "usage_scene": random.choice(["repair spare parts", "project materials", "lab testing", "installation support"]),
                "remark": "generated sample product",
                "created_at": datetime(2026, 1, random.randint(1, 8)).strftime("%Y-%m-%d"),
            }
        )
    return rows


def build_inventory(products):
    rows = []
    for index, product in enumerate(products, start=1):
        low, high = product_quantity_range(product["category"])
        safety_stock = random.randint(max(2, low // 5), max(5, low // 2))
        current_quantity = random.randint(low, high)
        rows.append(
            {
                "inventory_code": f"INV-SAMPLE-{index:04d}",
                "product_code": product["product_code"],
                "current_quantity": current_quantity,
                "location": LOCATIONS[index % len(LOCATIONS)],
                "minimum_stock": max(1, safety_stock // 2),
                "safety_stock": safety_stock,
                "last_updated_at": datetime(2026, 1, random.randint(20, 28), 16, 0).strftime("%Y-%m-%d %H:%M:%S"),
                "remark": "generated sample inventory row",
            }
        )
    return rows


def build_logs(products, inventory, count=273):
    current_by_code = {row["product_code"]: row["current_quantity"] for row in inventory}
    logs = []

    for index in range(1, count + 1):
        product = products[(index * 7) % len(products)]
        product_code = product["product_code"]
        before = current_by_code[product_code]
        change_type = random.choices(["stock_in", "stock_out", "adjustment"], weights=[45, 45, 10], k=1)[0]

        if change_type == "stock_in":
            quantity_change = random.randint(1, 40)
            after = before + quantity_change
        elif change_type == "stock_out":
            quantity_change = min(before, random.randint(1, 30))
            after = before - quantity_change
        else:
            after = max(0, before + random.randint(-10, 10))
            quantity_change = after - before

        current_by_code[product_code] = after
        logs.append(
            {
                "log_code": f"MOV-SAMPLE-{index:04d}",
                "product_code": product_code,
                "change_type": change_type,
                "quantity_change": quantity_change,
                "quantity_before": before,
                "quantity_after": after,
                "reason": random.choice(REASONS),
                "created_at": (datetime(2026, 1, 1, 9, 0) + timedelta(days=index % 28, hours=index % 8)).strftime("%Y-%m-%d %H:%M:%S"),
                "note": "generated sample movement",
            }
        )

    for row in inventory:
        row["current_quantity"] = current_by_code[row["product_code"]]

    return logs


def write_sheet(workbook, name, rows):
    worksheet = workbook.create_sheet(name)
    if not rows:
        return
    headers = list(rows[0].keys())
    worksheet.append(headers)
    for row in rows:
        worksheet.append([row.get(header) for header in headers])


def generate_mock_data(output_path=OUTPUT_PATH):
    random.seed(2605)
    products = build_products()
    inventory = build_inventory(products)
    logs = build_logs(products, inventory)

    workbook = Workbook()
    workbook.remove(workbook.active)
    write_sheet(workbook, "product_info", products)
    write_sheet(workbook, "inventory", inventory)
    write_sheet(workbook, "inventory_log", logs)
    workbook.save(output_path)

    return {
        "output_path": Path(output_path),
        "products": len(products),
        "inventory": len(inventory),
        "inventory_logs": len(logs),
    }


if __name__ == "__main__":
    result = generate_mock_data()
    print(f"Excel file generated: {result['output_path'].name}")
    print(f"products: {result['products']}")
    print(f"inventory: {result['inventory']}")
    print(f"inventory_logs: {result['inventory_logs']}")
