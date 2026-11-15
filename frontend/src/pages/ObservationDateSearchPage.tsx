import React, { useState, useEffect } from 'react';
import { apiService, ApiError } from '../services/api';
import {
  ObservationDateSearchResponse,
  ObservationDateFileItem,
  NavTab,
} from '../types/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';

interface ObservationDateSearchPageProps {
  onSelectObservation: (id: number) => void;
  onNavigateTab?: (tab: NavTab) => void;
}

export const ObservationDateSearchPage: React.FC<ObservationDateSearchPageProps> = ({
  onSelectObservation,
  onNavigateTab,
}) => {
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [searchExecuted, setSearchExecuted] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [initialLoading, setInitialLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Search response data
  const [searchResponse, setSearchResponse] = useState<ObservationDateSearchResponse | null>(null);
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [undatedFilesCount, setUndatedFilesCount] = useState<number>(0);

  // Expanded observation group cards
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  // Show undated files drawer/section
  const [showUndatedSection, setShowUndatedSection] = useState<boolean>(false);

  // Load available observation dates on mount
  useEffect(() => {
    const fetchCatalogDates = async () => {
      setInitialLoading(true);
      setError(null);
      try {
        const res = await apiService.searchObservationsByDate();
        setAvailableDates(res.available_observation_dates || []);
        setUndatedFilesCount(res.undated_files_count || 0);
      } catch (err: any) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError('Failed to fetch cataloged observation dates.');
        }
      } finally {
        setInitialLoading(false);
      }
    };
    fetchCatalogDates();
  }, []);

  const handleSearch = async (dateToSearch?: string) => {
    const targetDate = (dateToSearch !== undefined ? dateToSearch : selectedDate).trim();
    if (!targetDate) {
      alert('Please enter or select an observation date to search.');
      return;
    }

    setLoading(true);
    setError(null);
    setSearchExecuted(true);

    try {
      const res = await apiService.searchObservationsByDate(targetDate);
      setSearchResponse(res);
      setAvailableDates(res.available_observation_dates || []);
      setUndatedFilesCount(res.undated_files_count || 0);

      // Auto-expand all matching groups by default
      const allGroupNames = new Set((res.results || []).map((g) => g.observation_name));
      setExpandedGroups(allGroupNames);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to perform observation date search.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setSelectedDate('');
    setSearchExecuted(false);
    setSearchResponse(null);
    setError(null);
    setExpandedGroups(new Set());
  };

  const handleQuickDateSelect = (dateStr: string) => {
    setSelectedDate(dateStr);
    handleSearch(dateStr);
  };

  const toggleGroupExpand = (groupName: string) => {
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

  const handleExpandAll = () => {
    if (searchResponse?.results) {
      setExpandedGroups(new Set(searchResponse.results.map((g) => g.observation_name)));
    }
  };

  const handleCollapseAll = () => {
    setExpandedGroups(new Set());
  };

  const handleFileClick = (file: ObservationDateFileItem) => {
    if (file.observation_id != null) {
      onSelectObservation(file.observation_id);
    } else if (onNavigateTab) {
      onNavigateTab('add-data');
    }
  };

  if (initialLoading) {
    return <LoadingSpinner message="Querying uploaded observation records & verified dates..." />;
  }

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ── Search Controls Card ── */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>📅</span> Observation Date Search
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '4px', maxWidth: '750px', lineHeight: 1.5 }}>
              Search files already stored in ASTRA by their true recorded astronomical observation date.
              FITS observation dates are verified directly from file header metadata (<span className="mono" style={{ color: 'var(--primary)' }}>DATE-OBS</span>).
              Upload timestamps are never substituted for observation dates.
            </p>
          </div>

          <div
            style={{
              padding: '6px 12px',
              backgroundColor: 'rgba(56, 189, 248, 0.08)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.74rem',
              color: '#bae6fd',
              maxWidth: '300px',
            }}
          >
            🔒 <strong>Local Archive Search:</strong> Searches only files uploaded to ASTRA. Does not query external archives.
          </div>
        </div>

        {/* ── Search Bar: Date Picker, Search & Clear Buttons ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label htmlFor="obs-date-input" style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff' }}>
              Observation Date:
            </label>
            <input
              id="obs-date-input"
              type="date"
              className="search-input"
              style={{
                padding: '8px 14px',
                fontSize: '0.88rem',
                fontWeight: 600,
                color: '#fff',
                backgroundColor: 'var(--bg-input)',
                border: '1px solid var(--border-active)',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
                minWidth: '170px',
              }}
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSearch();
              }}
              placeholder="YYYY-MM-DD or select"
            />
          </div>

          <button
            className="btn btn-primary btn-sm"
            style={{ padding: '8px 18px', fontSize: '0.86rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            disabled={loading}
            onClick={() => handleSearch()}
          >
            {loading ? 'Searching...' : '🔍 Search'}
          </button>

          <button
            className="btn btn-secondary btn-sm"
            style={{ padding: '8px 14px', fontSize: '0.86rem' }}
            disabled={loading}
            onClick={handleClear}
          >
            ✕ Clear
          </button>

          {searchExecuted && searchResponse && (
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span
                style={{
                  fontSize: '0.84rem',
                  fontWeight: 700,
                  color: searchResponse.total_matching_observations > 0 ? 'var(--primary)' : 'var(--text-muted)',
                }}
              >
                Results: {searchResponse.total_matching_observations} observation{searchResponse.total_matching_observations === 1 ? '' : 's'} ({searchResponse.total_matching_files} file{searchResponse.total_matching_files === 1 ? '' : 's'})
              </span>
              {searchResponse.total_matching_observations > 0 && (
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button className="btn btn-secondary btn-sm" style={{ padding: '2px 8px', fontSize: '0.72rem' }} onClick={handleExpandAll}>
                    Expand All
                  </button>
                  <button className="btn btn-secondary btn-sm" style={{ padding: '2px 8px', fontSize: '0.72rem' }} onClick={handleCollapseAll}>
                    Collapse All
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Quick-Jump Verified Dates from Uploaded Data ── */}
        <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
            Recorded Observation Dates in Stored Data:
          </span>
          {availableDates.length === 0 ? (
            <span style={{ fontSize: '0.76rem', color: 'var(--text-dim)' }}>No verified observation dates currently cataloged.</span>
          ) : (
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {availableDates.map((d) => (
                <button
                  key={d}
                  onClick={() => handleQuickDateSelect(d)}
                  style={{
                    padding: '3px 10px',
                    fontSize: '0.76rem',
                    borderRadius: 'var(--radius-sm)',
                    border: d === selectedDate ? '1px solid var(--primary)' : '1px solid var(--border-subtle)',
                    backgroundColor: d === selectedDate ? 'rgba(14, 165, 233, 0.22)' : 'rgba(255, 255, 255, 0.03)',
                    color: d === selectedDate ? 'var(--primary)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: d === selectedDate ? 700 : 500,
                    transition: 'all 0.15s ease',
                  }}
                  title={`Search uploaded observations recorded on ${d}`}
                >
                  {d}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {error && <ErrorMessage title="Search Error" message={error} />}

      {/* ── Results Section ── */}
      {loading ? (
        <LoadingSpinner message="Searching verified observation records by date..." />
      ) : searchExecuted && searchResponse ? (
        searchResponse.total_matching_observations === 0 ? (
          /* Empty State as strictly required by prompt */
          <div className="card" style={{ textAlign: 'center', padding: '48px 20px' }}>
            <div style={{ fontSize: '2.8rem', marginBottom: '12px' }}>🔭</div>
            <h4 style={{ color: '#fff', fontSize: '1.15rem', fontWeight: 700, marginBottom: '8px' }}>
              No uploaded observations were found for this date.
            </h4>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.84rem', maxWidth: '540px', margin: '0 auto 16px', lineHeight: 1.5 }}>
              No cataloged files or astronomical records in ASTRA have a recorded observation date of{' '}
              <strong style={{ color: '#fff' }}>{searchResponse.search_date || selectedDate}</strong>.
            </p>
            <p style={{ fontSize: '0.76rem', color: 'var(--text-dim)', maxWidth: '500px', margin: '0 auto' }}>
              ASTRA never substitutes upload timestamps for scientific observation dates. You can try selecting one of the verified dates above.
            </p>
          </div>
        ) : (
          /* Matching Observations List */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#fff' }}>
                Matching Observations for Date:{' '}
                <span className="mono" style={{ color: 'var(--primary)', fontWeight: 800 }}>
                  {searchResponse.search_date}
                </span>
              </div>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                {searchResponse.total_matching_observations} observation{searchResponse.total_matching_observations === 1 ? '' : 's'} matching
              </span>
            </div>

            {searchResponse.results.map((group) => {
              const isExpanded = expandedGroups.has(group.observation_name);
              return (
                <div
                  key={group.observation_name}
                  className="card"
                  style={{
                    padding: '16px 20px',
                    border: '1px solid var(--border-active)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {/* Observation Group Header */}
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <button
                        onClick={() => toggleGroupExpand(group.observation_name)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--primary)',
                          cursor: 'pointer',
                          fontSize: '1rem',
                          padding: '2px 6px',
                        }}
                        title={isExpanded ? 'Collapse files' : 'Expand files'}
                      >
                        {isExpanded ? '▼' : '▶'}
                      </button>

                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                          <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff', margin: 0 }}>
                            {group.observation_name}
                          </h4>
                          <span className="badge badge-completed" style={{ fontSize: '0.72rem' }}>
                            {group.file_count} File{group.file_count === 1 ? '' : 's'}
                          </span>
                          {group.telescopes.length > 0 && (
                            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                              Telescope: <strong style={{ color: '#fff' }}>{group.telescopes.join(', ')}</strong>
                            </span>
                          )}
                          {group.instruments.length > 0 && (
                            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                              Instrument: <strong style={{ color: '#fff' }}>{group.instruments.join(', ')}</strong>
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                          Recorded Observation Date:{' '}
                          <span className="mono" style={{ color: 'var(--primary)', fontWeight: 600 }}>
                            {group.recorded_observation_date}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {/* Primary action to open first observation */}
                      {group.files[0]?.observation_id != null && (
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => onSelectObservation(group.files[0].observation_id!)}
                          title="Open observation details page"
                        >
                          Inspect Observation →
                        </button>
                      )}
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => toggleGroupExpand(group.observation_name)}
                      >
                        {isExpanded ? 'Hide Files ▲' : 'View Matching Files ▼'}
                      </button>
                    </div>
                  </div>

                  {/* Expandable Files Table */}
                  {isExpanded && (
                    <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
                      <div className="table-container">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Original Filename</th>
                              <th>Format</th>
                              <th>Recorded Obs Date</th>
                              <th>Telescope / Instrument</th>
                              <th>Date Verification Source</th>
                              <th>Size</th>
                              <th style={{ textAlign: 'right' }}>Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            {group.files.map((file, idx) => {
                              const isFITS = file.file_type.includes('FITS');
                              return (
                                <tr key={`${file.file_name}-${idx}`}>
                                  <td>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                      <span>{isFITS ? '🌌' : '📊'}</span>
                                      <span
                                        className="mono"
                                        style={{
                                          fontWeight: 600,
                                          color: '#fff',
                                          cursor: file.observation_id != null ? 'pointer' : 'default',
                                        }}
                                        onClick={() => handleFileClick(file)}
                                        title={file.observation_id != null ? 'Click to open details' : undefined}
                                      >
                                        {file.file_name}
                                      </span>
                                    </div>
                                  </td>
                                  <td>
                                    <span
                                      className={`badge ${
                                        file.file_type.includes('OPTICAL')
                                          ? 'badge-optical'
                                          : file.file_type.includes('RADIO')
                                          ? 'badge-radio'
                                          : 'badge-completed'
                                      }`}
                                      style={{ fontSize: '0.7rem' }}
                                    >
                                      {file.file_type}
                                    </span>
                                  </td>
                                  <td>
                                    <span className="mono" style={{ fontSize: '0.78rem', color: 'var(--primary)', fontWeight: 600 }}>
                                      {file.recorded_observation_date || 'Observation date unavailable'}
                                      {file.recorded_observation_time ? ` ${file.recorded_observation_time}` : ''}
                                    </span>
                                  </td>
                                  <td style={{ fontSize: '0.78rem' }}>
                                    {file.telescope || 'N/A'}{file.instrument ? ` • ${file.instrument}` : ''}
                                  </td>
                                  <td>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                      <span
                                        style={{
                                          fontSize: '0.74rem',
                                          padding: '2px 6px',
                                          borderRadius: '4px',
                                          backgroundColor: file.is_date_verified
                                            ? 'rgba(16, 185, 129, 0.12)'
                                            : 'rgba(239, 68, 68, 0.12)',
                                          color: file.is_date_verified ? '#6ee7b7' : '#fca5a5',
                                          border: `1px solid ${
                                            file.is_date_verified
                                              ? 'rgba(16, 185, 129, 0.3)'
                                              : 'rgba(239, 68, 68, 0.3)'
                                          }`,
                                          fontWeight: 600,
                                        }}
                                      >
                                        {file.is_date_verified ? '✓ Verified' : '⚠️ Unverified'}
                                      </span>
                                      <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                                        {file.date_source}
                                      </span>
                                    </div>
                                  </td>
                                  <td className="mono" style={{ fontSize: '0.76rem' }}>
                                    {file.file_size_mb != null ? `${file.file_size_mb} MB` : '—'}
                                  </td>
                                  <td style={{ textAlign: 'right' }}>
                                    <button
                                      className="btn btn-secondary btn-sm"
                                      onClick={() => handleFileClick(file)}
                                    >
                                      {file.observation_id != null ? 'Open Details →' : 'View in Add Data →'}
                                    </button>
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
              );
            })}
          </div>
        )
      ) : (
        /* Initial Landing Guidance when search has not yet run */
        <div className="card" style={{ padding: '30px 20px', textAlign: 'center' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '10px' }}>🗓️</div>
          <h4 style={{ color: '#fff', fontSize: '1.05rem', fontWeight: 700, marginBottom: '6px' }}>
            Ready to Search Recorded Observation Dates
          </h4>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.84rem', maxWidth: '560px', margin: '0 auto 16px', lineHeight: 1.5 }}>
            Pick a date using the date picker or click any of the available observation dates above to inspect matching observations and files stored in ASTRA.
          </p>
          <div style={{ display: 'inline-flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
            {availableDates.slice(0, 5).map((d) => (
              <button
                key={d}
                className="btn btn-secondary btn-sm"
                onClick={() => handleQuickDateSelect(d)}
              >
                📅 Try {d}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Separate Filter / Note for Undated Files (Requirement 3) ── */}
      <div
        className="card"
        style={{
          padding: '14px 18px',
          backgroundColor: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.84rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>ℹ️</span> Undated Files Notice:
              <span className="badge" style={{ backgroundColor: 'rgba(255, 255, 255, 0.06)', color: 'var(--text-dim)', fontSize: '0.72rem' }}>
                {undatedFilesCount} file{undatedFilesCount === 1 ? '' : 's'} without reliable observation date
              </span>
            </div>
            <p style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginTop: '3px' }}>
              Files that do not possess verified observation metadata (such as standalone CSVs without an associated astronomical observation record) are clearly labeled{' '}
              <strong style={{ color: 'var(--text-muted)' }}>"Observation date unavailable"</strong> and are not assigned invented dates.
            </p>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            style={{ fontSize: '0.74rem' }}
            onClick={() => setShowUndatedSection(!showUndatedSection)}
          >
            {showUndatedSection ? 'Hide Explanation ▲' : 'Learn More ▼'}
          </button>
        </div>

        {showUndatedSection && (
          <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            • <strong>Scientific Rigor:</strong> In ASTRA, an observation date signifies the exact historical moment the telescope collected photons or measurements.
            <br />
            • <strong>Upload Timestamp Distinction:</strong> The file upload date or server ingestion timestamp is intentionally NEVER used as an observation date.
            <br />
            • <strong>Accessing Undated Files:</strong> You can view and manage all files regardless of date under the <button style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', padding: 0, textDecoration: 'underline' }} onClick={() => onNavigateTab && onNavigateTab('observations')}>Observations catalog</button> or <button style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', padding: 0, textDecoration: 'underline' }} onClick={() => onNavigateTab && onNavigateTab('add-data')}>Add Data page</button>.
          </div>
        )}
      </div>
    </div>
  );
};
