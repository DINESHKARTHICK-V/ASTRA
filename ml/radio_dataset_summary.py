# ============================================================
#  ASTRA Cloud -- Step 10: Create Dataset Summary
#  File   : ml/radio_dataset_summary.py
#  Purpose: Reads reports/radio_fits_validation.csv, computes
#           statistical aggregations, and outputs:
#             1. reports/radio_dataset_summary.csv
#             2. reports/radio_dataset_summary.txt
# ============================================================

import sys
import io
import csv
from pathlib import Path

# UTF-8 output formatting
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT   = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
CSV_IN      = REPORTS_DIR / "radio_fits_validation.csv"
CSV_OUT     = REPORTS_DIR / "radio_dataset_summary.csv"
TXT_OUT     = REPORTS_DIR / "radio_dataset_summary.txt"


def generate_summary() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 10: Radio Dataset Summary")
    print("=" * 68)

    if not CSV_IN.exists():
        raise FileNotFoundError(f"Input validation CSV not found: {CSV_IN}")

    rows = []
    with open(CSV_IN, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    total_downloaded = len(rows)
    valid_fits_count = sum(1 for r in rows if r.get("valid_fits") == "YES")
    valid_radio_count = sum(1 for r in rows if r.get("validation_status") in ("VALID_RADIO", "VALID_PSRFITS"))
    invalid_count = sum(1 for r in rows if r.get("validation_status") == "INVALID_FITS")
    unsupported_count = sum(1 for r in rows if r.get("validation_status") == "UNSUPPORTED")

    # Files with missing metadata
    def has_missing_metadata(r: dict) -> bool:
        keys_to_check = ["telescope", "instrument", "target", "date_obs", "frequency"]
        return any(r.get(k) in ("NOT_AVAILABLE", "N/A", "", None) for k in keys_to_check)

    missing_metadata_count = sum(1 for r in rows if has_missing_metadata(r))

    # Files with NaN / Inf
    def count_val(val_str: str) -> int:
        try:
            return int(val_str)
        except (ValueError, TypeError):
            return 0

    nan_files_count = sum(1 for r in rows if count_val(r.get("nan_count")) > 0)
    inf_files_count = sum(1 for r in rows if count_val(r.get("inf_count")) > 0)

    # Totals for observations, unique targets, telescopes, instruments
    targets = set(r.get("target") for r in rows if r.get("target") not in ("NOT_AVAILABLE", "N/A", "", None))
    telescopes = set(r.get("telescope") for r in rows if r.get("telescope") not in ("NOT_AVAILABLE", "N/A", "", None))
    instruments = set(r.get("instrument") for r in rows if r.get("instrument") not in ("NOT_AVAILABLE", "N/A", "", None))

    summary_metrics = [
        {"metric": "Total downloaded files", "value": total_downloaded},
        {"metric": "Valid FITS files", "value": valid_fits_count},
        {"metric": "Valid radio/pulsar FITS files", "value": valid_radio_count},
        {"metric": "Invalid files", "value": invalid_count},
        {"metric": "Unsupported files", "value": unsupported_count},
        {"metric": "Files with missing metadata", "value": missing_metadata_count},
        {"metric": "Files with NaN", "value": nan_files_count},
        {"metric": "Files with Inf", "value": inf_files_count},
        {"metric": "Number of observations", "value": total_downloaded},
        {"metric": "Number of unique targets", "value": len(targets)},
        {"metric": "Number of telescopes", "value": len(telescopes)},
        {"metric": "Number of instruments", "value": len(instruments)},
    ]

    # 1. Write reports/radio_dataset_summary.csv
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(summary_metrics)

    # 2. Write reports/radio_dataset_summary.txt
    txt_content = (
        "ASTRA Cloud -- Real Radio & Pulsar Observation Dataset Summary\n"
        "==============================================================\n\n"
        f"Total downloaded files:          {total_downloaded}\n"
        f"Valid FITS files:                {valid_fits_count}\n"
        f"Valid radio/pulsar FITS files:   {valid_radio_count}\n"
        f"Invalid files:                   {invalid_count}\n"
        f"Unsupported files:               {unsupported_count}\n"
        f"Files with missing metadata:     {missing_metadata_count}\n"
        f"Files with NaN:                  {nan_files_count}\n"
        f"Files with Inf:                  {inf_files_count}\n\n"
        f"Number of observations:          {total_downloaded}\n"
        f"Number of unique targets:        {len(targets)} ({', '.join(sorted(targets))})\n"
        f"Number of telescopes:            {len(telescopes)} ({', '.join(sorted(telescopes))})\n"
        f"Number of instruments:           {len(instruments)} ({', '.join(sorted(instruments))})\n\n"
        "==============================================================\n"
        "Observations List:\n"
        "==============================================================\n"
    )

    for i, r in enumerate(rows, start=1):
        txt_content += (
            f"{i:2d}. {r['file_name']}\n"
            f"    Target: {r['target']} | Telescope: {r['telescope']} | Instrument: {r['instrument']}\n"
            f"    Date: {r['date_obs']} | Freq: {r['frequency']} MHz | Shape: {r['data_shape']}\n"
            f"    Status: {r['validation_status']}\n\n"
        )

    with open(TXT_OUT, "w", encoding="utf-8") as f:
        f.write(txt_content)

    print(f"[OK] Saved CSV summary → {CSV_OUT}")
    print(f"[OK] Saved TXT summary → {TXT_OUT}")
    print("\nSummary Metrics:")
    for sm in summary_metrics:
        print(f"  {sm['metric']:<32}: {sm['value']}")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    generate_summary()
