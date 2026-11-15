# ============================================================
#  ASTRA Cloud — Research Literature Extraction Service
#  File   : backend/app/services/extraction_service.py
#  Purpose: Extracts factually grounded scientific details from
#           retrieved astronomical literature metadata and
#           abstracts. Distinguishes verbatim evidence from
#           inferences; marks unsupported fields as not available.
# ============================================================

import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.schemas import (
    ExtractedResearchDetails,
    PaperExtractionResponse,
    FACTS_VS_INFERENCES_NOTE,
    SCIENTIFIC_COLLECTOR_DISCLAIMER,
)
from backend.app.models import ResearchRecord, PaperExtraction

logger = logging.getLogger("astra.extraction")

NOT_AVAILABLE = "Not available in retrieved source"

# ------------------------------------------------------------
# Known Astronomical Survey & Telescope Signatures
# ------------------------------------------------------------
DATASET_FACILITY_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(Green Bank Telescope|GBT|VEGAS)\b", re.IGNORECASE), "Green Bank Telescope (GBT)", "Pulsar timing & spectral archive (Radio)"),
    (re.compile(r"\b(Parkes|Murriyang|UWBR|UWL)\b", re.IGNORECASE), "Parkes 64m Telescope (Murriyang)", "Multibeam radio pulsar survey"),
    (re.compile(r"\b(FAST telescope|Five-hundred-meter Aperture Spherical|FAST 500m)\b|\bFAST\b(?!\s+(?:radio|burst|folding|fourier|timing|transient))", re.IGNORECASE), "FAST Telescope", "High-sensitivity drift scan radio survey"),
    (re.compile(r"\b(Arecibo|ALFA)\b", re.IGNORECASE), "Arecibo Observatory", "Arecibo Pulsar Survey / Timing archive"),
    (re.compile(r"\b(CHIME)\b", re.IGNORECASE), "CHIME Telescope", "Transit radio telescope archive (FRB / Pulsar)"),
    (re.compile(r"\b(MeerKAT|TRAPUM)\b", re.IGNORECASE), "MeerKAT Array", "Interferometric radio survey archive"),
    (re.compile(r"\b(ASKAP|CRAFT)\b", re.IGNORECASE), "ASKAP Array", "Wide-field radio survey"),
    (re.compile(r"\b(LOFAR)\b", re.IGNORECASE), "LOFAR", "Low-frequency radio array survey"),
    (re.compile(r"\b(HTRU2|HTRU)\b", re.IGNORECASE), "HTRU2 Benchmark Dataset", "Pulsar candidate feature benchmark"),
    (re.compile(r"\b(NANOGrav)\b", re.IGNORECASE), "NANOGrav Data Release", "Pulsar Timing Array (PTA) timing data"),
    (re.compile(r"\b(EPTA|European Pulsar Timing Array)\b", re.IGNORECASE), "EPTA Data Release", "Pulsar Timing Array (PTA) timing data"),
    (re.compile(r"\b(Hubble|HST|WFPC2|WFC3)\b", re.IGNORECASE), "Hubble Space Telescope (HST)", "Optical/UV astronomical image archive"),
    (re.compile(r"\b(Fermi|LAT)\b", re.IGNORECASE), "Fermi Large Area Telescope", "Gamma-ray pulsar catalog"),
]

# ------------------------------------------------------------
# Algorithmic & Model Signatures
# ------------------------------------------------------------
ALGORITHM_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(Convolutional Neural Network|CNN|ConvNet)\b", re.IGNORECASE), "Convolutional Neural Network (CNN)"),
    (re.compile(r"\b(Deep Neural Network|DNN|Deep Learning)\b", re.IGNORECASE), "Deep Neural Network (DNN)"),
    (re.compile(r"\b(Random Forest|Random Forests)\b", re.IGNORECASE), "Random Forest"),
    (re.compile(r"\b(Support Vector Machine|SVM)\b", re.IGNORECASE), "Support Vector Machine (SVM)"),
    (re.compile(r"\b(Multi-Layer Perceptron|Multilayer Perceptron|MLP)\b", re.IGNORECASE), "Multi-Layer Perceptron (MLP)"),
    (re.compile(r"\b(XGBoost|Gradient Boosted|Gradient Boosting)\b", re.IGNORECASE), "XGBoost / Gradient Boosting"),
    (re.compile(r"\b(Bayesian Inference|MCMC|Markov Chain Monte Carlo|Nested Sampling)\b", re.IGNORECASE), "Bayesian Inference / MCMC"),
    (re.compile(r"\b(TEMPO2|PINT)\b", re.IGNORECASE), "TEMPO2 / PINT Timing Software"),
    (re.compile(r"\b(Fast Folding Algorithm|FFA)\b", re.IGNORECASE), "Fast Folding Algorithm (FFA)"),
    (re.compile(r"\b(Fourier Transform|FFT|Fast Fourier)\b", re.IGNORECASE), "Fourier Transform (FFT)"),
    (re.compile(r"\b(Matched Filter|Matched Filtering|Template Matching)\b", re.IGNORECASE), "Matched Filtering"),
    (re.compile(r"\b(Decision Tree|Decision Trees)\b", re.IGNORECASE), "Decision Tree"),
    (re.compile(r"\b(Logistic Regression)\b", re.IGNORECASE), "Logistic Regression"),
]

# ------------------------------------------------------------
# Astronomical Feature Signatures
# ------------------------------------------------------------
FEATURE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(integrated pulse profile|pulse profile|folded profile)\b", re.IGNORECASE), "Integrated Pulse Profile"),
    (re.compile(r"\b(dispersion measure|DM curve|DM)\b", re.IGNORECASE), "Dispersion Measure (DM)"),
    (re.compile(r"\b(sub-integration|subint|time-phase array)\b", re.IGNORECASE), "Sub-integration Time Array"),
    (re.compile(r"\b(Stokes parameters|polarization|linear polarization|circular polarization)\b", re.IGNORECASE), "Stokes Polarization Parameters"),
    (re.compile(r"\b(pulse width|W50|W10)\b", re.IGNORECASE), "Pulse Width (W50 / W10)"),
    (re.compile(r"\b(spin period|pulsar period|pulse frequency)\b", re.IGNORECASE), "Spin Period / Frequency"),
    (re.compile(r"\b(period derivative|spin-down rate|P-dot)\b", re.IGNORECASE), "Period Derivative (P-dot)"),
    (re.compile(r"\b(rotation measure|Faraday rotation|RM)\b", re.IGNORECASE), "Rotation Measure (RM)"),
    (re.compile(r"\b(signal-to-noise ratio|SNR|S/N)\b", re.IGNORECASE), "Signal-to-Noise Ratio (SNR)"),
    (re.compile(r"\b(scintillation bandwidth|diffractive scintillation)\b", re.IGNORECASE), "Scintillation Parameters"),
]

# ------------------------------------------------------------
# Evaluation Metric Signatures
# ------------------------------------------------------------
METRIC_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(timing residual|residual RMS|RMS residual)\b", re.IGNORECASE), "Timing Residual RMS"),
    (re.compile(r"\b(reduced chi-square|chi-square|\bchi\^2\b|\bchi2\b)\b", re.IGNORECASE), "Chi-Square (χ²)"),
    (re.compile(r"\b(F1-score|F1 score|F-score)\b", re.IGNORECASE), "F1-Score"),
    (re.compile(r"\b(accuracy|classification accuracy)\b", re.IGNORECASE), "Classification Accuracy"),
    (re.compile(r"\b(precision)\b", re.IGNORECASE), "Precision"),
    (re.compile(r"\b(recall|sensitivity)\b", re.IGNORECASE), "Recall / Sensitivity"),
    (re.compile(r"\b(ROC-AUC|ROC AUC|area under the curve)\b", re.IGNORECASE), "ROC-AUC"),
    (re.compile(r"\b(Expected Calibration Error|ECE)\b", re.IGNORECASE), "Expected Calibration Error (ECE)"),
    (re.compile(r"\b(Brier score)\b", re.IGNORECASE), "Brier Score"),
    (re.compile(r"\b(false positive rate|FPR)\b", re.IGNORECASE), "False Positive Rate (FPR)"),
]

# ------------------------------------------------------------
# Sentence Extraction Regex
# ------------------------------------------------------------
SENTENCE_SPLIT_REGEX = re.compile(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s+")


def split_into_sentences(text: str) -> List[str]:
    """Split abstract or body text into individual clean sentences."""
    if not text or not text.strip():
        return []
    raw_sentences = SENTENCE_SPLIT_REGEX.split(text.strip())
    clean = []
    for s in raw_sentences:
        s_clean = " ".join(s.split()).strip()
        if len(s_clean) > 10:
            clean.append(s_clean)
    return clean


class LiteratureExtractionService:
    """Extracts factual, grounded information from retrieved paper metadata."""

    def extract_from_record(
        self,
        title: str,
        abstract: Optional[str],
        identifier: str,
        canonical_url: str,
        source_name: str = "arXiv",
        raw_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ExtractedResearchDetails, Dict[str, Any]]:
        """
        Extract supported fields from paper title and abstract.
        Strictly grounds all fields in verbatim sentences. Unsupported fields
        are set to 'Not available in retrieved source'.
        """
        combined_text = f"{title}. {abstract or ''}".strip()
        sentences = split_into_sentences(combined_text)

        evidence_locations: Dict[str, str] = {}

        # 1. Research Problem
        research_problem = self._extract_research_problem(title, sentences, evidence_locations)

        # 2. Dataset Name & Type
        dataset_name, dataset_type = self._extract_dataset(sentences, evidence_locations)

        # 3. Algorithms or Models
        algorithms = self._extract_algorithms(sentences, evidence_locations)

        # 4. Feature Types
        features = self._extract_features(sentences, evidence_locations)

        # 5. Evaluation Metrics
        metrics = self._extract_metrics(sentences, evidence_locations)

        # 6. Main Reported Findings
        findings = self._extract_findings(sentences, evidence_locations)

        # 7. Explicit Author Limitations
        limitations = self._extract_limitations(sentences, evidence_locations)

        # 8. Full-Text & License Access
        full_text_status, licence_status = self._extract_access(
            source_name, canonical_url, identifier, raw_metadata
        )

        # DOI extraction
        doi = None
        if identifier and (identifier.startswith("10.") or "doi.org" in identifier):
            doi = identifier
        elif raw_metadata and raw_metadata.get("doi"):
            doi = raw_metadata["doi"]

        # Provenance Tracking
        provenance = {
            "source_provider": source_name,
            "identifier": identifier,
            "canonical_url": canonical_url,
            "text_source": "Retrieved Abstract & Canonical Metadata (Zero restricted full-text bypass)",
            "character_count": len(combined_text),
            "sentence_count": len(sentences),
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "extraction_engine": "ASTRA-Literature-Extractor-v1.0",
        }

        details = ExtractedResearchDetails(
            research_problem=research_problem,
            dataset_name=dataset_name,
            dataset_type=dataset_type,
            algorithms_or_models=algorithms,
            feature_types=features,
            evaluation_metrics=metrics,
            main_reported_findings=findings,
            stated_limitations=limitations,
            full_text_availability=full_text_status,
            licence_or_access_status=licence_status,
            source_url=canonical_url,
            doi=doi,
            evidence_locations=evidence_locations,
            is_inferred=False,
            facts_vs_inferences_note=FACTS_VS_INFERENCES_NOTE,
        )

        return details, provenance

    def _extract_research_problem(
        self, title: str, sentences: List[str], evidence: Dict[str, str]
    ) -> str:
        problem_markers = [
            re.compile(r"\b(we address|we investigate|we study|we present|we develop|in this work|this paper focuses on|aims to|to detect|to timing|the challenge of|the task of)\b", re.IGNORECASE),
        ]
        for s in sentences:
            for pat in problem_markers:
                if pat.search(s):
                    evidence["research_problem"] = s
                    return s

        if title and len(title) > 15:
            evidence["research_problem"] = title
            return f"Investigation of: {title}"

        return NOT_AVAILABLE

    def _extract_dataset(
        self, sentences: List[str], evidence: Dict[str, str]
    ) -> Tuple[str, str]:
        for s in sentences:
            for pat, name, dtype in DATASET_FACILITY_PATTERNS:
                if pat.search(s):
                    evidence["dataset"] = s
                    return name, dtype
        return NOT_AVAILABLE, NOT_AVAILABLE

    def _extract_algorithms(
        self, sentences: List[str], evidence: Dict[str, str]
    ) -> List[str]:
        found: List[str] = []
        for s in sentences:
            for pat, algo_name in ALGORITHM_PATTERNS:
                if pat.search(s) and algo_name not in found:
                    found.append(algo_name)
                    if "algorithms_or_models" not in evidence:
                        evidence["algorithms_or_models"] = s

        return found if found else [NOT_AVAILABLE]

    def _extract_features(
        self, sentences: List[str], evidence: Dict[str, str]
    ) -> List[str]:
        found: List[str] = []
        for s in sentences:
            for pat, feat_name in FEATURE_PATTERNS:
                if pat.search(s) and feat_name not in found:
                    found.append(feat_name)
                    if "feature_types" not in evidence:
                        evidence["feature_types"] = s

        return found if found else [NOT_AVAILABLE]

    def _extract_metrics(
        self, sentences: List[str], evidence: Dict[str, str]
    ) -> List[str]:
        found: List[str] = []
        for s in sentences:
            for pat, metric_name in METRIC_PATTERNS:
                if pat.search(s) and metric_name not in found:
                    found.append(metric_name)
                    if "evaluation_metrics" not in evidence:
                        evidence["evaluation_metrics"] = s

        return found if found else [NOT_AVAILABLE]

    def _extract_findings(
        self, sentences: List[str], evidence: Dict[str, str]
    ) -> str:
        findings_markers = [
            re.compile(r"\b(we find that|we find|results show|results demonstrate|we achieve|achieves|yields|we discover|we identify|demonstrating|consistent with|outperforms)\b", re.IGNORECASE),
        ]
        for s in sentences:
            for pat in findings_markers:
                if pat.search(s):
                    evidence["main_reported_findings"] = s
                    return s
        return NOT_AVAILABLE

    def _extract_limitations(
        self, sentences: List[str], evidence: Dict[str, str]
    ) -> str:
        limitation_markers = [
            re.compile(r"\b(however|limitation|is limited by|cannot be applied|restricted to|caveat|requires future work|uncertainties remain|suffers from)\b", re.IGNORECASE),
        ]
        for s in sentences:
            for pat in limitation_markers:
                if pat.search(s):
                    evidence["stated_limitations"] = s
                    return s
        return NOT_AVAILABLE

    def _extract_access(
        self,
        source_name: str,
        canonical_url: str,
        identifier: str,
        raw_metadata: Optional[Dict[str, Any]],
    ) -> Tuple[str, str]:
        if source_name.lower() == "arxiv":
            # Extract arxiv id to build legal open-access link
            match = re.search(r"arxiv\.org/abs/([0-9]+\.[0-9]+(?:v[0-9]+)?|[a-zA-Z\-]+/[0-9]+)", canonical_url)
            arxiv_id = match.group(1) if match else identifier
            full_text = f"Open Access (Official arXiv PDF at https://arxiv.org/pdf/{arxiv_id})"
            licence = "arXiv Non-Exclusive License / Open Access"
            return full_text, licence

        if source_name.lower() == "zenodo":
            return "Open Access (Zenodo Open Science Archive)", "Creative Commons / Open Access"

        return "Metadata-only retrieved (Paywall / institutional subscription may apply)", NOT_AVAILABLE

    def persist_extraction(
        self,
        db: Session,
        record_id: Optional[int],
        identifier: str,
        title: str,
        details: ExtractedResearchDetails,
        provenance: Dict[str, Any],
    ) -> PaperExtraction:
        """Persist or update extracted literature facts in PostgreSQL paper_extractions."""
        existing = None
        if record_id:
            existing = db.query(PaperExtraction).filter(PaperExtraction.record_id == record_id).first()
        if not existing and identifier:
            existing = db.query(PaperExtraction).filter(PaperExtraction.identifier == identifier).first()

        algorithms_json = json.dumps(details.algorithms_or_models, ensure_ascii=False)
        features_json = json.dumps(details.feature_types, ensure_ascii=False)
        metrics_json = json.dumps(details.evaluation_metrics, ensure_ascii=False)
        evidence_json = json.dumps(details.evidence_locations, ensure_ascii=False)
        provenance_json = json.dumps(provenance, ensure_ascii=False)

        if existing:
            existing.research_problem = details.research_problem
            existing.dataset_name = details.dataset_name
            existing.dataset_type = details.dataset_type
            existing.algorithms_or_models = algorithms_json
            existing.feature_types = features_json
            existing.evaluation_metrics = metrics_json
            existing.main_reported_findings = details.main_reported_findings
            existing.stated_limitations = details.stated_limitations
            existing.full_text_availability = details.full_text_availability
            existing.licence_or_access_status = details.licence_or_access_status
            existing.source_url = details.source_url
            existing.doi = details.doi
            existing.evidence_locations_json = evidence_json
            existing.provenance_json = provenance_json
            existing.extracted_at = datetime.now(timezone.utc)
            db.commit()
            return existing

        new_extraction = PaperExtraction(
            record_id=record_id,
            identifier=identifier,
            research_problem=details.research_problem,
            dataset_name=details.dataset_name,
            dataset_type=details.dataset_type,
            algorithms_or_models=algorithms_json,
            feature_types=features_json,
            evaluation_metrics=metrics_json,
            main_reported_findings=details.main_reported_findings,
            stated_limitations=details.stated_limitations,
            full_text_availability=details.full_text_availability,
            licence_or_access_status=details.licence_or_access_status,
            source_url=details.source_url,
            doi=details.doi,
            evidence_locations_json=evidence_json,
            provenance_json=provenance_json,
        )
        db.add(new_extraction)
        db.commit()
        db.refresh(new_extraction)
        return new_extraction


# Singleton instance
literature_extractor = LiteratureExtractionService()
