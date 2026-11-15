-- =====================================================================
--  ASTRA Cloud — PostgreSQL Normalized Database Schema
--  Version : 1.0 (Phase 2)
--  Purpose : Stores observation metadata, extracted scientific features,
--            model predictions, multi-evidence ACIS scores, candidate rankings,
--            and end-to-end processing execution history.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. OBSERVATIONS TABLE (Step 46)
--    Stores physical observation and FITS file metadata.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS observations (
    id                  BIGSERIAL PRIMARY KEY,
    file_name           VARCHAR(255) NOT NULL UNIQUE,
    file_path           TEXT NOT NULL,
    file_type           VARCHAR(50) NOT NULL, -- 'PSRFITS_RADIO', 'FITS_IMAGE_OPTICAL', etc.
    telescope           VARCHAR(100),
    instrument          VARCHAR(100),
    target_name         VARCHAR(100),
    observation_date    DATE,
    observation_time    TIME,
    ra                  VARCHAR(50),
    dec                 VARCHAR(50),
    ra_deg              DOUBLE PRECISION,
    dec_deg             DOUBLE PRECISION,
    frequency_mhz       DOUBLE PRECISION,
    bandwidth_mhz       DOUBLE PRECISION,
    nchan               INTEGER,
    nsubint             INTEGER,
    nbin                INTEGER,
    observation_mode    VARCHAR(50),  -- e.g. 'PSR'
    data_mode           VARCHAR(50),  -- e.g. 'fold-mode'
    polarization_info   VARCHAR(100), -- e.g. 'NPOL=4, POL_TYPE=AABBCRCI'
    file_size_mb        DOUBLE PRECISION,
    validation_status   VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- 'VALID_PSRFITS', 'VALID_IMAGE', etc.
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- 2. FEATURES TABLE (Step 47)
--    Stores actual scientific features extracted by ASTRA pipeline.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS features (
    id                          BIGSERIAL PRIMARY KEY,
    observation_id              BIGINT NOT NULL UNIQUE REFERENCES observations(id) ON DELETE CASCADE,
    
    -- Pulse profile moments (Stokes I integrated profile)
    profile_mean                DOUBLE PRECISION,
    profile_std                 DOUBLE PRECISION,
    profile_skewness            DOUBLE PRECISION,
    profile_kurtosis            DOUBLE PRECISION,
    profile_bins                INTEGER,
    profile_status              VARCHAR(50),
    
    -- Dispersion Measure (DM) features
    dm_nominal                  DOUBLE PRECISION,
    dm_mean                     DOUBLE PRECISION,
    dm_std                      DOUBLE PRECISION,
    dm_skewness                 DOUBLE PRECISION,
    dm_kurtosis                 DOUBLE PRECISION,
    dm_curve_available          BOOLEAN NOT NULL DEFAULT FALSE,
    dm_status                   VARCHAR(100),
    
    -- Signal quality & statistical noise floor
    signal_mean                 DOUBLE PRECISION,
    signal_std                  DOUBLE PRECISION,
    noise_estimate              DOUBLE PRECISION,
    dynamic_range               DOUBLE PRECISION,
    valid_fraction              DOUBLE PRECISION,
    nan_fraction                DOUBLE PRECISION,
    inf_fraction                DOUBLE PRECISION,
    quality_status              VARCHAR(50),
    
    -- Radio Frequency Interference (RFI) analysis
    rfi_indicator               DOUBLE PRECISION,
    rfi_affected_channels       INTEGER,
    rfi_outlier_channels        INTEGER,
    rfi_status                  VARCHAR(50),
    
    -- Benchmark compatibility & domain shift diagnostics
    htru2_compatible            BOOLEAN NOT NULL DEFAULT FALSE,
    domain_shift_flag           VARCHAR(100),
    out_of_range_feature_count  INTEGER DEFAULT 0,
    
    extracted_at                TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- 3. PREDICTIONS TABLE (Step 48)
--    Stores machine learning inference results and confidence scores.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id                      BIGSERIAL PRIMARY KEY,
    observation_id          BIGINT NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    model_name              VARCHAR(100) NOT NULL,
    model_version           VARCHAR(50) NOT NULL,
    predicted_class         INTEGER, -- 0 for non-pulsar, 1 for pulsar, NULL if halted
    pulsar_probability      DOUBLE PRECISION,
    non_pulsar_probability  DOUBLE PRECISION,
    inference_status        VARCHAR(50) NOT NULL, -- 'COMPLETED', 'INFERENCE_HALTED', etc.
    halt_reason             TEXT,
    prediction_timestamp    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_obs_model UNIQUE (observation_id, model_name, model_version)
);

-- ---------------------------------------------------------------------
-- 4. CANDIDATE_SCORES TABLE (Step 49)
--    Stores ACIS (ASTRA Candidate Intelligence Score) multi-evidence output.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidate_scores (
    id                      BIGSERIAL PRIMARY KEY,
    observation_id          BIGINT NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    score_version           VARCHAR(50) NOT NULL DEFAULT 'ACIS_v1.0',
    
    -- Multi-evidence normalized input channels
    ml_probability          DOUBLE PRECISION,
    signal_quality          DOUBLE PRECISION,
    rfi_indicator           DOUBLE PRECISION,
    periodicity_evidence    DOUBLE PRECISION,
    dm_evidence             DOUBLE PRECISION,
    profile_evidence        DOUBLE PRECISION,
    
    -- ACIS computed score & triage classification
    acis_score              DOUBLE PRECISION NOT NULL,
    evidence_available      VARCHAR(50) NOT NULL, -- e.g. '5/6'
    score_status            VARCHAR(50) NOT NULL, -- e.g. 'PARTIAL_EVIDENCE'
    priority_group          VARCHAR(20) NOT NULL CHECK (priority_group IN ('HIGH', 'MEDIUM', 'LOW')),
    rank_position           INTEGER,
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_obs_acis_version UNIQUE (observation_id, score_version)
);

-- ---------------------------------------------------------------------
-- 5. PROCESSING_RUNS TABLE (Step 50)
--    Tracks pipeline execution runs and lifecycle status.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS processing_runs (
    id                  BIGSERIAL PRIMARY KEY,
    observation_id      BIGINT REFERENCES observations(id) ON DELETE SET NULL,
    run_identifier      VARCHAR(100) NOT NULL,
    pipeline_step       VARCHAR(100) NOT NULL,
    pipeline_version    VARCHAR(50) NOT NULL DEFAULT 'ASTRA_v1.0',
    processing_status   VARCHAR(50) NOT NULL CHECK (processing_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'HALTED')),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMPTZ,
    elapsed_seconds     DOUBLE PRECISION,
    error_message       TEXT,
    log_summary         TEXT
);

-- ---------------------------------------------------------------------
-- INDEXES FOR PERFORMANCE & FAST LOOKUP
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_obs_file_name ON observations(file_name);
CREATE INDEX IF NOT EXISTS idx_obs_target_name ON observations(target_name);
CREATE INDEX IF NOT EXISTS idx_obs_telescope ON observations(telescope);
CREATE INDEX IF NOT EXISTS idx_obs_val_status ON observations(validation_status);

CREATE INDEX IF NOT EXISTS idx_feat_obs_id ON features(observation_id);
CREATE INDEX IF NOT EXISTS idx_feat_htru2_compat ON features(htru2_compatible);

CREATE INDEX IF NOT EXISTS idx_pred_obs_id ON predictions(observation_id);
CREATE INDEX IF NOT EXISTS idx_pred_model ON predictions(model_name, model_version);
CREATE INDEX IF NOT EXISTS idx_pred_status ON predictions(inference_status);

CREATE INDEX IF NOT EXISTS idx_scores_obs_id ON candidate_scores(observation_id);
CREATE INDEX IF NOT EXISTS idx_scores_acis ON candidate_scores(acis_score DESC);
CREATE INDEX IF NOT EXISTS idx_scores_priority ON candidate_scores(priority_group);

CREATE INDEX IF NOT EXISTS idx_runs_obs_id ON processing_runs(observation_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON processing_runs(processing_status);
CREATE INDEX IF NOT EXISTS idx_runs_started ON processing_runs(started_at);

-- ---------------------------------------------------------------------
-- 6. RESEARCH RECORDS TABLE (Research Web Collector)
--    Stores normalized metadata for astronomy literature and datasets.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS research_records (
    id                  BIGSERIAL PRIMARY KEY,
    record_type         VARCHAR(50) NOT NULL DEFAULT 'paper',
    title               TEXT NOT NULL,
    authors             TEXT,
    abstract            TEXT,
    publication_date    DATE,
    identifier          VARCHAR(255) NOT NULL UNIQUE,
    source_name         VARCHAR(100) NOT NULL,
    canonical_url       TEXT NOT NULL,
    retrieval_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    retrieval_status    VARCHAR(50) NOT NULL DEFAULT 'COLLECTED',
    raw_metadata_json   TEXT,
    validation_notes    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_research_identifier ON research_records(identifier);
CREATE INDEX IF NOT EXISTS idx_research_source ON research_records(source_name);
CREATE INDEX IF NOT EXISTS idx_research_record_type ON research_records(record_type);
CREATE INDEX IF NOT EXISTS idx_research_status ON research_records(retrieval_status);
CREATE INDEX IF NOT EXISTS idx_research_retrieval_time ON research_records(retrieval_timestamp);

-- ---------------------------------------------------------------------
-- 7. PAPER EXTRACTIONS TABLE (Research Literature Extraction Layer)
--    Stores factually grounded extracted research details from papers.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paper_extractions (
    id                          BIGSERIAL PRIMARY KEY,
    record_id                   BIGINT UNIQUE REFERENCES research_records(id) ON DELETE CASCADE,
    identifier                  VARCHAR(255) NOT NULL,
    research_problem            TEXT NOT NULL,
    dataset_name                VARCHAR(255) NOT NULL,
    dataset_type                VARCHAR(100) NOT NULL,
    algorithms_or_models        TEXT NOT NULL, -- JSON array
    feature_types               TEXT NOT NULL, -- JSON array
    evaluation_metrics          TEXT NOT NULL, -- JSON array
    main_reported_findings      TEXT NOT NULL,
    stated_limitations          TEXT NOT NULL,
    full_text_availability      VARCHAR(100) NOT NULL,
    licence_or_access_status    VARCHAR(100) NOT NULL,
    source_url                  TEXT NOT NULL,
    doi                         VARCHAR(255),
    evidence_locations_json     TEXT NOT NULL, -- JSON dictionary
    provenance_json             TEXT NOT NULL, -- JSON dictionary
    extracted_at                TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_extraction_record_id ON paper_extractions(record_id);
CREATE INDEX IF NOT EXISTS idx_extraction_identifier ON paper_extractions(identifier);
CREATE INDEX IF NOT EXISTS idx_extraction_extracted_at ON paper_extractions(extracted_at);
