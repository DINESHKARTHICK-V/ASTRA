import React, { useEffect, useState } from 'react';
import { apiService, ApiError } from '../services/api';
import { CandidateScore } from '../types/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';

interface PriorityPageProps {
  priorityGroup: 'HIGH' | 'MEDIUM' | 'LOW';
  onSelectObservation: (id: number) => void;
}

const PRIORITY_META = {
  HIGH: {
    title: 'High Priority Triage Candidates',
    scoreRange: 'ACIS ≥ 0.7000',
    description:
      'Observations exhibiting strongest multi-channel consistency across signal SNR, profile morphology, dispersion, and periodicity.',
    badgeClass: 'badge-high',
  },
  MEDIUM: {
    title: 'Medium Priority Triage Candidates',
    scoreRange: '0.4500 ≤ ACIS < 0.7000',
    description:
      'Observations with intermediate evidence or partial channel agreement requiring secondary review.',
    badgeClass: 'badge-medium',
  },
  LOW: {
    title: 'Low Priority Triage Candidates',
    scoreRange: 'ACIS < 0.4500',
    description:
      'Observations with weak evidence or high RFI contamination, scheduled for low-priority manual inspection.',
    badgeClass: 'badge-low',
  },
};

export const PriorityPage: React.FC<PriorityPageProps> = ({
  priorityGroup,
  onSelectObservation,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<CandidateScore[]>([]);

  const meta = PRIORITY_META[priorityGroup];

  const loadCandidates = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.getCandidates(100, 0, priorityGroup);
      setCandidates(res.items);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(`Failed to retrieve ${priorityGroup} priority candidates.`);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCandidates();
  }, [priorityGroup]);

  if (loading) {
    return <LoadingSpinner message={`Loading ${priorityGroup} priority candidates...`} />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Triage Data Error"
        message={error}
        onRetry={loadCandidates}
      />
    );
  }

  return (
    <div className="page-container">
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">
              <span>{meta.title}</span>
              <span className={`badge ${meta.badgeClass}`}>{meta.scoreRange}</span>
              <span className="nav-badge">{candidates.length} candidates</span>
            </h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              {meta.description}
            </p>
          </div>
        </div>

        {candidates.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">⚖️</div>
            <h4 className="empty-title">No Candidates in {priorityGroup} Priority Group</h4>
            <p className="empty-desc">
              Currently, zero cataloged observations satisfy the {meta.scoreRange} threshold.
              In the baseline GBT/VEGAS timing archive dataset, all 12 verified radio archives exhibit strong profile evidence and rank in the HIGH priority category.
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Observation / Target</th>
                  <th>Original Archive</th>
                  <th>ACIS Score</th>
                  <th>Available Evidence</th>
                  <th>Channel Breakdown (SNR / RFI / Profile)</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((cand) => (
                  <tr key={cand.id}>
                    <td>
                      <span className="mono" style={{ fontWeight: 700, color: '#fff' }}>
                        #{cand.rank_position || '-'}
                      </span>
                    </td>
                    <td>
                      <strong style={{ color: '#fff' }}>
                        {cand.target_name || `Observation #${cand.observation_id}`}
                      </strong>
                    </td>
                    <td className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {cand.file_name || 'N/A'}
                    </td>
                    <td>
                      <span className="mono" style={{ fontWeight: 700, color: 'var(--primary)', fontSize: '0.92rem' }}>
                        {cand.acis_score.toFixed(4)}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                      {cand.evidence_available} channels
                    </td>
                    <td style={{ fontSize: '0.75rem' }}>
                      <span title="Signal Quality">SNR: {cand.signal_quality?.toFixed(2) ?? 'N/A'}</span>
                      {' • '}
                      <span title="RFI Cleanliness">RFI: {cand.rfi_indicator?.toFixed(2) ?? 'N/A'}</span>
                      {' • '}
                      <span title="Profile Evidence">Prof: {cand.profile_evidence?.toFixed(2) ?? 'N/A'}</span>
                    </td>
                    <td>
                      <span className="badge badge-completed">{cand.score_status}</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => onSelectObservation(cand.observation_id)}
                      >
                        Inspect Details →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
