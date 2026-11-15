# ASTRA Cloud — Database ETL Column Mapping Specification

**Version:** 1.0 (Phase 3)  
**Target Database:** `astra_cloud` (PostgreSQL 12.4)  
**Primary Source Reports:**
- `reports/radio_master_features.csv`
- `reports/acis_results.csv`
- `reports/candidate_ranking.csv`
- `reports/radio_fits_metadata.csv`
- `reports/radio_predictions.csv`
- `reports/radio_quality.csv`
- `reports/rfi_analysis.csv`
- `reports/dm_features.csv`
- `reports/radio_distribution_check.csv`

---

## 1. Mapping: `observations` Table

| Database Column | Data Type | Nullable? | Source File | Source Column / Transformation | Notes |
|---|---|---|---|---|---|
| `id` | BIGSERIAL | NO (PK) | System | Generated sequence | Auto-increment primary key |
| `file_name` | VARCHAR(255) | NO (UQ) | `radio_master_features.csv` | `file_name` | Unique FITS filename |
| `file_path` | TEXT | NO | Transformation | `'data/radio_fits/' || file_name` | Local repository relative path |
| `file_type` | VARCHAR(50) | NO | Constant | `'PSRFITS_RADIO'` | Verified PSRFITS format |
| `telescope` | VARCHAR(100) | YES | `radio_master_features.csv` | `telescope` | 'GBT' |
| `instrument` | VARCHAR(100) | YES | `radio_fits_metadata.csv` | `instrument` | 'VEGAS' |
| `target_name` | VARCHAR(100) | YES | `radio_master_features.csv` | `target` | 'J1713+0747' |
| `observation_date` | DATE | YES | `radio_master_features.csv` | `observation_date` | YYYY-MM-DD |
| `observation_time` | TIME | YES | `radio_fits_metadata.csv` | `time_obs` | HH:MM:SS.sss |
| `ra` | VARCHAR(50) | YES | Header extraction | `'17:13:49.552'` | Sexagesimal target RA |
| `dec` | VARCHAR(50) | YES | Header extraction | `'+07:47:37.308'` | Sexagesimal target DEC |
| `ra_deg` | DOUBLE PRECISION | YES | None | `NULL` | Left NULL (not computed) |
| `dec_deg` | DOUBLE PRECISION | YES | None | `NULL` | Left NULL (not computed) |
| `frequency_mhz` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `frequency` | 820.0 MHz |
| `bandwidth_mhz` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `bandwidth` | -200.0 or -800.0 MHz |
| `nchan` | INTEGER | YES | `radio_fits_metadata.csv` | `nchan` | 128 channels |
| `nsubint` | INTEGER | YES | `radio_fits_metadata.csv` | `nsubint` | 1 sub-integration |
| `nbin` | INTEGER | YES | `radio_fits_metadata.csv` | `nbin` | 2048 phase bins |
| `observation_mode` | VARCHAR(50) | YES | `radio_fits_metadata.csv` | `observation_mode` | 'PSR' |
| `data_mode` | VARCHAR(50) | YES | `radio_fits_metadata.csv` | `data_mode` | 'fold-mode' |
| `polarization_info` | VARCHAR(100) | YES | `radio_fits_metadata.csv` | `polarization_information` | 'NPOL=4, POL_TYPE=AABBCRCI' |
| `file_size_mb` | DOUBLE PRECISION | YES | `radio_fits_metadata.csv` | `file_size_mb` | File size in MB |
| `validation_status` | VARCHAR(50) | NO | `radio_fits_validation.csv` | `validation_status` | 'VALID_PSRFITS' |
| `created_at` | TIMESTAMPTZ | NO | System | `CURRENT_TIMESTAMP` | Record timestamp |
| `updated_at` | TIMESTAMPTZ | NO | System | `CURRENT_TIMESTAMP` | Record timestamp |

---

## 2. Mapping: `features` Table

| Database Column | Data Type | Nullable? | Source File | Source Column / Transformation | Notes |
|---|---|---|---|---|---|
| `id` | BIGSERIAL | NO (PK) | System | Generated sequence | Auto-increment primary key |
| `observation_id` | BIGINT | NO (FK, UQ) | `observations` | `observations.id` | 1:1 foreign key |
| `profile_mean` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `profile_mean` | Raw integrated baseline count |
| `profile_std` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `profile_std` | Profile standard deviation |
| `profile_skewness` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `profile_skewness` | Profile third moment |
| `profile_kurtosis` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `profile_kurtosis` | Profile fourth moment |
| `profile_bins` | INTEGER | YES | `radio_fits_metadata.csv` | `nbin` | 2048 phase bins |
| `profile_status` | VARCHAR(50) | YES | `pulse_profile_features.csv`| `profile_status` | 'VALID_PROFILE' / 'BLANK_OBSERVATION' |
| `dm_nominal` | DOUBLE PRECISION | YES | `dm_features.csv` | `dm_value` | 15.992196 pc/cm³ |
| `dm_mean` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `NULL` | Sourced 'NOT_AVAILABLE' → NULL |
| `dm_std` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `NULL` | Sourced 'NOT_AVAILABLE' → NULL |
| `dm_skewness` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `NULL` | Sourced 'NOT_AVAILABLE' → NULL |
| `dm_kurtosis` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `NULL` | Sourced 'NOT_AVAILABLE' → NULL |
| `dm_curve_available` | BOOLEAN | NO | `dm_features.csv` | `FALSE` | Trial curve absent in fold mode |
| `dm_status` | VARCHAR(100) | YES | `dm_features.csv` | `dm_status` | 'NOMINAL_DM_PRESENT_NO_TRIAL_CURVE' |
| `signal_mean` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `mean` | Full dynamic spectrum mean |
| `signal_std` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `std` | Full dynamic spectrum std |
| `noise_estimate` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `noise_estimate` | Baseline noise floor |
| `dynamic_range` | DOUBLE PRECISION | YES | `radio_quality.csv` | `dynamic_range` | Dynamic range span |
| `valid_fraction` | DOUBLE PRECISION | YES | `radio_quality.csv` | `valid_fraction` | 1.0 (100% valid samples) |
| `nan_fraction` | DOUBLE PRECISION | YES | `radio_quality.csv` | `nan_fraction` | 0.0 |
| `inf_fraction` | DOUBLE PRECISION | YES | `radio_quality.csv` | `inf_fraction` | 0.0 |
| `quality_status` | VARCHAR(50) | YES | `radio_quality.csv` | `quality_status` | 'VALID' or 'BLANK_OBSERVATION' |
| `rfi_indicator` | DOUBLE PRECISION | YES | `radio_master_features.csv` | `rfi_indicator` | Fraction of affected channels |
| `rfi_affected_channels`| INTEGER | YES | `rfi_analysis.csv` | `affected_channel_count` | Zero-weight / RFI channels |
| `rfi_outlier_channels` | INTEGER | YES | `rfi_analysis.csv` | `affected_time_region_count` | Spectral outlier channels |
| `rfi_status` | VARCHAR(50) | YES | Constant | `'ANALYSIS_COMPLETE'` | RFI status |
| `htru2_compatible` | BOOLEAN | NO | Constant | `FALSE` | All 12 incompatible |
| `domain_shift_flag` | VARCHAR(100) | YES | `radio_distribution_check.csv`| `distribution_warning` | 'HIGH_DOMAIN_SHIFT: ...' |
| `out_of_range_feature_count` | INTEGER | YES | `radio_distribution_check.csv`| `number_of_out_of_range_features` | 6 out-of-range features |
| `extracted_at` | TIMESTAMPTZ | NO | System | `CURRENT_TIMESTAMP` | Record timestamp |

---

## 3. Mapping: `predictions` Table

| Database Column | Data Type | Nullable? | Source File | Source Column / Transformation | Notes |
|---|---|---|---|---|---|
| `id` | BIGSERIAL | NO (PK) | System | Generated sequence | Auto-increment primary key |
| `observation_id` | BIGINT | NO (FK) | `observations` | `observations.id` | Foreign key to observations |
| `model_name` | VARCHAR(100) | NO | Constant | `'RandomForestClassifier'` | Evaluated benchmark model |
| `model_version` | VARCHAR(50) | NO | Constant | `'random_forest_htru2.pkl_v1.0'` | Serialized model artifact |
| `predicted_class` | INTEGER | YES | `radio_predictions.csv` | `NULL` | Inference safely halted |
| `pulsar_probability` | DOUBLE PRECISION | YES | `radio_predictions.csv` | `NULL` | 'NOT_AVAILABLE' → NULL |
| `non_pulsar_probability` | DOUBLE PRECISION | YES | None | `NULL` | 'NOT_AVAILABLE' → NULL |
| `inference_status` | VARCHAR(50) | NO | `radio_predictions.csv` | `prediction` | 'INFERENCE_HALTED' |
| `halt_reason` | TEXT | YES | `radio_distribution_check.csv`| `distribution_warning` | Documented scientific reason |
| `prediction_timestamp` | TIMESTAMPTZ | NO | System | `CURRENT_TIMESTAMP` | Record timestamp |
| `created_at` | TIMESTAMPTZ | NO | System | `CURRENT_TIMESTAMP` | Record timestamp |

---

## 4. Mapping: `candidate_scores` Table

| Database Column | Data Type | Nullable? | Source File | Source Column / Transformation | Notes |
|---|---|---|---|---|---|
| `id` | BIGSERIAL | NO (PK) | System | Generated sequence | Auto-increment primary key |
| `observation_id` | BIGINT | NO (FK) | `observations` | `observations.id` | Foreign key to observations |
| `score_version` | VARCHAR(50) | NO | Constant | `'ACIS_v1.0'` | Scoring model version |
| `ml_probability` | DOUBLE PRECISION | YES | `acis_results.csv` | `NULL` | 'NOT_AVAILABLE' → NULL |
| `signal_quality` | DOUBLE PRECISION | YES | `acis_results.csv` | `signal_quality`::FLOAT | Normalized (1.0 or 0.0) |
| `rfi_indicator` | DOUBLE PRECISION | YES | `acis_results.csv` | `rfi_indicator`::FLOAT | Normalized cleanliness score |
| `periodicity_evidence` | DOUBLE PRECISION | YES | `acis_results.csv` | `periodicity_evidence`::FLOAT | 0.70 (known period) |
| `dm_evidence` | DOUBLE PRECISION | YES | `acis_results.csv` | `dm_evidence`::FLOAT | 0.70 (known DM) |
| `profile_evidence` | DOUBLE PRECISION | YES | `acis_results.csv` | `profile_evidence`::FLOAT | Profile moment proximity |
| `acis_score` | DOUBLE PRECISION | NO | `acis_results.csv` | `acis_score`::FLOAT | Mean=0.8400 (range 0.8176–0.8613) |
| `evidence_available` | VARCHAR(50) | NO | `acis_results.csv` | `evidence_available` | '5/6' (or '3/6' for blank) |
| `score_status` | VARCHAR(50) | NO | `acis_results.csv` | `score_status` | 'PARTIAL_EVIDENCE' |
| `priority_group` | VARCHAR(20) | NO | `candidate_ranking.csv` | `priority_group` | 'HIGH' |
| `rank_position` | INTEGER | YES | `candidate_ranking.csv` | `rank` | 1 to 12 |
| `notes` | TEXT | YES | `candidate_ranking.csv` | `notes` | Standard interpretation note |
| `created_at` | TIMESTAMPTZ | NO | System | `CURRENT_TIMESTAMP` | Record timestamp |

---

## 5. Mapping: `processing_runs` Table

| Database Column | Data Type | Nullable? | Source File | Source Column / Transformation | Notes |
|---|---|---|---|---|---|
| `id` | BIGSERIAL | NO (PK) | System | Generated sequence | Auto-increment primary key |
| `observation_id` | BIGINT | YES (FK) | `observations` | `observations.id` | Associated observation |
| `run_identifier` | VARCHAR(100) | NO | Master Pipeline | `'ASTRA_PIPELINE_RUN_FINAL'` | Scientific pipeline run id |
| `pipeline_step` | VARCHAR(100) | NO | Constant | `'run_astra_pipeline.py (Steps 9-29)'` | Full pipeline execution |
| `pipeline_version` | VARCHAR(50) | NO | Constant | `'ASTRA_v1.0'` | System pipeline version |
| `processing_status` | VARCHAR(50) | NO | Master Pipeline | `'COMPLETED'` | Exit code 0 |
| `started_at` | TIMESTAMPTZ | NO | Pipeline Summary | `'2026-09-24 08:42:27'` | Pipeline execution start |
| `completed_at` | TIMESTAMPTZ | YES | Pipeline Summary | `'2026-09-24 08:42:52'` | Pipeline completion |
| `elapsed_seconds` | DOUBLE PRECISION | YES | Pipeline Summary | `25.1` | Duration |
| `error_message` | TEXT | YES | None | `NULL` | Zero errors logged |
| `log_summary` | TEXT | YES | Pipeline Summary | `'All 20 scientific steps completed successfully'` | Run summary |

---

## 6. Nullability and Data Integrity Guarantee
- No scientific values are invented.
- Columns where features are legitimately unavailable (e.g., `dm_mean`, `predicted_class`, `ml_probability`) are populated as strict SQL `NULL`, maintaining full fidelity with the scientific reports.
- All primary and foreign keys adhere to PostgreSQL referential integrity.
