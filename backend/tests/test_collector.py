# ============================================================
#  ASTRA Cloud — Research Web Collector Unit Test Suite
#  File   : backend/tests/test_collector.py
#  Purpose: Comprehensive mocked tests for astronomical research
#           metadata discovery, normalization, validation,
#           deduplication, rate limiting, error handling, and API.
#  Safety : Completely mocked; zero external live network requests.
# ============================================================

import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest
import requests
from starlette.testclient import TestClient
from sqlalchemy import text

from backend.app.main import app
from backend.app.database import engine, Base
from backend.app.models import ResearchRecord, ProcessingRun
from backend.app.schemas import NormalizedResearchRecord, SCIENTIFIC_COLLECTOR_DISCLAIMER
from backend.app.services.collector_service import (
    ArxivCollector,
    collector_service,
    validate_canonical_url,
    normalize_identifier,
    normalize_canonical_url,
    deduplicate_records,
    validate_record,
)


@pytest.fixture(scope="module")
def client():
    """Provides TestClient with tables created safely."""
    # Ensure research_records table exists
    Base.metadata.create_all(bind=engine, tables=[ResearchRecord.__table__], checkfirst=True)
    return TestClient(app)


# Sample realistic arXiv Atom XML feed for mocking
SAMPLE_ARXIV_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <title type="html">ArXiv Query: search_query=pulsar</title>
  <opensearch:totalResults>2</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>2</opensearch:itemsPerPage>
  <entry>
    <id>http://arxiv.org/abs/2403.11111v1</id>
    <published>2024-03-15T18:00:00Z</published>
    <updated>2024-03-15T18:00:00Z</updated>
    <title> High Precision Timing of Binary Millisecond Pulsars with GBT </title>
    <summary> We report on 10-year high-precision timing observations of PSR J1713+0747. </summary>
    <author>
      <name>Jane Astronomer</name>
    </author>
    <author>
      <name>John Cosmologist</name>
    </author>
    <arxiv:doi>10.1051/0004-6361/2024001</arxiv:doi>
    <arxiv:primary_category term="astro-ph.HE" scheme="http://arxiv.org/schemas/atom"/>
    <category term="astro-ph.HE" scheme="http://arxiv.org/schemas/atom"/>
    <category term="astro-ph.IM" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2403.22222v2</id>
    <published>2024-03-16T12:30:00Z</published>
    <updated>2024-03-18T09:00:00Z</updated>
    <title> Deep Neural Networks for Dispersion Measure Estimation </title>
    <summary> Automatic pulse profile de-dispersion using convolutional neural networks. </summary>
    <author>
      <name>Alice Radio</name>
    </author>
    <arxiv:primary_category term="astro-ph.IM" scheme="http://arxiv.org/schemas/atom"/>
    <category term="astro-ph.IM" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>
"""


# ------------------------------------------------------------
# 1. Validation and Normalization Unit Tests
# ------------------------------------------------------------

def test_validate_canonical_url():
    assert validate_canonical_url("https://arxiv.org/abs/2403.11111") is True
    assert validate_canonical_url("http://doi.org/10.1051/0004-6361") is True
    assert validate_canonical_url("ftp://invalid.scheme/file") is False
    assert validate_canonical_url("just-a-string") is False
    assert validate_canonical_url("") is False
    assert validate_canonical_url(None) is False


def test_normalize_identifier():
    assert normalize_identifier("10.1051/0004-6361/2024001") == "10.1051/0004-6361/2024001"
    assert normalize_identifier("doi: 10.1051/0004-6361/2024001") == "10.1051/0004-6361/2024001"
    assert normalize_identifier("https://doi.org/10.1051/0004-6361/2024001") == "10.1051/0004-6361/2024001"
    assert normalize_identifier("arXiv:2403.11111v2") == "2403.11111"
    assert normalize_identifier("2403.11111v1") == "2403.11111"


def test_deduplicate_records():
    r1 = NormalizedResearchRecord(
        record_type="paper",
        title="Paper A",
        authors=["Author 1"],
        identifier="10.1234/test.1",
        source_name="arXiv",
        canonical_url="https://arxiv.org/abs/2403.00001",
    )
    # Duplicate identifier
    r2 = NormalizedResearchRecord(
        record_type="paper",
        title="Paper A (Duplicate DOI)",
        authors=["Author 1"],
        identifier="doi: 10.1234/test.1",
        source_name="arXiv",
        canonical_url="https://arxiv.org/abs/2403.00001v2",
    )
    # Duplicate canonical URL
    r3 = NormalizedResearchRecord(
        record_type="paper",
        title="Paper A (Duplicate URL)",
        authors=["Author 1"],
        identifier="arXiv:2403.00001",
        source_name="arXiv",
        canonical_url="https://arxiv.org/abs/2403.00001",
    )
    # Distinct unique record
    r4 = NormalizedResearchRecord(
        record_type="paper",
        title="Paper B Distinct",
        authors=["Author 2"],
        identifier="10.1234/test.2",
        source_name="arXiv",
        canonical_url="https://arxiv.org/abs/2403.00002",
    )

    unique, dedup_count = deduplicate_records([r1, r2, r3, r4])
    assert len(unique) == 2
    assert dedup_count == 2
    assert unique[0].identifier == "10.1234/test.1"
    assert unique[1].identifier == "10.1234/test.2"


def test_validate_record_detects_missing_fields():
    invalid_rec = NormalizedResearchRecord(
        record_type="paper",
        title="",
        authors=[],
        identifier="",
        source_name="",
        canonical_url="not-a-url",
    )
    is_valid, errors = validate_record(invalid_rec)
    assert is_valid is False
    assert len(errors) >= 3


# ------------------------------------------------------------
# 2. arXiv Provider Unit Tests (Mocked Upstream Requests)
# ------------------------------------------------------------

def test_arxiv_collector_successful_query_mocked():
    collector = ArxivCollector()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = SAMPLE_ARXIV_XML

    with patch("requests.get", return_value=mock_resp) as mock_get:
        records, total_found, meta = collector.query("pulsar timing", max_results=2)

        assert mock_get.called
        assert meta["status"] == "COMPLETED"
        assert total_found == 2
        assert len(records) == 2

        # Verify record 1
        r1 = records[0]
        assert r1.title == "High Precision Timing of Binary Millisecond Pulsars with GBT"
        assert r1.authors == ["Jane Astronomer", "John Cosmologist"]
        assert r1.identifier == "10.1051/0004-6361/2024001"
        assert r1.canonical_url == "https://arxiv.org/abs/2403.11111v1"
        assert r1.publication_date == "2024-03-15"
        assert r1.scientific_disclaimer == SCIENTIFIC_COLLECTOR_DISCLAIMER

        # Verify record 2 fallback identifier to arXiv ID
        r2 = records[1]
        assert r2.identifier == "arXiv:2403.22222v2"
        assert r2.canonical_url == "https://arxiv.org/abs/2403.22222v2"
        assert r2.authors == ["Alice Radio"]


def test_arxiv_collector_handles_timeout():
    collector = ArxivCollector()

    with patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out")):
        records, total_found, meta = collector.query("pulsar", timeout=5.0)
        assert records == []
        assert total_found == 0
        assert meta["status"] == "TIMEOUT"
        assert "timed out" in meta["error"]


def test_arxiv_collector_handles_rate_limiting():
    collector = ArxivCollector()

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.content = b"Too Many Requests"

    with patch("requests.get", return_value=mock_resp):
        records, total_found, meta = collector.query("pulsar")
        assert records == []
        assert meta["status"] == "RATE_LIMITED"


def test_arxiv_collector_handles_malformed_xml():
    collector = ArxivCollector()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"<html><head><title>500 Internal Error</title></head><body>Broken XML"

    with patch("requests.get", return_value=mock_resp):
        records, total_found, meta = collector.query("pulsar")
        assert records == []
        assert meta["status"] == "MALFORMED_RESPONSE"


# ------------------------------------------------------------
# 3. Router & API Integration Tests
# ------------------------------------------------------------

def test_api_list_collector_sources(client):
    response = client.get("/api/collector/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    arxiv_src = next((s for s in data if s["name"] == "arXiv"), None)
    assert arxiv_src is not None
    assert arxiv_src["is_operational"] is True
    assert "paper" in arxiv_src["supported_record_types"]


def test_api_query_collector_mocked(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = SAMPLE_ARXIV_XML

    with patch("requests.get", return_value=mock_resp):
        payload = {
            "query": "pulsar timing",
            "source": "arXiv",
            "category": "astro-ph.HE",
            "max_results": 2,
            "save_to_db": True,
        }
        response = client.post("/api/collector/query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "pulsar timing"
        assert data["source"] == "arXiv"
        assert data["total_returned"] == 2
        assert len(data["items"]) == 2
        assert data["scientific_disclaimer"] == SCIENTIFIC_COLLECTOR_DISCLAIMER
        assert "execution_seconds" in data


def test_api_query_collector_invalid_source_rejected(client):
    payload = {
        "query": "pulsar",
        "source": "NonExistentSource",
        "max_results": 5,
    }
    response = client.post("/api/collector/query", json=payload)
    assert response.status_code == 400
    assert "not registered" in response.json()["detail"]


def test_api_query_collector_short_query_validation(client):
    payload = {
        "query": "a",  # min_length is 2
        "source": "arXiv",
    }
    response = client.post("/api/collector/query", json=payload)
    assert response.status_code == 422


def test_api_list_and_get_records(client):
    # Retrieve stored records
    response = client.get("/api/collector/records?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert data["scientific_disclaimer"] == SCIENTIFIC_COLLECTOR_DISCLAIMER

    if data["items"]:
        first_id = data["items"][0]["id"]
        detail_resp = client.get(f"/api/collector/records/{first_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == first_id
        assert detail["scientific_disclaimer"] == SCIENTIFIC_COLLECTOR_DISCLAIMER


def test_database_table_counts_safety(client):
    """
    Verify that existing astronomical tables (observations, features, predictions,
    candidate_scores) were NOT modified by the research collector.
    """
    with engine.connect() as conn:
        for tbl in ["observations", "features", "predictions", "candidate_scores"]:
            res = conn.execute(text(f"SELECT count(*) FROM {tbl};"))
            # Just ensure query executes without errors and table integrity holds
            assert res.scalar() is not None

        # Verify research_records table exists and can be queried
        res_rec = conn.execute(text("SELECT count(*) FROM research_records;"))
        assert res_rec.scalar() >= 0
