# ============================================================
#  ASTRA Cloud -- Step 18: Master Radio Feature Table
#  File   : ml/create_radio_feature_table.py
#  Purpose: Synthesize metadata, data statistics, signal quality,
#           RFI indicators, profile moments, and DM analysis
#           into a unified master feature table.
#  Output : reports/radio_master_features.csv
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

META_CSV    = REPORTS_DIR / "radio_fits_metadata.csv"
STATS_CSV   = REPORTS_DIR / "radio_data_statistics.csv"
QUAL_CSV    = REPORTS_DIR / "radio_quality.csv"
RFI_CSV     = REPORTS_DIR / "rfi_analysis.csv"
PROF_CSV    = REPORTS_DIR / "pulse_profile_features.csv"
DM_CSV      = REPORTS_DIR / "dm_features.csv"
MASTER_CSV  = REPORTS_DIR / "radio_master_features.csv"

MASTER_FIELDS = [
    "file_name",
    "telescope",
    "target",
    "observation_date",
    "frequency",
    "bandwidth",
    "data_shape",
    "mean",
    "std",
    "noise_estimate",
    "rfi_indicator",
    "profile_mean",
    "profile_std",
    "profile_skewness",
    "profile_kurtosis",
    "dm_mean",
    "dm_std",
    "dm_skewness",
    "dm_kurtosis",
]


def _read_csv_to_dict(csv_path: Path) -> dict:
    data = {}
    if not csv_path.exists():
        print(f"[WARN] File not found: {csv_path}")
        return data
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fname = row.get("file_name")
            if fname:
                data[fname] = row
    return data


def create_master_table() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 18: Master Radio Feature Table")
    print("=" * 68)

    meta_dict  = _read_csv_to_dict(META_CSV)
    stats_dict = _read_csv_to_dict(STATS_CSV)
    qual_dict  = _read_csv_to_dict(QUAL_CSV)
    rfi_dict   = _read_csv_to_dict(RFI_CSV)
    prof_dict  = _read_csv_to_dict(PROF_CSV)
    dm_dict    = _read_csv_to_dict(DM_CSV)

    all_files = sorted(set(meta_dict.keys()) | set(stats_dict.keys()) | set(qual_dict.keys()))

    if not all_files:
        print("[WARN] No observation records found to compile.")
        return

    master_records = []

    for fname in all_files:
        m  = meta_dict.get(fname, {})
        st = stats_dict.get(fname, {})
        q  = qual_dict.get(fname, {})
        r  = rfi_dict.get(fname, {})
        p  = prof_dict.get(fname, {})
        d  = dm_dict.get(fname, {})

        record = {
            "file_name":        fname,
            "telescope":        m.get("telescope", "NOT_AVAILABLE"),
            "target":           m.get("target", "NOT_AVAILABLE"),
            "observation_date": m.get("date_obs", "NOT_AVAILABLE"),
            "frequency":        m.get("frequency", "NOT_AVAILABLE"),
            "bandwidth":        m.get("bandwidth", "NOT_AVAILABLE"),
            "data_shape":       st.get("data_shape", "NOT_AVAILABLE"),
            "mean":             st.get("mean_val", "NOT_AVAILABLE"),
            "std":              st.get("std_val", "NOT_AVAILABLE"),
            "noise_estimate":   q.get("noise_estimate", "NOT_AVAILABLE"),
            "rfi_indicator":    r.get("rfi_indicator", "NOT_AVAILABLE"),
            "profile_mean":     p.get("profile_mean", "NOT_AVAILABLE"),
            "profile_std":      p.get("profile_std", "NOT_AVAILABLE"),
            "profile_skewness":  p.get("profile_skewness", "NOT_AVAILABLE"),
            "profile_kurtosis":  p.get("profile_kurtosis", "NOT_AVAILABLE"),
            "dm_mean":          d.get("dm_mean", "NOT_AVAILABLE"),
            "dm_std":           d.get("dm_std", "NOT_AVAILABLE"),
            "dm_skewness":      d.get("dm_skewness", "NOT_AVAILABLE"),
            "dm_kurtosis":      d.get("dm_kurtosis", "NOT_AVAILABLE"),
        }

        master_records.append(record)
        print(f"Compiled: {fname:<44} | ProfMean={record['profile_mean']:<10} | DM_Mean={record['dm_mean']}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(MASTER_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MASTER_FIELDS)
        writer.writeheader()
        writer.writerows(master_records)

    print(f"\n[OK] Master feature table saved → {MASTER_CSV}")
    print(f"Total compiled observations: {len(master_records)}\n")


if __name__ == "__main__":
    create_master_table()
