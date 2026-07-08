import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import research_agent_codebase as rag


# ----------------------------------------------------
# Helpers
# ----------------------------------------------------

def build_payload(
    *,
    company="Microsoft",
    query="Microsoft latest AI news",
    age_minutes=10,
):
    """
    Creates a fake cache payload.
    """

    now = datetime.utcnow()

    last_updated = now - timedelta(minutes=age_minutes)
    expires_at = last_updated + timedelta(seconds=rag.CACHE_TTL_SECONDS)

    return {
        "company": company,
        "query": query,
        "last_updated": last_updated.isoformat() + "Z",
        "expires_at": expires_at.isoformat() + "Z",
        "pipeline_version": "v2",
        "metrics": {},
        "all_articles": [],
        "top_articles": [],
        "articles_analyzed": [],
        "research_summary": None,
    }


# ----------------------------------------------------
# Cache Age
# ----------------------------------------------------

def test_cache_age_recent():

    payload = build_payload(age_minutes=5)

    age = rag._cache_age_seconds(payload)

    assert age < 360


def test_cache_age_old():

    payload = build_payload(age_minutes=120)

    age = rag._cache_age_seconds(payload)

    assert age > rag.CACHE_TTL_SECONDS


def test_cache_age_invalid_timestamp():

    payload = build_payload()

    payload["last_updated"] = "invalid"

    assert rag._cache_age_seconds(payload) == float("inf")


# ----------------------------------------------------
# Cache Expiry
# ----------------------------------------------------

def test_cache_expiry_remaining():

    payload = build_payload(age_minutes=15)

    remaining = rag._cache_expires_in_seconds(payload)

    assert remaining > 0


def test_cache_expired():

    payload = build_payload(age_minutes=120)

    remaining = rag._cache_expires_in_seconds(payload)

    assert remaining < 0


# ----------------------------------------------------
# Cache Usability
# ----------------------------------------------------

def test_cache_reusable():

    payload = build_payload()

    usable, score = rag._cache_is_usable(
        query="Microsoft latest AI news",
        company="Microsoft",
        payload=payload,
    )

    assert usable is True
    assert score >= 0.65


def test_cache_expired_not_reusable():

    payload = build_payload(age_minutes=90)

    usable, _ = rag._cache_is_usable(
        query="Microsoft latest AI news",
        company="Microsoft",
        payload=payload,
    )

    assert usable is False


def test_company_mismatch():

    payload = build_payload(company="Apple")

    usable, score = rag._cache_is_usable(
        query="Microsoft latest AI news",
        company="Microsoft",
        payload=payload,
    )

    assert usable is False
    assert score == 0.0


def test_low_similarity():

    payload = build_payload(
        query="Apple Vision Pro launch"
    )

    usable, score = rag._cache_is_usable(
        query="Microsoft Azure earnings",
        company="Microsoft",
        payload=payload,
    )

    assert usable is False
    assert score < 0.65


# ----------------------------------------------------
# Cache Message
# ----------------------------------------------------

def test_cache_message_contains_readable_time():

    payload = build_payload()

    msg = rag._cache_message_from_payload(payload)

    assert "Cached research reused" in msg
    assert "Fresh research available after" in msg
    assert "IST" in msg


# ----------------------------------------------------
# Cache Serialization
# ----------------------------------------------------

def test_serialize_contains_required_fields():

    payload = rag._serialize_payload(
        company="Microsoft",
        query="Microsoft AI",
        all_articles=[],
        top_articles=[],
        articles_analyzed=[],
        research_summary=None,
        repo_path=Path("latest.json"),
    )

    assert "last_updated" in payload
    assert "expires_at" in payload
    assert "cache_note" in payload
    assert "metrics" in payload
    assert "pipeline_version" in payload


# ----------------------------------------------------
# JSON Cache IO
# ----------------------------------------------------

def test_write_and_load_cache(tmp_path):

    payload = build_payload()

    cache_file = tmp_path / "latest.json"

    rag._write_json(cache_file, payload)

    loaded = rag._latest_payload_from_cache(cache_file)

    assert loaded["company"] == "Microsoft"
    assert loaded["query"] == payload["query"]


def test_invalid_cache_file(tmp_path):

    cache_file = tmp_path / "latest.json"

    cache_file.write_text("[]")

    with pytest.raises(ValueError):
        rag._latest_payload_from_cache(cache_file)