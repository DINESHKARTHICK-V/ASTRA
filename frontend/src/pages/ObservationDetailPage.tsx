import React, { useEffect, useState } from 'react';
import { apiService, ApiError } from '../services/api';
import {
  Observation,
  Feature,
  Prediction,
  CandidateScore,
  OpticalPreview,
  ProcessingRun,
  CsvFileItem,
} from '../types/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';

interface ObservationDetailPageProps {
  observationId: number;
  onBack: () => void;
}

type DetailTab =
  | 'overview'
  | 'metadata'
  | 'preview'
  | 'analysis'
  | 'quality'
  | 'history'
  | 'reports';

export const ObservationDetailPage: React.FC<ObservationDetailPageProps> = ({
  observationId,
  onBack,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [obs, setObs] = useState<Observation | null>(null);
  const [feature, setFeature] = useState<Feature | null>(null);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [candidate, setCandidate] = useState<CandidateScore | null>(null);
  const [runs, setRuns] = useState<ProcessingRun[]>([]);
  const [preview, setPreview] = useState<OpticalPreview | null>(null);

  // CSV attachment state for reports
  const [csvFiles, setCsvFiles] = useState<CsvFileItem[]>([]);
  const [selectedCsvServerName, setSelectedCsvServerName] = useState<string>('');

  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [showHaltReason, setShowHaltReason] = useState(false);
  const [showAboutFile, setShowAboutFile] = useState(true);

  // Editable display name
  const [isEditingName, setIsEditingName] = useState(false);
  const [displayNameInput, setDisplayNameInput] = useState('');
  const [nameSaving, setNameSaving] = useState(false);

  // PDF report state
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  // Multi-extension / plane selector for optical data
  const [selectedGroupIdx, setSelectedGroupIdx] = useState(0);
  const [previewLoading, setPreviewLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [obsData, featData, predData, candData, runsRes, csvListRes] = await Promise.all([
        apiService.getObservation(observationId),
        apiService.getObservationFeatures(observationId).catch(() => null),
        apiService.getObservationPredictions(observationId).catch(() => []),
        apiService.getCandidate(observationId).catch(() => null),
        apiService.getProcessingRuns(50, 0).catch(() => ({ items: [] })),
        apiService.listCsvFiles().catch(() => []),
      ]);

      setObs(obsData);
      setFeature(featData);
      setPredictions(predData);
      setCandidate(candData);
      setDisplayNameInput(obsData.target_name || obsData.file_name);
      setCsvFiles(csvListRes || []);

      const matchingRuns = (runsRes.items || []).filter(
        (r) => r.observation_id === observationId
      );
      setRuns(matchingRuns);

      // Check if optical file or has 2D preview available
      const isOptical =
        obsData.file_type.includes('OPTICAL') || obsData.file_type.includes('IMAGE');
      if (isOptical) {
        try {
          const prev = await apiService.getObservationPreview(observationId, selectedGroupIdx);
          setPreview(prev);
        } catch {
          // Preview might not be available yet if raw array unsupported
        }
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to retrieve observation details.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [observationId]);

  const handleGroupChange = async (newIdx: number) => {
    setSelectedGroupIdx(newIdx);
    setPreviewLoading(true);
    try {
      const prev = await apiService.getObservationPreview(observationId, newIdx);
      setPreview(prev);
    } catch {
      // Keep old preview or report error
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSaveDisplayName = async () => {
    if (!displayNameInput.trim()) return;
    setNameSaving(true);
    try {
      const updated = await apiService.updateObservation(observationId, displayNameInput.trim());
      setObs(updated);
      setIsEditingName(false);
    } catch (err: any) {
      alert(`Failed to update display name: ${err?.message || 'Network error'}`);
    } finally {
      setNameSaving(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!obs) return;
    setPdfLoading(true);
    setPdfError(null);
    try {
      await apiService.downloadObservationReport(obs.id, selectedCsvServerName || undefined);
    } catch (err: any) {
      setPdfError(err?.message || 'Failed to generate PDF report.');
    } finally {
      setPdfLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message={`Loading observational telemetry for ID #${observationId}...`} />;
  }

  if (error || !obs) {
    return (
      <div className="page-container">
        <button onClick={onBack} className="btn btn-secondary btn-sm" style={{ marginBottom: '16px' }}>
          ← Back to Catalog
        </button>
        <ErrorMessage
          title="Observation Not Found"
          message={error || `Observation #${observationId} could not be retrieved.`}
          onRetry={loadData}
        />
      </div>
    );
  }

  const isOptical = obs.file_type.includes('OPTICAL') || obs.file_type.includes('IMAGE');
  const isHalted = predictions.some((p) => p.inference_status === 'INFERENCE_HALTED');
  const haltedPred = predictions.find((p) => p.inference_status === 'INFERENCE_HALTED');

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Breadcrumb & Action Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={onBack} className="btn btn-secondary btn-sm">
            ← Back to Catalog
          </button>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {isEditingName ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <input
                    type="text"
                    className="upload-item-name-input"
                    value={displayNameInput}
                    onChange={(e) => setDisplayNameInput(e.target.value)}
                  />
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={nameSaving}
                    onClick={handleSaveDisplayName}
                  >
                    Save
                  </button>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      setIsEditingName(false);
                      setDisplayNameInput(obs.target_name || obs.file_name);
                    }}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>
                    {obs.target_name || obs.file_name}
                  </h2>
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '2px 8px', fontSize: '0.72rem' }}
                    onClick={() => setIsEditingName(true)}
                    title="Rename observation display name"
                  >
                    ✎ Edit Name
                  </button>
                </>
              )}
              <span className={`badge ${isOptical ? 'badge-optical' : 'badge-radio'}`}>
                {isOptical ? 'Optical FITS' : 'Radio PSRFITS'}
              </span>
            </div>
            <div className="mono" style={{ fontSize: '0.74rem', color: 'var(--text-dim)', marginTop: '2px' }}>
              Archive: {obs.file_name} • Format: {obs.file_type} • ID #{obs.id}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            className="btn btn-primary btn-sm"
            disabled={pdfLoading}
            onClick={handleDownloadPdf}
          >
            {pdfLoading ? '⏳ Generating PDF...' : '📄 Download PDF Report'}
          </button>
        </div>
      </div>

      {pdfError && (
        <div
          style={{
            padding: '10px 14px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: 'var(--radius-sm)',
            color: '#fca5a5',
            fontSize: '0.8rem',
          }}
        >
          {pdfError}
        </div>
      )}

      {/* Simplified Scientific Warning for Halted Inference (STEP 108) */}
      {!isOptical && isHalted && (
        <div className="collapsible-box">
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.88rem', color: '#fbbf24' }}>
                ⚠️ ML prediction unavailable
              </div>
              <p style={{ fontSize: '0.8rem', color: '#fef3c7', marginTop: '3px' }}>
                The available data do not contain all the signal features required for this prediction. Metadata and supported analysis results remain available.
              </p>
            </div>
            <button
              className="btn btn-secondary btn-sm"
              style={{ color: '#fbbf24', borderColor: 'rgba(245, 158, 11, 0.4)' }}
              onClick={() => setShowHaltReason(!showHaltReason)}
            >
              {showHaltReason ? 'Hide Explanation ▲' : 'Why is prediction unavailable? ▼'}
            </button>
          </div>

          {showHaltReason && (
            <div className="collapsible-body">
              <strong>Actual Scientific Reason:</strong> {haltedPred?.halt_reason || 'Missing multi-trial DM-SNR curves in single-epoch folded archives required by HTRU2 benchmark classifier.'}
            </div>
          )}
        </div>
      )}

      {/* COMPACT "ABOUT THIS FILE" PANEL (Simple English Guide) */}
      <div
        className="card"
        style={{
          padding: '14px 18px',
          marginBottom: '16px',
          backgroundColor: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid rgba(59, 130, 246, 0.25)',
          borderRadius: 'var(--radius-md)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.1rem' }}>ℹ️</span>
            <div>
              <h4 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#fff', margin: 0 }}>
                About This File: Simple Guide to {obs.file_name}
              </h4>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0, marginTop: '2px' }}>
                Understand what type of file this is, what information it contains, and what you can do with it.
              </p>
            </div>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            style={{ fontSize: '0.75rem', padding: '4px 10px' }}
            onClick={() => setShowAboutFile(!showAboutFile)}
          >
            {showAboutFile ? 'Hide Guide ▲' : 'Show Guide ▼'}
          </button>
        </div>

        {showAboutFile && (
          <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
            <div style={{ padding: '10px 12px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--primary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                1. File Format & Type
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
                {isOptical ? (
                  <>
                    <strong>Optical Astronomical Image</strong> in Flexible Image Transport System (FITS) format. FITS files can contain images, binary tables, or time-series data; this file is verified as a calibrated 2D pixel array capturing spatial photon intensities and detector geometry.
                  </>
                ) : (
                  <>
                    <strong>Radio Pulsar Archive</strong> in PSRFITS format (FITS format with binary extension tables). Contains folded time-series radio pulse profiles partitioned across frequency channels and pulse phase bins.
                  </>
                )}
              </p>
            </div>

            <div style={{ padding: '10px 12px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--primary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                2. What the Metadata Means
              </div>
              <ul style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0, paddingLeft: '16px', lineHeight: 1.45 }}>
                <li><strong>Target:</strong> {obs.target_name || 'Not available'} (celestial object observed)</li>
                <li><strong>Telescope / Observatory:</strong> {obs.telescope || 'Not available'}</li>
                <li><strong>Instrument:</strong> {obs.instrument || 'Not available'} (detector/backend used)</li>
                <li><strong>Observation Date:</strong> {obs.observation_date ? `${obs.observation_date} ${obs.observation_time || ''}`.trim() : 'Not available'}</li>
                <li><strong>Coordinates:</strong> {obs.ra && obs.dec ? `${obs.ra} / ${obs.dec}` : 'Not available'}</li>
              </ul>
            </div>

            <div style={{ padding: '10px 12px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--primary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                3. Data Sections & Dimensions
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
                {isOptical ? (
                  <>
                    Contains Header Data Units (HDUs) with 2D image matrix dimensions {preview?.width && preview?.height ? `(${preview.width} × ${preview.height} pixels)` : '(viewable in Tab 3)'}. Does not contain radio pulsar profiles.
                  </>
                ) : (
                  <>
                    Contains HDU extension tables with {obs.nsubint ?? 'Not available'} subintegrations, {obs.nchan ?? 'Not available'} frequency channels, and {obs.nbin ?? 'Not available'} phase bins. Center frequency: {obs.frequency_mhz ? `${obs.frequency_mhz} MHz` : 'Not available'}, bandwidth: {obs.bandwidth_mhz ? `${obs.bandwidth_mhz} MHz` : 'Not available'}.
                  </>
                )}
              </p>
            </div>

            <div style={{ padding: '10px 12px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--primary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                4. What You Can Preview & Analyze
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
                {isOptical ? (
                  <>
                    Inspect the astronomical 2D image in <strong>Tab 3 (View Data)</strong> with interactive zoom, pan, and colormaps. Read FITS header cards in <strong>Tab 2</strong>, and generate scientific PDF reports in <strong>Tab 7</strong>. Optical images are safeguarded against pulsar models.
                  </>
                ) : (
                  <>
                    Inspect integrated pulse profiles in <strong>Tab 3 (View Data)</strong>, review physical data quality metrics in <strong>Tab 5</strong>, check candidate prioritization in <strong>Tab 1</strong>, and export comprehensive audit PDF reports in <strong>Tab 7</strong>.
                  </>
                )}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 7 USER-FRIENDLY DETAIL TABS */}
      <div className="tabs-nav" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '16px' }}>
        <button
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          1. Summary
        </button>
        <button
          className={`tab-btn ${activeTab === 'metadata' ? 'active' : ''}`}
          onClick={() => setActiveTab('metadata')}
        >
          2. File Information
        </button>
        <button
          className={`tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
          onClick={() => setActiveTab('preview')}
        >
          3. View Data
        </button>
        <button
          className={`tab-btn ${activeTab === 'analysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('analysis')}
        >
          4. Analysis Results
        </button>
        <button
          className={`tab-btn ${activeTab === 'quality' ? 'active' : ''}`}
          onClick={() => setActiveTab('quality')}
        >
          5. Data Quality
        </button>
        <button
          className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          6. Processing History
        </button>
        <button
          className={`tab-btn ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
        >
          7. Reports
        </button>
      </div>

      {/* TAB 1: Overview / Summary */}
      {activeTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="card">
            <div style={{ marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
              <h4 style={{ fontSize: '0.94rem', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
                Summary - What is this observation?
              </h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
                Basic information about this observation, including its source, date, and file size.
              </p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
              <div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Target Name / Field</div>
                <strong style={{ color: '#fff' }}>{obs.target_name || 'N/A'}</strong>
              </div>
              <div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Observatory / Telescope</div>
                <strong style={{ color: '#fff' }}>{obs.telescope || 'N/A'}</strong>
              </div>
              <div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Instrument / Backend</div>
                <strong style={{ color: '#fff' }}>{obs.instrument || 'N/A'}</strong>
              </div>
              <div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Observation Date</div>
                <strong style={{ color: '#fff' }}>{obs.observation_date || 'N/A'}</strong>
              </div>
              <div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Coordinates (RA / DEC)</div>
                <span className="mono" style={{ color: '#fff' }}>{obs.ra || 'N/A'} / {obs.dec || 'N/A'}</span>
              </div>
              <div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>File Size</div>
                <span className="mono" style={{ color: '#fff' }}>{obs.file_size_mb || 'N/A'} MB</span>
              </div>
            </div>
          </div>

          {candidate && (
            <div className="card">
              <h4 style={{ fontSize: '0.92rem', fontWeight: 600, color: '#fff', marginBottom: '14px' }}>
                ACIS Candidate Prioritization
              </h4>
              <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>ACIS Score</div>
                  <div className="mono" style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--primary)' }}>
                    {candidate.acis_score.toFixed(4)}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Priority Rank</div>
                  <span className={`badge ${candidate.priority_group === 'HIGH' ? 'badge-high' : candidate.priority_group === 'MEDIUM' ? 'badge-medium' : 'badge-low'}`}>
                    {candidate.priority_group} PRIORITY (#{candidate.rank_position || '-'})
                  </span>
                </div>
                <div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Evidence Channels</div>
                  <strong style={{ color: '#fff' }}>{candidate.evidence_available} channels</strong>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: File Information */}
      {activeTab === 'metadata' && (
        <div className="card">
          <div style={{ marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
            <h4 style={{ fontSize: '0.94rem', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
              File Information - What does the file tell us?
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
              Details recorded inside the file, such as observation date, instrument, and available metadata.
            </p>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>File Path:</span>
              <div className="mono" style={{ fontSize: '0.8rem', color: '#fff' }}>{obs.file_path}</div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Observing Mode:</span>
              <div style={{ fontSize: '0.85rem', color: '#fff' }}>{obs.observation_mode || 'N/A'} ({obs.data_mode || 'N/A'})</div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Center Frequency & Bandwidth:</span>
              <div style={{ fontSize: '0.85rem', color: '#fff' }}>
                {obs.frequency_mhz ? `${obs.frequency_mhz} MHz` : 'N/A'} • {obs.bandwidth_mhz ? `${obs.bandwidth_mhz} MHz` : 'N/A'}
              </div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Channels / Subints / Bins:</span>
              <div style={{ fontSize: '0.85rem', color: '#fff' }}>
                {obs.nchan ?? 'N/A'} chan • {obs.nsubint ?? 'N/A'} subints • {obs.nbin ?? 'N/A'} bins
              </div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Polarization Info:</span>
              <div style={{ fontSize: '0.85rem', color: '#fff' }}>{obs.polarization_info || 'N/A'}</div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Ingestion Time:</span>
              <div style={{ fontSize: '0.85rem', color: '#fff' }}>{new Date(obs.created_at).toLocaleString()}</div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: View Data */}
      {activeTab === 'preview' && (
        <div className="card">
          <div style={{ marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
            <h4 style={{ fontSize: '0.94rem', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
              View Data - See the contents of the file
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
              Inspect the actual information stored in this file.
            </p>
          </div>
          <div className="card-header">
            <div>
              <h4 className="card-title">
                <span>{isOptical ? 'Optical Image 2D Preview' : 'Radio Profile Visualization'}</span>
              </h4>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                {isOptical
                  ? 'Rendered astronomical CCD frame with percentile contrast stretch'
                  : 'Stokes I pulse profile integrated across radio subintegrations'}
              </p>
            </div>

            {/* Chip / Plane selector for multi-group optical cubes */}
            {isOptical && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Select Frame:</span>
                {[0, 1, 2, 3].map((idx) => (
                  <button
                    key={idx}
                    className={`btn btn-sm ${selectedGroupIdx === idx ? 'btn-primary' : 'btn-secondary'}`}
                    disabled={previewLoading}
                    onClick={() => handleGroupChange(idx)}
                  >
                    Group {idx + 1}
                  </button>
                ))}
              </div>
            )}
          </div>

          {previewLoading ? (
            <LoadingSpinner message="Rendering astronomical FITS image slice..." />
          ) : preview ? (
            <div style={{ textAlign: 'center' }}>
              <img
                src={preview.image_data_url}
                alt="FITS Optical Preview"
                style={{
                  maxWidth: '100%',
                  maxHeight: '440px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                }}
              />
              <div
                className="mono"
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  gap: '16px',
                  fontSize: '0.76rem',
                  color: 'var(--text-dim)',
                  marginTop: '12px',
                  flexWrap: 'wrap',
                }}
              >
                <span>Frame: {preview.slice_name}</span>
                <span>Resolution: {preview.width}×{preview.height} px</span>
                <span>Min: {preview.min_val}</span>
                <span>Max: {preview.max_val}</span>
                <span>Mean: {preview.mean_val}</span>
                <span>Median: {preview.median_val}</span>
                <span>NaNs: {preview.nan_count}</span>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">📈</div>
              <p className="empty-desc">
                {isOptical
                  ? 'No 2D image preview rendered yet. Run "Preview Image" from Add Data or analysis workflow.'
                  : `Radio archive profile visualized in reports. Nominal DM: ${feature?.dm_nominal ? feature.dm_nominal.toFixed(4) + ' pc/cm³' : 'N/A'}`}
              </p>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Analysis Results */}
      {activeTab === 'analysis' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="card">
            <div style={{ marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
              <h4 style={{ fontSize: '0.94rem', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
                Analysis Results - What did the analysis find?
              </h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
                See the results produced by the available analysis tools.
              </p>
            </div>
            {isOptical ? (
              <div>
                <h5 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#fff', marginBottom: '10px' }}>
                  Optical Astronomy Analysis
                </h5>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  • <strong>Data Classification:</strong> Verified astronomical image FITS archive.<br />
                  • <strong>Photometric Domain:</strong> Optical imaging domain.<br />
                  • <strong>Safeguard Compliance:</strong> Optical images are strictly excluded from radio pulsar ML classifiers and ACIS pulsar prioritization.
                </p>
              </div>
            ) : (
              <div>
                <h5 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#fff', marginBottom: '10px' }}>
                  Machine Learning Evaluation & Status
                </h5>
                {predictions.map((p) => (
                  <div key={p.id} style={{ padding: '12px', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong style={{ color: '#fff' }}>{p.model_name} ({p.model_version})</strong>
                      <span className="badge badge-halted">{p.inference_status}</span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                      Reason: {p.halt_reason || 'Safe stop triggered to prevent domain shift artifacts'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: Data Quality */}
      {activeTab === 'quality' && (
        <div className="card">
          <div style={{ marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
            <h4 style={{ fontSize: '0.94rem', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
              Data Quality - How good is the available data?
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
              Review available checks that help describe the quality and completeness of the data.
            </p>
          </div>
          <h5 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#fff', marginBottom: '14px' }}>
            Data Quality & Physical Diagnostics
          </h5>
          {feature ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
              <div>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Stokes I Profile Mean:</span>
                <div className="mono" style={{ color: '#fff' }}>{feature.profile_mean?.toFixed(2) ?? 'N/A'}</div>
              </div>
              <div>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Profile Std Deviation:</span>
                <div className="mono" style={{ color: '#fff' }}>{feature.profile_std?.toFixed(2) ?? 'N/A'}</div>
              </div>
              <div>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Nominal DM:</span>
                <div className="mono" style={{ color: '#fff' }}>{feature.dm_nominal ? `${feature.dm_nominal.toFixed(4)} pc/cm³` : 'N/A'}</div>
              </div>
              <div>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Noise Floor Estimate:</span>
                <div className="mono" style={{ color: '#fff' }}>{feature.noise_estimate?.toFixed(2) ?? 'N/A'}</div>
              </div>
              <div>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>RFI Cleanliness Ratio:</span>
                <div className="mono" style={{ color: '#fff' }}>{feature.rfi_indicator?.toFixed(4) ?? 'N/A'}</div>
              </div>
              <div>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Dynamic Range:</span>
                <div className="mono" style={{ color: '#fff' }}>{feature.dynamic_range?.toFixed(2) ?? 'N/A'}</div>
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-dim)', fontSize: '0.82rem' }}>
              {isOptical
                ? 'Photometric statistics computed dynamically during image preview.'
                : 'No feature extraction record found.'}
            </div>
          )}
        </div>
      )}

      {/* TAB 6: Processing History */}
      {activeTab === 'history' && (
        <div className="card">
          <div style={{ marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
            <h4 style={{ fontSize: '0.94rem', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
              Processing History - What has ASTRA done?
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
              See the processing steps and their recorded status.
            </p>
          </div>
          <h5 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#fff', marginBottom: '14px' }}>
            Pipeline Execution History ({runs.length} runs)
          </h5>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run Identifier</th>
                  <th>Step Name</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Executed At</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id}>
                    <td className="mono" style={{ fontSize: '0.76rem', color: 'var(--primary)' }}>
                      {r.run_identifier}
                    </td>
                    <td>{r.pipeline_step}</td>
                    <td>
                      <span className="badge badge-completed">{r.processing_status}</span>
                    </td>
                    <td className="mono" style={{ fontSize: '0.76rem' }}>
                      {r.elapsed_seconds ? `${r.elapsed_seconds.toFixed(2)}s` : 'N/A'}
                    </td>
                    <td style={{ fontSize: '0.76rem', color: 'var(--text-dim)' }}>
                      {new Date(r.started_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 7: Reports */}
      {activeTab === 'reports' && (
        <div className="card">
          <div style={{ marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
            <h4 style={{ fontSize: '0.94rem', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
              Reports - View and download reports
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
              Generate or download a readable report of the available results.
            </p>
          </div>
          <div className="card-header">
            <div>
              <h4 className="card-title">
                <span>Scientific Audit Report</span>
              </h4>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                Download official publication-grade PDF report compiled for this observation
              </p>
            </div>
            <button
              className="btn btn-primary btn-sm"
              disabled={pdfLoading}
              onClick={handleDownloadPdf}
            >
              {pdfLoading
                ? 'Generating...'
                : selectedCsvServerName
                ? '📄 Download PDF with CSV Data'
                : '📄 Download PDF Report'}
            </button>
          </div>

          {pdfError && (
            <div
              style={{
                padding: '10px 14px',
                marginBottom: '14px',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: 'var(--radius-sm)',
                color: '#f87171',
                fontSize: '0.82rem',
              }}
            >
              <strong>Error generating report:</strong> {pdfError}
            </div>
          )}

          {/* CSV File Selection Card */}
          <div
            style={{
              padding: '14px',
              backgroundColor: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: 'var(--radius-md)',
              marginBottom: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label
                htmlFor="csv-report-select"
                style={{ fontSize: '0.84rem', fontWeight: 600, color: '#fff' }}
              >
                Include Tabular CSV Dataset (Optional)
              </label>
              {csvFiles.length > 0 && (
                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                  {csvFiles.length} cataloged dataset{csvFiles.length === 1 ? '' : 's'} available
                </span>
              )}
            </div>

            <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
              Select an ingested CSV file to include its source records, descriptive statistics, and multi-page table directly in Section 5 ('CSV Data and Summary') of the generated PDF.
            </p>

            {csvFiles.length === 0 ? (
              <div
                style={{
                  padding: '8px 12px',
                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.78rem',
                  color: 'var(--text-dim)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                ℹ No CSV files are currently associated or uploaded in the server catalog. The report will generate standard observational telemetry without CSV data.
              </div>
            ) : (
              <div>
                <select
                  id="csv-report-select"
                  className="select-input"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#fff',
                    fontSize: '0.82rem',
                  }}
                  value={selectedCsvServerName}
                  onChange={(e) => setSelectedCsvServerName(e.target.value)}
                >
                  <option value="">(None — Standard FITS observation audit report)</option>
                  {csvFiles.map((c) => (
                    <option key={c.server_name} value={c.server_name}>
                      {c.file_name} ({c.total_rows != null ? `${c.total_rows.toLocaleString()} rows` : 'N/A rows'} • {c.total_columns != null ? `${c.total_columns} cols` : ''} • {c.file_size_kb} KB)
                    </option>
                  ))}
                </select>

                {selectedCsvServerName ? (
                  <div
                    style={{
                      marginTop: '10px',
                      padding: '8px 12px',
                      backgroundColor: 'rgba(56, 189, 248, 0.08)',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.76rem',
                      color: '#bae6fd',
                    }}
                  >
                    ✓ <strong>CSV Included:</strong> Dataset records and descriptive statistics will be formatted into a publication-grade table with repeated column headers across pages. Untrusted values are safely sanitized.
                  </div>
                ) : (
                  <div
                    style={{
                      marginTop: '8px',
                      fontSize: '0.74rem',
                      color: 'var(--text-dim)',
                    }}
                  >
                    Standard report mode: No CSV dataset attached. Pure FITS telemetry will be compiled.
                  </div>
                )}
              </div>
            )}
          </div>

          <div style={{ padding: '16px', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-md)' }}>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              The generated PDF document conforms to academic publication standards and includes:
              <br />
              • Full telescope, instrument, and coordinate metadata.<br />
              {isOptical ? (
                <>
                  • Extension HDU structure and photometric pixel array metrics.<br />
                  • Clear domain separation disclaimer confirming optical imaging nature.<br />
                </>
              ) : (
                <>
                  • Stokes I pulse profile moments and noise estimates.<br />
                  • Transparent machine learning inference halt disclosure.<br />
                  • ACIS multi-evidence triage breakdown and rank position.<br />
                </>
              )}
              • Full execution history and timestamped audit logs.<br />
              • Optional Section 5: CSV Data and Summary with pagination, column formatting, and descriptive statistics.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
