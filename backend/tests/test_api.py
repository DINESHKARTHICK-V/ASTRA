# ============================================================
#  ASTRA Cloud — Backend Test Suite
#  File   : backend/tests/test_api.py
#  Purpose: Comprehensive read-only tests for FastAPI endpoints:
#           - Startup & service info
#           - Health check & DB connectivity
#           - Observations list & detail
#           - Features & predictions
#           - ACIS candidates ranking & detail
#           - Processing runs
#           - Pagination & bounds
#           - 404 responses on missing IDs
#           - Preservation of scientific inference status (INFERENCE_HALTED)
#           - Verification of zero DB modifications
# ============================================================

import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.database import engine
from sqlalchemy import text


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient instance for API requests."""
    return TestClient(app)


def get_current_table_counts():
    """Helper to read row counts across all production tables."""
    tables = ["observations", "features", "predictions", "candidate_scores", "processing_runs"]
    counts = {}
    with engine.connect() as conn:
        for tbl in tables:
            res = conn.execute(text(f"SELECT count(*) FROM {tbl};"))
            counts[tbl] = res.scalar()
    return counts


# Snapshot DB counts before any test runs in this module.
# Used by test_database_row_counts_remain_unchanged to prove
# the test suite itself is read-only.
_BASELINE_COUNTS = get_current_table_counts()


# ------------------------------------------------------------
# 1. Startup & Root Endpoint
# ------------------------------------------------------------
def test_root_service_info(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "ASTRA API"
    assert data["version"] == "1.0.0"
    assert "docs_url" in data
    assert "endpoints" in data
    assert "/health" in data["endpoints"].values()
    assert "/api/observations" in data["endpoints"].values()


# ------------------------------------------------------------
# 2. Health & Database Connectivity
# ------------------------------------------------------------
def test_health_check_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert "active and responsive" in data["database_message"]
    assert "timestamp" in data


# ------------------------------------------------------------
# 3. Observations Endpoints
# ------------------------------------------------------------
def test_list_observations(client):
    response = client.get("/api/observations")
    assert response.status_code == 200
    data = response.json()
    expected = _BASELINE_COUNTS["observations"]
    assert data["total"] == expected
    assert data["total"] >= 12, "Seed data should have at least 12 observations"
    # Verify mandatory fields on first item returned
    item = data["items"][0]
    assert "file_name" in item
    assert "file_path" in item
    assert item["file_type"] == "PSRFITS_RADIO"
    assert item["validation_status"] == "VALID_PSRFITS"


def test_list_observations_pagination(client):
    response = client.get("/api/observations?limit=5&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == _BASELINE_COUNTS["observations"]
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert len(data["items"]) == 5

    # Test second page
    response_p2 = client.get("/api/observations?limit=5&offset=5")
    assert response_p2.status_code == 200
    data_p2 = response_p2.json()
    assert len(data_p2["items"]) == 5
    assert data_p2["items"][0]["id"] != data["items"][0]["id"]


def test_get_observation_detail(client):
    # Fetch first observation
    list_res = client.get("/api/observations?limit=1")
    first_id = list_res.json()["items"][0]["id"]

    response = client.get(f"/api/observations/{first_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == first_id
    assert "vegas_" in data["file_name"]
    assert data["telescope"] == "GBT"
    assert data["instrument"] == "VEGAS"
    assert data["target_name"] == "J1713+0747"
    assert data["frequency_mhz"] == 820.0


def test_get_observation_not_found(client):
    response = client.get("/api/observations/999999")
    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]


# ------------------------------------------------------------
# 4. Features & Predictions Endpoints
# ------------------------------------------------------------
def test_get_observation_features(client):
    list_res = client.get("/api/observations?limit=1")
    first_id = list_res.json()["items"][0]["id"]

    response = client.get(f"/api/observations/{first_id}/features")
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert data["observation_id"] == first_id
    assert data["dm_nominal"] == pytest.approx(15.992196, rel=1e-4)
    assert data["dm_curve_available"] is False
    assert data["htru2_compatible"] is False
    assert "HIGH_DOMAIN_SHIFT" in data["domain_shift_flag"]
    assert data["profile_mean"] is not None


def test_get_features_not_found(client):
    response = client.get("/api/observations/999999/features")
    assert response.status_code == 404


def test_get_observation_predictions_preserves_halted_status(client):
    list_res = client.get("/api/observations?limit=1")
    first_id = list_res.json()["items"][0]["id"]

    response = client.get(f"/api/observations/{first_id}/predictions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    pred = data[0]
    assert pred["observation_id"] == first_id
    assert pred["model_name"] == "RandomForestClassifier"
    # Scientific integrity check: inference status must be INFERENCE_HALTED
    assert pred["inference_status"] == "INFERENCE_HALTED"
    assert pred["predicted_class"] is None
    assert pred["pulsar_probability"] is None
    assert "missing" in pred["halt_reason"].lower() or "halt" in pred["halt_reason"].lower()


def test_get_predictions_not_found(client):
    response = client.get("/api/observations/999999/predictions")
    assert response.status_code == 404


# ------------------------------------------------------------
# 5. Candidates & ACIS Ranking Endpoints
# ------------------------------------------------------------
def test_list_candidates_ranking_order(client):
    response = client.get("/api/candidates")
    assert response.status_code == 200
    data = response.json()
    expected = _BASELINE_COUNTS["candidate_scores"]
    assert data["total"] == expected
    assert data["total"] >= 12, "Should have at least 12 seeded candidates"
    items = data["items"]
    assert len(items) == expected

    # Verify rank 1 has the highest score
    assert items[0]["rank_position"] == 1
    assert items[0]["acis_score"] == pytest.approx(0.8613, rel=1e-4)
    assert items[0]["priority_group"] == "HIGH"
    assert items[0]["evidence_available"] == "5/6"
    assert items[0]["target_name"] == "J1713+0747"

    # Verify monotonic ranking order
    for i in range(len(items) - 1):
        assert items[i]["rank_position"] < items[i + 1]["rank_position"]
        assert items[i]["acis_score"] >= items[i + 1]["acis_score"]


def test_list_candidates_filter_by_priority(client):
    response = client.get("/api/candidates?priority_group=HIGH")
    assert response.status_code == 200
    data = response.json()
    # All seeded candidates should be HIGH priority
    assert data["total"] == _BASELINE_COUNTS["candidate_scores"]

    # Filter for non-existent priority group
    response_empty = client.get("/api/candidates?priority_group=LOW")
    assert response_empty.status_code == 200
    data_empty = response_empty.json()
    assert data_empty["total"] == 0
    assert len(data_empty["items"]) == 0


def test_get_candidate_detail(client):
    list_res = client.get("/api/observations?limit=1")
    first_id = list_res.json()["items"][0]["id"]

    response = client.get(f"/api/candidates/{first_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["observation_id"] == first_id
    assert data["score_version"] == "ACIS_v1.0"
    assert data["acis_score"] > 0.80
    assert data["priority_group"] == "HIGH"


def test_get_candidate_not_found(client):
    response = client.get("/api/candidates/999999")
    assert response.status_code == 404


# ------------------------------------------------------------
# 6. Processing Runs Endpoints
# ------------------------------------------------------------
def test_list_processing_runs(client):
    response = client.get("/api/processing-runs")
    assert response.status_code == 200
    data = response.json()
    expected = _BASELINE_COUNTS["processing_runs"]
    assert data["total"] == expected
    assert data["total"] >= 12, "Should have at least 12 seeded processing runs"
    assert len(data["items"]) == expected
    # Find the seeded ASTRA_v1.0 pipeline run
    run = next((r for r in data["items"] if r.get("pipeline_version") == "ASTRA_v1.0"), data["items"][0])
    assert run["processing_status"] == "COMPLETED"
    assert run["pipeline_version"] == "ASTRA_v1.0"
    assert run["elapsed_seconds"] == pytest.approx(25.1, rel=1e-1)


# ------------------------------------------------------------
# 7. PDF Report Generation Endpoints
# ------------------------------------------------------------
def test_get_observation_report_success(client):
    list_res = client.get("/api/observations?limit=1")
    first_id = list_res.json()["items"][0]["id"]

    response = client.get(f"/api/observations/{first_id}/report")
    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert f'astra_obs_{first_id}_report.pdf' in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000


def test_get_observation_report_not_found(client):
    response = client.get("/api/observations/999999/report")
    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]


def test_pdf_report_content_and_status_integrity(client):
    import re, zlib, base64
    list_res = client.get("/api/observations?limit=1")
    first_id = list_res.json()["items"][0]["id"]
    response = client.get(f"/api/observations/{first_id}/report")
    assert response.status_code == 200
    
    # Decompress ASCII85 FlateDecode stream
    streams = re.findall(b'stream\r?\n(.*?~>)endstream', response.content, re.DOTALL)
    assert len(streams) >= 1
    a85_dec = base64.a85decode(streams[0].strip(), adobe=True)
    text = zlib.decompress(a85_dec).decode('latin1', errors='replace')
    assert "INFERENCE_HALTED" in text
    assert "J1713+0747" in text


def test_pdf_generation_robustness_with_null_metadata():
    from backend.app.models import Observation
    from backend.app.services.report_service import generate_observation_pdf
    
    # Observation with missing optional fields
    mock_obs = Observation(
        id=999,
        file_name="mock_test_archive.fits",
        file_path="data/mock/mock.fits",
        file_type="PSRFITS_RADIO",
        telescope=None,
        instrument=None,
        target_name=None,
        observation_date=None,
        observation_time=None,
        ra=None,
        dec=None,
        frequency_mhz=None,
        bandwidth_mhz=None,
        nchan=None,
        nsubint=None,
        nbin=None,
        validation_status="VALID_PSRFITS"
    )
    # None for feature, candidate, empty runs
    buf = generate_observation_pdf(mock_obs, None, [], None, [])
    data = buf.read()
    assert data.startswith(b"%PDF")
    assert len(data) > 1000


def test_error_handling_does_not_leak_secrets(client):
    # Test non-existent ID
    res_404 = client.get("/api/observations/999999")
    assert res_404.status_code == 404
    body_404 = res_404.text.lower()
    assert "password" not in body_404
    assert "openpgpwd" not in body_404
    assert "traceback" not in body_404

    # Test invalid limit parameter (validation error)
    res_422 = client.get("/api/observations?limit=99999")
    assert res_422.status_code == 422
    body_422 = res_422.text.lower()
    assert "password" not in body_422
    assert "openpgpwd" not in body_422



# ------------------------------------------------------------
# 7b. Observation Date Search Endpoints
# ------------------------------------------------------------
def test_observation_date_search_summary(client):
    res = client.get("/api/observations/date-search")
    assert res.status_code == 200
    data = res.json()
    assert "available_observation_dates" in data
    assert len(data["available_observation_dates"]) > 0
    assert "2019-06-03" in data["available_observation_dates"]
    assert data["total_matching_observations"] == 0


def test_observation_date_search_match_known_date(client):
    # Test searching for a known observation date in YYYY-MM-DD
    res = client.get("/api/observations/date-search?date=2019-06-03")
    assert res.status_code == 200
    data = res.json()
    assert data["total_matching_observations"] >= 1
    assert data["total_matching_files"] >= 1
    assert data["search_date"] == "2019-06-03"
    assert len(data["results"]) >= 1
    first_group = data["results"][0]
    assert first_group["recorded_observation_date"] == "2019-06-03"
    first_file = first_group["files"][0]
    assert first_file["recorded_observation_date"] == "2019-06-03"
    assert first_file["is_date_verified"] is True
    assert "Verified from file metadata" in first_file["date_source"]


def test_observation_date_search_supports_slash_format(client):
    # Test DD/MM/YYYY format as in user prompt example
    res = client.get("/api/observations/date-search?date=03/06/2019")
    assert res.status_code == 200
    data = res.json()
    assert data["total_matching_observations"] >= 1
    assert data["search_date"] == "2019-06-03"


def test_observation_date_search_no_matches(client):
    # Search a date with no recorded observations
    res = client.get("/api/observations/date-search?date=2016-10-20")
    assert res.status_code == 200
    data = res.json()
    assert data["total_matching_observations"] == 0
    assert data["total_matching_files"] == 0
    assert data["message"] == "No uploaded observations were found for this date."


# ------------------------------------------------------------
# 8. Database Immutability Check (Zero modifications during test run)
# ------------------------------------------------------------
def test_database_row_counts_remain_unchanged():
    """Verify this read-only test suite made no DB modifications."""
    counts_after = get_current_table_counts()
    for table, before in _BASELINE_COUNTS.items():
        assert counts_after[table] == before, (
            f"Table '{table}' had {before} rows before tests but {counts_after[table]} after. "
            "This test suite must not modify the database."
        )

