# ============================================================
#  ASTRA Cloud -- Step 9: Validate All Radio FITS Files
#  File   : ml/validate_radio_fits.py
#  Purpose: Rigorous validation of all files in data/radio_fits/
#           Extracts HDUs, data shapes, dtypes, NaNs/Infs,
#           and observational metadata without crashing on missing keys.
#  Output : reports/radio_fits_validation.csv
# ============================================================

import sys
import io
import csv
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.utils.exceptions import AstropyWarning

# UTF-8 output formatting
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

warnings.filterwarnings("ignore", category=AstropyWarning)

REPO_ROOT   = Path(__file__).resolve().parent.parent
RADIO_DIR   = REPO_ROOT / "data" / "radio_fits"
REPORTS_DIR = REPO_ROOT / "reports"
CSV_OUT     = REPORTS_DIR / "radio_fits_validation.csv"

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
    "valid_fits",
    "hdu_count",
    "hdu_summary",
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
    "notes",
]


def _get_val(headers: list, *keys: str, default: str = "NOT_AVAILABLE") -> str:
    """Safely retrieve first non-empty header value."""
    for hdr in headers:
        for k in keys:
            val = hdr.get(k, None)
            if val not in (None, "", " "):
                return str(val).strip()
    return default


def validate_file(file_path: Path) -> dict:
    fname = file_path.name
    row = {k: "NOT_AVAILABLE" for k in CSV_FIELDS}
    row["file_name"] = fname

    # 1. Open using Astropy
    try:
        hdul = fits.open(file_path, mode="readonly", memmap=True, ignore_missing_simple=True)
        row["valid_fits"] = "YES"
    except Exception as exc:
        row["valid_fits"] = "NO"
        row["validation_status"] = "INVALID_FITS"
        row["notes"] = f"Failed to open FITS file: {exc}"
        return row

    try:
        # 2. HDU count and summary
        hdu_count = len(hdul)
        row["hdu_count"] = str(hdu_count)

        hdu_summaries = []
        for i, hdu in enumerate(hdul):
            hname = hdu.name if hdu.name else "PRIMARY"
            htype = type(hdu).__name__
            hdu_summaries.append(f"{i}:{htype}[{hname}]")
        row["hdu_summary"] = "; ".join(hdu_summaries)

        all_headers = [h.header for h in hdul]

        # 3. Read important header keywords
        telescope  = _get_val(all_headers, "TELESCOP")
        instrument = _get_val(all_headers, "INSTRUME", "BACKEND")
        target     = _get_val(all_headers, "SRC_NAME", "OBJECT", "TARGNAME")
        date_obs   = _get_val(all_headers, "DATE-OBS", "DATE_OBS")
        frequency  = _get_val(all_headers, "OBSFREQ", "FREQ", "CENTFREQ")
        bandwidth  = _get_val(all_headers, "OBSBW", "BANDWIDTH", "BW")
        fitstype   = _get_val(all_headers, "FITSTYPE")

        # Specific fallback for GBT VEGAS files
        if instrument == "NOT_AVAILABLE" and "VEGAS" in fname.upper():
            instrument = "VEGAS"

        row["telescope"]  = telescope
        row["instrument"] = instrument
        row["target"]     = target
        row["date_obs"]   = date_obs
        row["frequency"]  = frequency
        row["bandwidth"]  = bandwidth

        # 4. Check for SUBINT HDU or Primary Data
        subint_hdu = None
        for h in hdul:
            if h.name.upper() == "SUBINT":
                subint_hdu = h
                break

        nchan   = "NOT_AVAILABLE"
        nsubint = "NOT_AVAILABLE"
        nbin    = "NOT_AVAILABLE"
        data_shape = "NOT_AVAILABLE"
        dtype_str  = "NOT_AVAILABLE"
        nan_count  = 0
        inf_count  = 0

        if subint_hdu is not None and subint_hdu.data is not None:
            shdr = subint_hdu.header
            nchan_val = shdr.get("NCHAN", None)
            nbin_val  = shdr.get("NBIN", None)
            nsub_val  = shdr.get("NSUBINT", len(subint_hdu.data))

            if nchan_val is not None:
                nchan = str(nchan_val)
            if nbin_val is not None:
                nbin = str(nbin_val)
            if nsub_val is not None:
                nsubint = str(nsub_val)

            row["nchan"]   = nchan
            row["nsubint"] = nsubint
            row["nbin"]    = nbin

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
            row["notes"] = f"Identified as optical telescope ({telescope})."
        elif "PSRFITS" in fitstype_upper or subint_hdu is not None:
            row["validation_status"] = "VALID_PSRFITS"
            row["notes"] = (
                f"PSRFITS standard verified (FITSTYPE={fitstype}, SUBINT table present, "
                f"Target={target}, Freq={frequency} MHz, BW={bandwidth} MHz)."
            )
        elif any(rt in tel_upper for rt in RADIO_TELESCOPES) or frequency != "NOT_AVAILABLE":
            row["validation_status"] = "VALID_RADIO"
            row["notes"] = f"Radio telescope/frequency confirmed ({telescope})."
        else:
            row["validation_status"] = "UNKNOWN"
            row["notes"] = "Insufficient radio indicators."

    finally:
        hdul.close()

    return row


def main() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 9: Validate All Radio FITS Files")
    print("=" * 68)

    fits_files = sorted(
        p for p in RADIO_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".fits", ".fit", ".fts"}
    )

    if not fits_files:
        print(f"[WARN] No FITS files found in {RADIO_DIR}")
        return

    print(f"Scanning {len(fits_files)} file(s) in: {RADIO_DIR}\n")

    results = []
    for fp in fits_files:
        r = validate_file(fp)
        results.append(r)
        print(f"[{r['validation_status']}] {r['file_name']} | Target={r['target']} | Freq={r['frequency']} MHz | Shape={r['data_shape']}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[OK] Validation report saved → {CSV_OUT}")
    print(f"Total validated files: {len(results)}\n")


if __name__ == "__main__":
    main()
