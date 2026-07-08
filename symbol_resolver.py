from __future__ import annotations

import re
from typing import Any

import yfinance as yf

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-^=]{0,14}$")


def _is_valid_symbol(symbol: str) -> bool:
    """Check if a symbol actually resolves to price data on yfinance."""
    try:
        return not yf.Ticker(symbol).history(period="5d", interval="1d").empty
    except Exception:
        return False


def resolve_symbol(query: str) -> dict[str, Any]:
    query = (query or "").strip()

    if not query:
        return {
            "ok": False,
            "query": query,
            "symbol": None,
            "company_name": None,
            "source": "empty_query"}

    # Case 1: query itself looks like a ticker (e.g. "AAPL")
    token = query.split()[0].upper()
    if len(query.split()) == 1 and SYMBOL_PATTERN.fullmatch(token) and _is_valid_symbol(token):
        return {
            "ok": True,
            "query": query,
            "symbol": token,
            "company_name": None,
            "source": "direct_symbol"}

    # Case 2: fall back to yfinance search (e.g. "Apple Inc")
    try:
        quotes = getattr(yf.Search(query, max_results=10, news_count=0), "quotes", []) or []
    except Exception:
        quotes = []

    for item in quotes:
        symbol = str(item.get("symbol") or "").strip().upper()
        if symbol and _is_valid_symbol(symbol):
            name = str(item.get("shortname") or item.get("longname") or "").strip()
            return {
                "ok": True,
                "query": query,
                "symbol": symbol,
                "company_name": name or None,
                "source": "yfinance_search"}

    return {
        "ok": False,
        "query": query,
        "symbol": None,
        "company_name": None,
        "source": "not_found"}