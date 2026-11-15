# ============================================================
#  ASTRA Cloud — Neo4j Knowledge Graph Unit & Integration Tests
#  File   : backend/tests/test_neo4j_graph.py
#  Purpose: Validates Neo4j connectivity check, honest error handling,
#           graph schema statements, and idempotent MERGE synchronization.
# ============================================================

from unittest.mock import MagicMock, patch
import pytest
from backend.app.services.neo4j_service import Neo4jGraphService, neo4j_graph_service


def test_neo4j_connectivity_offline_handling():
    """Verify that when Neo4j is offline, connectivity check returns honest status without raising."""
    svc = Neo4jGraphService(uri="bolt://localhost:9999", user="neo4j", password="bad")
    is_conn, msg, telemetry = svc.check_connectivity()
    assert is_conn is False
    assert "unavailable" in msg.lower() or "failed" in msg.lower()
    assert telemetry.get("status") in ("OFFLINE", "ERROR")


def test_neo4j_get_statistics_offline():
    """Verify that get_graph_statistics returns honest offline status."""
    svc = Neo4jGraphService(uri="bolt://localhost:9999")
    stats = svc.get_graph_statistics()
    assert stats["connected"] is False
    assert stats["total_nodes"] == 0
    assert stats["total_relationships"] == 0


def test_neo4j_get_subgraph_offline():
    """Verify that get_graph_subgraph returns empty topology with status."""
    svc = Neo4jGraphService(uri="bolt://localhost:9999")
    subgraph = svc.get_graph_subgraph()
    assert subgraph["nodes"] == []
    assert subgraph["edges"] == []
    assert subgraph["summary"]["connected"] is False


def test_neo4j_mock_schema_initialization():
    """Verify schema initialization executes all required constraints and indexes."""
    svc = Neo4jGraphService()
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    # Mock ping return
    mock_ping = MagicMock()
    mock_ping.single.return_value = {"ping": 1, "c": 0}
    mock_session.run.return_value = mock_ping

    with patch.object(svc, "get_driver", return_value=mock_driver):
        with patch.object(svc, "check_connectivity", return_value=(True, "Online", {})):
            res = svc.init_schema()
            assert res["success"] is True
            # Verify constraints were run
            assert len(res["results"]) >= 7
            executed_stmts = [r["statement"] for r in res["results"]]
            assert any("FOR (d:Dataset)" in s for s in executed_stmts)
            assert any("FOR (p:Pulsar)" in s for s in executed_stmts)
            assert any("FOR (m:Model)" in s for s in executed_stmts)


def test_neo4j_mock_sync_astronomy_entities():
    """Verify idempotent sync generates correct Cypher MERGE calls for all research entities."""
    svc = Neo4jGraphService()
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    sample_obs = [
        {
            "id": 1,
            "file_name": "vegas_58637_21291_J1713+0747_0012.fits",
            "telescope": "GBT",
            "target_name": "J1713+0747",
            "observation_date": "2019-06-03",
            "validation_status": "VALID_PSRFITS",
        }
    ]
    sample_records = [
        {
            "id": 1,
            "title": "High Precision Timing of Binary Millisecond Pulsars with GBT (PSR J1713+0747)",
            "identifier": "10.1051/0004-6361/2024001",
            "source_name": "arXiv",
            "canonical_url": "https://arxiv.org/abs/2403.11111v1",
            "publication_date": "2024-03-15",
        }
    ]

    with patch.object(svc, "get_driver", return_value=mock_driver):
        with patch.object(svc, "check_connectivity", return_value=(True, "Online", {})):
            res = svc.sync_astronomy_entities(
                observations=sample_obs,
                research_records=sample_records,
                experiments_data={},
            )
            assert res["success"] is True
            counts = res["counts"]
            assert counts["datasets"] == 4
            assert counts["pulsars"] == 2
            assert counts["observations"] == 1
            assert counts["models"] == 4
            assert counts["features"] == 8
            assert counts["experiments"] == 5
            assert counts["papers"] == 1


def test_neo4j_execute_query_sanitization():
    """Verify that execute_query converts Neo4j DateTime and Node objects into JSON-safe dicts."""
    import json
    from neo4j.time import DateTime
    from neo4j.graph import Node

    svc = Neo4jGraphService()
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    mock_node = MagicMock(spec=Node)
    mock_node.element_id = "4:test:1"
    mock_node.labels = ["Dataset"]
    dt_val = DateTime(2026, 1, 15, 12, 0, 0)
    mock_node.items.return_value = [("name", "HTRU2"), ("created_at", dt_val)]

    mock_record = MagicMock()
    mock_record.items.return_value = [("n", mock_node), ("timestamp", dt_val), ("count", 42)]
    mock_session.run.return_value = [mock_record]

    with patch.object(svc, "get_driver", return_value=mock_driver):
        with patch.object(svc, "check_connectivity", return_value=(True, "Online", {})):
            res = svc.execute_query("MATCH (n:Dataset) RETURN n, n.created_at AS timestamp, 42 AS count")
            assert res["success"] is True
            assert res["record_count"] == 1
            # Crucial check: verify that json.dumps does NOT raise TypeError!
            serialized = json.dumps(res)
            assert "HTRU2" in serialized
            assert "2026-01-15" in serialized


def test_neo4j_subgraph_fallback_verified():
    """Verify that when Neo4j is offline, get_graph_subgraph with fallback_verified returns authentic research topology."""
    svc = Neo4jGraphService(uri="bolt://localhost:9999")
    res = svc.get_graph_subgraph(fallback_verified=True)
    assert res["summary"]["connected"] is False
    assert res["summary"]["source"] == "postgresql_master_dataset"
    assert len(res["nodes"]) >= 10
    assert len(res["edges"]) >= 8
    # Ensure real datasets and pulsars are present
    labels = {n["label"] for n in res["nodes"]}
    assert any("HTRU2" in l for l in labels)
    assert any("Parkes" in l or "0437" in l for l in labels)

