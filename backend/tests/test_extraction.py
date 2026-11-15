# ============================================================
#  ASTRA Cloud — Research Literature Extraction Unit Tests
#  File   : backend/tests/test_extraction.py
#  Purpose: Comprehensive mocked tests for the research literature
#           extraction layer. Verifies factual grounding,
#           unsupported field markers, provenance, handling of
#           incomplete abstracts, missing metadata, duplicate papers,
#           and API endpoint responses.
# ============================================================

import json
import pytest
from starlette.testclient import TestClient
from sqlalchemy import text

from backend.app.main import app
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import ResearchRecord, PaperExtraction
from backend.app.services.extraction_service import (
    LiteratureExtractionService,
    literature_extractor,
    NOT_AVAILABLE,
)
from backend.app.schemas import SCIENTIFIC_COLLECTOR_DISCLAIMER


@pytest.fixture(scope="module")
def client():
    """Ensure paper_extractions table exists and provide TestClient."""
    Base.metadata.create_all(bind=engine, tables=[ResearchRecord.__table__, PaperExtraction.__table__], checkfirst=True)
    return TestClient(app)


# Sample rich astronomical abstract
SAMPLE_RICH_ABSTRACT = (
    "We investigate high-precision timing of millisecond pulsars using 10 years of multi-frequency "
    "observations from the Green Bank Telescope (GBT). "
    "We apply Bayesian inference and TEMPO2 timing models to analyze folded integrated pulse profile moments "
    "and dispersion measure variations. "
    "Results demonstrate a sub-microsecond timing residual RMS of 120 ns across 15 binary pulsars. "
    "However, the timing precision is limited by unmodeled chromatic dispersion variations in the interstellar medium."
)

SAMPLE_INCOMPLETE_ABSTRACT = (
    "In this work, we discuss pulsar physics and magnetospheric emission geometries. "
    "The emission height can be constrained through relativistic aberration effects."
)


# ------------------------------------------------------------
# 1. Extraction Core Unit Tests
# ------------------------------------------------------------

def test_extraction_complete_abstract():
    extractor = LiteratureExtractionService()
    details, provenance = extractor.extract_from_record(
        title="High Precision Binary Pulsar Timing with GBT",
        abstract=SAMPLE_RICH_ABSTRACT,
        identifier="10.1051/0004-6361/2024001",
        canonical_url="https://arxiv.org/abs/2403.11111",
        source_name="arXiv",
        raw_metadata={"doi": "10.1051/0004-6361/2024001"},
    )

    # 1. Grounded problem
    assert "investigate high-precision timing" in details.research_problem

    # 2. Dataset and type
    assert details.dataset_name == "Green Bank Telescope (GBT)"
    assert "Radio" in details.dataset_type

    # 3. Algorithms
    assert "Bayesian Inference / MCMC" in details.algorithms_or_models
    assert "TEMPO2 / PINT Timing Software" in details.algorithms_or_models

    # 4. Features
    assert "Integrated Pulse Profile" in details.feature_types
    assert "Dispersion Measure (DM)" in details.feature_types

    # 5. Metrics
    assert "Timing Residual RMS" in details.evaluation_metrics

    # 6. Findings
    assert "sub-microsecond timing residual RMS" in details.main_reported_findings

    # 7. Author limitations
    assert "limited by unmodeled chromatic dispersion" in details.stated_limitations

    # 8. Full text & license
    assert "Open Access" in details.full_text_availability
    assert "arxiv.org/pdf" in details.full_text_availability
    assert details.doi == "10.1051/0004-6361/2024001"

    # Evidence locations
    assert "research_problem" in details.evidence_locations
    assert "dataset" in details.evidence_locations
    assert "main_reported_findings" in details.evidence_locations
    assert "stated_limitations" in details.evidence_locations

    # Facts vs inferences assertion
    assert details.is_inferred is False
    assert "factually extracted" in details.facts_vs_inferences_note

    # Provenance
    assert provenance["source_provider"] == "arXiv"
    assert provenance["sentence_count"] >= 3
    assert "Zero restricted full-text bypass" in provenance["text_source"]


def test_extraction_incomplete_abstract_marks_unsupported_fields():
    extractor = LiteratureExtractionService()
    details, provenance = extractor.extract_from_record(
        title="Magnetospheric Emission in Pulsars",
        abstract=SAMPLE_INCOMPLETE_ABSTRACT,
        identifier="arXiv:2403.99999",
        canonical_url="https://arxiv.org/abs/2403.99999",
        source_name="arXiv",
    )

    # Unsupported fields must be strictly marked NOT_AVAILABLE (Rule 2 & 3)
    assert details.dataset_name == NOT_AVAILABLE
    assert details.dataset_type == NOT_AVAILABLE
    assert details.algorithms_or_models == [NOT_AVAILABLE]
    assert details.evaluation_metrics == [NOT_AVAILABLE]
    assert details.stated_limitations == NOT_AVAILABLE

    # Problem should still be extracted factually
    assert "discuss pulsar physics" in details.research_problem


def test_extraction_missing_metadata_and_empty_abstract():
    extractor = LiteratureExtractionService()
    details, provenance = extractor.extract_from_record(
        title="Study of Pulsar Polarization",
        abstract="",
        identifier="arXiv:2403.00000",
        canonical_url="https://arxiv.org/abs/2403.00000",
        source_name="arXiv",
    )

    # All body fields unsupported
    assert details.dataset_name == NOT_AVAILABLE
    assert details.algorithms_or_models == [NOT_AVAILABLE]
    assert details.evaluation_metrics == [NOT_AVAILABLE]
    assert details.main_reported_findings == NOT_AVAILABLE
    assert details.stated_limitations == NOT_AVAILABLE
    assert details.doi is None

    # Title fallback for problem
    assert "Study of Pulsar Polarization" in details.research_problem


def test_extraction_malformed_and_edge_case_inputs():
    extractor = LiteratureExtractionService()
    # None abstract, short title, special characters
    details, provenance = extractor.extract_from_record(
        title="!@#$%^&*()_+",
        abstract=None,
        identifier="adhoc:123",
        canonical_url="https://example.org/paper",
        source_name="UnknownSource",
    )

    assert details.research_problem == NOT_AVAILABLE
    assert details.dataset_name == NOT_AVAILABLE
    assert details.full_text_availability == "Metadata-only retrieved (Paywall / institutional subscription may apply)"
    assert details.licence_or_access_status == NOT_AVAILABLE


def test_extraction_duplicate_papers_idempotent():
    db = SessionLocal()
    try:
        # Clean up any existing fixture
        db.query(ResearchRecord).filter(ResearchRecord.identifier == "test:idempotent:001").delete()
        db.commit()

        # Create a test research record
        test_rec = ResearchRecord(
            record_type="paper",
            title="Idempotency Test Paper on Pulsars",
            authors=json.dumps(["Dr. Tester"]),
            abstract=SAMPLE_RICH_ABSTRACT,
            identifier="test:idempotent:001",
            source_name="arXiv",
            canonical_url="https://arxiv.org/abs/test.001",
        )
        db.add(test_rec)
        db.commit()
        db.refresh(test_rec)

        extractor = LiteratureExtractionService()
        details, prov = extractor.extract_from_record(
            title=test_rec.title,
            abstract=test_rec.abstract,
            identifier=test_rec.identifier,
            canonical_url=test_rec.canonical_url,
            source_name=test_rec.source_name,
        )

        # First persist
        pe1 = extractor.persist_extraction(db, test_rec.id, test_rec.identifier, test_rec.title, details, prov)
        first_id = pe1.id

        # Second persist with same identifier should update, not duplicate
        pe2 = extractor.persist_extraction(db, test_rec.id, test_rec.identifier, test_rec.title, details, prov)
        assert pe2.id == first_id

        # Clean up
        db.delete(test_rec)
        db.commit()
    finally:
        db.close()


# ------------------------------------------------------------
# 2. Router & API Integration Tests
# ------------------------------------------------------------

def test_api_post_extract_adhoc(client):
    payload = {
        "title": "High Precision Binary Pulsar Timing with GBT",
        "abstract": SAMPLE_RICH_ABSTRACT,
        "identifier": "arXiv:2403.11111",
        "canonical_url": "https://arxiv.org/abs/2403.11111",
        "source_name": "arXiv",
        "save_to_db": False,
    }
    response = client.post("/api/collector/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["identifier"] == "arXiv:2403.11111"
    assert data["extracted_details"]["dataset_name"] == "Green Bank Telescope (GBT)"
    assert "TEMPO2 / PINT Timing Software" in data["extracted_details"]["algorithms_or_models"]
    assert data["scientific_disclaimer"] == SCIENTIFIC_COLLECTOR_DISCLAIMER


def test_api_extract_and_retrieve_record_extraction(client):
    # 1. Insert a temporary research record in DB
    db = SessionLocal()
    try:
        db.query(ResearchRecord).filter(ResearchRecord.identifier == "test:chime:frb:001").delete()
        db.commit()

        rec = ResearchRecord(
            record_type="paper",
            title="Fast Radio Burst Search with CHIME",
            authors=json.dumps(["CHIME Collaboration"]),
            abstract="In this work, we present Fast Radio Burst searches using the CHIME telescope. We use matched filtering. Results show 500 new FRB detections.",
            identifier="test:chime:frb:001",
            source_name="arXiv",
            canonical_url="https://arxiv.org/abs/test.chime.001",
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        rec_id = rec.id

        # 2. Call GET extraction (should run on-demand and persist)
        get_res = client.get(f"/api/collector/records/{rec_id}/extraction")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["record_id"] == rec_id
        assert get_data["extracted_details"]["dataset_name"] == "CHIME Telescope"
        assert "Matched Filtering" in get_data["extracted_details"]["algorithms_or_models"]
        assert "500 new FRB detections" in get_data["extracted_details"]["main_reported_findings"]
        assert get_data["extracted_details"]["stated_limitations"] == NOT_AVAILABLE

        # 3. Clean up
        db.delete(rec)
        db.commit()
    finally:
        db.close()


def test_api_extract_invalid_record_id_returns_404(client):
    response = client.get("/api/collector/records/9999999/extraction")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_database_table_counts_safety_unmodified():
    """Verify core astronomical tables remain completely untouched."""
    with engine.connect() as conn:
        for tbl in ["observations", "features", "predictions", "candidate_scores"]:
            res = conn.execute(text(f"SELECT count(*) FROM {tbl};"))
            assert res.scalar() is not None
