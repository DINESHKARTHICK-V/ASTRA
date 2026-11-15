# ============================================================
#  ASTRA Cloud -- Step 14: Basic Signal Quality Analysis
#  File   : ml/radio_quality.py
#  Purpose: Compute scientifically grounded quality indicators
#           (mean, std, median, dynamic range, noise estimate)
#           without inventing unverified SNR formulas.
#  Output : reports/radio_quality.csv
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
CSV_OUT     = REPORTS_DIR / "radio_quality.csv"

FIELDS = [
    "file_name",
    "mean",
    "median",
    "std",
    "min",
    "max",
    "dynamic_range",
    "valid_fraction",
    "nan_fraction",
    "inf_fraction",
    "noise_estimate",
    "snr_status",
    "quality_status",
    "notes",
]


def robust_noise_estimate(arr: np.ndarray) -> float:
    """
    Compute Median Absolute Deviation (MAD) noise estimate
    normalized to Gaussian equivalent standard deviation:
    sigma_noise = 1.4826 * median(|x - median(x)|).
    """
    flat = arr.ravel()
    finite = flat[np.isfinite(flat)]
    if finite.size == 0 or np.all(finite == 0):
        return 0.0
    med = np.median(finite)
    mad = np.median(np.abs(finite - med))
    return float(1.4826 * mad)


def analyze_radio_quality() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 14: Basic Signal Quality Analysis")
    print("=" * 68)

    fits_files = sorted(RADIO_DIR.glob("*.fits"))
    if not fits_files:
        print(f"[WARN] No files found in {RADIO_DIR}")
        return

    records = []

    for fp in fits_files:
        row = {k: "NOT_AVAILABLE" for k in FIELDS}
        row["file_name"] = fp.name
        row["snr_status"] = "SNR_NOT_CALCULATED"

        try:
            with fits.open(fp, mode="readonly", memmap=True) as hdul:
                subint = None
                for h in hdul:
                    if h.name.upper() == "SUBINT":
                        subint = h
                        break

                if subint is None or "DATA" not in subint.columns.names:
                    row["quality_status"] = "UNSUPPORTED"
                    row["notes"] = "No SUBINT data table found."
                    records.append(row)
                    continue

                d = subint.data
                raw = d["DATA"][0]

                # Apply calibration if available for accurate flux distribution
                if "DAT_SCL" in subint.columns.names and "DAT_OFFS" in subint.columns.names:
                    scl = d["DAT_SCL"][0].reshape(4, 128, 1)
                    offs = d["DAT_OFFS"][0].reshape(4, 128, 1)
                    data_arr = (raw.astype(np.float64) * scl + offs)[0]  # polarization 0 (AA)
                else:
                    data_arr = raw[0].astype(np.float64)

                flat = data_arr.ravel()
                total_samples = flat.size

                nan_count = int(np.isnan(flat).sum())
                inf_count = int(np.isinf(flat).sum())
                finite = flat[np.isfinite(flat)]

                nan_frac = nan_count / total_samples if total_samples > 0 else 0.0
                inf_frac = inf_count / total_samples if total_samples > 0 else 0.0
                valid_frac = finite.size / total_samples if total_samples > 0 else 0.0

                row["nan_fraction"]   = f"{nan_frac:.6f}"
                row["inf_fraction"]   = f"{inf_frac:.6f}"
                row["valid_fraction"] = f"{valid_frac:.6f}"

                if finite.size == 0 or np.all(finite == 0):
                    row["mean"] = "0.0000"
                    row["median"] = "0.0000"
                    row["std"] = "0.0000"
                    row["min"] = "0.0000"
                    row["max"] = "0.0000"
                    row["dynamic_range"] = "0.0000"
                    row["noise_estimate"] = "0.0000"
                    row["quality_status"] = "BLANK_OBSERVATION"
                    row["notes"] = "Observation contains all-zero pixel counts (uncalibrated / blank frame)."
                else:
                    d_min = float(np.min(finite))
                    d_max = float(np.max(finite))
                    d_mean = float(np.mean(finite))
                    d_median = float(np.median(finite))
                    d_std = float(np.std(finite))
                    dyn_range = d_max - d_min
                    noise_est = robust_noise_estimate(finite)

                    row["min"] = f"{d_min:.4f}"
                    row["max"] = f"{d_max:.4f}"
                    row["mean"] = f"{d_mean:.4f}"
                    row["median"] = f"{d_median:.4f}"
                    row["std"] = f"{d_std:.4f}"
                    row["dynamic_range"] = f"{dyn_range:.4f}"
                    row["noise_estimate"] = f"{noise_est:.4f}"

                    if nan_count > 0 or inf_count > 0:
                        row["quality_status"] = "WARNING"
                        row["notes"] = f"Observation readable with {nan_count} NaNs and {inf_count} Infs."
                    else:
                        row["quality_status"] = "VALID"
                        row["notes"] = "Nominal radio observation; 100% valid samples with clear baseline noise floor."

        except Exception as exc:
            row["quality_status"] = "ERROR"
            row["notes"] = f"Quality evaluation error: {exc}"

        records.append(row)
        print(f"[{row['quality_status']}] {row['file_name']} | Mean={row['mean']} | NoiseEst={row['noise_estimate']} | SNR={row['snr_status']}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print(f"\n[OK] Signal quality analysis saved → {CSV_OUT}")
    print(f"Total processed files: {len(records)}\n")


if __name__ == "__main__":
    analyze_radio_quality()
