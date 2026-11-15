# ============================================================
#  ASTRA Cloud — SQLAlchemy ORM Data Models
#  File   : backend/app/models.py
#  Purpose: Mirrors the 5 PostgreSQL tables in astra_cloud:
#           observations, features, predictions,
#           candidate_scores, processing_runs.
# ============================================================

from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    Date,
    Time,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.database import Base


class Observation(Base):
    __tablename__ = "observations"

    id = Column(BigInteger, primary_key=True, index=True)
    file_name = Column(String(255), unique=True, nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    file_type = Column(String(50), nullable=False)
    telescope = Column(String(100), index=True)
    instrument = Column(String(100))
    target_name = Column(String(100), index=True)
    observation_date = Column(Date)
    observation_time = Column(Time)
    ra = Column(String(50))
    dec = Column(String(50))
    ra_deg = Column(Float)
    dec_deg = Column(Float)
    frequency_mhz = Column(Float)
    bandwidth_mhz = Column(Float)
    nchan = Column(Integer)
    nsubint = Column(Integer)
    nbin = Column(Integer)
    observation_mode = Column(String(50))
    data_mode = Column(String(50))
    polarization_info = Column(String(100))
    file_size_mb = Column(Float)
    validation_status = Column(String(50), nullable=False, default="PENDING", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    features = relationship("Feature", back_populates="observation", uselist=False, cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="observation", cascade="all, delete-orphan")
    candidate_scores = relationship("CandidateScore", back_populates="observation", cascade="all, delete-orphan")
    processing_runs = relationship("ProcessingRun", back_populates="observation")


class Feature(Base):
    __tablename__ = "features"

    id = Column(BigInteger, primary_key=True, index=True)
    observation_id = Column(BigInteger, ForeignKey("observations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Pulse profile moments
    profile_mean = Column(Float)
    profile_std = Column(Float)
    profile_skewness = Column(Float)
    profile_kurtosis = Column(Float)
    profile_bins = Column(Integer)
    profile_status = Column(String(50))

    # Dispersion Measure
    dm_nominal = Column(Float)
    dm_mean = Column(Float)
    dm_std = Column(Float)
    dm_skewness = Column(Float)
    dm_kurtosis = Column(Float)
    dm_curve_available = Column(Boolean, nullable=False, default=False)
    dm_status = Column(String(100))

    # Signal Quality & Noise
    signal_mean = Column(Float)
    signal_std = Column(Float)
    noise_estimate = Column(Float)
    dynamic_range = Column(Float)
    valid_fraction = Column(Float)
    nan_fraction = Column(Float)
    inf_fraction = Column(Float)
    quality_status = Column(String(50))

    # RFI analysis
    rfi_indicator = Column(Float)
    rfi_affected_channels = Column(Integer)
    rfi_outlier_channels = Column(Integer)
    rfi_status = Column(String(50))

    # Domain shift diagnostics
    htru2_compatible = Column(Boolean, nullable=False, default=False, index=True)
    domain_shift_flag = Column(String(100))
    out_of_range_feature_count = Column(Integer, default=0)

    extracted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    observation = relationship("Observation", back_populates="features")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(BigInteger, primary_key=True, index=True)
    observation_id = Column(BigInteger, ForeignKey("observations.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    predicted_class = Column(Integer)
    pulsar_probability = Column(Float)
    non_pulsar_probability = Column(Float)
    inference_status = Column(String(50), nullable=False, index=True)
    halt_reason = Column(Text)
    prediction_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("observation_id", "model_name", "model_version", name="uq_obs_model"),
    )

    observation = relationship("Observation", back_populates="predictions")


class CandidateScore(Base):
    __tablename__ = "candidate_scores"

    id = Column(BigInteger, primary_key=True, index=True)
    observation_id = Column(BigInteger, ForeignKey("observations.id", ondelete="CASCADE"), nullable=False, index=True)
    score_version = Column(String(50), nullable=False, default="ACIS_v1.0")

    # Normalized evidence channels
    ml_probability = Column(Float)
    signal_quality = Column(Float)
    rfi_indicator = Column(Float)
    periodicity_evidence = Column(Float)
    dm_evidence = Column(Float)
    profile_evidence = Column(Float)

    # ACIS scoring
    acis_score = Column(Float, nullable=False, index=True)
    evidence_available = Column(String(50), nullable=False)
    score_status = Column(String(50), nullable=False)
    priority_group = Column(String(20), nullable=False, index=True)
    rank_position = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("observation_id", "score_version", name="uq_obs_acis_version"),
        CheckConstraint("priority_group IN ('HIGH', 'MEDIUM', 'LOW')", name="chk_priority_group"),
    )

    observation = relationship("Observation", back_populates="candidate_scores")


class ProcessingRun(Base):
    __tablename__ = "processing_runs"

    id = Column(BigInteger, primary_key=True, index=True)
    observation_id = Column(BigInteger, ForeignKey("observations.id", ondelete="SET NULL"), nullable=True, index=True)
    run_identifier = Column(String(100), nullable=False)
    pipeline_step = Column(String(100), nullable=False)
    pipeline_version = Column(String(50), nullable=False, default="ASTRA_v1.0")
    processing_status = Column(String(50), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True))
    elapsed_seconds = Column(Float)
    error_message = Column(Text)
    log_summary = Column(Text)

    __table_args__ = (
        CheckConstraint(
            "processing_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'HALTED')",
            name="chk_processing_status"
        ),
    )

    observation = relationship("Observation", back_populates="processing_runs")


class ResearchRecord(Base):
    __tablename__ = "research_records"

    id = Column(BigInteger, primary_key=True, index=True)
    record_type = Column(String(50), nullable=False, default="paper", index=True)  # 'paper' or 'dataset'
    title = Column(Text, nullable=False)
    authors = Column(Text)  # JSON-encoded array or comma-separated string
    abstract = Column(Text)
    publication_date = Column(Date)
    identifier = Column(String(255), unique=True, index=True, nullable=False)  # DOI or source ID (e.g. arXiv:2403.xxxxx)
    source_name = Column(String(100), nullable=False, index=True)  # 'arXiv', 'NASA ADS', etc.
    canonical_url = Column(Text, nullable=False)
    retrieval_timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    retrieval_status = Column(String(50), nullable=False, default="COLLECTED", index=True)
    raw_metadata_json = Column(Text)  # Auditable raw metadata as JSON string
    validation_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    extraction = relationship("PaperExtraction", back_populates="record", uselist=False, cascade="all, delete-orphan")


class PaperExtraction(Base):
    __tablename__ = "paper_extractions"

    id = Column(BigInteger, primary_key=True, index=True)
    record_id = Column(BigInteger, ForeignKey("research_records.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)
    identifier = Column(String(255), index=True, nullable=False)
    research_problem = Column(Text, nullable=False)
    dataset_name = Column(String(255), nullable=False)
    dataset_type = Column(String(100), nullable=False)
    algorithms_or_models = Column(Text, nullable=False)  # JSON array
    feature_types = Column(Text, nullable=False)        # JSON array
    evaluation_metrics = Column(Text, nullable=False)   # JSON array
    main_reported_findings = Column(Text, nullable=False)
    stated_limitations = Column(Text, nullable=False)
    full_text_availability = Column(String(100), nullable=False)
    licence_or_access_status = Column(String(100), nullable=False)
    source_url = Column(Text, nullable=False)
    doi = Column(String(255))
    evidence_locations_json = Column(Text, nullable=False)  # JSON dict mapping field -> sentence
    provenance_json = Column(Text, nullable=False)          # JSON dict describing extraction provenance
    extracted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    record = relationship("ResearchRecord", back_populates="extraction")
