# ASTRA Cloud — Astronomy Data Explorer Frontend

**Component:** Professional Astronomy Data Explorer Interface  
**Stack:** React 18.3, Vite 5.4, TypeScript 5.6, Vanilla Scientific CSS  
**Branding:** ASTRA — Astronomy Data Explorer  
**Backend API:** FastAPI (`http://127.0.0.1:8000`)  

---

## 1. Overview and Redesign Highlights

The upgraded ASTRA user interface provides a modern scientific workspace for astronomers and researchers to ingest, inspect, triage, and analyze multi-type astronomical observations (Radio PSRFITS and Optical FITS).

### Navigation Architecture
The application features a permanent left sidebar with 8 dedicated navigation views:
1. **Overview:** High-level operational dashboard with real observation metrics, recent files, and quick actions.
2. **Add Data:** Multi-file drag-and-drop FITS uploader with custom observation naming, format validation, and post-upload workflow selection.
3. **Observations:** Searchable, sortable, filterable catalog of all cataloged observations (Radio and Optical).
4. **High Priority:** Candidates with ACIS triage score ≥ 0.70 recommended for priority investigation.
5. **Medium Priority:** Candidates with ACIS triage score 0.45 – 0.69 requiring secondary review.
6. **Low Priority:** Candidates with ACIS triage score < 0.45 or unranked observations.
7. **Reports:** Centralized library of publication-grade PDF observation reports with one-click download.
8. **System Status:** Real-time PostgreSQL database connectivity indicator, runtime health, and comprehensive scientific methodology notes.

### Observation Detail View (7 Dedicated Sections)
1. **Overview:** Core telescope, coordinate, and triage summary.
2. **FITS Metadata:** Complete header parameters, observing modes, and frequencies.
3. **Data Preview:** High-contrast 2D astronomical image viewer with plane/group selectors for optical cubes.
4. **Analysis Results:** Model evaluations, feature summaries, or optical classification notices.
5. **Quality Information:** Stokes I moments, dispersion measure, noise floors, and dynamic range.
6. **Processing History:** Comprehensive pipeline execution audit trail.
7. **Reports:** Official PDF report preview and instant download action.

### Scientific Safeguards in UI
- **Collapsible Halt Notice:** Replaced technical warning paragraphs on the dashboard with a clean alert ("ML prediction unavailable") and an expandable drawer ("Why is prediction unavailable?") explaining the physical absence of multi-trial DM-SNR curves.
- **Strict Domain Separation:** Optical FITS images are never ranked as radio pulsar candidates, displaying `Not ranked — insufficient compatible evidence`.

---

## 2. Directory Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Sidebar.tsx             # Permanent left sidebar with the 8 required items
│   │   ├── Header.tsx              # Compact top header with live DB connection pill
│   │   ├── StatusBadge.tsx         # Telemetry badge component
│   │   ├── LoadingSpinner.tsx      # Pulse loading indicator
│   │   └── ErrorMessage.tsx        # Error alert box with retry triggers
│   ├── pages/
│   │   ├── OverviewPage.tsx        # Dashboard KPI metrics & recent observations
│   │   ├── AddDataPage.tsx         # Multi-file drag & drop upload & workflow chooser
│   │   ├── ObservationsPage.tsx    # Searchable, filterable catalog table
│   │   ├── PriorityPage.tsx        # Dedicated High, Medium, Low ACIS triage views
│   │   ├── ReportsPage.tsx         # Reports library and PDF download manager
│   │   ├── SystemStatusPage.tsx    # Real PostgreSQL status and secondary about section
│   │   └── ObservationDetailPage.tsx # 7-tab deep inspection view
│   ├── services/
│   │   └── api.ts                  # Typed native fetch client with upload & preview
│   ├── types/
│   │   └── api.ts                  # TypeScript models matching backend schemas
│   ├── App.tsx                     # Master app shell
│   ├── index.css                   # Scientific navy design system
│   ├── main.tsx                    # React DOM entrypoint
│   └── vite-env.d.ts               # Vite environment types
├── dist/                           # Production build output
├── package.json                    # Scripts and dependencies
└── README.md                       # This document
```

---

## 3. Development and Production Build

```bash
# Run local Vite development server
npm run dev

# Build production bundle with TypeScript verification
npm run build
```

Production build compiles with **0 TypeScript errors** in ~1.2s.
