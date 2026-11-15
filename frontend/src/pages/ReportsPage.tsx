import React, { useEffect, useState } from 'react';
import { apiService, ApiError } from '../services/api';
import { Observation } from '../types/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ErrorMessage } from '../components/ErrorMessage';

interface ReportsPageProps {
  onSelectObservation: (id: number) => void;
}

export const ReportsPage: React.FC<ReportsPageProps> = ({
  onSelectObservation,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.getObservations(100, 0);
      setObservations(res.items);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load observation reports library.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDownload = async (obsId: number) => {
    setDownloadingId(obsId);
    try {
      await apiService.downloadObservationReport(obsId);
    } catch (err: any) {
      alert(`Report download failed: ${err?.message || 'Error generating PDF'}`);
    } finally {
      setDownloadingId(null);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading observation reports library..." />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Reports Library Error"
        message={error}
        onRetry={loadData}
      />
    );
  }

  return (
    <div className="page-container">
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">
              <span>Scientific Observation Reports</span>
              <span className="nav-badge">{observations.length} reports</span>
            </h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Download publication-grade scientific PDF audit reports compiled directly from verified observation metadata and analysis telemetry
            </p>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Observation Name</th>
                <th>Original Archive</th>
                <th>Observation Type</th>
                <th>Telescope / Instrument</th>
                <th>Report Specification</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {observations.map((obs) => {
                const isOptical =
                  obs.file_type.includes('OPTICAL') || obs.file_type.includes('IMAGE');
                const isDownloading = downloadingId === obs.id;

                return (
                  <tr key={obs.id}>
                    <td>
                      <strong style={{ color: '#fff' }}>
                        {obs.target_name || obs.file_name}
                      </strong>
                    </td>
                    <td className="mono" style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {obs.file_name}
                    </td>
                    <td>
                      <span className={`badge ${isOptical ? 'badge-optical' : 'badge-radio'}`}>
                        {isOptical ? 'Optical FITS Report' : 'Radio PSRFITS Report'}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>
                      {obs.telescope || 'N/A'} {obs.instrument ? `• ${obs.instrument}` : ''}
                    </td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                      {isOptical
                        ? 'Photometry & CCD HDU Audit (PDF)'
                        : 'Stokes I & ACIS Triage Audit (PDF)'}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '8px' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => onSelectObservation(obs.id)}
                        >
                          View Details
                        </button>
                        <button
                          className="btn btn-primary btn-sm"
                          disabled={isDownloading}
                          onClick={() => handleDownload(obs.id)}
                        >
                          {isDownloading ? 'Generating...' : '📄 Download PDF'}
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
    </div>
  );
};
