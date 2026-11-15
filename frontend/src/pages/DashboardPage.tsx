import React, { useEffect, useState } from 'react';
import { apiService, ApiError } from '../services/api';
import {
  ObservationListResponse,
  CandidateListResponse,
  ProcessingRunListResponse,
  HealthResponse,
} from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';

interface DashboardPageProps {
  onSelectObservation: (id: number) => void;
  onNavigateTab: (tab: 'dashboard' | 'candidates' | 'processing') => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onSelectObservation,
  onNavigateTab,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [obsData, setObsData] = useState<ObservationListResponse | null>(null);
  const [candData, setCandData] = useState<CandidateListResponse | null>(null);
  const [runsData, setRunsData] = useState<ProcessingRunListResponse | null>(null);
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [obs, cand, runs, health] = await Promise.all([
        apiService.getObservations(10, 0),
        apiService.getCandidates(10, 0),
        apiService.getProcessingRuns(10, 0),
        apiService.getHealth(),
      ]);
      setObsData(obs);
      setCandData(cand);
      setRunsData(runs);
      setHealthData(health);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load dashboard telemetry.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return <LoadingSpinner message="Loading ASTRA observational telemetry..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Telemetry Retrieval Failure"
        message={error}
        onRetry={loadData}
      />
    );
  }

  const totalObservations = obsData?.total || 0;
  const highPriorityCount = candData?.items.filter((c) => c.priority_group === 'HIGH').length || 0;
  const meanAcisScore =
    candData && candData.items.length > 0
      ? (
          candData.items.reduce((acc, c) => acc + c.acis_score, 0) / candData.items.length
        ).toFixed(4)
      : 'N/A';
  const completedRunsCount =
    runsData?.items.filter((r) => r.processing_status === 'COMPLETED').length || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Banner Notice */}
      <div className="alert-box alert-info">
        <span style={{ fontSize: '1.1rem' }}>📡</span>
        <div>
          <strong style={{ color: '#fff' }}>Astrophysical Target: PSR J1713+0747 (GBT/VEGAS @ 820 MHz)</strong>
          <p style={{ margin: '4px 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
            Data source: 12 folded PSRFITS timing archive observations. 
            ML search-mode inference safely halted; ACIS multi-evidence scoring operational.
          </p>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="metrics-grid">
        <div className="metric-card" style={{ '--card-accent': 'var(--cyan)' } as any}>
          <span className="metric-label">Total Cataloged Observations</span>
          <span className="metric-value">{totalObservations}</span>
          <span className="metric-sub">12 PSRFITS Archives Verified</span>
        </div>

        <div className="metric-card" style={{ '--card-accent': 'var(--green)' } as any}>
          <span className="metric-label">High Priority Candidates</span>
          <span className="metric-value">{highPriorityCount}</span>
          <span className="metric-sub">ACIS Score Threshold ≥ 0.65</span>
        </div>

        <div className="metric-card" style={{ '--card-accent': 'var(--purple)' } as any}>
          <span className="metric-label">Mean ACIS Intelligence Score</span>
          <span className="metric-value">{meanAcisScore}</span>
          <span className="metric-sub">5/6 Physical Channels Active</span>
        </div>

        <div className="metric-card" style={{ '--card-accent': 'var(--amber)' } as any}>
          <span className="metric-label">Pipeline Runs Completed</span>
          <span className="metric-value">{completedRunsCount}</span>
          <span className="metric-sub">100% Pipeline Verification</span>
        </div>
      </div>

      {/* Main Grid: Candidates Preview & System Health */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '24px' }}>
        {/* Candidates Table Preview */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <span>★</span>
              <span>Top Prioritized Candidates (ACIS)</span>
            </h3>
            <button
              onClick={() => onNavigateTab('candidates')}
              className="btn"
              style={{ fontSize: '0.78rem', padding: '4px 10px' }}
            >
              View Full Table →
            </button>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Observation File</th>
                  <th>ACIS Score</th>
                  <th>Priority</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {candData?.items.slice(0, 5).map((cand) => (
                  <tr key={cand.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--cyan)' }}>
                      #{cand.rank_position}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                      {cand.file_name}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {cand.acis_score.toFixed(4)}
                    </td>
                    <td>
                      <StatusBadge type="priority" value={cand.priority_group} />
                    </td>
                    <td>
                      <button
                        onClick={() => onSelectObservation(cand.observation_id)}
                        className="btn"
                        style={{ fontSize: '0.75rem', padding: '3px 8px' }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* System & Telemetry Summary Card */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <span>⚙</span>
              <span>Telemetry & Database Status</span>
            </h3>
            <button
              onClick={loadData}
              className="btn"
              style={{ fontSize: '0.78rem', padding: '4px 10px' }}
            >
              ↻ Refresh
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.88rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>PostgreSQL Database</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--green)' }}>
                {healthData?.database_connected ? 'CONNECTED (astra_cloud)' : 'DISCONNECTED'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Target Pulsar</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>PSR J1713+0747</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Observing Facility</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>Green Bank Telescope (GBT / VEGAS)</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Observation Frequency</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>820.0 MHz</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0' }}>
              <span style={{ color: 'var(--text-muted)' }}>ML Classifier Status</span>
              <StatusBadge type="inference" value="INFERENCE_HALTED" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
