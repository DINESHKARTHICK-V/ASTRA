# ============================================================
#  ASTRA Cloud — MLflow Tracking Unit & Integration Tests
#  File   : backend/tests/test_mlflow_tracker.py
#  Purpose: Validates MLflow connectivity, experiment lifecycle,
#           parameter and metric logging, run querying, and artifact recording.
# ============================================================

import os
import pytest
from backend.app.services.mlflow_service import mlflow_tracker_service


def test_mlflow_connectivity():
    """Verify live connectivity to MLflow tracking store."""
    is_conn, message, telemetry = mlflow_tracker_service.check_connectivity()
    assert is_conn is True
    assert "active" in message.lower()
    assert telemetry.get("status") == "ONLINE"
    assert "tracking_uri" in telemetry


def test_mlflow_log_research_run():
    """Verify logging parameters, metrics, and tags to an experiment."""
    res = mlflow_tracker_service.log_research_run(
        experiment_name="ASTRA_Test_Suite_Experiment",
        run_name="Test_RF_Run_001",
        params={"model": "RandomForest", "n_estimators": 50, "seed": 42},
        metrics={"accuracy": 0.9816, "f1_score": 0.8952, "roc_auc": 0.9668},
        tags={"environment": "pytest", "test_id": "test_001"},
    )
    assert res.get("success") is True
    assert "run_id" in res
    assert res.get("metrics_logged") == 3
    assert res.get("params_logged") == 3


def test_mlflow_list_experiments_and_runs():
    """Verify querying experiments and retrieving logged runs."""
    exps = mlflow_tracker_service.list_experiments()
    assert isinstance(exps, list)
    assert len(exps) >= 1
    exp_names = [e["name"] for e in exps]
    assert "ASTRA_Test_Suite_Experiment" in exp_names

    runs = mlflow_tracker_service.list_runs(experiment_name="ASTRA_Test_Suite_Experiment")
    assert isinstance(runs, list)
    assert len(runs) >= 1
    run = runs[0]
    assert "accuracy" in run["metrics"]
    assert pytest.approx(run["metrics"]["accuracy"], 0.001) == 0.9816
    assert run["params"]["model"] == "RandomForest"


def test_mlflow_get_best_run():
    """Verify retrieving top-performing run by metric."""
    # Log a second run with lower F1
    mlflow_tracker_service.log_research_run(
        experiment_name="ASTRA_Test_Suite_Experiment",
        run_name="Test_RF_Run_002_Lower",
        params={"model": "RandomForest", "n_estimators": 10},
        metrics={"accuracy": 0.9500, "f1_score": 0.7500},
    )

    best = mlflow_tracker_service.get_best_run(
        experiment_name="ASTRA_Test_Suite_Experiment", metric_name="f1_score"
    )
    assert best is not None
    assert pytest.approx(best["metrics"]["f1_score"], 0.001) == 0.8952


def test_mlflow_sync_research_experiments():
    """Verify empirical synchronization of all 5 research problems."""
    res = mlflow_tracker_service.sync_project_experiments_to_mlflow()
    assert res.get("success") is True
    assert res.get("runs_logged") >= 10

    # Verify HTRU2 classification experiment
    rf_best = mlflow_tracker_service.get_best_run("ASTRA_HTRU2_Classification", "f1_score")
    assert rf_best is not None
    assert pytest.approx(rf_best["metrics"]["f1_score"], 0.001) == 0.8952
    assert pytest.approx(rf_best["metrics"]["roc_auc"], 0.001) == 0.9668
