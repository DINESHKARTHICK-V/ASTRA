import React from 'react';
import { HealthResponse } from '../types/api';

interface NavbarProps {
  currentTab: 'dashboard' | 'candidates' | 'processing';
  onSelectTab: (tab: 'dashboard' | 'candidates' | 'processing') => void;
  health: HealthResponse | null;
  healthLoading: boolean;
  onRefreshHealth: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onSelectTab,
  health,
  healthLoading,
  onRefreshHealth,
}) => {
  const isHealthy = health?.status === 'healthy' && health?.database_connected;

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="brand" onClick={() => onSelectTab('dashboard')}>
          <div className="brand-icon">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#06b6d4"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M12 2v3m0 14v3M2 12h3m14 0h3m-3.5-6.5l-2.1 2.1m-8.8 8.8l-2.1 2.1m13-2.1l-2.1-2.1m-8.8-8.8l-2.1-2.1" />
            </svg>
          </div>
          <div className="brand-title">
            <span>ASTRA</span>
            <span style={{ color: 'var(--cyan)' }}>Cloud</span>
            <span className="brand-badge">v1.0</span>
          </div>
        </div>

        <nav className="nav-links">
          <button
            className={`nav-btn ${currentTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => onSelectTab('dashboard')}
          >
            <span>Overview</span>
          </button>
          <button
            className={`nav-btn ${currentTab === 'candidates' ? 'active' : ''}`}
            onClick={() => onSelectTab('candidates')}
          >
            <span>Candidate Prioritization (ACIS)</span>
          </button>
          <button
            className={`nav-btn ${currentTab === 'processing' ? 'active' : ''}`}
            onClick={() => onSelectTab('processing')}
          >
            <span>Pipeline Monitor</span>
          </button>
        </nav>

        <div className="header-status" title={health?.database_message || 'Connecting...'}>
          <span
            className={`status-dot ${isHealthy ? 'healthy' : 'degraded'}`}
            style={{ animation: healthLoading ? 'pulse 1s infinite' : 'none' }}
          ></span>
          <span>
            {healthLoading
              ? 'Checking...'
              : isHealthy
              ? 'PostgreSQL Connected'
              : 'DB Degraded'}
          </span>
          <button
            onClick={onRefreshHealth}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-dim)',
              cursor: 'pointer',
              marginLeft: '4px',
              fontSize: '0.85rem',
            }}
            title="Refresh database connectivity"
          >
            ↻
          </button>
        </div>
      </div>
    </header>
  );
};
