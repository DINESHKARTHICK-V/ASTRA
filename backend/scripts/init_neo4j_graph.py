# ============================================================
#  ASTRA Cloud — Neo4j Knowledge Graph Initialization & Sync
#  File   : backend/scripts/init_neo4j_graph.py
#  Purpose: Initializes constraints and synchronizes astronomy
#           research entities into Neo4j from PostgreSQL and Master Dataset.
# ============================================================

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.app.database import SessionLocal
from backend.app.models import Observation, ResearchRecord
from backend.app.services.neo4j_service import neo4j_graph_service
from backend.app.services.dataset_service import dataset_service


def main():
    print("=" * 70)
    print("ASTRA CLOUD — Neo4j Knowledge Graph Initialization & Sync")
    print("=" * 70)

    # 1. Connectivity Check
    is_conn, msg, telemetry = neo4j_graph_service.check_connectivity()
    print(f"Target Neo4j URI : {neo4j_graph_service.uri}")
    print(f"Connection Status: {'ONLINE' if is_conn else 'OFFLINE'} ({msg})")

    if not is_conn:
        print("\n[NOTE] Neo4j database is currently unreachable.")
        print("To start a local Neo4j instance, use Docker or the desktop application:")
        print("  docker compose up -d neo4j")
        print("Or run Neo4j Community Edition on bolt://localhost:7687.")
        print("The application will run with honest connection status handling.")
        return False

    # 2. Schema Initialization
    print("\n--- Initializing Graph Schema Constraints & Indexes ---")
    schema_res = neo4j_graph_service.init_schema()
    print(f"Result: {schema_res.get('message')}")
    for item in schema_res.get("results", []):
        status = item.get("status")
        stmt = item.get("statement", "")[:55]
        print(f"  [{status}] {stmt}...")

    # 3. Synchronize Entities
    print("\n--- Synchronizing Astronomy Entities into Neo4j ---")
    db = SessionLocal()
    try:
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
    finally:
        db.close()

    report_file = ROOT / "reports" / "two_dataset_integration_report.json"
    exp_report = {}
    if report_file.exists():
        try:
            import json
            with open(report_file, "r", encoding="utf-8") as f:
                exp_report = json.load(f)
        except Exception:
            exp_report = {}

    sync_res = neo4j_graph_service.sync_astronomy_entities(
        observations=obs_list,
        research_records=rec_list,
        experiments_data=exp_report,
    )
    print(f"Result: {sync_res.get('message')}")
    print(f"Counts: {sync_res.get('counts')}")

    # 4. Verify with Cypher Statistics
    stats = neo4j_graph_service.get_graph_statistics()
    print("\n--- Graph Topology Verification ---")
    print(f"Total Nodes        : {stats.get('total_nodes')}")
    print(f"Total Relationships: {stats.get('total_relationships')}")
    print(f"Node Labels        : {stats.get('labels')}")
    print(f"Relationship Types : {stats.get('relationships')}")
    print("\nKnowledge Graph sync complete.")
    return True


if __name__ == "__main__":
    main()
