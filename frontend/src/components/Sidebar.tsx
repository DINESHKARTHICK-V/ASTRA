import React from 'react';
import { NavTab } from '../types/api';

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  counts?: {
    totalObservations?: number;
    highPriority?: number;
    mediumPriority?: number;
    lowPriority?: number;
  };
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
}) => {
  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand" onClick={() => onSelectTab('overview')}>
        <div className="sidebar-logo">A</div>
        <div className="sidebar-title">
          <h1>ASTRA</h1>
          <p>Pulsar Research & Analysis</p>
        </div>
      </div>

      {/* Primary Research Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section-title">Research Overview</div>
        <button
          className={`nav-item ${currentTab === 'overview' ? 'active' : ''}`}
          onClick={() => onSelectTab('overview')}
        >
          <div className="nav-item-left">
            <span className="nav-icon">📊</span>
            <span>Overview</span>
          </div>
        </button>

        <div className="nav-section-title">Datasets & Experiments</div>
        <button
          className={`nav-item ${currentTab === 'integrated-datasets' ? 'active' : ''}`}
          onClick={() => onSelectTab('integrated-datasets')}
        >
          <div className="nav-item-left">
            <span className="nav-icon">🗄️</span>
            <span>Integrated Datasets</span>
          </div>
        </button>

        <button
          className={`nav-item ${currentTab === 'dataset-experiments' ? 'active' : ''}`}
          onClick={() => onSelectTab('dataset-experiments')}
        >
          <div className="nav-item-left">
            <span className="nav-icon">🧪</span>
            <span>Research Experiments</span>
          </div>
        </button>

        <div className="nav-section-title">Pipelines & Literature</div>
        <button
          className={`nav-item ${currentTab === 'ml-workflow' ? 'active' : ''}`}
          onClick={() => onSelectTab('ml-workflow')}
        >
          <div className="nav-item-left">
            <span className="nav-icon">⚡</span>
            <span>ML Workflow</span>
          </div>
        </button>

        <button
          className={`nav-item ${currentTab === 'knowledge-graph' ? 'active' : ''}`}
          onClick={() => onSelectTab('knowledge-graph')}
        >
          <div className="nav-item-left">
            <span className="nav-icon">🌌</span>
            <span>Knowledge Graph</span>
          </div>
        </button>

        <button
          className={`nav-item ${currentTab === 'mlflow-tracking' ? 'active' : ''}`}
          onClick={() => onSelectTab('mlflow-tracking')}
        >
          <div className="nav-item-left">
            <span className="nav-icon">🧪</span>
            <span>MLflow Tracking</span>
          </div>
        </button>

        <button
          className={`nav-item ${currentTab === 'research-sources' ? 'active' : ''}`}
          onClick={() => onSelectTab('research-sources')}
        >
          <div className="nav-item-left">
            <span className="nav-icon">🔬</span>
            <span>Research Sources</span>
          </div>
        </button>

        <div className="nav-section-title">Dissemination & Health</div>
        <button
          className={`nav-item ${currentTab === 'reports' ? 'active' : ''}`}
          onClick={() => onSelectTab('reports')}
        >
          <div className="nav-item-left">
            <span className="nav-icon">📄</span>
            <span>Reports</span>
          </div>
        </button>

        <button
          className={`nav-item ${currentTab === 'system-status' ? 'active' : ''}`}
          onClick={() => onSelectTab('system-status')}
        >
          <div className="nav-item-left">
            <span className="nav-icon">⚙️</span>
            <span>System Status</span>
          </div>
        </button>
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span style={{ fontWeight: 600, color: '#334155' }}>ASTRA</span>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>MSc CS Research Suite</span>
        </div>
        <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--primary)' }}>v1.0</span>
      </div>
    </aside>
  );
};
