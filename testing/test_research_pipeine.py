import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest

import research_agent_codebase as rag


# ------------------------------------------------------
# Fixtures
# ------------------------------------------------------

@pytest.fixture
def temp_store(tmp_path, monkeypatch):
    """
    Redirect research_store to a temporary folder.
    """
    monkeypatch.setattr(
        rag,
        "RESEARCH_STORE_DIR",
        tmp_path / "research_store",
    )

    return tmp_path


@pytest.fixture
def dummy_summary():
    return rag.ResearchSummary(
        company="Microsoft",
        overall_sentiment="positive",
        positive_catalysts=["Azure"],
        negative_catalysts=[],
        key_risks=[],
        opportunities=["AI"],
        final_reasoning="Positive outlook",
    )


# ------------------------------------------------------
# Empty query
# ------------------------------------------------------

def test_empty_query():

    result = rag.run_research_agent("")

    assert result["ok"] is False
    assert result["cache_used"] is False


# ------------------------------------------------------
# Cancel
# ------------------------------------------------------

def test_cancel(monkeypatch):

    monkeypatch.setattr(
        rag,
        "resolve_entity",
        lambda q: "Microsoft",
    )

    result = rag.run_research_agent(
        "Microsoft",
        repo_action="cancel",
    )

    assert result["cancelled"] is True
    assert result["repo_action"] == "cancel"


# ------------------------------------------------------
# Refresh path
# ------------------------------------------------------

def test_refresh_pipeline(
    monkeypatch,
    temp_store,
    dummy_summary,
):

    monkeypatch.setattr(
        rag,
        "resolve_entity",
        lambda q: "Microsoft",
    )

    monkeypatch.setattr(
        rag,
        "research_articles",
        lambda q, c: [],
    )

    monkeypatch.setattr(
        rag,
        "rank_articles",
        lambda a, c: [],
    )

    monkeypatch.setattr(
        rag,
        "analyze_articles",
        lambda c, r: [],
    )

    monkeypatch.setattr(
        rag,
        "build_research_summary",
        lambda c, a: dummy_summary,
    )

    result = rag.run_research_agent(
        "Microsoft AI",
        repo_action="refresh",
    )

    assert result["ok"] is True

    assert result["repo_action"] == "refresh"

    assert result["cache_used"] is False

    assert Path(result["repo_latest_path"]).exists()


# ------------------------------------------------------
# Cache Reuse
# ------------------------------------------------------

def test_cache_reuse(
    monkeypatch,
    temp_store,
    dummy_summary,
):

    monkeypatch.setattr(
        rag,
        "resolve_entity",
        lambda q: "Microsoft",
    )

    monkeypatch.setattr(
        rag,
        "research_articles",
        lambda q, c: [],
    )

    monkeypatch.setattr(
        rag,
        "rank_articles",
        lambda a, c: [],
    )

    monkeypatch.setattr(
        rag,
        "analyze_articles",
        lambda c, r: [],
    )

    monkeypatch.setattr(
        rag,
        "build_research_summary",
        lambda c, a: dummy_summary,
    )

    rag.run_research_agent(
        "Microsoft AI",
        repo_action="refresh",
    )

    result = rag.run_research_agent(
        "Microsoft AI",
        repo_action="auto",
    )

    assert result["ok"]

    assert result["repo_action"] == "reuse"

    assert result["cache_used"] is True


# ------------------------------------------------------
# Different company forces refresh
# ------------------------------------------------------

def test_different_company_refresh(
    monkeypatch,
    temp_store,
    dummy_summary,
):

    companies = ["Microsoft", "Apple"]

    def fake_resolve(_):
        return companies.pop(0)

    monkeypatch.setattr(
        rag,
        "resolve_entity",
        fake_resolve,
    )

    monkeypatch.setattr(
        rag,
        "research_articles",
        lambda q, c: [],
    )

    monkeypatch.setattr(
        rag,
        "rank_articles",
        lambda a, c: [],
    )

    monkeypatch.setattr(
        rag,
        "analyze_articles",
        lambda c, r: [],
    )

    monkeypatch.setattr(
        rag,
        "build_research_summary",
        lambda c, a: dummy_summary,
    )

    rag.run_research_agent(
        "Microsoft",
        repo_action="refresh",
    )

    result = rag.run_research_agent(
        "Apple",
        repo_action="auto",
    )

    assert result["repo_action"] == "refresh"


# ------------------------------------------------------
# History File Created
# ------------------------------------------------------

def test_history_file_created(
    monkeypatch,
    temp_store,
    dummy_summary,
):

    monkeypatch.setattr(
        rag,
        "resolve_entity",
        lambda q: "Microsoft",
    )

    monkeypatch.setattr(
        rag,
        "research_articles",
        lambda q, c: [],
    )

    monkeypatch.setattr(
        rag,
        "rank_articles",
        lambda a, c: [],
    )

    monkeypatch.setattr(
        rag,
        "analyze_articles",
        lambda c, r: [],
    )

    monkeypatch.setattr(
        rag,
        "build_research_summary",
        lambda c, a: dummy_summary,
    )

    result = rag.run_research_agent(
        "Microsoft",
        repo_action="refresh",
    )

    history_dir = (
        Path(result["repo_company_dir"])
        / "history"
    )

    files = list(history_dir.glob("*.json"))

    assert len(files) == 1


# ------------------------------------------------------
# Return Structure
# ------------------------------------------------------

def test_response_structure(
    monkeypatch,
    temp_store,
    dummy_summary,
):

    monkeypatch.setattr(
        rag,
        "resolve_entity",
        lambda q: "Microsoft",
    )

    monkeypatch.setattr(
        rag,
        "research_articles",
        lambda q, c: [],
    )

    monkeypatch.setattr(
        rag,
        "rank_articles",
        lambda a, c: [],
    )

    monkeypatch.setattr(
        rag,
        "analyze_articles",
        lambda c, r: [],
    )

    monkeypatch.setattr(
        rag,
        "build_research_summary",
        lambda c, a: dummy_summary,
    )

    result = rag.run_research_agent(
        "Microsoft",
        repo_action="refresh",
    )

    required = {
        "ok",
        "query",
        "resolved_company",
        "repo_action",
        "cache_used",
        "cache_message",
        "repo_latest_path",
        "repo_company_dir",
        "research_summary",
    }

    assert required.issubset(result.keys())