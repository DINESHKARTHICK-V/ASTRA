# ============================================================
#  ASTRA Cloud -- Real Radio FITS Inventory & Validation
#  File   : ml/radio_fits_inventory.py
#  Purpose: Scan data/radio_fits/, inspect every FITS file using
#           Astropy, verify PSRFITS / radio headers and binary
#           tables, compute data dimensions and statistics,
#           and output reports/radio_fits_inventory.csv.
#  Deps   : astropy, numpy
#  NOTE   : Read-only -- does not modify any FITS file.
# ============================================================

import sys
import io
import csv
import math
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.utils.exceptions import AstropyWarning

# UTF-8 output for Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

warnings.filterwarnings("ignore", category=AstropyWarning)

REPO_ROOT   = Path(__file__).resolve().parent.parent
RADIO_DIR   = REPO_ROOT / "data" / "radio_fits"
REPORTS_DIR = REPO_ROOT / "reports"
CSV_OUT     = REPORTS_DIR / "radio_fits_inventory.csv"

# Known Radio Telescopes and Instruments
RADIO_TELESCOPES = {
    "GBT", "GREEN BANK", "PARKES", "MURRIYANG", "ARECIBO", "FAST",
    "GMRT", "UGMRT", "VLA", "EVLA", "JVLA", "VLBA", "LOFAR",
    "MEERKAT", "ASKAP", "CHIME", "MWA", "EFFELSBERG", "JODRELL",
    "LOVELL", "OOTY", "ALMA", "ATCA", "WSRT", "DRAO"
}

OPTICAL_TELESCOPES = {
    "HST", "HUBBLE", "JWST", "SPITZER", "KECK", "VLT", "SUBARU",
    "GEMINI", "SDSS", "PALOMAR", "GAIA", "CHANDRA", "XMM", "EUCLID"
}

CSV_FIELDS = [
    "file_name",
    "file_size_mb",
    "hdu_count",
    "hdu_types",
    "telescope",
    "instrument",
    "target",
    "date_obs",
    "frequency",
    "bandwidth",
    "nchan",
    "nsubint",
    "nbin",
    "data_shape",
    "dtype",
    "nan_count",
    "inf_count",
    "validation_status",
    "reason",
]


def _get_first(headers: list, *keys: str, default: str = "N/A") -> str:
    """Return the first non-empty value for any of *keys* across *headers*."""
    for hdr in headers:
        for k in keys:
            val = hdr.get(k, None)
            if val not in (None, "", " "):
                return str(val).strip()
    return default


def inspect_radio_file(file_path: Path) -> dict:
    """
    Open and inspect a single radio / pulsar FITS file.
    Returns a dictionary matching CSV_FIELDS.
    """
    fname = file_path.name
    size_mb = round(file_path.stat().st_size / (1024 * 1024), 3)

    row = {k: "N/A" for k in CSV_FIELDS}
    row["file_name"] = fname
    row["file_size_mb"] = str(size_mb)

    sep = "-" * 68

    print(f"\n{'=' * 68}")
    print(f"  FILE : {fname} ({size_mb} MB)")
    print(f"{'=' * 68}")

    # 1. Open safely
    try:
        hdul = fits.open(file_path, mode="readonly", memmap=True, ignore_missing_simple=True)
    except Exception as exc:
        row["validation_status"] = "INVALID_FITS"
        row["reason"] = f"Failed to open with Astropy: {exc}"
        print(f"  [ERROR] Cannot open file: {exc}")
        return row

    try:
        # 2. HDU count and structure
        hdu_count = len(hdul)
        row["hdu_count"] = str(hdu_count)

        hdu_type_list = [f"{i}:{type(h).__name__}[{h.name}]" for i, h in enumerate(hdul)]
        row["hdu_types"] = "; ".join(hdu_type_list)

        print(f"  HDU Count   : {hdu_count}")
        print("  HDU Table   :")
        for idx, hdu in enumerate(hdul):
            dshape = "None"
            if hdu.data is not None:
                if hasattr(hdu.data, "shape"):
                    dshape = str(hdu.data.shape)
                elif hasattr(hdu, "columns"):
                    dshape = f"{len(hdu.data)} rows x {len(hdu.columns)} cols"
            print(f"    [{idx}] {hdu.name:<12} {type(hdu).__name__:<16} Cards: {len(hdu.header):<4} Shape: {dshape}")

        all_headers = [h.header for h in hdul]
        primary_hdr = hdul[0].header

        # 3. Read important header metadata
        telescope   = _get_first(all_headers, "TELESCOP")
        instrument  = _get_first(all_headers, "INSTRUME", "BACKEND")
        target      = _get_first(all_headers, "SRC_NAME", "OBJECT", "TARGNAME")
        date_obs    = _get_first(all_headers, "DATE-OBS", "DATE_OBS")
        fitstype    = _get_first(all_headers, "FITSTYPE")
        obs_mode    = _get_first(all_headers, "OBS_MODE", "OBSMODE")
        freq        = _get_first(all_headers, "OBSFREQ", "FREQ", "CENTFREQ")
        bandwidth   = _get_first(all_headers, "OBSBW", "BANDWIDTH", "BW", "CHAN_BW")

        # Specific backend fallback for GBT VEGAS
        if instrument == "N/A" and "VEGAS" in fname.upper():
            instrument = "VEGAS"

        row["telescope"]  = telescope
        row["instrument"] = instrument
        row["target"]     = target
        row["date_obs"]   = date_obs
        row["frequency"]  = freq
        row["bandwidth"]  = bandwidth

        # 4. Check for SUBINT or Data HDU
        subint_hdu = None
        for h in hdul:
            if h.name.upper() == "SUBINT":
                subint_hdu = h
                break

        nchan   = "N/A"
        nsubint = "N/A"
        nbin    = "N/A"
        data_shape = "None"
        dtype_str  = "None"
        nan_count  = 0
        inf_count  = 0

        if subint_hdu is not None and subint_hdu.data is not None:
            shdr = subint_hdu.header
            nchan   = str(shdr.get("NCHAN", "N/A"))
            nbin    = str(shdr.get("NBIN", "N/A"))
            nsubint = str(shdr.get("NSUBINT", len(subint_hdu.data)))

            row["nchan"]   = nchan
            row["nsubint"] = nsubint
            row["nbin"]    = nbin

            # Check DATA column in SUBINT
            if "DATA" in subint_hdu.columns.names:
                data_col = subint_hdu.data["DATA"]
                data_shape = str(data_col.shape)
                dtype_str  = str(data_col.dtype)

                if np.issubdtype(data_col.dtype, np.floating):
                    nan_count = int(np.isnan(data_col).sum())
                    inf_count = int(np.isinf(data_col).sum())
                else:
                    nan_count = 0
                    inf_count = 0
        elif hdul[0].data is not None and isinstance(hdul[0].data, np.ndarray):
            # Fallback for primary image-like radio data
            pdata = hdul[0].data
            data_shape = str(pdata.shape)
            dtype_str  = str(pdata.dtype)
            if np.issubdtype(pdata.dtype, np.floating):
                nan_count = int(np.isnan(pdata).sum())
                inf_count = int(np.isinf(pdata).sum())

        row["data_shape"] = data_shape
        row["dtype"]      = dtype_str
        row["nan_count"]  = str(nan_count)
        row["inf_count"]  = str(inf_count)

        # 5. Validation status & classification logic
        tel_upper = telescope.upper()
        fitstype_upper = fitstype.upper()

        if any(ot in tel_upper for ot in OPTICAL_TELESCOPES):
            row["validation_status"] = "OPTICAL"
            row["reason"] = f"Header telescope ({telescope}) identifies as optical/space observatory."
        elif "PSRFITS" in fitstype_upper or subint_hdu is not None:
            row["validation_status"] = "VALID_PSRFITS"
            row["reason"] = (
                f"Verified PSRFITS format (FITSTYPE={fitstype}, SUBINT table present, "
                f"Telescope={telescope}, Target={target}, Freq={freq} MHz, BW={bandwidth} MHz, "
                f"NCHAN={nchan}, NBIN={nbin})."
            )
        elif any(rt in tel_upper for rt in RADIO_TELESCOPES) or freq != "N/A":
            row["validation_status"] = "VALID_RADIO"
            row["reason"] = f"Radio telescope/frequency verified ({telescope}, Freq={freq} MHz)."
        else:
            row["validation_status"] = "UNKNOWN"
            row["reason"] = "Insufficient radio or PSRFITS indicators."

        # Print detailed inspection report
        print(f"\n  Telescope       : {row['telescope']}")
        print(f"  Instrument      : {row['instrument']}")
        print(f"  Target / Source : {row['target']}")
        print(f"  Observation Date: {row['date_obs']}")
        print(f"  Frequency (MHz) : {row['frequency']}")
        print(f"  Bandwidth (MHz) : {row['bandwidth']}")
        print(f"  NCHAN / NBIN    : Channels={row['nchan']}, Bins={row['nbin']}, Subints={row['nsubint']}")
        print(f"  Data Shape      : {row['data_shape']}")
        print(f"  Data Type       : {row['dtype']}")
        print(f"  NaN / Inf Count : NaNs={row['nan_count']}, Infs={row['inf_count']}")
        print(f"  Status          : {row['validation_status']}")
        print(f"  Reason          : {row['reason']}")

    finally:
        hdul.close()

    return row


def run_inventory() -> list[dict]:
    print("=" * 68)
    print("  ASTRA Cloud -- Real Radio FITS Inventory & Validation")
    print("=" * 68)

    fits_files = sorted(
        p for p in RADIO_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".fits", ".fit", ".fts"}
    )

    if not fits_files:
        print(f"\n[WARN] No FITS files found in {RADIO_DIR}")
        return []

    print(f"\nDiscovered {len(fits_files)} file(s) in: {RADIO_DIR}")

    rows = []
    for fp in fits_files:
        r = inspect_radio_file(fp)
        rows.append(r)

    # Save to CSV
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "N/A") for k in CSV_FIELDS})

    print(f"\n{'=' * 68}")
    print(f"  Inventory report saved  →  {CSV_OUT}")
    print(f"  Total files processed   :  {len(rows)}")
    print(f"{'=' * 68}\n")

    return rows


if __name__ == "__main__":
    run_inventory()
