
---

# Investment Decision Support System

 An MCP-powered investment assistant for portfolio management, technical market analysis, financial research, and explainable investment decision support.

---

# Overview

The Investment Decision Support System is an MCP (Model Context Protocol) server that enables AI assistants such as Claude to perform deterministic investment-related tasks through specialized tools instead of relying solely on language model reasoning.

The system combines portfolio management, technical market analysis, financial news research, and explainable decision support into a unified tool ecosystem. Rather than generating investment suggestions directly from an LLM, it delegates calculations, data retrieval, and analysis to deterministic Python modules while allowing the language model to orchestrate tools and explain results.

This architecture improves consistency, reduces hallucination risk for mathematical computations, and makes investment recommendations transparent and reproducible.

---

# Motivation

Many AI-powered stock assistants generate investment suggestions directly from language models. While this approach can produce fluent responses, it often lacks consistency for tasks that require deterministic computation such as technical indicators, portfolio calculations, and structured financial analysis.

The motivation behind this project was to build a system where:

* Mathematical calculations are performed by deterministic algorithms rather than probabilistic language generation.
* AI is responsible for reasoning, orchestration, and explanation instead of numerical computation.
* Every recommendation is supported by structured analysis rather than opaque AI-generated predictions.

Instead of creating another "AI stock predictor," this project focuses on providing explainable decision support backed by reproducible calculations and structured research.

---

# Why MCP?

This project uses the **Model Context Protocol (MCP)** instead of exposing a traditional REST API because the primary consumer is an AI model rather than another software application.

MCP enables:

* **Dynamic tool discovery** – Claude automatically discovers available tools and selects the appropriate one based on the user's request without hardcoded routing logic.
* **AI-native integration** – Instead of manually wiring individual API endpoints to prompts, the model interacts with self-described tools through a standardized protocol, allowing reasoning and tool execution to work together naturally.

This makes the system significantly easier to extend as new investment tools are added.

---

# Who Is This For?

The system is designed for users who want structured investment assistance rather than automated trading.

Typical users include:

* Beginners building their first stock portfolio.
* Long-term investors researching companies before investing.
* Users seeking technical analysis without manually calculating indicators.
* Investors wanting explainable reasoning behind market observations instead of black-box AI predictions.
* Anyone looking for a single interface that combines portfolio management, market analysis, and financial research.

The project is **not** intended to replace financial advisors or execute trades automatically. It serves as a decision-support system that helps users make more informed investment decisions.

---

# Core Capabilities

### Portfolio Management

* Create user portfolios
* Add, update, and remove stock holdings
* View current portfolio

---

### Technical Market Analysis

* RSI analysis
* EMA trend analysis
* Market trend evaluation
* Technical situation assessment
* Market interpretation layer

---

### Financial Research

* Resolve company names and stock symbols
* Generate intelligent financial search queries
* Retrieve recent financial news
* Rank articles by investment relevance
* AI-powered article analysis
* Explainable research summaries
* One-hour intelligent research cache

---

### Explainable Decision Support

* Technical decision engine
* Confidence-based analysis
* Structured reasoning
* Transparent investment explanations
* Modular decision pipeline

---

# MCP Tools

| Tool                           | Purpose                                        |
| ------------------------------ | ---------------------------------------------- |
| `create_user_portfolio`        | Create a portfolio for a user                  |
| `add_stock_to_portfolio`       | Add a stock holding                            |
| `view_portfolio`               | Display portfolio holdings                     |
| `modify_stock`                 | Update an existing holding                     |
| `remove_stock`                 | Delete a holding                               |
| `resolve_company_symbol`       | Resolve company names to ticker symbols        |
| `analyze_stock_price`          | Technical analysis using EMA & RSI             |
| `analyze_market_environment`   | Analyze overall market conditions              |
| `get_stock_market_context`     | Combine stock and market interpretation        |
| `analyze_stock_situation_tool` | Generate structured technical context          |
| `run_research`                 | Perform financial research and summarization   |
| `technical_decision_tool`      | Produce explainable technical decision support |


---
# Current Scope

The current version focuses on deterministic technical analysis and explainable financial research while using Claude as the reasoning and orchestration layer.

Future versions will extend the system by combining technical analysis with financial research to produce a unified, evidence-based investment decision engine.

---

# Try It Yourself

The deployed MCP server can be connected directly to Claude Desktop.

### Live MCP Endpoint

> https://thundering-olive-mongoose.fastmcp.app/mcp
```
 Connect to Claude Desktop

1. Open **Claude Desktop**.
2. Navigate to **Profile & Settings**.
3. Open **Connectors**.
4. Click **Add Connector**.
5. Choose **Add Custom Connector**.
6. Paste the deployed MCP server URL.
7. Save the connector.
8. Restart Claude Desktop.
9. The Investment Decision Support System tools will now be available automatically.

---
