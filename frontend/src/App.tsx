import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { OverviewPage } from './pages/OverviewPage';
import { AddDataPage } from './pages/AddDataPage';
import { ObservationsPage } from './pages/ObservationsPage';
import { HistoryPage } from './pages/HistoryPage';
import { ObservationDateSearchPage } from './pages/ObservationDateSearchPage';
import { PriorityPage } from './pages/PriorityPage';
import { ReportsPage } from './pages/ReportsPage';
import { SystemStatusPage } from './pages/SystemStatusPage';
import { ObservationDetailPage } from './pages/ObservationDetailPage';
import { ResearchSourcesPage } from './pages/ResearchSourcesPage';
import { DatasetExperimentsPage } from './pages/DatasetExperimentsPage';
import { IntegratedDatasetsPage } from './pages/IntegratedDatasetsPage';
import { MLWorkflowPage } from './pages/MLWorkflowPage';
import { KnowledgeGraphPage } from './pages/KnowledgeGraphPage';
import { MLflowTrackingPage } from './pages/MLflowTrackingPage';
import { apiService } from './services/api';
import { HealthResponse, NavTab } from './types/api';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>('overview');
  const [selectedObservationId, setSelectedObservationId] = useState<number | null>(null);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  // Dynamic counts for sidebar badges
  const [counts, setCounts] = useState<{
    totalObservations?: number;
    highPriority?: number;
    mediumPriority?: number;
    lowPriority?: number;
  }>({});

  const checkHealth = async () => {
    setHealthLoading(true);
    try {
      const data = await apiService.getHealth();
      setHealth(data);
    } catch {
      setHealth({
        status: 'degraded',
        database_connected: false,
        database_message: 'Cannot connect to ASTRA FastAPI backend.',
        timestamp: new Date().toISOString(),
      });
    } finally {
      setHealthLoading(false);
    }
  };

  const loadSidebarCounts = async () => {
    try {
      const [obsRes, candRes] = await Promise.all([
        apiService.getObservations(1, 0),
        apiService.getCandidates(100, 0),
      ]);

      const high = candRes.items.filter((c) => c.priority_group === 'HIGH').length;
      const medium = candRes.items.filter((c) => c.priority_group === 'MEDIUM').length;
      const low = candRes.items.filter((c) => c.priority_group === 'LOW').length;

      setCounts({
        totalObservations: obsRes.total,
        highPriority: high,
        mediumPriority: medium,
        lowPriority: low,
      });
    } catch {
      // Keep existing
    }
  };

  useEffect(() => {
    checkHealth();
    loadSidebarCounts();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectObservation = (id: number) => {
    setSelectedObservationId(id);
  };

  const handleBackToCatalog = () => {
    setSelectedObservationId(null);
    loadSidebarCounts();
  };

  const handleSelectTab = (tab: NavTab) => {
    setSelectedObservationId(null);
    setCurrentTab(tab);
    loadSidebarCounts();
  };

  return (
    <div className="app-layout">
      {/* Required Left Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={handleSelectTab}
        counts={counts}
      />

      {/* Main Content Area */}
      <div className="main-wrapper">
        <Header
          currentTab={currentTab}
          health={health}
          healthLoading={healthLoading}
          onRefreshHealth={checkHealth}
          onNavigateTab={handleSelectTab}
          selectedObservationName={
            selectedObservationId !== null ? `Observation #${selectedObservationId}` : undefined
          }
        />

        <main className="main-content">
          {selectedObservationId !== null ? (
            <ObservationDetailPage
              observationId={selectedObservationId}
              onBack={handleBackToCatalog}
            />
          ) : (
            <>
              {currentTab === 'overview' && (
                <OverviewPage
                  onSelectObservation={handleSelectObservation}
                  onNavigateTab={handleSelectTab}
                />
              )}
              {currentTab === 'integrated-datasets' && (
                <IntegratedDatasetsPage />
              )}
              {currentTab === 'dataset-experiments' && (
                <DatasetExperimentsPage />
              )}
              {currentTab === 'ml-workflow' && (
                <MLWorkflowPage />
              )}
              {currentTab === 'knowledge-graph' && (
                <KnowledgeGraphPage />
              )}
              {currentTab === 'mlflow-tracking' && (
                <MLflowTrackingPage />
              )}
              {currentTab === 'research-sources' && (
                <ResearchSourcesPage />
              )}
              {currentTab === 'reports' && (
                <ReportsPage onSelectObservation={handleSelectObservation} />
              )}
              {currentTab === 'system-status' && (
                <SystemStatusPage
                  health={health}
                  healthLoading={healthLoading}
                  onRefreshHealth={checkHealth}
                />
              )}
              {currentTab === 'add-data' && (
                <AddDataPage onSelectObservation={handleSelectObservation} />
              )}
              {currentTab === 'observations' && (
                <ObservationsPage onSelectObservation={handleSelectObservation} />
              )}
              {currentTab === 'observation-date-search' && (
                <ObservationDateSearchPage
                  onSelectObservation={handleSelectObservation}
                  onNavigateTab={handleSelectTab}
                />
              )}
              {currentTab === 'history' && (
                <HistoryPage
                  onSelectObservation={handleSelectObservation}
                  onNavigateTab={handleSelectTab}
                />
              )}
              {currentTab === 'high-priority' && (
                <PriorityPage
                  priorityGroup="HIGH"
                  onSelectObservation={handleSelectObservation}
                />
              )}
              {currentTab === 'medium-priority' && (
                <PriorityPage
                  priorityGroup="MEDIUM"
                  onSelectObservation={handleSelectObservation}
                />
              )}
              {currentTab === 'low-priority' && (
                <PriorityPage
                  priorityGroup="LOW"
                  onSelectObservation={handleSelectObservation}
                />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
