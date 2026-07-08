import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
import sqlite3
from pathlib import Path

from db import (
    initialize_database,
    create_portfolio_table,
    add_stock,
    get_all_stocks,
    delete_stock,
    update_stock,
    DB_PATH
)


# =====================================================
# TEST CONSTANTS
# =====================================================

TEST_TABLE = "testuser_portfolio"


# =====================================================
# SETUP
# =====================================================

@pytest.fixture(scope="module", autouse=True)
def setup_database():

    initialize_database()
    create_portfolio_table(TEST_TABLE)

    yield

    # Optional cleanup after tests
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")

    conn.commit()
    conn.close()


# =====================================================
# DATABASE INITIALIZATION TESTS
# =====================================================

def test_database_file_exists():

    assert Path(DB_PATH).exists()


def test_database_initialization_response():

    response = initialize_database()

    assert response["status"] == "success"


# =====================================================
# TABLE CREATION TESTS
# =====================================================

def test_create_table_success():

    response = create_portfolio_table(TEST_TABLE)

    assert response["status"] == "success"


def test_duplicate_table_creation():

    response = create_portfolio_table(TEST_TABLE)

    assert response["status"] == "success"


def test_invalid_table_name_sql_injection():

    malicious_name = "abc; DROP TABLE users;"

    with pytest.raises(Exception):
        create_portfolio_table(malicious_name)


# =====================================================
# INSERT RECORD TESTS
# =====================================================

def test_add_stock_success():

    response = add_stock(
        table_name=TEST_TABLE,
        company_name="Apple",
        symbol="AAPL",
        buy_price=200.5,
        quantity=10,
        buy_date="2026-05-19"
    )

    assert response["status"] == "success"


def test_add_stock_empty_symbol():

    response = add_stock(
        table_name=TEST_TABLE,
        company_name="Tesla",
        symbol="",
        buy_price=500,
        quantity=2,
        buy_date="2026-05-19"
    )

    assert response["status"] == "success"


def test_add_stock_negative_price():

    response = add_stock(
        table_name=TEST_TABLE,
        company_name="Meta",
        symbol="META",
        buy_price=-100,
        quantity=5,
        buy_date="2026-05-19"
    )

    # Current code allows this
    assert response["status"] == "success"


def test_add_stock_negative_quantity():

    response = add_stock(
        table_name=TEST_TABLE,
        company_name="Netflix",
        symbol="NFLX",
        buy_price=300,
        quantity=-10,
        buy_date="2026-05-19"
    )

    # Current code allows this
    assert response["status"] == "success"


def test_add_stock_invalid_table():

    with pytest.raises(Exception):
        add_stock(
            table_name="ghost_table",
            company_name="Apple",
            symbol="AAPL",
            buy_price=200,
            quantity=1,
            buy_date="2026-05-19"
        )


def test_add_stock_large_values():

    response = add_stock(
        table_name=TEST_TABLE,
        company_name="BigCorp",
        symbol="BIG",
        buy_price=999999999999999,
        quantity=999999999999999,
        buy_date="2026-05-19"
    )

    assert response["status"] == "success"


def test_add_stock_unicode_company():

    response = add_stock(
        table_name=TEST_TABLE,
        company_name="株式会社トヨタ",
        symbol="TYT",
        buy_price=100,
        quantity=1,
        buy_date="2026-05-19"
    )

    assert response["status"] == "success"


# =====================================================
# RETRIEVE TESTS
# =====================================================

def test_get_all_stocks():

    rows = get_all_stocks(TEST_TABLE)

    assert isinstance(rows, list)

    assert len(rows) > 0


def test_get_all_stocks_structure():

    rows = get_all_stocks(TEST_TABLE)

    first_row = rows[0]

    assert "id" in first_row
    assert "company_name" in first_row
    assert "symbol" in first_row
    assert "buy_price" in first_row
    assert "quantity" in first_row
    assert "buy_date" in first_row


def test_get_all_invalid_table():

    with pytest.raises(Exception):
        get_all_stocks("invalid_table")


# =====================================================
# UPDATE TESTS
# =====================================================

def test_update_stock_success():

    rows = get_all_stocks(TEST_TABLE)

    stock_id = rows[0]["id"]

    response = update_stock(
        table_name=TEST_TABLE,
        stock_id=stock_id,
        company_name="Updated Apple",
        symbol="AAPL",
        buy_price=300,
        quantity=20,
        buy_date="2026-05-20"
    )

    assert response["status"] == "success"


def test_update_nonexistent_stock():

    response = update_stock(
        table_name=TEST_TABLE,
        stock_id=999999,
        company_name="Ghost",
        symbol="GST",
        buy_price=1,
        quantity=1,
        buy_date="2026-05-19"
    )

    # Current code falsely returns success
    assert response["status"] == "success"


def test_update_invalid_table():

    with pytest.raises(Exception):
        update_stock(
            table_name="ghost_table",
            stock_id=1,
            company_name="Ghost",
            symbol="GST",
            buy_price=1,
            quantity=1,
            buy_date="2026-05-19"
        )


# =====================================================
# DELETE TESTS
# =====================================================

def test_delete_stock_success():

    rows = get_all_stocks(TEST_TABLE)

    stock_id = rows[0]["id"]

    response = delete_stock(TEST_TABLE, stock_id)

    assert response["status"] == "success"


def test_delete_nonexistent_stock():

    response = delete_stock(TEST_TABLE, 999999)

    # Current code still returns success
    assert response["status"] == "success"


def test_delete_invalid_table():

    with pytest.raises(Exception):
        delete_stock("ghost_table", 1)


# =====================================================
# EDGE CASE TESTS
# =====================================================

def test_extremely_long_company_name():

    long_name = "A" * 10000

    response = add_stock(
        table_name=TEST_TABLE,
        company_name=long_name,
        symbol="LONG",
        buy_price=100,
        quantity=1,
        buy_date="2026-05-19"
    )

    assert response["status"] == "success"


def test_null_company_name():

    with pytest.raises(Exception):
        add_stock(
            table_name=TEST_TABLE,
            company_name=None,
            symbol="NULL",
            buy_price=100,
            quantity=1,
            buy_date="2026-05-19"
        )


def test_invalid_buy_price_type():

    with pytest.raises(Exception):
        add_stock(
            table_name=TEST_TABLE,
            company_name="Apple",
            symbol="AAPL",
            buy_price="INVALID",
            quantity=1,
            buy_date="2026-05-19"
        )


def test_invalid_quantity_type():

    with pytest.raises(Exception):
        add_stock(
            table_name=TEST_TABLE,
            company_name="Apple",
            symbol="AAPL",
            buy_price=100,
            quantity="INVALID",
            buy_date="2026-05-19"
        )


def test_invalid_date_format():

    response = add_stock(
        table_name=TEST_TABLE,
        company_name="DateTest",
        symbol="DT",
        buy_price=100,
        quantity=1,
        buy_date="banana-date"
    )

    # Current code allows invalid date strings
    assert response["status"] == "success"