# ============================================================
#  ASTRA Cloud — Observations Router
#  File   : backend/app/routers/observations.py
#  Purpose: Read-only endpoints for astronomical observations.
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import json
from datetime import datetime as dt_cls
from pathlib import Path

from backend.app.database import get_db
from backend.app.models import Observation
from backend.app.schemas import (
    ObservationResponse,
    ObservationListResponse,
    ObservationDateFileItem,
    ObservationDateGroupMatch,
    ObservationDateSearchResponse,
)

router = APIRouter(prefix="/api/observations", tags=["Observations"])


def _normalize_date_string(date_str: str) -> Optional[str]:
    """Parse dates in formats like YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY into standard YYYY-MM-DD."""
    cleaned = date_str.strip()
    if not cleaned:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return dt_cls.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


@router.get(
    "",
    response_model=ObservationListResponse,
    summary="List astronomical observations",
    description="Retrieve paginated list of cataloged observations with physical and telescope metadata."
)
def list_observations(
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of observations to return"),
    offset: int = Query(default=0, ge=0, description="Offset index for pagination"),
    db: Session = Depends(get_db),
):
    total = db.query(Observation).count()
    items = (
        db.query(Observation)
        .order_by(Observation.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ObservationListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get(
    "/date-search",
    response_model=ObservationDateSearchResponse,
    summary="Search uploaded observations by recorded observation date",
    description=(
        "Searches existing uploaded-file and observation records in ASTRA by their true "
        "recorded observation date. For FITS/PSRFITS files, uses verified DATE-OBS header metadata. "
        "For CSV files, uses verified observation metadata. Never substitutes upload timestamps."
    ),
)
def search_observations_by_date(
    date: Optional[str] = Query(
        default=None,
        description="Target observation date to search, formatted as YYYY-MM-DD or DD/MM/YYYY"
    ),
    db: Session = Depends(get_db),
):
    from backend.app.services.fits_service import REPO_ROOT

    # 1. Fetch all cataloged observations from database
    db_observations = db.query(Observation).order_by(Observation.id.asc()).all()

    # Index observations by target_name and file_name for CSV association
    obs_by_name: Dict[str, Observation] = {}
    for o in db_observations:
        if o.target_name:
            obs_by_name[o.target_name.strip().lower()] = o
        if o.file_name:
            obs_by_name[o.file_name.strip().lower()] = o

    all_file_items: List[ObservationDateFileItem] = []
    known_observation_dates = set()

    # 2. Process FITS/PSRFITS observations
    for obs in db_observations:
        obs_date_str = obs.observation_date.strftime("%Y-%m-%d") if obs.observation_date else None
        obs_time_str = obs.observation_time.strftime("%H:%M:%S") if obs.observation_time else None
        is_verified = obs_date_str is not None

        if is_verified:
            known_observation_dates.add(obs_date_str)

        all_file_items.append(
            ObservationDateFileItem(
                id=obs.id,
                observation_id=obs.id,
                file_name=obs.file_name,
                file_type=obs.file_type,
                file_size_mb=obs.file_size_mb,
                telescope=obs.telescope,
                instrument=obs.instrument,
                target_name=obs.target_name or obs.file_name,
                recorded_observation_date=obs_date_str,
                recorded_observation_time=obs_time_str,
                date_source="Verified from file metadata (DATE-OBS)" if is_verified else "Observation date unavailable",
                is_date_verified=is_verified,
                server_path=obs.file_path,
                csv_server_name=None,
            )
        )

    # 3. Process uploaded CSV files from data/uploads/csv
    csv_dir = (REPO_ROOT / "data" / "uploads" / "csv").resolve()
    if csv_dir.exists() and csv_dir.is_dir():
        for csv_file in csv_dir.glob("*.csv"):
            if not csv_file.is_file():
                continue
            server_name = csv_file.name
            meta_path = csv_dir / f"{server_name}.meta.json"
            meta: dict = {}
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as mf:
                        meta = json.load(mf)
                except Exception:
                    pass

            assoc_name = meta.get("observation_name") or ""
            clean_assoc = assoc_name.strip().lower()

            # Check if associated with an existing cataloged observation
            matched_obs = obs_by_name.get(clean_assoc) if clean_assoc else None

            csv_obs_date: Optional[str] = None
            csv_obs_time: Optional[str] = None
            date_source = "Observation date unavailable"
            is_verified = False
            telescope = None
            instrument = None

            if matched_obs and matched_obs.observation_date:
                csv_obs_date = matched_obs.observation_date.strftime("%Y-%m-%d")
                csv_obs_time = matched_obs.observation_time.strftime("%H:%M:%S") if matched_obs.observation_time else None
                date_source = "Derived from associated observation metadata"
                is_verified = True
                telescope = matched_obs.telescope
                instrument = matched_obs.instrument
                known_observation_dates.add(csv_obs_date)
            elif meta.get("observation_date"):
                # Explicit observation date in CSV metadata (NOT upload_date)
                csv_obs_date = _normalize_date_string(str(meta.get("observation_date")))
                if csv_obs_date:
                    date_source = "Stored observation metadata"
                    is_verified = True
                    known_observation_dates.add(csv_obs_date)

            file_size_mb = round(csv_file.stat().st_size / (1024 * 1024), 3)

            all_file_items.append(
                ObservationDateFileItem(
                    id=None,
                    observation_id=matched_obs.id if matched_obs else None,
                    file_name=meta.get("original_name") or server_name,
                    file_type="CSV_DATASET",
                    file_size_mb=file_size_mb,
                    telescope=telescope,
                    instrument=instrument,
                    target_name=assoc_name or meta.get("original_name", server_name).replace(".csv", ""),
                    recorded_observation_date=csv_obs_date,
                    recorded_observation_time=csv_obs_time,
                    date_source=date_source,
                    is_date_verified=is_verified,
                    server_path=f"data/uploads/csv/{server_name}",
                    csv_server_name=server_name,
                )
            )

    sorted_dates = sorted(list(known_observation_dates), reverse=True)
    undated_count = sum(1 for f in all_file_items if not f.is_date_verified or not f.recorded_observation_date)

    # 4. If no search date provided, return catalog date summary
    if not date or not date.strip():
        return ObservationDateSearchResponse(
            search_date=None,
            total_matching_observations=0,
            total_matching_files=0,
            results=[],
            undated_files_count=undated_count,
            available_observation_dates=sorted_dates,
            message="Please select a date to search uploaded observations.",
        )

    # 5. Normalize search date and filter matching files
    norm_date = _normalize_date_string(date)
    if not norm_date:
        return ObservationDateSearchResponse(
            search_date=date.strip(),
            total_matching_observations=0,
            total_matching_files=0,
            results=[],
            undated_files_count=undated_count,
            available_observation_dates=sorted_dates,
            message=f"Invalid date format '{date}'. Please use YYYY-MM-DD or DD/MM/YYYY.",
        )

    matching_files = [f for f in all_file_items if f.recorded_observation_date == norm_date]

    if not matching_files:
        return ObservationDateSearchResponse(
            search_date=norm_date,
            total_matching_observations=0,
            total_matching_files=0,
            results=[],
            undated_files_count=undated_count,
            available_observation_dates=sorted_dates,
            message="No uploaded observations were found for this date.",
        )

    # 6. Group matching files by observation name
    groups_map: Dict[str, List[ObservationDateFileItem]] = {}
    for mf in matching_files:
        group_key = mf.target_name or mf.file_name
        if group_key not in groups_map:
            groups_map[group_key] = []
        groups_map[group_key].append(mf)

    group_matches: List[ObservationDateGroupMatch] = []
    for g_name, g_files in groups_map.items():
        telescopes = sorted(list(set(f.telescope for f in g_files if f.telescope)))
        instruments = sorted(list(set(f.instrument for f in g_files if f.instrument)))
        group_matches.append(
            ObservationDateGroupMatch(
                observation_name=g_name,
                recorded_observation_date=norm_date,
                file_count=len(g_files),
                telescopes=telescopes,
                instruments=instruments,
                files=g_files,
            )
        )

    return ObservationDateSearchResponse(
        search_date=norm_date,
        total_matching_observations=len(group_matches),
        total_matching_files=len(matching_files),
        results=group_matches,
        undated_files_count=undated_count,
        available_observation_dates=sorted_dates,
        message=f"Found {len(group_matches)} observation(s) with {len(matching_files)} matching file(s) on {norm_date}.",
    )


@router.get(
    "/{observation_id}",
    response_model=ObservationResponse,
    summary="Get observation details",
    description="Retrieve metadata for a specific observation by its unique identifier."
)
def get_observation(
    observation_id: int,
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation with ID {observation_id} was not found."
        )
    return obs


# ── PDF report ─────────────────────────────────────────────────────────────────
from pathlib import Path
from fastapi.responses import StreamingResponse
from backend.app.models import Feature, Prediction, CandidateScore, ProcessingRun
from backend.app.services.report_service import generate_observation_pdf
from backend.app.services.fits_service import REPO_ROOT


@router.get(
    "/{observation_id}/report",
    summary="Generate PDF report for an observation",
    description=(
        "Generates and streams a PDF audit report for a cataloged observation, "
        "including FITS metadata, extracted features, ACIS candidate score, "
        "ML inference status, processing history, and optional CSV dataset records."
    ),
    response_class=StreamingResponse,
)
def get_observation_report(
    observation_id: int,
    csv_server_name: Optional[str] = Query(
        default=None,
        description="Optional server_name of CSV file in data/uploads/csv to include in report"
    ),
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation with ID {observation_id} was not found."
        )

    # Optional CSV file validation & resolution
    csv_path: Optional[Path] = None
    csv_original_name: Optional[str] = None
    if csv_server_name and csv_server_name.strip():
        clean_name = Path(csv_server_name.strip()).name
        if not clean_name.lower().endswith(".csv"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Requested file '{clean_name}' is not a valid CSV file."
            )
        csv_dir = (REPO_ROOT / "data" / "uploads" / "csv").resolve()
        candidate_path = (csv_dir / clean_name).resolve()

        # Prevent path traversal
        try:
            candidate_path.relative_to(csv_dir)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid CSV file path specified."
            )

        if not candidate_path.exists() or not candidate_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"CSV file '{clean_name}' was not found on the server."
            )

        csv_path = candidate_path
        parts = clean_name.split("_", 3)
        csv_original_name = parts[-1] if len(parts) >= 4 else clean_name

    feature = db.query(Feature).filter(Feature.observation_id == observation_id).first()
    predictions = db.query(Prediction).filter(Prediction.observation_id == observation_id).all()
    candidate = db.query(CandidateScore).filter(CandidateScore.observation_id == observation_id).first()
    runs = db.query(ProcessingRun).filter(ProcessingRun.observation_id == observation_id).all()

    pdf_buffer = generate_observation_pdf(
        obs,
        feature,
        predictions,
        candidate,
        runs,
        csv_path=csv_path,
        csv_original_name=csv_original_name,
    )

    filename = f"astra_obs_{observation_id}_report.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Optical image preview & display name management ───────────────────────────
from pathlib import Path
from pydantic import BaseModel
from backend.app.schemas import OpticalPreviewResponse
from backend.app.services.fits_service import REPO_ROOT, generate_optical_preview_image


@router.get(
    "/{observation_id}/preview",
    response_model=OpticalPreviewResponse,
    summary="Get optical image preview",
    description="Renders a high-contrast 2D preview frame with pixel statistics for an astronomical observation."
)
def get_observation_preview(
    observation_id: int,
    group_idx: int = Query(default=0, ge=0, description="Plane or group index for multi-dimensional FITS cubes"),
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation with ID {observation_id} was not found."
        )

    filepath = Path(obs.file_path)
    if not filepath.is_absolute():
        filepath = REPO_ROOT / filepath

    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FITS data file '{obs.file_name}' not found on disk."
        )

    try:
        preview_data = generate_optical_preview_image(filepath, group_idx=group_idx)
        return OpticalPreviewResponse(
            observation_id=obs.id,
            image_data_url=preview_data["image_data_url"],
            slice_name=preview_data["slice_name"],
            width=preview_data["width"],
            height=preview_data["height"],
            min_val=preview_data["min_val"],
            max_val=preview_data["max_val"],
            mean_val=preview_data["mean_val"],
            median_val=preview_data["median_val"],
            std_val=preview_data["std_val"],
            nan_count=preview_data["nan_count"],
            inf_count=preview_data["inf_count"],
            total_pixels=preview_data["total_pixels"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to generate 2D image preview: {str(exc)}"
        )


class ObservationUpdateRequest(BaseModel):
    display_name: str


class GroupRenameRequest(BaseModel):
    old_name: str
    new_name: str


@router.patch(
    "/group/rename",
    summary="Rename an observation group",
    description="Updates the target_name display identifier for all observation files in a group."
)
def rename_observation_group(
    req: GroupRenameRequest,
    db: Session = Depends(get_db),
):
    clean_new = req.new_name.strip()
    if not clean_new:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New observation group name cannot be empty."
        )
    clean_old = req.old_name.strip()
    matches = db.query(Observation).filter(Observation.target_name == clean_old).all()
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No observations found under group name '{clean_old}'."
        )
    for obs in matches:
        obs.target_name = clean_new
    db.commit()
    return {
        "updated_count": len(matches),
        "old_name": clean_old,
        "new_name": clean_new,
        "message": f"Successfully renamed {len(matches)} file(s) to '{clean_new}'."
    }


@router.patch(
    "/{observation_id}",
    response_model=ObservationResponse,
    summary="Update observation display name",
    description="Updates the user-friendly observation display name (target_name)."
)
def update_observation(
    observation_id: int,
    req: ObservationUpdateRequest,
    db: Session = Depends(get_db),
):
    clean_name = req.display_name.strip()
    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Display name cannot be empty."
        )

    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation with ID {observation_id} was not found."
        )

    obs.target_name = clean_name
    db.commit()
    db.refresh(obs)

    return obs


@router.delete(
    "/{observation_id}",
    summary="Delete an observation",
    description="Safely deletes an observation and cascades cleanup of associated records."
)
def delete_observation(
    observation_id: int,
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation with ID #{observation_id} was not found."
        )

    obs_name = obs.target_name or obs.file_name

    # Clean up associated processing runs
    db.query(ProcessingRun).filter(ProcessingRun.observation_id == observation_id).delete()

    # Safely delete uploaded file from disk if inside data/uploads/ (never delete reference files)
    try:
        raw_path = Path(obs.file_path)
        full_path = raw_path if raw_path.is_absolute() else (REPO_ROOT / raw_path)
        uploads_dir = (REPO_ROOT / "data" / "uploads").resolve()
        if full_path.exists() and full_path.is_file():
            try:
                full_path.resolve().relative_to(uploads_dir)
                full_path.unlink(missing_ok=True)
            except ValueError:
                pass  # Do not touch files outside uploads/
    except Exception:
        pass

    db.delete(obs)
    db.commit()

    return {
        "message": f"Observation #{observation_id} ('{obs_name}') successfully deleted.",
        "observation_id": observation_id,
    }


