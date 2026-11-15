# ============================================================
#  ASTRA Cloud — Research Web Collector Router
#  File   : backend/app/routers/collector.py
#  Purpose: REST API endpoints for discovering, retrieving,
#           and querying astronomical research literature and
#           dataset metadata from official interfaces.
# ============================================================

import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from backend.app.database import get_db
from backend.app.models import ResearchRecord
from backend.app.schemas import (
    CollectorSourceInfo,
    CollectorQueryRequest,
    CollectorQueryResponse,
    ResearchRecordResponse,
    ResearchRecordListResponse,
    SCIENTIFIC_COLLECTOR_DISCLAIMER,
)
from backend.app.services.collector_service import collector_service

router = APIRouter(
    prefix="/api/collector",
    tags=["Research Collector"],
    responses={
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"},
    },
)


@router.get(
    "/sources",
    response_model=List[CollectorSourceInfo],
    summary="List supported official metadata sources",
)
def list_collector_sources() -> List[CollectorSourceInfo]:
    """
    Returns all supported and modularly planned metadata sources for
    astronomical literature and dataset discovery.
    """
    return collector_service.list_sources()


@router.post(
    "/query",
    response_model=CollectorQueryResponse,
    summary="Query official astronomy metadata interfaces",
)
def query_research_metadata(
    req: CollectorQueryRequest,
    db: Session = Depends(get_db),
) -> CollectorQueryResponse:
    """
    Execute a live metadata search against supported official interfaces (e.g., arXiv).
    Normalizes fields, validates canonical URLs, deduplicates records, and
    optionally persists unique records to the research catalog.
    """
    try:
        records, total_found, total_returned, dedup_count, elapsed = (
            collector_service.execute_collection(
                query=req.query,
                source_name=req.source,
                category=req.category,
                max_results=req.max_results,
                save_to_db=req.save_to_db,
                db=db,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Collector service error while querying {req.source}: {exc}",
        )

    return CollectorQueryResponse(
        query=req.query,
        source=req.source,
        total_found=total_found,
        total_returned=total_returned,
        total_deduplicated=dedup_count,
        total_saved=total_returned if req.save_to_db else 0,
        items=records,
        scientific_disclaimer=SCIENTIFIC_COLLECTOR_DISCLAIMER,
        execution_seconds=round(elapsed, 3),
    )


def _serialize_record(r: ResearchRecord) -> ResearchRecordResponse:
    """Helper to deserialize author JSON and return typed response."""
    authors = []
    if r.authors:
        try:
            authors = json.loads(r.authors)
        except Exception:
            authors = [a.strip() for a in r.authors.split(",") if a.strip()]

    return ResearchRecordResponse(
        id=r.id,
        record_type=r.record_type,
        title=r.title,
        authors=authors,
        abstract=r.abstract,
        publication_date=r.publication_date,
        identifier=r.identifier,
        source_name=r.source_name,
        canonical_url=r.canonical_url,
        retrieval_timestamp=r.retrieval_timestamp,
        retrieval_status=r.retrieval_status,
        scientific_disclaimer=SCIENTIFIC_COLLECTOR_DISCLAIMER,
    )


@router.get(
    "/records",
    response_model=ResearchRecordListResponse,
    summary="List collected research records with filtering",
)
def list_collected_records(
    q: Optional[str] = Query(None, description="Search keyword in title or abstract"),
    source: Optional[str] = Query(None, description="Filter by source provider (e.g. 'arXiv')"),
    record_type: Optional[str] = Query(None, description="Filter by record type ('paper' or 'dataset')"),
    limit: int = Query(20, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
) -> ResearchRecordListResponse:
    """
    Retrieve stored research records from PostgreSQL with optional text search,
    source filtering, and pagination.
    """
    query = db.query(ResearchRecord)

    if source:
        query = query.filter(ResearchRecord.source_name == source)
    if record_type:
        query = query.filter(ResearchRecord.record_type == record_type)
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                ResearchRecord.title.ilike(term),
                ResearchRecord.abstract.ilike(term),
                ResearchRecord.identifier.ilike(term),
            )
        )

    total = query.count()
    items = query.order_by(desc(ResearchRecord.retrieval_timestamp)).offset(offset).limit(limit).all()

    return ResearchRecordListResponse(
        total=total,
        items=[_serialize_record(r) for r in items],
        scientific_disclaimer=SCIENTIFIC_COLLECTOR_DISCLAIMER,
    )


@router.get(
    "/records/{record_id}",
    response_model=ResearchRecordResponse,
    summary="Get single research record detail",
)
def get_collected_record_detail(
    record_id: int,
    db: Session = Depends(get_db),
) -> ResearchRecordResponse:
    """Retrieve complete metadata and provenance for a single collected research record."""
    record = db.query(ResearchRecord).filter(ResearchRecord.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research record with ID {record_id} not found.",
        )
    return _serialize_record(record)


# ============================================================
# Literature Extraction Endpoints
# ============================================================

from backend.app.models import PaperExtraction
from backend.app.schemas import (
    ExtractionRequest,
    PaperExtractionResponse,
    ExtractedResearchDetails,
)
from backend.app.services.extraction_service import literature_extractor


@router.post(
    "/extract",
    response_model=PaperExtractionResponse,
    summary="Extract grounded scientific details from paper metadata",
)
def extract_paper_details(
    req: ExtractionRequest,
    db: Session = Depends(get_db),
) -> PaperExtractionResponse:
    """
    Extract factual research attributes (problem, datasets, algorithms, features,
    evaluation metrics, findings, limitations, access status, evidence locations)
    from a collected record or submitted text.
    Unsupported fields are marked 'Not available in retrieved source'.
    """
    record = None
    if req.record_id:
        record = db.query(ResearchRecord).filter(ResearchRecord.id == req.record_id).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research record with ID {req.record_id} not found.",
            )
        title = record.title
        abstract = record.abstract
        identifier = record.identifier
        canonical_url = record.canonical_url
        source_name = record.source_name
        raw_meta = json.loads(record.raw_metadata_json) if record.raw_metadata_json else {}
    else:
        if not req.title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either record_id or title must be provided for extraction.",
            )
        title = req.title
        abstract = req.abstract or ""
        identifier = req.identifier or f"adhoc:{hash(title)}"
        canonical_url = req.canonical_url or "https://arxiv.org"
        source_name = req.source_name or "arXiv"
        raw_meta = req.raw_metadata or {}

    details, provenance = literature_extractor.extract_from_record(
        title=title,
        abstract=abstract,
        identifier=identifier,
        canonical_url=canonical_url,
        source_name=source_name,
        raw_metadata=raw_meta,
    )

    extraction_id = None
    if req.save_to_db:
        pe = literature_extractor.persist_extraction(
            db=db,
            record_id=record.id if record else None,
            identifier=identifier,
            title=title,
            details=details,
            provenance=provenance,
        )
        extraction_id = pe.id

    return PaperExtractionResponse(
        id=extraction_id,
        record_id=record.id if record else None,
        identifier=identifier,
        title=title,
        extracted_details=details,
        provenance=provenance,
        extracted_at=datetime.now(timezone.utc),
        scientific_disclaimer=SCIENTIFIC_COLLECTOR_DISCLAIMER,
    )


@router.get(
    "/records/{record_id}/extraction",
    response_model=PaperExtractionResponse,
    summary="Get or generate extracted literature facts for a research record",
)
def get_record_extraction(
    record_id: int,
    db: Session = Depends(get_db),
) -> PaperExtractionResponse:
    """
    Retrieve stored extraction details for a record. If not yet extracted,
    runs the extraction pipeline on the record's abstract, persists it, and returns it.
    """
    record = db.query(ResearchRecord).filter(ResearchRecord.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research record with ID {record_id} not found.",
        )

    pe = db.query(PaperExtraction).filter(PaperExtraction.record_id == record_id).first()
    if pe:
        # Deserialize stored extraction
        details = ExtractedResearchDetails(
            research_problem=pe.research_problem,
            dataset_name=pe.dataset_name,
            dataset_type=pe.dataset_type,
            algorithms_or_models=json.loads(pe.algorithms_or_models),
            feature_types=json.loads(pe.feature_types),
            evaluation_metrics=json.loads(pe.evaluation_metrics),
            main_reported_findings=pe.main_reported_findings,
            stated_limitations=pe.stated_limitations,
            full_text_availability=pe.full_text_availability,
            licence_or_access_status=pe.licence_or_access_status,
            source_url=pe.source_url,
            doi=pe.doi,
            evidence_locations=json.loads(pe.evidence_locations_json),
            is_inferred=False,
        )
        prov = json.loads(pe.provenance_json) if pe.provenance_json else {}
        return PaperExtractionResponse(
            id=pe.id,
            record_id=record.id,
            identifier=pe.identifier,
            title=record.title,
            extracted_details=details,
            provenance=prov,
            extracted_at=pe.extracted_at,
            scientific_disclaimer=SCIENTIFIC_COLLECTOR_DISCLAIMER,
        )

    # Perform on-demand extraction
    raw_meta = json.loads(record.raw_metadata_json) if record.raw_metadata_json else {}
    details, provenance = literature_extractor.extract_from_record(
        title=record.title,
        abstract=record.abstract,
        identifier=record.identifier,
        canonical_url=record.canonical_url,
        source_name=record.source_name,
        raw_metadata=raw_meta,
    )
    saved_pe = literature_extractor.persist_extraction(
        db=db,
        record_id=record.id,
        identifier=record.identifier,
        title=record.title,
        details=details,
        provenance=provenance,
    )

    return PaperExtractionResponse(
        id=saved_pe.id,
        record_id=record.id,
        identifier=record.identifier,
        title=record.title,
        extracted_details=details,
        provenance=provenance,
        extracted_at=saved_pe.extracted_at,
        scientific_disclaimer=SCIENTIFIC_COLLECTOR_DISCLAIMER,
    )


# ============================================================
# Literature Comparison & Synthesis Endpoints
# ============================================================

import os
from backend.app.schemas import (
    LiteratureComparisonRequest,
    LiteratureComparisonResponse,
)
from backend.app.services.comparison_service import literature_comparator, REPORTS_DIR


@router.post(
    "/compare",
    response_model=LiteratureComparisonResponse,
    summary="Generate comparative literature synthesis across records",
)
def compare_literature_records(
    req: LiteratureComparisonRequest,
    db: Session = Depends(get_db),
) -> LiteratureComparisonResponse:
    """
    Generate a structured comparison table, research gap candidates, conflicting
    setups, and manual verification items across collected and extracted papers.
    """
    items = []

    # 1. Load from DB
    if req.record_ids or req.record_ids is None:
        db_query = db.query(ResearchRecord)
        if req.record_ids:
            db_query = db_query.filter(ResearchRecord.id.in_(req.record_ids))
        records = db_query.all()
        for rec in records:
            pe = db.query(PaperExtraction).filter(PaperExtraction.record_id == rec.id).first()
            if pe:
                det = ExtractedResearchDetails(
                    research_problem=pe.research_problem,
                    dataset_name=pe.dataset_name,
                    dataset_type=pe.dataset_type,
                    algorithms_or_models=json.loads(pe.algorithms_or_models),
                    feature_types=json.loads(pe.feature_types),
                    evaluation_metrics=json.loads(pe.evaluation_metrics),
                    main_reported_findings=pe.main_reported_findings,
                    stated_limitations=pe.stated_limitations,
                    full_text_availability=pe.full_text_availability,
                    licence_or_access_status=pe.licence_or_access_status,
                    source_url=pe.source_url,
                    doi=pe.doi,
                    evidence_locations=json.loads(pe.evidence_locations_json),
                    is_inferred=False,
                )
            else:
                raw_meta = json.loads(rec.raw_metadata_json) if rec.raw_metadata_json else {}
                det, _ = literature_extractor.extract_from_record(
                    title=rec.title,
                    abstract=rec.abstract,
                    identifier=rec.identifier,
                    canonical_url=rec.canonical_url,
                    source_name=rec.source_name,
                    raw_metadata=raw_meta,
                )
            items.append((rec.identifier, rec.title, det))

    # 2. Add adhoc records if provided
    if req.include_adhoc_records:
        for adhoc in req.include_adhoc_records:
            t = adhoc.title or "Untitled Adhoc Paper"
            ident = adhoc.identifier or f"adhoc:{hash(t)}"
            det, _ = literature_extractor.extract_from_record(
                title=t,
                abstract=adhoc.abstract or "",
                identifier=ident,
                canonical_url=adhoc.canonical_url or "https://arxiv.org",
                source_name=adhoc.source_name or "arXiv",
                raw_metadata=adhoc.raw_metadata or {},
            )
            items.append((ident, t, det))

    return literature_comparator.compare_extractions(items, save_report=req.save_report)


@router.get(
    "/compare/latest",
    response_model=LiteratureComparisonResponse,
    summary="Get latest generated literature comparison synthesis",
)
def get_latest_comparison(
    db: Session = Depends(get_db),
) -> LiteratureComparisonResponse:
    """
    Retrieve the most recently generated literature comparison report.
    If none exists on disk, performs an initial synthesis on available DB records.
    """
    json_path = os.path.join(REPORTS_DIR, "literature_comparison.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return LiteratureComparisonResponse(**data)
        except Exception:
            pass

    return literature_comparator.compare_database_records(db=db, save_report=True)
