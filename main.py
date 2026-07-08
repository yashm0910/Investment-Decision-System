from fastmcp import FastMCP

from db import (
    initialize_database,
    create_portfolio_table,
    add_stock,
    get_all_stocks,
    delete_stock,
    update_stock
)

from analysis_engine import analyze_stock, analyze_market
from market_interpretation_layer import interpret_stock_context
from situation_engine import (
    analyze_stock_situation
)
from research_agent_codebase import run_research_agent
from decision_engine.decision_engine import technical_decision_engine
from symbol_resolver import resolve_symbol


mcp = FastMCP("Portfolio MCP Server")


# ----------------------------------
# INITIALIZE DATABASE
# ----------------------------------

initialize_database()


# ----------------------------------
# CREATE USER TABLE
# ----------------------------------

@mcp.tool()
def create_user_portfolio(username: str):

    table_name = f"{username.lower()}_portfolio"

    return create_portfolio_table(table_name)


# ----------------------------------
# ADD STOCK
# ----------------------------------

@mcp.tool()
def add_stock_to_portfolio(
    username: str,
    company_name: str,
    buy_price: float,
    quantity: int,
    buy_date: str,
    symbol: str = ""
):

    table_name = f"{username.lower()}_portfolio"

    return add_stock(
        table_name=table_name,
        company_name=company_name,
        buy_price=buy_price,
        quantity=quantity,
        buy_date=buy_date,
        symbol=symbol
    )


# ----------------------------------
# VIEW PORTFOLIO
# ----------------------------------

@mcp.tool()
def view_portfolio(username: str):

    table_name = f"{username.lower()}_portfolio"

    return get_all_stocks(table_name)


# ----------------------------------
# DELETE STOCK
# ----------------------------------

@mcp.tool()
def remove_stock(
    username: str,
    stock_id: int
):

    table_name = f"{username.lower()}_portfolio"

    return delete_stock(table_name, stock_id)


# ----------------------------------
# UPDATE STOCK
# ----------------------------------

@mcp.tool()
def modify_stock(
    username: str,
    stock_id: int,
    company_name: str,
    symbol: str,
    buy_price: float,
    quantity: int,
    buy_date: str
):

    table_name = f"{username.lower()}_portfolio"

    return update_stock(
        table_name=table_name,
        stock_id=stock_id,
        company_name=company_name,
        symbol=symbol,
        buy_price=buy_price,
        quantity=quantity,
        buy_date=buy_date
    )
    
# -----------------------------------
# STOCK RESOLVER TOOL
# -----------------------------------
@mcp.tool()
def resolve_company_symbol(query: str) -> dict:
    """
    Resolve a company name or ticker query to a Yahoo Finance stock symbol.

    """
    return resolve_symbol(query)

# -----------------------------------
# MARKET ANALYSIS TOOL
# -----------------------------------

@mcp.tool()
def analyze_stock_price(symbol: str):

    """
    Analyze stock market trend and momentum
    using EMA + RSI indicators.
    """

    return analyze_stock(symbol)

@mcp.tool()
def analyze_market_environment(market: str):
    

    return analyze_market(market)


# =========== Overall Market Interpretation ===========

@mcp.tool()
def get_stock_market_context(
    symbol: str
):
    return interpret_stock_context(symbol)

@mcp.tool()
def analyze_stock_situation_tool(
    symbol: str
):

    return analyze_stock_situation(symbol)

@mcp.tool()
def run_research(
    query:str
):
    return run_research_agent(query)

@mcp.tool()
def technical_decision_tool(symbol: str):
    """
    Technical-only confidence tool.

    Expects output from analyze_stock_situation_tool().
    """

    stock_situation = analyze_stock_situation_tool(symbol)

    return technical_decision_engine(stock_situation)



# ----------------------------------
# RUN MCP SERVER
# ----------------------------------

if __name__ == "__main__":
    mcp.run()