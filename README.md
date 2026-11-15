# ASTRA Cloud

**AI-Assisted Radio Pulsar Candidate Analysis and Prioritization**  
*MSc Computer Science Research Project*

---

## 1. Project Title

**ASTRA Cloud** — AI-Assisted Radio Pulsar Candidate Analysis System

---

## 2. Project Objective

ASTRA Cloud aims to develop an AI-assisted pipeline for analysing real radio telescope observations of pulsar candidates, benchmarking machine learning classifiers on a standard pulsar dataset, and proposing a multi-evidence candidate prioritization score when direct ML inference is not applicable due to data format constraints.

ASTRA is designed as an **analysis and candidate-prioritization layer** to assist radio astronomers. It does **not** replace established pulsar detection pipelines (e.g., PRESTO, SIGPROC, PEASOUP), nor does it autonomously confirm pulsar discoveries.

---

## 3. Problem Statement

Pulsar candidate triage is a challenging task in radio astronomy. Modern surveys produce large numbers of candidates, most of which are radio frequency interference (RFI) or noise. Machine learning classifiers trained on labelled benchmark datasets (e.g., HTRU2) are effective for search-mode candidates, but face a fundamental structural incompatibility when applied to folded timing archive data (PSRFITS format), which lacks the multi-trial DM-SNR curve features required by search-mode classifiers.

This project investigates:
1. How well ML classifiers trained on the HTRU2 benchmark perform.
2. What happens when those classifiers are applied to real folded PSRFITS observations.
3. Whether a multi-evidence scoring approach (ACIS) can provide useful candidate prioritization when direct ML inference is not possible.

---

## 4. Dataset Description

### 4.1 HTRU2 Dataset

| Property | Value |
|---|---|
| Source | Lyon et al. (2016), High Time Resolution Universe survey |
| Total samples | 17,898 |
| Class 0 (non-pulsar) | 16,259 (90.8%) |
| Class 1 (pulsar) | 1,639 (9.2%) |
| Input features | 8 (Profile: mean, std, skewness, kurtosis; DM-SNR: mean, std, skewness, kurtosis) |
| Training split | 12,528 (70%, stratified, `random_state=42`) |
| Testing split | 5,370 (30%, stratified, `random_state=42`) |
| File | `data/htru2/HTRU_2.csv` |

### 4.2 Real Radio FITS Dataset

| Property | Value |
|---|---|
| Source | NANOGrav / Zenodo (Jennings et al. 2022) |
| Telescope | Green Bank Telescope (GBT), VEGAS backend |
| Target | PSR J1713+0747 (millisecond pulsar) |
| Frequency | 820 MHz |
| Format | PSRFITS (folded timing archives) |
| Files collected | 12 |
| Observation dates | 2019–2022 |
| File location | `data/radio_fits/` |

---

## 5. System Workflow

```
HTRU2 Dataset (17,898 samples)
    ↓
ML Training (Random Forest, XGBoost, SVM, MLP)
    ↓
Model Evaluation (accuracy, precision, recall, F1, ROC-AUC)
    ↓
SHAP Feature Importance Analysis
    ↓
Real Radio FITS (12 GBT/VEGAS observations)
    ↓
FITS Validation → Metadata Extraction → Data Analysis
    ↓
Signal Quality → RFI Analysis → Pulse Profile → DM Analysis
    ↓
Feature Extraction → Compatibility Check → Distribution Check
    ↓
[IF COMPATIBLE] → Random Forest Inference → SHAP Explanation
[IF INCOMPATIBLE] → Inference Safely Halted (documented)
    ↓
Candidate Evidence Collection (6 evidence channels)
    ↓
ACIS Scoring (multi-evidence prioritization)
    ↓
Candidate Ranking (HIGH / MEDIUM / LOW priority)
    ↓
Final Reports and Audit
```

---

## 6. ML Models

Four classifiers were trained on the HTRU2 dataset:

| Model | Configuration |
|---|---|
| Random Forest | 200 estimators, `random_state=42`, `n_jobs=-1` |
| XGBoost | 200 estimators, `learning_rate=0.1`, `max_depth=6` |
| SVM | RBF kernel, `C=1.0`, `CalibratedClassifierCV` |
| MLP | Layers: (128, 64), ReLU, early stopping |

The Random Forest model is saved to `models/random_forest_htru2.pkl` and used in the inference pipeline.

---

## 7. Model Evaluation

All models evaluated on HTRU2 test set (n = 5,370, stratified 30% split):

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| **Random Forest** | **0.9810** | 0.9333 | 0.8537 | 0.8917 | 0.9694 |
| XGBoost | 0.9799 | 0.9192 | 0.8557 | 0.8863 | 0.9769 |
| SVM | 0.9801 | **0.9594** | 0.8171 | 0.8825 | 0.9572 |
| MLP | 0.9804 | 0.9448 | **0.8557** | 0.8867 | **0.9781** |

**Random Forest Confusion Matrix:**

|  | Predicted 0 | Predicted 1 |
|---|---|---|
| **Actual 0** | 4,848 (TN) | 30 (FP) |
| **Actual 1** | 72 (FN) | 420 (TP) |

---

## 8. FITS Processing

The FITS processing pipeline (Steps 9–18) covers:

- **Validation:** PSRFITS format integrity check using Astropy
- **Metadata extraction:** Telescope, target, date, frequency, bandwidth, polarization
- **Data structure analysis:** HDU inventory, sub-integration and channel counts
- **Quality assessment:** Valid fraction, noise floor, blank frame detection
- **Dynamic spectrum visualization:** Per-file frequency-time plots

---

## 9. Feature Extraction

Features extracted from real radio PSRFITS files:

| Feature | Source | HTRU2 Compatible? |
|---|---|---|
| Profile Mean | Integrated Stokes I profile | ⚠️ Scale mismatch (ADU vs normalised) |
| Profile Std | Integrated profile | ⚠️ Scale mismatch |
| Profile Skewness | Integrated profile | ✅ Partially compatible |
| Profile Kurtosis | Integrated profile | ✅ Partially compatible |
| DM_Mean | DM-SNR trial curve | ❌ Unavailable in folded archives |
| DM_Std | DM-SNR trial curve | ❌ Unavailable in folded archives |
| DM_Skewness | DM-SNR trial curve | ❌ Unavailable in folded archives |
| DM_Kurtosis | DM-SNR trial curve | ❌ Unavailable in folded archives |

**Finding:** All 12 real radio files were flagged as `HIGH_DOMAIN_SHIFT` and rejected from ML inference.

---

## 10. SHAP Analysis

SHAP (SHapley Additive exPlanations) was applied to the Random Forest to identify which of the 8 features contribute most to pulsar vs non-pulsar predictions on the HTRU2 test set. Output: `reports/shap_summary.png`.

For real radio observations, SHAP was not computable because ML inference was halted (no predictions to explain). The halted status is documented in `reports/radio_shap_summary.csv`.

---

## 11. ACIS — ASTRA Candidate Intelligence Score

ACIS is a **project-proposed** multi-evidence candidate prioritization score.

> **Disclaimer:** ACIS is not an established astronomy algorithm. It requires experimental validation. No claim of global novelty is made.

**Evidence channels and default weights:**

| Channel | Weight | Description |
|---|---|---|
| ML Probability | 0.35 | Random Forest score (when available) |
| Signal Quality | 0.20 | Data quality status |
| RFI Indicator | 0.15 | Fraction of clean channels |
| Periodicity Evidence | 0.10 | Known ephemeris period |
| DM Evidence | 0.10 | Known DM value consistency |
| Profile Evidence | 0.10 | Pulse profile shape statistics |

When a channel is unavailable, its weight is redistributed proportionally. Missing values are never imputed as 0 or 1.

---

## 12. Candidate Ranking

Candidates are ranked by ACIS score and assigned priority groups:

| Priority | ACIS Range | Meaning |
|---|---|---|
| HIGH | ≥ 0.65 | Recommended for earlier human inspection |
| MEDIUM | 0.40 – 0.65 | Moderate evidence |
| LOW | < 0.40 | Limited evidence |

**Result for this dataset:** All 12 observations received HIGH priority (ACIS range: 0.8176 – 0.8613), consistent with all observations being confirmed timing archives of a known pulsar.

---

## 13. Results Summary

| Component | Result |
|---|---|
| HTRU2 best model | Random Forest (Accuracy: 0.981, ROC-AUC: 0.9694) |
| HTRU2 test set size | 5,370 samples |
| Radio files collected | 12 |
| Radio files compatible with HTRU2 ML model | 0 |
| ML inference produced | 0 predictions (safely halted) |
| ACIS scores produced | 12 |
| HIGH priority candidates | 12 |

---

## 14. Limitations

Key limitations of this project:

1. The HTRU2-trained model cannot be applied to folded PSRFITS archives due to structural feature incompatibility.
2. Class imbalance in HTRU2 (9.9:1) means the model misses ~14.6% of real pulsars in the test set.
3. All real radio observations target a single known pulsar (PSR J1713+0747) — non-pulsar performance cannot be evaluated.
4. ACIS weights are not empirically optimised and require validation on labelled real-radio data.
5. ASTRA does not replace expert astronomer review.

See [`reports/project_limitations.md`](reports/project_limitations.md) for full details.

---

## 15. Project Structure

```
ASTRA CLOUD/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint (10 endpoints)
│   │   ├── database.py              # PostgreSQL SQLAlchemy engine & connection pool
│   │   ├── models.py                # 5 normalized SQLAlchemy ORM models
│   │   ├── schemas.py               # Pydantic v2 schemas
│   │   ├── routers/                 # Observations, Features, Candidates routers
│   │   └── services/
│   │       └── report_service.py    # ReportLab publication-grade PDF generator
│   ├── database/
│   │   ├── schema.sql               # PostgreSQL DDL schema definition
│   │   └── ingest.py                # Idempotent ETL ingestion engine
│   ├── tests/
│   │   └── test_api.py              # Comprehensive pytest endpoint test suite (21/21 passing)
│   ├── requirements.txt             # Backend Python dependencies (FastAPI, ReportLab, etc.)
│   └── README.md                    # Backend architecture manual
├── frontend/
│   ├── src/
│   │   ├── pages/                   # Dashboard, Candidates, ObservationDetail, ProcessingMonitor
│   │   ├── components/              # Navbar, StatusBadge, LoadingSpinner, ErrorMessage
│   │   ├── services/api.ts          # Centralized typed REST client
│   │   └── types/api.ts             # TypeScript interface definitions
│   ├── vite.config.ts               # Vite configuration (port 3000, host 127.0.0.1)
│   ├── package.json                 # React 18, Vite 5, TypeScript 5 dependencies
│   └── README.md                    # Frontend manual
├── data/
│   ├── htru2/          HTRU_2.csv (17,898 benchmark samples)
│   ├── fits/           HST/WFPC2 optical FITS (isolated reference)
│   └── radio_fits/     12 GBT/VEGAS PSRFITS observations (PSR J1713+0747)
├── models/
│   ├── random_forest_htru2.pkl   Main RF model (Accuracy: 98.10%, ROC-AUC: 0.9694)
│   ├── htru2_features.pkl        Feature name list
│   ├── random_forest.joblib      RF model
│   ├── xgboost.joblib
│   ├── svm.joblib
│   ├── mlp.joblib
│   └── scaler.joblib
├── ml/                 All Python pipeline scripts (Steps 1–42)
├── reports/            All output reports, CSVs, plots, validation logs
└── README.md
```

---

## 16. How to Run the Complete Platform

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm 9+
- PostgreSQL 12+ running on `localhost:5432` with database `astra_cloud`

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### Step 2: Ingest Scientific Data into PostgreSQL (Phase 3 ETL)
```bash
python backend/database/ingest.py
```

### Step 3: Run Backend Tests
```bash
python -m pytest backend/tests/ -v
```
*(All 33 tests pass, verifying endpoints, uploads, workflows, optical previews, PDF generation, and database row immutability).*

### Step 4: Start the FastAPI Backend (Port 8000)
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
- Interactive API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check Heartbeat: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Step 5: Start the React Frontend Dashboard (Port 3000)
```bash
cd frontend
npm install
npm run dev
```
- Open Browser Dashboard: [http://127.0.0.1:3000](http://127.0.0.1:3000)
- Production Build Verification: `npm run build` (0 TypeScript errors)

### Step 6: Reproducing Core Scientific Experiments (Steps 1–42)
```bash
python ml/train_pipeline.py
python ml/evaluate_models.py
python ml/shap_analysis.py
python ml/run_astra_pipeline.py
python ml/final_dataset_audit.py
python ml/final_model_audit.py
python ml/reproducibility_test.py
python ml/acis_audit.py
```

---

## 17. UI/UX Redesign & Multi-Type FITS Ingestion (Safe Enhancement Phase)

The application includes an upgraded scientific user interface with multi-type FITS support:
1. **Multi-Type FITS Support:** Ingests both Radio astronomy PSRFITS archives (.fits, .sf) and Optical astronomy FITS images/cubes (.fits, .fit, .fts, .fits.gz).
2. **Safe Ingestion & Deduplication:** Drag-and-drop multi-file upload with custom observation names, chunked streaming to `data/uploads/`, and SHA-256 duplicate checking.
3. **User-Selected Scientific Workflows:** Analysis workflows are chosen after file ingestion. Optical data workflows (preview, statistics, HDUs, tables) remain strictly separated from radio workflows (signal moments, ML inference, ACIS).
4. **Permanent Navigation Sidebar:** 8 dedicated sections: Overview, Add Data, Observations, High Priority, Medium Priority, Low Priority, Reports, and System Status.
5. **Observation Detail Suite:** 7 structured tabs (Overview, Metadata, Data Preview, Analysis Results, Quality, History, Reports) with collapsible scientific halt explanations and live 2D optical preview rendering.
6. **Scientific Safeguards Intact:** Database row counts, ACIS thresholds, HTRU2 benchmark models, and inference halt rules remain strictly preserved.

---

## Acknowledgements

- HTRU2 dataset: Lyon et al. (2016)
- GBT/VEGAS PSRFITS data: NANOGrav Collaboration / Jennings et al. (2022) via Zenodo
- Machine learning: scikit-learn, XGBoost
- Astronomy data processing: Astropy
- Explainability: SHAP (Lundberg & Lee, 2017)
