# ============================================================
#  ASTRA Cloud -- Step 11: Extract Radio FITS Metadata
#  File   : ml/extract_radio_metadata.py
#  Purpose: Extract standardized metadata fields from valid
#           radio/pulsar FITS files in data/radio_fits/.
#  Output : reports/radio_fits_metadata.csv
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
CSV_OUT     = REPORTS_DIR / "radio_fits_metadata.csv"

FIELDS = [
    "file_name",
    "source",
    "telescope",
    "instrument",
    "target",
    "date_obs",
    "time_obs",
    "frequency",
    "bandwidth",
    "nchan",
    "nsubint",
    "nbin",
    "observation_mode",
    "data_mode",
    "polarization_information",
    "file_size_mb",
]


def extract_metadata() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 11: Extract Radio FITS Metadata")
    print("=" * 68)

    fits_files = sorted(RADIO_DIR.glob("*.fits"))
    if not fits_files:
        print(f"[WARN] No files found in {RADIO_DIR}")
        return

    records = []

    for fp in fits_files:
        size_mb = round(fp.stat().st_size / (1024 * 1024), 3)
        row = {k: "NOT_AVAILABLE" for k in FIELDS}
        row["file_name"] = fp.name
        row["file_size_mb"] = str(size_mb)
        row["source"] = "Zenodo (Jennings et al. 2022 / NANOGrav)"

        try:
            with fits.open(fp, mode="readonly", memmap=True) as hdul:
                h0 = hdul[0].header

                telescope  = h0.get("TELESCOP", "NOT_AVAILABLE")
                instrument = h0.get("INSTRUME", None)
                if instrument in (None, "", " ") and "VEGAS" in fp.name.upper():
                    instrument = "VEGAS"
                elif instrument is None:
                    instrument = "NOT_AVAILABLE"

                target   = h0.get("SRC_NAME", h0.get("OBJECT", "NOT_AVAILABLE"))
                date_obs_full = h0.get("DATE-OBS", "NOT_AVAILABLE")

                if date_obs_full != "NOT_AVAILABLE" and "T" in str(date_obs_full):
                    date_part, time_part = str(date_obs_full).split("T", 1)
                    date_obs = date_part
                    time_obs = time_part
                else:
                    date_obs = date_obs_full
                    time_obs = "NOT_AVAILABLE"

                freq = h0.get("OBSFREQ", "NOT_AVAILABLE")
                bw   = h0.get("OBSBW", "NOT_AVAILABLE")
                obs_mode = h0.get("OBS_MODE", "NOT_AVAILABLE")
                data_mode = "fold-mode" if obs_mode == "PSR" else obs_mode

                row["telescope"] = str(telescope)
                row["instrument"] = str(instrument)
                row["target"] = str(target)
                row["date_obs"] = str(date_obs)
                row["time_obs"] = str(time_obs)
                row["frequency"] = str(freq)
                row["bandwidth"] = str(bw)
                row["observation_mode"] = str(obs_mode)
                row["data_mode"] = str(data_mode)

                # SUBINT HDU
                subint = None
                for h in hdul:
                    if h.name.upper() == "SUBINT":
                        subint = h
                        break

                if subint is not None:
                    shdr = subint.header
                    row["nchan"]   = str(shdr.get("NCHAN", "NOT_AVAILABLE"))
                    row["nbin"]    = str(shdr.get("NBIN", "NOT_AVAILABLE"))
                    row["nsubint"] = str(shdr.get("NSUBINT", len(subint.data)))
                    pol_type = shdr.get("POL_TYPE", "NOT_AVAILABLE")
                    npol     = shdr.get("NPOL", "NOT_AVAILABLE")
                    row["polarization_information"] = f"NPOL={npol}, POL_TYPE={pol_type}"

        except Exception as e:
            row["notes"] = f"Extraction error: {e}"

        records.append(row)
        print(f"[EXTRACTED] {row['file_name']} | Target={row['target']} | Freq={row['frequency']} MHz | Pol={row['polarization_information']}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print(f"\n[OK] Metadata table saved → {CSV_OUT}")
    print(f"Total processed files: {len(records)}\n")


if __name__ == "__main__":
    extract_metadata()
