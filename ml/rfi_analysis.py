# ============================================================
#  ASTRA Cloud -- Step 15: Radio Frequency Interference (RFI) Analysis
#  File   : ml/rfi_analysis.py
#  Purpose: Inspect frequency channels and phase/time samples
#           to calculate transparent, non-binary RFI indicators
#           based on observatory weights and spectral outliers.
#  Output : reports/rfi_analysis.csv
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
CSV_OUT     = REPORTS_DIR / "rfi_analysis.csv"

FIELDS = [
    "file_name",
    "rfi_analysis_possible",
    "affected_channel_count",
    "affected_time_region_count",
    "rfi_indicator",
    "notes",
]


def analyze_rfi() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 15: RFI Analysis")
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
                    row["rfi_analysis_possible"] = "NO"
                    row["affected_channel_count"] = "NOT_AVAILABLE"
                    row["affected_time_region_count"] = "NOT_AVAILABLE"
                    row["rfi_indicator"] = "NOT_AVAILABLE"
                    row["notes"] = "Insufficient channel/frequency data for RFI analysis (no SUBINT table)."
                    records.append(row)
                    continue

                d = subint.data
                raw = d["DATA"][0]

                if np.all(raw == 0):
                    row["rfi_analysis_possible"] = "YES"
                    row["affected_channel_count"] = "0"
                    row["affected_time_region_count"] = "0"
                    row["rfi_indicator"] = "0.0000"
                    row["notes"] = "Blank observation frame; no active signal or RFI detected."
                    records.append(row)
                    continue

                row["rfi_analysis_possible"] = "YES"

                # Check observatory channel weights (DAT_WTS)
                nchan = raw.shape[1]  # 128 channels
                flagged_by_weights = 0
                weights = None
                if "DAT_WTS" in subint.columns.names:
                    weights = d["DAT_WTS"][0]
                    flagged_by_weights = int(np.sum(weights == 0.0))

                # Compute mean channel power across Stokes I (pol 0 + pol 1)
                stokes_i = raw[0].astype(np.float64) + raw[1].astype(np.float64)
                chan_power = np.mean(stokes_i, axis=1)  # shape: (128,)

                # Detect spectral outliers (> 3 * MAD from median of non-zero channels)
                valid_mask = np.ones(nchan, dtype=bool)
                if weights is not None:
                    valid_mask = weights > 0

                outlier_channels = 0
                if np.any(valid_mask):
                    valid_powers = chan_power[valid_mask]
                    med_p = np.median(valid_powers)
                    mad_p = np.median(np.abs(valid_powers - med_p))
                    threshold = med_p + 3.5 * (1.4826 * mad_p)
                    outliers = valid_powers > threshold
                    outlier_channels = int(np.sum(outliers))

                total_affected_channels = flagged_by_weights + outlier_channels
                rfi_fraction = total_affected_channels / nchan if nchan > 0 else 0.0

                # Temporal / phase stability check: search for abnormal non-periodic spikes in off-pulse region
                # Pulse in J1713+0747 is around phase 0.95 (bin ~1950)
                # Off-pulse bins: 0 to 1500
                off_pulse = stokes_i[:, :1500]
                off_mean = np.mean(off_pulse, axis=0)
                med_t = np.median(off_mean)
                mad_t = np.median(np.abs(off_mean - med_t))
                sigma_t = 1.4826 * mad_t if mad_t > 0 else 1.0
                time_spikes = int(np.sum(np.abs(off_mean - med_t) > 4.5 * sigma_t))

                row["affected_channel_count"] = str(total_affected_channels)
                row["affected_time_region_count"] = str(time_spikes)
                row["rfi_indicator"] = f"{rfi_fraction:.4f}"
                row["notes"] = (
                    f"RFI indicator derived from {flagged_by_weights} zero-weighted band/RFI channels "
                    f"and {outlier_channels} statistical spectral outlier channels out of {nchan} total channels."
                )

        except Exception as exc:
            row["rfi_analysis_possible"] = "ERROR"
            row["notes"] = f"RFI screening error: {exc}"

        records.append(row)
        print(f"[{row['rfi_analysis_possible']}] {row['file_name']} | AffectedChans={row['affected_channel_count']} | RFI_Indicator={row['rfi_indicator']}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print(f"\n[OK] RFI analysis report saved → {CSV_OUT}")
    print(f"Total processed files: {len(records)}\n")


if __name__ == "__main__":
    analyze_rfi()
