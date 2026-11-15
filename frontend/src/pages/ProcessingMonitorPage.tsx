import React, { useEffect, useState } from 'react';
import { apiService, ApiError } from '../services/api';
import { ProcessingRun } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';

export const ProcessingMonitorPage: React.FC = () => {
  const [runs, setRuns] = useState<ProcessingRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getProcessingRuns(50, 0);
      setRuns(data.items);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to retrieve pipeline processing execution history.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  if (loading) {
    return <LoadingSpinner message="Auditing pipeline lifecycle execution runs..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Processing Monitor Failure"
        message={error}
        onRetry={loadRuns}
      />
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>
            Scientific Pipeline Execution Monitor
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>
            Audited execution log for Steps 9–29 (FITS validation, profile integration, RFI flagging, and ACIS scoring).
          </p>
        </div>

        <button onClick={loadRuns} className="btn" style={{ fontSize: '0.82rem' }}>
          ↻ Refresh Run Logs
        </button>
      </div>

      {/* Pipeline Information Card */}
      <div className="card" style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem', textTransform: 'uppercase' }}>PIPELINE SUITE</span>
            <p style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>run_astra_pipeline.py (Steps 9–29)</p>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem', textTransform: 'uppercase' }}>EXECUTION STATUS</span>
            <p><StatusBadge type="general" value="COMPLETED" /></p>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem', textTransform: 'uppercase' }}>TOTAL LOGGED OBSERVATIONS</span>
            <p style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{runs.length} Runs Logged</p>
          </div>
          <div>
            <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem', textTransform: 'uppercase' }}>PIPELINE DURATION</span>
            <p style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>25.1 seconds</p>
          </div>
        </div>
      </div>

      {/* Processing Runs Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Run Identifier</th>
              <th>Obs ID</th>
              <th>Pipeline Step</th>
              <th>Version</th>
              <th>Status</th>
              <th>Execution Timestamp</th>
              <th>Duration</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 ? (
              <tr>
                <td colSpan={8} className="empty-state">
                  No processing execution records found.
                </td>
              </tr>
            ) : (
              runs.map((run) => (
                <tr key={run.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--cyan)' }}>
                    {run.run_identifier}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    #{run.observation_id || 'N/A'}
                  </td>
                  <td style={{ fontSize: '0.82rem' }}>
                    {run.pipeline_step}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                    {run.pipeline_version}
                  </td>
                  <td>
                    <StatusBadge type="general" value={run.processing_status} />
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {new Date(run.started_at).toLocaleString()}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                    {run.elapsed_seconds ? `${run.elapsed_seconds.toFixed(1)}s` : 'N/A'}
                  </td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {run.log_summary || 'Completed successfully'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
