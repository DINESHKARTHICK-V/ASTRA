# ============================================================
#  ASTRA Cloud — Pydantic API Schemas
#  File   : backend/app/schemas.py
#  Purpose: Request and response serialization for FastAPI endpoints.
# ============================================================

from typing import Optional, List, Dict, Any, Literal
from datetime import date, time, datetime
from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------
# System & Health Schemas
# ------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall service status ('healthy' or 'degraded')")
    database_connected: bool = Field(..., description="PostgreSQL connectivity flag")
    database_message: str = Field(..., description="Status description of the database connection")
    timestamp: datetime = Field(..., description="UTC timestamp of the health check")

    model_config = ConfigDict(from_attributes=True)


class RootInfoResponse(BaseModel):
    project: str
    version: str
    description: str
    docs_url: str
    endpoints: Dict[str, str]

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# Observations Schemas
# ------------------------------------------------------------
class ObservationResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    file_type: str
    telescope: Optional[str] = None
    instrument: Optional[str] = None
    target_name: Optional[str] = None
    observation_date: Optional[date] = None
    observation_time: Optional[time] = None
    ra: Optional[str] = None
    dec: Optional[str] = None
    ra_deg: Optional[float] = None
    dec_deg: Optional[float] = None
    frequency_mhz: Optional[float] = None
    bandwidth_mhz: Optional[float] = None
    nchan: Optional[int] = None
    nsubint: Optional[int] = None
    nbin: Optional[int] = None
    observation_mode: Optional[str] = None
    data_mode: Optional[str] = None
    polarization_info: Optional[str] = None
    file_size_mb: Optional[float] = None
    validation_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ObservationListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[ObservationResponse]

    model_config = ConfigDict(from_attributes=True)


class ObservationDateFileItem(BaseModel):
    id: Optional[int] = None
    observation_id: Optional[int] = None
    file_name: str
    file_type: str
    file_size_mb: Optional[float] = None
    telescope: Optional[str] = None
    instrument: Optional[str] = None
    target_name: Optional[str] = None
    recorded_observation_date: Optional[str] = None
    recorded_observation_time: Optional[str] = None
    date_source: str
    is_date_verified: bool
    server_path: Optional[str] = None
    csv_server_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ObservationDateGroupMatch(BaseModel):
    observation_name: str
    recorded_observation_date: Optional[str] = None
    file_count: int
    telescopes: List[str] = []
    instruments: List[str] = []
    files: List[ObservationDateFileItem] = []

    model_config = ConfigDict(from_attributes=True)


class ObservationDateSearchResponse(BaseModel):
    search_date: Optional[str] = None
    total_matching_observations: int
    total_matching_files: int
    results: List[ObservationDateGroupMatch] = []
    undated_files_count: int = 0
    available_observation_dates: List[str] = []
    message: str

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# Features Schemas
# ------------------------------------------------------------
class FeatureResponse(BaseModel):
    id: int
    observation_id: int

    # Pulse profile moments
    profile_mean: Optional[float] = None
    profile_std: Optional[float] = None
    profile_skewness: Optional[float] = None
    profile_kurtosis: Optional[float] = None
    profile_bins: Optional[int] = None
    profile_status: Optional[str] = None

    # Dispersion Measure
    dm_nominal: Optional[float] = None
    dm_mean: Optional[float] = None
    dm_std: Optional[float] = None
    dm_skewness: Optional[float] = None
    dm_kurtosis: Optional[float] = None
    dm_curve_available: bool
    dm_status: Optional[str] = None

    # Signal Quality & Noise
    signal_mean: Optional[float] = None
    signal_std: Optional[float] = None
    noise_estimate: Optional[float] = None
    dynamic_range: Optional[float] = None
    valid_fraction: Optional[float] = None
    nan_fraction: Optional[float] = None
    inf_fraction: Optional[float] = None
    quality_status: Optional[str] = None

    # RFI analysis
    rfi_indicator: Optional[float] = None
    rfi_affected_channels: Optional[int] = None
    rfi_outlier_channels: Optional[int] = None
    rfi_status: Optional[str] = None

    # Domain shift diagnostics
    htru2_compatible: bool
    domain_shift_flag: Optional[str] = None
    out_of_range_feature_count: Optional[int] = 0
    extracted_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# Predictions Schemas
# ------------------------------------------------------------
class PredictionResponse(BaseModel):
    id: int
    observation_id: int
    model_name: str
    model_version: str
    predicted_class: Optional[int] = None
    pulsar_probability: Optional[float] = None
    non_pulsar_probability: Optional[float] = None
    inference_status: str
    halt_reason: Optional[str] = None
    prediction_timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# Candidate Score & Ranking Schemas (ACIS)
# ------------------------------------------------------------
class CandidateScoreResponse(BaseModel):
    id: int
    observation_id: int
    file_name: Optional[str] = None
    target_name: Optional[str] = None
    telescope: Optional[str] = None
    score_version: str

    # Normalized evidence channels
    ml_probability: Optional[float] = None
    signal_quality: Optional[float] = None
    rfi_indicator: Optional[float] = None
    periodicity_evidence: Optional[float] = None
    dm_evidence: Optional[float] = None
    profile_evidence: Optional[float] = None

    # ACIS scoring
    acis_score: float
    evidence_available: str
    score_status: str
    priority_group: str
    rank_position: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[CandidateScoreResponse]

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# Processing Runs Schemas
# ------------------------------------------------------------
class ProcessingRunResponse(BaseModel):
    id: int
    observation_id: Optional[int] = None
    run_identifier: str
    pipeline_step: str
    pipeline_version: str
    processing_status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    elapsed_seconds: Optional[float] = None
    error_message: Optional[str] = None
    log_summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProcessingRunListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[ProcessingRunResponse]

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------
# Upload & Dynamic Analysis Schemas
# ------------------------------------------------------------

class CsvColumnStat(BaseModel):
    name: str
    dtype: str
    non_null: int
    null_count: int
    min: Optional[Any] = None
    max: Optional[Any] = None
    mean: Optional[float] = None


class CsvUploadResponse(BaseModel):
    file_name: str
    file_size_kb: float
    total_rows: int
    total_columns: int
    columns: List[CsvColumnStat]
    preview_rows: List[Dict[str, Any]]   # first 10 rows
    available_workflows: List[Dict[str, Any]]
    server_file_path: str               # relative path for analysis calls
    message: str


class CsvAnalysisRequest(BaseModel):
    server_file_path: str               # relative path returned by upload
    workflow_id: str


class CsvAnalysisResult(BaseModel):
    workflow_id: str
    status: str
    summary: str
    details: Dict[str, Any]
    elapsed_seconds: float


class CsvFileItem(BaseModel):
    server_name: str
    server_file_path: str
    file_name: str
    file_size_kb: float
    upload_date: str
    total_rows: Optional[int] = None
    total_columns: Optional[int] = None
    status: str = "INGESTED"
    observation_name: Optional[str] = None


class CsvColumnDetail(BaseModel):
    name: str
    inferred_type: str
    non_empty_count: int
    missing_count: int
    min: Optional[Any] = None
    max: Optional[Any] = None
    mean: Optional[float] = None
    std: Optional[float] = None


class CsvDataResponse(BaseModel):
    file_info: CsvFileItem
    columns: List[CsvColumnDetail]
    rows: List[Dict[str, Any]]
    page: int
    page_size: int
    total_rows: int
    total_pages: int


class CsvUpdateRequest(BaseModel):
    observation_name: Optional[str] = None



class FileUploadItem(BaseModel):
    observation_id: int
    file_name: str
    display_name: str
    file_size_mb: float
    detected_type: str
    telescope: Optional[str] = None
    instrument: Optional[str] = None
    checksum: str
    is_duplicate: bool = False
    available_workflows: List[Dict[str, Any]]


class UploadResponse(BaseModel):
    total_uploaded: int
    files: List[FileUploadItem]
    message: str


class StartAnalysisRequest(BaseModel):
    observation_id: int
    workflow_id: str
    options: Optional[Dict[str, Any]] = None


class AnalysisResultResponse(BaseModel):
    run_id: int
    observation_id: int
    workflow: str
    status: str
    elapsed_seconds: float
    summary: str
    details: Dict[str, Any]


class OpticalPreviewResponse(BaseModel):
    observation_id: int
    image_data_url: str
    slice_name: str
    width: int
    height: int
    min_val: float
    max_val: float
    mean_val: float
    median_val: float
    std_val: float
    nan_count: int
    inf_count: int
    total_pixels: int


# ============================================================
#  Research Web Collector Schemas
# ============================================================

SCIENTIFIC_COLLECTOR_DISCLAIMER = (
    "Metadata collection only. This record does not constitute verification or endorsement "
    "of research methodology, scientific claims, or research novelty."
)


class CollectorSourceInfo(BaseModel):
    name: str
    supported_record_types: List[str]
    is_operational: bool
    requires_credentials: bool
    description: str
    rate_limit_policy: str


class NormalizedResearchRecord(BaseModel):
    record_type: Literal["paper", "dataset"] = "paper"
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    publication_date: Optional[str] = None
    identifier: str  # DOI or unique persistent identifier
    source_name: str
    canonical_url: str
    retrieval_timestamp: datetime = Field(default_factory=datetime.utcnow)
    retrieval_status: str = "COLLECTED"
    raw_metadata: Optional[Dict[str, Any]] = None
    validation_notes: Optional[str] = None
    scientific_disclaimer: str = SCIENTIFIC_COLLECTOR_DISCLAIMER


class CollectorQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=255, description="Search query string or keywords")
    source: str = Field("arXiv", description="Official metadata provider (e.g., 'arXiv')")
    category: Optional[str] = Field("astro-ph", description="Astronomy category/subject filter")
    max_results: int = Field(10, ge=1, le=100, description="Maximum number of records to retrieve")
    save_to_db: bool = Field(True, description="Whether to persist normalized records into database")


class CollectorQueryResponse(BaseModel):
    query: str
    source: str
    total_found: int
    total_returned: int
    total_deduplicated: int
    total_saved: int
    items: List[NormalizedResearchRecord]
    scientific_disclaimer: str = SCIENTIFIC_COLLECTOR_DISCLAIMER
    execution_seconds: float


class ResearchRecordResponse(BaseModel):
    id: int
    record_type: str
    title: str
    authors: List[str]
    abstract: Optional[str]
    publication_date: Optional[date]
    identifier: str
    source_name: str
    canonical_url: str
    retrieval_timestamp: datetime
    retrieval_status: str
    scientific_disclaimer: str = SCIENTIFIC_COLLECTOR_DISCLAIMER

    model_config = ConfigDict(from_attributes=True)


class ResearchRecordListResponse(BaseModel):
    total: int
    items: List[ResearchRecordResponse]
    scientific_disclaimer: str = SCIENTIFIC_COLLECTOR_DISCLAIMER


# ============================================================
#  Literature Extraction Schemas
# ============================================================

FACTS_VS_INFERENCES_NOTE = (
    "All fields are factually extracted and grounded in retrieved source sentences. "
    "Inferred research gaps and speculative automated extrapolations are segregated and omitted."
)


class ExtractedResearchDetails(BaseModel):
    research_problem: str = Field(..., description="Problem or scientific inquiry addressed by paper")
    dataset_name: str = Field(..., description="Name of astronomical dataset/survey/instrument used")
    dataset_type: str = Field(..., description="Category or format of dataset (e.g. timing archive, benchmark)")
    algorithms_or_models: List[str] = Field(default_factory=list, description="Explicitly mentioned models or algorithms")
    feature_types: List[str] = Field(default_factory=list, description="Extracted physical or signal features")
    evaluation_metrics: List[str] = Field(default_factory=list, description="Reported evaluation metrics or benchmarks")
    main_reported_findings: str = Field(..., description="Factual findings or results stated by authors")
    stated_limitations: str = Field(..., description="Author-stated caveats, bounds, or limitations")
    full_text_availability: str = Field(..., description="Availability status (Open Access, arXiv PDF, etc.)")
    licence_or_access_status: str = Field(..., description="License or access conditions")
    source_url: str = Field(..., description="Canonical source URL")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    evidence_locations: Dict[str, str] = Field(default_factory=dict, description="Verbatim text fragments supporting extracted fields")
    is_inferred: bool = Field(False, description="Explicit flag indicating whether fields are factual vs inferred")
    facts_vs_inferences_note: str = Field(default=FACTS_VS_INFERENCES_NOTE)


class ExtractionRequest(BaseModel):
    record_id: Optional[int] = Field(None, description="Existing ResearchRecord ID to extract from")
    title: Optional[str] = Field(None, description="Optional title if extracting directly from text")
    abstract: Optional[str] = Field(None, description="Optional abstract if extracting directly from text")
    identifier: Optional[str] = Field(None, description="Optional identifier/DOI")
    canonical_url: Optional[str] = Field(None, description="Optional canonical URL")
    source_name: Optional[str] = Field("arXiv", description="Source provider name")
    raw_metadata: Optional[Dict[str, Any]] = Field(None, description="Optional raw metadata dictionary")
    save_to_db: bool = Field(True, description="Whether to persist the extracted details")


class PaperExtractionResponse(BaseModel):
    id: Optional[int] = None
    record_id: Optional[int] = None
    identifier: str
    title: str
    extracted_details: ExtractedResearchDetails
    provenance: Dict[str, Any]
    extracted_at: datetime
    scientific_disclaimer: str = SCIENTIFIC_COLLECTOR_DISCLAIMER


# ============================================================
#  Literature Comparison Schemas
# ============================================================

RESEARCH_GAP_DISCLAIMER = (
    "Research gap candidates identify unaddressed dimensions in the currently analyzed literature sample. "
    "Because search coverage is non-exhaustive, these candidates must not be declared novel discoveries "
    "without systematic full-text literature review and human domain verification."
)


class ComparisonTableRow(BaseModel):
    identifier: str
    title: str
    research_problem: str
    data_source_and_mode: str
    dataset_size: str
    algorithm_or_method: str
    input_features_or_signal: str
    evaluation_metrics: str
    main_reported_result: str
    stated_limitations: str
    relevance_to_astra_recoverability: str


class ResearchGapCandidate(BaseModel):
    gap_id: str
    title: str
    description: str
    supporting_paper_identifiers: List[str]
    evidence_context: str
    novelty_claim_status: str = RESEARCH_GAP_DISCLAIMER


class IncomparableSetupDetail(BaseModel):
    conflict_id: str
    dimension: str
    setup_a: str
    setup_b: str
    reason_incomparable: str
    affected_papers: List[str]


class ManualVerificationItem(BaseModel):
    item_id: str
    paper_identifier: str
    title: str
    unresolved_detail: str
    reason_manual_check_needed: str


class LiteratureComparisonRequest(BaseModel):
    record_ids: Optional[List[int]] = Field(None, description="Optional list of specific record IDs to compare. If omitted, compares all available records.")
    include_adhoc_records: Optional[List[ExtractionRequest]] = Field(None, description="Optional adhoc records to include in comparison")
    save_report: bool = Field(True, description="Whether to write report artifacts to reports/literature_comparison.*")


class LiteratureComparisonResponse(BaseModel):
    total_papers_analyzed: int
    comparison_table: List[ComparisonTableRow]
    research_gap_candidates: List[ResearchGapCandidate]
    conflicting_or_incomparable_setups: List[IncomparableSetupDetail]
    manual_verification_required: List[ManualVerificationItem]
    methodological_caveats: str
    scientific_disclaimer: str = SCIENTIFIC_COLLECTOR_DISCLAIMER
    generated_at: datetime
