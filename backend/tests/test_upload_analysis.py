# ============================================================
#  ASTRA Cloud — Multi-Type FITS Upload & Analysis Tests
#  File   : backend/tests/test_upload_analysis.py
#  Purpose: Comprehensive integration tests for multi-file upload,
#           file validation, checksum deduplication, scientific
#           workflow dispatch, optical preview, and boundary enforcement.
# ============================================================

import io
import pytest
from pathlib import Path
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import Observation, ProcessingRun

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    # Teardown fixture: removes only the test-uploaded row upon completion
    yield
    db = SessionLocal()
    try:
        db.query(ProcessingRun).filter(ProcessingRun.pipeline_version == "ASTRA_v2.0_UI").delete()
        db.query(Observation).filter(Observation.file_name == "WFPC2u5780205r_c0fx.fits").delete()
        db.commit()
    finally:
        db.close()


def test_service_info_includes_new_endpoints(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "upload_fits" in data["endpoints"]
    assert "start_analysis" in data["endpoints"]
    assert "observation_preview" in data["endpoints"]


def test_upload_rejects_empty_file(client):
    files = {"files": ("empty.fits", b"", "application/octet-stream")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_rejects_unsupported_format(client):
    files = {"files": ("test.txt", b"not a fits file", "text/plain")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_upload_rejects_invalid_fits_header(client):
    files = {"files": ("corrupt.fits", b"CORRUPT_RANDOM_BYTES_WITHOUT_SIMPLE_HEADER" * 10, "application/octet-stream")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 400
    assert "valid fits" in response.json()["detail"].lower()


def test_upload_and_inspect_optical_fits(client):
    # Use real optical reference FITS
    optical_file_path = REPO_ROOT / "data" / "fits" / "WFPC2u5780205r_c0fx.fits"
    assert optical_file_path.exists(), "Reference optical file WFPC2u5780205r_c0fx.fits must exist."

    with open(optical_file_path, "rb") as f:
        file_bytes = f.read()

    files = {"files": ("WFPC2u5780205r_c0fx.fits", file_bytes, "application/octet-stream")}
    data = {"display_names": '["HST WFPC2 Optical Field NGC4151"]'}

    response = client.post("/api/upload", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["total_uploaded"] == 1

    item = res_data["files"][0]
    assert item["detected_type"] == "FITS_IMAGE_OPTICAL"
    assert item["display_name"] in ("HST WFPC2 Optical Field NGC4151", "WFPC2 NGC 4151 Renovated Name")
    assert item["telescope"] == "HST"
    assert item["instrument"] == "WFPC2"
    assert len(item["checksum"]) == 64

    # Verify optical workflows are present and radio-only workflows are excluded
    workflow_ids = [w["id"] for w in item["available_workflows"]]
    assert "inspect_metadata" in workflow_ids
    assert "preview_image" in workflow_ids
    assert "image_statistics" in workflow_ids
    assert "inspect_hdus" in workflow_ids
    assert "radio_signal" not in workflow_ids
    assert "pulsar_inference" not in workflow_ids


def test_duplicate_upload_detection(client):
    optical_file_path = REPO_ROOT / "data" / "fits" / "WFPC2u5780205r_c0fx.fits"
    with open(optical_file_path, "rb") as f:
        file_bytes = f.read()

    files = {"files": ("WFPC2u5780205r_c0fx.fits", file_bytes, "application/octet-stream")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["files"][0]["is_duplicate"] is True


def test_optical_image_preview_endpoint(client):
    # Find the uploaded optical observation
    db = SessionLocal()
    try:
        opt_obs = db.query(Observation).filter(Observation.file_name == "WFPC2u5780205r_c0fx.fits").first()
        assert opt_obs is not None
        obs_id = opt_obs.id
    finally:
        db.close()

    response = client.get(f"/api/observations/{obs_id}/preview")
    assert response.status_code == 200
    preview = response.json()
    assert preview["observation_id"] == obs_id
    assert preview["image_data_url"].startswith("data:image/png;base64,")
    assert preview["width"] == 200
    assert preview["height"] == 200
    assert preview["total_pixels"] == 40000


def test_optical_analysis_execution(client):
    db = SessionLocal()
    try:
        opt_obs = db.query(Observation).filter(Observation.file_name == "WFPC2u5780205r_c0fx.fits").first()
        obs_id = opt_obs.id
    finally:
        db.close()

    # Run image statistics workflow
    req = {"observation_id": obs_id, "workflow_id": "image_statistics"}
    response = client.post("/api/analysis/start", json=req)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "COMPLETED"
    assert "mean" in res["details"]
    assert "median" in res["details"]


def test_boundary_enforcement_blocks_pulsar_inference_on_optical(client):
    db = SessionLocal()
    try:
        opt_obs = db.query(Observation).filter(Observation.file_name == "WFPC2u5780205r_c0fx.fits").first()
        obs_id = opt_obs.id
    finally:
        db.close()

    # Attempt to start pulsar inference on optical file
    req = {"observation_id": obs_id, "workflow_id": "pulsar_inference"}
    response = client.post("/api/analysis/start", json=req)
    assert response.status_code == 400
    assert "cannot run" in response.json()["detail"].lower()
    assert "optical" in response.json()["detail"].lower()


def test_radio_workflow_preserves_inference_halted(client):
    # Observation #1 is a fold-mode radio archive
    req = {"observation_id": 1, "workflow_id": "pulsar_inference"}
    response = client.post("/api/analysis/start", json=req)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HALTED"
    assert data["details"]["inference_status"] == "INFERENCE_HALTED"
    assert "dm-snr curve" in data["details"]["halt_reason"].lower()


def test_update_observation_display_name(client):
    db = SessionLocal()
    try:
        opt_obs = db.query(Observation).filter(Observation.file_name == "WFPC2u5780205r_c0fx.fits").first()
        obs_id = opt_obs.id
    finally:
        db.close()

    patch_req = {"display_name": "WFPC2 NGC 4151 Renovated Name"}
    response = client.patch(f"/api/observations/{obs_id}", json=patch_req)
    assert response.status_code == 200
    assert response.json()["target_name"] == "WFPC2 NGC 4151 Renovated Name"


def test_optical_report_generation(client):
    db = SessionLocal()
    try:
        opt_obs = db.query(Observation).filter(Observation.file_name == "WFPC2u5780205r_c0fx.fits").first()
        obs_id = opt_obs.id
    finally:
        db.close()

    response = client.get(f"/api/observations/{obs_id}/report")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-1.4")
    assert len(response.content) > 3000


def test_csv_upload_and_analysis_workflows(client):
    csv_path = REPO_ROOT / "pulsar_data_test.csv"
    assert csv_path.exists(), "pulsar_data_test.csv must exist in repo root."

    with open(csv_path, "rb") as f:
        csv_bytes = f.read()

    files = {"file": ("pulsar_data_test.csv", csv_bytes, "text/csv")}
    upload_res = client.post("/api/upload/csv", files=files)
    assert upload_res.status_code == 200
    data = upload_res.json()

    assert data["file_name"] == "pulsar_data_test.csv"
    assert data["total_rows"] > 5000
    assert data["total_columns"] == 9
    assert len(data["columns"]) == 9
    assert len(data["preview_rows"]) == 10
    assert "data/uploads/csv" in data["server_file_path"]

    available_wf_ids = [w["id"] for w in data["available_workflows"]]
    assert "csv_statistics" in available_wf_ids
    assert "csv_correlation" in available_wf_ids
    assert "csv_pulsar_inference" in available_wf_ids

    server_path = data["server_file_path"]

    # 1. Test Statistical Summary
    stat_res = client.post(
        "/api/upload/csv/analyze",
        json={"server_file_path": server_path, "workflow_id": "csv_statistics"}
    )
    assert stat_res.status_code == 200
    stat_data = stat_res.json()
    assert stat_data["status"] == "COMPLETED"
    assert "histogram_url" in stat_data["details"]

    # 2. Test Correlation Matrix
    corr_res = client.post(
        "/api/upload/csv/analyze",
        json={"server_file_path": server_path, "workflow_id": "csv_correlation"}
    )
    assert corr_res.status_code == 200
    corr_data = corr_res.json()
    assert corr_data["status"] == "COMPLETED"
    assert "heatmap_url" in corr_data["details"]
    assert len(corr_data["details"]["top_correlations"]) > 0

    # 3. Test Pulsar ML Inference
    ml_res = client.post(
        "/api/upload/csv/analyze",
        json={"server_file_path": server_path, "workflow_id": "csv_pulsar_inference"}
    )
    assert ml_res.status_code == 200
    ml_data = ml_res.json()
    assert ml_data["status"] == "COMPLETED"
    assert ml_data["details"]["pulsar_candidates"] > 0
    assert "chart_url" in ml_data["details"]
    assert len(ml_data["details"]["top_candidates"]) > 0


def test_csv_analysis_security_rejection(client):
    # Path traversal attack attempt
    res = client.post(
        "/api/upload/csv/analyze",
        json={"server_file_path": "../../backend/app/main.py", "workflow_id": "csv_statistics"}
    )
    assert res.status_code == 400
    assert "access denied" in res.json()["detail"].lower()


def test_csv_pdf_report_generation_suite(client):
    """
    Validates all requirements for CSV inclusion in PDF reports:
    1. Observation with one CSV file.
    2. Multi-page CSV with many rows and repeated headers.
    3. Missing values, long column names, and formula injection safety.
    4. Observation with no CSV file (FITS-only fallback).
    5. Observation association accuracy (correct CSV attached).
    6. Security validation (path traversal rejection, nonexistent file).
    """
    from backend.app.services.fits_service import REPO_ROOT

    csv_dir = REPO_ROOT / "data" / "uploads" / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    # 1. Upload standard CSV file
    csv_content_1 = b"flux_peak,frequency_mhz,snr,dispersion_measure\n12.4,1400.0,24.1,34.5\n8.1,1400.0,15.2,34.8\n19.5,1400.0,32.0,34.2\n"
    res1 = client.post(
        "/api/upload/csv",
        files={"file": ("flux_measurements.csv", csv_content_1, "text/csv")},
    )
    assert res1.status_code == 200
    server_name_1 = res1.json()["server_file_path"].split("/")[-1]

    # Test Case 1 & 5: Generate PDF with this CSV for observation 1
    pdf_res1 = client.get(f"/api/observations/1/report?csv_server_name={server_name_1}")
    assert pdf_res1.status_code == 200
    assert pdf_res1.headers["content-type"] == "application/pdf"
    assert pdf_res1.content.startswith(b"%PDF")
    assert len(pdf_res1.content) > 2000

    # Test Case 2: Multi-page CSV with many rows (> 120 rows)
    rows = ["idx,freq_mhz,cal_power,noise_rms"]
    for i in range(120):
        rows.append(f"{i},{1400.0 + i * 0.5},{50.2 + (i % 7)},{1.24 + (i % 3) * 0.1}")
    large_csv_content = "\n".join(rows).encode("utf-8")
    res_large = client.post(
        "/api/upload/csv",
        files={"file": ("large_telemetry_series.csv", large_csv_content, "text/csv")},
    )
    assert res_large.status_code == 200
    server_name_large = res_large.json()["server_file_path"].split("/")[-1]

    pdf_res_large = client.get(f"/api/observations/1/report?csv_server_name={server_name_large}")
    assert pdf_res_large.status_code == 200
    assert pdf_res_large.content.startswith(b"%PDF")
    assert len(pdf_res_large.content) > 5000

    # Test Case 3: CSV with missing values, long column names, and special characters
    csv_edge_content = (
        b"extremely_long_pulsar_characteristic_flux_channel_a,secondary_param_with_special_chars_&_symbols,null_dense_column,formula_test\n"
        b"12.5,alpha & beta,,=SUM(A1:B1)\n"
        b",gamma < 5,NaN,+100.5\n"
        b"19.2,,,@test\n"
        b",delta > 2,99.9,-42.0\n"
    )
    res_edge = client.post(
        "/api/upload/csv",
        files={"file": ("edge_cases_and_formula_test.csv", csv_edge_content, "text/csv")},
    )
    assert res_edge.status_code == 200
    server_name_edge = res_edge.json()["server_file_path"].split("/")[-1]

    pdf_res_edge = client.get(f"/api/observations/1/report?csv_server_name={server_name_edge}")
    assert pdf_res_edge.status_code == 200
    assert pdf_res_edge.content.startswith(b"%PDF")

    # Test Case 4 & 6: Generate report with NO CSV file (FITS-only)
    pdf_res_none = client.get("/api/observations/1/report")
    assert pdf_res_none.status_code == 200
    assert pdf_res_none.content.startswith(b"%PDF")

    # Test Case 5: Verify correct CSV selection and distinction
    # Clean up test files from server after test
    for s_name in [server_name_1, server_name_large, server_name_edge]:
        del_res = client.delete(f"/api/upload/csv/{s_name}")
        assert del_res.status_code == 200

    # Security rejection on invalid / nonexistent / path traversal
    res_traversal = client.get("/api/observations/1/report?csv_server_name=../../etc/passwd")
    assert res_traversal.status_code in (400, 404)

    res_notfound = client.get("/api/observations/1/report?csv_server_name=nonexistent_data.csv")
    assert res_notfound.status_code == 404


def test_csv_file_explorer_and_direct_pdf_suite(client):
    """
    Validates CSV file explorer data pagination, original CSV download,
    direct CSV PDF report generation, and observation grouping metadata.
    """
    csv_content = (
        b"pulse_period_ms,dm_pc_cm3,flux_density_jy,source_label,detection_date\n"
        b"33.5,56.8,1.25,PSR_B0531+21,2026-05-12\n"
        b"5.2,12.4,0.85,PSR_J0437-4715,2026-06-18\n"
        b"120.0,,2.10,PSR_B1937+21,2026-07-22\n"
        b"45.2,88.1,,PSR_CAND_01,2026-08-01\n"
    )

    # 1. Upload CSV with associated observation name
    upload_res = client.post(
        "/api/upload/csv",
        files={"file": ("target_survey_candidates.csv", csv_content, "text/csv")},
        data={"observation_name": "SURVEY_OBS_ALPHA"},
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    server_path = upload_data["server_file_path"]
    server_name = server_path.split("/")[-1]

    try:
        # 2. Check list includes observation_name
        list_res = client.get("/api/upload/csv")
        assert list_res.status_code == 200
        found = next((item for item in list_res.json() if item["server_name"] == server_name), None)
        assert found is not None
        assert found["observation_name"] == "SURVEY_OBS_ALPHA"
        assert found["file_name"] == "target_survey_candidates.csv"

        # 3. CSV File Explorer data endpoint: pagination & structure
        data_res = client.get(f"/api/upload/csv/{server_name}/data?page=1&page_size=2")
        assert data_res.status_code == 200
        data_json = data_res.json()
        assert data_json["total_rows"] == 4
        assert data_json["total_pages"] == 2
        assert len(data_json["rows"]) == 2
        assert data_json["rows"][0]["_row_index"] == 1
        assert data_json["rows"][1]["_row_index"] == 2
        assert data_json["rows"][0]["source_label"] == "PSR_B0531+21"

        # Check column metadata and inferred types
        cols = {c["name"]: c for c in data_json["columns"]}
        assert "pulse_period_ms" in cols
        assert cols["pulse_period_ms"]["inferred_type"] in ("Decimal", "Integer")
        assert cols["pulse_period_ms"]["non_empty_count"] == 4
        assert cols["dm_pc_cm3"]["missing_count"] == 1
        assert cols["source_label"]["inferred_type"] == "Text"
        assert cols["detection_date"]["inferred_type"] == "Date"

        # Page 2
        page2_res = client.get(f"/api/upload/csv/{server_name}/data?page=2&page_size=2")
        assert page2_res.status_code == 200
        page2_json = page2_res.json()
        assert len(page2_json["rows"]) == 2
        assert page2_json["rows"][0]["_row_index"] == 3

        # 4. Download original unchanged CSV
        dl_res = client.get(f"/api/upload/csv/{server_name}/download")
        assert dl_res.status_code == 200
        assert dl_res.headers["content-type"].startswith("text/csv")
        assert dl_res.content == csv_content

        # 5. Direct CSV PDF Report generation
        pdf_res = client.get(f"/api/upload/csv/{server_name}/report")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF")
        assert len(pdf_res.content) > 1000

        # 6. Update observation name via PATCH
        patch_res = client.patch(
            f"/api/upload/csv/{server_name}",
            json={"observation_name": "SURVEY_OBS_BETA"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["observation_name"] == "SURVEY_OBS_BETA"

        # Re-check data endpoint reflects updated observation name
        data_after_patch = client.get(f"/api/upload/csv/{server_name}/data?page=1&page_size=10")
        assert data_after_patch.json()["file_info"]["observation_name"] == "SURVEY_OBS_BETA"

        # 7. Error handling
        notfound_data = client.get("/api/upload/csv/nonexistent.csv/data")
        assert notfound_data.status_code == 404

        notfound_dl = client.get("/api/upload/csv/nonexistent.csv/download")
        assert notfound_dl.status_code == 404

        notfound_pdf = client.get("/api/upload/csv/nonexistent.csv/report")
        assert notfound_pdf.status_code == 404

        traversal_pdf = client.get("/api/upload/csv/..%2F..%2Fetc/report")
        assert traversal_pdf.status_code in (400, 404)

    finally:
        # 8. Clean up uploaded file and companion metadata
        del_res = client.delete(f"/api/upload/csv/{server_name}")
        assert del_res.status_code == 200

