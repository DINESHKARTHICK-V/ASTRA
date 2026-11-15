# ============================================================
#  ASTRA Cloud -- Step 17: Dispersion / DM Analysis
#  File   : ml/dm_analysis.py
#  Purpose: Inspect radio files for Dispersion Measure (DM)
#           parameters, trial tables, and DM-SNR curves.
#           Records nominal physical DM and transparently flags
#           absence of multi-trial search-mode curves.
#  Output : reports/dm_features.csv
# ============================================================

import sys
import io
import csv
import warnings
from pathlib import Path
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
CSV_OUT     = REPORTS_DIR / "dm_features.csv"

FIELDS = [
    "file_name",
    "dm_available",
    "dm_value",
    "dm_mean",
    "dm_std",
    "dm_skewness",
    "dm_kurtosis",
    "dm_status",
    "notes",
]


def analyze_dispersion() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 17: Dispersion / DM Analysis")
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
                h0 = hdul[0].header

                # Look for DM in Primary Header
                chan_dm = h0.get("CHAN_DM", None)
                if chan_dm is None:
                    chan_dm = h0.get("DM", None)

                # Look for DM in PSRPARAM table
                psrparam_dm = None
                for h in hdul:
                    if h.name.upper() == "PSRPARAM" and h.data is not None:
                        for card in h.data.field(0):
                            card_str = str(card).strip()
                            if card_str.startswith("DM "):
                                parts = card_str.split()
                                if len(parts) >= 2:
                                    psrparam_dm = parts[1]
                                break

                # Look for any search-mode DM trial table / DM-SNR curve
                has_dm_trials = False
                for h in hdul:
                    if any(t in h.name.upper() for t in ("DMTRIAL", "DMSNR", "DM_CURVE", "CANDIDATE")):
                        has_dm_trials = True
                        break

                dm_val = chan_dm if chan_dm is not None else psrparam_dm

                if dm_val is not None:
                    row["dm_available"] = "YES"
                    row["dm_value"] = f"{float(dm_val):.6f}"

                    if has_dm_trials:
                        row["dm_status"] = "DM_TRIAL_DATA_PRESENT"
                        row["notes"] = "Search-mode DM trials present."
                    else:
                        # Folded timing archives do not contain search-mode DM-SNR trials
                        row["dm_mean"] = "NOT_AVAILABLE"
                        row["dm_std"] = "NOT_AVAILABLE"
                        row["dm_skewness"] = "NOT_AVAILABLE"
                        row["dm_kurtosis"] = "NOT_AVAILABLE"
                        row["dm_status"] = "NOMINAL_DM_PRESENT_NO_TRIAL_CURVE"
                        row["notes"] = (
                            f"Nominal pulsar DM present in ephemeris (DM={row['dm_value']} pc/cm³). "
                            "Search-mode multi-trial DM-SNR curve is not contained in folded timing observations; "
                            "HTRU2 DM-SNR statistical moments cannot be derived from single-DM archives."
                        )
                else:
                    row["dm_available"] = "NO"
                    row["dm_status"] = "DM_INFORMATION_NOT_AVAILABLE"
                    row["notes"] = "No Dispersion Measure keywords found in header or ephemeris."

        except Exception as exc:
            row["dm_status"] = "ERROR"
            row["notes"] = f"DM inspection error: {exc}"

        records.append(row)
        print(f"[{row['dm_status']}] {row['file_name']} | DM={row['dm_value']} | DM-SNR Curve={row['dm_mean']}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print(f"\n[OK] DM analysis saved → {CSV_OUT}")
    print(f"Total processed files: {len(records)}\n")


if __name__ == "__main__":
    analyze_dispersion()
