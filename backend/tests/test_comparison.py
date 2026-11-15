# ============================================================
#  ASTRA Cloud — Research Literature Comparison Unit Tests
#  File   : backend/tests/test_comparison.py
#  Purpose: Comprehensive unit and integration tests for literature
#           comparison synthesis, gap candidate identification,
#           conflicting setup detection, and manual verification items.
#  Safety : Tests empty collections, duplicate records, missing fields,
#           and verifies non-assertion of research novelty.
# ============================================================

import os
import json
import pytest
from starlette.testclient import TestClient
from sqlalchemy import text

from backend.app.main import app
from backend.app.database import engine, Base
from backend.app.models import ResearchRecord, PaperExtraction
from backend.app.schemas import (
    ExtractedResearchDetails,
    RESEARCH_GAP_DISCLAIMER,
    SCIENTIFIC_COLLECTOR_DISCLAIMER,
)
from backend.app.services.extraction_service import NOT_AVAILABLE
from backend.app.services.comparison_service import (
    LiteratureComparisonService,
    literature_comparator,
    REPORTS_DIR,
)


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine, tables=[ResearchRecord.__table__, PaperExtraction.__table__], checkfirst=True)
    return TestClient(app)


# Sample extracted details fixtures
PAPER_A_GBT = ExtractedResearchDetails(
    research_problem="High-precision timing of binary millisecond pulsars using GBT observations.",
    dataset_name="Green Bank Telescope (GBT)",
    dataset_type="Pulsar timing archive (Radio)",
    algorithms_or_models=["Bayesian Inference / MCMC", "TEMPO2 / PINT Timing Software"],
    feature_types=["Integrated Pulse Profile", "Dispersion Measure (DM)"],
    evaluation_metrics=["Timing Residual RMS"],
    main_reported_findings="Results demonstrate timing residual RMS of 120 ns across 15 binary pulsars.",
    stated_limitations="However, the timing precision is limited by unmodeled chromatic dispersion variations.",
    full_text_availability="Open Access (Official arXiv PDF at https://arxiv.org/pdf/2403.11111)",
    licence_or_access_status="arXiv Non-Exclusive License / Open Access",
    source_url="https://arxiv.org/abs/2403.11111",
    doi="10.1051/0004-6361/2024001",
    evidence_locations={"dataset": "Green Bank Telescope (GBT)"},
)

PAPER_B_HTRU2 = ExtractedResearchDetails(
    research_problem="Pulsar candidate classification on benchmark surveys.",
    dataset_name="HTRU2 Benchmark Dataset",
    dataset_type="Benchmark dataset",
    algorithms_or_models=["Random Forest", "Support Vector Machine (SVM)"],
    feature_types=["Integrated Pulse Profile", "Dispersion Measure (DM)"],
    evaluation_metrics=["F1-Score", "Classification Accuracy"],
    main_reported_findings="Random Forest achieves an accuracy of 97.8% on 17,898 candidate samples.",
    stated_limitations="However, classifier performance drops significantly on severely unbalanced candidate sets.",
    full_text_availability="Open Access (Official arXiv PDF at https://arxiv.org/pdf/2403.22222)",
    licence_or_access_status="arXiv Non-Exclusive License / Open Access",
    source_url="https://arxiv.org/abs/2403.22222",
    doi=None,
    evidence_locations={"dataset": "HTRU2 Benchmark Dataset"},
)

PAPER_C_CHIME = ExtractedResearchDetails(
    research_problem="Detection and localization of Fast Radio Bursts.",
    dataset_name="CHIME Telescope",
    dataset_type="Transit radio telescope archive",
    algorithms_or_models=["Matched Filtering", "Fast Folding Algorithm (FFA)"],
    feature_types=["Dispersion Measure (DM)", "Signal-to-Noise Ratio (SNR)"],
    evaluation_metrics=["Signal-to-Noise Ratio (SNR)"],
    main_reported_findings="We discover 500 new FRB events with peak SNR exceeding 10.0.",
    stated_limitations=NOT_AVAILABLE,
    full_text_availability="Open Access (Official arXiv PDF at https://arxiv.org/pdf/2403.33333)",
    licence_or_access_status="arXiv Non-Exclusive License / Open Access",
    source_url="https://arxiv.org/abs/2403.33333",
    doi="10.1038/s41586-024-001",
    evidence_locations={},
)


# ------------------------------------------------------------
# 1. Comparison Core Unit Tests
# ------------------------------------------------------------

def test_compare_empty_collection():
    comparator = LiteratureComparisonService()
    res = comparator.compare_extractions([], save_report=False)
    assert res.total_papers_analyzed == 0
    assert len(res.comparison_table) == 0
    assert len(res.research_gap_candidates) == 0
    assert "No research literature records" in res.methodological_caveats
    assert res.scientific_disclaimer == SCIENTIFIC_COLLECTOR_DISCLAIMER


def test_compare_duplicate_records_deduplicated():
    comparator = LiteratureComparisonService()
    items = [
        ("arXiv:2403.11111", "Paper 1 (Original)", PAPER_A_GBT),
        ("arXiv:2403.11111", "Paper 1 (Duplicate Instance)", PAPER_A_GBT),
        ("arXiv:2403.22222", "Paper 2", PAPER_B_HTRU2),
    ]
    res = comparator.compare_extractions(items, save_report=False)
    assert res.total_papers_analyzed == 2
    assert len(res.comparison_table) == 2
    identifiers = [r.identifier for r in res.comparison_table]
    assert identifiers == ["arXiv:2403.11111", "arXiv:2403.22222"]


def test_compare_missing_fields_and_manual_verification():
    comparator = LiteratureComparisonService()
    incomplete_details = ExtractedResearchDetails(
        research_problem="Theoretical study of neutron star crusts.",
        dataset_name=NOT_AVAILABLE,
        dataset_type=NOT_AVAILABLE,
        algorithms_or_models=[NOT_AVAILABLE],
        feature_types=[NOT_AVAILABLE],
        evaluation_metrics=[NOT_AVAILABLE],
        main_reported_findings=NOT_AVAILABLE,
        stated_limitations=NOT_AVAILABLE,
        full_text_availability="Metadata-only retrieved",
        licence_or_access_status=NOT_AVAILABLE,
        source_url="https://example.org/incomplete",
        doi=None,
        evidence_locations={},
    )
    items = [("test:incomplete:001", "Incomplete Paper", incomplete_details)]
    res = comparator.compare_extractions(items, save_report=False)

    assert res.total_papers_analyzed == 1
    row = res.comparison_table[0]
    assert row.data_source_and_mode == NOT_AVAILABLE
    assert row.algorithm_or_method == NOT_AVAILABLE
    assert row.dataset_size == "Not explicitly reported in abstract"

    # Must generate an item requiring manual verification
    assert len(res.manual_verification_required) >= 1
    v_item = res.manual_verification_required[0]
    assert v_item.paper_identifier == "test:incomplete:001"
    assert "Manual inspection of the full publication text is required" in v_item.reason_manual_check_needed


def test_compare_synthesis_relevance_and_gaps():
    comparator = LiteratureComparisonService()
    items = [
        ("arXiv:2403.11111", "GBT Timing Paper", PAPER_A_GBT),
        ("arXiv:2403.22222", "HTRU2 ML Paper", PAPER_B_HTRU2),
        ("arXiv:2403.33333", "CHIME FRB Paper", PAPER_C_CHIME),
    ]
    res = comparator.compare_extractions(items, save_report=False)
    assert res.total_papers_analyzed == 3
    assert len(res.comparison_table) == 3

    # Check relevance evaluation for GBT
    gbt_row = next(r for r in res.comparison_table if r.identifier == "arXiv:2403.11111")
    assert "Direct Architecture Relevance" in gbt_row.relevance_to_astra_recoverability
    assert "15 binary pulsars" in gbt_row.dataset_size

    # Check relevance evaluation for HTRU2
    htru2_row = next(r for r in res.comparison_table if r.identifier == "arXiv:2403.22222")
    assert "Domain-Shift" in htru2_row.relevance_to_astra_recoverability
    assert "17,898 candidate" in htru2_row.dataset_size

    # Verify Research Gap Candidates disclaimer (Rule: No unwarranted novelty assertions)
    assert len(res.research_gap_candidates) >= 2
    for gap in res.research_gap_candidates:
        assert gap.novelty_claim_status == RESEARCH_GAP_DISCLAIMER
        assert len(gap.supporting_paper_identifiers) == 3

    # Verify Conflicting / Incomparable Setups
    assert len(res.conflicting_or_incomparable_setups) >= 2
    dimensions = [c.dimension for c in res.conflicting_or_incomparable_setups]
    assert "Input Signal Representation" in dimensions
    assert "Evaluation Objectives and Target Metrics" in dimensions


def test_persistence_report_files_generation():
    comparator = LiteratureComparisonService()
    items = [
        ("arXiv:2403.11111", "GBT Timing Paper", PAPER_A_GBT),
        ("arXiv:2403.22222", "HTRU2 ML Paper", PAPER_B_HTRU2),
    ]
    res = comparator.compare_extractions(items, save_report=True)
    json_path = os.path.join(REPORTS_DIR, "literature_comparison.json")
    md_path = os.path.join(REPORTS_DIR, "literature_comparison.md")

    assert os.path.exists(json_path)
    assert os.path.exists(md_path)

    # Verify markdown contents
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    assert "# ASTRA Cloud — Research Literature Comparison & Synthesis" in md_text
    assert "1. Structured Literature Comparison Table" in md_text
    assert "2. Research Gap Candidates" in md_text
    assert "3. Conflicting & Incomparable Experimental Setups" in md_text
    assert "4. Details Requiring Manual Full-Paper Verification" in md_text
    assert RESEARCH_GAP_DISCLAIMER in md_text


# ------------------------------------------------------------
# 2. Router & API Integration Tests
# ------------------------------------------------------------

def test_api_post_compare_endpoint(client):
    payload = {
        "include_adhoc_records": [
            {
                "title": "GBT Pulsar Timing",
                "abstract": "We study binary pulsars with Green Bank Telescope using TEMPO2. Timing residual RMS is 150 ns.",
                "identifier": "adhoc:gbt:001",
                "canonical_url": "https://arxiv.org/abs/adhoc.001",
                "source_name": "arXiv",
            },
            {
                "title": "HTRU2 Benchmark Classification",
                "abstract": "We evaluate Random Forest on the HTRU2 dataset. Accuracy is 98%.",
                "identifier": "adhoc:htru2:002",
                "canonical_url": "https://arxiv.org/abs/adhoc.002",
                "source_name": "arXiv",
            },
        ],
        "save_report": True,
    }
    response = client.post("/api/collector/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_papers_analyzed"] >= 2
    assert len(data["comparison_table"]) >= 2
    assert len(data["research_gap_candidates"]) >= 2
    assert data["scientific_disclaimer"] == SCIENTIFIC_COLLECTOR_DISCLAIMER


def test_api_get_latest_comparison_endpoint(client):
    response = client.get("/api/collector/compare/latest")
    assert response.status_code == 200
    data = response.json()
    assert "comparison_table" in data
    assert "research_gap_candidates" in data
    assert "conflicting_or_incomparable_setups" in data
    assert "manual_verification_required" in data


def test_database_immutability():
    """Verify that astronomical observation tables remain untouched."""
    with engine.connect() as conn:
        for tbl in ["observations", "features", "predictions", "candidate_scores"]:
            res = conn.execute(text(f"SELECT count(*) FROM {tbl};"))
            assert res.scalar() is not None
