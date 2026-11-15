# ============================================================
#  ASTRA Cloud -- FITS Quality Checker
#  File   : ml/fits_quality.py
#  Purpose: Run basic quality checks on every FITS file found
#           in data/fits/ and emit a per-file quality status
#           (VALID / WARNING / ERROR) plus detailed metrics to
#           reports/fits_quality.csv.
#  Deps   : astropy, numpy
#  NOTE   : Read-only — FITS files are never modified.
# ============================================================

import sys
import io
import csv
import math
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.utils.exceptions import AstropyWarning

# UTF-8 output (clean printing on Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Suppress non-critical astropy warnings
warnings.filterwarnings("ignore", category=AstropyWarning)

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent.parent
FITS_DIR    = REPO_ROOT / "data" / "fits"
REPORTS_DIR = REPO_ROOT / "reports"
CSV_OUT     = REPORTS_DIR / "fits_quality.csv"

# ------------------------------------------------------------------
# CSV column order
# ------------------------------------------------------------------
CSV_FIELDS = [
    "fits_file",
    "status",
    "status_reason",
    "hdu_count",
    "numeric_data_available",
    "data_dimensions",
    "total_pixels",
    "nan_count",
    "inf_count",
    "invalid_pixel_pct",
    "zero_pixel_count",
    "zero_pixel_pct",
    "data_min",
    "data_max",
    "data_mean",
    "data_median",
    "data_std",
]

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _fmt(value: float, precision: int = 6) -> str:
    """Format a float; return 'N/A' for NaN / None / Inf."""
    if value is None:
        return "N/A"
    try:
        if math.isnan(value) or math.isinf(value):
            return "N/A"
        return f"{value:.{precision}f}"
    except (TypeError, ValueError):
        return str(value)


def _pct(numerator: int, denominator: int) -> str:
    """Return percentage string or '0.000000' when denominator is zero."""
    if denominator == 0:
        return "0.000000"
    return f"{100.0 * numerator / denominator:.6f}"


# ------------------------------------------------------------------
# Core quality check for one FITS file
# ------------------------------------------------------------------
def check_fits(fits_path: Path) -> dict:
    """
    Run all quality checks on *fits_path* and return a result dict
    containing every CSV field.  The FITS file is never modified.
    """
    sep  = "=" * 65
    sep2 = "-" * 65
    fname = fits_path.name

    print(f"\n{sep}")
    print(f"  FILE : {fname}")
    print(sep)

    row: dict = {k: "N/A" for k in CSV_FIELDS}
    row["fits_file"] = fname

    # ── Check 1: File can be opened ──────────────────────────────
    try:
        hdul = fits.open(fits_path, mode="readonly", memmap=True,
                         ignore_missing_simple=True)
    except Exception as exc:
        msg = f"Cannot open file: {exc}"
        print(f"  [ERROR] {msg}")
        row["status"]        = "ERROR"
        row["status_reason"] = msg
        row["hdu_count"]     = "0"
        row["numeric_data_available"] = "False"
        return row

    try:
        # ── Check 2: HDU count ───────────────────────────────────
        hdu_count = len(hdul)
        row["hdu_count"] = str(hdu_count)
        print(f"  HDU count           : {hdu_count}")

        # ── Check 3: Numeric data availability ───────────────────
        # Walk all HDUs; gather the first usable numeric ndarray.
        numeric_data: np.ndarray | None = None
        for hdu in hdul:
            d = hdu.data
            if d is not None and isinstance(d, np.ndarray) and np.issubdtype(d.dtype, np.number):
                numeric_data = d
                break

        has_numeric = numeric_data is not None
        row["numeric_data_available"] = str(has_numeric)
        print(f"  Numeric data found  : {has_numeric}")

        if not has_numeric:
            msg = "No usable numeric data in any HDU"
            print(f"  [ERROR] {msg}")
            row["status"]        = "ERROR"
            row["status_reason"] = msg
            return row

        # ── Checks 4 – 13: Computed from the numeric array ───────
        # Convert to float64 and flatten for uniform statistics.
        flat = numeric_data.astype(np.float64).ravel()

        # Check 4: Data dimensions
        dims = str(numeric_data.shape)
        row["data_dimensions"] = dims
        print(f"  Data dimensions     : {dims}")

        total_pixels = flat.size
        row["total_pixels"] = str(total_pixels)
        print(f"  Total pixels        : {total_pixels}")

        # Check 5: NaN count
        nan_count = int(np.isnan(flat).sum())
        row["nan_count"] = str(nan_count)
        print(f"  NaN count           : {nan_count}")

        # Check 6: Inf count
        inf_count = int(np.isinf(flat).sum())
        row["inf_count"] = str(inf_count)
        print(f"  Inf count           : {inf_count}")

        # Invalid pixel percentage (NaN + Inf)
        invalid_count = nan_count + inf_count
        invalid_pct   = _pct(invalid_count, total_pixels)
        row["invalid_pixel_pct"] = invalid_pct
        print(f"  Invalid pixels      : {invalid_count}  ({invalid_pct} %)")

        # Zero-valued pixels (finite zeros)
        zero_count = int((flat == 0.0).sum())
        zero_pct   = _pct(zero_count, total_pixels)
        row["zero_pixel_count"] = str(zero_count)
        row["zero_pixel_pct"]   = zero_pct
        print(f"  Zero pixels         : {zero_count}  ({zero_pct} %)")

        # Statistics computed on finite pixels only
        finite = flat[np.isfinite(flat)]
        if finite.size > 0:
            data_min    = float(np.min(finite))
            data_max    = float(np.max(finite))
            data_mean   = float(np.mean(finite))
            data_median = float(np.median(finite))
            data_std    = float(np.std(finite))
        else:
            data_min = data_max = data_mean = data_median = data_std = float("nan")

        # Check 7: Minimum
        row["data_min"] = _fmt(data_min)
        print(f"  Min                 : {_fmt(data_min)}")

        # Check 8: Maximum
        row["data_max"] = _fmt(data_max)
        print(f"  Max                 : {_fmt(data_max)}")

        # Check 9: Mean
        row["data_mean"] = _fmt(data_mean)
        print(f"  Mean                : {_fmt(data_mean)}")

        # Check 10: Median
        row["data_median"] = _fmt(data_median)
        print(f"  Median              : {_fmt(data_median)}")

        # Check 11: Standard deviation
        row["data_std"] = _fmt(data_std)
        print(f"  Std Dev             : {_fmt(data_std)}")

        # ── Quality status ────────────────────────────────────────
        # ERROR  : already returned above (open failure / no data)
        # WARNING: any NaN or Inf present
        # VALID  : readable, numeric, no invalid pixels
        print(f"\n  {sep2}")
        if invalid_count > 0:
            reason = (
                f"{nan_count} NaN pixel(s) and {inf_count} Inf pixel(s) detected"
            )
            row["status"]        = "WARNING"
            row["status_reason"] = reason
            print(f"  STATUS  : ⚠  WARNING")
            print(f"  REASON  : {reason}")
        else:
            row["status"]        = "VALID"
            row["status_reason"] = "All pixels finite; data readable and complete"
            print(f"  STATUS  : ✓  VALID")
            print(f"  REASON  : {row['status_reason']}")
        print(f"  {sep2}")

    finally:
        hdul.close()    # always release the file handle

    return row


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
def main() -> None:
    print("=" * 65)
    print("  ASTRA Cloud  --  FITS Quality Checker")
    print("=" * 65)

    fits_extensions = {".fits", ".fit", ".fts"}
    fits_files = sorted(
        p for p in FITS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in fits_extensions
    )

    if not fits_files:
        print(f"\n[WARN] No FITS files found in: {FITS_DIR}")
        return

    print(f"\n  Found {len(fits_files)} FITS file(s) in: {FITS_DIR}")

    rows: list[dict] = []
    summary = {"VALID": 0, "WARNING": 0, "ERROR": 0}

    for fp in fits_files:
        row = check_fits(fp)
        rows.append(row)
        status = row.get("status", "ERROR")
        summary[status] = summary.get(status, 0) + 1

    # ── Save CSV ──────────────────────────────────────────────────
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            complete = {k: row.get(k, "N/A") for k in CSV_FIELDS}
            writer.writerow(complete)

    # ── Summary ───────────────────────────────────────────────────
    print(f"\n{'=' * 65}")
    print("  QUALITY SUMMARY")
    print(f"  {'─' * 30}")
    print(f"  Files checked : {len(rows)}")
    print(f"  VALID         : {summary.get('VALID',   0)}")
    print(f"  WARNING       : {summary.get('WARNING', 0)}")
    print(f"  ERROR         : {summary.get('ERROR',   0)}")
    print(f"  {'─' * 30}")
    print(f"  CSV saved →   {CSV_OUT}")
    print(f"{'=' * 65}\n")


if __name__ == "__main__":
    main()
