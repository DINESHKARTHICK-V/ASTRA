# ASTRA Cloud — Database Layer

## 1. Overview and Purpose

The ASTRA Cloud database layer provides a structured, normalized relational store for astronomical observations, scientific features, machine learning inferences, multi-evidence ACIS scores, and processing history.

The database adheres strictly to the **hybrid local architecture** of ASTRA Cloud:
- **Raw astronomical data:** Stored locally in `data/fits/` and `data/radio_fits/`.
- **Database records:** Store paths, metadata, derived features, and scientific evaluations linked to each file.
- **Source of truth:** The existing scientific pipeline (`ml/`) and audit reports remain the foundation. The database acts as a queryable persistent catalog for candidate triage and future API access.

---

## 2. Table Specifications and Entity Relationships

The schema consists of five normalized tables:

```
[ observations ] (1)
       │
       ├── (1:1) ── [ features ]
       │
       ├── (1:N) ── [ predictions ]
       │
       ├── (1:N) ── [ candidate_scores ]
       │
       └── (1:N) ── [ processing_runs ]
```

### Table 1: `observations`
- **Purpose:** Primary catalog of all inspected astronomical observations (both PSRFITS radio archives and optical FITS images).
- **Key Columns:** `id` (PK), `file_name` (UNIQUE), `file_path`, `file_type`, `telescope`, `instrument`, `target_name`, `observation_date`, `observation_time`, `ra`, `dec`, `frequency_mhz`, `bandwidth_mhz`, `nchan`, `nsubint`, `nbin`, `validation_status`.
- **Relationship:** Root parent entity. All other tables reference `observations.id`.

### Table 2: `features`
- **Purpose:** Stores actual physical and statistical features extracted from observations by the ASTRA scientific pipeline.
- **Key Columns:** `id` (PK), `observation_id` (FK, UNIQUE), `profile_mean`, `profile_std`, `profile_skewness`, `profile_kurtosis`, `profile_bins`, `dm_nominal`, `dm_mean`, `dm_std`, `dm_skewness`, `dm_kurtosis`, `dm_curve_available`, `signal_mean`, `signal_std`, `noise_estimate`, `dynamic_range`, `valid_fraction`, `rfi_indicator`, `rfi_affected_channels`, `htru2_compatible`, `domain_shift_flag`.
- **Relationship:** Strict 1:1 relationship with `observations`. Deleting an observation cascades to its features.

### Table 3: `predictions`
- **Purpose:** Records ML classifier inferences, predicted classes, posterior probabilities, and safe-inference halt reasons.
- **Key Columns:** `id` (PK), `observation_id` (FK), `model_name`, `model_version`, `predicted_class` (0, 1, or NULL if halted), `pulsar_probability`, `non_pulsar_probability`, `inference_status`, `halt_reason`, `prediction_timestamp`.
- **Relationship:** 1:N with `observations`. Supports multi-model benchmarking (e.g., comparing RF, XGBoost, SVM) and version tracking (`uq_obs_model` constraint).

### Table 4: `candidate_scores`
- **Purpose:** Stores the multi-evidence ASTRA Candidate Intelligence Score (ACIS) and prioritization triage labels.
- **Key Columns:** `id` (PK), `observation_id` (FK), `score_version`, `ml_probability`, `signal_quality`, `rfi_indicator`, `periodicity_evidence`, `dm_evidence`, `profile_evidence`, `acis_score`, `evidence_available`, `score_status`, `priority_group` ('HIGH', 'MEDIUM', 'LOW'), `rank_position`, `notes`.
- **Relationship:** 1:N with `observations` (allows versioned scoring revisions).

### Table 5: `processing_runs`
- **Purpose:** Lifecycle audit tracking for every step executed on an observation.
- **Key Columns:** `id` (PK), `observation_id` (FK, nullable), `run_identifier`, `pipeline_step`, `pipeline_version`, `processing_status` ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'HALTED'), `started_at`, `completed_at`, `elapsed_seconds`, `error_message`, `log_summary`.
- **Relationship:** Audit log referencing `observations`. `ON DELETE SET NULL` preserves execution logs if an observation record is archived.

---

## 3. Database Creation and Setup Instructions

### Prerequisites
- PostgreSQL 12 or newer installed and running on port 5432.
- The PostgreSQL client tool (`psql`) accessible via command line.

### Step 1: Create Database
Connect to PostgreSQL and create the dedicated `astra_cloud` database:

```bash
psql -h localhost -p 5432 -U openpg -d postgres -c "CREATE DATABASE astra_cloud WITH ENCODING='UTF8';"
```

### Step 2: Apply the DDL Schema
Execute the schema file against `astra_cloud`:

```bash
psql -h localhost -p 5432 -U openpg -d astra_cloud -f backend/database/schema.sql
```

### Step 3: Verify Table Creation
Inspect the created relations:

```bash
psql -h localhost -p 5432 -U openpg -d astra_cloud -c "\dt"
```

Expected relations:
- `candidate_scores`
- `features`
- `observations`
- `predictions`
- `processing_runs`

---

## 4. Ingestion / ETL Operations (`backend/database/ingest.py`)

### 4.1 Environment Variables
Database connection parameters are read from environment variables (fallback to defaults if unset):

```bash
# Optional: override database connection parameters
export ASTRA_DB_HOST="localhost"
export ASTRA_DB_PORT="5432"
export ASTRA_DB_NAME="astra_cloud"
export ASTRA_DB_USER="openpg"
export ASTRA_DB_PASSWORD="your_password"
```

*Note: Passwords are never hardcoded or printed to stdout.*

### 4.2 Dry-Run Mode (Validation Only)
To test mapping validity, inspect data types, and check record counts without making any database changes:

```bash
python backend/database/ingest.py --dry-run
```

Expected output confirms all 10 source reports are verified, mappings are valid, and 12 rows per table are queued for insertion.

### 4.3 Live Ingestion
To populate the database from the validated reports:

```bash
python backend/database/ingest.py
```

This ingests:
- 12 rows into `observations`
- 12 rows into `features`
- 12 rows into `predictions`
- 12 rows into `candidate_scores`
- 12 rows into `processing_runs`

### 4.4 Idempotency & Safe Re-Running
The ingestion script is **fully idempotent**. Running it multiple times:
```bash
python backend/database/ingest.py
python backend/database/ingest.py
```
Will **NOT** create duplicate rows. It performs `ON CONFLICT DO UPDATE` using PostgreSQL unique constraints:
- `observations.file_name` (UNIQUE)
- `features.observation_id` (UNIQUE)
- `predictions.(observation_id, model_name, model_version)` (UNIQUE)
- `candidate_scores.(observation_id, score_version)` (UNIQUE)
- `processing_runs.run_identifier` (deterministic key matching)

Total table counts remain strictly 12 rows per table.

### 4.5 Post-Ingestion Validation Queries
Verify row counts and foreign-key integrity using `psql`:

```sql
-- Check table row counts (each must equal 12)
SELECT
  (SELECT count(*) FROM observations)     AS obs_count,
  (SELECT count(*) FROM features)         AS feat_count,
  (SELECT count(*) FROM predictions)      AS pred_count,
  (SELECT count(*) FROM candidate_scores) AS score_count,
  (SELECT count(*) FROM processing_runs)  AS run_count;

-- Check for orphan records (must return 0 for all)
SELECT count(*) FROM features f LEFT JOIN observations o ON f.observation_id = o.id WHERE o.id IS NULL;
SELECT count(*) FROM predictions p LEFT JOIN observations o ON p.observation_id = o.id WHERE o.id IS NULL;
SELECT count(*) FROM candidate_scores cs LEFT JOIN observations o ON cs.observation_id = o.id WHERE o.id IS NULL;
```

---

## 5. Local FITS Files vs Database Records

1. **Decoupled Architecture:** FITS files are large binary datasets (typically several megabytes to gigabytes). They are preserved untouched in their native filesystem directory:
   - `data/radio_fits/*.fits` (PSRFITS pulsar timing archives)
   - `data/fits/*.fits` (HST optical FITS images)
2. **Metadata Reference:** The `observations.file_path` column stores the relative repository path to each FITS file.
3. **Reproducibility Guarantee:** Any database record can be mapped directly back to its source FITS header and HDU tables using `astropy.io.fits`.
4. **No Data Fabrication:** Database tables are populated only from validated scientific scripts and audit reports. Fake scientific values are never inserted.
