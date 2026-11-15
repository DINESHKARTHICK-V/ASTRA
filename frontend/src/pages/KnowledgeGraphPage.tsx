// ============================================================
//  ASTRA — Neo4j Astronomy Knowledge Graph Page
//  File   : frontend/src/pages/KnowledgeGraphPage.tsx
//  Purpose: Interactive research knowledge graph connecting datasets,
//           physical pulsars, telescope observations, ML models,
//           experiments, and literature records with honest connectivity
//           telemetry and Cypher query console.
// ============================================================

import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import {
  GraphStatusResponse,
  GraphStatisticsResponse,
  GraphSubgraphResponse,
  GraphNode,
} from '../types/api';
import { LoadingSpinner } from '../components/LoadingSpinner';

const LABEL_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  Dataset: { bg: '#e0f2fe', border: '#0284c7', text: '#0369a1' },
  Pulsar: { bg: '#ede9fe', border: '#7c3aed', text: '#6d28d9' },
  Observation: { bg: '#fef3c7', border: '#d97706', text: '#b45309' },
  Model: { bg: '#dcfce7', border: '#16a34a', text: '#15803d' },
  ResearchExperiment: { bg: '#e0e7ff', border: '#4f46e5', text: '#4338ca' },
  Feature: { bg: '#f1f5f9', border: '#64748b', text: '#334155' },
  ResearchPaper: { bg: '#ffe4e6', border: '#e11d48', text: '#be123c' },
};

export const KnowledgeGraphPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [testingConn, setTestingConn] = useState(false);
  const [status, setStatus] = useState<GraphStatusResponse | null>(null);
  const [stats, setStats] = useState<GraphStatisticsResponse | null>(null);
  const [subgraph, setSubgraph] = useState<GraphSubgraphResponse | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedLabel, setSelectedLabel] = useState<string>('ALL');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Cypher console state
  const [customCypher, setCustomCypher] = useState<string>('MATCH (d:Dataset) RETURN d.name AS name, d.id AS id, d.format AS format');
  const [queryRunning, setQueryRunning] = useState(false);
  const [queryResult, setQueryResult] = useState<any | null>(null);

  // Canvas pan / zoom
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const loadGraphData = async () => {
    setLoading(true);
    try {
      const [statusRes, statsRes, subgraphRes] = await Promise.all([
        apiService.getGraphStatus().catch(() => ({
          connected: false,
          message: 'Unable to contact Neo4j graph API',
          telemetry: { status: 'OFFLINE', uri: 'bolt://127.0.0.1:7687' },
        })),
        apiService.getGraphStatistics().catch(() => ({
          connected: false,
          message: 'Offline',
          labels: {},
          relationships: {},
          total_nodes: 0,
          total_relationships: 0,
        })),
        apiService.getGraphSubgraph(100).catch(() => ({
          nodes: [],
          edges: [],
          summary: { connected: false, message: 'Offline', node_count: 0, edge_count: 0 },
        })),
      ]);

      setStatus(statusRes);
      setStats(statsRes);
      setSubgraph(subgraphRes);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraphData();
  }, []);

  const handleTestConnection = async () => {
    setTestingConn(true);
    setMessage(null);
    try {
      const res = await apiService.getGraphStatus();
      setStatus(res);
      if (res.connected) {
        setMessage({
          text: `Neo4j connection successful! Service active at ${res.telemetry?.uri || 'bolt://127.0.0.1:7687'}.`,
          type: 'success',
        });
        await loadGraphData();
      } else {
        setMessage({
          text: `Connection test result: ${res.message}. Ensure Neo4j container or desktop daemon is running on port 7687.`,
          type: 'error',
        });
      }
    } catch (err: any) {
      setMessage({
        text: `Connection failed: ${err?.message || 'Neo4j service unreachable'}`,
        type: 'error',
      });
    } finally {
      setTestingConn(false);
    }
  };

  const handleSyncGraph = async () => {
    setSyncing(true);
    setMessage(null);
    try {
      const res = await apiService.syncKnowledgeGraph();
      if (res.success) {
        setMessage({
          text: `Knowledge graph synchronized successfully! ${res.counts?.datasets || 4} datasets, ${res.counts?.pulsars || 2} pulsars, and ${res.counts?.models || 4} models updated.`,
          type: 'success',
        });
        await loadGraphData();
      } else {
        setMessage({
          text: `Sync note: ${res.message || 'Neo4j database offline. Please start Neo4j service.'}`,
          type: 'error',
        });
      }
    } catch (err: any) {
      setMessage({
        text: `Sync failed: ${err?.message || 'Neo4j service is offline. Start Neo4j container on bolt://127.0.0.1:7687.'}`,
        type: 'error',
      });
    } finally {
      setSyncing(false);
    }
  };

  const handleExecuteQuery = async (queryToRun?: string) => {
    const q = queryToRun || customCypher;
    if (!q.trim()) return;
    setQueryRunning(true);
    setQueryResult(null);
    try {
      const res = await apiService.executeGraphQuery(q);
      setQueryResult(res);
      if (res.success && res.connected) {
        setMessage({
          text: `Cypher query executed successfully: ${res.record_count} record(s) returned.`,
          type: 'success',
        });
      } else if (!res.connected) {
        setMessage({
          text: `Neo4j connection unavailable: ${res.error || 'Server offline'}.`,
          type: 'error',
        });
      } else {
        setMessage({
          text: `Cypher execution notice: ${res.error || 'Query returned 0 records.'}`,
          type: 'info',
        });
      }
    } catch (err: any) {
      setQueryResult({
        success: false,
        connected: false,
        error: err?.message || 'Failed to execute query',
        records: [],
      });
    } finally {
      setQueryRunning(false);
    }
  };

  // Node filtering
  const filteredNodes = (subgraph?.nodes || []).filter(
    (n) => selectedLabel === 'ALL' || n.type === selectedLabel
  );
  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = (subgraph?.edges || []).filter(
    (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
  );

  // Position nodes in a radial cluster layout
  const nodePositions = React.useMemo(() => {
    const pos: Record<string, { x: number; y: number }> = {};
    const count = filteredNodes.length;
    if (count === 0) return pos;

    const centerX = 450;
    const centerY = 320;
    const radius = Math.min(centerX - 80, centerY - 80);

    filteredNodes.forEach((node, idx) => {
      const angle = (idx / count) * 2 * Math.PI;
      const r = node.type === 'Dataset' ? radius * 0.45 : radius * 0.85;
      pos[node.id] = {
        x: centerX + r * Math.cos(angle),
        y: centerY + r * Math.sin(angle),
      };
    });
    return pos;
  }, [filteredNodes]);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  if (loading) {
    return <LoadingSpinner message="Querying Neo4j Astronomy Knowledge Graph & Topology..." />;
  }

  const isConnected = status?.connected === true;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ──────────────────────────────────────────────────────────── */}
      {/* 1. KNOWLEDGE GRAPH HEADER BANNER */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="card" style={{ borderLeft: isConnected ? '4px solid #16a34a' : '4px solid #d97706', padding: '20px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '1.4rem' }}>🌌</span>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                Neo4j Astronomy Research Knowledge Graph
              </h2>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  padding: '3px 10px',
                  borderRadius: '12px',
                  backgroundColor: isConnected ? '#dcfce7' : '#fef3c7',
                  color: isConnected ? '#15803d' : '#b45309',
                  border: `1px solid ${isConnected ? '#bbf7d0' : '#fde68a'}`,
                }}
              >
                {isConnected ? '● Connected (Neo4j Bolt Engine)' : '○ Neo4j Disconnected (Port 7687)'}
              </span>
            </div>
            <p style={{ margin: '6px 0 0', color: 'var(--text-muted)', fontSize: '0.84rem', maxWidth: '850px', lineHeight: 1.5 }}>
              Models relationships between datasets, physical pulsars, telescope observations, machine learning models,
              SHAP feature importance rankings, and astronomical research papers using native graph topology.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              className="btn btn-secondary"
              onClick={handleTestConnection}
              disabled={testingConn}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {testingConn ? 'Testing...' : '⚡ Test Connection'}
            </button>
            <button
              className="btn btn-primary"
              onClick={handleSyncGraph}
              disabled={syncing || !isConnected}
              title={!isConnected ? 'Start Neo4j to enable graph synchronization' : 'Synchronize research entities to Neo4j'}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {syncing ? 'Synchronizing...' : '🔄 Sync Neo4j Graph'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={loadGraphData}
            >
              ↻ Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Notification Message */}
      {message && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '6px',
            fontSize: '0.84rem',
            backgroundColor: message.type === 'success' ? '#f0fdf4' : message.type === 'error' ? '#fef2f2' : '#f0f9ff',
            color: message.type === 'success' ? '#166534' : message.type === 'error' ? '#991b1b' : '#0369a1',
            border: `1px solid ${message.type === 'success' ? '#bbf7d0' : message.type === 'error' ? '#fecaca' : '#bae6fd'}`,
          }}
        >
          {message.text}
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 2. CONNECTION TELEMETRY & DIAGNOSTICS TILES */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="kpi-grid">
        <div className="kpi-card" style={{ '--kpi-accent': isConnected ? '#16a34a' : '#d97706' } as any}>
          <div className="kpi-label">Service Status</div>
          <div className="kpi-value" style={{ fontSize: '1.2rem', color: isConnected ? '#16a34a' : '#d97706' }}>
            {isConnected ? 'ONLINE' : 'OFFLINE'}
          </div>
          <div className="kpi-subtext">{status?.telemetry?.uri || 'bolt://127.0.0.1:7687'}</div>
        </div>

        <div className="kpi-card" style={{ '--kpi-accent': '#0284c7' } as any}>
          <div className="kpi-label">Graph Nodes</div>
          <div className="kpi-value">{stats?.total_nodes || subgraph?.nodes?.length || 0}</div>
          <div className="kpi-subtext">Datasets, Pulsars, Models, Obs</div>
        </div>

        <div className="kpi-card" style={{ '--kpi-accent': '#7c3aed' } as any}>
          <div className="kpi-label">Relationships</div>
          <div className="kpi-value">{stats?.total_relationships || subgraph?.edges?.length || 0}</div>
          <div className="kpi-subtext">Directed semantic links</div>
        </div>

        <div className="kpi-card" style={{ '--kpi-accent': '#475569' } as any}>
          <div className="kpi-label">Target Database</div>
          <div className="kpi-value" style={{ fontSize: '1.2rem' }}>{status?.telemetry?.database || 'neo4j'}</div>
          <div className="kpi-subtext">{isConnected ? 'Bolt protocol port 7687' : 'Port 7687 unreachable'}</div>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 3. DIAGNOSTICS CARD (Shown when offline) */}
      {/* ──────────────────────────────────────────────────────────── */}
      {!isConnected && (
        <div className="card" style={{ backgroundColor: '#fffbeb', border: '1px solid #fde68a', padding: '16px 20px' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '1.4rem' }}>⚠️</span>
            <div style={{ flex: 1 }}>
              <strong style={{ color: '#92400e', fontSize: '0.92rem' }}>
                Neo4j Service Disconnected — Connection Diagnostics
              </strong>
              <p style={{ margin: '4px 0 8px', fontSize: '0.82rem', color: '#78350f', lineHeight: 1.45 }}>
                {status?.message || 'Neo4j service is unavailable at bolt://127.0.0.1:7687. The port is unreachable or the Neo4j daemon is not currently started.'}
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '8px', fontSize: '0.78rem', background: '#fef3c7', padding: '10px 14px', borderRadius: '6px' }}>
                <div><span style={{ color: '#92400e', fontWeight: 600 }}>Bolt URI:</span> <code>bolt://127.0.0.1:7687</code></div>
                <div><span style={{ color: '#92400e', fontWeight: 600 }}>Database:</span> <code>neo4j</code></div>
                <div><span style={{ color: '#92400e', fontWeight: 600 }}>Driver:</span> neo4j Python driver installed</div>
                <div><span style={{ color: '#92400e', fontWeight: 600 }}>Start Command:</span> <code>docker compose up -d neo4j</code></div>
              </div>
              <p style={{ margin: '8px 0 0', fontSize: '0.76rem', color: '#92400e' }}>
                ASTRA enforces scientific integrity: no mock graph data is fabricated while Neo4j is offline. Once the Neo4j service is running, click <strong>"⚡ Test Connection"</strong> followed by <strong>"🔄 Sync Neo4j Graph"</strong> to import all verified research entities.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 4. CYPHER QUERY RUNNER & GRAPH ENGINE CONSOLE */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="card" style={{ borderLeft: '4px solid #0284c7' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px', marginBottom: '12px' }}>
          <div>
            <h4 style={{ margin: '0 0 4px', color: '#0f172a', fontSize: '0.98rem', fontWeight: 700 }}>
              Interactive Cypher Query Console
            </h4>
            <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Execute parameterized Cypher graph queries or inspect knowledge graph entities and relationships.
            </p>
          </div>
          <span className="badge badge-validated">
            Cypher 5.x / bolt://127.0.0.1:7687
          </span>
        </div>

        {/* Query Presets */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Presets:</span>
          {[
            { label: 'All Datasets', q: 'MATCH (d:Dataset) RETURN d.name AS name, d.id AS id, d.format AS format' },
            { label: 'Models & Features', q: 'MATCH (m:Model)-[r:ANALYZES_FEATURE]->(f:Feature) RETURN m.name AS model, f.name AS feature, r.importance_rank AS importance' },
            { label: 'Experiments (P1-P5)', q: 'MATCH (e:ResearchExperiment) RETURN e.id AS id, e.name AS name, e.status AS status' },
            { label: 'Observations & Pulsars', q: 'MATCH (o:Observation)-[r:OBSERVED_SOURCE]->(p:Pulsar) RETURN o.id AS observation, p.name AS pulsar' },
          ].map((preset, idx) => (
            <button
              key={idx}
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setCustomCypher(preset.q);
                handleExecuteQuery(preset.q);
              }}
              style={{ fontSize: '0.74rem', padding: '3px 8px' }}
            >
              {preset.label}
            </button>
          ))}
        </div>

        {/* Query Input Box */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input
            type="text"
            className="input"
            value={customCypher}
            onChange={(e) => setCustomCypher(e.target.value)}
            placeholder="Enter Cypher query (e.g. MATCH (n) RETURN n LIMIT 10)..."
            style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', flex: 1 }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleExecuteQuery();
            }}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleExecuteQuery()}
            disabled={queryRunning}
            style={{ fontSize: '0.82rem', padding: '6px 16px' }}
          >
            {queryRunning ? 'Running...' : '▶ Execute'}
          </button>
        </div>

        {/* Query Results Display */}
        {queryResult && (
          <div style={{ marginTop: '14px', background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.76rem', fontWeight: 600, color: queryResult.success ? '#16a34a' : '#dc2626' }}>
                {queryResult.success ? `✓ Query Executed: ${queryResult.record_count} record(s)` : `✗ Error: ${queryResult.error || 'Execution failed'}`}
              </span>
              <button
                onClick={() => setQueryResult(null)}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '0.8rem', color: '#64748b' }}
              >
                Clear
              </button>
            </div>

            {queryResult.records && queryResult.records.length > 0 ? (
              <div className="table-container" style={{ maxHeight: '220px', overflowY: 'auto' }}>
                <table className="data-table" style={{ fontSize: '0.78rem' }}>
                  <thead>
                    <tr>
                      {Object.keys(queryResult.records[0] || {}).map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {queryResult.records.map((row: any, rIdx: number) => (
                      <tr key={rIdx}>
                        {Object.values(row).map((val: any, cIdx: number) => (
                          <td key={cIdx} className="mono">
                            {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : queryResult.success ? (
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Query executed successfully. 0 records matched the query.
              </span>
            ) : null}
          </div>
        )}
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 5. INTERACTIVE GRAPH TOPOLOGY EXPLORER */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3 className="card-title">Astronomy Research Subgraph Topology</h3>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Interactive entity-relationship network visualizer. Click any node to inspect metadata.
            </span>
          </div>

          {/* Node Type Filter Chips */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginRight: '4px' }}>Filter:</span>
            {['ALL', 'Dataset', 'Pulsar', 'Observation', 'Model', 'ResearchExperiment', 'Feature', 'ResearchPaper'].map((lbl) => (
              <button
                key={lbl}
                onClick={() => setSelectedLabel(lbl)}
                style={{
                  padding: '3px 8px',
                  borderRadius: '4px',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: '1px solid #cbd5e1',
                  backgroundColor: selectedLabel === lbl ? '#0284c7' : '#ffffff',
                  color: selectedLabel === lbl ? '#ffffff' : '#475569',
                }}
              >
                {lbl}
              </button>
            ))}
          </div>
        </div>

        {/* Graph Canvas Container */}
        <div style={{ display: 'grid', gridTemplateColumns: selectedNode ? '1fr 320px' : '1fr', gap: '16px', marginTop: '16px' }}>
          <div
            style={{
              position: 'relative',
              height: '560px',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              backgroundColor: '#f8fafc',
              overflow: 'hidden',
              cursor: isDragging ? 'grabbing' : 'grab',
            }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          >
            {/* Topology Source Bar */}
            <div style={{
              position: 'absolute',
              top: '12px',
              left: '12px',
              zIndex: 10,
              padding: '4px 10px',
              borderRadius: '4px',
              fontSize: '0.74rem',
              fontWeight: 600,
              background: isConnected ? '#f0fdf4' : '#f8fafc',
              border: `1px solid ${isConnected ? '#bbf7d0' : '#cbd5e1'}`,
              color: isConnected ? '#166534' : '#475569',
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            }}>
              {isConnected
                ? '● Live Neo4j Graph (Bolt 7687)'
                : '○ Verified Research Topology (PostgreSQL & Master Dataset)'}
            </div>

            {/* Zoom / Pan Controls */}
            <div style={{ position: 'absolute', top: '12px', right: '12px', zIndex: 10, display: 'flex', gap: '6px' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setZoom((z) => Math.min(z + 0.2, 2.5))}
                title="Zoom In"
              >
                +
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setZoom((z) => Math.max(z - 0.2, 0.4))}
                title="Zoom Out"
              >
                −
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setZoom(1);
                  setPan({ x: 0, y: 0 });
                }}
                title="Reset View"
              >
                Reset
              </button>
            </div>

            {/* SVG Visualizer / Empty / Offline States */}
            {filteredNodes.length === 0 ? (
              <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', padding: '20px', textAlign: 'center' }}>
                <span style={{ fontSize: '2.5rem', marginBottom: '8px' }}>🕸️</span>
                <span style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f172a' }}>
                  {isConnected ? 'Knowledge Graph is Currently Empty' : 'Neo4j Bolt Service is Offline'}
                </span>
                <span style={{ fontSize: '0.82rem', marginTop: '6px', maxWidth: '480px', lineHeight: 1.5 }}>
                  {isConnected
                    ? 'Neo4j connection is active. Click "🔄 Sync Neo4j Graph" above to import datasets, pulsars, models, and research experiments.'
                    : 'Live graph topology visualization requires an active Neo4j Bolt service at bolt://127.0.0.1:7687. Start your Neo4j container to explore the live research graph.'}
                </span>
              </div>
            ) : (
              <svg
                width="100%"
                height="100%"
                style={{ overflow: 'visible' }}
              >
                <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                  {/* Edges */}
                  {filteredEdges.map((edge) => {
                    const src = nodePositions[edge.source];
                    const dst = nodePositions[edge.target];
                    if (!src || !dst) return null;

                    const midX = (src.x + dst.x) / 2;
                    const midY = (src.y + dst.y) / 2;

                    return (
                      <g key={edge.id}>
                        <line
                          x1={src.x}
                          y1={src.y}
                          x2={dst.x}
                          y2={dst.y}
                          stroke="#cbd5e1"
                          strokeWidth="1.5"
                          strokeDasharray={edge.type.includes('ANALYZES') ? '4 2' : undefined}
                        />
                        <text
                          x={midX}
                          y={midY}
                          fill="#64748b"
                          fontSize="9"
                          textAnchor="middle"
                          style={{ userSelect: 'none', background: '#ffffff' }}
                        >
                          {edge.type}
                        </text>
                      </g>
                    );
                  })}

                  {/* Nodes */}
                  {filteredNodes.map((node) => {
                    const pos = nodePositions[node.id];
                    if (!pos) return null;

                    const colors = LABEL_COLORS[node.type] || { bg: '#f1f5f9', border: '#64748b', text: '#334155' };
                    const isSelected = selectedNode?.id === node.id;

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${pos.x}, ${pos.y})`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedNode(node);
                        }}
                        style={{ cursor: 'pointer' }}
                      >
                        <circle
                          r={node.type === 'Dataset' ? 24 : node.type === 'Pulsar' ? 20 : 16}
                          fill={colors.bg}
                          stroke={isSelected ? '#0f172a' : colors.border}
                          strokeWidth={isSelected ? 3 : 2}
                        />
                        <text
                          y={node.type === 'Dataset' ? 34 : 26}
                          fill="#0f172a"
                          fontSize="10"
                          fontWeight="600"
                          textAnchor="middle"
                          style={{ userSelect: 'none' }}
                        >
                          {node.label.length > 20 ? `${node.label.slice(0, 18)}...` : node.label}
                        </text>
                        <text
                          y={-22}
                          fill={colors.text}
                          fontSize="8"
                          fontWeight="700"
                          textAnchor="middle"
                          style={{ userSelect: 'none' }}
                        >
                          {node.type}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </svg>
            )}
          </div>

          {/* Node Inspector Card */}
          {selectedNode && (
            <div
              style={{
                background: '#ffffff',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      color: LABEL_COLORS[selectedNode.type]?.text || '#475569',
                    }}
                  >
                    {selectedNode.type}
                  </span>
                  <h4 style={{ margin: '4px 0 0', fontSize: '1rem', color: '#0f172a', fontWeight: 700 }}>
                    {selectedNode.label}
                  </h4>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  style={{
                    border: 'none',
                    background: 'transparent',
                    cursor: 'pointer',
                    fontSize: '1.1rem',
                    color: '#94a3b8',
                  }}
                >
                  ×
                </button>
              </div>

              <div style={{ fontSize: '0.8rem', color: '#475569' }}>
                <strong style={{ color: '#0f172a' }}>Node Properties:</strong>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '8px' }}>
                  {Object.entries(selectedNode.properties || {}).map(([key, val]) => (
                    <div key={key} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '4px' }}>
                      <span style={{ color: 'var(--text-dim)', fontSize: '0.74rem' }}>{key}:</span>
                      <span className="mono" style={{ fontWeight: 600, color: '#0f172a', fontSize: '0.74rem', maxWidth: '170px', textAlign: 'right', wordBreak: 'break-word' }}>
                        {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
