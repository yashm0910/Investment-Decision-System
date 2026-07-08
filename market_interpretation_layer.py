from analysis_engine import analyze_market,analyze_stock


def determine_market(symbol: str):

    symbol = symbol.upper()

    if symbol.endswith(".NS"):
        return "nifty"

    elif symbol.endswith(".BO"):
        return "sensex"

    else:
        return "nasdaq"
    
def interpret_stock_context(
    symbol: str
):

    market = determine_market(symbol)

    stock_analysis = analyze_stock(symbol)

    market_analysis = analyze_market(market)

    return {
        "symbol": symbol,

        "market": market,

        "stock_analysis": stock_analysis,

        "market_analysis": market_analysis,

        "prompt_context": {
            "market_regime":
                market_analysis["market_regime"],

            "market_trend":
                market_analysis["trend"],

            "stock_trend":
                stock_analysis["trend_signal"],

            "stock_momentum":
                stock_analysis["momentum_signal"],

            "signals":
                stock_analysis["signals"]
        }
    }