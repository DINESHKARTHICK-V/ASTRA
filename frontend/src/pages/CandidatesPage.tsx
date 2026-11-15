import React, { useEffect, useState, useMemo } from 'react';
import { apiService, ApiError } from '../services/api';
import { CandidateScore } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';

interface CandidatesPageProps {
  onSelectObservation: (id: number) => void;
}

export const CandidatesPage: React.FC<CandidatesPageProps> = ({ onSelectObservation }) => {
  const [candidates, setCandidates] = useState<CandidateScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [sortField, setSortField] = useState<'rank' | 'score' | 'name'>('rank');
  const [sortAsc, setSortAsc] = useState(true);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const loadCandidates = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getCandidates(50, 0);
      setCandidates(data.items);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to retrieve candidate rankings.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCandidates();
  }, []);

  // Filter & Sort Pipeline
  const filteredAndSorted = useMemo(() => {
    return candidates
      .filter((c) => {
        const matchesSearch =
          (c.file_name?.toLowerCase().includes(searchTerm.toLowerCase()) || false) ||
          (c.target_name?.toLowerCase().includes(searchTerm.toLowerCase()) || false);
        const matchesPriority =
          priorityFilter === 'ALL' || c.priority_group === priorityFilter;
        return matchesSearch && matchesPriority;
      })
      .sort((a, b) => {
        let cmp = 0;
        if (sortField === 'rank') {
          cmp = (a.rank_position || 999) - (b.rank_position || 999);
        } else if (sortField === 'score') {
          cmp = a.acis_score - b.acis_score;
        } else if (sortField === 'name') {
          cmp = (a.file_name || '').localeCompare(b.file_name || '');
        }
        return sortAsc ? cmp : -cmp;
      });
  }, [candidates, searchTerm, priorityFilter, sortField, sortAsc]);

  const totalPages = Math.ceil(filteredAndSorted.length / pageSize) || 1;
  const paginatedItems = filteredAndSorted.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const handleSort = (field: 'rank' | 'score' | 'name') => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Querying ACIS candidate intelligence ranking..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Candidate Triage Retrieval Error"
        message={error}
        onRetry={loadCandidates}
      />
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Title & Methodology Notice */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>
            Pulsar Candidate Prioritization (ACIS)
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>
            Multi-evidence intelligence scores evaluated across 6 scientific channels (Signal Quality, RFI, DM, Profile, Ephemeris).
          </p>
        </div>

        <button onClick={loadCandidates} className="btn" style={{ fontSize: '0.82rem' }}>
          ↻ Refresh Candidates
        </button>
      </div>

      {/* Domain Shift Explanation Banner */}
      <div className="alert-box alert-warning">
        <span>⚠</span>
        <div style={{ fontSize: '0.82rem' }}>
          <strong>Scientific Methodology Notice:</strong> All GBT archives are folded timing archives of PSR J1713+0747. 
          The HTRU2 ML classifier was safely halted to avoid invalid inference on missing DM-SNR curve features. 
          Prioritization relies on 5 active physical observational channels.
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div
        className="card"
        style={{
          padding: '16px 20px',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '14px',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', gap: '12px', flex: 1, minWidth: '280px' }}>
          <input
            type="text"
            className="input-field"
            placeholder="Search by filename or target..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            style={{ width: '100%', maxWidth: '360px' }}
          />

          <select
            className="input-field"
            value={priorityFilter}
            onChange={(e) => {
              setPriorityFilter(e.target.value);
              setCurrentPage(1);
            }}
          >
            <option value="ALL">All Priorities</option>
            <option value="HIGH">High Priority (≥ 0.65)</option>
            <option value="MEDIUM">Medium Priority (0.40–0.65)</option>
            <option value="LOW">Low Priority (&lt; 0.40)</option>
          </select>
        </div>

        <div style={{ fontSize: '0.82rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          Showing {filteredAndSorted.length} of {candidates.length} candidates
        </div>
      </div>

      {/* Candidate Data Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th
                onClick={() => handleSort('rank')}
                style={{ cursor: 'pointer', userSelect: 'none' }}
              >
                Rank {sortField === 'rank' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th
                onClick={() => handleSort('name')}
                style={{ cursor: 'pointer', userSelect: 'none' }}
              >
                Observation File {sortField === 'name' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th>Target</th>
              <th
                onClick={() => handleSort('score')}
                style={{ cursor: 'pointer', userSelect: 'none' }}
              >
                ACIS Score {sortField === 'score' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th>Priority Group</th>
              <th>Active Channels</th>
              <th>ML Inference</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {paginatedItems.length === 0 ? (
              <tr>
                <td colSpan={8} className="empty-state">
                  No candidates match the selected search criteria.
                </td>
              </tr>
            ) : (
              paginatedItems.map((cand) => (
                <tr key={cand.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--cyan)' }}>
                    #{cand.rank_position}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                    {cand.file_name}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    {cand.target_name || 'J1713+0747'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.95rem' }}>
                    {cand.acis_score.toFixed(4)}
                  </td>
                  <td>
                    <StatusBadge type="priority" value={cand.priority_group} />
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    {cand.evidence_available}
                  </td>
                  <td>
                    <StatusBadge type="inference" value="INFERENCE_HALTED" />
                  </td>
                  <td>
                    <button
                      onClick={() => onSelectObservation(cand.observation_id)}
                      className="btn btn-primary"
                      style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                    >
                      Inspect Data
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div className="pagination">
            <span>
              Page {currentPage} of {totalPages}
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className="btn"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                style={{ fontSize: '0.78rem', padding: '4px 10px' }}
              >
                ← Previous
              </button>
              <button
                className="btn"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                style={{ fontSize: '0.78rem', padding: '4px 10px' }}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
