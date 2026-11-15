# ============================================================
#  ASTRA Cloud — CSV Upload Router
#  File   : backend/app/routers/csv_upload.py
#  Purpose: Accepts CSV tabular data files, validates them,
#           computes column statistics, and returns a preview.
# ============================================================

import json
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Any, Optional, Dict

import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from backend.app.schemas import (
    CsvUploadResponse,
    CsvColumnStat,
    CsvAnalysisRequest,
    CsvAnalysisResult,
    CsvFileItem,
    CsvColumnDetail,
    CsvDataResponse,
    CsvUpdateRequest,
)
from backend.app.services.fits_service import REPO_ROOT, sanitize_filename
from backend.app.services.csv_service import get_csv_workflows, execute_csv_analysis
from backend.app.services.report_service import generate_csv_report_pdf, infer_column_type

router = APIRouter(prefix="/api/upload/csv", tags=["CSV Upload"])

# Storage directory for uploaded CSVs
CSV_UPLOAD_DIR = REPO_ROOT / "data" / "uploads" / "csv"
CSV_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_CSV_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB


def _safe_val(v: Any) -> Any:
    """Convert numpy / float NaN/Inf to None for JSON serialisation."""
    if v is None:
        return None
    try:
        if math.isnan(float(v)) or math.isinf(float(v)):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _get_meta_path(server_name: str) -> Path:
    clean = Path(server_name).name
    return CSV_UPLOAD_DIR / f"{clean}.meta.json"


def _read_csv_meta(server_name: str) -> dict:
    p = _get_meta_path(server_name)
    if p.exists() and p.is_file():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _write_csv_meta(server_name: str, meta: dict):
    p = _get_meta_path(server_name)
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
    except Exception:
        pass


@router.post(
    "",
    response_model=CsvUploadResponse,
    summary="Upload a CSV data file",
    description=(
        "Accepts a .csv file, validates format, computes per-column statistics "
        "(dtype, min, max, mean, null counts), and returns a 10-row preview. "
        "The file is saved to data/uploads/csv/ on the server."
    ),
)
async def upload_csv_file(
    file: UploadFile = File(..., description="CSV file to upload"),
    observation_name: Optional[str] = Form(None, description="Optional associated observation name"),
):
    orig_filename = file.filename or "data.csv"
    sanitized = sanitize_filename(orig_filename)

    # Validate extension
    if not sanitized.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format for '{orig_filename}'. Only .csv files are accepted here.",
        )

    # Stream to disk
    timestamp_prefix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    server_name = f"{timestamp_prefix}_{sanitized}"
    target_path = CSV_UPLOAD_DIR / server_name

    total_bytes = 0
    try:
        with open(target_path, "wb") as buf:
            while chunk := await file.read(1024 * 1024):  # 1 MB chunks
                total_bytes += len(chunk)
                if total_bytes > MAX_CSV_SIZE_BYTES:
                    target_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum CSV upload limit of {MAX_CSV_SIZE_BYTES // (1024 * 1024)} MB.",
                    )
                buf.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store uploaded CSV: {str(exc)}",
        )

    if total_bytes == 0:
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file is empty (0 bytes).",
        )

    # Parse with pandas
    try:
        df = pd.read_csv(target_path)
    except Exception as exc:
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV: {str(exc)}",
        )

    if df.empty or len(df.columns) == 0:
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file contains no data rows or columns.",
        )

    # Build column statistics
    col_stats: List[CsvColumnStat] = []
    for col in df.columns:
        series = df[col]
        non_null = int(series.notna().sum())
        null_count = int(series.isna().sum())
        col_min = col_max = col_mean = None

        if pd.api.types.is_numeric_dtype(series):
            valid = series.dropna()
            if len(valid) > 0:
                col_min = _safe_val(float(valid.min()))
                col_max = _safe_val(float(valid.max()))
                col_mean = _safe_val(float(valid.mean()))

        col_stats.append(
            CsvColumnStat(
                name=col,
                dtype=str(series.dtype),
                non_null=non_null,
                null_count=null_count,
                min=col_min,
                max=col_max,
                mean=col_mean,
            )
        )

    # Preview rows (first 10), replace NaN with None
    preview_df = df.head(10).where(pd.notnull(df.head(10)), other=None)
    preview_rows = preview_df.to_dict(orient="records")

    file_size_kb = round(total_bytes / 1024, 2)
    workflows = get_csv_workflows(df)
    rel_server_path = f"data/uploads/csv/{server_name}"

    obs_name = (
        observation_name.strip()
        if observation_name and observation_name.strip()
        else Path(orig_filename).stem
    )
    _write_csv_meta(
        server_name,
        {
            "observation_name": obs_name,
            "original_name": orig_filename,
            "upload_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        },
    )

    return CsvUploadResponse(
        file_name=orig_filename,
        file_size_kb=file_size_kb,
        total_rows=len(df),
        total_columns=len(df.columns),
        columns=col_stats,
        preview_rows=preview_rows,
        available_workflows=workflows,
        server_file_path=rel_server_path,
        message=f"CSV ingested successfully: {len(df)} rows × {len(df.columns)} columns.",
    )


@router.post(
    "/analyze",
    response_model=CsvAnalysisResult,
    summary="Run scientific or ML analysis on uploaded CSV data",
    description=(
        "Executes a statistical summary, correlation matrix, or pulsar ML classification workflow "
        "on a previously ingested CSV file."
    ),
)
async def analyze_csv_file(
    req: CsvAnalysisRequest,
):
    clean_path = Path(req.server_file_path).as_posix().lstrip("/\\")
    target_path = (REPO_ROOT / clean_path).resolve()

    # Security boundary: file must reside within CSV_UPLOAD_DIR
    try:
        target_path.relative_to(CSV_UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access denied: file must reside within data/uploads/csv/.",
        )

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Uploaded CSV file not found on server at '{req.server_file_path}'.",
        )

    valid_workflows = {"csv_statistics", "csv_correlation", "csv_pulsar_inference"}
    if req.workflow_id not in valid_workflows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported CSV workflow '{req.workflow_id}'. Must be one of: {sorted(valid_workflows)}",
        )

    try:
        result = execute_csv_analysis(target_path, req.workflow_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV analysis failed: {str(exc)}",
        )

    return CsvAnalysisResult(
        workflow_id=req.workflow_id,
        status=result.get("status", "COMPLETED"),
        summary=result.get("summary", ""),
        details=result.get("details", {}),
        elapsed_seconds=result.get("elapsed_seconds", 0.0),
    )


@router.get(
    "",
    response_model=List[CsvFileItem],
    summary="List uploaded CSV data files",
    description="Retrieves catalog of all ingested CSV files from data/uploads/csv/."
)
def list_uploaded_csv_files():
    items: List[CsvFileItem] = []
    if not CSV_UPLOAD_DIR.exists():
        return items

    for p in sorted(CSV_UPLOAD_DIR.glob("*.csv"), key=lambda f: f.stat().st_mtime, reverse=True):
        if not p.is_file():
            continue
        server_name = p.name
        # Format: YYYYMMDD_HHMMSS_microseconds_original_filename.csv
        parts = server_name.split("_", 3)
        orig_name = parts[-1] if len(parts) >= 4 else server_name

        meta = _read_csv_meta(server_name)
        obs_name = meta.get("observation_name") or orig_name.replace(".csv", "")
        if meta.get("original_name"):
            orig_name = meta["original_name"]

        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        upload_date_str = mtime.strftime("%Y-%m-%d %H:%M:%S UTC")

        file_size_kb = round(p.stat().st_size / 1024, 2)

        row_count = None
        col_count = None
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                first_line = f.readline()
                if first_line:
                    col_count = len(first_line.split(","))
                row_count = sum(1 for _ in f)
        except Exception:
            pass

        items.append(
            CsvFileItem(
                server_name=server_name,
                server_file_path=f"data/uploads/csv/{server_name}",
                file_name=orig_name,
                file_size_kb=file_size_kb,
                upload_date=upload_date_str,
                total_rows=row_count,
                total_columns=col_count,
                status="INGESTED",
                observation_name=obs_name,
            )
        )
    return items


@router.get(
    "/{server_name}/download",
    summary="Download original CSV file",
    description="Streams the unchanged original CSV file from server storage."
)
def download_csv_file(server_name: str):
    clean_name = Path(server_name).name
    if not clean_name.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested file '{clean_name}' is not a valid CSV file.",
        )
    target_path = (CSV_UPLOAD_DIR / clean_name).resolve()
    try:
        target_path.relative_to(CSV_UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV file path specified."
        )

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSV file '{clean_name}' was not found on the server."
        )

    meta = _read_csv_meta(clean_name)
    parts = clean_name.split("_", 3)
    orig_name = meta.get("original_name") or (parts[-1] if len(parts) >= 4 else clean_name)

    return FileResponse(
        path=target_path,
        media_type="text/csv",
        filename=orig_name,
    )


@router.get(
    "/{server_name}/data",
    response_model=CsvDataResponse,
    summary="Get paginated data rows and column structure for a CSV file",
    description="Returns detailed column structure, inferred types, non-empty/null counts, descriptive statistics, and paginated rows."
)
def get_csv_file_data(
    server_name: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=500, description="Number of rows per page"),
):
    clean_name = Path(server_name).name
    if not clean_name.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested file '{clean_name}' is not a valid CSV file.",
        )
    target_path = (CSV_UPLOAD_DIR / clean_name).resolve()
    try:
        target_path.relative_to(CSV_UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV file path specified."
        )

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSV file '{clean_name}' was not found on the server."
        )

    if target_path.stat().st_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV file '{clean_name}' is empty (0 bytes).",
        )

    try:
        df = pd.read_csv(target_path, keep_default_na=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse CSV file: {str(exc)}",
        )

    total_rows = len(df)
    total_cols = len(df.columns)
    total_pages = max(1, math.ceil(total_rows / page_size)) if total_rows > 0 else 1

    # Column details
    col_details: List[CsvColumnDetail] = []
    for col in df.columns:
        s = df[col]
        non_null = int(s.notna().sum())
        null_count = int(s.isna().sum())
        inf_type = infer_column_type(s)
        c_min = c_max = c_mean = c_std = None

        if pd.api.types.is_numeric_dtype(s) and non_null > 0:
            valid_vals = s.dropna()
            if len(valid_vals) > 0:
                c_min = _safe_val(float(valid_vals.min()))
                c_max = _safe_val(float(valid_vals.max()))
                c_mean = _safe_val(float(valid_vals.mean()))
                c_std = _safe_val(float(valid_vals.std())) if len(valid_vals) > 1 else 0.0

        col_details.append(
            CsvColumnDetail(
                name=str(col),
                inferred_type=inf_type,
                non_empty_count=non_null,
                missing_count=null_count,
                min=c_min,
                max=c_max,
                mean=c_mean,
                std=c_std,
            )
        )

    # Paginated rows
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)
    sub_df = df.iloc[start_idx:end_idx] if start_idx < total_rows else pd.DataFrame(columns=df.columns)

    rows: List[Dict[str, Any]] = []
    for i, (_, row_series) in enumerate(sub_df.iterrows()):
        row_dict: Dict[str, Any] = {"_row_index": start_idx + i + 1}
        for col in df.columns:
            val = row_series[col]
            if pd.isna(val) or val is None:
                row_dict[str(col)] = None
            elif isinstance(val, (int, float, bool)):
                row_dict[str(col)] = _safe_val(val)
            else:
                row_dict[str(col)] = str(val)
        rows.append(row_dict)

    meta = _read_csv_meta(clean_name)
    parts = clean_name.split("_", 3)
    orig_name = meta.get("original_name") or (parts[-1] if len(parts) >= 4 else clean_name)
    obs_name = meta.get("observation_name") or orig_name.replace(".csv", "")
    mtime = datetime.fromtimestamp(target_path.stat().st_mtime, tz=timezone.utc)
    upload_date_str = mtime.strftime("%Y-%m-%d %H:%M:%S UTC")
    file_size_kb = round(target_path.stat().st_size / 1024, 2)

    file_info = CsvFileItem(
        server_name=clean_name,
        server_file_path=f"data/uploads/csv/{clean_name}",
        file_name=orig_name,
        file_size_kb=file_size_kb,
        upload_date=upload_date_str,
        total_rows=total_rows,
        total_columns=total_cols,
        status="INGESTED",
        observation_name=obs_name,
    )

    return CsvDataResponse(
        file_info=file_info,
        columns=col_details,
        rows=rows,
        page=page,
        page_size=page_size,
        total_rows=total_rows,
        total_pages=total_pages,
    )


@router.get(
    "/{server_name}/report",
    summary="Generate PDF report for a CSV file",
    description="Generates and streams a publication-grade scientific audit report for the selected CSV file.",
    response_class=StreamingResponse,
)
def get_csv_report(
    server_name: str,
    observation_name: Optional[str] = Query(None, description="Optional associated observation name override"),
):
    clean_name = Path(server_name).name
    if not clean_name.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested file '{clean_name}' is not a valid CSV file.",
        )
    target_path = (CSV_UPLOAD_DIR / clean_name).resolve()
    try:
        target_path.relative_to(CSV_UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV file path specified."
        )

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSV file '{clean_name}' was not found on the server."
        )

    if target_path.stat().st_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV file '{clean_name}' is empty (0 bytes).",
        )

    meta = _read_csv_meta(clean_name)
    parts = clean_name.split("_", 3)
    orig_name = meta.get("original_name") or (parts[-1] if len(parts) >= 4 else clean_name)
    obs_name = (
        observation_name.strip()
        if observation_name and observation_name.strip()
        else (meta.get("observation_name") or orig_name.replace(".csv", ""))
    )

    try:
        pdf_buffer = generate_csv_report_pdf(
            csv_path=target_path,
            csv_original_name=orig_name,
            observation_name=obs_name,
        )
    except ValueError as ve:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(exc)}"
        )

    filename = f"astra_csv_{Path(orig_name).stem}_report.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch(
    "/{server_name}",
    response_model=CsvFileItem,
    summary="Update CSV metadata such as associated observation name",
    description="Updates custom observation association for an uploaded CSV dataset."
)
def update_csv_metadata(server_name: str, req: CsvUpdateRequest):
    clean_name = Path(server_name).name
    target_path = (CSV_UPLOAD_DIR / clean_name).resolve()
    try:
        target_path.relative_to(CSV_UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid CSV file path specified.")

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"CSV file '{clean_name}' not found on server.")

    meta = _read_csv_meta(clean_name)
    if req.observation_name is not None:
        meta["observation_name"] = req.observation_name.strip()
    _write_csv_meta(clean_name, meta)

    parts = clean_name.split("_", 3)
    orig_name = meta.get("original_name") or (parts[-1] if len(parts) >= 4 else clean_name)
    mtime = datetime.fromtimestamp(target_path.stat().st_mtime, tz=timezone.utc)
    upload_date_str = mtime.strftime("%Y-%m-%d %H:%M:%S UTC")
    file_size_kb = round(target_path.stat().st_size / 1024, 2)

    row_count = None
    col_count = None
    try:
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            first_line = f.readline()
            if first_line:
                col_count = len(first_line.split(","))
            row_count = sum(1 for _ in f)
    except Exception:
        pass

    return CsvFileItem(
        server_name=clean_name,
        server_file_path=f"data/uploads/csv/{clean_name}",
        file_name=orig_name,
        file_size_kb=file_size_kb,
        upload_date=upload_date_str,
        total_rows=row_count,
        total_columns=col_count,
        status="INGESTED",
        observation_name=meta.get("observation_name") or orig_name.replace(".csv", ""),
    )


@router.delete(
    "/{server_name}",
    summary="Delete an uploaded CSV file",
    description="Safely removes an uploaded CSV file from server storage."
)
def delete_uploaded_csv(server_name: str):
    clean_name = Path(server_name).name
    target_path = (CSV_UPLOAD_DIR / clean_name).resolve()
    try:
        target_path.relative_to(CSV_UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid CSV file path specified.")

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSV file '{clean_name}' not found on server."
        )

    try:
        target_path.unlink()
        _get_meta_path(clean_name).unlink(missing_ok=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete CSV file: {str(exc)}"
        )

    return {"message": f"CSV file '{clean_name}' successfully deleted.", "server_name": clean_name}


