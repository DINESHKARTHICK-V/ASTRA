# ============================================================
#  ASTRA Cloud — MLflow Tracking Router
#  File   : backend/app/routers/mlflow_tracker.py
#  Purpose: FastAPI endpoints for MLflow experiment tracking,
#           runs exploration, parameter & metric retrieval,
#           model comparisons, and artifact inspections.
# ============================================================

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query

from backend.app.services.mlflow_service import mlflow_tracker_service

router = APIRouter(prefix="/api/mlflow", tags=["MLflow Tracking"])


@router.get("/status")
def get_mlflow_status():
    """
    Check connectivity to the MLflow tracking store.
    Returns tracking URI, UI URL, total experiments, and run counts.
    """
    is_conn, message, telemetry = mlflow_tracker_service.check_connectivity()
    return {
        "connected": is_conn,
        "message": message,
        "telemetry": telemetry,
    }


@router.get("/experiments")
def list_experiments():
    """
    List all MLflow registered experiments with run telemetry.
    """
    return mlflow_tracker_service.list_experiments()


@router.get("/runs")
def list_runs(
    experiment_name: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    List tracked runs across one or all experiments with parameters and metrics.
    """
    return mlflow_tracker_service.list_runs(experiment_name=experiment_name, limit=limit)


@router.get("/best-run")
def get_best_run(
    experiment_name: str = Query(default="ASTRA_HTRU2_Classification"),
    metric_name: str = Query(default="f1_score"),
):
    """
    Retrieve the optimal run for a specified experiment based on target metric.
    """
    best = mlflow_tracker_service.get_best_run(experiment_name=experiment_name, metric_name=metric_name)
    if not best:
        raise HTTPException(status_code=404, detail="No matching runs found with specified metric")
    return best


@router.post("/sync-research-experiments")
def sync_research_experiments():
    """
    Execute empirical synchronization: registers all 5 research problems and
    model benchmarks into MLflow with verified parameters, metrics, and artifacts.
    """
    res = mlflow_tracker_service.sync_project_experiments_to_mlflow()
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("message"))
    return res
