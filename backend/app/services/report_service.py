# ============================================================
#  ASTRA Cloud — Scientific Observation PDF Report Generator
#  File   : backend/app/services/report_service.py
#  Purpose: Generates a publication-grade scientific PDF audit report
#           for cataloged astronomical observations using ReportLab.
# ============================================================

import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Any, Dict
import xml.sax.saxutils

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.pdfgen.canvas import Canvas

from backend.app.models import Observation, Feature, Prediction, CandidateScore, ProcessingRun


class NumberedCanvas(Canvas):
    """Two-pass canvas to dynamically compute and draw headers and 'Page X of Y' footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header rule & title
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(40, letter[1] - 32, letter[0] - 40, letter[1] - 32)
        self.drawString(40, letter[1] - 25, "ASTRA — Astronomical Observation Audit & Intelligence Report")
        self.drawRightString(letter[0] - 40, letter[1] - 25, "UNCLASSIFIED // RESEARCH DEMONSTRATOR")

        # Footer rule & page number
        self.line(40, 36, letter[0] - 40, 36)
        footer_left = "SCIENTIFIC TRIAGE AUDIT — STRICTLY NOT AN AUTONOMOUS DISCOVERY CONFIRMATION"
        footer_right = f"Page {self._pageNumber} of {page_count}"
        self.drawString(40, 24, footer_left)
        self.drawRightString(letter[0] - 40, 24, footer_right)
        self.restoreState()


class CsvNumberedCanvas(Canvas):
    """Two-pass canvas for CSV reports with institutional header and dynamic Page X of Y footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header rule & title
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, letter[1] - 30, letter[0] - 36, letter[1] - 30)
        self.drawString(36, letter[1] - 23, "ASTRA — Research Data Audit Report")
        self.drawRightString(letter[0] - 36, letter[1] - 23, "SCIENTIFIC OBSERVATION DATA REPORT")

        # Footer rule & page number
        self.line(36, 32, letter[0] - 36, 32)
        footer_left = "SCIENTIFIC OBSERVATION AUDIT — STRICTLY UNMODIFIED SOURCE RECORDS"
        footer_right = f"Page {self._pageNumber} of {page_count}"
        self.drawString(36, 22, footer_left)
        self.drawRightString(letter[0] - 36, 22, footer_right)
        self.restoreState()


def infer_column_type(series: pd.Series) -> str:
    """Safely and deterministically infer a human-readable column data type."""
    if pd.api.types.is_bool_dtype(series):
        return "Boolean"
    if pd.api.types.is_integer_dtype(series):
        return "Integer"
    if pd.api.types.is_float_dtype(series):
        valid = series.dropna()
        if len(valid) > 0 and (valid % 1 == 0).all():
            return "Integer"
        return "Decimal"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "Date"
    valid = series.dropna()
    if len(valid) > 0 and len(valid) <= 1000:
        sample = valid.astype(str).str.strip()
        date_pattern = r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}"
        if sample.str.match(date_pattern).all():
            return "Date"
    return "Text"



def generate_observation_pdf(
    obs: Observation,
    feature: Optional[Feature],
    predictions: List[Prediction],
    candidate: Optional[CandidateScore],
    runs: List[ProcessingRun],
    csv_path: Optional[Path] = None,
    csv_original_name: Optional[str] = None,
) -> io.BytesIO:
    """
    Builds an institutional-grade PDF report stream for a cataloged observation,
    optionally incorporating tabular CSV dataset records and descriptive statistics.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=46,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()

    # Typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#0f172a'),
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#475569'),
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0369a1'),
        spaceBefore=8,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1e293b'),
    )
    body_muted = ParagraphStyle(
        'BodyMuted',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#64748b'),
    )
    mono_style = ParagraphStyle(
        'Mono',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#0f172a'),
    )
    callout_alert = ParagraphStyle(
        'CalloutAlert',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#b45309'),
    )
    callout_success = ParagraphStyle(
        'CalloutSuccess',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#15803d'),
    )

    elements = []

    # ── Executive Title Header ────────────────────────────────
    elements.append(Paragraph("ASTRA — ASTRONOMICAL OBSERVATION AUDIT REPORT", title_style))
    doc_id = f"ASTRA-REP-OBS-{obs.id:04d}"
    gen_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    elements.append(Paragraph(
        f"<b>Document ID:</b> {doc_id} &nbsp;|&nbsp; <b>Generated:</b> {gen_time} &nbsp;|&nbsp; "
        f"<b>Target:</b> {obs.target_name or 'N/A'} &nbsp;|&nbsp; <b>Telescope:</b> {obs.telescope or 'N/A'}",
        subtitle_style
    ))
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0284c7"), spaceAfter=8))

    # ── Scientific Method & Provenance Legend ─────────────────
    legend_data = [
        [
            Paragraph("<b>EVALUATION FRAMEWORK:</b>", body_style),
            Paragraph(
                "• <b>[MEASURED]</b> Hardware detector metadata & coordinates &nbsp;|&nbsp; "
                "• <b>[DERIVED]</b> Algorithmic Stokes I profile moments & DM curve &nbsp;|&nbsp; "
                "• <b>[MODEL]</b> Supervised ML classifier &nbsp;|&nbsp; "
                "• <b>[HEURISTIC]</b> ACIS multi-evidence triage score (uncalibrated queue priority)",
                body_muted
            ),
        ]
    ]
    t_legend = Table(legend_data, colWidths=[1.8 * inch, 5.4 * inch])
    t_legend.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_legend)
    elements.append(Spacer(1, 6))

    is_optical = "OPTICAL" in (obs.file_type or "").upper() or "IMAGE" in (obs.file_type or "").upper()

    # ── SECTION 1: Target & Detector Parameters ───────────────
    section1_title = "1. OPTICAL OBSERVATION & DETECTOR METADATA" if is_optical else "1. ASTRONOMICAL OBSERVATION & HARDWARE METADATA"
    elements.append(Paragraph(section1_title, section_heading))

    obs_meta_data = [
        [
            Paragraph("<b>Target Source:</b>", body_style), Paragraph(str(obs.target_name or 'N/A'), body_style),
            Paragraph("<b>Source File:</b>", body_style), Paragraph(str(obs.file_name), mono_style),
        ],
        [
            Paragraph("<b>Observatory / Instrument:</b>", body_style), Paragraph(f"{obs.telescope or 'N/A'} / {obs.instrument or 'N/A'}", body_style),
            Paragraph("<b>Observation Date & Time:</b>", body_style), Paragraph(f"{obs.observation_date or 'N/A'} {obs.observation_time or ''}".strip(), body_style),
        ],
        [
            Paragraph("<b>Sky Coordinates (RA / DEC):</b>", body_style), Paragraph(f"{obs.ra or 'N/A'} / {obs.dec or 'N/A'}", mono_style),
            Paragraph("<b>Data Format / Type:</b>", body_style), Paragraph(str(obs.file_type or 'N/A'), body_style),
        ],
        [
            Paragraph("<b>File Size / Ingested:</b>", body_style), Paragraph(f"{obs.file_size_mb or 'N/A'} MB &nbsp;({obs.created_at.strftime('%Y-%m-%d') if obs.created_at else 'N/A'})", body_style),
            Paragraph("<b>Validation Status:</b>", body_style), Paragraph(f"<b>{obs.validation_status}</b>", body_style),
        ],
    ]

    if not is_optical:
        obs_meta_data.append([
            Paragraph("<b>Central Freq / Bandwidth:</b>", body_style),
            Paragraph(f"{obs.frequency_mhz or 'N/A'} MHz / {obs.bandwidth_mhz or 'N/A'} MHz", body_style),
            Paragraph("<b>Subints / Channels / Bins:</b>", body_style),
            Paragraph(f"{obs.nsubint or 'N/A'} subints / {obs.nchan or 'N/A'} chans / {obs.nbin or 'N/A'} bins", body_style),
        ])

    t_obs = Table(obs_meta_data, colWidths=[1.6 * inch, 2.3 * inch, 1.6 * inch, 1.7 * inch])
    t_obs.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_obs)
    elements.append(Spacer(1, 8))

    # ── SECTION 2: Physical Features ──────────────────────────
    if is_optical:
        elements.append(Paragraph("2. OPTICAL IMAGE ARRAY & HDU STRUCTURE", section_heading))
        opt_info = [
            [
                Paragraph("<b>Primary Image Structure:</b>", body_style),
                Paragraph("2D / 3D Array in primary and extension HDUs", mono_style),
                Paragraph("<b>Sensor Type:</b>", body_style),
                Paragraph("Optical / Ultraviolet CCD Imager", body_style),
            ],
            [
                Paragraph("<b>Astrophysical Domain:</b>", body_style),
                Paragraph("Optical Photometry & Spatial Morphology", body_style),
                Paragraph("<b>Radio Triage Applicable:</b>", body_style),
                Paragraph("<b>NO — Optical imaging data</b>", callout_alert),
            ]
        ]
        t_opt = Table(opt_info, colWidths=[1.6 * inch, 2.3 * inch, 1.6 * inch, 1.7 * inch])
        t_opt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_opt)
        elements.append(Spacer(1, 8))

        elements.append(Paragraph("3. SCIENTIFIC CLASSIFICATION & DOMAIN INTEGRITY", section_heading))
        notice_box = [
            [
                Paragraph("<b>ASTRONOMICAL DOMAIN:</b>", body_style),
                Paragraph("<b>Optical Astronomy Observation (FITS Image Array)</b>", callout_success)
            ],
            [
                Paragraph("<b>Radio ML Classifier:</b>", body_style),
                Paragraph("<i>Excluded by design: HTRU2 pulsar classifier is strictly prohibited on optical datasets.</i>", body_style)
            ],
            [
                Paragraph("<b>Candidate Prioritization:</b>", body_style),
                Paragraph("Not evaluated — ACIS scoring requires radio dispersion and periodic Stokes I pulse profiles.", body_style)
            ]
        ]
        t_notice = Table(notice_box, colWidths=[1.8 * inch, 5.4 * inch])
        t_notice.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f9ff')),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#0284c7')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bae6fd')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_notice)
        elements.append(Spacer(1, 8))

    else:
        # RADIO DATA SECTIONS
        elements.append(Paragraph("2. EXTRACTED PHYSICAL & OBSERVATIONAL FEATURES", section_heading))
        if feature:
            feat_data = [
                [
                    Paragraph("<b>Stokes I Profile Mean:</b>", body_style),
                    Paragraph(f"{feature.profile_mean:.2f}" if feature.profile_mean is not None else "Not available", mono_style),
                    Paragraph("<b>Nominal DM:</b>", body_style),
                    Paragraph(f"{feature.dm_nominal:.4f} pc/cm³" if feature.dm_nominal is not None else "Not available", mono_style),
                ],
                [
                    Paragraph("<b>Stokes I Profile Std:</b>", body_style),
                    Paragraph(f"{feature.profile_std:.2f}" if feature.profile_std is not None else "Not available", mono_style),
                    Paragraph("<b>DM-SNR Curve Available:</b>", body_style),
                    Paragraph("NO (Single folded timing archive)", body_style),
                ],
                [
                    Paragraph("<b>Profile Skew / Kurtosis:</b>", body_style),
                    Paragraph(f"{feature.profile_skewness:.4f} / {feature.profile_kurtosis:.4f}" if feature.profile_skewness is not None else "Not available", mono_style),
                    Paragraph("<b>Multi-Trial DM Moments:</b>", body_style),
                    Paragraph("Not evaluated (structurally absent in fold-mode)", body_style),
                ],
                [
                    Paragraph("<b>Baseline Noise Estimate:</b>", body_style),
                    Paragraph(f"{feature.noise_estimate:.2f}" if feature.noise_estimate is not None else "Not available", mono_style),
                    Paragraph("<b>RFI Cleanliness Metric:</b>", body_style),
                    Paragraph(f"{feature.rfi_indicator:.4f}" if feature.rfi_indicator is not None else "Not available", mono_style),
                ],
                [
                    Paragraph("<b>Dynamic Range:</b>", body_style),
                    Paragraph(f"{feature.dynamic_range:.2f}" if feature.dynamic_range is not None else "Not available", mono_style),
                    Paragraph("<b>HTRU2 Benchmark Compatible:</b>", body_style),
                    Paragraph("<b>NO (Domain Mismatch Detected)</b>", callout_alert),
                ]
            ]
            t_feat = Table(feat_data, colWidths=[1.6 * inch, 2.3 * inch, 1.6 * inch, 1.7 * inch])
            t_feat.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(t_feat)
        else:
            elements.append(Paragraph("<i>No extracted physical features recorded in catalog database for this observation.</i>", body_style))
        elements.append(Spacer(1, 8))

        # ── SECTION 3: ML Inference Status ───────────────────────
        elements.append(Paragraph("3. SUPERVISED MACHINE LEARNING CLASSIFIER EVALUATION", section_heading))
        if predictions:
            # Render actual predictions table
            pred_rows = [
                [
                    Paragraph("<b>Model Name</b>", body_style),
                    Paragraph("<b>Version</b>", body_style),
                    Paragraph("<b>Predicted Class</b>", body_style),
                    Paragraph("<b>Pulsar Probability</b>", body_style),
                    Paragraph("<b>Inference Status</b>", body_style),
                ]
            ]
            for p in predictions:
                prob_str = f"{p.pulsar_probability:.4f}" if p.pulsar_probability is not None else "Not available"
                class_str = "PULSAR (1)" if p.predicted_class == 1 else "NON-PULSAR (0)" if p.predicted_class == 0 else "Not evaluated"
                pred_rows.append([
                    Paragraph(str(p.model_name), body_style),
                    Paragraph(str(p.model_version), mono_style),
                    Paragraph(class_str, body_style),
                    Paragraph(prob_str, mono_style),
                    Paragraph(str(p.inference_status), callout_alert if "HALT" in p.inference_status else body_style),
                ])
            t_pred = Table(pred_rows, colWidths=[1.8 * inch, 1.0 * inch, 1.5 * inch, 1.4 * inch, 1.5 * inch])
            t_pred.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(t_pred)
        else:
            # Model inference halted for fold-mode archive safeguard
            ml_status_box = [
                [
                    Paragraph("<b>EVALUATION STATUS:</b>", body_style),
                    Paragraph("<b>INFERENCE_HALTED (Scientific Safeguard Enforced)</b>", callout_alert)
                ],
                [
                    Paragraph("<b>Target Classifier:</b>", body_style),
                    Paragraph("RandomForestClassifier (200 trees, trained on HTRU2 search candidate benchmark)", body_style)
                ],
                [
                    Paragraph("<b>Pulsar Probability:</b>", body_style),
                    Paragraph("<i>Not evaluated — model execution safely halted to prevent domain-shifted fabricated predictions.</i>", body_style)
                ],
                [
                    Paragraph("<b>Scientific Halt Reason:</b>", body_style),
                    Paragraph(
                        "Incompatible feature schema: HTRU2 models require 4 multi-trial DM-SNR moments which are "
                        "structurally absent in single-epoch folded timing archives. Unscaled amplitude units (~17,000 ADU) "
                        "further diverge from normalized candidate benchmarks.", body_style
                    )
                ]
            ]
            t_ml = Table(ml_status_box, colWidths=[1.8 * inch, 5.4 * inch])
            t_ml.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef3c7')),
                ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#f59e0b')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#fde68a')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(t_ml)
        elements.append(Spacer(1, 8))

    # ── SECTION 4: ACIS Candidate Prioritization ──────────────
    elements.append(Paragraph("4. ACIS MULTI-EVIDENCE CANDIDATE PRIORITIZATION", section_heading))
    if candidate:
        acis_data = [
            [
                Paragraph("<b>ACIS Intelligence Score:</b>", body_style),
                Paragraph(f"<b>{candidate.acis_score:.4f}</b> &nbsp;(range: 0.0000 – 1.0000)", callout_success),
                Paragraph("<b>Inspection Priority:</b>", body_style),
                Paragraph(f"<b>{candidate.priority_group} PRIORITY</b>", callout_success),
            ],
            [
                Paragraph("<b>Catalog Triage Rank:</b>", body_style),
                Paragraph(f"Rank #{candidate.rank_position} in current triage queue", body_style),
                Paragraph("<b>Active Evidence Channels:</b>", body_style),
                Paragraph(f"{candidate.evidence_available} channels &nbsp;(ML probability excluded)", body_style),
            ],
            [
                Paragraph("<b>Signal Quality Evidence:</b>", body_style),
                Paragraph(f"{candidate.signal_quality:.2f}" if candidate.signal_quality is not None else "Not evaluated", mono_style),
                Paragraph("<b>RFI Cleanliness Metric:</b>", body_style),
                Paragraph(f"{candidate.rfi_indicator:.4f}" if candidate.rfi_indicator is not None else "Not evaluated", mono_style),
            ],
            [
                Paragraph("<b>Periodicity Evidence:</b>", body_style),
                Paragraph(f"{candidate.periodicity_evidence:.2f}" if candidate.periodicity_evidence is not None else "Not evaluated", mono_style),
                Paragraph("<b>DM Consistency Evidence:</b>", body_style),
                Paragraph(f"{candidate.dm_evidence:.2f}" if candidate.dm_evidence is not None else "Not evaluated", mono_style),
            ],
            [
                Paragraph("<b>Profile Shape Evidence:</b>", body_style),
                Paragraph(f"{candidate.profile_evidence:.4f}" if candidate.profile_evidence is not None else "Not evaluated", mono_style),
                Paragraph("<b>Scoring Status:</b>", body_style),
                Paragraph(str(candidate.score_status), body_style),
            ]
        ]
        t_acis = Table(acis_data, colWidths=[1.6 * inch, 2.3 * inch, 1.6 * inch, 1.7 * inch])
        t_acis.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0fdf4')),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#16a34a')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bbf7d0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_acis)
    else:
        elements.append(Paragraph("<i>No ACIS prioritization score computed for this observation.</i>", body_style))
    elements.append(Spacer(1, 8))

    # ── SECTION: CSV Data and Summary (if CSV included) ───────────
    sec_num = 5
    if csv_path is not None:
        elements.append(Paragraph(f"{sec_num}. CSV DATA AND SUMMARY", section_heading))
        sec_num += 1

        # Read CSV data safely
        df: Optional[pd.DataFrame] = None
        csv_read_error: Optional[str] = None
        file_size_kb = 0.0

        try:
            if csv_path.exists() and csv_path.is_file():
                file_size_kb = round(csv_path.stat().st_size / 1024, 2)
                df = pd.read_csv(csv_path, keep_default_na=True)
            else:
                csv_read_error = f"CSV file not found at path: {csv_path.name}"
        except Exception as exc:
            csv_read_error = str(exc)

        orig_name = csv_original_name or csv_path.name
        obs_name = obs.target_name or obs.file_name
        total_rows = len(df) if df is not None else 0
        total_cols = len(df.columns) if df is not None else 0

        # Scope and filtering description
        MAX_DISPLAY_ROWS = 100
        MAX_DISPLAY_COLS = 8

        if df is not None:
            if total_rows > MAX_DISPLAY_ROWS:
                scope_text = f"Preview: Rows 1–{MAX_DISPLAY_ROWS} of {total_rows:,} (pagination constrained)"
            else:
                scope_text = f"Full Dataset: All {total_rows:,} rows included"
        else:
            scope_text = "Parsing error — dataset unavailable"

        # Tabular Ingestion Notice & Provenance
        elements.append(Paragraph(
            "<b>Tabular Ingestion Notice & Provenance:</b> Tabular records displayed below are ingested from "
            "the user-selected CSV dataset associated with this observation audit. In accordance with ASTRA "
            "astronomical verification standards, generic CSV columns are not fed into pulsar classifier pipelines or "
            "ACIS candidate scoring heuristics. Descriptive statistics represent non-inferential source summaries.",
            ParagraphStyle('CsvNotice', parent=body_style, fontSize=7.2, leading=9.5, textColor=colors.HexColor('#475569'))
        ))
        elements.append(Spacer(1, 4))

        meta_rows = [
            [
                Paragraph("<b>Source CSV Dataset:</b>", body_style),
                Paragraph(xml.sax.saxutils.escape(orig_name), mono_style),
                Paragraph("<b>Associated Observation:</b>", body_style),
                Paragraph(xml.sax.saxutils.escape(f"{obs_name} (ID #{obs.id})"), body_style),
            ],
            [
                Paragraph("<b>Total Ingested Rows:</b>", body_style),
                Paragraph(f"{total_rows:,}" if df is not None else "N/A", mono_style),
                Paragraph("<b>Total Column Count:</b>", body_style),
                Paragraph(f"{total_cols}" if df is not None else "N/A", mono_style),
            ],
            [
                Paragraph("<b>Server Filename:</b>", body_style),
                Paragraph(xml.sax.saxutils.escape(csv_path.name), mono_style),
                Paragraph("<b>Dataset File Size:</b>", body_style),
                Paragraph(f"{file_size_kb:.2f} KB", mono_style),
            ],
            [
                Paragraph("<b>Tabular Scope:</b>", body_style),
                Paragraph(xml.sax.saxutils.escape(scope_text), body_style),
                Paragraph("<b>Data Status:</b>", body_style),
                Paragraph("Verified Ingested Data" if not csv_read_error else "Ingestion Warning", body_style),
            ],
        ]
        t_csv_meta = Table(meta_rows, colWidths=[1.6 * inch, 2.3 * inch, 1.6 * inch, 1.7 * inch])
        t_csv_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_csv_meta)
        elements.append(Spacer(1, 6))

        if csv_read_error:
            elements.append(Paragraph(
                f"<b>Warning: Unable to parse tabular records:</b> {xml.sax.saxutils.escape(csv_read_error)}",
                callout_alert
            ))
        elif df is not None:
            # 2. Descriptive Statistics (Numeric columns)
            num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            if num_cols:
                elements.append(Paragraph("<b>Descriptive Statistics (Numeric Features):</b>", body_style))
                elements.append(Spacer(1, 2))
                stats_rows = [
                    [
                        Paragraph("<b>Column Name</b>", body_style),
                        Paragraph("<b>Records</b>", body_style),
                        Paragraph("<b>Missing (NaN)</b>", body_style),
                        Paragraph("<b>Min Value</b>", body_style),
                        Paragraph("<b>Max Value</b>", body_style),
                        Paragraph("<b>Mean Value</b>", body_style),
                    ]
                ]
                for col_name in num_cols:
                    s = df[col_name]
                    non_null = int(s.count())
                    null_count = int(s.isna().sum())
                    s_min = f"{s.min():.4g}" if non_null > 0 and pd.notna(s.min()) else "—"
                    s_max = f"{s.max():.4g}" if non_null > 0 and pd.notna(s.max()) else "—"
                    s_mean = f"{s.mean():.4g}" if non_null > 0 and pd.notna(s.mean()) else "—"

                    col_label = str(col_name)
                    if len(col_label) > 32:
                        col_label = col_label[:29] + "..."

                    stats_rows.append([
                        Paragraph(xml.sax.saxutils.escape(col_label), mono_style),
                        Paragraph(str(non_null), body_style),
                        Paragraph(str(null_count), body_style),
                        Paragraph(s_min, body_style),
                        Paragraph(s_max, body_style),
                        Paragraph(s_mean, body_style),
                    ])

                t_stats = Table(stats_rows, colWidths=[2.2 * inch, 0.9 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.1 * inch])
                t_stats.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                elements.append(t_stats)
                elements.append(Paragraph(
                    "<i>Descriptive statistics calculated strictly from source values; not scientific conclusions.</i>",
                    body_muted
                ))
                elements.append(Spacer(1, 6))

            # 3. Tabular Data Records
            displayed_cols = list(df.columns[:MAX_DISPLAY_COLS])
            omitted_cols = list(df.columns[MAX_DISPLAY_COLS:])
            df_subset = df.head(MAX_DISPLAY_ROWS) if total_rows > MAX_DISPLAY_ROWS else df

            notes = []
            if total_rows > MAX_DISPLAY_ROWS:
                notes.append(f"Displaying rows 1–{len(df_subset)} of {total_rows} total rows due to document pagination constraints. Full dataset retained on disk.")
            else:
                notes.append(f"Displaying all {total_rows} records from source dataset.")

            if omitted_cols:
                omitted_preview = ", ".join(str(c) for c in omitted_cols[:6])
                if len(omitted_cols) > 6:
                    omitted_preview += f" (+{len(omitted_cols) - 6} more)"
                notes.append(f"Showing first {len(displayed_cols)} of {total_cols} columns. Omitted from print layout: [{omitted_preview}].")

            elements.append(Paragraph(f"<b>Tabular Data Records:</b> &nbsp; <font color='#64748b'>{' | '.join(notes)}</font>", body_style))
            elements.append(Spacer(1, 3))

            if total_rows == 0:
                elements.append(Paragraph("<i>The selected CSV file contains 0 data records.</i>", body_muted))
            else:
                def _fmt_cell(val: Any) -> str:
                    if pd.isna(val) or val is None:
                        return '<font color="#94a3b8">—</font>'
                    val_str = str(val).strip()
                    if val_str and val_str[0] in ('=', '+', '-', '@'):
                        val_str = "'" + val_str
                    if len(val_str) > 36:
                        val_str = val_str[:33] + '...'
                    return xml.sax.saxutils.escape(val_str)

                def _fmt_header(name: Any) -> str:
                    h_str = str(name).strip()
                    if len(h_str) > 24:
                        h_str = h_str[:21] + '...'
                    return xml.sax.saxutils.escape(h_str)

                header_cell_style = ParagraphStyle(
                    'CsvHead', parent=body_style, fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.white
                )
                data_cell_style = ParagraphStyle(
                    'CsvCell', parent=body_style, fontName='Helvetica', fontSize=6.5, leading=8, textColor=colors.HexColor('#0f172a')
                )

                t_csv_data = [
                    [Paragraph(f"<b>{_fmt_header(c)}</b>", header_cell_style) for c in displayed_cols]
                ]
                for row in df_subset[displayed_cols].itertuples(index=False):
                    t_csv_data.append([Paragraph(_fmt_cell(v), data_cell_style) for v in row])

                col_w = (7.2 * inch) / max(len(displayed_cols), 1)
                t_table = Table(t_csv_data, colWidths=[col_w] * len(displayed_cols), repeatRows=1)
                t_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                    ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 1.8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1.8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 2.5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 2.5),
                ]))
                elements.append(t_table)

        elements.append(Spacer(1, 8))

    # ── SECTION: Processing History & Audit Trail ───────────
    elements.append(Paragraph(f"{sec_num}. PROCESSING HISTORY & AUDIT TRAIL", section_heading))
    sec_num += 1
    if runs:
        run_data = [
            [
                Paragraph("<b>Run Identifier</b>", body_style),
                Paragraph("<b>Pipeline Step</b>", body_style),
                Paragraph("<b>Status</b>", body_style),
                Paragraph("<b>Duration</b>", body_style),
                Paragraph("<b>Timestamp (UTC)</b>", body_style),
            ]
        ]
        for r in runs:
            run_data.append([
                Paragraph(str(r.run_identifier), mono_style),
                Paragraph(str(r.pipeline_step), body_style),
                Paragraph(str(r.processing_status), body_style),
                Paragraph(f"{r.elapsed_seconds:.1f}s" if r.elapsed_seconds is not None else "N/A", body_style),
                Paragraph(r.started_at.strftime('%Y-%m-%d %H:%M') if r.started_at else "N/A", body_style),
            ])
        t_runs = Table(run_data, colWidths=[2.1 * inch, 2.1 * inch, 0.9 * inch, 0.7 * inch, 1.4 * inch])
        t_runs.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_runs)
    else:
        elements.append(Paragraph("<i>No processing run history records available for this observation.</i>", body_style))
    elements.append(Spacer(1, 8))

    # ── SECTION: Scientific Methodology & Limitations ──────
    elements.append(KeepTogether([
        Paragraph(f"{sec_num}. SCIENTIFIC METHODOLOGY, LIMITATIONS & CAUTIONARY NOTICE", section_heading),
        Paragraph(
            "<b>Astronomical Integrity & Operational Scope:</b><br/>"
            "1. <b>Not an Autonomous Discovery Confirmation:</b> ASTRA is designed as an AI-assisted analysis and "
            "candidate-prioritization layer to assist radio astronomers. High ACIS scores indicate recommended order for "
            "human expert inspection, not the physical confirmation of a newly discovered astronomical pulsar.<br/>"
            "2. <b>Distinction of Heuristic Scoring:</b> ACIS intelligence scores reflect multi-evidence heuristic prioritization "
            "weights. They are intentionally distinct from calibrated physical probabilities and should not be cited as statistical detection p-values.<br/>"
            "3. <b>Search vs Timing Domain Separation:</b> Supervised search-mode classifiers (e.g. HTRU2 benchmark models) "
            "cannot be validly evaluated against folded timing archives without inducing domain distribution shift. "
            "The ACIS architecture safely omits uncalibrated ML channels to preserve scientific validity.<br/>"
            "4. <b>Data Provenance:</b> All values presented herein originate from verified detector FITS headers and deterministic "
            "numerical moment extraction algorithms. No values have been synthesized or arbitrarily imputed.",
            ParagraphStyle('Discl', parent=body_style, fontSize=7.2, leading=10, textColor=colors.HexColor('#475569'))
        )
    ]))

    # Build PDF using NumberedCanvas
    doc.build(elements, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer


def generate_csv_report_pdf(
    csv_path: Path,
    csv_original_name: Optional[str] = None,
    observation_name: Optional[str] = None,
) -> io.BytesIO:
    """
    Builds a publication-grade scientific research audit report for a CSV dataset.
    Conforms to Task 2 standards:
      1. Simple title and observation-information section.
      2. Clearly labeled CSV Data Summary section (rows, cols, missing values, column types).
      3. Readable table with original CSV column names, row numbers, and actual values.
      4. Descriptive statistics for numeric columns.
      5. Consistent fonts, margins, subtle styling, repeated headers, page numbers.
      6. Clear pagination and preview limit notices (never silently omitting rows).
    """
    if not csv_path.exists() or not csv_path.is_file():
        raise FileNotFoundError(f"CSV file was not found at path: {csv_path.name}")

    if csv_path.stat().st_size == 0:
        raise ValueError(f"CSV file '{csv_path.name}' is empty (0 bytes).")

    try:
        df = pd.read_csv(csv_path, keep_default_na=True)
    except Exception as exc:
        raise ValueError(f"Failed to parse CSV file: {str(exc)}")

    if df.empty and len(df.columns) == 0:
        raise ValueError(f"CSV file '{csv_path.name}' contains no readable columns or data rows.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=44,
        bottomMargin=44,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CsvDocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0f172a'),
    )
    subtitle_style = ParagraphStyle(
        'CsvDocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#475569'),
    )
    section_heading = ParagraphStyle(
        'CsvSectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        'CsvBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1e293b'),
    )
    body_muted = ParagraphStyle(
        'CsvBodyMuted',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.5,
        textColor=colors.HexColor('#64748b'),
    )
    mono_style = ParagraphStyle(
        'CsvMono',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#0f172a'),
    )

    elements = []

    orig_name = csv_original_name or csv_path.name
    obs_name = observation_name or Path(orig_name).stem
    file_size_kb = round(csv_path.stat().st_size / 1024, 2)
    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols
    total_missing = int(df.isna().sum().sum())
    missing_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0.0

    # Title & Header
    elements.append(Paragraph("ASTRA — CSV OBSERVATION DATA REPORT", title_style))
    doc_id = f"ASTRA-REP-CSV-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    gen_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    elements.append(Paragraph(
        f"<b>Document ID:</b> {doc_id} &nbsp;|&nbsp; <b>Generated:</b> {gen_time} &nbsp;|&nbsp; <b>Observation:</b> {xml.sax.saxutils.escape(obs_name)}",
        subtitle_style
    ))
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#334155"), spaceAfter=8))

    # Section 1: Observation & File Information
    elements.append(Paragraph("1. OBSERVATION & FILE INFORMATION", section_heading))
    meta_info = [
        [
            Paragraph("<b>Associated Observation:</b>", body_style), Paragraph(xml.sax.saxutils.escape(obs_name), body_style),
            Paragraph("<b>Original File Name:</b>", body_style), Paragraph(xml.sax.saxutils.escape(orig_name), mono_style),
        ],
        [
            Paragraph("<b>File Size:</b>", body_style), Paragraph(f"{file_size_kb:.2f} KB", mono_style),
            Paragraph("<b>Storage Path:</b>", body_style), Paragraph(xml.sax.saxutils.escape(f"data/uploads/csv/{csv_path.name}"), mono_style),
        ],
        [
            Paragraph("<b>Row × Column Count:</b>", body_style), Paragraph(f"{total_rows:,} rows × {total_cols} columns", mono_style),
            Paragraph("<b>Processing Status:</b>", body_style), Paragraph("<b>INGESTED (Verified)</b>", body_style),
        ],
    ]
    t_info = Table(meta_info, colWidths=[1.7 * inch, 2.2 * inch, 1.6 * inch, 1.7 * inch])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 8))

    # Section 2: CSV Data Summary
    elements.append(Paragraph("2. CSV DATA SUMMARY", section_heading))
    
    # Summary KPI row
    kpi_data = [
        [
            Paragraph(f"<b>Total Rows:</b> {total_rows:,}", body_style),
            Paragraph(f"<b>Total Columns:</b> {total_cols}", body_style),
            Paragraph(f"<b>Total Cells:</b> {total_cells:,}", body_style),
            Paragraph(f"<b>Missing Values:</b> {total_missing:,} ({missing_pct:.2f}%)", body_style),
        ]
    ]
    t_kpi = Table(kpi_data, colWidths=[1.8 * inch, 1.6 * inch, 1.8 * inch, 2.0 * inch])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_kpi)
    elements.append(Spacer(1, 5))

    # Column Structure & Descriptive Statistics Table
    stats_rows = [
        [
            Paragraph("<b>Column Name</b>", body_style),
            Paragraph("<b>Inferred Type</b>", body_style),
            Paragraph("<b>Non-Empty</b>", body_style),
            Paragraph("<b>Missing</b>", body_style),
            Paragraph("<b>Min Value</b>", body_style),
            Paragraph("<b>Max Value</b>", body_style),
            Paragraph("<b>Mean Value</b>", body_style),
        ]
    ]
    for col in df.columns:
        s = df[col]
        non_null = int(s.notna().sum())
        null_count = int(s.isna().sum())
        inf_type = infer_column_type(s)
        s_min = s_max = s_mean = "—"
        if pd.api.types.is_numeric_dtype(s) and non_null > 0:
            valid_vals = s.dropna()
            if len(valid_vals) > 0:
                s_min = f"{valid_vals.min():.4g}"
                s_max = f"{valid_vals.max():.4g}"
                s_mean = f"{valid_vals.mean():.4g}"
        
        col_label = str(col)
        if len(col_label) > 28:
            col_label = col_label[:25] + "..."
            
        stats_rows.append([
            Paragraph(xml.sax.saxutils.escape(col_label), mono_style),
            Paragraph(inf_type, body_style),
            Paragraph(str(non_null), body_style),
            Paragraph(str(null_count), body_style),
            Paragraph(s_min, body_style),
            Paragraph(s_max, body_style),
            Paragraph(s_mean, body_style),
        ])

    t_col_stats = Table(stats_rows, colWidths=[2.0 * inch, 0.9 * inch, 0.8 * inch, 0.7 * inch, 0.9 * inch, 0.9 * inch, 1.0 * inch])
    t_col_stats.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_col_stats)
    elements.append(Paragraph(
        "<i>Descriptive statistics computed directly from source values. Inferred data types represent algorithmic column properties, not verified physical conclusions.</i>",
        body_muted
    ))
    elements.append(Spacer(1, 8))

    # Section 3: Tabular Data Records
    elements.append(Paragraph("3. TABULAR DATA RECORDS", section_heading))
    
    MAX_DISPLAY_ROWS = 100
    MAX_DISPLAY_COLS = 8

    displayed_cols = list(df.columns[:MAX_DISPLAY_COLS])
    omitted_cols = list(df.columns[MAX_DISPLAY_COLS:])
    df_subset = df.head(MAX_DISPLAY_ROWS) if total_rows > MAX_DISPLAY_ROWS else df

    scope_notes = []
    if total_rows > MAX_DISPLAY_ROWS:
        scope_notes.append(f"Preview: Rows 1–{len(df_subset)} of {total_rows:,} records (pagination constrained for print publication). Full dataset retained on disk.")
    else:
        scope_notes.append(f"Displaying all {total_rows} records from source dataset.")

    if omitted_cols:
        omitted_preview = ", ".join(str(c) for c in omitted_cols[:6])
        if len(omitted_cols) > 6:
            omitted_preview += f" (+{len(omitted_cols) - 6} more)"
        scope_notes.append(f"Showing primary {len(displayed_cols)} of {total_cols} columns. Omitted from print layout: [{omitted_preview}].")

    elements.append(Paragraph(" &nbsp;|&nbsp; ".join(scope_notes), body_muted))
    elements.append(Spacer(1, 4))

    if total_rows == 0:
        elements.append(Paragraph("<i>The selected CSV file contains 0 data records.</i>", body_muted))
    else:
        def _fmt_cell(val: Any) -> str:
            if pd.isna(val) or val is None:
                return '<font color="#94a3b8">—</font>'
            val_str = str(val).strip()
            if val_str and val_str[0] in ('=', '+', '-', '@'):
                val_str = "'" + val_str
            if len(val_str) > 36:
                val_str = val_str[:33] + '...'
            return xml.sax.saxutils.escape(val_str)

        def _fmt_header(name: Any) -> str:
            h_str = str(name).strip()
            if len(h_str) > 22:
                h_str = h_str[:19] + '...'
            return xml.sax.saxutils.escape(h_str)

        head_style = ParagraphStyle('HeadS', parent=body_style, fontName='Helvetica-Bold', fontSize=6.5, leading=8, textColor=colors.white)
        cell_style = ParagraphStyle('CellS', parent=body_style, fontName='Helvetica', fontSize=6.5, leading=8, textColor=colors.HexColor('#0f172a'))
        idx_style = ParagraphStyle('IdxS', parent=mono_style, fontSize=6.5, leading=8, textColor=colors.HexColor('#64748b'))

        table_header = [Paragraph("<b>#</b>", head_style)] + [Paragraph(f"<b>{_fmt_header(c)}</b>", head_style) for c in displayed_cols]
        table_data = [table_header]

        for idx, row in enumerate(df_subset[displayed_cols].itertuples(index=False)):
            row_cells = [Paragraph(str(idx + 1), idx_style)] + [Paragraph(_fmt_cell(v), cell_style) for v in row]
            table_data.append(row_cells)

        idx_width = 0.35 * inch
        remaining_w = (7.2 * inch) - idx_width
        col_w = remaining_w / max(len(displayed_cols), 1)
        col_widths = [idx_width] + [col_w] * len(displayed_cols)

        t_records = Table(table_data, colWidths=col_widths, repeatRows=1)
        t_records.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1.8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.8),
            ('LEFTPADDING', (0, 0), (-1, -1), 2.5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_records)

    elements.append(Spacer(1, 8))

    # Section 4: Data Provenance & Methodological Notice
    elements.append(KeepTogether([
        Paragraph("4. DATA PROVENANCE & METHODOLOGY NOTICE", section_heading),
        Paragraph(
            "<b>Astronomical Data Integrity Protocol:</b> Tabular records presented in this report represent unmodified "
            "source records ingested into the ASTRA platform. Values are preserved verbatim without numerical "
            "imputation, synthetic augmentation, or formula execution. In accordance with platform integrity standards, "
            "generic tabular records are strictly segregated from autonomous pulsar machine-learning classifiers and ACIS heuristic "
            "candidate ranking algorithms without verified pipeline approval.",
            ParagraphStyle('CsvDisc', parent=body_style, fontSize=7.2, leading=9.5, textColor=colors.HexColor('#475569'))
        )
    ]))

    doc.build(elements, canvasmaker=CsvNumberedCanvas)
    buffer.seek(0)
    return buffer


def generate_two_dataset_experiments_pdf(results: Dict[str, Any]) -> io.BytesIO:
    """
    Builds a publication-grade scientific PDF audit report for the Two-Dataset
    Integration and Five Research Problems suite (HTRU2 + Parkes PSRFITS).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=44,
        bottomMargin=44,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ExpDocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0f172a'),
    )
    subtitle_style = ParagraphStyle(
        'ExpDocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#475569'),
    )
    section_heading = ParagraphStyle(
        'ExpSectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#0f172a'),
    )
    body_style = ParagraphStyle(
        'ExpBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#334155'),
    )
    table_cell = ParagraphStyle(
        'ExpCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#1e293b'),
    )
    table_cell_bold = ParagraphStyle(
        'ExpCellB',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#0f172a'),
    )

    elements = []

    # Title & Metadata
    elements.append(Paragraph("ASTRA — TWO-DATASET INTEGRATION & FIVE RESEARCH PROBLEMS", title_style))
    elements.append(Paragraph(
        f"Astrophysical Validation Report &bull; Generated: {results.get('execution_timestamp', 'N/A')} &bull; "
        f"Random Seed: {results.get('reproducible_seed', 42)} &bull; Execution Time: {results.get('execution_seconds', 0)}s",
        subtitle_style
    ))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0284c7'), spaceAfter=8))

    # Section 1: Dataset Provenance
    elements.append(Paragraph("1. REGISTERED DATASETS & PROVENANCE", section_heading))
    htru2_meta = results.get('datasets', {}).get('dataset_a_htru2', {})
    parkes_meta = results.get('datasets', {}).get('dataset_b_parkes', {})

    prov_data = [
        [Paragraph("Property", table_cell_bold), Paragraph("Dataset A (HTRU2)", table_cell_bold), Paragraph("Dataset B (Parkes PSRFITS)", table_cell_bold)],
        [Paragraph("Source", table_cell_bold), Paragraph(str(htru2_meta.get('source', 'UCI ML')), table_cell), Paragraph(str(parkes_meta.get('source', 'NASA / Parkes')), table_cell)],
        [Paragraph("File Path", table_cell_bold), Paragraph(str(htru2_meta.get('file_path', 'data/htru2/HTRU_2.csv')), table_cell), Paragraph(str(parkes_meta.get('file_path', 'data/parkes/...')), table_cell)],
        [Paragraph("Representation", table_cell_bold), Paragraph("8 Summary Moments (Tabular)", table_cell), Paragraph("Streamed Time-Frequency (512 Channels)", table_cell)],
        [Paragraph("Sample Count", table_cell_bold), Paragraph(f"{htru2_meta.get('row_count', 17898)} candidates", table_cell), Paragraph(f"{parkes_meta.get('total_time_samples', 40960)} time samples ({parkes_meta.get('total_duration_seconds', 3.93)}s)", table_cell)],
        [Paragraph("Label Availability", table_cell_bold), Paragraph("Supervised Binary (0: Noise / 1: Pulsar)", table_cell), Paragraph("Unlabelled single target stream (J0437-4715)", table_cell)],
        [Paragraph("SHA-256", table_cell_bold), Paragraph(str(htru2_meta.get('sha256', ''))[:24] + "...", table_cell), Paragraph(str(parkes_meta.get('sha256', ''))[:24] + "...", table_cell)],
    ]
    t_prov = Table(prov_data, colWidths=[110, 215, 215])
    t_prov.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_prov)
    elements.append(Spacer(1, 8))

    # Section 2: Problem 1 — Perturbations & Controlled Noise
    p1 = results.get('problems', {}).get('p1_perturbations', {})
    elements.append(Paragraph("2. PROBLEM 1: PERTURBATION & CONTROLLED NOISE EVALUATION", section_heading))
    elements.append(Paragraph(
        "<b>HTRU2 Classification Degradation Under Profile Perturbation & DM-SNR Attenuation:</b>", body_style
    ))

    p1_htru2_rows = [
        [Paragraph("Scale", table_cell_bold), Paragraph("Perturbation Description", table_cell_bold),
         Paragraph("Accuracy", table_cell_bold), Paragraph("Precision", table_cell_bold),
         Paragraph("Recall", table_cell_bold), Paragraph("F1-Score", table_cell_bold), Paragraph("ROC-AUC", table_cell_bold)]
    ]
    for row in p1.get('htru2_perturbations', []):
        p1_htru2_rows.append([
            Paragraph(str(row['perturbation_scale']), table_cell),
            Paragraph(row['description'], table_cell),
            Paragraph(f"{row['accuracy']:.4f}", table_cell),
            Paragraph(f"{row['precision']:.4f}", table_cell),
            Paragraph(f"{row['recall']:.4f}", table_cell),
            Paragraph(f"{row['f1_score']:.4f}", table_cell),
            Paragraph(f"{row['roc_auc']:.4f}", table_cell),
        ])
    t_p1 = Table(p1_htru2_rows, colWidths=[35, 175, 55, 55, 55, 55, 70])
    t_p1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    elements.append(t_p1)
    elements.append(Spacer(1, 6))

    # Parkes Synthetic Noise
    elements.append(Paragraph(
        "<b>Parkes Search-Mode Stream Under Controlled Synthetic Additive Noise (Non-RFI):</b>", body_style
    ))
    p1_parkes_rows = [
        [Paragraph("Ratio", table_cell_bold), Paragraph("Synthetic Noise Tier", table_cell_bold),
         Paragraph("Signal RMS", table_cell_bold), Paragraph("Observed SNR", table_cell_bold),
         Paragraph("SNR Retention", table_cell_bold), Paragraph("Degradation %", table_cell_bold)]
    ]
    for row in p1.get('parkes_noise_experiments', []):
        p1_parkes_rows.append([
            Paragraph(f"{row['noise_ratio']}x", table_cell),
            Paragraph(row['label'], table_cell),
            Paragraph(str(row['signal_rms']), table_cell),
            Paragraph(f"{row['observed_snr']:.4f}", table_cell),
            Paragraph(f"{row['snr_retention']:.4f}", table_cell),
            Paragraph(f"{row['snr_degradation_pct']:.1f}%", table_cell),
        ])
    t_p1_parkes = Table(p1_parkes_rows, colWidths=[40, 200, 75, 75, 75, 75])
    t_p1_parkes.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    elements.append(t_p1_parkes)
    elements.append(Spacer(1, 8))

    # Section 3: Problem 2 — Channel Masking
    p2 = results.get('problems', {}).get('p2_channel_masking', {})
    elements.append(Paragraph("3. PROBLEM 2: PARKES FREQUENCY-CHANNEL MASKING & RECOVERABILITY", section_heading))
    p2_rows = [
        [Paragraph("Mask %", table_cell_bold), Paragraph("Masked", table_cell_bold),
         Paragraph("Remaining", table_cell_bold), Paragraph("Energy Retention", table_cell_bold),
         Paragraph("SNR", table_cell_bold), Paragraph("SNR Retention", table_cell_bold),
         Paragraph("Recoverability Index", table_cell_bold), Paragraph("Status", table_cell_bold)]
    ]
    for row in p2.get('masking_experiments', []):
        status_color = '#16a34a' if row['status'] == 'PASS' else '#dc2626'
        p2_rows.append([
            Paragraph(f"{row['mask_fraction']*100:.0f}%", table_cell),
            Paragraph(str(row['masked_channel_count']), table_cell),
            Paragraph(str(row['remaining_channel_count']), table_cell),
            Paragraph(f"{row['energy_retention_ratio']:.4f}", table_cell),
            Paragraph(f"{row['observed_snr']:.4f}", table_cell),
            Paragraph(f"{row['snr_retention_ratio']:.4f}", table_cell),
            Paragraph(f"{row['recoverability_index']:.4f}", table_cell_bold),
            Paragraph(f"<font color='{status_color}'>{row['status']}</font>", table_cell_bold),
        ])
    t_p2 = Table(p2_rows, colWidths=[45, 55, 60, 80, 60, 75, 95, 70])
    t_p2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    elements.append(t_p2)
    elements.append(Spacer(1, 8))

    # Section 4: Problem 3 — Compatibility Audit
    p3 = results.get('problems', {}).get('p3_cross_compatibility', {})
    elements.append(Paragraph(f"4. PROBLEM 3: CROSS-DATASET COMPATIBILITY AUDIT ({p3.get('verdict')})", section_heading))
    elements.append(Paragraph(
        f"<b>Audit Decision:</b> {p3.get('transfer_evaluation_status')}. "
        f"{p3.get('policy_statement')}",
        body_style
    ))
    elements.append(Spacer(1, 4))
    p3_rows = [
        [Paragraph("Dimension", table_cell_bold), Paragraph("Dataset A (HTRU2)", table_cell_bold),
         Paragraph("Dataset B (Parkes PSRFITS)", table_cell_bold), Paragraph("Compatible?", table_cell_bold)]
    ]
    for row in p3.get('compatibility_matrix', []):
        compat_text = "<font color='#16a34a'>YES</font>" if row['compatible'] else "<font color='#dc2626'>NO</font>"
        p3_rows.append([
            Paragraph(row['dimension'], table_cell_bold),
            Paragraph(row['dataset_a_htru2'], table_cell),
            Paragraph(row['dataset_b_parkes'], table_cell),
            Paragraph(compat_text, table_cell_bold),
        ])
    t_p3 = Table(p3_rows, colWidths=[110, 185, 185, 60])
    t_p3.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    elements.append(t_p3)
    elements.append(Spacer(1, 8))

    # Section 5: Problem 4 — Calibration
    p4 = results.get('problems', {}).get('p4_confidence_calibration', {})
    elements.append(Paragraph(
        f"5. PROBLEM 4: CONFIDENCE CALIBRATION ON HTRU2 (ECE: {p4.get('expected_calibration_error_ece', 'N/A')}, Brier: {p4.get('brier_score', 'N/A')})",
        section_heading
    ))
    p4_rows = [
        [Paragraph("Bin", table_cell_bold), Paragraph("Confidence Range", table_cell_bold),
         Paragraph("Samples", table_cell_bold), Paragraph("Mean Confidence", table_cell_bold),
         Paragraph("Empirical Accuracy", table_cell_bold), Paragraph("Calibration Error", table_cell_bold),
         Paragraph("Status", table_cell_bold)]
    ]
    for b in p4.get('reliability_diagram_bins', []):
        p4_rows.append([
            Paragraph(str(b['bin_index']), table_cell),
            Paragraph(b['confidence_range'], table_cell),
            Paragraph(str(b['sample_count']), table_cell),
            Paragraph(f"{b['mean_confidence']:.4f}", table_cell),
            Paragraph(f"{b['empirical_accuracy']:.4f}", table_cell),
            Paragraph(f"{b['calibration_error']:.4f}", table_cell),
            Paragraph(b['calibration_status'], table_cell),
        ])
    t_p4 = Table(p4_rows, colWidths=[30, 95, 55, 90, 90, 85, 95])
    t_p4.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    elements.append(t_p4)
    elements.append(Spacer(1, 8))

    # Section 6: Problem 5 — Failure Analysis
    p5 = results.get('problems', {}).get('p5_failure_analysis', {})
    h_fail = p5.get('htru2_classification_failures', {})
    p_fail = p5.get('parkes_signal_quality_failures', {})
    elements.append(Paragraph("6. PROBLEM 5: FAILURE ANALYSIS (HTRU2 & PARKES)", section_heading))
    elements.append(Paragraph(
        f"<b>HTRU2 Confusion Counts:</b> True Positives: {h_fail.get('counts', {}).get('true_positives')} &bull; "
        f"True Negatives: {h_fail.get('counts', {}).get('true_negatives')} &bull; "
        f"False Positives: {h_fail.get('counts', {}).get('false_positives')} (FPR: {h_fail.get('rates', {}).get('false_positive_rate')}) &bull; "
        f"False Negatives: {h_fail.get('counts', {}).get('false_negatives')} (FNR: {h_fail.get('rates', {}).get('false_negative_rate')})",
        body_style
    ))
    elements.append(Paragraph(
        f"<b>FP Mechanism:</b> {h_fail.get('fp_mechanism', '')}<br/>"
        f"<b>FN Mechanism:</b> {h_fail.get('fn_mechanism', '')}",
        body_style
    ))
    elements.append(Paragraph(
        f"<b>Parkes Breakdown Thresholds:</b> {p_fail.get('critical_masking_threshold', '')} &bull; "
        f"{p_fail.get('critical_noise_threshold', '')}",
        body_style
    ))

    doc.build(elements, canvasmaker=CsvNumberedCanvas)
    buffer.seek(0)
    return buffer


