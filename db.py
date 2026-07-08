import re
import sqlite3
from pathlib import Path


# -----------------------------
# DATABASE + FOLDER SETUP
# -----------------------------

DATA_FOLDER = Path("portfolio_data")
DB_PATH = DATA_FOLDER / "portfolio.db"

# Only allow simple identifier-safe table names.
# Adjust the pattern if you need a stricter format (e.g. must end in "_portfolio").
TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def initialize_database():
    """
    Creates:
    - portfolio_data folder
    - portfolio.db file
    IF they do not already exist
    """

    DATA_FOLDER.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.close()

    return {
        "status": "success",
        "message": "Database initialized successfully"
    }


# -----------------------------
# CONNECTION
# -----------------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# VALIDATION HELPERS
# -----------------------------

def _validate_table_name(table_name: str):
    if not isinstance(table_name, str) or not TABLE_NAME_PATTERN.match(table_name):
        raise ValueError(
            f"table_name must be alphanumeric/underscore only, got: {table_name!r}"
        )


def _validate_company_name(company_name):
    if not isinstance(company_name, str) or not company_name.strip():
        raise ValueError(
            f"company_name is required and must be a non-empty string, got: {company_name!r}"
        )


def _validate_symbol(symbol):
    if symbol is not None and not isinstance(symbol, str):
        raise ValueError(f"symbol must be a string, got {type(symbol).__name__}: {symbol!r}")


def _validate_buy_price(buy_price):
    # bool is a subclass of int in Python, so explicitly exclude it
    if isinstance(buy_price, bool) or not isinstance(buy_price, (int, float)):
        raise ValueError(
            f"buy_price must be a number, got {type(buy_price).__name__}: {buy_price!r}"
        )


def _validate_quantity(quantity):
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise ValueError(
            f"quantity must be an integer, got {type(quantity).__name__}: {quantity!r}"
        )


def _validate_buy_date(buy_date):
    if not isinstance(buy_date, str) or not buy_date.strip():
        raise ValueError(
            f"buy_date must be a non-empty string, got: {buy_date!r}"
        )


def _validate_stock_id(stock_id):
    if isinstance(stock_id, bool) or not isinstance(stock_id, int):
        raise ValueError(
            f"stock_id must be an integer, got {type(stock_id).__name__}: {stock_id!r}"
        )


# -----------------------------
# CREATE TABLE
# -----------------------------

def create_portfolio_table(table_name: str):
    """
    Creates user portfolio table if not exists
    Example:
        yash_portfolio
        alex_portfolio
    """

    _validate_table_name(table_name)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            symbol TEXT,
            buy_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            buy_date TEXT NOT NULL
        )
        """

        cursor.execute(query)
        conn.commit()

        return {
            "status": "success",
            "message": f"Table '{table_name}' ready"
        }
    finally:
        conn.close()


# -----------------------------
# INSERT RECORD
# -----------------------------

def add_stock(
    table_name: str,
    company_name: str,
    buy_price: float,
    quantity: int,
    buy_date: str,
    symbol: str = ""
):

    _validate_table_name(table_name)
    _validate_company_name(company_name)
    _validate_symbol(symbol)
    _validate_buy_price(buy_price)
    _validate_quantity(quantity)
    _validate_buy_date(buy_date)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        query = f"""
        INSERT INTO {table_name}
        (
            company_name,
            symbol,
            buy_price,
            quantity,
            buy_date
        )
        VALUES (?, ?, ?, ?, ?)
        """

        cursor.execute(query, (
            company_name,
            symbol,
            buy_price,
            quantity,
            buy_date
        ))

        conn.commit()

        return {
            "status": "success",
            "message": f"{company_name} added successfully"
        }
    finally:
        conn.close()


# -----------------------------
# GET ALL RECORDS
# -----------------------------

def get_all_stocks(table_name: str):

    _validate_table_name(table_name)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        query = f"""
        SELECT * FROM {table_name}
        ORDER BY id DESC
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


# -----------------------------
# DELETE RECORD
# -----------------------------

def delete_stock(
    table_name: str,
    stock_id: int
):

    _validate_table_name(table_name)
    _validate_stock_id(stock_id)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        query = f"""
        DELETE FROM {table_name}
        WHERE id = ?
        """

        cursor.execute(query, (stock_id,))
        conn.commit()

        return {
            "status": "success",
            "message": f"Deleted record {stock_id}"
        }
    finally:
        conn.close()


# -----------------------------
# UPDATE RECORD
# -----------------------------

def update_stock(
    table_name: str,
    stock_id: int,
    company_name: str,
    symbol: str,
    buy_price: float,
    quantity: int,
    buy_date: str
):

    _validate_table_name(table_name)
    _validate_stock_id(stock_id)
    _validate_company_name(company_name)
    _validate_symbol(symbol)
    _validate_buy_price(buy_price)
    _validate_quantity(quantity)
    _validate_buy_date(buy_date)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        query = f"""
        UPDATE {table_name}
        SET
            company_name = ?,
            symbol = ?,
            buy_price = ?,
            quantity = ?,
            buy_date = ?
        WHERE id = ?
        """

        cursor.execute(query, (
            company_name,
            symbol,
            buy_price,
            quantity,
            buy_date,
            stock_id
        ))

        conn.commit()

        return {
            "status": "success",
            "message": f"Updated record {stock_id}"
        }
    finally:
        conn.close()