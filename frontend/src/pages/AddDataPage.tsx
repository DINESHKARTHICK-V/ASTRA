import React, { useState, useRef } from 'react';
import { apiService, ApiError } from '../services/api';
import {
  FileUploadItem,
  AnalysisResult,
  CsvUploadResponse,
  CsvColumnStat,
  CsvAnalysisResult,
  CsvWorkflow,
} from '../types/api';

interface AddDataPageProps {
  onSelectObservation: (id: number) => void;
  onAnalysisStarted?: (runId: number) => void;
}

interface StagedFile {
  file: File;
  displayName: string;
}

type ActiveTab = 'fits' | 'csv';

export const AddDataPage: React.FC<AddDataPageProps> = ({
  onSelectObservation,
}) => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('fits');

  // ── FITS state ────────────────────────────────────────────
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [uploadedItems, setUploadedItems] = useState<FileUploadItem[] | null>(null);
  const [selectedWorkflows, setSelectedWorkflows] = useState<Record<number, string>>({});
  const [executingAnalysis, setExecutingAnalysis] = useState<Record<number, boolean>>({});
  const [analysisResults, setAnalysisResults] = useState<Record<number, AnalysisResult>>({});

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // ── CSV state ─────────────────────────────────────────────
  const [csvDragActive, setCsvDragActive] = useState(false);
  const [csvUploading, setCsvUploading] = useState(false);
  const [csvError, setCsvError] = useState<string | null>(null);
  const [csvResult, setCsvResult] = useState<CsvUploadResponse | null>(null);
  const [csvStagedFile, setCsvStagedFile] = useState<File | null>(null);
  const csvInputRef = useRef<HTMLInputElement | null>(null);

  // CSV Analysis state
  const [selectedCsvWorkflow, setSelectedCsvWorkflow] = useState<string>('');
  const [csvAnalyzing, setCsvAnalyzing] = useState(false);
  const [csvAnalysisError, setCsvAnalysisError] = useState<string | null>(null);
  const [csvAnalysisResult, setCsvAnalysisResult] = useState<CsvAnalysisResult | null>(null);
  const [activeCsvView, setActiveCsvView] = useState<'analysis' | 'columns' | 'preview'>('analysis');

  // ── FITS handlers ─────────────────────────────────────────
  const handleFilesSelected = (newFiles: FileList | null) => {
    if (!newFiles || newFiles.length === 0) return;
    setUploadError(null);

    const additions: StagedFile[] = [];
    for (let i = 0; i < newFiles.length; i++) {
      const f = newFiles[i];
      const defaultName = f.name.replace(/\.[^/.]+$/, '').replace(/_+/g, ' ').trim();
      additions.push({ file: f, displayName: defaultName });
    }
    setStagedFiles((prev) => [...prev, ...additions]);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelected(e.dataTransfer.files);
    }
  };

  const handleRemoveStaged = (index: number) => {
    setStagedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateDisplayName = (index: number, newName: string) => {
    setStagedFiles((prev) =>
      prev.map((item, i) => (i === index ? { ...item, displayName: newName } : item))
    );
  };

  const handleUploadSubmit = async () => {
    if (stagedFiles.length === 0) return;
    setUploading(true);
    setUploadError(null);

    try {
      const files = stagedFiles.map((s) => s.file);
      const names = stagedFiles.map((s) => s.displayName);
      const response = await apiService.uploadFiles(files, names);

      setUploadedItems(response.files);
      const initialSelected: Record<number, string> = {};
      response.files.forEach((item) => {
        if (item.available_workflows && item.available_workflows.length > 0) {
          initialSelected[item.observation_id] = item.available_workflows[0].id;
        }
      });
      setSelectedWorkflows(initialSelected);
      setStagedFiles([]);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setUploadError(err.message);
      } else {
        setUploadError('Upload validation failed. Please ensure files are valid FITS format.');
      }
    } finally {
      setUploading(false);
    }
  };

  const handleWorkflowChange = (observationId: number, workflowId: string) => {
    setSelectedWorkflows((prev) => ({ ...prev, [observationId]: workflowId }));
  };

  const handleStartAnalysis = async (item: FileUploadItem) => {
    const obsId = item.observation_id;
    const workflowId = selectedWorkflows[obsId];
    if (!workflowId) return;

    setExecutingAnalysis((prev) => ({ ...prev, [obsId]: true }));
    try {
      const result = await apiService.startAnalysis({
        observation_id: obsId,
        workflow_id: workflowId,
      });
      setAnalysisResults((prev) => ({ ...prev, [obsId]: result }));
    } catch (err: any) {
      alert(`Analysis failed: ${err?.message || 'Execution error'}`);
    } finally {
      setExecutingAnalysis((prev) => ({ ...prev, [obsId]: false }));
    }
  };

  const handleReset = () => {
    setUploadedItems(null);
    setStagedFiles([]);
    setSelectedWorkflows({});
    setAnalysisResults({});
    setUploadError(null);
  };

  // ── CSV handlers ──────────────────────────────────────────
  const handleCsvDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setCsvDragActive(true);
    else if (e.type === 'dragleave') setCsvDragActive(false);
  };

  const handleCsvDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setCsvDragActive(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleCsvFileSelected(f);
  };

  const handleCsvFileSelected = (f: File) => {
    setCsvError(null);
    setCsvResult(null);
    setCsvAnalysisResult(null);
    setCsvAnalysisError(null);
    if (!f.name.toLowerCase().endsWith('.csv')) {
      setCsvError('Only .csv files are accepted here.');
      return;
    }
    setCsvStagedFile(f);
  };

  const handleCsvUpload = async () => {
    if (!csvStagedFile) return;
    setCsvUploading(true);
    setCsvError(null);
    setCsvAnalysisError(null);
    try {
      const result = await apiService.uploadCsv(csvStagedFile);
      setCsvResult(result);
      setCsvStagedFile(null);
      // Auto-select pulsar inference if available, otherwise first workflow
      const pulsarWf = result.available_workflows?.find((w) => w.id === 'csv_pulsar_inference');
      const firstWf = result.available_workflows?.[0]?.id || '';
      setSelectedCsvWorkflow(pulsarWf ? pulsarWf.id : firstWf);
      setCsvAnalysisResult(null);
      setActiveCsvView('analysis');
    } catch (err: any) {
      setCsvError(err?.message || 'CSV upload failed.');
    } finally {
      setCsvUploading(false);
    }
  };

  const handleRunCsvAnalysis = async () => {
    if (!csvResult || !selectedCsvWorkflow) return;
    setCsvAnalyzing(true);
    setCsvAnalysisError(null);
    try {
      const res = await apiService.analyzeCsv(csvResult.server_file_path, selectedCsvWorkflow);
      setCsvAnalysisResult(res);
      setActiveCsvView('analysis');
    } catch (err: any) {
      setCsvAnalysisError(err?.message || 'CSV analysis failed.');
    } finally {
      setCsvAnalyzing(false);
    }
  };

  const handleCsvReset = () => {
    setCsvResult(null);
    setCsvStagedFile(null);
    setCsvError(null);
    setCsvAnalysisResult(null);
    setCsvAnalysisError(null);
    setSelectedCsvWorkflow('');
    setActiveCsvView('analysis');
  };

  // ── Helpers ───────────────────────────────────────────────
  const fmtNum = (v: number | string | null) =>
    v == null ? '—' : typeof v === 'number' ? v.toFixed(4) : v;

  // ── Render ────────────────────────────────────────────────
  return (
    <div className="page-container">
      {/* Tab switcher */}
      <div
        style={{
          display: 'flex',
          gap: '0',
          marginBottom: '20px',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        {(['fits', 'csv'] as ActiveTab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '10px 24px',
              background: 'transparent',
              border: 'none',
              borderBottom:
                activeTab === tab
                  ? '2px solid var(--primary)'
                  : '2px solid transparent',
              color: activeTab === tab ? 'var(--primary)' : 'var(--text-muted)',
              fontWeight: activeTab === tab ? 700 : 400,
              fontSize: '0.88rem',
              cursor: 'pointer',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              transition: 'color 0.2s, border-color 0.2s',
            }}
          >
            {tab === 'fits' ? '🔭 FITS Files' : '📊 CSV Data'}
          </button>
        ))}
      </div>

      {/* ──────────── FITS PANEL ──────────── */}
      {activeTab === 'fits' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {!uploadedItems ? (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">
                  <span>Ingest Astronomical Observations</span>
                </h3>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Supported: .fits, .fit, .fts, .fits.gz, .sf (PSRFITS)
                </span>
              </div>

              {uploadError && (
                <div
                  style={{
                    padding: '12px 16px',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: 'var(--radius-md)',
                    color: '#fca5a5',
                    fontSize: '0.82rem',
                    marginBottom: '16px',
                  }}
                >
                  ⚠️ {uploadError}
                </div>
              )}

              <div
                className={`dropzone ${dragActive ? 'drag-active' : ''}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".fits,.fit,.fts,.fits.gz,.sf"
                  style={{ display: 'none' }}
                  onChange={(e) => handleFilesSelected(e.target.files)}
                />
                <div className="dropzone-icon">📥</div>
                <h4 className="dropzone-title">Drag &amp; drop astronomical FITS files here</h4>
                <p className="dropzone-subtitle">or click to browse from local computer</p>
              </div>

              {stagedFiles.length > 0 && (
                <div className="upload-list">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h4 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#fff' }}>
                      Files Staged for Ingestion ({stagedFiles.length})
                    </h4>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => setStagedFiles([])}
                    >
                      Clear All
                    </button>
                  </div>

                  {stagedFiles.map((staged, idx) => (
                    <div key={idx} className="upload-item">
                      <div className="upload-item-info">
                        <span style={{ fontSize: '1.2rem' }}>📄</span>
                        <div>
                          <div className="mono" style={{ fontSize: '0.82rem', color: '#fff' }}>
                            {staged.file.name}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                            {(staged.file.size / (1024 * 1024)).toFixed(2)} MB
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          Display Name:
                        </label>
                        <input
                          type="text"
                          className="upload-item-name-input"
                          value={staged.displayName}
                          onChange={(e) => handleUpdateDisplayName(idx, e.target.value)}
                          placeholder="Observation Name"
                        />
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ color: 'var(--danger)' }}
                          onClick={() => handleRemoveStaged(idx)}
                          title="Remove file"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))}

                  <div style={{ marginTop: '14px', display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      className="btn btn-primary"
                      disabled={uploading}
                      onClick={handleUploadSubmit}
                    >
                      {uploading ? 'Validating & Ingesting...' : 'Upload & Choose Analysis →'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Post-Upload Scientific Analysis Selection */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div className="card">
                <div className="card-header">
                  <div>
                    <h3 className="card-title">
                      <span>Data Ingestion Validated</span>
                    </h3>
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Select an analysis workflow for each uploaded observation. Scientific analysis will not run until chosen.
                    </p>
                  </div>
                  <button className="btn btn-secondary btn-sm" onClick={handleReset}>
                    + Ingest More Files
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {uploadedItems.map((item) => {
                    const isOptical = item.detected_type.includes('OPTICAL') || item.detected_type.includes('IMAGE');
                    const isExecuting = executingAnalysis[item.observation_id] || false;
                    const result = analysisResults[item.observation_id];
                    const activeWorkflowId = selectedWorkflows[item.observation_id];

                    return (
                      <div
                        key={item.observation_id}
                        style={{
                          backgroundColor: 'rgba(255, 255, 255, 0.02)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--radius-lg)',
                          padding: '20px',
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            gap: '12px',
                            marginBottom: '16px',
                            borderBottom: '1px solid var(--border-subtle)',
                            paddingBottom: '12px',
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <strong style={{ fontSize: '1rem', color: '#fff' }}>
                                {item.display_name}
                              </strong>
                              <span className={`badge ${isOptical ? 'badge-optical' : 'badge-radio'}`}>
                                {isOptical ? 'Optical FITS' : 'Radio PSRFITS'}
                              </span>
                              {item.is_duplicate && (
                                <span className="badge badge-medium">Existing in catalog</span>
                              )}
                            </div>
                            <div className="mono" style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                              {item.file_name} • {item.file_size_mb} MB • Telescope: {item.telescope || 'N/A'} • Instrument: {item.instrument || 'N/A'}
                            </div>
                          </div>

                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => onSelectObservation(item.observation_id)}
                          >
                            Inspect Catalog Record
                          </button>
                        </div>

                        <div>
                          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                            Available Scientific Workflows for {isOptical ? 'Optical Data' : 'Radio Data'}:
                          </div>

                          <div className="workflow-grid">
                            {item.available_workflows.map((wf) => {
                              const isSelected = activeWorkflowId === wf.id;
                              return (
                                <div
                                  key={wf.id}
                                  className={`workflow-card ${isSelected ? 'selected' : ''}`}
                                  onClick={() => handleWorkflowChange(item.observation_id, wf.id)}
                                >
                                  <div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                      <div className="workflow-card-title">{wf.name}</div>
                                      <input
                                        type="radio"
                                        name={`wf-${item.observation_id}`}
                                        checked={isSelected}
                                        onChange={() => handleWorkflowChange(item.observation_id, wf.id)}
                                      />
                                    </div>
                                    <div className="workflow-card-desc">{wf.description}</div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>

                          <div
                            style={{
                              marginTop: '16px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              flexWrap: 'wrap',
                              gap: '12px',
                            }}
                          >
                            <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                              Selected: <strong style={{ color: 'var(--primary)' }}>{activeWorkflowId}</strong>
                            </div>
                            <button
                              className="btn btn-primary"
                              disabled={isExecuting || !activeWorkflowId}
                              onClick={() => handleStartAnalysis(item)}
                            >
                              {isExecuting ? 'Running Scientific Processing...' : '▶ Start Selected Analysis'}
                            </button>
                          </div>

                          {result && (
                            <div
                              style={{
                                marginTop: '16px',
                                padding: '16px',
                                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                                border: '1px solid var(--border-active)',
                                borderRadius: 'var(--radius-md)',
                              }}
                            >
                              <div
                                style={{
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  marginBottom: '8px',
                                }}
                              >
                                <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#fff' }}>
                                  Analysis Result: {result.workflow}
                                </span>
                                <span
                                  className={`badge ${
                                    result.status === 'COMPLETED'
                                      ? 'badge-completed'
                                      : result.status === 'HALTED'
                                      ? 'badge-halted'
                                      : 'badge-high'
                                  }`}
                                >
                                  {result.status} ({result.elapsed_seconds}s)
                                </span>
                              </div>

                              <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
                                {result.summary}
                              </p>

                              {result.details?.image_data_url && (
                                <div style={{ marginTop: '12px', textAlign: 'center' }}>
                                  <img
                                    src={result.details.image_data_url}
                                    alt="FITS Preview"
                                    style={{
                                      maxWidth: '100%',
                                      maxHeight: '380px',
                                      borderRadius: 'var(--radius-md)',
                                      border: '1px solid var(--border-subtle)',
                                    }}
                                  />
                                  <div className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '6px' }}>
                                    {result.details.slice_name} • {result.details.width}x{result.details.height} px • Range: [{result.details.min_val} .. {result.details.max_val}]
                                  </div>
                                </div>
                              )}

                              {result.details?.inference_status === 'INFERENCE_HALTED' && (
                                <div
                                  style={{
                                    marginTop: '10px',
                                    padding: '12px',
                                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                    border: '1px solid rgba(245, 158, 11, 0.3)',
                                    borderRadius: 'var(--radius-sm)',
                                    fontSize: '0.78rem',
                                    color: '#fef3c7',
                                  }}
                                >
                                  <strong>ML Prediction Unavailable:</strong> {result.details.halt_reason}
                                </div>
                              )}

                              <div style={{ marginTop: '12px', display: 'flex', gap: '10px' }}>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => onSelectObservation(item.observation_id)}
                                >
                                  View Full Observation Telemetry →
                                </button>
                                <button
                                  className="btn btn-outline btn-sm"
                                  onClick={() => apiService.downloadObservationReport(item.observation_id)}
                                >
                                  📄 Download PDF Report
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ──────────── CSV PANEL ──────────── */}
      {activeTab === 'csv' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">
                <span>Ingest CSV Tabular Data</span>
              </h3>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Supported: .csv — comma-separated values, UTF-8
              </span>
            </div>

            {csvError && (
              <div
                style={{
                  padding: '12px 16px',
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: 'var(--radius-md)',
                  color: '#fca5a5',
                  fontSize: '0.82rem',
                  marginBottom: '16px',
                }}
              >
                ⚠️ {csvError}
              </div>
            )}

            {!csvResult ? (
              <>
                {/* Drop zone */}
                <div
                  className={`dropzone ${csvDragActive ? 'drag-active' : ''}`}
                  onDragEnter={handleCsvDrag}
                  onDragLeave={handleCsvDrag}
                  onDragOver={handleCsvDrag}
                  onDrop={handleCsvDrop}
                  onClick={() => csvInputRef.current?.click()}
                >
                  <input
                    ref={csvInputRef}
                    type="file"
                    accept=".csv"
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) handleCsvFileSelected(f);
                    }}
                  />
                  <div className="dropzone-icon">📊</div>
                  <h4 className="dropzone-title">Drag &amp; drop a CSV file here</h4>
                  <p className="dropzone-subtitle">or click to browse from local computer</p>
                </div>

                {/* Staged CSV file */}
                {csvStagedFile && (
                  <div className="upload-list" style={{ marginTop: '16px' }}>
                    <div className="upload-item">
                      <div className="upload-item-info">
                        <span style={{ fontSize: '1.2rem' }}>📄</span>
                        <div>
                          <div className="mono" style={{ fontSize: '0.82rem', color: '#fff' }}>
                            {csvStagedFile.name}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                            {(csvStagedFile.size / 1024).toFixed(1)} KB
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <button
                          className="btn btn-primary"
                          disabled={csvUploading}
                          onClick={handleCsvUpload}
                        >
                          {csvUploading ? 'Parsing CSV...' : 'Upload & Preview →'}
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ color: 'var(--danger)' }}
                          onClick={() => setCsvStagedFile(null)}
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              /* ── CSV Result View ── */
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {/* Summary bar */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px',
                    padding: '14px 18px',
                    backgroundColor: 'rgba(99, 102, 241, 0.08)',
                    border: '1px solid rgba(99, 102, 241, 0.25)',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  <div style={{ display: 'flex', gap: '28px', flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>File</div>
                      <div className="mono" style={{ fontSize: '0.85rem', color: '#fff' }}>{csvResult.file_name}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Size</div>
                      <div className="mono" style={{ fontSize: '0.85rem', color: '#fff' }}>{csvResult.file_size_kb} KB</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Rows</div>
                      <div className="mono" style={{ fontSize: '0.85rem', color: 'var(--primary)' }}>{csvResult.total_rows.toLocaleString()}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Columns</div>
                      <div className="mono" style={{ fontSize: '0.85rem', color: 'var(--primary)' }}>{csvResult.total_columns}</div>
                    </div>
                  </div>
                  <button className="btn btn-secondary btn-sm" onClick={handleCsvReset}>
                    + Upload Another CSV
                  </button>
                </div>

                {/* ── Workflow Selection Card ── */}
                {csvResult.available_workflows && csvResult.available_workflows.length > 0 && (
                  <div
                    style={{
                      padding: '18px 20px',
                      backgroundColor: 'rgba(15, 23, 42, 0.75)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-lg)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '16px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                      <div>
                        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span>⚡</span> Choose Scientific Analysis Workflow
                        </h4>
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          Select an astronomical pipeline workflow to execute on this CSV dataset.
                        </p>
                      </div>

                      <button
                        className="btn btn-primary"
                        disabled={csvAnalyzing || !selectedCsvWorkflow}
                        onClick={handleRunCsvAnalysis}
                        style={{
                          padding: '9px 20px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          fontWeight: 600,
                          fontSize: '0.85rem',
                        }}
                      >
                        {csvAnalyzing ? (
                          <>
                            <span className="spinner" style={{ width: '14px', height: '14px' }}></span>
                            <span>Executing Analysis...</span>
                          </>
                        ) : (
                          <>
                            <span>▶ Run Analysis</span>
                          </>
                        )}
                      </button>
                    </div>

                    {csvAnalysisError && (
                      <div
                        style={{
                          padding: '10px 14px',
                          backgroundColor: 'rgba(239, 68, 68, 0.12)',
                          border: '1px solid rgba(239, 68, 68, 0.3)',
                          borderRadius: 'var(--radius-md)',
                          color: '#fca5a5',
                          fontSize: '0.8rem',
                        }}
                      >
                        ⚠️ {csvAnalysisError}
                      </div>
                    )}

                    {/* Workflow Options Grid */}
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                        gap: '12px',
                      }}
                    >
                      {csvResult.available_workflows.map((wf: CsvWorkflow) => {
                        const isSelected = selectedCsvWorkflow === wf.id;
                        const icon =
                          wf.id === 'csv_pulsar_inference'
                            ? '⚡'
                            : wf.id === 'csv_correlation'
                            ? '🔥'
                            : '📊';
                        const badgeColor =
                          wf.category === 'ml'
                            ? 'var(--radio)'
                            : wf.category === 'visualization'
                            ? 'var(--primary)'
                            : 'var(--success)';

                        return (
                          <div
                            key={wf.id}
                            onClick={() => setSelectedCsvWorkflow(wf.id)}
                            style={{
                              padding: '14px 16px',
                              borderRadius: 'var(--radius-md)',
                              border: isSelected
                                ? '1.5px solid var(--primary)'
                                : '1px solid var(--border-subtle)',
                              backgroundColor: isSelected
                                ? 'rgba(14, 165, 233, 0.12)'
                                : 'rgba(255, 255, 255, 0.02)',
                              cursor: 'pointer',
                              transition: 'all 0.2s ease',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '6px',
                              boxShadow: isSelected
                                ? '0 0 16px rgba(14, 165, 233, 0.15)'
                                : 'none',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ fontSize: '1.1rem' }}>{icon}</span>
                                <span style={{ fontWeight: 600, color: '#fff', fontSize: '0.85rem' }}>
                                  {wf.name}
                                </span>
                              </div>
                              <span
                                className="badge mono"
                                style={{
                                  fontSize: '0.65rem',
                                  textTransform: 'uppercase',
                                  backgroundColor: 'rgba(255,255,255,0.06)',
                                  color: badgeColor,
                                  borderColor: badgeColor,
                                }}
                              >
                                {wf.category}
                              </span>
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                              {wf.description}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* ── Sub Navigation Tabs ── */}
                <div
                  style={{
                    display: 'flex',
                    gap: '8px',
                    borderBottom: '1px solid var(--border-subtle)',
                    paddingBottom: '8px',
                  }}
                >
                  <button
                    className={`btn btn-sm ${activeCsvView === 'analysis' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveCsvView('analysis')}
                    style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <span>🔬 Analysis Results</span>
                    {csvAnalysisResult && (
                      <span
                        style={{
                          fontSize: '0.65rem',
                          backgroundColor: 'var(--success)',
                          color: '#fff',
                          borderRadius: '50%',
                          width: '14px',
                          height: '14px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        ✓
                      </span>
                    )}
                  </button>
                  <button
                    className={`btn btn-sm ${activeCsvView === 'columns' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveCsvView('columns')}
                  >
                    📊 Column Statistics ({csvResult.columns.length})
                  </button>
                  <button
                    className={`btn btn-sm ${activeCsvView === 'preview' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveCsvView('preview')}
                  >
                    📄 Data Preview (first {csvResult.preview_rows.length} rows)
                  </button>
                </div>

                {/* ── VIEW 1: Scientific Analysis Results ── */}
                {activeCsvView === 'analysis' && (
                  <div>
                    {!csvAnalysisResult ? (
                      <div
                        style={{
                          textAlign: 'center',
                          padding: '40px 20px',
                          backgroundColor: 'rgba(255,255,255,0.015)',
                          borderRadius: 'var(--radius-lg)',
                          border: '1px dashed var(--border-subtle)',
                        }}
                      >
                        <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>🔭</div>
                        <h4 style={{ color: '#fff', fontSize: '1rem', fontWeight: 600, marginBottom: '6px' }}>
                          No Analysis Executed Yet
                        </h4>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', maxWidth: '480px', margin: '0 auto 16px' }}>
                          Pick an available workflow above and click <strong>&quot;Run Analysis&quot;</strong> to generate statistical insights, correlation structures, or ML pulsar classifications.
                        </p>
                        {selectedCsvWorkflow && (
                          <button
                            className="btn btn-primary"
                            disabled={csvAnalyzing}
                            onClick={handleRunCsvAnalysis}
                          >
                            {csvAnalyzing ? 'Executing Analysis...' : '▶ Run Selected Workflow Now'}
                          </button>
                        )}
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        {/* Summary Header Banner */}
                        <div
                          style={{
                            padding: '14px 18px',
                            backgroundColor: 'rgba(16, 185, 129, 0.08)',
                            border: '1px solid rgba(16, 185, 129, 0.25)',
                            borderRadius: 'var(--radius-md)',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            gap: '10px',
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <span
                                className="badge"
                                style={{
                                  backgroundColor: 'rgba(16, 185, 129, 0.2)',
                                  color: 'var(--success)',
                                  borderColor: 'var(--success)',
                                  fontWeight: 700,
                                }}
                              >
                                {csvAnalysisResult.status}
                              </span>
                              <span style={{ color: '#fff', fontWeight: 600, fontSize: '0.9rem' }}>
                                {csvAnalysisResult.workflow_id === 'csv_pulsar_inference'
                                  ? 'Pulsar ML Classification'
                                  : csvAnalysisResult.workflow_id === 'csv_correlation'
                                  ? 'Pearson Correlation Matrix'
                                  : 'Statistical Summary & Distributions'}
                              </span>
                              <span className="mono" style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>
                                ({csvAnalysisResult.elapsed_seconds.toFixed(2)}s)
                              </span>
                            </div>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '6px' }}>
                              {csvAnalysisResult.summary}
                            </div>
                          </div>
                        </div>

                        {/* WORKFLOW SPECIFIC RENDERERS */}
                        {/* 1. Pulsar ML Inference */}
                        {csvAnalysisResult.workflow_id === 'csv_pulsar_inference' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                            {/* KPI Metrics */}
                            <div
                              style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                                gap: '12px',
                              }}
                            >
                              <div
                                style={{
                                  padding: '14px 16px',
                                  backgroundColor: 'rgba(168, 85, 247, 0.1)',
                                  border: '1px solid rgba(168, 85, 247, 0.3)',
                                  borderRadius: 'var(--radius-md)',
                                }}
                              >
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                                  Pulsar Candidates
                                </div>
                                <div className="mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--radio)', marginTop: '4px' }}>
                                  {csvAnalysisResult.details.pulsar_candidates ?? 0}
                                </div>
                                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                                  Detection Rate: {csvAnalysisResult.details.pulsar_rate_pct}%
                                </div>
                              </div>

                              <div
                                style={{
                                  padding: '14px 16px',
                                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                                  border: '1px solid var(--border-subtle)',
                                  borderRadius: 'var(--radius-md)',
                                }}
                              >
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                                  Total Rows Scored
                                </div>
                                <div className="mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fff', marginTop: '4px' }}>
                                  {csvAnalysisResult.details.total_rows_scored ?? 0}
                                </div>
                                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                                  Skipped (NaN): {csvAnalysisResult.details.rows_skipped ?? 0}
                                </div>
                              </div>

                              <div
                                style={{
                                  padding: '14px 16px',
                                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                                  border: '1px solid var(--border-subtle)',
                                  borderRadius: 'var(--radius-md)',
                                }}
                              >
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                                  Noise / RFI Rejections
                                </div>
                                <div className="mono" style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-muted)', marginTop: '4px' }}>
                                  {csvAnalysisResult.details.noise_rfi ?? 0}
                                </div>
                                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                                  P(pulsar) &lt; 0.50 threshold
                                </div>
                              </div>

                              <div
                                style={{
                                  padding: '14px 16px',
                                  backgroundColor: 'rgba(14, 165, 233, 0.08)',
                                  border: '1px solid rgba(14, 165, 233, 0.25)',
                                  borderRadius: 'var(--radius-md)',
                                }}
                              >
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                                  Inference Model
                                </div>
                                <div className="mono" style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--primary)', marginTop: '6px' }}>
                                  {csvAnalysisResult.details.model_used || 'RandomForestClassifier'}
                                </div>
                                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                                  8 Canonical HTRU2 Features
                                </div>
                              </div>
                            </div>

                            {/* Dual Chart Visualization */}
                            {csvAnalysisResult.details.chart_url && (
                              <div
                                style={{
                                  padding: '16px',
                                  backgroundColor: 'rgba(7, 10, 18, 0.8)',
                                  border: '1px solid var(--border-subtle)',
                                  borderRadius: 'var(--radius-lg)',
                                  textAlign: 'center',
                                }}
                              >
                                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                  Candidate Probability Distribution &amp; Classification Breakdown
                                </h4>
                                <img
                                  src={csvAnalysisResult.details.chart_url}
                                  alt="Pulsar ML Classification Chart"
                                  style={{
                                    maxWidth: '100%',
                                    height: 'auto',
                                    borderRadius: 'var(--radius-md)',
                                    border: '1px solid var(--border-subtle)',
                                  }}
                                />
                              </div>
                            )}

                            {/* Top Pulsar Candidates Table */}
                            {csvAnalysisResult.details.top_candidates && csvAnalysisResult.details.top_candidates.length > 0 && (
                              <div>
                                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                  Top High-Confidence Pulsar Candidates (Ranked by Probability)
                                </h4>
                                <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                    <thead>
                                      <tr style={{ backgroundColor: 'rgba(255,255,255,0.04)' }}>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>Rank</th>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>Row #</th>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>Probability</th>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>Class</th>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>Profile Mean</th>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>Profile Std</th>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>DM Mean</th>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>DM Std</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {csvAnalysisResult.details.top_candidates.map((cand: any) => {
                                        const prob = cand.pulsar_probability;
                                        const probPct = (prob * 100).toFixed(1);
                                        return (
                                          <tr
                                            key={cand.rank}
                                            style={{
                                              backgroundColor: cand.rank % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                                            }}
                                          >
                                            <td style={{ padding: '9px 14px', color: '#fff', fontWeight: 700 }}>
                                              #{cand.rank}
                                            </td>
                                            <td className="mono" style={{ padding: '9px 14px', color: 'var(--primary)' }}>
                                              Row {cand.row_index}
                                            </td>
                                            <td style={{ padding: '9px 14px' }}>
                                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                <div
                                                  style={{
                                                    width: '60px',
                                                    height: '6px',
                                                    backgroundColor: 'rgba(255,255,255,0.1)',
                                                    borderRadius: '3px',
                                                    overflow: 'hidden',
                                                  }}
                                                >
                                                  <div
                                                    style={{
                                                      width: `${probPct}%`,
                                                      height: '100%',
                                                      backgroundColor: prob >= 0.8 ? 'var(--radio)' : 'var(--primary)',
                                                    }}
                                                  />
                                                </div>
                                                <span className="mono" style={{ color: prob >= 0.8 ? 'var(--radio)' : '#fff', fontWeight: 600 }}>
                                                  {probPct}%
                                                </span>
                                              </div>
                                            </td>
                                            <td style={{ padding: '9px 14px' }}>
                                              <span
                                                className="badge"
                                                style={{
                                                  backgroundColor: cand.predicted_class === 1 ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255,255,255,0.05)',
                                                  color: cand.predicted_class === 1 ? 'var(--radio)' : 'var(--text-dim)',
                                                  borderColor: cand.predicted_class === 1 ? 'var(--radio)' : 'transparent',
                                                  fontSize: '0.7rem',
                                                }}
                                              >
                                                {cand.predicted_class === 1 ? '★ PULSAR' : 'NOISE'}
                                              </span>
                                            </td>
                                            <td className="mono" style={{ padding: '9px 14px', color: 'var(--text-muted)' }}>
                                              {cand.features?.Profile_Mean != null ? cand.features.Profile_Mean.toFixed(2) : '—'}
                                            </td>
                                            <td className="mono" style={{ padding: '9px 14px', color: 'var(--text-muted)' }}>
                                              {cand.features?.Profile_Std != null ? cand.features.Profile_Std.toFixed(2) : '—'}
                                            </td>
                                            <td className="mono" style={{ padding: '9px 14px', color: 'var(--text-muted)' }}>
                                              {cand.features?.DM_Mean != null ? cand.features.DM_Mean.toFixed(2) : '—'}
                                            </td>
                                            <td className="mono" style={{ padding: '9px 14px', color: 'var(--text-muted)' }}>
                                              {cand.features?.DM_Std != null ? cand.features.DM_Std.toFixed(2) : '—'}
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* 2. Correlation Matrix */}
                        {csvAnalysisResult.workflow_id === 'csv_correlation' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                            {csvAnalysisResult.details.heatmap_url && (
                              <div
                                style={{
                                  padding: '16px',
                                  backgroundColor: 'rgba(7, 10, 18, 0.8)',
                                  border: '1px solid var(--border-subtle)',
                                  borderRadius: 'var(--radius-lg)',
                                  textAlign: 'center',
                                }}
                              >
                                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                  Pearson Correlation Heatmap
                                </h4>
                                <img
                                  src={csvAnalysisResult.details.heatmap_url}
                                  alt="Correlation Heatmap"
                                  style={{
                                    maxWidth: '100%',
                                    maxHeight: '620px',
                                    borderRadius: 'var(--radius-md)',
                                    border: '1px solid var(--border-subtle)',
                                  }}
                                />
                              </div>
                            )}

                            {/* Top Correlations Table */}
                            {csvAnalysisResult.details.top_correlations && csvAnalysisResult.details.top_correlations.length > 0 && (
                              <div>
                                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                  Top Co-Linear Variable Pairs
                                </h4>
                                <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                    <thead>
                                      <tr style={{ backgroundColor: 'rgba(255,255,255,0.04)' }}>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>Feature A</th>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>Feature B</th>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>Pearson r</th>
                                        <th style={{ padding: '10px 14px', textAlign: 'left', color: 'var(--text-muted)' }}>Correlation Strength</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {csvAnalysisResult.details.top_correlations.map((pair: any, idx: number) => {
                                        const absR = Math.abs(pair.r);
                                        const strength =
                                          absR >= 0.8
                                            ? 'Strong'
                                            : absR >= 0.5
                                            ? 'Moderate'
                                            : 'Weak';
                                        return (
                                          <tr
                                            key={idx}
                                            style={{
                                              backgroundColor: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                                            }}
                                          >
                                            <td style={{ padding: '9px 14px', color: '#fff', fontWeight: 600 }}>{pair.col_a}</td>
                                            <td style={{ padding: '9px 14px', color: '#fff', fontWeight: 600 }}>{pair.col_b}</td>
                                            <td className="mono" style={{ padding: '9px 14px', color: pair.r > 0 ? 'var(--primary)' : 'var(--danger)', fontWeight: 700 }}>
                                              {pair.r > 0 ? `+${pair.r.toFixed(4)}` : pair.r.toFixed(4)}
                                            </td>
                                            <td style={{ padding: '9px 14px' }}>
                                              <span
                                                className="badge mono"
                                                style={{
                                                  fontSize: '0.7rem',
                                                  backgroundColor: absR >= 0.8 ? 'rgba(14, 165, 233, 0.2)' : 'rgba(255,255,255,0.05)',
                                                  color: absR >= 0.8 ? 'var(--primary)' : 'var(--text-muted)',
                                                }}
                                              >
                                                {strength}
                                              </span>
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* 3. Statistical Summary */}
                        {csvAnalysisResult.workflow_id === 'csv_statistics' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                            {csvAnalysisResult.details.histogram_url && (
                              <div
                                style={{
                                  padding: '16px',
                                  backgroundColor: 'rgba(7, 10, 18, 0.8)',
                                  border: '1px solid var(--border-subtle)',
                                  borderRadius: 'var(--radius-lg)',
                                  textAlign: 'center',
                                }}
                              >
                                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                  Feature Distribution Histograms
                                </h4>
                                <img
                                  src={csvAnalysisResult.details.histogram_url}
                                  alt="Histograms"
                                  style={{
                                    maxWidth: '100%',
                                    borderRadius: 'var(--radius-md)',
                                    border: '1px solid var(--border-subtle)',
                                  }}
                                />
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* ── VIEW 2: Column statistics ── */}
                {activeCsvView === 'columns' && (
                  <div>
                    <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Column Statistics
                    </h4>
                    <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                        <thead>
                          <tr style={{ backgroundColor: 'rgba(255,255,255,0.04)' }}>
                            {['Column', 'Type', 'Non-Null', 'Nulls', 'Min', 'Max', 'Mean'].map((h) => (
                              <th
                                key={h}
                                style={{
                                  padding: '10px 14px',
                                  textAlign: 'left',
                                  color: 'var(--text-muted)',
                                  fontWeight: 600,
                                  whiteSpace: 'nowrap',
                                  borderBottom: '1px solid var(--border-subtle)',
                                }}
                              >
                                {h}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {csvResult.columns.map((col: CsvColumnStat, i: number) => (
                            <tr
                              key={col.name}
                              style={{
                                backgroundColor: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                                transition: 'background 0.15s',
                              }}
                            >
                              <td style={{ padding: '9px 14px', color: '#fff', fontWeight: 600, whiteSpace: 'nowrap' }}>{col.name}</td>
                              <td><span className="badge badge-medium mono" style={{ fontSize: '0.72rem' }}>{col.dtype}</span></td>
                              <td style={{ padding: '9px 14px', color: 'var(--accent)' }}>{col.non_null.toLocaleString()}</td>
                              <td style={{ padding: '9px 14px', color: col.null_count > 0 ? '#fca5a5' : 'var(--text-dim)' }}>{col.null_count}</td>
                              <td className="mono" style={{ padding: '9px 14px', color: 'var(--text-muted)', fontSize: '0.77rem' }}>{fmtNum(col.min)}</td>
                              <td className="mono" style={{ padding: '9px 14px', color: 'var(--text-muted)', fontSize: '0.77rem' }}>{fmtNum(col.max)}</td>
                              <td className="mono" style={{ padding: '9px 14px', color: 'var(--text-muted)', fontSize: '0.77rem' }}>{col.mean != null ? col.mean.toFixed(4) : '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* ── VIEW 3: Row preview ── */}
                {activeCsvView === 'preview' && (
                  <div>
                    <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Data Preview (first {csvResult.preview_rows.length} rows)
                    </h4>
                    <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                        <thead>
                          <tr style={{ backgroundColor: 'rgba(255,255,255,0.04)' }}>
                            {csvResult.columns.map((col: CsvColumnStat) => (
                              <th
                                key={col.name}
                                style={{
                                  padding: '9px 12px',
                                  textAlign: 'left',
                                  color: 'var(--primary)',
                                  fontWeight: 600,
                                  whiteSpace: 'nowrap',
                                  borderBottom: '1px solid var(--border-subtle)',
                                }}
                              >
                                {col.name}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {csvResult.preview_rows.map((row: Record<string, any>, i: number) => (
                            <tr
                              key={i}
                              style={{
                                backgroundColor: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                              }}
                            >
                              {csvResult.columns.map((col: CsvColumnStat) => (
                                <td
                                  key={col.name}
                                  className="mono"
                                  style={{
                                    padding: '8px 12px',
                                    color: row[col.name] == null ? 'var(--text-dim)' : 'var(--text-muted)',
                                    whiteSpace: 'nowrap',
                                    borderBottom: '1px solid rgba(255,255,255,0.04)',
                                  }}
                                >
                                  {row[col.name] == null ? 'null' : String(row[col.name])}
                                </td>
                              ))}
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
        </div>
      )}
    </div>
  );
};
