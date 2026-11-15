# ============================================================
#  ASTRA Cloud — Multi-File FITS Upload Router
#  File   : backend/app/routers/upload.py
#  Purpose: Handles secure multi-file FITS upload, validation,
#           checksum duplicate check, metadata indexing,
#           and available workflow discovery.
# ============================================================

import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Observation
from backend.app.schemas import UploadResponse, FileUploadItem
from backend.app.services.fits_service import (
    REPO_ROOT,
    UPLOAD_DIR,
    MAX_UPLOAD_SIZE_BYTES,
    sanitize_filename,
    compute_file_sha256,
    detect_fits_type_and_metadata,
    get_available_workflows_for_type,
)

router = APIRouter(prefix="/api/upload", tags=["Data Upload"])

SUPPORTED_EXTENSIONS = {".fits", ".fit", ".fts", ".gz", ".sf"}


@router.post(
    "",
    response_model=UploadResponse,
    summary="Upload one or multiple FITS files",
    description=(
        "Safely ingests and validates FITS/PSRFITS observation files. "
        "Calculates SHA-256 checksums to detect duplicate uploads, "
        "extracts header metadata, detects scientific data type, "
        "and stages the file for user-selected analysis."
    ),
)
async def upload_fits_files(
    files: List[UploadFile] = File(..., description="One or multiple FITS files to upload"),
    display_names: Optional[str] = Form(None, description="Optional JSON array of custom observation display names"),
    db: Session = Depends(get_db),
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided in upload request."
        )

    # Parse display names if provided
    custom_names: List[str] = []
    if display_names:
        try:
            parsed = json.loads(display_names)
            if isinstance(parsed, list):
                custom_names = [str(n).strip() for n in parsed]
        except Exception:
            # Fallback if comma-separated
            custom_names = [s.strip() for s in display_names.split(",") if s.strip()]

    uploaded_items: List[FileUploadItem] = []

    for idx, upload in enumerate(files):
        orig_filename = upload.filename or "observation.fits"
        sanitized = sanitize_filename(orig_filename)
        ext = Path(sanitized).suffix.lower()

        # Check file extension
        if not any(sanitized.lower().endswith(sup_ext) for sup_ext in SUPPORTED_EXTENSIONS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format for '{orig_filename}'. Supported: .fits, .fit, .fts, .fits.gz, .sf"
            )

        # Generate a safe server-side storage filename
        timestamp_prefix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        server_storage_name = f"{timestamp_prefix}_{sanitized}"
        target_path = UPLOAD_DIR / server_storage_name

        # Stream file to disk in chunks to avoid high RAM usage
        total_bytes = 0
        try:
            with open(target_path, "wb") as buffer:
                while chunk := await upload.read(1024 * 1024):  # 1MB chunks
                    total_bytes += len(chunk)
                    if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                        target_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File '{orig_filename}' exceeds the maximum upload limit of {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
                        )
                    buffer.write(chunk)
        except HTTPException:
            raise
        except Exception as exc:
            target_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stream and store upload '{orig_filename}': {str(exc)}"
            )

        if total_bytes == 0:
            target_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{orig_filename}' is empty (0 bytes)."
            )

        # Validate FITS header signature
        header_bytes = b""
        try:
            with open(target_path, "rb") as f:
                header_bytes = f.read(80)
        except Exception as exc:
            target_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error reading header for '{orig_filename}': {str(exc)}"
            )

        is_standard_fits = header_bytes.startswith(b"SIMPLE  =") or header_bytes.startswith(b"XTENSION=")
        is_gzip = header_bytes.startswith(b"\x1f\x8b")
        if not (is_standard_fits or is_gzip):
            target_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{orig_filename}' does not contain a valid FITS header signature."
            )

        # Compute SHA-256 Checksum
        file_hash = compute_file_sha256(target_path)

        # Check for existing duplicate observation
        existing_obs = (
            db.query(Observation)
            .filter((Observation.file_name == sanitized) | (Observation.file_name == orig_filename))
            .first()
        )

        # Assign user-friendly observation display name
        display_name = (
            custom_names[idx]
            if idx < len(custom_names) and custom_names[idx]
            else Path(orig_filename).stem
        )

        if existing_obs:
            # File already exists in catalog
            target_path.unlink(missing_ok=True)  # Avoid storing duplicate copy
            workflows = get_available_workflows_for_type(existing_obs.file_type)
            uploaded_items.append(
                FileUploadItem(
                    observation_id=existing_obs.id,
                    file_name=orig_filename,
                    display_name=existing_obs.target_name or display_name,
                    file_size_mb=existing_obs.file_size_mb or round(total_bytes / (1024 * 1024), 3),
                    detected_type=existing_obs.file_type,
                    telescope=existing_obs.telescope,
                    instrument=existing_obs.instrument,
                    checksum=file_hash,
                    is_duplicate=True,
                    available_workflows=workflows,
                )
            )
            continue

        # Extract metadata & detect type
        meta = detect_fits_type_and_metadata(target_path)
        detected_type = meta["detected_type"]

        # If user did not provide display name, use target from header if available, or filename stem
        if not (idx < len(custom_names) and custom_names[idx]):
            if meta.get("target_name"):
                display_name = meta["target_name"]

        rel_path = f"data/uploads/{server_storage_name}"
        obs_date = None
        if meta.get("observation_date"):
            try:
                obs_date = datetime.strptime(meta["observation_date"], "%Y-%m-%d").date()
            except Exception:
                pass

        obs_time = None
        if meta.get("observation_time"):
            try:
                obs_time = datetime.strptime(meta["observation_time"], "%H:%M:%S").time()
            except Exception:
                pass

        # Create new observation record in PostgreSQL
        new_obs = Observation(
            file_name=sanitized,
            file_path=rel_path,
            file_type=detected_type,
            telescope=meta.get("telescope"),
            instrument=meta.get("instrument"),
            target_name=display_name,
            observation_date=obs_date,
            observation_time=obs_time,
            ra=meta.get("ra"),
            dec=meta.get("dec"),
            ra_deg=meta.get("ra_deg"),
            dec_deg=meta.get("dec_deg"),
            frequency_mhz=meta.get("frequency_mhz"),
            bandwidth_mhz=meta.get("bandwidth_mhz"),
            nchan=meta.get("nchan"),
            nsubint=meta.get("nsubint"),
            nbin=meta.get("nbin"),
            observation_mode=meta.get("observation_mode"),
            data_mode=meta.get("data_mode"),
            polarization_info=None,
            file_size_mb=meta["file_size_mb"],
            validation_status="UPLOADED",
        )
        db.add(new_obs)
        db.commit()
        db.refresh(new_obs)

        workflows = get_available_workflows_for_type(detected_type)
        uploaded_items.append(
            FileUploadItem(
                observation_id=new_obs.id,
                file_name=orig_filename,
                display_name=display_name,
                file_size_mb=meta["file_size_mb"],
                detected_type=detected_type,
                telescope=meta.get("telescope"),
                instrument=meta.get("instrument"),
                checksum=file_hash,
                is_duplicate=False,
                available_workflows=workflows,
            )
        )

    return UploadResponse(
        total_uploaded=len(uploaded_items),
        files=uploaded_items,
        message=f"Successfully ingested {len(uploaded_items)} FITS file(s). Select an analysis workflow to begin processing.",
    )


@router.get(
    "/{observation_id}/workflows",
    summary="Get available workflows for observation",
    description="Returns valid scientific workflows supported by the detected file type."
)
def get_observation_workflows(
    observation_id: int,
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation #{observation_id} was not found."
        )

    workflows = get_available_workflows_for_type(obs.file_type)
    return {
        "observation_id": obs.id,
        "file_name": obs.file_name,
        "target_name": obs.target_name,
        "file_type": obs.file_type,
        "workflows": workflows,
    }
