// ============================================================
//  ASTRA — Centralized REST API Client
//  File   : frontend/src/services/api.ts
//  Purpose: Handles all asynchronous communication with FastAPI.
// ============================================================

import {
  HealthResponse,
  RootInfoResponse,
  Observation,
  ObservationListResponse,
  Feature,
  Prediction,
  CandidateScore,
  CandidateListResponse,
  ProcessingRunListResponse,
  UploadResponse,
  StartAnalysisRequest,
  AnalysisResult,
  OpticalPreview,
  AnalysisWorkflow,
  CsvUploadResponse,
  CsvAnalysisResult,
  CsvFileItem,
  CsvDataResponse,
  ObservationDateSearchResponse,
  CollectorSource,
  ResearchRecord,
  ResearchRecordListResponse,
  CollectorQueryRequest,
  CollectorQueryResponse,
  PaperExtractionResponse,
  LiteratureComparisonResponse,
  DatasetItem,
  DatasetStatusResponse,
  ExperimentSuiteResponse,
  MasterDatasetPreviewResponse,
  MasterManifest,
  DataDictionaryItem,
  ShapAnalysisResponse,
  GraphStatusResponse,
  GraphStatisticsResponse,
  GraphSubgraphResponse,
  MLflowStatusResponse,
  MLflowExperimentItem,
  MLflowRunItem,
} from '../types/api';


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      let errorDetail = `HTTP Error ${response.status}: ${response.statusText}`;
      let errorData = null;
      try {
        errorData = await response.json();
        if (errorData?.detail) {
          errorDetail = errorData.detail;
        }
      } catch {
        // Response was not JSON
      }
      throw new ApiError(errorDetail, response.status, errorData);
    }

    return await response.json();
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    // Network connectivity or CORS error
    throw new ApiError(
      `Network connection failed. Unable to reach ASTRA API at ${API_BASE_URL}.`,
      0,
      err
    );
  }
}

export const apiService = {
  getBaseUrl(): string {
    return API_BASE_URL;
  },

  async getHealth(): Promise<HealthResponse> {
    return fetchJson<HealthResponse>('/health');
  },

  async getRootInfo(): Promise<RootInfoResponse> {
    return fetchJson<RootInfoResponse>('/');
  },

  async getObservations(limit = 50, offset = 0): Promise<ObservationListResponse> {
    return fetchJson<ObservationListResponse>(`/api/observations?limit=${limit}&offset=${offset}`);
  },

  async getObservation(id: number): Promise<Observation> {
    return fetchJson<Observation>(`/api/observations/${id}`);
  },

  async getObservationFeatures(id: number): Promise<Feature | null> {
    return fetchJson<Feature | null>(`/api/observations/${id}/features`);
  },

  async getObservationPredictions(id: number): Promise<Prediction[]> {
    return fetchJson<Prediction[]>(`/api/observations/${id}/predictions`);
  },

  async getCandidates(
    limit = 50,
    offset = 0,
    priorityGroup?: string
  ): Promise<CandidateListResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    if (priorityGroup) {
      params.append('priority_group', priorityGroup);
    }
    return fetchJson<CandidateListResponse>(`/api/candidates?${params.toString()}`);
  },

  async getCandidate(observationId: number): Promise<CandidateScore> {
    return fetchJson<CandidateScore>(`/api/candidates/${observationId}`);
  },

  async getProcessingRuns(limit = 50, offset = 0): Promise<ProcessingRunListResponse> {
    return fetchJson<ProcessingRunListResponse>(
      `/api/processing-runs?limit=${limit}&offset=${offset}`
    );
  },

  async uploadFiles(files: File[], displayNames?: string[]): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    if (displayNames && displayNames.length > 0) {
      formData.append('display_names', JSON.stringify(displayNames));
    }

    const url = `${API_BASE_URL}/api/upload`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let detail = `HTTP Error ${response.status}: ${response.statusText}`;
      try {
        const err = await response.json();
        if (err?.detail) detail = err.detail;
      } catch { /* empty */ }
      throw new ApiError(detail, response.status);
    }

    return await response.json();
  },

  async uploadCsv(file: File, observationName?: string): Promise<CsvUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (observationName && observationName.trim()) {
      formData.append('observation_name', observationName.trim());
    }

    const url = `${API_BASE_URL}/api/upload/csv`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let detail = `HTTP Error ${response.status}: ${response.statusText}`;
      try {
        const err = await response.json();
        if (err?.detail) detail = err.detail;
      } catch { /* empty */ }
      throw new ApiError(detail, response.status);
    }

    return await response.json();
  },

  async analyzeCsv(server_file_path: string, workflow_id: string): Promise<CsvAnalysisResult> {
    const url = `${API_BASE_URL}/api/upload/csv/analyze`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ server_file_path, workflow_id }),
    });

    if (!response.ok) {
      let detail = `HTTP Error ${response.status}: ${response.statusText}`;
      try {
        const err = await response.json();
        if (err?.detail) detail = err.detail;
      } catch { /* empty */ }
      throw new ApiError(detail, response.status);
    }

    return await response.json();
  },

  async getObservationWorkflows(observationId: number): Promise<{ workflows: AnalysisWorkflow[] }> {
    return fetchJson<{ workflows: AnalysisWorkflow[] }>(`/api/upload/${observationId}/workflows`);
  },

  async startAnalysis(req: StartAnalysisRequest): Promise<AnalysisResult> {
    return fetchJson<AnalysisResult>('/api/analysis/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req),
    });
  },

  async getObservationPreview(observationId: number, groupIdx = 0): Promise<OpticalPreview> {
    return fetchJson<OpticalPreview>(`/api/observations/${observationId}/preview?group_idx=${groupIdx}`);
  },

  async updateObservation(observationId: number, displayName: string): Promise<Observation> {
    return fetchJson<Observation>(`/api/observations/${observationId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ display_name: displayName }),
    });
  },

  async downloadObservationReport(id: number, csvServerName?: string): Promise<void> {
    const params = new URLSearchParams();
    if (csvServerName && csvServerName.trim()) {
      params.set('csv_server_name', csvServerName.trim());
    }
    const query = params.toString() ? `?${params.toString()}` : '';
    const url = `${API_BASE_URL}/api/observations/${id}/report${query}`;
    const response = await fetch(url, { method: 'GET' });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const err = await response.json();
        if (err?.detail) detail = err.detail;
      } catch { /* empty */ }
      throw new ApiError(detail, response.status);
    }
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = blobUrl;
    anchor.download = csvServerName
      ? `astra_obs_${id}_report_with_csv.pdf`
      : `astra_obs_${id}_report.pdf`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(blobUrl);
  },

  async deleteObservation(id: number): Promise<{ message: string; observation_id: number }> {
    return fetchJson<{ message: string; observation_id: number }>(`/api/observations/${id}`, {
      method: 'DELETE',
    });
  },

  async renameObservationGroup(oldName: string, newName: string): Promise<{ updated_count: number; new_name: string }> {
    return fetchJson<{ updated_count: number; new_name: string }>('/api/observations/group/rename', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ old_name: oldName, new_name: newName }),
    });
  },

  async listCsvFiles(): Promise<CsvFileItem[]> {
    return fetchJson<CsvFileItem[]>('/api/upload/csv');
  },

  async deleteCsvFile(serverName: string): Promise<{ message: string; server_name: string }> {
    return fetchJson<{ message: string; server_name: string }>(`/api/upload/csv/${encodeURIComponent(serverName)}`, {
      method: 'DELETE',
    });
  },

  async getCsvData(serverName: string, page = 1, pageSize = 50): Promise<CsvDataResponse> {
    return fetchJson<CsvDataResponse>(
      `/api/upload/csv/${encodeURIComponent(serverName)}/data?page=${page}&page_size=${pageSize}`
    );
  },

  async downloadCsvReport(serverName: string, observationName?: string): Promise<void> {
    const params = new URLSearchParams();
    if (observationName && observationName.trim()) {
      params.set('observation_name', observationName.trim());
    }
    const query = params.toString() ? `?${params.toString()}` : '';
    const url = `${API_BASE_URL}/api/upload/csv/${encodeURIComponent(serverName)}/report${query}`;
    const response = await fetch(url, { method: 'GET' });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const err = await response.json();
        if (err?.detail) detail = err.detail;
      } catch { /* empty */ }
      throw new ApiError(detail, response.status);
    }
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = blobUrl;
    const cleanStem = serverName.replace(/\.csv$/i, '');
    anchor.download = `astra_csv_${cleanStem}_report.pdf`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(blobUrl);
  },

  async downloadOriginalCsv(serverName: string, originalName?: string): Promise<void> {
    const url = `${API_BASE_URL}/api/upload/csv/${encodeURIComponent(serverName)}/download`;
    const response = await fetch(url, { method: 'GET' });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const err = await response.json();
        if (err?.detail) detail = err.detail;
      } catch { /* empty */ }
      throw new ApiError(detail, response.status);
    }
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = blobUrl;
    anchor.download = originalName || serverName;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(blobUrl);
  },

  async updateCsvMetadata(serverName: string, observationName: string): Promise<CsvFileItem> {
    return fetchJson<CsvFileItem>(`/api/upload/csv/${encodeURIComponent(serverName)}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ observation_name: observationName }),
    });
  },

  async searchObservationsByDate(date?: string): Promise<ObservationDateSearchResponse> {
    const params = new URLSearchParams();
    if (date && date.trim()) {
      params.set('date', date.trim());
    }
    const query = params.toString() ? `?${params.toString()}` : '';
    return fetchJson<ObservationDateSearchResponse>(`/api/observations/date-search${query}`);
  },

  // ============================================================
  //  Research Web Collector Methods
  // ============================================================

  async listCollectorSources(): Promise<CollectorSource[]> {
    return fetchJson<CollectorSource[]>('/api/collector/sources');
  },

  async queryCollector(req: CollectorQueryRequest): Promise<CollectorQueryResponse> {
    return fetchJson<CollectorQueryResponse>('/api/collector/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
  },

  async listResearchRecords(params?: {
    q?: string;
    source?: string;
    record_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<ResearchRecordListResponse> {
    const p = new URLSearchParams();
    if (params?.q) p.set('q', params.q);
    if (params?.source) p.set('source', params.source);
    if (params?.record_type) p.set('record_type', params.record_type);
    if (params?.limit !== undefined) p.set('limit', String(params.limit));
    if (params?.offset !== undefined) p.set('offset', String(params.offset));
    const qs = p.toString() ? `?${p.toString()}` : '';
    return fetchJson<ResearchRecordListResponse>(`/api/collector/records${qs}`);
  },

  async getResearchRecord(id: number): Promise<ResearchRecord> {
    return fetchJson<ResearchRecord>(`/api/collector/records/${id}`);
  },

  async getRecordExtraction(id: number): Promise<PaperExtractionResponse> {
    return fetchJson<PaperExtractionResponse>(`/api/collector/records/${id}/extraction`);
  },

  async getLatestComparison(): Promise<LiteratureComparisonResponse> {
    return fetchJson<LiteratureComparisonResponse>('/api/collector/compare/latest');
  },

  async triggerComparison(recordIds?: number[]): Promise<LiteratureComparisonResponse> {
    return fetchJson<LiteratureComparisonResponse>('/api/collector/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ record_ids: recordIds || null, save_report: true }),
    });
  },

  //  Dataset Integration & Five Research Problems Methods
  async getDatasets(): Promise<DatasetItem[]> {
    return fetchJson<DatasetItem[]>('/api/datasets');
  },

  async getDatasetStatus(): Promise<DatasetStatusResponse> {
    return fetchJson<DatasetStatusResponse>('/api/datasets/status');
  },

  async getExperimentResults(): Promise<ExperimentSuiteResponse> {
    return fetchJson<ExperimentSuiteResponse>('/api/datasets/experiments/results');
  },

  async runExperiments(seed: number = 42): Promise<ExperimentSuiteResponse> {
    return fetchJson<ExperimentSuiteResponse>('/api/datasets/experiments/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ seed, record_processing_run: true }),
    });
  },

  async downloadExperimentPdf(): Promise<void> {
    const url = `${API_BASE_URL}/api/datasets/experiments/pdf`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new ApiError(`Failed to download experiments PDF (HTTP ${res.status})`, res.status);
    }
    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `ASTRA_Two_Dataset_Integration_Audit_Report_${new Date().toISOString().slice(0, 10)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(blobUrl);
  },

  // ============================================================
  //  Integrated Master Dataset Methods
  // ============================================================

  async getMasterDatasetPreview(params?: {
    limit?: number;
    offset?: number;
    source?: string;
    search?: string;
  }): Promise<MasterDatasetPreviewResponse> {
    const p = new URLSearchParams();
    if (params?.limit !== undefined) p.set('limit', String(params.limit));
    if (params?.offset !== undefined) p.set('offset', String(params.offset));
    if (params?.source) p.set('source', params.source);
    if (params?.search) p.set('search', params.search);
    const qs = p.toString() ? `?${p.toString()}` : '';
    return fetchJson<MasterDatasetPreviewResponse>(`/api/datasets/master/preview${qs}`);
  },

  async getMasterManifest(): Promise<MasterManifest> {
    return fetchJson<MasterManifest>('/api/datasets/master/manifest');
  },

  async getMasterValidationReport(): Promise<any> {
    return fetchJson<any>('/api/datasets/master/validation');
  },

  async getMasterDataDictionary(): Promise<DataDictionaryItem[]> {
    return fetchJson<DataDictionaryItem[]>('/api/datasets/master/data-dictionary');
  },

  async downloadMasterDatasetCsv(): Promise<void> {
    const url = `${API_BASE_URL}/api/datasets/master/download`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new ApiError(`Failed to download master dataset (HTTP ${res.status})`, res.status);
    }
    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `master_dataset_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(blobUrl);
  },

  async downloadMasterDatasetParquet(): Promise<void> {
    const url = `${API_BASE_URL}/api/datasets/master/download-parquet`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new ApiError(`Failed to download master dataset Parquet (HTTP ${res.status})`, res.status);
    }
    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `master_dataset_${new Date().toISOString().slice(0, 10)}.parquet`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(blobUrl);
  },

  getReportImageUrl(imageName: string): string {
    return `${API_BASE_URL}/api/datasets/images/${encodeURIComponent(imageName)}`;
  },

  async getShapAnalysis(): Promise<ShapAnalysisResponse> {
    return fetchJson<ShapAnalysisResponse>('/api/datasets/shap');
  },

  // ============================================================
  //  Neo4j Knowledge Graph Methods
  // ============================================================

  async getGraphStatus(): Promise<GraphStatusResponse> {
    return fetchJson<GraphStatusResponse>('/api/graph/status');
  },

  async getGraphStatistics(): Promise<GraphStatisticsResponse> {
    return fetchJson<GraphStatisticsResponse>('/api/graph/statistics');
  },

  async getGraphSubgraph(limit: number = 100, label?: string): Promise<GraphSubgraphResponse> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (label) params.append('label', label);
    return fetchJson<GraphSubgraphResponse>(`/api/graph/subgraph?${params.toString()}`);
  },

  async syncKnowledgeGraph(): Promise<any> {
    return fetchJson<any>('/api/graph/sync', {
      method: 'POST',
    });
  },

  async initGraphSchema(): Promise<any> {
    return fetchJson<any>('/api/graph/init-schema', {
      method: 'POST',
    });
  },

  async executeGraphQuery(query: string, parameters?: Record<string, any>): Promise<any> {
    return fetchJson<any>('/api/graph/query', {
      method: 'POST',
      body: JSON.stringify({ query, parameters: parameters || {} }),
    });
  },

  // ============================================================
  //  MLflow Tracking Methods
  // ============================================================

  async getMLflowStatus(): Promise<MLflowStatusResponse> {
    return fetchJson<MLflowStatusResponse>('/api/mlflow/status');
  },

  async getMLflowExperiments(): Promise<MLflowExperimentItem[]> {
    return fetchJson<MLflowExperimentItem[]>('/api/mlflow/experiments');
  },

  async getMLflowRuns(experimentName?: string, limit: number = 50): Promise<MLflowRunItem[]> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (experimentName) params.append('experiment_name', experimentName);
    return fetchJson<MLflowRunItem[]>(`/api/mlflow/runs?${params.toString()}`);
  },

  async getMLflowBestRun(experimentName: string = 'ASTRA_HTRU2_Classification', metricName: string = 'f1_score'): Promise<MLflowRunItem> {
    const params = new URLSearchParams({ experiment_name: experimentName, metric_name: metricName });
    return fetchJson<MLflowRunItem>(`/api/mlflow/best-run?${params.toString()}`);
  },

  async syncMLflowExperiments(): Promise<any> {
    return fetchJson<any>('/api/mlflow/sync-research-experiments', {
      method: 'POST',
    });
  },
};


