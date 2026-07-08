from __future__ import annotations

from typing import Any

from .schemas import DecisionConfidence, ToolResponse
from .stock_reasoner import normalize_stock_situation, build_evidence_vectors
from .confidence_math import normalize_confidence


def technical_decision_engine(stock_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Technical-only confidence engine.

    Input:
        output from analyze_stock_situation_tool()

    Output:
        MCP-friendly dict with status/code/message/data
    """
    try:
        situation = normalize_stock_situation(stock_payload)

        evidence, reasons = build_evidence_vectors(situation)

        raw_buy = float(evidence[0])
        raw_hold = float(evidence[1])
        raw_sell = float(evidence[2])

        confidence = normalize_confidence(raw_buy, raw_hold, raw_sell)

        dominant_action = max(confidence, key=confidence.get).upper()

        result = DecisionConfidence(
            buy=confidence["buy"],
            hold=confidence["hold"],
            sell=confidence["sell"],
            dominant_action=dominant_action,  # type: ignore[arg-type]
            regime=situation.market_regime,
            reasons=reasons,
            raw_scores={
                "buy": round(raw_buy, 2),
                "hold": round(raw_hold, 2),
                "sell": round(raw_sell, 2),
            },
        )

        return ToolResponse(
            status="success",
            code=200,
            message="Technical confidence generated successfully",
            data=result.model_dump(),
        ).model_dump()

    except (TypeError, ValueError) as e:
        return ToolResponse(
            status="error",
            code=400,
            message=str(e),
            data=None,
        ).model_dump()

    except Exception as e:
        return ToolResponse(
            status="error",
            code=500,
            message=f"Unexpected technical decision error: {e}",
            data=None,
        ).model_dump()