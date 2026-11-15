import React from 'react';
import { HealthResponse, NavTab } from '../types/api';

interface HeaderProps {
  currentTab: NavTab;
  health: HealthResponse | null;
  healthLoading: boolean;
  onRefreshHealth: () => void;
  onNavigateTab: (tab: NavTab) => void;
  selectedObservationName?: string;
}

const TAB_TITLES: Record<NavTab, { title: string; subtitle: string }> = {
  overview: {
    title: 'ASTRA — Pulsar Research & Analysis',
    subtitle: 'MSc Computer Science Research Platform • Multi-Dataset Radio Astronomy & ML Evaluation',
  },
  'integrated-datasets': {
    title: 'Integrated Astronomical Datasets',
    subtitle: 'HTRU2 candidate benchmark and Parkes search-mode PSRFITS stream specifications',
  },
  'dataset-experiments': {
    title: 'Five Research Problems (P1–P5) Evaluation Suite',
    subtitle: 'Empirical perturbation, masking, calibration, and failure telemetry across HTRU2 and Parkes',
  },
  'ml-workflow': {
    title: 'ML Workflow & Radio Signal Pipeline',
    subtitle: 'Visual 7-stage processing architecture with decoupled HTRU2 and Parkes paths',
  },
  'knowledge-graph': {
    title: 'Neo4j Astronomy Research Knowledge Graph',
    subtitle: 'Graph database topology connecting datasets, pulsars, telescope observations, and ML models',
  },
  'mlflow-tracking': {
    title: 'MLflow Experiment Tracking & Governance',
    subtitle: 'Parameter, metric, and artifact tracking across model benchmarks and the five research problems',
  },
  'research-sources': {
    title: 'Research Sources & Literature Collector',
    subtitle: 'Astronomy paper discovery, grounded fact extraction, and literature comparison',
  },
  reports: {
    title: 'Observation & Research Reports',
    subtitle: 'Publication-grade scientific PDF reports and provenance audit trails',
  },
  'system-status': {
    title: 'System Status & Infrastructure',
    subtitle: 'PostgreSQL database connectivity, API health, and system telemetry',
  },
  'add-data': {
    title: 'Add Astronomical Data',
    subtitle: 'Multi-type FITS upload and scientific workflow selection',
  },
  observations: {
    title: 'Observational Catalog',
    subtitle: 'Catalog of radio PSRFITS and optical astronomical observations',
  },
  'observation-date-search': {
    title: 'Observation Date Search',
    subtitle: 'Search uploaded observations and files by verified recorded observation date',
  },
  history: {
    title: 'Observation & Processing History',
    subtitle: 'Audit trail and historical records filtered by calendar date',
  },
  'high-priority': {
    title: 'High Priority Candidates',
    subtitle: 'ACIS triage score ≥ 0.70 recommended for priority investigation',
  },
  'medium-priority': {
    title: 'Medium Priority Candidates',
    subtitle: 'ACIS triage score 0.45 – 0.69 requiring secondary review',
  },
  'low-priority': {
    title: 'Low Priority Candidates',
    subtitle: 'ACIS triage score < 0.45 or unranked observations',
  },
};

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  health,
  healthLoading,
  onRefreshHealth,
  onNavigateTab,
  selectedObservationName,
}) => {
  const isHealthy = health?.status === 'healthy' && health?.database_connected;
  const currentMeta = TAB_TITLES[currentTab] || {
    title: 'ASTRA',
    subtitle: 'Astronomy Data Explorer',
  };

  return (
    <header className="top-header">
      <div className="header-left">
        <h2 className="page-title">
          {selectedObservationName ? `Observation: ${selectedObservationName}` : currentMeta.title}
        </h2>
        <span className="page-subtitle">
          {selectedObservationName ? 'Detailed inspection' : currentMeta.subtitle}
        </span>
      </div>

      <div className="header-right">
        {/* Real Backend DB Status Pill */}
        <div
          className="db-pill"
          title={health?.database_message || 'Connecting to backend...'}
        >
          <span
            className={`pulse-dot ${
              healthLoading ? 'checking' : isHealthy ? 'healthy' : 'degraded'
            }`}
          />
          <span>
            {healthLoading
              ? 'Checking DB...'
              : isHealthy
              ? 'PostgreSQL Connected'
              : 'DB Degraded'}
          </span>
          <button
            onClick={onRefreshHealth}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              marginLeft: '4px',
              fontSize: '0.85rem',
              lineHeight: 1,
            }}
            title="Refresh database connectivity check"
          >
            ↻
          </button>
        </div>

        {currentTab !== 'add-data' && !selectedObservationName && (
          <button
            className="btn btn-primary btn-sm"
            onClick={() => onNavigateTab('add-data')}
          >
            + Add Data
          </button>
        )}
      </div>
    </header>
  );
};
