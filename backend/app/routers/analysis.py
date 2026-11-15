# ============================================================
#  ASTRA Cloud — User-Selected Analysis Router
#  File   : backend/app/routers/analysis.py
#  Purpose: Dispatches and manages user-selected astronomical
#           analysis workflows for radio and optical FITS.
# ============================================================

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Observation, ProcessingRun
from backend.app.schemas import (
    StartAnalysisRequest,
    AnalysisResultResponse,
    ProcessingRunResponse,
)
from backend.app.services.fits_service import (
    execute_observation_analysis,
    get_available_workflows_for_type,
)

router = APIRouter(prefix="/api/analysis", tags=["Scientific Analysis"])


@router.post(
    "/start",
    response_model=AnalysisResultResponse,
    summary="Start user-selected analysis on an observation",
    description=(
        "Executes a user-chosen analysis workflow (Metadata, Quality, Signal, "
        "Inference, or Optical Preview/Statistics) on an observation. "
        "Strictly prevents running radio pulsar inference on optical images."
    ),
)
def start_analysis(
    req: StartAnalysisRequest,
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == req.observation_id).first()
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation with ID #{req.observation_id} was not found."
        )

    # Scientific boundary guard: optical images cannot run radio pulsar workflows
    is_optical = "OPTICAL" in obs.file_type or "IMAGE" in obs.file_type
    radio_only_workflows = {"radio_quality", "radio_signal", "pulsar_inference"}

    if is_optical and req.workflow_id in radio_only_workflows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid scientific analysis: Cannot run '{req.workflow_id}' on an optical FITS image. "
                "Optical images do not contain radio Stokes I profiles or dispersion measure characteristics."
            )
        )

    # Check that the workflow is supported for this file
    available_workflows = [w["id"] for w in get_available_workflows_for_type(obs.file_type)]
    if req.workflow_id not in available_workflows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow '{req.workflow_id}' is not supported for file type '{obs.file_type}'."
        )

    # Execute analysis
    result = execute_observation_analysis(db, obs, req.workflow_id)

    return AnalysisResultResponse(
        run_id=result["run_id"],
        observation_id=result["observation_id"],
        workflow=result["workflow"],
        status=result["status"],
        elapsed_seconds=result["elapsed_seconds"],
        summary=result["summary"],
        details=result["details"],
    )


@router.get(
    "/status/{run_id}",
    response_model=ProcessingRunResponse,
    summary="Get status of an analysis run",
    description="Polls execution progress and telemetry for a pipeline execution run."
)
def get_run_status(
    run_id: int,
    db: Session = Depends(get_db),
):
    run = db.query(ProcessingRun).filter(ProcessingRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processing run #{run_id} was not found."
        )
    return run
