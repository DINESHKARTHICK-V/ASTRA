import React, { useEffect, useState, useMemo } from 'react';
import { apiService, ApiError } from '../services/api';
import {
  Observation,
  ProcessingRun,
  CsvFileItem,
  CandidateScore,
} from '../types/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';

interface HistoryPageProps {
  onSelectObservation: (id: number) => void;
  onNavigateTab?: (tab: any) => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({
  onSelectObservation,
  onNavigateTab,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Raw catalog data
  const [observations, setObservations] = useState<Observation[]>([]);
  const [processingRuns, setProcessingRuns] = useState<ProcessingRun[]>([]);
  const [csvFiles, setCsvFiles] = useState<CsvFileItem[]>([]);
  const [candidates, setCandidates] = useState<CandidateScore[]>([]);

  // Date selection state: default to today or recent active date
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    return new Date().toISOString().slice(0, 10);
  });

  const [activeCategory, setActiveCategory] = useState<'ALL' | 'OBSERVATIONS' | 'RUNS' | 'CSV'>('ALL');

  // Load all records once
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [obsRes, runsRes, csvRes, candRes] = await Promise.all([
        apiService.getObservations(500, 0),
        apiService.getProcessingRuns(500, 0),
        apiService.listCsvFiles().catch(() => []),
        apiService.getCandidates(500, 0).catch(() => ({ items: [], total: 0 })),
      ]);

      setObservations(obsRes.items);
      setProcessingRuns(runsRes.items);
      setCsvFiles(csvRes);
      setCandidates(candRes.items);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to retrieve history telemetry.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Candidate map for ACIS lookup
  const candidateMap = useMemo(() => {
    const map = new Map<number, CandidateScore>();
    candidates.forEach((c) => map.set(c.observation_id, c));
    return map;
  }, [candidates]);

  // Map observation IDs to targets for run records
  const obsMap = useMemo(() => {
    const map = new Map<number, Observation>();
    observations.forEach((o) => map.set(o.id, o));
    return map;
  }, [observations]);

  // Extract all unique historical dates present in the system
  const availableHistoricalDates = useMemo(() => {
    const dates = new Set<string>();

    observations.forEach((o) => {
      if (o.observation_date) dates.add(o.observation_date.slice(0, 10));
      if (o.created_at) dates.add(o.created_at.slice(0, 10));
    });

    processingRuns.forEach((r) => {
      if (r.started_at) dates.add(r.started_at.slice(0, 10));
    });

    csvFiles.forEach((c) => {
      if (c.upload_date) dates.add(c.upload_date.slice(0, 10));
    });

    return Array.from(dates).filter(Boolean).sort().reverse();
  }, [observations, processingRuns, csvFiles]);

  // Filter observations matching selectedDate (matches either observation_date or created_at)
  const matchedObservations = useMemo(() => {
    if (!selectedDate) return [];
    return observations.filter((o) => {
      const obsDate = o.observation_date ? o.observation_date.slice(0, 10) : '';
      const createdDate = o.created_at ? o.created_at.slice(0, 10) : '';
      return obsDate === selectedDate || createdDate === selectedDate;
    });
  }, [observations, selectedDate]);

  // Filter processing runs matching selectedDate
  const matchedRuns = useMemo(() => {
    if (!selectedDate) return [];
    return processingRuns.filter((r) => {
      const runDate = r.started_at ? r.started_at.slice(0, 10) : '';
      return runDate === selectedDate;
    });
  }, [processingRuns, selectedDate]);

  // Filter CSV files matching selectedDate
  const matchedCsvFiles = useMemo(() => {
    if (!selectedDate) return [];
    return csvFiles.filter((c) => {
      const uploadDate = c.upload_date ? c.upload_date.slice(0, 10) : '';
      return uploadDate === selectedDate;
    });
  }, [csvFiles, selectedDate]);

  const totalMatched = matchedObservations.length + matchedRuns.length + matchedCsvFiles.length;

  // Date stepper handlers
  const handleStepDay = (delta: number) => {
    try {
      const d = new Date(selectedDate);
      d.setDate(d.getDate() + delta);
      setSelectedDate(d.toISOString().slice(0, 10));
    } catch {
      // fallback
    }
  };

  const handleDownloadPdf = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    try {
      await apiService.downloadObservationReport(id);
    } catch (err: any) {
      alert(`Could not download PDF report: ${err?.message || 'Error'}`);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Querying chronological audit logs & historical records..." />;
  }

  if (error) {
    return <ErrorMessage title="History Telemetry Error" message={error} onRetry={loadData} />;
  }

  return (
    <div className="page-container">
      {/* ── Date Picker Control Card ── */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>⏱️</span> Chronological History &amp; Audit Trail
            </h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Filter cataloged observations, automated pipeline runs, and CSV tabular ingestions by calendar date (UTC).
            </p>
          </div>

          {/* Date Picker Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => handleStepDay(-1)}
              title="Previous day"
            >
              ◀ Prev Day
            </button>

            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <input
                type="date"
                className="search-input"
                style={{
                  padding: '7px 12px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  color: '#fff',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-active)',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  minWidth: '150px',
                }}
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
              />
            </div>

            <button
              className="btn btn-secondary btn-sm"
              onClick={() => handleStepDay(1)}
              title="Next day"
            >
              Next Day ▶
            </button>

            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedDate(new Date().toISOString().slice(0, 10))}
            >
              Today
            </button>

            <button
              className="btn btn-secondary btn-sm"
              onClick={loadData}
              title="Refresh records"
            >
              🔄
            </button>
          </div>
        </div>

        {/* Quick-Jump Historical Dates Bar */}
        <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.73rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Quick Jump to Dates with Stored Records:
          </span>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {availableHistoricalDates.slice(0, 10).map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDate(d)}
                style={{
                  padding: '3px 8px',
                  fontSize: '0.72rem',
                  borderRadius: 'var(--radius-sm)',
                  border: d === selectedDate ? '1px solid var(--primary)' : '1px solid var(--border-subtle)',
                  backgroundColor: d === selectedDate ? 'rgba(14, 165, 233, 0.18)' : 'rgba(255, 255, 255, 0.03)',
                  color: d === selectedDate ? 'var(--primary)' : 'var(--text-muted)',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: d === selectedDate ? 700 : 500,
                  transition: 'all 0.15s ease',
                }}
              >
                {d}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Summary KPI Cards for Selected Date ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '12px',
          marginBottom: '20px',
        }}
      >
        <div className="card" style={{ padding: '14px 16px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Total Records ({selectedDate})
          </div>
          <div className="mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fff', marginTop: '4px' }}>
            {totalMatched}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            Observations, runs &amp; datasets
          </div>
        </div>

        <div className="card" style={{ padding: '14px 16px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Astronomical Observations
          </div>
          <div className="mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--primary)', marginTop: '4px' }}>
            {matchedObservations.length}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            Radio PSRFITS &amp; Optical FITS
          </div>
        </div>

        <div className="card" style={{ padding: '14px 16px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Pipeline Processing Runs
          </div>
          <div className="mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-purple)', marginTop: '4px' }}>
            {matchedRuns.length}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            Telemetry executions
          </div>
        </div>

        <div className="card" style={{ padding: '14px 16px' }}>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            CSV Ingested Files
          </div>
          <div className="mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--success)', marginTop: '4px' }}>
            {matchedCsvFiles.length}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
            Tabular survey datasets
          </div>
        </div>
      </div>

      {/* ── Empty State vs Tabbed Results ── */}
      {totalMatched === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '50px 20px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '14px' }}>📅</div>
          <h4 style={{ color: '#fff', fontSize: '1.1rem', fontWeight: 700, marginBottom: '6px' }}>
            No Activity Recorded on {selectedDate}
          </h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', maxWidth: '520px', margin: '0 auto 20px', lineHeight: '1.5' }}>
            No cataloged astronomical observations, pipeline processing runs, or CSV ingestions match this UTC calendar date.
          </p>

          <div style={{ display: 'inline-flex', flexDirection: 'column', gap: '10px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
              Try selecting one of the known active dates from your recorded history:
            </span>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
              {availableHistoricalDates.slice(0, 6).map((d) => (
                <button
                  key={d}
                  className="btn btn-secondary btn-sm"
                  onClick={() => setSelectedDate(d)}
                >
                  📅 Jump to {d}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="card">
          {/* Sub-navigation category pills */}
          <div
            style={{
              display: 'flex',
              gap: '8px',
              borderBottom: '1px solid var(--border-subtle)',
              paddingBottom: '12px',
              marginBottom: '16px',
            }}
          >
            <button
              className={`btn btn-sm ${activeCategory === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveCategory('ALL')}
            >
              All Records ({totalMatched})
            </button>
            <button
              className={`btn btn-sm ${activeCategory === 'OBSERVATIONS' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveCategory('OBSERVATIONS')}
            >
              Observations ({matchedObservations.length})
            </button>
            <button
              className={`btn btn-sm ${activeCategory === 'RUNS' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveCategory('RUNS')}
            >
              Processing Runs ({matchedRuns.length})
            </button>
            <button
              className={`btn btn-sm ${activeCategory === 'CSV' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveCategory('CSV')}
            >
              CSV Datasets ({matchedCsvFiles.length})
            </button>
          </div>

          {/* ── 1. OBSERVATIONS SECTION ── */}
          {(activeCategory === 'ALL' || activeCategory === 'OBSERVATIONS') && matchedObservations.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <h4 style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                <span>🌌</span> Astronomical Observations ({matchedObservations.length})
              </h4>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Target Name</th>
                      <th>Filename</th>
                      <th>Type</th>
                      <th>Telescope / Instrument</th>
                      <th>Obs Date / Time</th>
                      <th>Validation</th>
                      <th>ACIS Priority</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matchedObservations.map((obs) => {
                      const isOptical = obs.file_type.includes('OPTICAL') || obs.file_type.includes('IMAGE');
                      const cand = candidateMap.get(obs.id);
                      return (
                        <tr key={obs.id}>
                          <td>
                            <strong style={{ color: '#fff' }}>{obs.target_name || obs.file_name}</strong>
                          </td>
                          <td className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                            {obs.file_name}
                          </td>
                          <td>
                            <span className={`badge ${isOptical ? 'badge-optical' : 'badge-radio'}`}>
                              {isOptical ? 'Optical' : 'Radio'}
                            </span>
                          </td>
                          <td style={{ fontSize: '0.78rem' }}>
                            {obs.telescope || 'N/A'} {obs.instrument ? `• ${obs.instrument}` : ''}
                          </td>
                          <td className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                            {obs.observation_date || obs.created_at?.slice(0, 10)}
                          </td>
                          <td>
                            <span className={`badge ${obs.validation_status.includes('VALID') ? 'badge-completed' : 'badge-pending'}`}>
                              {obs.validation_status}
                            </span>
                          </td>
                          <td>
                            {cand ? (
                              <span
                                className={`badge ${
                                  cand.priority_group === 'HIGH'
                                    ? 'badge-high'
                                    : cand.priority_group === 'MEDIUM'
                                    ? 'badge-medium'
                                    : 'badge-low'
                                }`}
                              >
                                {cand.priority_group} ({cand.acis_score.toFixed(3)})
                              </span>
                            ) : (
                              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>—</span>
                            )}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', gap: '6px' }}>
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => onSelectObservation(obs.id)}
                              >
                                Inspect
                              </button>
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={(e) => handleDownloadPdf(e, obs.id)}
                                title="Download PDF Audit Report"
                              >
                                PDF
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── 2. PROCESSING RUNS SECTION ── */}
          {(activeCategory === 'ALL' || activeCategory === 'RUNS') && matchedRuns.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <h4 style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--accent-purple)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                <span>⚡</span> Pipeline Processing Runs ({matchedRuns.length})
              </h4>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Run Identifier</th>
                      <th>Associated Target</th>
                      <th>Pipeline Step</th>
                      <th>Status</th>
                      <th>Duration</th>
                      <th>Started At (UTC)</th>
                      <th>Log / Summary</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matchedRuns.map((run) => {
                      const associatedObs = run.observation_id ? obsMap.get(run.observation_id) : null;
                      return (
                        <tr key={run.id}>
                          <td className="mono" style={{ fontSize: '0.78rem', color: 'var(--primary)' }}>
                            {run.run_identifier}
                          </td>
                          <td>
                            {associatedObs ? (
                              <button
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  color: '#fff',
                                  cursor: 'pointer',
                                  fontWeight: 600,
                                  padding: 0,
                                  textDecoration: 'underline',
                                }}
                                onClick={() => onSelectObservation(associatedObs.id)}
                              >
                                {associatedObs.target_name || associatedObs.file_name}
                              </button>
                            ) : (
                              <span style={{ color: 'var(--text-dim)' }}>Global / Unlinked</span>
                            )}
                          </td>
                          <td>
                            <span className="badge mono" style={{ fontSize: '0.7rem' }}>
                              {run.pipeline_step}
                            </span>
                          </td>
                          <td>
                            <span
                              className={`badge ${
                                run.processing_status === 'COMPLETED'
                                  ? 'badge-completed'
                                  : run.processing_status === 'HALTED'
                                  ? 'badge-medium'
                                  : 'badge-low'
                              }`}
                            >
                              {run.processing_status}
                            </span>
                          </td>
                          <td className="mono" style={{ fontSize: '0.75rem' }}>
                            {run.elapsed_seconds != null ? `${run.elapsed_seconds.toFixed(2)}s` : '—'}
                          </td>
                          <td className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                            {run.started_at ? run.started_at.slice(0, 19).replace('T', ' ') : '—'}
                          </td>
                          <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {run.log_summary || run.error_message || 'OK'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── 3. CSV TABULAR DATASETS SECTION ── */}
          {(activeCategory === 'ALL' || activeCategory === 'CSV') && matchedCsvFiles.length > 0 && (
            <div>
              <h4 style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--success)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                <span>📊</span> CSV Tabular Datasets ({matchedCsvFiles.length})
              </h4>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Filename</th>
                      <th>Server Path</th>
                      <th>Size</th>
                      <th>Rows × Cols</th>
                      <th>Upload Date</th>
                      <th>Status</th>
                      <th style={{ textAlign: 'right' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matchedCsvFiles.map((csv) => (
                      <tr key={csv.server_name}>
                        <td style={{ fontWeight: 600, color: '#fff' }}>
                          📄 {csv.file_name}
                        </td>
                        <td className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                          {csv.server_file_path}
                        </td>
                        <td className="mono" style={{ fontSize: '0.78rem' }}>
                          {csv.file_size_kb} KB
                        </td>
                        <td className="mono" style={{ fontSize: '0.78rem', color: 'var(--primary)' }}>
                          {csv.total_rows != null ? `${csv.total_rows.toLocaleString()} rows × ${csv.total_columns} cols` : '—'}
                        </td>
                        <td className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                          {csv.upload_date}
                        </td>
                        <td>
                          <span className="badge badge-completed">
                            {csv.status}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => onNavigateTab && onNavigateTab('add-data')}
                          >
                            Inspect in Add Data →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
