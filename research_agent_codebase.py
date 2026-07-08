from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict
from urllib.parse import urlparse

from dateutil import parser as date_parser
from ddgs import DDGS
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, Field
from datetime import timedelta
from uuid import uuid4
from logger import get_logger

CACHE_TTL_SECONDS = 3600  
RESEARCH_STORE_DIR = Path("research_store")
PIPELINE_VERSION = "v2.0"

MAX_ARTICLES = 30
TOP_K = 10
DDG_RESULTS_PER_QUERY = 3
PREVIEW_CHARS = 280

DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"
LLM_MODEL = os.getenv("RESEARCH_LLM_MODEL", DEFAULT_LLM_MODEL).strip() or DEFAULT_LLM_MODEL
logger = get_logger("research_agent")

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
if not GROQ_API_KEY:
    raise RuntimeError("Set GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)


# =======================
# Schemas
# =======================

class Article(BaseModel):
    """Compact article preview stored in cache; not full article text."""
    title: str
    url: str
    source: str
    published_date: str
    content: str
    relevance_score: float | None = None


class ArticleAnalysis(BaseModel):
    title: str
    summary: str
    stock_impact: str
    sentiment: str
    importance_score: int = Field(ge=1, le=10)
    reasoning: str


class RankedArticle(BaseModel):
    title: str
    url: str
    source: str
    published_date: str
    content: str
    decision_value_score: float = Field(ge=0.0, le=10.0)
    recency_score: float = Field(ge=0.0, le=10.0)
    impact_score: float = Field(ge=0.0, le=10.0)
    novelty_score: float = Field(ge=0.0, le=10.0)
    evidence_score: float = Field(ge=0.0, le=10.0)
    reasoning: str


class ResearchSummary(BaseModel):
    company: str
    overall_sentiment: str
    positive_catalysts: list[str]
    negative_catalysts: list[str]
    key_risks: list[str]
    opportunities: list[str]
    final_reasoning: str


class ResearchState(TypedDict, total=False):
    query: str
    resolved_company: str
    all_articles: list[Article]
    top_articles: list[RankedArticle]
    articles_analyzed: list[ArticleAnalysis]
    research_summary: ResearchSummary

    repo_hit: bool
    repo_action: Literal["reuse", "refresh", "cancel", "auto"]
    repo_company_dir: str
    repo_latest_path: str
    cached_research: dict[str, Any]
    cache_match_score: float


# =======================
# Utilities
# =======================

def _truncate(text: str, limit: int = PREVIEW_CHARS) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _strip_code_fences(raw: str) -> str:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE | re.DOTALL)
        raw = re.sub(r"\s*```$", "", raw, flags=re.DOTALL)
    return raw.strip()


def _extract_json(raw: str):
    raw = _strip_code_fences(raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to isolate the first object or array conservatively.
    first_obj = raw.find("{")
    last_obj = raw.rfind("}")
    if first_obj != -1 and last_obj != -1 and last_obj > first_obj:
        candidate = raw[first_obj:last_obj + 1].strip()
        try:
            return json.loads(candidate)
        except Exception:
            pass

    first_arr = raw.find("[")
    last_arr = raw.rfind("]")
    if first_arr != -1 and last_arr != -1 and last_arr > first_arr:
        candidate = raw[first_arr:last_arr + 1].strip()
        return json.loads(candidate)

    raise json.JSONDecodeError("Unable to extract JSON", raw, 0)


def _company_slug(company: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (company or "").lower()).strip("_")
    return slug or "unknown"


def _company_dir(company: str) -> Path:
    return RESEARCH_STORE_DIR / _company_slug(company)


def _latest_path(company: str) -> Path:
    return _company_dir(company) / "latest.json"


def _history_path(company: str, run_ts: str) -> Path:
    return _company_dir(company) / "history" / f"{run_ts}.json"


def _to_jsonable(obj):
    if obj is None:
        return None
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    return obj


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    tmp.replace(path)


def _safe_company_name(data) -> str:
    if isinstance(data, dict):
        return (data.get("company") or "").strip()
    if isinstance(data, str):
        return data.strip()
    return ""


def _flatten_llm_list_response(data) -> list[str]:
    if isinstance(data, list):
        return [str(x).strip() for x in data if str(x).strip()]
    if isinstance(data, dict):
        vals = data.get("queries")
        if isinstance(vals, list):
            return [str(x).strip() for x in vals if str(x).strip()]
    return []


def _tokenize_query(text: str) -> set[str]:
    stopwords = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "by", "from", "at", "is", "are", "was", "were", "be", "been", "being",
        "latest", "news", "today", "current", "update", "updates", "about",
        "what", "why", "how", "when", "where", "who", "will", "did", "do", "does",
        "company", "stock", "shares", "share", "market",
    }
    tokens = re.findall(r"[a-z0-9]+", _normalize_text(text))
    return {t for t in tokens if len(t) > 2 and t not in stopwords}


def _jaccard_similarity(a: str, b: str) -> float:
    sa = _tokenize_query(a)
    sb = _tokenize_query(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _query_cache_match_score(query: str, cached: dict[str, Any]) -> float:
    cached_query = str(cached.get("query") or "")
    cached_company = str(cached.get("company") or "")
    current_company = str(cached.get("current_company") or "")

    q_score = _jaccard_similarity(query, cached_query)
    c_score = 1.0 if _normalize_text(cached_company) == _normalize_text(current_company) and current_company else 0.0
    return round((0.8 * q_score) + (0.2 * c_score), 3)


# =======================
# LLM helpers
# =======================

def _llm_chat_json(prompt: str, *, system: str | None = None, temperature: float = 0.1):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=temperature,
    )
    raw = resp.choices[0].message.content or ""
    return _extract_json(raw.strip())


def _resolve_company_from_query(query: str) -> str:
    prompt = f"""
You are resolving the company mentioned in a financial research query.

Return ONLY a JSON object like:
{{"company":"Microsoft"}}

Rules:
- Map symbols, founder names, products, projects, or company nicknames to the company.
- Return the most likely company.
- Do not explain.
- Do not return markdown.

User query: {query}
"""
    data = _llm_chat_json(prompt, temperature=0.1)
    company = _safe_company_name(data)
    if not company:
        raise ValueError(f"Could not resolve company from query: {query}")
    return company


def _generate_search_queries(query: str, company: str) -> list[str]:
    base_queries = [
        query,
        f"{company} latest news",
        f"{company} earnings",
        f"{company} guidance",
        f"{company} AI developments",
        f"{company} regulation",
        f"{company} lawsuit",
        f"{company} probe",
        f"{company} partnerships",
        f"{company} acquisitions",
        f"{company} product launch",
    ]

    llm_prompt = f"""
You are helping build search queries for a financial research agent.

Given the user query below, generate 6 short web search queries.

Rules:
- Focus on the resolved company and likely relevant subtopics.
- Prefer real company-moving topics: earnings, guidance, regulation, lawsuits, products, strategy, partnerships, acquisitions, AI, management.
- Avoid vague queries.
- Return ONLY a JSON array of strings.
- No markdown, no explanation.

User query: {query}
Resolved company: {company}
"""
    try:
        llm_queries = _flatten_llm_list_response(
            _llm_chat_json(
                llm_prompt,
                system="You generate focused financial search queries.",
                temperature=0.1,
            )
        )
        base_queries.extend(llm_queries)
    except Exception as e:
        # OLD: print(f"[research_articles] LLM query generation failed, using fallback queries only: {e}")
        logger.warning("LLM query generation failed, using fallback queries only: %s", e)

    seen: set[str] = set()
    queries: list[str] = []
    for q in base_queries:
        q = (q or "").strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            queries.append(q)

    # Hard cap to reduce DDG churn.
    return queries[:10]


def _search_ddg_query(ddgs, query: str, *, max_results: int, retries: int = 2):
    last_err: Exception | None = None

    for attempt in range(retries + 1):
        try:
            news_results = list(ddgs.news(query, max_results=max_results))
            if news_results:
                return news_results

            text_results = list(ddgs.text(query, max_results=max_results, safesearch="moderate"))
            if text_results:
                return text_results

            return []
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
            else:
                # OLD: print(f"[research_articles] DDG search failed for query='{query}': {e}")
                logger.error("DDG search failed | query=%s | error=%s", query, e)

    if last_err:
        return []
    return []


def _parse_ddg_result(r: dict[str, Any]) -> Article | None:
    title = (r.get("title") or "").strip()
    url = (r.get("href") or r.get("url") or "").strip()
    body = (r.get("body") or r.get("snippet") or "").strip()

    if not title or not url:
        return None

    source = urlparse(url).netloc.replace("www.", "") if url else "duckduckgo"
    published_date = r.get("date") or datetime.utcnow().date().isoformat()

    return Article(
        title=title,
        url=url,
        source=source or "duckduckgo",
        published_date=published_date,
        content=_truncate(body if body else title, PREVIEW_CHARS),
        relevance_score=None,
    )


# =======================
# Pipeline steps
# =======================

def resolve_entity(query: str) -> str:
    query = (query or "").strip()
    if not query:
        raise ValueError("query is empty")
    return _resolve_company_from_query(query)


def research_articles(query: str, company: str) -> list[Article]:
    query = (query or "").strip()
    company = (company or "").strip()

    if not query:
        raise ValueError("query is empty in research_articles()")
    if not company:
        raise ValueError("company is empty in research_articles()")

    queries = _generate_search_queries(query, company)
    results: list[Article] = []

    with DDGS() as ddgs:
        for q in queries:
            raw_results = _search_ddg_query(ddgs, q, max_results=DDG_RESULTS_PER_QUERY, retries=2)
            for r in raw_results:
                if not isinstance(r, dict):
                    continue
                article = _parse_ddg_result(r)
                if article:
                    results.append(article)

    deduped: list[Article] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for item in results:
        u = item.url.rstrip("/").lower()
        t = _normalize_text(item.title)
        if u in seen_urls or t in seen_titles:
            continue
        seen_urls.add(u)
        seen_titles.add(t)
        deduped.append(item)
        if len(deduped) >= MAX_ARTICLES:
            break

    if not deduped:
        raise ValueError(f"No articles found for query='{query}', company='{company}'. Used queries: {queries}")

    return deduped


def _score_recency(published_date: str) -> float:
    try:
        dt = date_parser.parse(published_date)
        days_old = (datetime.utcnow() - dt.replace(tzinfo=None)).days
        if days_old <= 1:
            return 10.0
        if days_old <= 3:
            return 9.0
        if days_old <= 7:
            return 8.0
        if days_old <= 14:
            return 7.0
        if days_old <= 30:
            return 6.0
        if days_old <= 90:
            return 4.0
        return 2.0
    except Exception:
        return 3.0


def _score_impact(article: Article, company: str) -> tuple[float, list[str]]:
    text = _normalize_text(f"{article.title} {article.content}")
    company_norm = _normalize_text(company)
    reasons: list[str] = []
    score = 3.0

    high_impact_keywords = [
        "earnings", "guidance", "forecast", "capex", "investment",
        "regulation", "antitrust", "lawsuit", "probe", "investigation",
        "acquisition", "merger", "partnership", "launch", "product",
        "debut", "restructuring", "layoff", "ceo", "management", "margin",
        "revenue", "profit", "free cash flow", "openai", "ai chip", "data center",
    ]

    if company_norm and company_norm in text:
        score += 1.5
        reasons.append("direct company mention")

    for kw in high_impact_keywords:
        if kw in text:
            score += 0.55
            reasons.append(f"keyword:{kw}")

    if any(x in text for x in ["earnings", "guidance", "forecast"]):
        score += 1.0
        reasons.append("earnings/guidance content")

    if any(x in text for x in ["regulation", "antitrust", "lawsuit", "probe", "investigation"]):
        score += 1.2
        reasons.append("regulatory/legal impact")

    if any(x in text for x in ["acquisition", "merger", "partnership"]):
        score += 0.9
        reasons.append("strategic event")

    if any(x in text for x in ["launch", "product", "platform", "model", "infrastructure"]):
        score += 0.7
        reasons.append("product/strategy development")

    # Penalize likely commentary slightly.
    if any(x in text for x in ["opinion", "analysis", "commentary", "view"]):
        score -= 0.7
        reasons.append("commentary penalty")

    return min(max(score, 0.0), 10.0), reasons


def _score_novelty(article: Article, seen_titles: set[str], seen_urls: set[str]) -> float:
    title = _normalize_text(article.title)
    url = (article.url or "").rstrip("/").lower()

    if url in seen_urls:
        return 1.0
    if title in seen_titles:
        return 2.0
    return 8.0


def _score_evidence(article: Article) -> float:
    text = _normalize_text(f"{article.title} {article.content}")
    score = 4.0

    evidence_keywords = [
        "reported", "announced", "filed", "sec", "earnings",
        "guidance", "revenue", "profit", "margin", "cash flow",
        "capex", "contract", "deal", "launch", "official", "ceo",
        "board", "filing", "regulator", "court", "reuters", "ap", "bloomberg",
    ]

    if any(kw in text for kw in evidence_keywords):
        score += 2.0

    if re.search(r"\b\d+(?:\.\d+)?%?\b", text):
        score += 0.75
    if re.search(r"\b\d{4}\b", text):
        score += 0.25

    if any(kw in text for kw in ["analysis", "opinion", "commentary", "view"]):
        score -= 1.5

    if len(article.content or "") > 220:
        score += 0.5
    elif len(article.content or "") < 120:
        score -= 0.5

    return max(0.0, min(score, 10.0))


def rank_articles(articles: list[Article], company: str) -> list[RankedArticle]:
    if not articles:
        return []

    weighted_articles: list[RankedArticle] = []
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()

    w_recency = 0.25
    w_impact = 0.40
    w_novelty = 0.15
    w_evidence = 0.20

    for idx, article in enumerate(articles, start=1):
        try:
            recency_score = _score_recency(article.published_date)
            impact_score, impact_reasons = _score_impact(article, company)
            novelty_score = _score_novelty(article, seen_titles, seen_urls)
            evidence_score = _score_evidence(article)

            decision_value_score = round(
                (
                    w_recency * recency_score
                    + w_impact * impact_score
                    + w_novelty * novelty_score
                    + w_evidence * evidence_score
                ),
                2,
            )

            reasoning_parts = [
                f"recency={recency_score:.1f}/10",
                f"impact={impact_score:.1f}/10",
                f"novelty={novelty_score:.1f}/10",
                f"evidence={evidence_score:.1f}/10",
            ]
            if impact_reasons:
                reasoning_parts.append("impact_signals=" + ", ".join(impact_reasons[:5]))

            weighted_articles.append(
                RankedArticle(
                    title=article.title,
                    url=article.url,
                    source=article.source,
                    published_date=article.published_date,
                    content=article.content,
                    decision_value_score=decision_value_score,
                    recency_score=round(recency_score, 2),
                    impact_score=round(impact_score, 2),
                    novelty_score=round(novelty_score, 2),
                    evidence_score=round(evidence_score, 2),
                    reasoning=" | ".join(reasoning_parts),
                )
            )

            seen_titles.add(_normalize_text(article.title))
            seen_urls.add((article.url or "").rstrip("/").lower())

        except Exception as e:
            # OLD: print(f"[rank_articles] Skipping article #{idx} due to error: {e}")
            logger.warning("Skipping article #%s during ranking: %s", idx, e)

    weighted_articles.sort(key=lambda x: x.decision_value_score, reverse=True)
    return weighted_articles[:TOP_K]


def analyze_articles(company: str, top_articles: list[RankedArticle]) -> list[ArticleAnalysis]:
    if not top_articles:
        return []

    prompt_items = []
    for i, art in enumerate(top_articles, start=1):
        prompt_items.append(
            f"""
{i}. TITLE: {art.title}
   SOURCE: {art.source}
   DATE: {art.published_date}
   PREVIEW: {art.content}
   RANK REASONING: {art.reasoning}
""".strip()
        )

    prompt = f"""
You are a financial analyst.

Analyze each article for {company} and return ONLY valid JSON.

Requirements:
- Return a JSON array.
- One object per input article.
- Preserve the title exactly.
- Keep summaries concise but factual.
- Use the following schema for each object:
  {{
    "title": "...",
    "summary": "...",
    "stock_impact": "...",
    "sentiment": "positive|negative|neutral",
    "importance_score": 1-10,
    "reasoning": "..."
  }}

Articles:
{chr(10).join(prompt_items)}
"""

    try:
        data = _llm_chat_json(prompt, temperature=0.1)
        if not isinstance(data, list):
            raise ValueError("Article analysis LLM did not return a JSON list.")

        analyses: list[ArticleAnalysis] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                analyses.append(ArticleAnalysis(**item))
            except Exception as e:
                # OLD: print(f"[analyze_articles] Skipping invalid analysis item: {e}")
                logger.warning("Skipping invalid analysis item for company=%s: %s", company, e)

        # Deterministic fallback for any missing items.
        if len(analyses) < len(top_articles):
            seen_titles = {a.title for a in analyses}
            for art in top_articles:
                if art.title in seen_titles:
                    continue
                analyses.append(
                    ArticleAnalysis(
                        title=art.title,
                        summary=_truncate(art.content, 180),
                        stock_impact="Potentially relevant to the investment thesis.",
                        sentiment="neutral",
                        importance_score=max(1, min(10, int(round(art.decision_value_score)))),
                        reasoning=art.reasoning,
                    )
                )

        return analyses[:TOP_K]

    except Exception as e:
        # OLD: print(f"[analyze_articles] LLM analysis failed, using fallback: {e}")
        logger.error("LLM analysis failed for company=%s, using fallback: %s", company, e)
        return [
            ArticleAnalysis(
                title=art.title,
                summary=_truncate(art.content, 180),
                stock_impact="Potentially relevant to the investment thesis.",
                sentiment="neutral",
                importance_score=max(1, min(10, int(round(art.decision_value_score)))),
                reasoning=art.reasoning,
            )
            for art in top_articles
        ]


def build_research_summary(company: str, analyses: list[ArticleAnalysis]) -> ResearchSummary:
    if not analyses:
        return ResearchSummary(
            company=company or "Unknown",
            overall_sentiment="neutral",
            positive_catalysts=[],
            negative_catalysts=[],
            key_risks=[],
            opportunities=[],
            final_reasoning="No sufficiently strong articles were available for synthesis.",
        )

    prompt_items = []
    for i, a in enumerate(analyses, start=1):
        prompt_items.append(
            f"""
{i}. TITLE: {a.title}
   SUMMARY: {a.summary}
   STOCK IMPACT: {a.stock_impact}
   SENTIMENT: {a.sentiment}
   IMPORTANCE: {a.importance_score}
   REASONING: {a.reasoning}
""".strip()
        )

    prompt = f"""
You are a portfolio analyst.

Synthesize the article analyses for {company}.
Return ONLY valid JSON matching this schema:
{{
  "company": "{company}",
  "overall_sentiment": "positive|negative|neutral",
  "positive_catalysts": ["..."],
  "negative_catalysts": ["..."],
  "key_risks": ["..."],
  "opportunities": ["..."],
  "final_reasoning": "..."
}}

Analyses:
{chr(10).join(prompt_items)}
"""

    try:
        data = _llm_chat_json(prompt, temperature=0.1)
        return ResearchSummary(**data)
    except Exception as e:
        # OLD: print(f"[build_research_summary] LLM synthesis failed, using fallback: {e}")
        logger.error("LLM synthesis failed for company=%s, using fallback: %s", company, e)
        positive = [a.title for a in analyses if a.sentiment == "positive"][:5]
        negative = [a.title for a in analyses if a.sentiment == "negative"][:5]
        return ResearchSummary(
            company=company or "Unknown",
            overall_sentiment="neutral",
            positive_catalysts=positive,
            negative_catalysts=negative,
            key_risks=negative[:3],
            opportunities=positive[:3],
            final_reasoning="Synthesized from ranked article analyses with a deterministic fallback because the final LLM synthesis failed.",
        )



# =======================
# Cache handling
# =======================
from zoneinfo import ZoneInfo

def _format_datetime(dt_string: str) -> str:
    """
    Convert UTC ISO timestamp to readable IST time.
    """

    dt = date_parser.parse(dt_string)

    dt = dt.astimezone(
        ZoneInfo("Asia/Kolkata")
    )

    return dt.strftime("%d %b %Y, %I:%M %p IST")

def _latest_payload_from_cache(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid cache format: {path}")
    return payload


def _cache_age_seconds(payload: dict[str, Any]) -> float:
    """
    Returns cache age in seconds.
    """
    last_updated = payload.get("last_updated")
    if not last_updated:
        return float("inf")

    try:
        cache_time = date_parser.parse(last_updated)
        now = datetime.utcnow()
        return (now - cache_time.replace(tzinfo=None)).total_seconds()
    except Exception:
        return float("inf")


def _cache_expires_in_seconds(payload: dict[str, Any]) -> float:
    expires_at = payload.get("expires_at")
    if not expires_at:
        return float("-inf")

    try:
        expiry_time = date_parser.parse(expires_at)
        now = datetime.utcnow()
        return (expiry_time.replace(tzinfo=None) - now).total_seconds()
    except Exception:
        return float("-inf")


def _cache_is_usable(
    query: str,
    company: str,
    payload: dict[str, Any],
    *,
    similarity_threshold: float = 0.65,
) -> tuple[bool, float]:
    cached_company = str(payload.get("company") or "")
    if _normalize_text(cached_company) != _normalize_text(company):
        return False, 0.0

    similarity = _query_cache_match_score(
        query,
        {
            **payload,
            "current_company": company,
        },
    )

    age = _cache_age_seconds(payload)
    ttl_valid = age <= CACHE_TTL_SECONDS
    usable = ttl_valid and similarity >= similarity_threshold
    return usable, similarity


def _cache_message_from_payload(payload: dict[str, Any]) -> str:
    age_minutes = max(
        0.0,
        round(_cache_age_seconds(payload) / 60.0, 1)
    )

    expires_at = payload.get("expires_at")

    if expires_at:
        readable_time = _format_datetime(expires_at)

        return (
            f"Cached research reused ({age_minutes} min old). "
            f"Fresh research available after {readable_time}."
        )

    return f"Cached research reused ({age_minutes} min old)."


def _rehydrate_cached_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "company": payload.get("company"),
        "query": payload.get("query"),
        "last_updated": payload.get("last_updated"),
        "expires_at": payload.get("expires_at"),
        "pipeline_version": payload.get("pipeline_version"),
        "repo_path": payload.get("repo_path"),
        "metrics": payload.get("metrics") or {},
        "all_articles": [Article(**x) for x in payload.get("all_articles", [])],
        "top_articles": [RankedArticle(**x) for x in payload.get("top_articles", [])],
        "articles_analyzed": [ArticleAnalysis(**x) for x in payload.get("articles_analyzed", [])],
        "research_summary": ResearchSummary(**payload["research_summary"]) if payload.get("research_summary") else None,
    }


def _serialize_payload(
    *,
    company: str,
    query: str,
    all_articles: list[Article],
    top_articles: list[RankedArticle],
    articles_analyzed: list[ArticleAnalysis],
    research_summary: ResearchSummary,
    repo_path: Path,
) -> dict[str, Any]:
    run_ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    now = datetime.utcnow()
    expiry = now + timedelta(seconds=CACHE_TTL_SECONDS)

    return {
        "company": company,
        "query": query,
        "query_signature": sorted(_tokenize_query(query)),
        "last_updated": now.isoformat() + "Z",
        "expires_at": expiry.isoformat() + "Z",
        "cache_note": "Fresh research generated. Cache valid for 1 hour.",
        "pipeline_version": PIPELINE_VERSION,
        "repo_path": str(repo_path),
        "metrics": {
            "articles_fetched": len(all_articles),
            "articles_ranked": len(top_articles),
            "articles_analyzed": len(articles_analyzed),
        },
        "all_articles": _to_jsonable(all_articles),
        "top_articles": _to_jsonable(top_articles),
        "articles_analyzed": _to_jsonable(articles_analyzed),
        "research_summary": _to_jsonable(research_summary),
        "run_timestamp": run_ts,
    }


# =======================
# Public tool entrypoint
# =======================

def run_research_agent(
    query: str,
    *,
    repo_action: Literal["auto", "reuse", "refresh", "cancel"] = "auto",
    reuse_similarity_threshold: float = 0.65,
) -> dict[str, Any]:
    """
    Main MCP-friendly entrypoint.

    repo_action:
        auto    -> reuse cache only when company matches, query similarity is high, and TTL has not expired
        reuse   -> use cache if present for the resolved company and TTL has not expired
        refresh -> ignore cache and rebuild
        cancel  -> return without running
    """
    query = (query or "").strip()
    if not query:
        return {
            "ok": False,
            "error": "query is empty",
            "cache_used": False,
            "cache_message": "No query provided.",
        }

    request_id = uuid4().hex[:8]
    logger.info("request_id=%s | start | query=%s", request_id, query)

    try:
        company = resolve_entity(query)
        logger.info("request_id=%s | resolved_company=%s", request_id, company)
        company_dir = _company_dir(company)
        latest = _latest_path(company)
        cache_hit = False
        cache_match_score = 0.0
        cached_payload: dict[str, Any] | None = None
        usable = False

        if latest.exists():
            cache_hit = True
            try:
                cached_payload = _latest_payload_from_cache(latest)
                usable, cache_match_score = _cache_is_usable(
                    query,
                    company,
                    cached_payload,
                    similarity_threshold=reuse_similarity_threshold,
                )
            except Exception as e:
                cached_payload = None
                usable = False
                cache_match_score = 0.0
                # OLD: print(f"[repo] Failed to load cache for {company}: {e}")
                logger.warning("Failed to load cache for %s: %s", company, e)

        if repo_action == "cancel":
            logger.info(
                "request_id=%s | cancelled_before_research | company=%s | cache_hit=%s",
                request_id,
                company,
                cache_hit,
            )
            return {
                "ok": True,
                "cancelled": True,
                "query": query,
                "resolved_company": company,
                "repo_hit": cache_hit,
                "repo_action": "cancel",
                "cache_used": False,
                "cache_match_score": cache_match_score,
                "cache_message": "Request cancelled before research.",
            }

        if repo_action == "reuse" or (repo_action == "auto" and usable):
            if cached_payload is None:
                raise ValueError("No reusable cache was available.")

            rehydrated = _rehydrate_cached_payload(cached_payload)
            logger.info(
                "request_id=%s | cache_reuse | company=%s | age_minutes=%.1f | score=%.3f",
                request_id,
                company,
                round(_cache_age_seconds(cached_payload) / 60.0, 1),
                cache_match_score,
            )
            return {
                "ok": True,
                "query": query,
                "resolved_company": company,
                "repo_hit": True,
                "repo_action": "reuse",
                "cache_used": True,
                "cache_age_seconds": round(_cache_age_seconds(cached_payload), 2),
                "cache_age_minutes": round(_cache_age_seconds(cached_payload) / 60.0, 1),
                "cache_valid_until": _format_datetime(
                    cached_payload["expires_at"]
                ),
                "cache_match_score": cache_match_score,
                "cache_message": _cache_message_from_payload(cached_payload),
                "repo_company_dir": str(company_dir),
                "repo_latest_path": str(latest),
                **rehydrated,
            }
            
        
        reason = []

        if cached_payload is not None:
            if _cache_age_seconds(cached_payload) > CACHE_TTL_SECONDS:
                reason.append("TTL expired")
        else:
            reason.append("cache unavailable")

        if cache_match_score < reuse_similarity_threshold:
            reason.append("query similarity below threshold")

        # OLD:
        # print(
        #     f"[CACHE] Refreshing research for {company} ({', '.join(reason)})"
        # )
        logger.info(
            "request_id=%s | refresh_cache | company=%s | reasons=%s | cache_score=%.3f",
            request_id,
            company,
            ", ".join(reason) if reason else "none",
            cache_match_score,
        )
        
        # refresh path
        logger.info("request_id=%s | stage=research_articles", request_id)
        all_articles = research_articles(query, company)

        logger.info("request_id=%s | stage=rank_articles", request_id)
        ranked = rank_articles(all_articles, company)

        logger.info("request_id=%s | stage=analyze_articles", request_id)
        analyzed = analyze_articles(company, ranked)

        logger.info("request_id=%s | stage=build_research_summary", request_id)
        summary = build_research_summary(company, analyzed)

        payload = _serialize_payload(
            company=company,
            query=query,
            all_articles=all_articles,
            top_articles=ranked,
            articles_analyzed=analyzed,
            research_summary=summary,
            repo_path=latest,
        )

        _write_json(latest, payload)

        history_file = _history_path(company, payload["run_timestamp"])
        _write_json(history_file, payload)

        logger.info(
            "request_id=%s | success | company=%s | action=refresh | cache_used=False",
            request_id,
            company,
        )

        return {
            "ok": True,
            "query": query,
            "resolved_company": company,
            "repo_hit": cache_hit,
            "repo_action": "refresh",
            "cache_used": False,
            "cache_age_seconds": 0.0,
            "cache_age_minutes": 0.0,
            "cache_match_score": cache_match_score,
            "cache_message": (
                f"Fresh research generated. "
                f"Cache valid until {_format_datetime(payload['expires_at'])}."
            ),
            "repo_company_dir": str(company_dir),
            "repo_latest_path": str(latest),
            **_rehydrate_cached_payload(payload),
        }

    except Exception as e:
        logger.exception(
            "request_id=%s | failed | query=%s | error=%s",
            request_id if 'request_id' in locals() else "unknown",
            query,
            e,
        )
        return {
            "ok": False,
            "query": query,
            "cache_used": False,
            "error": str(e),
        }


if __name__ == "__main__":
    sample_query = "current S"
    result = run_research_agent(sample_query, repo_action="auto")
    print(json.dumps(_to_jsonable(result), indent=2, ensure_ascii=False, default=str))
