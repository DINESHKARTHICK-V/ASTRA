# ============================================================
#  ASTRA Cloud — Dataset Integration & Experiments Unit Tests
#  File   : backend/tests/test_dataset_experiments.py
#  Purpose: Comprehensive mocked and live tests for HTRU2 &
#           Parkes dataset readers, Five Research Problems
#           (P1 through P5), API endpoints, and PDF generation.
# ============================================================

import os
import json
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.database import engine, Base
from backend.app.models import ProcessingRun
from backend.app.services.dataset_service import dataset_registry
from backend.app.services.research_experiments_service import research_experiments
from backend.app.services.report_service import generate_two_dataset_experiments_pdf


@pytest.fixture(scope="module")
def client():
    """Ensure processing_runs table exists and provide TestClient."""
    Base.metadata.create_all(bind=engine, tables=[ProcessingRun.__table__], checkfirst=True)
    return TestClient(app)


def test_list_registered_datasets():
    datasets = dataset_registry.list_registered_datasets()
    assert len(datasets) >= 2
    ds_ids = [d["id"] for d in datasets]
    assert "DATASET_A_HTRU2" in ds_ids
    assert "DATASET_B_PARKES" in ds_ids
    assert "DATASET_C_GBT_VEGAS" in ds_ids

    htru2 = next(d for d in datasets if d["id"] == "DATASET_A_HTRU2")
    assert htru2["validation_status"] == "VALIDATED"
    assert htru2["record_count"] == 17898
    assert htru2["label_availability"] is True
    assert "Supervised Pulsar Classification" in htru2["supported_experiment_types"]

    parkes = next(d for d in datasets if d["id"] == "DATASET_B_PARKES")
    assert parkes["validation_status"] == "VALIDATED"
    assert parkes["record_count"] == 40
    assert parkes["feature_count"] == 512
    assert parkes["label_availability"] is False
    assert "Frequency Channel Masking & Excision (P2)" in parkes["supported_experiment_types"]

    gbt = next(d for d in datasets if d["id"] == "DATASET_C_GBT_VEGAS")
    assert gbt["validation_status"] == "VALIDATED"
    assert gbt["record_count"] == 12



def test_dataset_readers():
    # 1. HTRU2 Reader
    df, prov_a = dataset_registry.read_htru2()
    assert df.shape[0] == 17898
    assert df.shape[1] == 9
    assert "Profile_Mean" in df.columns
    assert "Target" in df.columns
    assert prov_a["class_distribution"]["positive_pulsar"] == 1639
    assert prov_a["class_distribution"]["negative_noise_rfi"] == 16259

    # 2. Parkes PSRFITS Reader
    matrix, prov_b = dataset_registry.read_parkes_psrfits(max_subints=2)
    assert matrix.shape == (8192, 512)
    assert prov_b["telescope"] == "PARKES"
    assert prov_b["nchan"] == 512
    assert prov_b["source_name"] == "J0437-4715"


def test_p1_perturbation_and_controlled_noise():
    df, _ = dataset_registry.read_htru2()
    features = [
        "Profile_Mean", "Profile_Std", "Profile_Skewness", "Profile_Kurtosis",
        "DM_Mean", "DM_Std", "DM_Skewness", "DM_Kurtosis"
    ]
    X_test = df[features].iloc[:200].values
    y_test = df["Target"].iloc[:200].values
    model = research_experiments._load_htru2_model()

    parkes_matrix, _ = dataset_registry.read_parkes_psrfits(max_subints=2)

    res_p1 = research_experiments.evaluate_p1_perturbations(X_test, y_test, model, parkes_matrix, seed=42)
    assert res_p1["problem"].startswith("P1")
    assert len(res_p1["htru2_perturbations"]) == 6
    assert len(res_p1["parkes_noise_experiments"]) == 6

    # Verify baseline is cleanest
    baseline_htru2 = res_p1["htru2_perturbations"][0]
    high_noise_htru2 = res_p1["htru2_perturbations"][-1]
    assert baseline_htru2["accuracy"] >= high_noise_htru2["accuracy"]

    # Verify synthetic noise labeling
    assert "strictly distinguished from empirical telescope RFI" in res_p1["scientific_note"]


def test_p2_channel_masking():
    parkes_matrix, _ = dataset_registry.read_parkes_psrfits(max_subints=2)
    res_p2 = research_experiments.evaluate_p2_channel_masking(parkes_matrix, seed=42)

    assert res_p2["problem"].startswith("P2")
    assert res_p2["baseline_channels"] == 512
    assert len(res_p2["masking_experiments"]) == 6

    # Recoverability index must drop at 75% masking compared to 5%
    rec_5pct = res_p2["masking_experiments"][0]["recoverability_index"]
    rec_75pct = res_p2["masking_experiments"][-1]["recoverability_index"]
    assert rec_5pct > rec_75pct
    assert res_p2["masking_experiments"][-1]["status"] == "DEGRADED"


def test_p3_cross_compatibility():
    res_p3 = research_experiments.evaluate_p3_compatibility()
    assert res_p3["verdict"] == "INCOMPATIBLE_BY_DESIGN"
    assert "HALTED" in res_p3["transfer_evaluation_status"]
    assert len(res_p3["compatibility_matrix"]) == 4
    assert all(not r["compatible"] for r in res_p3["compatibility_matrix"])
    assert len(res_p3["prerequisite_pipeline_steps"]) == 4


def test_p4_confidence_calibration():
    df, _ = dataset_registry.read_htru2()
    features = [
        "Profile_Mean", "Profile_Std", "Profile_Skewness", "Profile_Kurtosis",
        "DM_Mean", "DM_Std", "DM_Skewness", "DM_Kurtosis"
    ]
    X_test = df[features].iloc[:500].values
    y_test = df["Target"].iloc[:500].values
    model = research_experiments._load_htru2_model()

    res_p4 = research_experiments.evaluate_p4_calibration(X_test, y_test, model, n_bins=10)
    assert res_p4["problem"].startswith("P4")
    assert 0.0 <= res_p4["brier_score"] <= 1.0
    assert 0.0 <= res_p4["expected_calibration_error_ece"] <= 1.0
    assert len(res_p4["reliability_diagram_bins"]) == 10


def test_p5_failure_analysis():
    df, _ = dataset_registry.read_htru2()
    features = [
        "Profile_Mean", "Profile_Std", "Profile_Skewness", "Profile_Kurtosis",
        "DM_Mean", "DM_Std", "DM_Skewness", "DM_Kurtosis"
    ]
    X_test = df[features].iloc[:500].values
    y_test = df["Target"].iloc[:500].values
    model = research_experiments._load_htru2_model()
    parkes_matrix, _ = dataset_registry.read_parkes_psrfits(max_subints=2)

    res_p5 = research_experiments.evaluate_p5_failure_analysis(X_test, y_test, model, parkes_matrix, seed=42)
    assert res_p5["problem"].startswith("P5")
    h_fail = res_p5["htru2_classification_failures"]
    assert "counts" in h_fail
    assert "false_positives" in h_fail["counts"]
    assert "false_negatives" in h_fail["counts"]
    assert "fp_mechanism" in h_fail
    assert "fn_mechanism" in h_fail

    p_fail = res_p5["parkes_signal_quality_failures"]
    assert "critical_masking_threshold" in p_fail
    assert "critical_noise_threshold" in p_fail


def test_api_datasets_endpoints(client):
    # 1. GET /api/datasets
    resp = client.get("/api/datasets")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # 2. GET /api/datasets/status
    status_resp = client.get("/api/datasets/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "READY"

    # 3. GET /api/datasets/experiments/results
    results_resp = client.get("/api/datasets/experiments/results")
    assert results_resp.status_code == 200
    results_data = results_resp.json()
    assert "problems" in results_data
    assert "p1_perturbations" in results_data["problems"]
    assert "p2_channel_masking" in results_data["problems"]
    assert "p3_cross_compatibility" in results_data["problems"]
    assert "p4_confidence_calibration" in results_data["problems"]
    assert "p5_failure_analysis" in results_data["problems"]

    # 4. POST /api/datasets/experiments/run
    try:
        run_resp = client.post("/api/datasets/experiments/run", json={"seed": 42, "record_processing_run": True})
        assert run_resp.status_code == 200
        run_data = run_resp.json()
        assert run_data["reproducible_seed"] == 42
    finally:
        with engine.begin() as conn:
            from sqlalchemy import text
            conn.execute(text("DELETE FROM processing_runs WHERE pipeline_step = 'RESEARCH_DATASET_EXPERIMENT_P1_P5';"))


def test_api_download_experiments_pdf(client):
    resp = client.get("/api/datasets/experiments/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 5000
    assert resp.content.startswith(b"%PDF")


def test_api_master_dataset_and_shap(client):
    # 1. Master Dataset Preview
    resp = client.get("/api/datasets/master/preview?limit=10")
    assert resp.status_code == 200
    preview = resp.json()
    assert preview["total_records"] == 17950
    assert preview["htru2_count"] == 17898
    assert preview["parkes_subints"] == 40
    assert len(preview["records"]) == 10

    # Test filtering by source
    resp_parkes = client.get("/api/datasets/master/preview?source=PARKES_PDFB4")
    assert resp_parkes.status_code == 200
    p_data = resp_parkes.json()
    assert p_data["total_records"] == 40
    assert all(r["source_archive"] == "PARKES_PDFB4" for r in p_data["records"])

    # 2. Master Manifest
    resp_m = client.get("/api/datasets/master/manifest")
    assert resp_m.status_code == 200
    manifest = resp_m.json()
    assert manifest["record_summary"]["total_records"] == 17950
    assert any("f1238937" in str(cat.get("sha256", "")) for cat in manifest.get("source_catalog", []))

    # 3. Validation Report
    resp_v = client.get("/api/datasets/master/validation")
    assert resp_v.status_code == 200
    val_report = resp_v.json()
    assert val_report["total_master_records"] == 17950
    assert all(check["passed"] for check in val_report["validation_checks"])

    # 4. Data Dictionary
    resp_dd = client.get("/api/datasets/master/data-dictionary")
    assert resp_dd.status_code == 200
    dd = resp_dd.json()
    assert len(dd) >= 41

    # 5. SHAP Analysis
    resp_s = client.get("/api/datasets/shap")
    assert resp_s.status_code == 200
    shap_data = resp_s.json()
    assert shap_data["explainer_type"] == "TreeExplainer"
    assert len(shap_data["feature_importances"]) == 8
    assert shap_data["feature_importances"][0]["feature"] == "Profile_Skewness"


