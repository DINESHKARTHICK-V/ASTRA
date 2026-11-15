# ============================================================
#  ASTRA Cloud -- Step 19: Check Feature Compatibility
#  File   : ml/check_feature_compatibility.py
#  Purpose: Compare extracted real-radio features from
#           reports/radio_master_features.csv against the
#           8 HTRU2 model features. Assesses physical meaning,
#           scale consistency, and model compatibility.
#  Output : reports/feature_compatibility.csv
# ============================================================

import sys
import io
import csv
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT   = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
MASTER_CSV  = REPORTS_DIR / "radio_master_features.csv"
CSV_OUT     = REPORTS_DIR / "feature_compatibility.csv"

FIELDS = [
    "feature_name",
    "available",
    "source_column",
    "scientific_meaning",
    "htru2_compatible",
    "notes",
]

HTRU2_FEATURES = [
    {
        "feature_name": "Profile_Mean",
        "source_column": "profile_mean",
        "scientific_meaning": "Mean intensity level across the integrated pulse profile.",
        "eval_fn": lambda row: row.get("profile_mean") not in ("NOT_AVAILABLE", "N/A", "", None),
        "compatibility": "NOT_COMPATIBLE",
        "notes": "Available in 11 active radio files, but unnormalized baseline flux (~17,000 ADU) strongly differs from HTRU2 normalized candidate mean (~111.0 ADU). Requires domain normalization before ML ingestion.",
    },
    {
        "feature_name": "Profile_Std",
        "source_column": "profile_std",
        "scientific_meaning": "Standard deviation / flux dispersion of the integrated pulse profile.",
        "eval_fn": lambda row: row.get("profile_std") not in ("NOT_AVAILABLE", "N/A", "", None),
        "compatibility": "NOT_COMPATIBLE",
        "notes": "Available in 11 active radio files, but scale is sensitive to bin resolution (2048 bins vs ~64-128 bins in HTRU2 candidates) and telescope gain.",
    },
    {
        "feature_name": "Profile_Skewness",
        "source_column": "profile_skewness",
        "scientific_meaning": "Third standardized statistical moment (asymmetry) of the integrated pulse profile.",
        "eval_fn": lambda row: row.get("profile_skewness") not in ("NOT_AVAILABLE", "N/A", "", None),
        "compatibility": "PARTIALLY_COMPATIBLE",
        "notes": "Dimensionless statistical moment available in 11 active files. Represents pulse shape asymmetry, though narrower duty cycle in 2048-bin timing archives affects moment magnitude.",
    },
    {
        "feature_name": "Profile_Kurtosis",
        "source_column": "profile_kurtosis",
        "scientific_meaning": "Fourth standardized statistical moment (excess kurtosis/peakedness) of the pulse profile.",
        "eval_fn": lambda row: row.get("profile_kurtosis") not in ("NOT_AVAILABLE", "N/A", "", None),
        "compatibility": "PARTIALLY_COMPATIBLE",
        "notes": "Dimensionless statistical moment available in 11 active files. Quantifies pulse peak sharpness relative to baseline.",
    },
    {
        "feature_name": "DM_Mean",
        "source_column": "dm_mean",
        "scientific_meaning": "Mean of the signal-to-noise ratio curve evaluated across hundreds of trial Dispersion Measures (search mode).",
        "eval_fn": lambda row: row.get("dm_mean") not in ("NOT_AVAILABLE", "N/A", "", None),
        "compatibility": "NOT_COMPATIBLE",
        "notes": "MISSING. Radio files are folded timing archives at a single physical DM (15.992 pc/cm³). Multi-trial de-dispersion search curves do not exist in single-DM folded timing archives.",
    },
    {
        "feature_name": "DM_Std",
        "source_column": "dm_std",
        "scientific_meaning": "Standard deviation of the DM-SNR curve across trial dispersion measures.",
        "eval_fn": lambda row: row.get("dm_std") not in ("NOT_AVAILABLE", "N/A", "", None),
        "compatibility": "NOT_COMPATIBLE",
        "notes": "MISSING. Search-mode DM-SNR trial series is absent in folded timing data.",
    },
    {
        "feature_name": "DM_Skewness",
        "source_column": "dm_skewness",
        "scientific_meaning": "Skewness of the DM-SNR trial distribution.",
        "eval_fn": lambda row: row.get("dm_skewness") not in ("NOT_AVAILABLE", "N/A", "", None),
        "compatibility": "NOT_COMPATIBLE",
        "notes": "MISSING. Cannot be derived from single-DM timing observations.",
    },
    {
        "feature_name": "DM_Kurtosis",
        "source_column": "dm_kurtosis",
        "scientific_meaning": "Excess kurtosis of the DM-SNR curve reflecting sharpness of signal peak at optimal DM.",
        "eval_fn": lambda row: row.get("dm_kurtosis") not in ("NOT_AVAILABLE", "N/A", "", None),
        "compatibility": "NOT_COMPATIBLE",
        "notes": "MISSING. Requires raw search-mode filterbank data across varying trial DMs.",
    },
]


def check_compatibility() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 19: Check Feature Compatibility")
    print("=" * 68)

    if not MASTER_CSV.exists():
        raise FileNotFoundError(f"Master feature table not found: {MASTER_CSV}")

    rows = []
    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    total_files = len(rows)
    print(f"Inspecting {total_files} observation records against HTRU2 feature schema...\n")

    results = []

    for feat in HTRU2_FEATURES:
        fname = feat["feature_name"]
        available_count = sum(1 for r in rows if feat["eval_fn"](r))
        is_available = f"YES ({available_count}/{total_files})" if available_count > 0 else "NO (0/12)"

        res = {
            "feature_name": fname,
            "available": is_available,
            "source_column": feat["source_column"],
            "scientific_meaning": feat["scientific_meaning"],
            "htru2_compatible": feat["compatibility"],
            "notes": feat["notes"],
        }
        results.append(res)
        print(f"[{res['htru2_compatible']:<20}] {fname:<18} | Available: {is_available:<12} | Source: {res['source_column']}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[OK] Feature compatibility report saved → {CSV_OUT}")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    check_compatibility()
