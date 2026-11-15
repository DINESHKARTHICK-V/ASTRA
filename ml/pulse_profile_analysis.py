# ============================================================
#  ASTRA Cloud -- Step 16: Pulse Profile Analysis
#  File   : ml/pulse_profile_analysis.py
#  Purpose: Extract 1D integrated pulse profile and compute
#           statistical moments (mean, std, skewness, kurtosis)
#           from valid radio PSRFITS files.
#  Output : reports/pulse_profile_features.csv
# ============================================================

import sys
import io
import csv
import warnings
from pathlib import Path

import numpy as np
import scipy.stats as stats
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
CSV_OUT     = REPORTS_DIR / "pulse_profile_features.csv"

FIELDS = [
    "file_name",
    "profile_mean",
    "profile_std",
    "profile_skewness",
    "profile_kurtosis",
    "profile_bins",
    "profile_status",
    "notes",
]


def analyze_pulse_profiles() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 16: Pulse Profile Analysis")
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
                subint = None
                for h in hdul:
                    if h.name.upper() == "SUBINT":
                        subint = h
                        break

                if subint is None or "DATA" not in subint.columns.names:
                    row["profile_status"] = "PROFILE_DATA_NOT_FOUND"
                    row["notes"] = "File lacks SUBINT table with folded profile arrays."
                    records.append(row)
                    continue

                d = subint.data
                raw = d["DATA"][0]

                if np.all(raw == 0):
                    row["profile_mean"] = "0.0000"
                    row["profile_std"] = "0.0000"
                    row["profile_skewness"] = "0.0000"
                    row["profile_kurtosis"] = "0.0000"
                    row["profile_bins"] = str(raw.shape[-1])
                    row["profile_status"] = "BLANK_OBSERVATION"
                    row["notes"] = "All pixel values are zero (uncalibrated blank frame)."
                    records.append(row)
                    continue

                # Calibrate and form weighted Stokes I profile
                if "DAT_SCL" in subint.columns.names and "DAT_OFFS" in subint.columns.names:
                    scl = d["DAT_SCL"][0].reshape(4, 128, 1)
                    offs = d["DAT_OFFS"][0].reshape(4, 128, 1)
                    cal_data = raw.astype(np.float64) * scl + offs
                    stokes_i = cal_data[0] + cal_data[1]  # (128, 2048)
                else:
                    stokes_i = raw[0].astype(np.float64) + raw[1].astype(np.float64)

                weights = d["DAT_WTS"][0] if "DAT_WTS" in subint.columns.names else np.ones(stokes_i.shape[0])
                total_wt = float(np.sum(weights))

                if total_wt > 0:
                    profile = (stokes_i * weights[:, None]).sum(axis=0) / total_wt
                else:
                    profile = stokes_i.mean(axis=0)

                nbins = len(profile)
                p_mean = float(np.mean(profile))
                p_std  = float(np.std(profile))
                p_skew = float(stats.skew(profile))
                p_kurt = float(stats.kurtosis(profile, fisher=True))  # excess kurtosis

                row["profile_mean"] = f"{p_mean:.4f}"
                row["profile_std"] = f"{p_std:.4f}"
                row["profile_skewness"] = f"{p_skew:.4f}"
                row["profile_kurtosis"] = f"{p_kurt:.4f}"
                row["profile_bins"] = str(nbins)
                row["profile_status"] = "VALID_PROFILE"
                row["notes"] = (
                    "Integrated 1D Stokes I profile across 2048 bins, weighted by observatory weights. "
                    "Distinct physical representation from normalized HTRU2 candidate feature vectors."
                )

        except Exception as exc:
            row["profile_status"] = "ERROR"
            row["notes"] = f"Profile computation error: {exc}"

        records.append(row)
        print(f"[{row['profile_status']}] {row['file_name']} | Mean={row['profile_mean']} | Std={row['profile_std']} | Skew={row['profile_skewness']} | Kurt={row['profile_kurtosis']}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print(f"\n[OK] Pulse profile features saved → {CSV_OUT}")
    print(f"Total processed files: {len(records)}\n")


if __name__ == "__main__":
    analyze_pulse_profiles()
