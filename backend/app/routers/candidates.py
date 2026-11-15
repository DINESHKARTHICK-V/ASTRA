# ============================================================
#  ASTRA Cloud — Candidates & Processing Runs Router
#  File   : backend/app/routers/candidates.py
#  Purpose: Read-only endpoints for ACIS candidate prioritization
#           and pipeline execution history.
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List

from backend.app.database import get_db
from backend.app.models import CandidateScore, Observation, ProcessingRun
from backend.app.schemas import (
    CandidateScoreResponse,
    CandidateListResponse,
    ProcessingRunResponse,
    ProcessingRunListResponse,
)

router = APIRouter(prefix="/api", tags=["Candidates & Pipeline Runs"])


@router.get(
    "/candidates",
    response_model=CandidateListResponse,
    summary="List prioritized pulsar candidates (ACIS)",
    description=(
        "Retrieve candidates prioritized by the ASTRA Candidate Intelligence Score (ACIS). "
        "Supports filtering by priority group (HIGH, MEDIUM, LOW) and pagination."
    )
)
def list_candidates(
    priority_group: Optional[str] = Query(default=None, description="Filter by priority group ('HIGH', 'MEDIUM', 'LOW')"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of candidates to return"),
    offset: int = Query(default=0, ge=0, description="Offset index for pagination"),
    db: Session = Depends(get_db),
):
    query = (
        db.query(CandidateScore, Observation)
        .join(Observation, CandidateScore.observation_id == Observation.id)
    )

    if priority_group:
        normalized_group = priority_group.strip().upper()
        query = query.filter(CandidateScore.priority_group == normalized_group)

    total = query.count()

    results = (
        query
        .order_by(CandidateScore.rank_position.asc().nullslast(), CandidateScore.acis_score.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for score, obs in results:
        items.append(
            CandidateScoreResponse(
                id=score.id,
                observation_id=score.observation_id,
                file_name=obs.file_name,
                target_name=obs.target_name,
                telescope=obs.telescope,
                score_version=score.score_version,
                ml_probability=score.ml_probability,
                signal_quality=score.signal_quality,
                rfi_indicator=score.rfi_indicator,
                periodicity_evidence=score.periodicity_evidence,
                dm_evidence=score.dm_evidence,
                profile_evidence=score.profile_evidence,
                acis_score=score.acis_score,
                evidence_available=score.evidence_available,
                score_status=score.score_status,
                priority_group=score.priority_group,
                rank_position=score.rank_position,
                notes=score.notes,
                created_at=score.created_at,
            )
        )

    return CandidateListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get(
    "/candidates/{observation_id}",
    response_model=CandidateScoreResponse,
    summary="Get ACIS candidate evaluation for observation",
    description="Retrieve the ACIS score and multi-evidence details for a specific observation."
)
def get_candidate(
    observation_id: int,
    db: Session = Depends(get_db),
):
    result = (
        db.query(CandidateScore, Observation)
        .join(Observation, CandidateScore.observation_id == Observation.id)
        .filter(CandidateScore.observation_id == observation_id)
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate score for observation ID {observation_id} was not found."
        )

    score, obs = result
    return CandidateScoreResponse(
        id=score.id,
        observation_id=score.observation_id,
        file_name=obs.file_name,
        target_name=obs.target_name,
        telescope=obs.telescope,
        score_version=score.score_version,
        ml_probability=score.ml_probability,
        signal_quality=score.signal_quality,
        rfi_indicator=score.rfi_indicator,
        periodicity_evidence=score.periodicity_evidence,
        dm_evidence=score.dm_evidence,
        profile_evidence=score.profile_evidence,
        acis_score=score.acis_score,
        evidence_available=score.evidence_available,
        score_status=score.score_status,
        priority_group=score.priority_group,
        rank_position=score.rank_position,
        notes=score.notes,
        created_at=score.created_at,
    )


@router.get(
    "/processing-runs",
    response_model=ProcessingRunListResponse,
    summary="List pipeline processing runs",
    description="Retrieve execution audit history for ASTRA scientific pipeline operations."
)
def list_processing_runs(
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of runs to return"),
    offset: int = Query(default=0, ge=0, description="Offset index for pagination"),
    db: Session = Depends(get_db),
):
    total = db.query(ProcessingRun).count()
    items = (
        db.query(ProcessingRun)
        .order_by(ProcessingRun.started_at.desc(), ProcessingRun.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ProcessingRunListResponse(total=total, limit=limit, offset=offset, items=items)
