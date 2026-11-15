# ============================================================
#  ASTRA Cloud -- Step 12: Scientific Data Structure Analysis
#  File   : ml/radio_data_structure.py
#  Purpose: Analyze the scientific data HDU and multidimensional
#           arrays for all VALID_RADIO and VALID_PSRFITS files.
#           Computes descriptive numerical statistics and records
#           the exact physical data representation.
#  Output : reports/radio_data_statistics.csv
# ============================================================

import sys
import io
import csv
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.utils.exceptions import AstropyWarning

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

warnings.filterwarnings("ignore", category=AstropyWarning)

REPO_ROOT   = Path(__file__).resolve().parent.parent
RADIO_DIR   = REPO_ROOT / "data" / "radio_fits"
REPORTS_DIR = REPO_ROOT / "reports"
CSV_OUT     = REPORTS_DIR / "radio_data_statistics.csv"

FIELDS = [
    "file_name",
    "scientific_hdu",
    "dimensions_count",
    "data_shape",
    "dimension_labels",
    "dtype",
    "min_val",
    "max_val",
    "mean_val",
    "median_val",
    "std_val",
    "nan_count",
    "inf_count",
    "data_representation",
]


def analyze_data_structure() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 12: Scientific Data Structure Analysis")
    print("=" * 68)

    fits_files = sorted(RADIO_DIR.glob("*.fits"))
    if not fits_files:
        print(f"[WARN] No files found in {RADIO_DIR}")
        return

    records = []

    for fp in fits_files:
        row = {k: "NOT_AVAILABLE" for k in FIELDS}
        row["file_name"] = fp.name

        try:
            with fits.open(fp, mode="readonly", memmap=True) as hdul:
                # 1. Identify scientific data HDU
                subint = None
                for h in hdul:
                    if h.name.upper() == "SUBINT":
                        subint = h
                        break

                if subint is not None and "DATA" in subint.columns.names:
                    row["scientific_hdu"] = "SUBINT (HDU 4, column 'DATA')"
                    data_col = subint.data["DATA"]
                    shape = data_col.shape
                    row["dimensions_count"] = str(len(shape))
                    row["data_shape"] = str(shape)
                    row["dimension_labels"] = "NSUBINT x NPOL x NCHAN x NBIN"
                    row["dtype"] = str(data_col.dtype)

                    # Compute statistics on the raw data array
                    flat = data_col.ravel()
                    if np.issubdtype(flat.dtype, np.floating):
                        nan_c = int(np.isnan(flat).sum())
                        inf_c = int(np.isinf(flat).sum())
                        finite = flat[np.isfinite(flat)]
                    else:
                        nan_c = 0
                        inf_c = 0
                        finite = flat.astype(np.float64)

                    row["nan_count"] = str(nan_c)
                    row["inf_count"] = str(inf_c)

                    if finite.size > 0:
                        row["min_val"]    = f"{np.min(finite):.4f}"
                        row["max_val"]    = f"{np.max(finite):.4f}"
                        row["mean_val"]   = f"{np.mean(finite):.4f}"
                        row["median_val"] = f"{np.median(finite):.4f}"
                        row["std_val"]    = f"{np.std(finite):.4f}"

                    row["data_representation"] = (
                        "Folded pulse profile raw ADC counts (16-bit integer) across sub-integrations, "
                        "polarizations, channels, and phase bins. Scaled to physical flux units via DAT_SCL and DAT_OFFS."
                    )

                elif hdul[0].data is not None and isinstance(hdul[0].data, np.ndarray):
                    # Image-like primary HDU fallback
                    row["scientific_hdu"] = "PRIMARY (HDU 0)"
                    pdata = hdul[0].data
                    shape = pdata.shape
                    row["dimensions_count"] = str(len(shape))
                    row["data_shape"] = str(shape)
                    row["dimension_labels"] = "x".join(f"Axis{i}" for i in range(len(shape)))
                    row["dtype"] = str(pdata.dtype)

                    flat = pdata.ravel()
                    if np.issubdtype(flat.dtype, np.floating):
                        nan_c = int(np.isnan(flat).sum())
                        inf_c = int(np.isinf(flat).sum())
                        finite = flat[np.isfinite(flat)]
                    else:
                        nan_c = 0
                        inf_c = 0
                        finite = flat.astype(np.float64)

                    row["nan_count"] = str(nan_c)
                    row["inf_count"] = str(inf_c)
                    if finite.size > 0:
                        row["min_val"]    = f"{np.min(finite):.4f}"
                        row["max_val"]    = f"{np.max(finite):.4f}"
                        row["mean_val"]   = f"{np.mean(finite):.4f}"
                        row["median_val"] = f"{np.median(finite):.4f}"
                        row["std_val"]    = f"{np.std(finite):.4f}"

                    row["data_representation"] = "Astronomical intensity array."

        except Exception as e:
            row["data_representation"] = f"Analysis error: {e}"

        records.append(row)
        print(f"[PROCESSED] {row['file_name']} | Shape={row['data_shape']} | Min={row['min_val']} | Max={row['max_val']} | Mean={row['mean_val']} | Std={row['std_val']}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print(f"\n[OK] Data statistics saved → {CSV_OUT}")
    print(f"Total analyzed files: {len(records)}\n")


if __name__ == "__main__":
    analyze_data_structure()
