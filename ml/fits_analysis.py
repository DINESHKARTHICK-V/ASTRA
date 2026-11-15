# ============================================================
#  ASTRA Cloud -- FITS Analysis
#  File   : ml/fits_analysis.py
#  Purpose: Inspect every FITS file in data/fits, print per-HDU
#           details, compute primary-HDU statistics, extract
#           observation metadata, and save a CSV report.
#  Deps   : astropy, numpy
#  NOTE   : Read-only -- FITS files are never modified.
# ============================================================

import sys
import io
import os
import csv
import math
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.utils.exceptions import AstropyWarning

# ------------------------------------------------------------------
# UTF-8 output so Unicode / special chars print cleanly on Windows
# ------------------------------------------------------------------
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Suppress non-critical astropy warnings (e.g. HIERARCH, VerifyWarning)
warnings.filterwarnings("ignore", category=AstropyWarning)

# ------------------------------------------------------------------
# Paths (relative to the repository root, resolved from this file's
# location so the script works regardless of the working directory)
# ------------------------------------------------------------------
REPO_ROOT  = Path(__file__).resolve().parent.parent   # e:\ASTRA CLOUD
FITS_DIR   = REPO_ROOT / "data" / "fits"
REPORTS_DIR = REPO_ROOT / "reports"
CSV_OUT    = REPORTS_DIR / "fits_analysis.csv"

# ------------------------------------------------------------------
# CSV column order
# ------------------------------------------------------------------
CSV_FIELDS = [
    "fits_file",
    "object_name",
    "telescop",
    "instrume",
    "date_obs",
    "time_obs",
    "ra_targ",
    "dec_targ",
    "filter",
    "exptime",
    "primary_hdu_shape",
    "primary_hdu_dtype",
    "naxis",
    "naxis1",
    "naxis2",
    "naxis3",
    "data_min",
    "data_max",
    "data_mean",
    "data_median",
    "data_std",
    "nan_count",
    "inf_count",
    "total_hdu_count",
]

# ------------------------------------------------------------------
# Helper: search keyword across multiple headers
# ------------------------------------------------------------------
def _find_keyword(*keywords: str, headers: list, default: str = "N/A") -> str:
    """Return the first non-blank value for any of *keywords* across *headers*."""
    for hdr in headers:
        for kw in keywords:
            val = hdr.get(kw, None)
            if val not in (None, "", " "):
                return str(val).strip()
    return default


# ------------------------------------------------------------------
# Helper: safe scalar formatting
# ------------------------------------------------------------------
def _fmt(value, precision: int = 6) -> str:
    """Format a numeric scalar; return 'N/A' for NaN/None."""
    if value is None:
        return "N/A"
    try:
        if math.isnan(value) or math.isinf(value):
            return "N/A"
        return f"{value:.{precision}f}"
    except (TypeError, ValueError):
        return str(value)


# ------------------------------------------------------------------
# Main analysis function for a single FITS file
# ------------------------------------------------------------------
def analyse_fits(fits_path: Path) -> dict:
    """
    Open *fits_path* read-only, print per-HDU diagnostics and primary-HDU
    statistics, extract metadata, and return a dict of CSV row values.
    """
    sep  = "=" * 70
    sep2 = "-" * 70

    print(f"\n{sep}")
    print(f"  FILE : {fits_path.name}")
    print(sep)

    # ── 1. Open safely (read-only, memory-mapped) ─────────────────
    try:
        hdul = fits.open(fits_path, mode="readonly", memmap=True, ignore_missing_simple=True)
    except Exception as exc:
        print(f"  [ERROR] Cannot open file: {exc}")
        return {"fits_file": fits_path.name}

    row: dict = {"fits_file": fits_path.name}

    try:
        # ── 2. Identify all HDUs ──────────────────────────────────
        print(f"\n  {'HDU #':<6} {'NAME':<20} {'TYPE':<30} {'SHAPE':<25} {'DTYPE'}")
        print(f"  {sep2}")

        for idx, hdu in enumerate(hdul):
            hdu_name  = hdu.name  if hdu.name  else "(unnamed)"
            hdu_type  = type(hdu).__name__

            if hdu.data is not None and isinstance(hdu.data, np.ndarray):
                shape_str = str(hdu.data.shape)
                dtype_str = str(hdu.data.dtype)
            else:
                shape_str = "None"
                dtype_str = "None"

            # ── 3. Print per-HDU line ──────────────────────────
            print(f"  {idx:<6} {hdu_name:<20} {hdu_type:<30} {shape_str:<25} {dtype_str}")

        print()

        # ── 4. Primary HDU (index 0) deep inspection ──────────────
        primary = hdul[0]
        phdr    = primary.header

        print(f"  {sep2}")
        print("  PRIMARY HDU  (HDU 0) DETAILS")
        print(f"  {sep2}")

        naxis  = phdr.get("NAXIS",  "N/A")
        naxis1 = phdr.get("NAXIS1", "N/A")
        naxis2 = phdr.get("NAXIS2", "N/A")
        naxis3 = phdr.get("NAXIS3", "N/A")

        print(f"  NAXIS  = {naxis}")
        if naxis1 != "N/A":
            print(f"  NAXIS1 = {naxis1}")
        if naxis2 != "N/A":
            print(f"  NAXIS2 = {naxis2}")
        if naxis3 != "N/A":
            print(f"  NAXIS3 = {naxis3}")

        # Statistics
        if primary.data is not None and isinstance(primary.data, np.ndarray):
            raw        = primary.data
            shape_str  = str(raw.shape)
            dtype_str  = str(raw.dtype)
            flat       = raw.astype(np.float64).ravel()

            finite_mask = np.isfinite(flat)
            nan_count   = int(np.isnan(flat).sum())
            inf_count   = int(np.isinf(flat).sum())

            if finite_mask.any():
                finite_vals = flat[finite_mask]
                data_min    = float(np.min(finite_vals))
                data_max    = float(np.max(finite_vals))
                data_mean   = float(np.mean(finite_vals))
                data_median = float(np.median(finite_vals))
                data_std    = float(np.std(finite_vals))
            else:
                data_min = data_max = data_mean = data_median = data_std = float("nan")

            print(f"\n  Shape      : {shape_str}")
            print(f"  Dtype      : {dtype_str}")
            print(f"  Min        : {_fmt(data_min)}")
            print(f"  Max        : {_fmt(data_max)}")
            print(f"  Mean       : {_fmt(data_mean)}")
            print(f"  Median     : {_fmt(data_median)}")
            print(f"  Std Dev    : {_fmt(data_std)}")
            print(f"  NaN count  : {nan_count}")
            print(f"  Inf count  : {inf_count}")
        else:
            shape_str  = "None"
            dtype_str  = "None"
            data_min   = data_max = data_mean = data_median = data_std = float("nan")
            nan_count  = 0
            inf_count  = 0
            print("  [INFO] Primary HDU has no array data.")

        # ── 5. Extract metadata ───────────────────────────────────
        all_headers = [hdul[i].header for i in range(len(hdul))]

        object_name = _find_keyword("OBJECT",  "TARGNAME",            headers=all_headers)
        telescop    = _find_keyword("TELESCOP",                        headers=all_headers)
        instrume    = _find_keyword("INSTRUME",                        headers=all_headers)
        date_obs    = _find_keyword("DATE-OBS", "DATE_OBS",            headers=all_headers)
        time_obs    = _find_keyword("TIME-OBS", "TIME_OBS", "UT",      headers=all_headers)
        ra_targ     = _find_keyword("RA_TARG",  "RA",                  headers=all_headers)
        dec_targ    = _find_keyword("DEC_TARG", "DEC",                 headers=all_headers)
        filt        = _find_keyword("FILTER1",  "FILTNAM1", "FILTER",  headers=all_headers)
        exptime     = _find_keyword("EXPTIME",  "EXPOSURE",            headers=all_headers)

        print(f"\n  {sep2}")
        print("  OBSERVATION METADATA")
        print(f"  {sep2}")
        print(f"  Object / Target  : {object_name}")
        print(f"  Telescope        : {telescop}")
        print(f"  Instrument       : {instrume}")
        print(f"  Date-Obs         : {date_obs}")
        print(f"  Time-Obs         : {time_obs}")
        print(f"  RA (target)      : {ra_targ}")
        print(f"  Dec (target)     : {dec_targ}")
        print(f"  Filter           : {filt}")
        print(f"  Exposure time    : {exptime} s")

        # ── Build CSV row ─────────────────────────────────────────
        row.update({
            "object_name"       : object_name,
            "telescop"          : telescop,
            "instrume"          : instrume,
            "date_obs"          : date_obs,
            "time_obs"          : time_obs,
            "ra_targ"           : ra_targ,
            "dec_targ"          : dec_targ,
            "filter"            : filt,
            "exptime"           : exptime,
            "primary_hdu_shape" : shape_str,
            "primary_hdu_dtype" : dtype_str,
            "naxis"             : str(naxis),
            "naxis1"            : str(naxis1),
            "naxis2"            : str(naxis2),
            "naxis3"            : str(naxis3),
            "data_min"          : _fmt(data_min),
            "data_max"          : _fmt(data_max),
            "data_mean"         : _fmt(data_mean),
            "data_median"       : _fmt(data_median),
            "data_std"          : _fmt(data_std),
            "nan_count"         : str(nan_count),
            "inf_count"         : str(inf_count),
            "total_hdu_count"   : str(len(hdul)),
        })

    finally:
        hdul.close()   # always release the file handle

    return row


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
def main() -> None:
    print("=" * 70)
    print("  ASTRA Cloud  --  FITS Analysis")
    print("=" * 70)

    # Discover FITS files (case-insensitive extension match)
    fits_extensions = {".fits", ".fit", ".fts"}
    fits_files = sorted(
        p for p in FITS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in fits_extensions
    )

    if not fits_files:
        print(f"\n[WARN] No FITS files found in: {FITS_DIR}")
        return

    print(f"\n  Found {len(fits_files)} FITS file(s) in: {FITS_DIR}\n")

    rows: list[dict] = []
    for fp in fits_files:
        row = analyse_fits(fp)
        rows.append(row)

    # ── Save CSV ──────────────────────────────────────────────────
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            # Fill any missing keys with "N/A"
            complete_row = {k: row.get(k, "N/A") for k in CSV_FIELDS}
            writer.writerow(complete_row)

    print(f"\n{'=' * 70}")
    print(f"  CSV report saved  →  {CSV_OUT}")
    print(f"  Rows written      :  {len(rows)}")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
