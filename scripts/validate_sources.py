from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd


OUTPUT_DIR = Path("reports")


COLUMN_ALIASES = {}


REQUIRED_COLUMNS = {
    "products": ["product_code", "product_name", "unit", "cost_price", "sale_price"],
    "inventory": ["product_code", "current_quantity"],
    "customers": ["customer_id", "customer_name"],
    "orders": ["order_id", "customer_id", "order_date", "order_status", "total_amount"],
    "order_items": ["order_id", "product_code", "quantity", "unit_price", "subtotal"],
}


@dataclass
class ValidationResult:
    name: str
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    errors: list[dict] = field(default_factory=list)

    def add_error(self, row_number: int, column_name: str, message: str):
        self.errors.append(
            {
                "source": self.name,
                "row_number": row_number,
                "column": column_name,
                "message": message,
            }
        )

    def finish(self):
        bad_rows = {error["row_number"] for error in self.errors}
        self.invalid_rows = len(bad_rows)
        self.valid_rows = max(self.total_rows - self.invalid_rows, 0)


def read_source(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported file type: {path}")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for column in df.columns:
        cleaned = str(column).strip()
        rename_map[column] = COLUMN_ALIASES.get(cleaned, cleaned.strip().lower())
    return df.rename(columns=rename_map)


def row_no(index_value) -> int:
    return int(index_value) + 2


def check_required_columns(df: pd.DataFrame, result: ValidationResult, required: Iterable[str]):
    for column in required:
        if column not in df.columns:
            result.add_error(1, column, "missing required column")


def check_required_values(df: pd.DataFrame, result: ValidationResult, columns: Iterable[str]):
    for column in columns:
        if column not in df.columns:
            continue
        missing = df[column].isna() | (df[column].astype(str).str.strip() == "")
        for index_value in df[missing].index:
            result.add_error(row_no(index_value), column, "required value is empty")


def check_duplicates(df: pd.DataFrame, result: ValidationResult, column: str):
    if column not in df.columns:
        return
    duplicated = df[column].astype(str).str.strip().duplicated(keep=False)
    for index_value in df[duplicated].index:
        result.add_error(row_no(index_value), column, "duplicate value")


def numeric_series(df: pd.DataFrame, result: ValidationResult, column: str) -> pd.Series | None:
    if column not in df.columns:
        return None
    converted = pd.to_numeric(df[column], errors="coerce")
    invalid = converted.isna() & df[column].notna() & (df[column].astype(str).str.strip() != "")
    for index_value in df[invalid].index:
        result.add_error(row_no(index_value), column, "not a valid number")
    return converted


def date_series(df: pd.DataFrame, result: ValidationResult, column: str) -> pd.Series | None:
    if column not in df.columns:
        return None
    converted = pd.to_datetime(df[column], errors="coerce")
    invalid = converted.isna() & df[column].notna() & (df[column].astype(str).str.strip() != "")
    for index_value in df[invalid].index:
        result.add_error(row_no(index_value), column, "not a valid date")
    return converted


def check_nonnegative(df: pd.DataFrame, result: ValidationResult, columns: Iterable[str]):
    for column in columns:
        values = numeric_series(df, result, column)
        if values is None:
            continue
        for index_value in df[values < 0].index:
            result.add_error(row_no(index_value), column, "cannot be negative")


def check_positive(df: pd.DataFrame, result: ValidationResult, columns: Iterable[str]):
    for column in columns:
        values = numeric_series(df, result, column)
        if values is None:
            continue
        for index_value in df[values <= 0].index:
            result.add_error(row_no(index_value), column, "must be greater than zero")


def check_foreign_keys(
    child_df: pd.DataFrame,
    child_column: str,
    parent_df: pd.DataFrame | None,
    parent_column: str,
    result: ValidationResult,
):
    if parent_df is None or child_column not in child_df.columns or parent_column not in parent_df.columns:
        return
    parent_values = set(parent_df[parent_column].dropna().astype(str).str.strip())
    missing = ~child_df[child_column].astype(str).str.strip().isin(parent_values)
    for index_value in child_df[missing].index:
        result.add_error(row_no(index_value), child_column, "referenced value not found")


def check_order_item_subtotal(df: pd.DataFrame, result: ValidationResult):
    required = {"quantity", "unit_price", "subtotal"}
    if not required.issubset(df.columns):
        return
    quantity = pd.to_numeric(df["quantity"], errors="coerce")
    unit_price = pd.to_numeric(df["unit_price"], errors="coerce")
    subtotal = pd.to_numeric(df["subtotal"], errors="coerce")
    expected = (quantity * unit_price).round(2)
    diff = (subtotal - expected).abs()
    invalid = diff > 0.05
    for index_value in df[invalid].index:
        result.add_error(row_no(index_value), "subtotal", "subtotal does not match quantity * unit_price")


def validate_source(name: str, df: pd.DataFrame) -> ValidationResult:
    result = ValidationResult(name=name, total_rows=len(df))
    required = REQUIRED_COLUMNS[name]
    check_required_columns(df, result, required)
    check_required_values(df, result, required)

    if name == "products":
        check_duplicates(df, result, "product_code")
        check_nonnegative(df, result, ["cost_price", "sale_price"])
    elif name == "inventory":
        check_nonnegative(df, result, ["current_quantity", "minimum_stock", "safety_stock"])
    elif name == "customers":
        check_duplicates(df, result, "customer_id")
    elif name == "orders":
        check_duplicates(df, result, "order_id")
        check_nonnegative(df, result, ["total_amount"])
        date_series(df, result, "order_date")
    elif name == "order_items":
        check_positive(df, result, ["quantity"])
        check_nonnegative(df, result, ["unit_price", "subtotal"])
        check_order_item_subtotal(df, result)

    result.finish()
    return result


def load_optional_sources(args) -> dict[str, pd.DataFrame]:
    frames = {}
    for name in REQUIRED_COLUMNS:
        file_path = getattr(args, name)
        if not file_path:
            continue
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"{name} file not found: {path}")
        frames[name] = normalize_columns(read_source(path))
    return frames


def write_reports(results: list[ValidationResult]):
    OUTPUT_DIR.mkdir(exist_ok=True)
    summary = [
        {
            "source": result.name,
            "total_rows": result.total_rows,
            "valid_rows": result.valid_rows,
            "invalid_rows": result.invalid_rows,
            "error_count": len(result.errors),
        }
        for result in results
    ]
    (OUTPUT_DIR / "validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    import_log = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if any(result.invalid_rows for result in results) else "passed",
        "source_count": len(results),
        "total_rows": sum(result.total_rows for result in results),
        "valid_rows": sum(result.valid_rows for result in results),
        "invalid_rows": sum(result.invalid_rows for result in results),
        "error_count": sum(len(result.errors) for result in results),
        "outputs": {
            "validation_summary": str(OUTPUT_DIR / "validation_summary.json"),
            "invalid_rows": str(OUTPUT_DIR / "invalid_rows.csv"),
            "import_log": str(OUTPUT_DIR / "import_log.json"),
        },
        "sources": summary,
    }
    (OUTPUT_DIR / "import_log.json").write_text(
        json.dumps(import_log, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    error_rows = [error for result in results for error in result.errors]
    if error_rows:
        pd.DataFrame(error_rows).to_csv(OUTPUT_DIR / "invalid_rows.csv", index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame(columns=["source", "row_number", "column", "message"]).to_csv(
            OUTPUT_DIR / "invalid_rows.csv",
            index=False,
            encoding="utf-8-sig",
        )


def parse_args():
    parser = argparse.ArgumentParser(description="Validate inventory and order source files before loading.")
    parser.add_argument("--products", help="CSV or Excel file for products")
    parser.add_argument("--inventory", help="CSV or Excel file for inventory")
    parser.add_argument("--customers", help="CSV or Excel file for customers")
    parser.add_argument("--orders", help="CSV or Excel file for orders")
    parser.add_argument("--order-items", dest="order_items", help="CSV or Excel file for order items")
    return parser.parse_args()


def main():
    args = parse_args()
    frames = load_optional_sources(args)
    if not frames:
        raise SystemExit("No source files provided. Use --products, --customers, --orders, etc.")

    results = []
    for name, frame in frames.items():
        results.append(validate_source(name, frame))

    if "inventory" in frames:
        inventory_result = next(result for result in results if result.name == "inventory")
        check_foreign_keys(frames["inventory"], "product_code", frames.get("products"), "product_code", inventory_result)
        inventory_result.finish()

    if "orders" in frames:
        order_result = next(result for result in results if result.name == "orders")
        check_foreign_keys(frames["orders"], "customer_id", frames.get("customers"), "customer_id", order_result)
        order_result.finish()

    if "order_items" in frames:
        item_result = next(result for result in results if result.name == "order_items")
        check_foreign_keys(frames["order_items"], "order_id", frames.get("orders"), "order_id", item_result)
        check_foreign_keys(frames["order_items"], "product_code", frames.get("products"), "product_code", item_result)
        item_result.finish()

    write_reports(results)

    for result in results:
        print(
            f"{result.name}: total={result.total_rows}, "
            f"valid={result.valid_rows}, invalid={result.invalid_rows}, errors={len(result.errors)}"
        )
    print(f"Reports written to {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
