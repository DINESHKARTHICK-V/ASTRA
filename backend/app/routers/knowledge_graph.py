# ============================================================
#  ASTRA Cloud — Neo4j Knowledge Graph Router
#  File   : backend/app/routers/knowledge_graph.py
#  Purpose: FastAPI endpoints for Neo4j astronomy research graph
#           connectivity, schema initialization, entity synchronization,
#           subgraph extraction, and graph topology queries.
# ============================================================

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Observation, ResearchRecord
from backend.app.services.neo4j_service import neo4j_graph_service
from backend.app.services.dataset_service import dataset_service

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])


@router.get("/status")
def get_graph_status():
    """
    Check live connectivity to the Neo4j Knowledge Graph.
    Returns honest connection status, node/edge counts, and connection URI.
    """
    is_conn, message, telemetry = neo4j_graph_service.check_connectivity()
    return {
        "connected": is_conn,
        "message": message,
        "telemetry": telemetry,
    }


@router.post("/init-schema")
def init_graph_schema():
    """
    Initialize idempotent constraints and indexes in Neo4j.
    """
    res = neo4j_graph_service.init_schema()
    return res


@router.post("/sync")
def sync_knowledge_graph(db: Session = Depends(get_db)):
    """
    Synchronize astronomy research entities into Neo4j using idempotent MERGE:
    - Master and child Datasets (HTRU2, Parkes, GBT, Master)
    - Physical Pulsars (PSR J1713+0747, PSR J0437-4715)
    - Observations from PostgreSQL
    - Models (Random Forest, SVM, MLP, XGBoost)
    - Features & SHAP rankings
    - Five Research Experiments (P1–P5)
    - Academic Research Papers
    """
    # 1. Fetch observations from PostgreSQL
    obs_rows = db.query(Observation).all()
    obs_list = [
        {
            "id": o.id,
            "file_name": o.file_name,
            "telescope": o.telescope,
            "target_name": o.target_name,
            "observation_date": o.observation_date,
            "validation_status": o.validation_status,
        }
        for o in obs_rows
    ]

    # 2. Fetch research records from PostgreSQL
    rec_rows = db.query(ResearchRecord).all()
    rec_list = [
        {
            "id": r.id,
            "title": r.title,
            "identifier": r.identifier,
            "source_name": r.source_name,
            "canonical_url": r.canonical_url,
            "publication_date": r.publication_date,
        }
        for r in rec_rows
    ]

    # 3. Read experiment outputs
    from pathlib import Path
    report_file = Path(__file__).resolve().parent.parent.parent.parent / "reports" / "two_dataset_integration_report.json"
    exp_report = {}
    if report_file.exists():
        try:
            import json
            with open(report_file, "r", encoding="utf-8") as f:
                exp_report = json.load(f)
        except Exception:
            exp_report = {}

    # 4. Sync into Neo4j
    sync_result = neo4j_graph_service.sync_astronomy_entities(
        observations=obs_list,
        research_records=rec_list,
        experiments_data=exp_report,
    )

    return sync_result


@router.get("/subgraph")
def get_subgraph(
    limit: int = Query(default=100, ge=1, le=500),
    label: Optional[str] = Query(default=None),
    fallback_verified: bool = Query(default=True, description="When Neo4j daemon is offline, return verified research topology from PostgreSQL/master dataset"),
):
    """
    Fetch nodes and relationships formatted for interactive graph visualization.
    """
    return neo4j_graph_service.get_graph_subgraph(limit=limit, label_filter=label, fallback_verified=fallback_verified)


@router.get("/statistics")
def get_graph_statistics(
    fallback_verified: bool = Query(default=True, description="When Neo4j daemon is offline, return counts of verified research entities"),
):
    """
    Return node counts by label and relationship counts by type.
    """
    return neo4j_graph_service.get_graph_statistics(fallback_verified=fallback_verified)


@router.get("/stats")
def get_graph_stats_alias(
    fallback_verified: bool = Query(default=True),
):
    """
    Alias for /statistics for client backwards compatibility.
    """
    return neo4j_graph_service.get_graph_statistics(fallback_verified=fallback_verified)


@router.post("/query")
def execute_graph_query(payload: Dict[str, Any]):
    """
    Execute a parameterized Cypher query on the Neo4j Astronomy Knowledge Graph.
    Example payload: {"query": "MATCH (d:Dataset) RETURN d.name, d.id", "parameters": {}}
    """
    cypher = payload.get("query", "MATCH (n) RETURN n LIMIT 10")
    params = payload.get("parameters", {})
    return neo4j_graph_service.execute_query(query=cypher, parameters=params)
