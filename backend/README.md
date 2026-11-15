# ASTRA Cloud — Backend API & Database Service

**Component:** FastAPI REST Backend  
**Version:** 1.0.0 (API Contract Compatible)  
**Database:** PostgreSQL 12.4 (`astra_cloud`)  
**Storage Architecture:** Local FITS Archives (`data/radio_fits/`, `data/fits/`, `data/uploads/`) + Normalized Relational Database  

---

## 1. Overview and Architecture

The ASTRA Cloud backend provides a high-performance REST API layer built on **FastAPI**, **SQLAlchemy**, and **PostgreSQL**. It serves verified observational metadata, extracted scientific features, machine learning inference statuses, and ASTRA Candidate Intelligence Score (ACIS) multi-evidence prioritization rankings directly to astronomers and client applications.

### Core Principles & Scientific Safeguards
1. **Source of Truth:** All data originates from validated scientific pipelines and safe local storage.
2. **Multi-Type FITS Support:** Seamlessly ingests both Radio astronomy PSRFITS archives and Optical astronomy FITS images/cubes using `astropy`.
3. **Scientific Boundary Enforcement:** Optical images cannot be classified as radio pulsars or assigned ACIS scores. Attempting to run radio pulsar workflows on optical files returns HTTP 400 with a clear scientific refusal.
4. **Safe Stop Preservation:** When required search-mode DM-SNR trial curves are structurally absent, machine learning inference is halted (`INFERENCE_HALTED`) rather than fabricating synthetic data.
5. **Decoupled Local Binary Storage:** FITS binaries are streamed to disk in `data/uploads/` (max 200MB, chunked). Only metadata and results are stored in PostgreSQL.

---

## 2. Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── database.py              # Database engine, connection pooling, health checker
│   ├── models.py                # SQLAlchemy ORM models (5 normalized tables)
│   ├── schemas.py               # Pydantic serialization & request/response schemas
│   ├── main.py                  # FastAPI application entrypoint, CORS, router mounts
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── observations.py      # /api/observations endpoints, previews, & PDF reports
│   │   ├── features_predictions.py # /api/observations/{id}/features & predictions
│   │   ├── candidates.py        # /api/candidates (ACIS) & /api/processing-runs
│   │   ├── upload.py            # /api/upload (multi-file streaming, deduplication)
│   │   └── analysis.py          # /api/analysis/start (user-selected workflow dispatch)
│   └── services/
│       ├── __init__.py
│       ├── fits_service.py      # Astropy inspection, type detection, optical preview, analysis
│       └── report_service.py    # ReportLab dual-mode (radio & optical) PDF generator
├── database/
│   ├── schema.sql               # PostgreSQL DDL schema definition
│   ├── ingest.py                # Idempotent ETL ingestion engine
│   ├── etl_mapping.md           # Column mapping documentation
│   └── README.md                # Database layer technical manual
├── tests/
│   ├── __init__.py
│   ├── test_api.py              # Baseline pytest endpoint test suite (21/21 passing)
│   └── test_upload_analysis.py  # Upload, analysis, and optical preview test suite (12/12 passing)
├── .env.example                 # Environment configuration template
├── requirements.txt             # Backend Python dependencies
└── README.md                    # This document
```

---

## 3. Endpoints Directory

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service root information and route catalog |
| `GET` | `/health` | Live PostgreSQL connectivity check |
| `POST` | `/api/upload` | Multipart multi-file FITS upload with SHA-256 deduplication |
| `GET` | `/api/upload/{id}/workflows` | Available scientific workflows for detected file type |
| `POST` | `/api/analysis/start` | Dispatch user-selected analysis (Metadata, Quality, Signal, Inference, Preview) |
| `GET` | `/api/analysis/status/{id}` | Poll processing run execution status |
| `GET` | `/api/observations` | Paginated catalog of all observations |
| `GET` | `/api/observations/{id}` | Detailed observation physical and telescope metadata |
| `PATCH` | `/api/observations/{id}` | Update observation display name |
| `GET` | `/api/observations/{id}/preview` | Base64 2D optical image preview with photometric statistics |
| `GET` | `/api/observations/{id}/features` | Extracted Stokes I profile moments & DM parameters |
| `GET` | `/api/observations/{id}/predictions` | ML predictions and safe halt reasons |
| `GET` | `/api/observations/{id}/report` | Streaming publication-grade PDF report (radio or optical) |
| `GET` | `/api/candidates` | ACIS candidate prioritization table (filter by HIGH, MEDIUM, LOW) |
| `GET` | `/api/candidates/{id}` | Detailed ACIS 5-evidence breakdown |
| `GET` | `/api/processing-runs` | Pipeline execution audit trail |

---

## 4. Running Backend Tests

```bash
# Run complete test suite (33 tests)
py -m pytest backend/tests/ -v
```

All 33 unit and integration tests pass with 100% success rate.
