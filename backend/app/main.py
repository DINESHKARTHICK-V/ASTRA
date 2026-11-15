# ============================================================
#  ASTRA — FastAPI Main Application Entrypoint
#  File   : backend/app/main.py
#  Purpose: Initializes FastAPI application, registers routers,
#           and exposes root and health status endpoints.
# ============================================================

from datetime import datetime, timezone
from fastapi import FastAPI, status, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database import check_db_connectivity
from backend.app.schemas import HealthResponse, RootInfoResponse
from backend.app.routers import (
    observations,
    features_predictions,
    candidates,
    upload,
    analysis,
    csv_upload,
    collector,
    datasets,
    knowledge_graph,
    mlflow_tracker,
)

API_TITLE = "ASTRA API"
API_VERSION = "1.0.0"
API_DESCRIPTION = (
    "AI-Assisted Astronomical Observation Intelligence & Candidate Prioritization REST API. "
    "Supports multi-type FITS ingestion, optical image visualization, radio Stokes I moment extraction, "
    "safeguarded ML inference, and ACIS candidate intelligence prioritization."
)

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(observations.router)
app.include_router(features_predictions.router)
app.include_router(candidates.router)
app.include_router(upload.router)
app.include_router(analysis.router)
app.include_router(csv_upload.router)
app.include_router(collector.router)
app.include_router(datasets.router)
app.include_router(knowledge_graph.router)
app.include_router(mlflow_tracker.router)


@app.get(
    "/",
    response_model=RootInfoResponse,
    summary="ASTRA Service Information",
    description="Provides basic project metadata, version, and catalog of primary API routes."
)
def get_service_info():
    return RootInfoResponse(
        project=API_TITLE,
        version=API_VERSION,
        description="ASTRA research backend serving radio & optical observation catalog, FITS analysis, and ACIS prioritization.",
        docs_url="/docs",
        endpoints={
            "service_info": "/",
            "health_check": "/health",
            "swagger_docs": "/docs",
            "upload_fits": "/api/upload",
            "upload_csv": "/api/upload/csv",
            "analyze_csv": "/api/upload/csv/analyze",
            "start_analysis": "/api/analysis/start",
            "observations_list": "/api/observations",
            "observation_detail": "/api/observations/{id}",
            "observation_preview": "/api/observations/{id}/preview",
            "observation_features": "/api/observations/{id}/features",
            "observation_predictions": "/api/observations/{id}/predictions",
            "candidates_ranking": "/api/candidates",
            "candidate_detail": "/api/candidates/{id}",
            "processing_runs": "/api/processing-runs",
            "collector_sources": "/api/collector/sources",
            "collector_query": "/api/collector/query",
            "collector_records": "/api/collector/records",
            "graph_status": "/api/graph/status",
            "graph_statistics": "/api/graph/statistics",
            "graph_subgraph": "/api/graph/subgraph",
            "mlflow_status": "/api/mlflow/status",
            "mlflow_experiments": "/api/mlflow/experiments",
            "mlflow_runs": "/api/mlflow/runs",
            "mlflow_best_run": "/api/mlflow/best-run",
        }
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check & database connectivity",
    description="Verifies the API runtime and tests live connectivity to the PostgreSQL astra_cloud database."
)
def get_health_status(response: Response):
    is_connected, message = check_db_connectivity()
    current_time = datetime.now(timezone.utc)

    if not is_connected:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="degraded",
            database_connected=False,
            database_message=message,
            timestamp=current_time,
        )

    return HealthResponse(
        status="healthy",
        database_connected=True,
        database_message=message,
        timestamp=current_time,
    )
