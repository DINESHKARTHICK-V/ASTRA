# ============================================================
#  ASTRA Cloud -- Step 20: Create Compatible Radio Dataset
#  File   : ml/create_htru2_compatible_radio.py
#  Purpose: Evaluates whether observations from radio_master_features.csv
#           possess all 8 required HTRU2 features. Files lacking
#           complete compatible features are excluded from inference
#           and logged in reports/radio_feature_rejection.csv.
#  Outputs: reports/radio_htru2_compatible.csv
#           reports/radio_feature_rejection.csv
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

REPO_ROOT     = Path(__file__).resolve().parent.parent
REPORTS_DIR   = REPO_ROOT / "reports"
MASTER_CSV    = REPORTS_DIR / "radio_master_features.csv"
COMPAT_CSV    = REPORTS_DIR / "radio_htru2_compatible.csv"
REJECTION_CSV = REPORTS_DIR / "radio_feature_rejection.csv"

HTRU2_FEATURES = [
    "Profile_Mean",
    "Profile_Std",
    "Profile_Skewness",
    "Profile_Kurtosis",
    "DM_Mean",
    "DM_Std",
    "DM_Skewness",
    "DM_Kurtosis",
]

COMPAT_COLUMNS = [
    "file_name",
    "target",
    "telescope",
    "observation_date",
    "Profile_Mean",
    "Profile_Std",
    "Profile_Skewness",
    "Profile_Kurtosis",
    "DM_Mean",
    "DM_Std",
    "DM_Skewness",
    "DM_Kurtosis",
]

REJECTION_COLUMNS = [
    "file_name",
    "target",
    "telescope",
    "observation_date",
    "missing_features",
    "rejection_reason",
]


def process_compatible_dataset() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 20: Create Compatible Radio Dataset")
    print("=" * 68)

    if not MASTER_CSV.exists():
        raise FileNotFoundError(f"Master feature table not found: {MASTER_CSV}")

    rows = []
    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    compatible_records = []
    rejection_records = []

    for r in rows:
        fname = r.get("file_name", "UNKNOWN")
        target = r.get("target", "NOT_AVAILABLE")
        telescope = r.get("telescope", "NOT_AVAILABLE")
        obs_date = r.get("observation_date", "NOT_AVAILABLE")

        # Check required profile features
        prof_mean = r.get("profile_mean")
        prof_std  = r.get("profile_std")
        prof_skew = r.get("profile_skewness")
        prof_kurt = r.get("profile_kurtosis")

        # Check required DM features
        dm_mean = r.get("dm_mean")
        dm_std  = r.get("dm_std")
        dm_skew = r.get("dm_skewness")
        dm_kurt = r.get("dm_kurtosis")

        missing = []
        if prof_mean in ("NOT_AVAILABLE", "N/A", "", None): missing.append("Profile_Mean")
        if prof_std in ("NOT_AVAILABLE", "N/A", "", None):  missing.append("Profile_Std")
        if prof_skew in ("NOT_AVAILABLE", "N/A", "", None): missing.append("Profile_Skewness")
        if prof_kurt in ("NOT_AVAILABLE", "N/A", "", None): missing.append("Profile_Kurtosis")
        if dm_mean in ("NOT_AVAILABLE", "N/A", "", None):   missing.append("DM_Mean")
        if dm_std in ("NOT_AVAILABLE", "N/A", "", None):    missing.append("DM_Std")
        if dm_skew in ("NOT_AVAILABLE", "N/A", "", None):   missing.append("DM_Skewness")
        if dm_kurt in ("NOT_AVAILABLE", "N/A", "", None):   missing.append("DM_Kurtosis")

        if missing:
            rejection_records.append({
                "file_name": fname,
                "target": target,
                "telescope": telescope,
                "observation_date": obs_date,
                "missing_features": "; ".join(missing),
                "rejection_reason": (
                    f"Observation lacks {len(missing)} required HTRU2 features ({'; '.join(missing)}). "
                    "Fold-mode timing archives do not contain search-mode multi-trial DM-SNR curves. "
                    "Excluded from direct HTRU2 Random Forest inference to prevent domain mismatch."
                ),
            })
            print(f"[EXCLUDED] {fname:<42} | Missing: {'; '.join(missing)}")
        else:
            compatible_records.append({
                "file_name": fname,
                "target": target,
                "telescope": telescope,
                "observation_date": obs_date,
                "Profile_Mean": prof_mean,
                "Profile_Std": prof_std,
                "Profile_Skewness": prof_skew,
                "Profile_Kurtosis": prof_kurt,
                "DM_Mean": dm_mean,
                "DM_Std": dm_std,
                "DM_Skewness": dm_skew,
                "DM_Kurtosis": dm_kurt,
            })
            print(f"[COMPATIBLE] {fname}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Write compatible dataset (headers only if 0 rows qualify)
    with open(COMPAT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COMPAT_COLUMNS)
        writer.writeheader()
        writer.writerows(compatible_records)

    # Write feature rejection log
    with open(REJECTION_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REJECTION_COLUMNS)
        writer.writeheader()
        writer.writerows(rejection_records)

    print(f"\n[OK] Compatible dataset saved  → {COMPAT_CSV} ({len(compatible_records)} records)")
    print(f"[OK] Feature rejection log saved → {REJECTION_CSV} ({len(rejection_records)} rejected records)")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    process_compatible_dataset()
