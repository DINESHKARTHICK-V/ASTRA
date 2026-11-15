import React, { useEffect, useState, useMemo } from 'react';
import { apiService, ApiError } from '../services/api';
import { Observation, CandidateScore, CsvFileItem, ObservationGroup } from '../types/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';
import { CsvFileExplorer } from '../components/CsvFileExplorer';

interface ObservationsPageProps {
  onSelectObservation: (id: number) => void;
}

export const ObservationsPage: React.FC<ObservationsPageProps> = ({
  onSelectObservation,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [observations, setObservations] = useState<Observation[]>([]);
  const [candidates, setCandidates] = useState<CandidateScore[]>([]);
  const [csvFiles, setCsvFiles] = useState<CsvFileItem[]>([]);

  // Selected CSV server name for dedicated CSV File Explorer view
  const [selectedCsvServerName, setSelectedCsvServerName] = useState<string | null>(null);

  // Category filter: FITS observations vs CSV datasets
  const [catalogScope, setCatalogScope] = useState<'ALL' | 'FITS' | 'CSV'>('ALL');

  // Search & Type Filtering
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<'ALL' | 'RADIO' | 'OPTICAL'>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Expanded observation groups state (set of group_name strings)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  // ── Rename Modal State ────────────────────────────────────
  const [renameModalOpen, setRenameModalOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<{
    type: 'GROUP' | 'FILE';
    id?: number;
    currentName: string;
    fileCount?: number;
  } | null>(null);
  const [newDisplayName, setNewDisplayName] = useState('');
  const [renameLoading, setRenameLoading] = useState(false);
  const [renameError, setRenameError] = useState<string | null>(null);

  // ── Delete Modal State ────────────────────────────────────
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{
    type: 'GROUP' | 'FILE' | 'CSV';
    id?: number;
    name: string;
    serverName?: string;
    fileCount?: number;
    obsIds?: number[];
    csvServerNames?: string[];
  } | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Feedback banner
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [obsRes, candRes, csvRes] = await Promise.all([
        apiService.getObservations(500, 0),
        apiService.getCandidates(500, 0).catch(() => ({ items: [], total: 0 })),
        apiService.listCsvFiles().catch(() => []),
      ]);
      setObservations(obsRes.items);
      setCandidates(candRes.items);
      setCsvFiles(csvRes);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load observations catalog.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  // Candidate map for ACIS lookup
  const candidateMap = useMemo(() => {
    const map = new Map<number, CandidateScore>();
    candidates.forEach((c) => map.set(c.observation_id, c));
    return map;
  }, [candidates]);

  // Toggle group expansion
  const toggleGroup = (groupName: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupName)) {
        next.delete(groupName);
      } else {
        next.add(groupName);
      }
      return next;
    });
  };

  const expandAllGroups = () => {
    const all = new Set(observationGroups.map((g) => g.group_name));
    setExpandedGroups(all);
  };

  const collapseAllGroups = () => {
    setExpandedGroups(new Set());
  };

  // ── Group Observations by Observation Name (FITS + CSV) ─────
  const observationGroups = useMemo<ObservationGroup[]>(() => {
    const groupsMap = new Map<string, { fits: Observation[]; csv: CsvFileItem[] }>();

    // 1. Group FITS observations by target_name (or file_name if target_name is missing)
    observations.forEach((obs) => {
      const key = (obs.target_name || obs.file_name).trim();
      if (!groupsMap.has(key)) {
        groupsMap.set(key, { fits: [], csv: [] });
      }
      groupsMap.get(key)!.fits.push(obs);
    });

    // 2. Group CSV files by observation_name (or file_name without .csv)
    csvFiles.forEach((csv) => {
      const key = (csv.observation_name || csv.file_name.replace(/\.csv$/i, '')).trim();
      if (!groupsMap.has(key)) {
        groupsMap.set(key, { fits: [], csv: [] });
      }
      groupsMap.get(key)!.csv.push(csv);
    });

    const groups: ObservationGroup[] = [];

    groupsMap.forEach(({ fits, csv }, groupName) => {
      // Find best ACIS priority in this group (from FITS candidates)
      let bestPriority = 'LOW';
      let bestScore = -1;

      fits.forEach((f) => {
        const cand = candidateMap.get(f.id);
        if (cand) {
          if (cand.priority_group === 'HIGH') {
            bestPriority = 'HIGH';
          } else if (cand.priority_group === 'MEDIUM' && bestPriority !== 'HIGH') {
            bestPriority = 'MEDIUM';
          }
          if (cand.acis_score > bestScore) {
            bestScore = cand.acis_score;
          }
        }
      });

      // Telescopes and instruments
      const telescopes = Array.from(new Set(fits.map((f) => f.telescope).filter(Boolean))) as string[];
      const instruments = Array.from(new Set(fits.map((f) => f.instrument).filter(Boolean))) as string[];
      if (fits.length === 0 && csv.length > 0) {
        telescopes.push('Tabular Ingestion');
        instruments.push('CSV Dataset');
      }

      // Primary dates
      const dates = fits.map((f) => f.observation_date).filter(Boolean) as string[];
      let primaryDate = dates.length > 0 ? dates[0] : fits[0]?.created_at?.slice(0, 10);
      if (!primaryDate && csv.length > 0) {
        primaryDate = csv[0].upload_date.slice(0, 10);
      }

      groups.push({
        group_name: groupName,
        files: fits,
        csv_files: csv,
        file_count: fits.length + csv.length,
        primary_date: primaryDate,
        telescopes,
        instruments,
        acis_priority: bestScore >= 0 ? bestPriority : undefined,
        acis_score: bestScore >= 0 ? bestScore : undefined,
      });
    });

    // Sort groups alphabetically by name
    return groups.sort((a, b) => a.group_name.localeCompare(b.group_name));
  }, [observations, csvFiles, candidateMap]);

  // ── Filtered Groups ───────────────────────────────────────
  const filteredGroups = useMemo(() => {
    return observationGroups.filter((grp) => {
      // Scope filter
      if (catalogScope === 'FITS' && grp.files.length === 0) return false;
      if (catalogScope === 'CSV' && (!grp.csv_files || grp.csv_files.length === 0)) return false;

      // Type filter
      if (typeFilter !== 'ALL') {
        if (grp.files.length === 0) return false;
        const hasMatchingType = grp.files.some((f) => {
          const isOptical = f.file_type.includes('OPTICAL') || f.file_type.includes('IMAGE');
          const isRadio = f.file_type.includes('RADIO') || f.file_type.includes('PSR');
          return typeFilter === 'OPTICAL' ? isOptical : isRadio;
        });
        if (!hasMatchingType) return false;
      }

      // Status filter
      if (statusFilter !== 'ALL') {
        const hasMatchingStatus = grp.files.some((f) => f.validation_status === statusFilter);
        const hasMatchingCsvStatus = grp.csv_files?.some((c) => c.status === statusFilter);
        if (!hasMatchingStatus && !hasMatchingCsvStatus) return false;
      }

      // Search term
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const groupMatch = grp.group_name.toLowerCase().includes(term);
        const telescopeMatch = grp.telescopes.some((t) => t.toLowerCase().includes(term));
        const instrumentMatch = grp.instruments.some((i) => i.toLowerCase().includes(term));
        const fileMatch = grp.files.some((f) => f.file_name.toLowerCase().includes(term));
        const csvMatch = grp.csv_files?.some((c) => c.file_name.toLowerCase().includes(term) || c.server_name.toLowerCase().includes(term));
        return groupMatch || telescopeMatch || instrumentMatch || fileMatch || Boolean(csvMatch);
      }

      return true;
    });
  }, [observationGroups, catalogScope, typeFilter, statusFilter, searchTerm]);

  // ── Filtered CSV Files ────────────────────────────────────
  const filteredCsvFiles = useMemo(() => {
    if (!searchTerm.trim()) return csvFiles;
    const term = searchTerm.toLowerCase();
    return csvFiles.filter((c) =>
      c.file_name.toLowerCase().includes(term) || c.server_name.toLowerCase().includes(term)
    );
  }, [csvFiles, searchTerm]);

  // ── Rename Handlers ───────────────────────────────────────
  const openRenameModal = (target: {
    type: 'GROUP' | 'FILE';
    id?: number;
    currentName: string;
    fileCount?: number;
  }) => {
    setRenameTarget(target);
    setNewDisplayName(target.currentName);
    setRenameError(null);
    setRenameModalOpen(true);
  };

  const handleExecuteRename = async () => {
    if (!renameTarget) return;
    const trimmed = newDisplayName.trim();
    if (!trimmed) {
      setRenameError('Observation name cannot be empty.');
      return;
    }

    setRenameLoading(true);
    setRenameError(null);
    try {
      if (renameTarget.type === 'FILE' && renameTarget.id) {
        await apiService.updateObservation(renameTarget.id, trimmed);
        setActionSuccess(`Observation file display name updated to "${trimmed}".`);
      } else if (renameTarget.type === 'GROUP') {
        const res = await apiService.renameObservationGroup(renameTarget.currentName, trimmed);
        setActionSuccess(`Observation group renamed: updated ${res.updated_count} file(s) to "${trimmed}".`);
      }
      setRenameModalOpen(false);
      await loadAll();
    } catch (err: any) {
      setRenameError(err?.message || 'Failed to rename observation.');
    } finally {
      setRenameLoading(false);
    }
  };

  // ── Delete Handlers ───────────────────────────────────────
  const openDeleteModal = (target: {
    type: 'GROUP' | 'FILE' | 'CSV';
    id?: number;
    name: string;
    serverName?: string;
    fileCount?: number;
    obsIds?: number[];
  }) => {
    setDeleteTarget(target);
    setDeleteError(null);
    setDeleteModalOpen(true);
  };

  const handleExecuteDelete = async () => {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    setDeleteError(null);

    try {
      if (deleteTarget.type === 'FILE' && deleteTarget.id) {
        await apiService.deleteObservation(deleteTarget.id);
        setActionSuccess(`Observation file "${deleteTarget.name}" deleted successfully.`);
      } else if (deleteTarget.type === 'GROUP' && deleteTarget.obsIds) {
        // Sequentially delete all files belonging to this group
        for (const obsId of deleteTarget.obsIds) {
          await apiService.deleteObservation(obsId);
        }
        setActionSuccess(`Observation group "${deleteTarget.name}" (${deleteTarget.obsIds.length} files) deleted successfully.`);
      } else if (deleteTarget.type === 'CSV' && deleteTarget.serverName) {
        await apiService.deleteCsvFile(deleteTarget.serverName);
        setActionSuccess(`CSV dataset "${deleteTarget.name}" deleted successfully.`);
      }
      setDeleteModalOpen(false);
      await loadAll();
    } catch (err: any) {
      setDeleteError(err?.message || 'Failed to complete deletion.');
    } finally {
      setDeleteLoading(false);
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

  const handleDownloadCsvPdf = async (e: React.MouseEvent, csv: CsvFileItem) => {
    e.stopPropagation();
    try {
      await apiService.downloadCsvReport(csv.server_name, csv.observation_name || csv.file_name);
    } catch (err: any) {
      alert(`Could not generate CSV PDF report: ${err?.message || 'Error'}`);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading cataloged astronomical observations and datasets..." />;
  }

  if (error) {
    return <ErrorMessage title="Catalog Loading Error" message={error} onRetry={loadAll} />;
  }

  // ── CSV File Explorer full-page view ──────────────────────
  if (selectedCsvServerName) {
    return (
      <div className="page-container">
        <CsvFileExplorer
          serverName={selectedCsvServerName}
          onBack={() => setSelectedCsvServerName(null)}
          onDeleteSuccess={() => {
            setSelectedCsvServerName(null);
            loadAll();
          }}
        />
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* ── Success Toast Banner ── */}
      {actionSuccess && (
        <div
          style={{
            padding: '10px 16px',
            backgroundColor: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: 'var(--radius-md)',
            color: '#6ee7b7',
            fontSize: '0.82rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '16px',
          }}
        >
          <span>✅ {actionSuccess}</span>
          <button
            style={{ background: 'none', border: 'none', color: '#6ee7b7', cursor: 'pointer', fontSize: '0.9rem' }}
            onClick={() => setActionSuccess(null)}
          >
            ✕
          </button>
        </div>
      )}

      <div className="card">
        {/* Header Bar */}
        <div className="card-header">
          <div>
            <h3 className="card-title">
              <span>Astronomical Observations &amp; Tabular Datasets</span>
              <span className="nav-badge">{observationGroups.length} Observations</span>
              <span className="nav-badge" style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)', color: 'var(--success)' }}>
                {observations.length} FITS Files
              </span>
              {csvFiles.length > 0 && (
                <span className="nav-badge" style={{ backgroundColor: 'rgba(14, 165, 233, 0.2)', color: 'var(--primary)' }}>
                  {csvFiles.length} CSVs
                </span>
              )}
            </h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Observations grouped by astronomical target. Click an observation to inspect all constituent files and telemetry.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-secondary btn-sm" onClick={expandAllGroups}>
              Expand All
            </button>
            <button className="btn btn-secondary btn-sm" onClick={collapseAllGroups}>
              Collapse All
            </button>
          </div>
        </div>

        {/* ── Scope Filter Tabs ── */}
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
            className={`btn btn-sm ${catalogScope === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setCatalogScope('ALL')}
          >
            All Datasets ({observations.length + csvFiles.length})
          </button>
          <button
            className={`btn btn-sm ${catalogScope === 'FITS' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setCatalogScope('FITS')}
          >
            🔭 FITS Observations ({observationGroups.length} groups · {observations.length} files)
          </button>
          <button
            className={`btn btn-sm ${catalogScope === 'CSV' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setCatalogScope('CSV')}
          >
            📊 CSV Tabular Data ({csvFiles.length})
          </button>
        </div>

        {/* Search & Filter Toolbar */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
            marginBottom: '16px',
          }}
        >
          {/* Search Box */}
          <div style={{ minWidth: '240px', flex: 1 }}>
            <input
              type="text"
              className="search-input"
              placeholder="Search by observation target, filename, telescope, instrument..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {/* FITS Type Filter */}
          {catalogScope !== 'CSV' && (
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                className={`btn btn-sm ${typeFilter === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setTypeFilter('ALL')}
              >
                All Types
              </button>
              <button
                className={`btn btn-sm ${typeFilter === 'RADIO' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setTypeFilter('RADIO')}
              >
                Radio PSRFITS
              </button>
              <button
                className={`btn btn-sm ${typeFilter === 'OPTICAL' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setTypeFilter('OPTICAL')}
              >
                Optical FITS
              </button>
            </div>
          )}

          {/* Status Filter */}
          {catalogScope !== 'CSV' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Status:</span>
              <select
                className="search-input"
                style={{ width: 'auto', padding: '6px 10px' }}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="ALL">All Statuses</option>
                <option value="VALID_PSRFITS">VALID_PSRFITS</option>
                <option value="VALID_IMAGE">VALID_IMAGE</option>
                <option value="UPLOADED">UPLOADED</option>
                <option value="PENDING">PENDING</option>
              </select>
            </div>
          )}
        </div>

        {/* ── FITS OBSERVATIONS GROUPED TABLE ── */}
        {(catalogScope === 'ALL' || catalogScope === 'FITS') && (
          <div style={{ marginBottom: catalogScope === 'ALL' ? '28px' : '0' }}>
            {catalogScope === 'ALL' && (
              <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                🔭 FITS Astronomical Observations (Grouped by Target)
              </h4>
            )}

            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: '38px' }}></th>
                    <th>Observation Name</th>
                    <th>Associated Files</th>
                    <th>Telescope / Instrument</th>
                    <th>Observation Date</th>
                    <th>Highest ACIS Triage</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredGroups.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: '32px' }}>
                        <div style={{ color: 'var(--text-muted)' }}>
                          No observation groups matching the selected criteria.
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredGroups.map((group) => {
                      const isExpanded = expandedGroups.has(group.group_name);
                      const fileCount = group.file_count;

                      return (
                        <React.Fragment key={group.group_name}>
                          {/* Group Header Row */}
                          <tr
                            style={{
                              backgroundColor: isExpanded
                                ? 'rgba(14, 165, 233, 0.08)'
                                : 'transparent',
                              cursor: 'pointer',
                              borderBottom: isExpanded ? 'none' : '1px solid var(--border-subtle)',
                              transition: 'background 0.15s ease',
                            }}
                            onClick={() => toggleGroup(group.group_name)}
                          >
                            <td style={{ textAlign: 'center', color: 'var(--primary)', fontSize: '0.9rem' }}>
                              {isExpanded ? '▼' : '▶'}
                            </td>
                            <td>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ fontSize: '1.05rem' }}>🌌</span>
                                <strong style={{ color: '#fff', fontSize: '0.9rem' }}>
                                  {group.group_name}
                                </strong>
                              </div>
                            </td>
                            <td>
                              <span
                                className="badge mono"
                                style={{
                                  backgroundColor: fileCount > 1 ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                                  color: fileCount > 1 ? '#a5b4fc' : 'var(--text-muted)',
                                  fontWeight: 700,
                                }}
                              >
                                {fileCount} {fileCount === 1 ? 'file' : 'files'}
                              </span>
                            </td>
                            <td style={{ fontSize: '0.78rem' }}>
                              {group.telescopes.join(', ') || 'N/A'}{' '}
                              {group.instruments.length > 0 ? `• ${group.instruments.join(', ')}` : ''}
                            </td>
                            <td className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                              {group.primary_date || 'N/A'}
                            </td>
                            <td>
                              {group.acis_priority ? (
                                <span
                                  className={`badge ${
                                    group.acis_priority === 'HIGH'
                                      ? 'badge-high'
                                      : group.acis_priority === 'MEDIUM'
                                      ? 'badge-medium'
                                      : 'badge-low'
                                  }`}
                                >
                                  {group.acis_priority} {group.acis_score != null && `(${group.acis_score.toFixed(3)})`}
                                </span>
                              ) : (
                                <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                                  Not evaluated
                                </span>
                              )}
                            </td>
                            <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                              <div style={{ display: 'inline-flex', gap: '6px' }}>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() =>
                                    openRenameModal({
                                      type: 'GROUP',
                                      currentName: group.group_name,
                                      fileCount: group.file_count,
                                    })
                                  }
                                  title="Rename this observation group name"
                                >
                                  ✏️ Rename
                                </button>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  style={{ color: 'var(--danger)' }}
                                  onClick={() =>
                                    openDeleteModal({
                                      type: 'GROUP',
                                      name: group.group_name,
                                      fileCount: group.file_count,
                                      obsIds: group.files.map((f) => f.id),
                                    })
                                  }
                                  title="Delete all files in this observation group"
                                >
                                  🗑️ Delete
                                </button>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => toggleGroup(group.group_name)}
                                >
                                  {isExpanded ? 'Hide Files' : 'Show Files'}
                                </button>
                              </div>
                            </td>
                          </tr>

                          {/* Expanded Files Sub-table */}
                          {isExpanded && (
                            <tr style={{ backgroundColor: 'rgba(15, 23, 42, 0.45)' }}>
                              <td colSpan={7} style={{ padding: '0 0 16px 38px' }}>
                                <div
                                  style={{
                                    borderLeft: '2px solid var(--primary)',
                                    borderRadius: '0 var(--radius-md) var(--radius-md) 0',
                                    backgroundColor: 'rgba(7, 10, 19, 0.65)',
                                    overflow: 'hidden',
                                    margin: '6px 12px 6px 0',
                                  }}
                                >
                                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                                    <thead>
                                      <tr style={{ backgroundColor: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border-subtle)' }}>
                                        <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)' }}>File ID</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)' }}>Filename</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)' }}>Data Mode</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)' }}>Size</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)' }}>Obs Date</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)' }}>Status</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)' }}>ACIS Priority</th>
                                        <th style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--text-muted)' }}>File Actions</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {group.files.map((file) => {
                                        const isOptical = file.file_type.includes('OPTICAL') || file.file_type.includes('IMAGE');
                                        const cand = candidateMap.get(file.id);

                                        return (
                                          <tr
                                            key={file.id}
                                            style={{
                                              borderBottom: '1px solid rgba(255,255,255,0.03)',
                                            }}
                                          >
                                            <td className="mono" style={{ padding: '7px 12px', color: 'var(--primary)', fontWeight: 600 }}>
                                              #{file.id}
                                            </td>
                                            <td className="mono" style={{ padding: '7px 12px', color: '#fff' }}>
                                              {file.file_name}
                                            </td>
                                            <td style={{ padding: '7px 12px' }}>
                                              <span className={`badge ${isOptical ? 'badge-optical' : 'badge-radio'}`} style={{ fontSize: '0.68rem' }}>
                                                {isOptical ? 'Optical' : 'Radio PSRFITS'}
                                              </span>
                                            </td>
                                            <td className="mono" style={{ padding: '7px 12px', color: 'var(--text-muted)' }}>
                                              {file.file_size_mb ? `${file.file_size_mb.toFixed(1)} MB` : 'N/A'}
                                            </td>
                                            <td className="mono" style={{ padding: '7px 12px', color: 'var(--text-dim)' }}>
                                              {file.observation_date || 'N/A'}
                                            </td>
                                            <td style={{ padding: '7px 12px' }}>
                                              <span className={`badge ${file.validation_status.includes('VALID') ? 'badge-completed' : 'badge-pending'}`} style={{ fontSize: '0.68rem' }}>
                                                {file.validation_status}
                                              </span>
                                            </td>
                                            <td style={{ padding: '7px 12px' }}>
                                              {cand ? (
                                                <span
                                                  className={`badge ${
                                                    cand.priority_group === 'HIGH'
                                                      ? 'badge-high'
                                                      : cand.priority_group === 'MEDIUM'
                                                      ? 'badge-medium'
                                                      : 'badge-low'
                                                  }`}
                                                  style={{ fontSize: '0.68rem' }}
                                                >
                                                  {cand.priority_group} ({cand.acis_score.toFixed(3)})
                                                </span>
                                              ) : (
                                                <span style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>—</span>
                                              )}
                                            </td>
                                            <td style={{ padding: '7px 12px', textAlign: 'right' }}>
                                              <div style={{ display: 'inline-flex', gap: '6px' }}>
                                                <button
                                                  className="btn btn-secondary btn-sm"
                                                  onClick={() => onSelectObservation(file.id)}
                                                >
                                                  Inspect
                                                </button>
                                                <button
                                                  className="btn btn-secondary btn-sm"
                                                  onClick={(e) => handleDownloadPdf(e, file.id)}
                                                  title="Download PDF Audit Report"
                                                >
                                                  PDF
                                                </button>
                                                <button
                                                  className="btn btn-secondary btn-sm"
                                                  onClick={() =>
                                                    openRenameModal({
                                                      type: 'FILE',
                                                      id: file.id,
                                                      currentName: file.target_name || file.file_name,
                                                    })
                                                  }
                                                  title="Rename this file's target name"
                                                >
                                                  ✏️
                                                </button>
                                                <button
                                                  className="btn btn-secondary btn-sm"
                                                  style={{ color: 'var(--danger)' }}
                                                  onClick={() =>
                                                    openDeleteModal({
                                                      type: 'FILE',
                                                      id: file.id,
                                                      name: file.file_name,
                                                    })
                                                  }
                                                  title="Delete this observation file"
                                                >
                                                  🗑️
                                                </button>
                                              </div>
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── CSV TABULAR DATASETS SECTION ── */}
        {(catalogScope === 'ALL' || catalogScope === 'CSV') && (
          <div>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--success)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>📊</span> CSV Tabular Data Files ({filteredCsvFiles.length})
            </h4>

            {filteredCsvFiles.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', backgroundColor: 'rgba(255,255,255,0.015)', borderRadius: 'var(--radius-md)' }}>
                No uploaded CSV files found. You can upload CSV data in the <strong>Add Data</strong> section.
              </div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>CSV File Name</th>
                      <th>Storage Server Path</th>
                      <th>File Size</th>
                      <th>Dimensions</th>
                      <th>Ingested Timestamp</th>
                      <th>Status</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCsvFiles.map((csv) => (
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
                          <div style={{ display: 'inline-flex', gap: '6px' }}>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => setSelectedCsvServerName(csv.server_name)}
                              title="Open CSV File Explorer — browse data, column structure and statistics"
                            >
                              🔍 Explore
                            </button>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={(e) => handleDownloadCsvPdf(e, csv)}
                              title="Generate and download PDF report for this CSV dataset"
                            >
                              📄 PDF
                            </button>
                            <button
                              className="btn btn-secondary btn-sm"
                              style={{ color: 'var(--danger)' }}
                              onClick={() =>
                                openDeleteModal({
                                  type: 'CSV',
                                  name: csv.file_name,
                                  serverName: csv.server_name,
                                })
                              }
                              title="Delete this uploaded CSV file"
                            >
                              🗑️
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── RENAME MODAL ── */}
      {renameModalOpen && renameTarget && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(4px)',
          }}
          onClick={() => setRenameModalOpen(false)}
        >
          <div
            className="card"
            style={{
              width: '460px',
              maxWidth: '90vw',
              padding: '24px',
              boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
              border: '1px solid var(--border-active)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h4 style={{ color: '#fff', fontSize: '1.05rem', fontWeight: 700 }}>
                ✏️ Rename {renameTarget.type === 'GROUP' ? 'Observation Group' : 'Observation Display Name'}
              </h4>
              <button
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.2rem' }}
                onClick={() => setRenameModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '16px', lineHeight: '1.4' }}>
              {renameTarget.type === 'GROUP'
                ? `This will update the observation target name for all ${renameTarget.fileCount} associated file(s). Original raw filenames remain unchanged.`
                : 'Update the user-friendly target display name for this individual file record.'}
            </p>

            {renameError && (
              <div
                style={{
                  padding: '8px 12px',
                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#fca5a5',
                  fontSize: '0.8rem',
                  marginBottom: '14px',
                }}
              >
                ⚠️ {renameError}
              </div>
            )}

            <div style={{ marginBottom: '20px' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', display: 'block', marginBottom: '6px' }}>
                New Observation Name
              </label>
              <input
                type="text"
                className="search-input"
                style={{ width: '100%', padding: '9px 12px', fontSize: '0.9rem' }}
                value={newDisplayName}
                onChange={(e) => setNewDisplayName(e.target.value)}
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleExecuteRename();
                  if (e.key === 'Escape') setRenameModalOpen(false);
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn btn-secondary btn-sm"
                disabled={renameLoading}
                onClick={() => setRenameModalOpen(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary btn-sm"
                disabled={renameLoading || !newDisplayName.trim()}
                onClick={handleExecuteRename}
              >
                {renameLoading ? 'Updating...' : 'Save Name'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── DELETE MODAL ── */}
      {deleteModalOpen && deleteTarget && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(4px)',
          }}
          onClick={() => setDeleteModalOpen(false)}
        >
          <div
            className="card"
            style={{
              width: '460px',
              maxWidth: '90vw',
              padding: '24px',
              boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <span style={{ fontSize: '1.4rem' }}>⚠️</span>
              <h4 style={{ color: '#fff', fontSize: '1.05rem', fontWeight: 700 }}>
                Confirm Deletion
              </h4>
            </div>

            <p style={{ fontSize: '0.82rem', color: '#fca5a5', marginBottom: '14px', lineHeight: '1.5' }}>
              {deleteTarget.type === 'GROUP' ? (
                <>
                  Are you sure you want to delete the entire observation group{' '}
                  <strong style={{ color: '#fff' }}>&quot;{deleteTarget.name}&quot;</strong>? This will permanently remove all{' '}
                  <strong style={{ color: '#fff' }}>{deleteTarget.fileCount}</strong> associated files, candidate scores, and telemetry runs.
                </>
              ) : deleteTarget.type === 'CSV' ? (
                <>
                  Are you sure you want to delete the uploaded CSV dataset{' '}
                  <strong style={{ color: '#fff' }}>&quot;{deleteTarget.name}&quot;</strong> from server storage?
                </>
              ) : (
                <>
                  Are you sure you want to delete the observation file{' '}
                  <strong style={{ color: '#fff' }}>&quot;{deleteTarget.name}&quot;</strong>? Associated features and candidate triage records will also be removed.
                </>
              )}
            </p>

            {deleteError && (
              <div
                style={{
                  padding: '8px 12px',
                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#fca5a5',
                  fontSize: '0.8rem',
                  marginBottom: '14px',
                }}
              >
                ⚠️ {deleteError}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
              <button
                className="btn btn-secondary btn-sm"
                disabled={deleteLoading}
                onClick={() => setDeleteModalOpen(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-sm"
                style={{
                  backgroundColor: 'var(--danger)',
                  color: '#fff',
                  border: 'none',
                  fontWeight: 600,
                }}
                disabled={deleteLoading}
                onClick={handleExecuteDelete}
              >
                {deleteLoading ? 'Deleting...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
