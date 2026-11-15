// ============================================================
//  ASTRA — TypeScript API Types & Models
//  File   : frontend/src/types/api.ts
//  Purpose: Matches FastAPI backend Pydantic schemas exactly.
// ============================================================

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  database_connected: boolean;
  database_message: string;
  timestamp: string;
}

export interface RootInfoResponse {
  project: string;
  version: string;
  description: string;
  docs_url: string;
  endpoints: Record<string, string>;
}

export interface Observation {
  id: number;
  file_name: string;
  file_path: string;
  file_type: string;
  telescope: string | null;
  instrument: string | null;
  target_name: string | null;
  observation_date: string | null;
  observation_time: string | null;
  ra: string | null;
  dec: string | null;
  ra_deg: number | null;
  dec_deg: number | null;
  frequency_mhz: number | null;
  bandwidth_mhz: number | null;
  nchan: number | null;
  nsubint: number | null;
  nbin: number | null;
  observation_mode: string | null;
  data_mode: string | null;
  polarization_info: string | null;
  file_size_mb: number | null;
  validation_status: string;
  created_at: string;
  updated_at: string;
}

export interface ObservationListResponse {
  total: number;
  limit: number;
  offset: number;
  items: Observation[];
}

export interface Feature {
  id: number;
  observation_id: number;
  profile_mean: number | null;
  profile_std: number | null;
  profile_skewness: number | null;
  profile_kurtosis: number | null;
  profile_bins: number | null;
  profile_status: string | null;
  dm_nominal: number | null;
  dm_mean: number | null;
  dm_std: number | null;
  dm_skewness: number | null;
  dm_kurtosis: number | null;
  dm_curve_available: boolean;
  dm_status: string | null;
  signal_mean: number | null;
  signal_std: number | null;
  noise_estimate: number | null;
  dynamic_range: number | null;
  valid_fraction: number | null;
  nan_fraction: number | null;
  inf_fraction: number | null;
  quality_status: string | null;
  rfi_indicator: number | null;
  rfi_affected_channels: number | null;
  rfi_outlier_channels: number | null;
  rfi_status: string | null;
  htru2_compatible: boolean;
  domain_shift_flag: string | null;
  out_of_range_feature_count: number | null;
  extracted_at: string;
}

export interface Prediction {
  id: number;
  observation_id: number;
  model_name: string;
  model_version: string;
  predicted_class: number | null;
  pulsar_probability: number | null;
  non_pulsar_probability: number | null;
  inference_status: string;
  halt_reason: string | null;
  prediction_timestamp: string;
  created_at: string;
}

export interface CandidateScore {
  id: number;
  observation_id: number;
  file_name: string | null;
  target_name: string | null;
  telescope: string | null;
  score_version: string;
  ml_probability: number | null;
  signal_quality: number | null;
  rfi_indicator: number | null;
  periodicity_evidence: number | null;
  dm_evidence: number | null;
  profile_evidence: number | null;
  acis_score: number;
  evidence_available: string;
  score_status: string;
  priority_group: 'HIGH' | 'MEDIUM' | 'LOW';
  rank_position: number | null;
  notes: string | null;
  created_at: string;
}

export interface CandidateListResponse {
  total: number;
  limit: number;
  offset: number;
  items: CandidateScore[];
}

export interface ProcessingRun {
  id: number;
  observation_id: number | null;
  run_identifier: string;
  pipeline_step: string;
  pipeline_version: string;
  processing_status: string;
  started_at: string;
  completed_at: string | null;
  elapsed_seconds: number | null;
  error_message: string | null;
  log_summary: string | null;
}

export interface ProcessingRunListResponse {
  total: number;
  limit: number;
  offset: number;
  items: ProcessingRun[];
}

export interface AnalysisWorkflow {
  id: string;
  name: string;
  description: string;
  category: 'metadata' | 'quality' | 'signal' | 'ml' | 'visualization' | 'report';
  enabled: boolean;
  disabled_reason?: string;
}

export interface FileUploadItem {
  observation_id: number;
  file_name: string;
  display_name: string;
  file_size_mb: number;
  detected_type: string;
  telescope: string | null;
  instrument: string | null;
  checksum: string;
  is_duplicate: boolean;
  available_workflows: AnalysisWorkflow[];
}

export interface UploadResponse {
  total_uploaded: number;
  files: FileUploadItem[];
  message: string;
}

export interface StartAnalysisRequest {
  observation_id: number;
  workflow_id: string;
  options?: Record<string, any>;
}

export interface AnalysisResult {
  run_id: number;
  observation_id: number;
  workflow: string;
  status: string;
  elapsed_seconds: number;
  summary: string;
  details: Record<string, any>;
}

export interface OpticalPreview {
  observation_id: number;
  image_data_url: string;
  slice_name: string;
  width: number;
  height: number;
  min_val: number;
  max_val: number;
  mean_val: number;
  median_val: number;
  std_val: number;
  nan_count: number;
  inf_count: number;
  total_pixels: number;
}

export type NavTab =
  | 'overview'
  | 'integrated-datasets'
  | 'dataset-experiments'
  | 'ml-workflow'
  | 'knowledge-graph'
  | 'mlflow-tracking'
  | 'research-sources'
  | 'reports'
  | 'system-status'
  | 'add-data'
  | 'observations'
  | 'observation-date-search'
  | 'history'
  | 'high-priority'
  | 'medium-priority'
  | 'low-priority';

export interface CsvFileItem {
  server_name: string;
  server_file_path: string;
  file_name: string;
  file_size_kb: number;
  upload_date: string;
  total_rows?: number;
  total_columns?: number;
  status: string;
  observation_name?: string;
}

export interface ObservationGroup {
  group_name: string;
  files: Observation[];
  file_count: number;
  primary_date?: string;
  telescopes: string[];
  instruments: string[];
  acis_priority?: string;
  acis_score?: number;
  csv_files?: CsvFileItem[];
}

export interface CsvColumnDetail {
  name: string;
  inferred_type: string;
  non_empty_count: number;
  missing_count: number;
  min: number | string | null;
  max: number | string | null;
  mean: number | null;
  std: number | null;
}

export interface CsvDataResponse {
  file_info: CsvFileItem;
  columns: CsvColumnDetail[];
  rows: Record<string, any>[];
  page: number;
  page_size: number;
  total_rows: number;
  total_pages: number;
}

export interface CsvColumnStat {
  name: string;
  dtype: string;
  non_null: number;
  null_count: number;
  min: number | string | null;
  max: number | string | null;
  mean: number | null;
}

export interface CsvWorkflow {
  id: string;
  name: string;
  description: string;
  category: 'statistics' | 'visualization' | 'ml';
  enabled: boolean;
}

export interface CsvUploadResponse {
  file_name: string;
  file_size_kb: number;
  total_rows: number;
  total_columns: number;
  columns: CsvColumnStat[];
  preview_rows: Record<string, any>[];
  available_workflows: CsvWorkflow[];
  server_file_path: string;
  message: string;
}

export interface CsvAnalysisRequest {
  server_file_path: string;
  workflow_id: string;
}

export interface CsvAnalysisResult {
  workflow_id: string;
  status: string;
  summary: string;
  details: Record<string, any>;
  elapsed_seconds: number;
}

export interface ObservationDateFileItem {
  id: number | null;
  observation_id: number | null;
  file_name: string;
  file_type: string;
  file_size_mb: number | null;
  telescope: string | null;
  instrument: string | null;
  target_name: string | null;
  recorded_observation_date: string | null;
  recorded_observation_time: string | null;
  date_source: string;
  is_date_verified: boolean;
  server_path?: string | null;
  csv_server_name?: string | null;
}

export interface ObservationDateGroupMatch {
  observation_name: string;
  recorded_observation_date: string | null;
  file_count: number;
  telescopes: string[];
  instruments: string[];
  files: ObservationDateFileItem[];
}

export interface ObservationDateSearchResponse {
  search_date: string | null;
  total_matching_observations: number;
  total_matching_files: number;
  results: ObservationDateGroupMatch[];
  undated_files_count: number;
  available_observation_dates: string[];
  message: string;
}

// ============================================================
//  Research Web Collector — API Types
// ============================================================

export interface CollectorSource {
  name: string;
  description: string;
  status: 'active' | 'planned' | 'disabled';
  supported_record_types: string[];
  rate_limit_note: string;
  base_url: string;
}

export interface ResearchRecord {
  id: number;
  record_type: string;
  title: string;
  authors: string[];
  abstract: string | null;
  publication_date: string | null;
  identifier: string;
  source_name: string;
  canonical_url: string;
  retrieval_timestamp: string;
  retrieval_status: string;
  scientific_disclaimer: string;
}

export interface ResearchRecordListResponse {
  total: number;
  items: ResearchRecord[];
  scientific_disclaimer: string;
}

export interface CollectorQueryRequest {
  query: string;
  source?: string;
  category?: string;
  max_results?: number;
  save_to_db?: boolean;
}

export interface CollectorQueryResponse {
  query: string;
  source: string;
  total_found: number;
  total_returned: number;
  total_deduplicated: number;
  total_saved: number;
  items: ResearchRecord[];
  scientific_disclaimer: string;
  execution_seconds: number;
}

export interface ExtractedResearchDetails {
  research_problem: string;
  dataset_name: string;
  dataset_type: string;
  algorithms_or_models: string[];
  feature_types: string[];
  evaluation_metrics: string[];
  main_reported_findings: string;
  stated_limitations: string;
  full_text_availability: string;
  licence_or_access_status: string;
  source_url: string;
  doi: string;
  evidence_locations: Record<string, string>;
  is_inferred: boolean;
}

export interface PaperExtractionResponse {
  id: number | null;
  record_id: number | null;
  identifier: string;
  title: string;
  extracted_details: ExtractedResearchDetails;
  provenance: Record<string, any>;
  extracted_at: string;
  scientific_disclaimer: string;
}

export interface ComparisonRow {
  identifier: string;
  title: string;
  research_problem: string;
  data_source: string;
  observing_mode: string;
  dataset_size: string;
  algorithm_or_method: string;
  input_features: string;
  evaluation_metrics: string;
  main_result: string;
  limitations: string;
  astra_relevance: string;
}

export interface GapCandidate {
  candidate_gap: string;
  supporting_papers: string[];
  confidence: string;
  human_verification_required: boolean;
  provenance_note: string;
}

export interface ConflictingSetup {
  description: string;
  papers_involved: string[];
  conflict_type: string;
}

export interface ManualVerificationItem {
  item: string;
  related_papers: string[];
  reason: string;
}

export interface LiteratureComparisonResponse {
  generated_at: string;
  total_papers_compared: number;
  comparison_table: ComparisonRow[];
  research_gap_candidates: GapCandidate[];
  conflicting_or_incomparable_setups: ConflictingSetup[];
  manual_verification_items: ManualVerificationItem[];
  scientific_disclaimer: string;
  coverage_warning: string;
}

// ── Two-Dataset Integration & Five Research Problems ────────

export interface DatasetItem {
  id: string;
  name: string;
  source: string;
  source_url: string;
  filename: string;
  file_path: string;
  format: string;
  dataset_type: string;
  record_count: number;
  feature_count: number;
  label_availability: boolean;
  label_classes?: Record<string, string> | null;
  file_size_bytes: number;
  validation_status: string;
  supported_experiment_types: string[];
  description: string;
}

export interface DatasetStatusResponse {
  status: string;
  datasets: DatasetItem[];
  timestamp: string;
}

export interface P1PerturbationRow {
  perturbation_scale: number;
  description: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  roc_auc: number;
}

export interface P1ParkesNoiseRow {
  noise_ratio: number;
  label: string;
  signal_rms: number;
  observed_snr: number;
  snr_retention: number;
  snr_degradation_pct: number;
}

export interface P1Result {
  problem: string;
  htru2_perturbations: P1PerturbationRow[];
  parkes_noise_experiments: P1ParkesNoiseRow[];
  scientific_note: string;
}

export interface P2MaskingRow {
  mask_fraction: number;
  masked_channel_count: number;
  remaining_channel_count: number;
  energy_retention_ratio: number;
  observed_snr: number;
  snr_retention_ratio: number;
  recoverability_index: number;
  status: string;
}

export interface P2Result {
  problem: string;
  baseline_channels: number;
  baseline_snr: number;
  masking_experiments: P2MaskingRow[];
  conclusion: string;
}

export interface P3CompatibilityRow {
  dimension: string;
  dataset_a_htru2: string;
  dataset_b_parkes: string;
  compatible: boolean;
  scientific_finding: string;
}

export interface P3Result {
  problem: string;
  verdict: string;
  transfer_evaluation_status: string;
  compatibility_matrix: P3CompatibilityRow[];
  prerequisite_pipeline_steps: string[];
  policy_statement: string;
}

export interface P4ReliabilityBin {
  bin_index: number;
  confidence_range: string;
  sample_count: number;
  mean_confidence: number;
  empirical_accuracy: number;
  calibration_error: number;
  calibration_status: string;
}

export interface P4Result {
  problem: string;
  test_sample_size: number;
  brier_score: number;
  expected_calibration_error_ece: number;
  maximum_calibration_error_mce: number;
  reliability_diagram_bins: P4ReliabilityBin[];
  interpretation: string;
}

export interface P5GroupStats {
  count: number;
  profile_mean: number;
  profile_std: number;
  profile_kurtosis: number;
  dm_mean: number;
  dm_std: number;
}

export interface P5Htru2Failures {
  counts: {
    true_positives: number;
    true_negatives: number;
    false_positives: number;
    false_negatives: number;
  };
  rates: {
    false_positive_rate: number;
    false_negative_rate: number;
  };
  feature_morphology: {
    true_positives: P5GroupStats;
    true_negatives: P5GroupStats;
    false_positives: P5GroupStats;
    false_negatives: P5GroupStats;
  };
  fp_mechanism: string;
  fn_mechanism: string;
}

export interface P5FailureMode {
  mode: string;
  impact: string;
}

export interface P5ParkesFailures {
  baseline_snr: number;
  critical_masking_threshold: string;
  critical_noise_threshold: string;
  failure_mechanisms: P5FailureMode[];
}

export interface P5Result {
  problem: string;
  htru2_classification_failures: P5Htru2Failures;
  parkes_signal_quality_failures: P5ParkesFailures;
}

export interface CrossExperimentComparisonItem {
  experiment_id: string;
  experiment_name: string;
  htru2_role: string;
  parkes_role: string;
  comparable_metrics: string;
  cross_dataset_conclusion: string;
  limitations_and_pending_stages: string;
}

export interface IntegratedSynthesisItem {
  problem_id: string;
  title: string;
  research_question: string;
  htru2_result: string;
  parkes_result: string;
  cross_dataset_interpretation: string;
  scientific_conclusion: string;
  limitations_and_missing_validation: string;
}

export interface UnifiedExperimentRecord {
  experiment_id: string;
  experiment_name: string;
  dataset_id: string;
  dataset_name: string;
  source_record_id: string;
  processing_stage: string;
  input_representation: string;
  feature_schema_version: string;
  model_or_method: string;
  parameters: Record<string, any>;
  metric_name: string;
  metric_value: number;
  metric_unit: string;
  result_type: 'measured' | 'simulated' | 'predicted' | 'unavailable';
  comparability_status: string;
  limitation: string;
  execution_timestamp: string;
}

export interface ExperimentSuiteResponse {
  suite_name: string;
  execution_timestamp: string;
  execution_seconds: number;
  reproducible_seed: number;
  datasets: {
    dataset_a_htru2: Record<string, any>;
    dataset_b_parkes: Record<string, any>;
  };
  problems: {
    p1_perturbations: P1Result;
    p2_channel_masking: P2Result;
    p3_cross_compatibility: P3Result;
    p4_confidence_calibration: P4Result;
    p5_failure_analysis: P5Result;
  };
  unified_experiment_records?: UnifiedExperimentRecord[];
  cross_experiment_comparison?: CrossExperimentComparisonItem[];
  integrated_syntheses?: Record<string, IntegratedSynthesisItem>;
}

export interface MasterRecord {
  master_record_id: string;
  source_dataset: 'HTRU2' | 'PARKES_PDFB4' | 'GBT_VEGAS' | string;
  source_record_id: string | number;
  source_file: string;
  data_format: string;
  target_name: string;
  telescope: string;
  observation_date: string | null;
  label_availability: boolean;
  target_label: number | null;
  target_class_description: string;
  htru2_profile_mean: number | null;
  htru2_profile_std: number | null;
  htru2_profile_skewness: number | null;
  htru2_profile_kurtosis: number | null;
  htru2_dm_mean: number | null;
  htru2_dm_std: number | null;
  htru2_dm_skewness: number | null;
  htru2_dm_kurtosis: number | null;
  parkes_tsubint_sec: number | null;
  parkes_offs_sub_sec: number | null;
  parkes_ra_deg: number | null;
  parkes_dec_deg: number | null;
  parkes_glon_deg: number | null;
  parkes_glat_deg: number | null;
  parkes_tel_az_deg: number | null;
  parkes_tel_zen_deg: number | null;
  parkes_center_freq_mhz: number | null;
  parkes_bandwidth_mhz: number | null;
  parkes_nchan: number | null;
  parkes_usable_channels: number | null;
  parkes_signal_mean: number | null;
  parkes_signal_std: number | null;
  parkes_snr_estimate: number | null;
  parkes_dynamic_range: number | null;
  parkes_rfi_indicator: number | null;
  parkes_aux_dm: number | null;
  parkes_aux_rm: number | null;
  gbt_telescope?: string | null;
  gbt_backend?: string | null;
  gbt_obsfreq_mhz?: number | null;
  gbt_nchan?: number | null;
  gbt_nbin?: number | null;
  gbt_profile_mean?: number | null;
  gbt_profile_kurtosis?: number | null;
  feature_availability: string;
  processing_status: string;
  validation_notes: string;
}

export interface MasterDatasetPreviewResponse {
  total: number;
  limit: number;
  offset: number;
  items: MasterRecord[];
  summary: {
    total_records: number;
    htru2_records: number;
    parkes_records: number;
    gbt_vegas_records?: number;
    filtered_records: number;
    column_count?: number;
  };
}

export interface MasterManifest {
  manifest_version: string;
  generated_at_utc: string;
  project: string;
  description: string;
  storage_format: {
    csv_master: string;
    parquet_supported: boolean;
    parquet_reason: string;
  };
  source_catalog: Array<{
    source_id: string;
    file_path: string;
    sha256: string;
    file_size_bytes: number;
    source_record_count?: number;
    source_subint_count?: number;
    integrated_record_count: number;
    rejected_record_count: number;
    duplicate_record_count: number;
    data_type: string;
    label_availability: boolean;
    class_distribution?: Record<string, number>;
    label_note?: string;
  }>;
  record_summary: {
    total_records: number;
    htru2_records: number;
    parkes_records: number;
    feature_column_count: number;
    canonical_id_column: string;
    shared_feature_count: number;
    shared_feature_explanation: string;
  };
}

export interface DataDictionaryItem {
  column_name: string;
  data_type: string;
  description: string;
  units: string;
  source: string;
}

export interface ShapRankingItem {
  feature: string;
  mean_abs_shap: number;
  relative_importance_pct: number;
}

export interface ShapAnalysisResponse {
  model_type: string;
  explainer_type: string;
  sample_size?: number;
  total_test_records?: number;
  ranking: ShapRankingItem[];
  interpretation: string;
}

// ── Neo4j Knowledge Graph Types ───────────────────────────────
export interface GraphStatusResponse {
  connected: boolean;
  message: string;
  telemetry: {
    uri?: string;
    database?: string;
    node_count?: number;
    relationship_count?: number;
    status?: string;
    error?: string;
  };
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
}

export interface GraphSubgraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  summary: {
    connected: boolean;
    node_count?: number;
    edge_count?: number;
    message?: string;
  };
}

export interface GraphStatisticsResponse {
  connected: boolean;
  message: string;
  labels: Record<string, number>;
  relationships: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
  uri?: string;
  database?: string;
}

// ── MLflow Tracking Types ─────────────────────────────────────
export interface MLflowStatusResponse {
  connected: boolean;
  message: string;
  telemetry: {
    tracking_uri?: string;
    ui_url?: string;
    experiment_count?: number;
    total_runs?: number;
    status?: string;
    error?: string;
  };
}

export interface MLflowExperimentItem {
  experiment_id: string;
  name: string;
  artifact_location: string;
  lifecycle_stage: string;
  run_count: number;
  tags?: Record<string, string>;
}

export interface MLflowRunItem {
  run_id: string;
  experiment_id: string;
  run_name: string;
  status: string;
  start_time: string | null;
  end_time: string | null;
  params: Record<string, any>;
  metrics: Record<string, number>;
  tags: Record<string, string>;
  artifact_uri: string;
}

