import React, { useEffect, useState, useCallback } from 'react';
import { apiService, ApiError } from '../services/api';
import { CsvDataResponse } from '../types/api';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorMessage } from './ErrorMessage';

interface CsvFileExplorerProps {
  serverName: string;
  onBack: () => void;
  onDeleteSuccess?: () => void;
}

export const CsvFileExplorer: React.FC<CsvFileExplorerProps> = ({
  serverName,
  onBack,
}) => {
  const [loading, setLoading] = useState(true);
  const [pageLoading, setPageLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dataResponse, setDataResponse] = useState<CsvDataResponse | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  // Active view tab
  const [activeTab, setActiveTab] = useState<'data' | 'structure'>('data');

  // Action states
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [csvDownloading, setCsvDownloading] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Rename observation association modal
  const [isEditingObsName, setIsEditingObsName] = useState(false);
  const [newObsName, setNewObsName] = useState('');
  const [renameLoading, setRenameLoading] = useState(false);

  const loadData = useCallback(async (page: number, size: number, initial = false) => {
    if (initial) setLoading(true);
    else setPageLoading(true);
    setError(null);
    try {
      const res = await apiService.getCsvData(serverName, page, size);
      setDataResponse(res);
      setCurrentPage(res.page);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load CSV file details and contents.');
      }
    } finally {
      if (initial) setLoading(false);
      else setPageLoading(false);
    }
  }, [serverName]);

  useEffect(() => {
    loadData(1, pageSize, true);
  }, [loadData, pageSize]);

  const handlePageChange = (newPage: number) => {
    if (!dataResponse || newPage < 1 || newPage > dataResponse.total_pages) return;
    loadData(newPage, pageSize, false);
  };

  const handleDownloadPdf = async () => {
    if (!dataResponse) return;
    setPdfDownloading(true);
    setActionMessage(null);
    try {
      await apiService.downloadCsvReport(
        serverName,
        dataResponse.file_info.observation_name || dataResponse.file_info.file_name
      );
      setActionMessage({ type: 'success', text: 'PDF report generated and downloaded successfully.' });
    } catch (err: any) {
      setActionMessage({ type: 'error', text: `PDF generation failed: ${err?.message || 'Unknown error'}` });
    } finally {
      setPdfDownloading(false);
    }
  };

  const handleDownloadOriginalCsv = async () => {
    if (!dataResponse) return;
    setCsvDownloading(true);
    setActionMessage(null);
    try {
      await apiService.downloadOriginalCsv(
        serverName,
        dataResponse.file_info.file_name
      );
      setActionMessage({ type: 'success', text: 'Original CSV downloaded successfully.' });
    } catch (err: any) {
      setActionMessage({ type: 'error', text: `CSV download failed: ${err?.message || 'Unknown error'}` });
    } finally {
      setCsvDownloading(false);
    }
  };

  const handleSaveObsName = async () => {
    const trimmed = newObsName.trim();
    if (!trimmed) return;
    setRenameLoading(true);
    try {
      const updated = await apiService.updateCsvMetadata(serverName, trimmed);
      if (dataResponse) {
        setDataResponse({
          ...dataResponse,
          file_info: {
            ...dataResponse.file_info,
            observation_name: updated.observation_name,
          },
        });
      }
      setIsEditingObsName(false);
      setActionMessage({ type: 'success', text: `Observation association updated to "${trimmed}".` });
    } catch (err: any) {
      setActionMessage({ type: 'error', text: `Update failed: ${err?.message || 'Error updating observation name'}` });
    } finally {
      setRenameLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Reading and indexing CSV dataset records..." />;
  }

  if (error || !dataResponse) {
    return (
      <div className="page-container">
        <button
          className="btn btn-secondary btn-sm"
          onClick={onBack}
          style={{ marginBottom: '16px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          ← Return to Parent Observation
        </button>
        <ErrorMessage
          title="CSV Explorer Error"
          message={error || 'CSV dataset not found or unreadable.'}
          onRetry={() => loadData(1, pageSize, true)}
        />
      </div>
    );
  }

  const { file_info, columns, rows, total_rows, total_pages, page } = dataResponse;
  const parentObsName = file_info.observation_name || file_info.file_name.replace(/\.csv$/i, '');

  return (
    <div className="csv-explorer-view" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* ── Top Navigation & Action Header ── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          paddingBottom: '14px',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={onBack}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontWeight: 600 }}
            title="Return to parent observation catalog"
          >
            ← Return to Observation: <span style={{ color: '#fff' }}>{parentObsName}</span>
          </button>
          <span className="badge badge-completed" style={{ fontSize: '0.72rem' }}>
            {file_info.status}
          </span>
        </div>

        {/* File Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleDownloadPdf}
            disabled={pdfDownloading}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            title="Generate a publication-grade PDF report of this CSV file"
          >
            {pdfDownloading ? 'Generating PDF...' : '📄 Generate PDF'}
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleDownloadOriginalCsv}
            disabled={csvDownloading}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            title="Download the unchanged original CSV file"
          >
            {csvDownloading ? 'Downloading...' : '💾 Download Original CSV'}
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => loadData(currentPage, pageSize, false)}
            disabled={pageLoading}
            title="Refresh CSV data preview"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionMessage && (
        <div
          style={{
            padding: '10px 14px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.8rem',
            backgroundColor: actionMessage.type === 'success' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
            border: `1px solid ${actionMessage.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            color: actionMessage.type === 'success' ? '#6ee7b7' : '#fca5a5',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>{actionMessage.type === 'success' ? '✓' : '⚠️'} {actionMessage.text}</span>
          <button
            onClick={() => setActionMessage(null)}
            style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '0.9rem' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* ── SECTION A: File Information Card ── */}
      <div className="card" style={{ padding: '16px 20px', backgroundColor: 'rgba(255, 255, 255, 0.02)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px', marginBottom: '14px' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>📊</span> CSV Dataset: <span className="mono" style={{ color: 'var(--primary)' }}>{file_info.file_name}</span>
            </h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '3px' }}>
              Storage identifier: <span className="mono" style={{ color: 'var(--text-dim)' }}>{file_info.server_name}</span>
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>Associated Observation:</span>
            {!isEditingObsName ? (
              <span
                style={{
                  fontWeight: 600,
                  color: '#fff',
                  backgroundColor: 'rgba(255, 255, 255, 0.06)',
                  padding: '3px 8px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.8rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                {parentObsName}
                <button
                  onClick={() => {
                    setNewObsName(parentObsName);
                    setIsEditingObsName(true);
                  }}
                  style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.75rem', opacity: 0.7 }}
                  title="Edit associated observation group name"
                >
                  ✏️
                </button>
              </span>
            ) : (
              <div style={{ display: 'inline-flex', gap: '4px', alignItems: 'center' }}>
                <input
                  type="text"
                  className="input mono"
                  style={{ padding: '3px 8px', fontSize: '0.78rem', width: '180px' }}
                  value={newObsName}
                  onChange={(e) => setNewObsName(e.target.value)}
                  placeholder="Observation name"
                />
                <button
                  className="btn btn-primary btn-sm"
                  style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                  onClick={handleSaveObsName}
                  disabled={renameLoading}
                >
                  {renameLoading ? '...' : 'Save'}
                </button>
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                  onClick={() => setIsEditingObsName(false)}
                >
                  ✕
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Key Metrics Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: '12px',
          }}
        >
          <div style={{ padding: '10px 14px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Records</div>
            <div className="mono" style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff', marginTop: '2px' }}>
              {total_rows != null ? total_rows.toLocaleString() : 'N/A'}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '2px' }}>Data rows</div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Column Count</div>
            <div className="mono" style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff', marginTop: '2px' }}>
              {columns.length}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '2px' }}>Attributes cataloged</div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>File Size</div>
            <div className="mono" style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff', marginTop: '2px' }}>
              {file_info.file_size_kb < 1024 ? `${file_info.file_size_kb.toFixed(1)} KB` : `${(file_info.file_size_kb / 1024).toFixed(2)} MB`}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '2px' }}>Raw disk footprint</div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Ingestion Date</div>
            <div className="mono" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#fff', marginTop: '4px' }}>
              {file_info.upload_date.slice(0, 10)}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '2px' }}>{file_info.upload_date.slice(11)}</div>
          </div>
        </div>
      </div>

      {/* ── Tabs Navigation: CSV Data vs Data Structure ── */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
        <button
          className={`btn btn-sm ${activeTab === 'data' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('data')}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <span>📄 CSV Data</span>
          <span className="mono" style={{ fontSize: '0.7rem', opacity: 0.8 }}>({total_rows.toLocaleString()} rows)</span>
        </button>
        <button
          className={`btn btn-sm ${activeTab === 'structure' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('structure')}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <span>📊 Data Structure & Column Statistics</span>
          <span className="mono" style={{ fontSize: '0.7rem', opacity: 0.8 }}>({columns.length} columns)</span>
        </button>
      </div>

      {/* ── SECTION B: CSV Data View (Table with Horizontal Scroll & Pagination) ── */}
      {activeTab === 'data' && (
        <div className="card" style={{ padding: '16px' }}>
          {/* Table Header Toolbar & Pagination Bar */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
              marginBottom: '12px',
            }}
          >
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Showing rows <strong style={{ color: '#fff' }}>{((page - 1) * pageSize) + 1}</strong> to{' '}
              <strong style={{ color: '#fff' }}>{Math.min(page * pageSize, total_rows)}</strong> of{' '}
              <strong style={{ color: '#fff' }}>{total_rows.toLocaleString()}</strong> records
              {pageLoading && <span style={{ marginLeft: '10px', color: 'var(--primary)' }}>Loading page...</span>}
            </div>

            {/* Pagination Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginRight: '8px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    const newSize = Number(e.target.value);
                    setPageSize(newSize);
                    loadData(1, newSize, false);
                  }}
                  style={{
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    color: '#fff',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '3px 6px',
                    fontSize: '0.75rem',
                  }}
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={250}>250</option>
                </select>
              </div>

              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handlePageChange(1)}
                disabled={page <= 1 || pageLoading}
                style={{ padding: '3px 8px' }}
                title="First Page"
              >
                «
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1 || pageLoading}
                style={{ padding: '3px 8px' }}
                title="Previous Page"
              >
                ‹ Prev
              </button>
              <span className="mono" style={{ fontSize: '0.76rem', color: 'var(--text-muted)', padding: '0 6px' }}>
                Page <strong style={{ color: '#fff' }}>{page}</strong> of <strong>{total_pages}</strong>
              </span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= total_pages || pageLoading}
                style={{ padding: '3px 8px' }}
                title="Next Page"
              >
                Next ›
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handlePageChange(total_pages)}
                disabled={page >= total_pages || pageLoading}
                style={{ padding: '3px 8px' }}
                title="Last Page"
              >
                »
              </button>
            </div>
          </div>

          {/* Horizontally Scrollable Data Table */}
          <div
            className="table-container"
            style={{
              maxHeight: '620px',
              overflowX: 'auto',
              overflowY: 'auto',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <table className="data-table" style={{ width: 'max-content', minWidth: '100%' }}>
              <thead style={{ position: 'sticky', top: 0, zIndex: 2, backgroundColor: '#0f172a' }}>
                <tr>
                  <th style={{ width: '56px', textAlign: 'center', backgroundColor: '#0f172a' }}>#</th>
                  {columns.map((col) => (
                    <th key={col.name} style={{ whiteSpace: 'nowrap', backgroundColor: '#0f172a' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span style={{ color: '#fff', fontWeight: 600 }}>{col.name}</span>
                        <span style={{ fontSize: '0.62rem', color: 'var(--text-dim)', fontWeight: 400 }}>
                          {col.inferred_type}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length + 1} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      No data rows in this CSV dataset.
                    </td>
                  </tr>
                ) : (
                  rows.map((row) => (
                    <tr key={row._row_index}>
                      <td className="mono" style={{ textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.72rem' }}>
                        {row._row_index}
                      </td>
                      {columns.map((col) => {
                        const cellVal = row[col.name];
                        const isNull = cellVal === null || cellVal === undefined;
                        return (
                          <td key={col.name} className="mono" style={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                            {isNull ? (
                              <span style={{ color: 'var(--text-dim)', fontStyle: 'italic', opacity: 0.6 }}>—</span>
                            ) : (
                              String(cellVal)
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Bottom Pagination Bar */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '12px',
              paddingTop: '8px',
              borderTop: '1px solid var(--border-subtle)',
            }}
          >
            <span style={{ fontSize: '0.74rem', color: 'var(--text-dim)' }}>
              Source records rendered verbatim without client-side formula execution or value modification.
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1 || pageLoading}
                style={{ padding: '2px 8px', fontSize: '0.74rem' }}
              >
                ‹ Prev
              </button>
              <span className="mono" style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                {page} / {total_pages}
              </span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= total_pages || pageLoading}
                style={{ padding: '2px 8px', fontSize: '0.74rem' }}
              >
                Next ›
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── SECTION C: Data Structure & Column Statistics View ── */}
      {activeTab === 'structure' && (
        <div className="card" style={{ padding: '16px 20px' }}>
          <div style={{ marginBottom: '14px' }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#fff', marginBottom: '4px' }}>
              Attribute Schema & Descriptive Statistics ({columns.length} columns)
            </h4>
            <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
              Algorithmic data type inference, population counts, and descriptive numeric distributions computed strictly from raw CSV records.
            </p>
          </div>

          <div className="table-container" style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Column Name</th>
                  <th>Inferred Data Type</th>
                  <th>Non-Empty Records</th>
                  <th>Missing Values</th>
                  <th>Min Value</th>
                  <th>Max Value</th>
                  <th>Mean Value</th>
                  <th>Std Deviation</th>
                </tr>
              </thead>
              <tbody>
                {columns.map((col) => {
                  const typeColor =
                    col.inferred_type === 'Integer'
                      ? 'var(--primary)'
                      : col.inferred_type === 'Decimal'
                      ? '#38bdf8'
                      : col.inferred_type === 'Date'
                      ? 'var(--success)'
                      : col.inferred_type === 'Boolean'
                      ? '#c084fc'
                      : 'var(--text-muted)';

                  return (
                    <tr key={col.name}>
                      <td className="mono" style={{ fontWeight: 600, color: '#fff' }}>
                        {col.name}
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            fontSize: '0.68rem',
                            color: typeColor,
                            borderColor: typeColor,
                            backgroundColor: 'rgba(255, 255, 255, 0.04)',
                          }}
                        >
                          {col.inferred_type}
                        </span>
                      </td>
                      <td className="mono" style={{ fontSize: '0.78rem' }}>
                        {col.non_empty_count.toLocaleString()}{' '}
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>
                          ({total_rows > 0 ? ((col.non_empty_count / total_rows) * 100).toFixed(1) : 0}%)
                        </span>
                      </td>
                      <td className="mono" style={{ fontSize: '0.78rem' }}>
                        {col.missing_count > 0 ? (
                          <span style={{ color: '#fca5a5' }}>
                            {col.missing_count.toLocaleString()}{' '}
                            <span style={{ fontSize: '0.68rem', opacity: 0.8 }}>
                              ({((col.missing_count / total_rows) * 100).toFixed(1)}%)
                            </span>
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-dim)' }}>0</span>
                        )}
                      </td>
                      <td className="mono" style={{ fontSize: '0.78rem', color: col.min != null ? '#fff' : 'var(--text-dim)' }}>
                        {col.min != null ? String(col.min) : '—'}
                      </td>
                      <td className="mono" style={{ fontSize: '0.78rem', color: col.max != null ? '#fff' : 'var(--text-dim)' }}>
                        {col.max != null ? String(col.max) : '—'}
                      </td>
                      <td className="mono" style={{ fontSize: '0.78rem', color: col.mean != null ? '#fff' : 'var(--text-dim)' }}>
                        {col.mean != null ? col.mean.toFixed(4) : '—'}
                      </td>
                      <td className="mono" style={{ fontSize: '0.78rem', color: col.std != null ? '#fff' : 'var(--text-dim)' }}>
                        {col.std != null ? col.std.toFixed(4) : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Scientific Disclaimer Card */}
          <div
            style={{
              marginTop: '16px',
              padding: '12px 16px',
              backgroundColor: 'rgba(56, 189, 248, 0.06)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.76rem',
              color: '#bae6fd',
              lineHeight: 1.5,
            }}
          >
            <strong>Scientific Integrity & Provenance Protocol:</strong> Inferred data types and descriptive statistics presented above are non-inferential source summaries calculated strictly from uploaded CSV cell values. In accordance with platform standards, generic CSV attributes are segregated from supervised pulsar ML classifiers and ACIS heuristic candidate scoring without manual pipeline verification.
          </div>
        </div>
      )}
    </div>
  );
};
