// ============================================================
//  ASTRA — ML Workflow & Radio Signal Pipeline
//  File   : frontend/src/pages/MLWorkflowPage.tsx
//  Purpose: Clear, research-oriented presentation of the two
//           supported scientific data paths and their connections:
//           Path 1: HTRU2 Labelled Features → Preprocessing → Train/Test Split
//                   → Random Forest Training → Held-Out Evaluation → Saved Model
//                   → HTRU2 Predictions & Evaluation
//           Path 2: Parkes Radio Observation → Format Verification & Metadata Reading
//                   → Signal Inspection & Preprocessing → Appropriate Signal Processing
//                   → Feature Extraction → Quality/Noise/Channel Experiments
//                   → Compatible Feature Validation (Pending / Incomplete)
//                   → Cross-Dataset Research Interpretation
//           Connects both paths to Integrated Research Layer, PostgreSQL, Neo4j, and MLflow.
// ============================================================

import React, { useState } from 'react';
import { PulseProfilePlot } from '../components/charts/PulseProfilePlot';

interface WorkflowNode {
  title: string;
  subtitle: string;
  details: string;
  artifact: string;
  status: 'COMPLETED' | 'PENDING' | 'HALTED_BY_DESIGN';
}

const HTRU2_WORKFLOW: WorkflowNode[] = [
  {
    title: 'HTRU2 Labelled Features',
    subtitle: '17,898 Benchmark Candidates',
    details: 'UCI ML Repository benchmark tabular data with 8 numerical moments (4 integrated profile moments + 4 DM-SNR curve moments). Supervised labels: 1,639 positive pulsars (9.16%) vs 16,259 negative RFI/noise candidates (90.84%).',
    artifact: 'data/htru2/HTRU_2.csv (SHA-256 verified)',
    status: 'COMPLETED',
  },
  {
    title: 'Preprocessing',
    subtitle: 'Moments Extraction & Z-Score Scaling',
    details: 'Feature validation, missing value assertion, and StandardScaler z-score normalization fit strictly on training set to prevent data leakage.',
    artifact: 'StandardScaler transformer (8 features)',
    status: 'COMPLETED',
  },
  {
    title: 'Train / Test Split',
    subtitle: 'Stratified 80/20 Partition',
    details: 'Stratified split preserving class proportion (14,318 train candidates, 3,580 test candidates; random seed 42).',
    artifact: 'train_test_split(stratify=y, test_size=0.20)',
    status: 'COMPLETED',
  },
  {
    title: 'Random Forest Training',
    subtitle: '100 Trees Ensemble',
    details: 'Supervised ensemble (n_estimators=100, max_depth=12, random_state=42). Trained exclusively on tabular feature distributions.',
    artifact: 'models/random_forest_pipeline.pkl',
    status: 'COMPLETED',
  },
  {
    title: 'Held-Out Evaluation',
    subtitle: 'Metric Benchmarking & Calibration',
    details: 'Evaluated on held-out 3,580 candidates: F1=0.8952, Accuracy=98.16%, ROC-AUC=0.9668, Precision=93.38%, Recall=85.98%. Brier score=0.0152, ECE=1.24%.',
    artifact: 'MLflow Run: ASTRA_HTRU2_Classification',
    status: 'COMPLETED',
  },
  {
    title: 'Saved Model',
    subtitle: 'Model Serialization & Governance',
    details: 'Model serialized with preprocessing pipeline transformer. Registered with full hyperparameter and metric provenance in MLflow tracking store.',
    artifact: 'models/random_forest_pipeline.pkl (MLflow Run ID: ASTRA-RF-001)',
    status: 'COMPLETED',
  },
  {
    title: 'HTRU2 Predictions & Evaluation',
    subtitle: 'Inference & Error Decomposition',
    details: 'Prediction confidence probabilities, confusion matrix decomposition (TN=3,232, TP=282, FP=20, FN=46), and SHAP feature attribution rankings.',
    artifact: 'reports/plots/final_random_forest_confusion_matrix.png',
    status: 'COMPLETED',
  },
];

const PARKES_WORKFLOW: WorkflowNode[] = [
  {
    title: 'Parkes Radio Observation',
    subtitle: 'PDFB4 2-bit Search Stream',
    details: 'Observational data from Parkes 64m radio telescope (Murriyang). Raw continuous search-mode observation stream of confirmed bright millisecond pulsar PSR J0437-4715.',
    artifact: 'data/parkes/PDFB4_Search_J0437-4715.sf',
    status: 'COMPLETED',
  },
  {
    title: 'Format Verification & Metadata',
    subtitle: 'Astropy PSRFITS Header Inspection',
    details: 'Header Data Unit extraction and binary table validation via Astropy io.fits. Reads 512 channels, center frequency (1369 MHz), channel bandwidth (0.5 MHz), total bandwidth (256 MHz).',
    artifact: 'PSRFITS Header: 512 channels, 10 subintegrations',
    status: 'COMPLETED',
  },
  {
    title: 'Signal Inspection & Preprocessing',
    subtitle: '2-bit Bit-Unpacking & Dynamic Spectrum',
    details: 'Binary 2-bit quantization unpacking into raw frequency-time intensity matrix (163,840 time samples × 512 channels, 40,960 samples evaluated in 10-subint representative block).',
    artifact: 'In-memory 2D float32 dynamic spectrum array',
    status: 'COMPLETED',
  },
  {
    title: 'Appropriate Signal Processing',
    subtitle: 'Bandpass Integration & Baseline Subtraction',
    details: 'Channel-by-channel baseline subtraction, bandpass integration across 512 frequency channels, and pulse peak extraction isolating pulsar emission from instrumental thermal background.',
    artifact: 'Detrended frequency-integrated time series profile',
    status: 'COMPLETED',
  },
  {
    title: 'Feature Extraction',
    subtitle: 'Physical Profile Moments & SNR',
    details: 'Extracts integrated pulse profile moments (Profile Mean, Profile Kurtosis = 14.8) and observed signal-to-noise ratio (SNR = 30.70 at nominal DM = 2.644 pc/cm³).',
    artifact: 'Observed SNR = 30.70, Profile Kurtosis = 14.8',
    status: 'COMPLETED',
  },
  {
    title: 'Quality / Noise / Channel Experiments',
    subtitle: 'P1 Additive Noise & P2 Channel Masking',
    details: 'Systematic testing: additive white noise injection (0% to 200% sigma, SNR retention down to 42.1%) and frequency-channel masking (5% to 75% excision, recoverability index down to 0.34).',
    artifact: 'MLflow Runs: ASTRA_P1_Perturbation & ASTRA_P2_Masking',
    status: 'COMPLETED',
  },
  {
    title: 'Compatible Feature Validation',
    subtitle: 'Dedispersion & Epoch Folding Audit',
    details: 'Assesses whether extracted Parkes features match HTRU2 tabular input requirements. Direct transfer is currently blocked by design: coherent dedispersion and epoch folding at P0=5.76 ms are required prerequisites.',
    artifact: 'Prerequisites: Coherent Dedispersion & Epoch Folding (Pending)',
    status: 'PENDING',
  },
  {
    title: 'Cross-Dataset Research Interpretation',
    subtitle: 'Synthesis with Tabular ML Findings',
    details: 'Connects pre-detection radio signal quality boundaries (excision safety envelope <=20%) with post-detection classifier noise tolerance, forming a single scientifically valid research framework.',
    artifact: 'reports/two_dataset_integration_report.json',
    status: 'COMPLETED',
  },
];

export const MLWorkflowPage: React.FC = () => {
  const [selectedHTRU2Node, setSelectedHTRU2Node] = useState<number>(0);
  const [selectedParkesNode, setSelectedParkesNode] = useState<number>(0);

  const activeHTRU2 = HTRU2_WORKFLOW[selectedHTRU2Node];
  const activeParkes = PARKES_WORKFLOW[selectedParkesNode];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Page Header */}
      <div className="card" style={{ borderLeft: '4px solid var(--primary)', padding: '18px 22px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Research Architecture & Methodology
            </span>
            <h2 style={{ margin: '4px 0 6px', fontSize: '1.25rem', color: 'var(--text-main)', fontWeight: 700 }}>
              ASTRA — ML Workflow & Radio Signal Processing Pipeline
            </h2>
            <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-muted)', maxWidth: '880px', lineHeight: 1.45 }}>
              This diagram presents the actual processing stages supported in ASTRA across both scientific data paths.
              Both paths connect to the <strong>Integrated Research Results Layer</strong>, <strong>PostgreSQL</strong>, the <strong>Neo4j Knowledge Graph</strong>, and <strong>MLflow Tracking</strong>.
            </p>
          </div>
          <span className="badge badge-completed">
            ✓ Decoupled Architecture Enforced
          </span>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 1. PATH 1: HTRU2 TABULAR ML WORKFLOW */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="card" style={{ padding: '20px', borderTop: '3px solid #0284c7' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.1rem' }}>📊</span>
              <h3 className="card-title" style={{ margin: 0, color: '#0369a1' }}>
                Path 1: HTRU2 Labelled Machine Learning Pipeline
              </h3>
            </div>
            <p style={{ margin: '3px 0 0', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
              HTRU2 Labelled Features &rarr; Preprocessing &rarr; Train/Test Split &rarr; Random Forest Training &rarr; Held-Out Evaluation &rarr; Saved Model &rarr; Predictions & Evaluation
            </p>
          </div>
          <span className="badge badge-completed">
            7 / 7 Stages Completed
          </span>
        </div>

        {/* Stepper Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
          {HTRU2_WORKFLOW.map((node, idx) => {
            const isSelected = idx === selectedHTRU2Node;
            return (
              <div
                key={node.title}
                onClick={() => setSelectedHTRU2Node(idx)}
                style={{
                  padding: '10px',
                  borderRadius: '6px',
                  backgroundColor: isSelected ? '#e0f2fe' : '#f8fafc',
                  border: `1px solid ${isSelected ? '#0284c7' : 'var(--border-subtle)'}`,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <span
                    style={{
                      width: '18px',
                      height: '18px',
                      borderRadius: '50%',
                      background: isSelected ? '#0284c7' : '#cbd5e1',
                      color: '#fff',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {idx + 1}
                  </span>
                  <strong style={{ fontSize: '0.74rem', color: isSelected ? '#0369a1' : 'var(--text-main)', lineHeight: 1.2 }}>
                    {node.title}
                  </strong>
                </div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', paddingLeft: '24px' }}>
                  {node.subtitle}
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Stage Detail Panel */}
        <div style={{ marginTop: '14px', background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '14px 16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase' }}>
              Stage {selectedHTRU2Node + 1} Details: {activeHTRU2.title} ({activeHTRU2.subtitle})
            </span>
            <span className="badge badge-validated">Validated Implementation</span>
          </div>
          <p style={{ margin: '0 0 8px', fontSize: '0.8rem', color: 'var(--text-main)', lineHeight: 1.5 }}>
            {activeHTRU2.details}
          </p>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            <strong>Output Artifact:</strong> <span className="mono" style={{ color: '#0284c7' }}>{activeHTRU2.artifact}</span>
          </div>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 2. PATH 2: PARKES RADIO SIGNAL PROCESSING WORKFLOW */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="card" style={{ padding: '20px', borderTop: '3px solid #7c3aed' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.1rem' }}>📡</span>
              <h3 className="card-title" style={{ margin: 0, color: '#6b21a8' }}>
                Path 2: Parkes Radio-Signal Stream Pipeline
              </h3>
            </div>
            <p style={{ margin: '3px 0 0', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
              Observation &rarr; Format Verification &rarr; Signal Inspection &rarr; Signal Processing &rarr; Feature Extraction &rarr; Quality/Noise Experiments &rarr; Feature Validation (Pending) &rarr; Cross-Dataset Interpretation
            </p>
          </div>
          <span className="badge badge-pending">
            7 Completed / 1 Pending Validation
          </span>
        </div>

        {/* Stepper Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
          {PARKES_WORKFLOW.map((node, idx) => {
            const isSelected = idx === selectedParkesNode;
            const isPending = node.status === 'PENDING';
            return (
              <div
                key={node.title}
                onClick={() => setSelectedParkesNode(idx)}
                style={{
                  padding: '10px',
                  borderRadius: '6px',
                  backgroundColor: isSelected ? '#f3e8ff' : '#f8fafc',
                  border: `1px solid ${isSelected ? '#7c3aed' : isPending ? '#fbbf24' : 'var(--border-subtle)'}`,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <span
                    style={{
                      width: '18px',
                      height: '18px',
                      borderRadius: '50%',
                      background: isPending ? '#d97706' : isSelected ? '#7c3aed' : '#cbd5e1',
                      color: '#fff',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {idx + 1}
                  </span>
                  <strong style={{ fontSize: '0.74rem', color: isSelected ? '#6b21a8' : 'var(--text-main)', lineHeight: 1.2 }}>
                    {node.title}
                  </strong>
                </div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', paddingLeft: '24px' }}>
                  {node.subtitle}
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Stage Detail Panel */}
        <div style={{ marginTop: '14px', background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '14px 16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.74rem', fontWeight: 700, color: '#6b21a8', textTransform: 'uppercase' }}>
              Stage {selectedParkesNode + 1} Details: {activeParkes.title} ({activeParkes.subtitle})
            </span>
            <span className={`badge ${activeParkes.status === 'COMPLETED' ? 'badge-validated' : 'badge-pending'}`}>
              {activeParkes.status === 'COMPLETED' ? 'Validated Implementation' : 'Prerequisite Incomplete (Pending Dedispersion)'}
            </span>
          </div>
          <p style={{ margin: '0 0 8px', fontSize: '0.8rem', color: 'var(--text-main)', lineHeight: 1.5 }}>
            {activeParkes.details}
          </p>
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            <strong>Output Artifact:</strong> <span className="mono" style={{ color: '#7c3aed' }}>{activeParkes.artifact}</span>
          </div>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 3. SCIENTIFIC DECOUPLING & DOMAIN INTEGRITY NOTICE */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div
        className="card"
        style={{
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '8px',
          padding: '16px 20px',
        }}
      >
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
          <span style={{ fontSize: '1.4rem' }}>🛡️</span>
          <div>
            <strong style={{ color: '#991b1b', fontSize: '0.9rem' }}>
              Research Problem 3 Constraint: Architectural Decoupling Policy
            </strong>
            <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: '#7f1d1d', lineHeight: 1.45 }}>
              Raw Parkes radio-frequency data is <strong>never passed directly</strong> into the HTRU2 Random Forest classifier.
              Direct transfer violates domain validity because of mismatched dimensionality (8-feature scalar summary moments vs. 40,960 × 512 time-frequency array).
              The Parkes stream requires dedicated folding, de-dispersion, and DM-curve optimization before cross-domain classifier evaluation can be performed. Transfer accuracy is never fabricated.
            </p>
          </div>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 4. ACTUAL SUPPORTED OUTPUTS & SYSTEM ARCHITECTURE CONNECTIONS */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="card" style={{ padding: '20px' }}>
        <h3 className="card-title" style={{ margin: '0 0 4px' }}>
          Integrated System Connections & Infrastructure Architecture
        </h3>
        <p style={{ margin: '0 0 16px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          Both scientific paths feed into the unified research-results layer, database, knowledge graph, and MLflow tracking store
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
          <div style={{ background: '#f8fafc', padding: '14px', borderRadius: '6px', border: '1px solid var(--border-subtle)', borderTop: '3px solid #0284c7' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
              1. Research Results Layer
            </div>
            <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#0284c7', marginTop: '4px' }}>
              Unified Schema & Reports
            </div>
            <p style={{ margin: '6px 0 0', fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>
              Stores standardized experiment records with 15 fields (experiment_id, result_type, comparability_status, limitations). Persists to <span className="mono">reports/two_dataset_integration_report.json</span>.
            </p>
          </div>

          <div style={{ background: '#f8fafc', padding: '14px', borderRadius: '6px', border: '1px solid var(--border-subtle)', borderTop: '3px solid #16a34a' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
              2. PostgreSQL Database
            </div>
            <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#16a34a', marginTop: '4px' }}>
              Relational Storage & Audits
            </div>
            <p style={{ margin: '6px 0 0', fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>
              Tracks observations, features, candidate scores, and pipeline execution logs in the <span className="mono">processing_runs</span> table on port 5432.
            </p>
          </div>

          <div style={{ background: '#f8fafc', padding: '14px', borderRadius: '6px', border: '1px solid var(--border-subtle)', borderTop: '3px solid #7c3aed' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
              3. Neo4j Knowledge Graph
            </div>
            <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#7c3aed', marginTop: '4px' }}>
              Bolt Protocol Port 7687
            </div>
            <p style={{ margin: '6px 0 0', fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>
              Models directed semantic links between Datasets, Pulsars (J1713, J0437), Models (RF, SVM, MLP), SHAP Features, and Research Experiments P1–P5.
            </p>
          </div>

          <div style={{ background: '#f8fafc', padding: '14px', borderRadius: '6px', border: '1px solid var(--border-subtle)', borderTop: '3px solid #d97706' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
              4. MLflow Experiment Tracking
            </div>
            <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#d97706', marginTop: '4px' }}>
              SQLite Tracking Store & Artifacts
            </div>
            <p style={{ margin: '6px 0 0', fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>
              Tracks 6 research experiments and runs in <span className="mono">backend/data/mlflow.db</span> with hyperparameter logs, evaluation metrics, and model artifacts.
            </p>
          </div>
        </div>
      </div>

      {/* Demonstration Pulse Profile */}
      <div>
        <h4 style={{ fontSize: '0.94rem', color: 'var(--text-main)', fontWeight: 700, marginBottom: '10px' }}>
          Extracted Radio Profile Verification (PSR J0437-4715)
        </h4>
        <PulseProfilePlot
          targetName="PSR J0437-4715 (Parkes Search Stream)"
          telescope="Parkes 64m (PDFB4 Backend @ 1369 MHz)"
          nominalDm={2.644}
          profileKurtosis={14.8}
          snr={30.70}
          candidateDecision="Candidate"
        />
      </div>
    </div>
  );
};

export default MLWorkflowPage;
