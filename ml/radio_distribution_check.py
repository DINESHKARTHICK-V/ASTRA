# ============================================================
#  ASTRA Cloud -- Step 22: Check Out-Of-Distribution Data
#  File   : ml/radio_distribution_check.py
#  Purpose: Transparently evaluate whether extracted real-radio
#           features lie outside the HTRU2 training domain range.
#           Provides domain-shift and data-quality warnings.
#  Output : reports/radio_distribution_check.csv
# ============================================================

import sys
import io
import csv
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

warnings.filterwarnings("ignore", category=UserWarning)

REPO_ROOT   = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
DATA_DIR    = REPO_ROOT / "data"

HTRU2_CSV   = DATA_DIR / "htru2" / "HTRU_2.csv"
RADIO_CSV   = REPORTS_DIR / "radio_master_features.csv"
CSV_OUT     = REPORTS_DIR / "radio_distribution_check.csv"

HTRU2_COLUMNS = [
    "Profile_Mean",
    "Profile_Std",
    "Profile_Skewness",
    "Profile_Kurtosis",
    "DM_Mean",
    "DM_Std",
    "DM_Skewness",
    "DM_Kurtosis",
    "Target",
]

CSV_FIELDS = [
    "file_name",
    "feature_outside_training_range",
    "number_of_out_of_range_features",
    "distribution_warning",
]


def check_out_of_distribution() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 22: Check Out-Of-Distribution Data")
    print("=" * 68)

    if not HTRU2_CSV.exists() or not RADIO_CSV.exists():
        raise FileNotFoundError("Missing HTRU2 or radio master feature dataset.")

    # Load HTRU2 ranges
    first_line = pd.read_csv(HTRU2_CSV, nrows=1)
    if "Profile_Mean" in first_line.columns or "mean_ip" in first_line.columns:
        htru2_df = pd.read_csv(HTRU2_CSV)
        htru2_df.columns = HTRU2_COLUMNS
    else:
        htru2_df = pd.read_csv(HTRU2_CSV, header=None, names=HTRU2_COLUMNS)

    ranges = {}
    for col in HTRU2_COLUMNS[:-1]:
        s = pd.to_numeric(htru2_df[col], errors="coerce").dropna()
        ranges[col] = (float(s.min()), float(s.max()))

    print("HTRU2 Training Feature Ranges:")
    for col, (rmin, rmax) in ranges.items():
        print(f"  {col:<18}: [{rmin:>9.4f}, {rmax:>9.4f}]")
    print()

    # Load Radio Observations
    radio_df = pd.read_csv(RADIO_CSV)
    records = []

    feature_pairs = [
        ("Profile_Mean", "profile_mean"),
        ("Profile_Std", "profile_std"),
        ("Profile_Skewness", "profile_skewness"),
        ("Profile_Kurtosis", "profile_kurtosis"),
    ]

    for _, row in radio_df.iterrows():
        fname = row["file_name"]
        out_of_range = []

        if row.get("mean") == "0.0000":
            records.append({
                "file_name": fname,
                "feature_outside_training_range": "ALL_FEATURES (Blank frame)",
                "number_of_out_of_range_features": "8",
                "distribution_warning": "CRITICAL_BLANK_OBSERVATION: Observation contains all-zero pixel counts.",
            })
            print(f"[BLANK] {fname:<44} | 8 out of range")
            continue

        for h_name, r_name in feature_pairs:
            val_str = row.get(r_name)
            try:
                val = float(val_str)
                rmin, rmax = ranges[h_name]
                if val < rmin or val > rmax:
                    out_of_range.append(f"{h_name} ({val:.2f} ∉ [{rmin:.2f}, {rmax:.2f}])")
            except (ValueError, TypeError):
                out_of_range.append(f"{h_name} (MISSING)")

        # DM features are completely absent in folded timing data
        for dm_col in ["DM_Mean", "DM_Std", "DM_Skewness", "DM_Kurtosis"]:
            out_of_range.append(f"{dm_col} (ABSENT_IN_FOLD_MODE)")

        num_out = len(out_of_range)

        if num_out >= 4:
            warning = "HIGH_DOMAIN_SHIFT: Unnormalized profile baseline and missing DM-SNR curve."
        elif num_out > 0:
            warning = "MODERATE_DOMAIN_SHIFT: Specific feature magnitudes diverge from training domain."
        else:
            warning = "IN_DISTRIBUTION: Feature values fall within training range bounds."

        records.append({
            "file_name": fname,
            "feature_outside_training_range": "; ".join(out_of_range),
            "number_of_out_of_range_features": str(num_out),
            "distribution_warning": warning,
        })

        print(f"[{warning[:18]}] {fname:<42} | Out-of-range features: {num_out}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print(f"\n[OK] Distribution check report saved → {CSV_OUT}")
    print(f"Total checked observations: {len(records)}\n")


if __name__ == "__main__":
    check_out_of_distribution()
