# ============================================================
#  ASTRA Cloud -- FITS Type Detector
#  File   : ml/fits_type_detector.py
#  Purpose: Determine whether astronomical FITS files are:
#             1. OPTICAL_IMAGE
#             2. RADIO_DATA
#             3. UNKNOWN
#           Inspects headers (TELESCOP, INSTRUME, CTYPE, FREQ,
#           BAND, etc.) without modifying files or using ML.
#  Deps   : astropy, numpy
#  NOTE   : Read-only. Does NOT perform pulsar classification.
#           Does NOT connect to the ML model.
# ============================================================

import sys
import io
import csv
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.utils.exceptions import AstropyWarning

# UTF-8 output for clean printing on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Suppress benign astropy warnings (HIERARCH, VerifyWarning)
warnings.filterwarnings("ignore", category=AstropyWarning)

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent.parent
FITS_DIR    = REPO_ROOT / "data" / "fits"
REPORTS_DIR = REPO_ROOT / "reports"
CSV_OUT     = REPORTS_DIR / "fits_type_detection.csv"

# ------------------------------------------------------------------
# Known Reference Telescopes and Instruments
# ------------------------------------------------------------------
OPTICAL_TELESCOPES = {
    "HST", "HUBBLE", "JWST", "SPITZER", "KECK", "VLT", "SUBARU",
    "GEMINI", "SDSS", "PALOMAR", "PAN-STARRS", "GAIA", "CHANDRA",
    "XMM", "EUCLID", "RUBIN", "LSST", "CFHT", "NOT", "INT", "WHT",
    "LCOGT", "MAO", "KPNO", "CTIO", "ESO", "SOPHIE", "WISE"
}

OPTICAL_INSTRUMENTS = {
    "WFPC", "WFPC2", "WFC3", "ACS", "STIS", "NICMOS", "COS", "FOC",
    "NIRCAM", "MIRI", "NIRSPEC", "NIRISS", "MUSE", "FORS", "FORS1",
    "FORS2", "SPHERE", "HAWK-I", "VISIR", "DECAM", "MEGACAM", "HSC",
    "SUPRIMECAM", "EPIC", "GMOS", "UVES", "X-SHOOTER", "HARPS", "FLAMES"
}

RADIO_TELESCOPES = {
    "PARKES", "MURRIYANG", "ARECIBO", "FAST", "GMRT", "UGMRT",
    "VLA", "EVLA", "JVLA", "VLBA", "LOFAR", "MEERKAT", "ASKAP",
    "CHIME", "MWA", "EFFELSBERG", "JODRELL", "LOVELL", "GREEN BANK",
    "GBT", "NRAO", "OOTY", "ORT", "ALMA", "DRAO", "WSRT", "ATCA",
    "SKA", "UTR-2", "LWA", "NANCAY", "TORUN", "MEDICINA", "NOTO",
    "SARDINIA", "SRT", "TIANLAI"
}

RADIO_INSTRUMENTS_BACKENDS = {
    "PSRFITS", "BPSR", "DFB", "DFB1", "DFB2", "DFB3", "DFB4",
    "CASPSR", "APSR", "GUPPI", "PUPPI", "VEGAS", "ROACH", "CODD",
    "MEDUSA", "AFB", "WAPP", "PDEV", "UWBR", "MBRECEIV", "KST",
    "HSA", "MULTIBEAM", "MB20CM", "P20CM", "P70CM", "SCAMP"
}

CSV_FIELDS = [
    "filename",
    "detected_type",
    "confidence",
    "reason",
    "telescope",
    "instrument",
    "data_shape",
    "object_name",
    "date_obs",
]


# ------------------------------------------------------------------
# Header extraction helper
# ------------------------------------------------------------------
def _get_first(headers: list, *keys: str, default: str = "N/A") -> str:
    """Return the first non-empty value for any of *keys* across *headers*."""
    for hdr in headers:
        for k in keys:
            val = hdr.get(k, None)
            if val not in (None, "", " "):
                return str(val).strip()
    return default


# ------------------------------------------------------------------
# Core Classification Logic
# ------------------------------------------------------------------
def classify_fits_file(fits_path: Path) -> dict:
    """
    Inspect FITS headers and data structure to determine whether the file
    represents OPTICAL_IMAGE, RADIO_DATA, or UNKNOWN.
    """
    fname = fits_path.name

    try:
        with fits.open(fits_path, mode="readonly", memmap=True, ignore_missing_simple=True) as hdul:
            all_headers = [h.header for h in hdul]
            primary_hdr = hdul[0].header

            # Extract key header items
            telescope  = _get_first(all_headers, "TELESCOP")
            instrument = _get_first(all_headers, "INSTRUME")
            object_name = _get_first(all_headers, "OBJECT", "TARGNAME")
            date_obs   = _get_first(all_headers, "DATE-OBS", "DATE_OBS")

            # Coordinates / projections
            ctype1 = _get_first(all_headers, "CTYPE1")
            ctype2 = _get_first(all_headers, "CTYPE2")
            ctype3 = _get_first(all_headers, "CTYPE3")

            # Radio-specific keywords
            fitstype  = _get_first(all_headers, "FITSTYPE")
            obs_mode  = _get_first(all_headers, "OBS_MODE", "OBSMODE")
            freq      = _get_first(all_headers, "FREQ", "FREQUENCY", "OBSFREQ", "CENTFREQ")
            band      = _get_first(all_headers, "BAND", "BANDWIDTH", "CHAN_BW", "BW")
            backend   = _get_first(all_headers, "BACKEND")
            frontend  = _get_first(all_headers, "FRONTEND")

            # Check primary data dimensions
            primary_data = hdul[0].data
            if primary_data is not None and isinstance(primary_data, np.ndarray):
                data_shape = str(primary_data.shape)
                ndim = primary_data.ndim
            else:
                # Look for data in secondary HDUs if primary has none
                found_shape = "None"
                ndim = 0
                for hdu in hdul[1:]:
                    if hdu.data is not None and isinstance(hdu.data, np.ndarray):
                        found_shape = str(hdu.data.shape)
                        ndim = hdu.data.ndim
                        break
                data_shape = found_shape

    except Exception as exc:
        return {
            "filename": fname,
            "detected_type": "UNKNOWN",
            "confidence": "LOW",
            "reason": f"Failed to open/parse FITS file: {exc}",
            "telescope": "N/A",
            "instrument": "N/A",
            "data_shape": "None",
            "object_name": "N/A",
            "date_obs": "N/A",
        }

    # Normalize fields for matching
    tel_upper  = telescope.upper()
    inst_upper = instrument.upper()
    ctypes = f"{ctype1} {ctype2} {ctype3}".upper()
    fitstype_upper = fitstype.upper()
    obs_mode_upper = obs_mode.upper()
    backend_upper  = backend.upper()
    frontend_upper = frontend.upper()

    # Evidence lists
    radio_evidence = []
    optical_evidence = []

    # ── 1. Check for Radio Evidence ──────────────────────────────
    if any(rt in tel_upper for rt in RADIO_TELESCOPES):
        radio_evidence.append(f"Telescope is known radio facility ({telescope})")

    if any(ri in inst_upper or ri in backend_upper or ri in frontend_upper for ri in RADIO_INSTRUMENTS_BACKENDS):
        radio_evidence.append(f"Radio instrument/backend detected ({instrument if instrument != 'N/A' else backend})")

    if "PSRFITS" in fitstype_upper or "PSR" in fitstype_upper:
        radio_evidence.append(f"FITSTYPE={fitstype} indicates PSRFITS/pulsar format")

    if obs_mode_upper in ("SEARCH", "PSR", "CAL", "FOLD", "FASTSPEC", "SPECTRAL"):
        radio_evidence.append(f"Radio observation mode OBS_MODE={obs_mode}")

    if any(k in ctypes for k in ("FREQ", "CHANNEL", "FREQ-OBS")):
        radio_evidence.append(f"Radio coordinate axis present ({ctypes.strip()})")

    if freq != "N/A" and freq != "":
        radio_evidence.append(f"Radio observation frequency specified ({freq})")

    if band != "N/A" and band != "":
        radio_evidence.append(f"Radio bandwidth specified ({band})")

    # ── 2. Check for Optical Image Evidence ───────────────────────
    if any(ot in tel_upper for ot in OPTICAL_TELESCOPES):
        optical_evidence.append(f"Telescope is known optical/space observatory ({telescope})")

    if any(oi in inst_upper for oi in OPTICAL_INSTRUMENTS):
        optical_evidence.append(f"Instrument is known optical imaging system ({instrument})")

    # Tangent/Sine celestial projection typical of optical CCD imaging
    if any(proj in ctypes for proj in ("TAN", "SIN", "ARC", "STG")):
        optical_evidence.append(f"Optical sky projection coordinate ({ctypes.strip()})")

    # Multi-dimensional imaging array (2D or 3D image cube/chips)
    if ndim in (2, 3) and not any(k in ctypes for k in ("FREQ", "CHANNEL")):
        optical_evidence.append(f"Spatial image array ({data_shape})")

    # Filter / Exposure keywords typical of optical observations
    filter_val = _get_first(all_headers, "FILTER", "FILTER1", "FILTNAM1")
    if filter_val != "N/A":
        optical_evidence.append(f"Optical filter present ({filter_val})")

    # ── 3. Decision Rules & Confidence Assignment ────────────────
    # Radio data takes precedence only if meaningful radio indicators are present
    if radio_evidence:
        detected_type = "RADIO_DATA"
        # High confidence if radio telescope/backend or PSRFITS format verified
        if any(rt in tel_upper for rt in RADIO_TELESCOPES) or "PSRFITS" in fitstype_upper or any(ri in inst_upper for ri in RADIO_INSTRUMENTS_BACKENDS):
            confidence = "HIGH"
        elif len(radio_evidence) >= 2:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        reason = "; ".join(radio_evidence)

    elif optical_evidence:
        detected_type = "OPTICAL_IMAGE"
        # High confidence if known telescope or instrument matches
        if any(ot in tel_upper for ot in OPTICAL_TELESCOPES) or any(oi in inst_upper for oi in OPTICAL_INSTRUMENTS):
            confidence = "HIGH"
        elif any(proj in ctypes for proj in ("TAN", "SIN")) and ndim in (2, 3):
            confidence = "MEDIUM"
        elif len(optical_evidence) >= 2:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        reason = "; ".join(optical_evidence)

    else:
        detected_type = "UNKNOWN"
        confidence = "LOW"
        reason = "Insufficient optical or radio header markers found."

    return {
        "filename": fname,
        "detected_type": detected_type,
        "confidence": confidence,
        "reason": reason,
        "telescope": telescope,
        "instrument": instrument,
        "data_shape": data_shape,
        "object_name": object_name,
        "date_obs": date_obs,
    }


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
def main() -> None:
    print("=" * 68)
    print("  ASTRA Cloud  --  FITS Data Type Detector")
    print("=" * 68)

    fits_extensions = {".fits", ".fit", ".fts"}
    fits_files = sorted(
        p for p in FITS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in fits_extensions
    )

    if not fits_files:
        print(f"\n[WARN] No FITS files found in: {FITS_DIR}")
        return

    print(f"\nScanning {len(fits_files)} file(s) in: {FITS_DIR}\n")

    results: list[dict] = []

    for fp in fits_files:
        res = classify_fits_file(fp)
        results.append(res)

        print("-" * 68)
        print(f"Filename:      {res['filename']}")
        print(f"Detected type: {res['detected_type']}")
        print(f"Confidence:    {res['confidence']}")
        print(f"Reason:        {res['reason']}")
        print(f"Telescope:     {res['telescope']}")
        print(f"Instrument:    {res['instrument']}")
        print(f"Data shape:    {res['data_shape']}")
        print("-" * 68)
        print()

    # ── Save CSV ──────────────────────────────────────────────────
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "N/A") for k in CSV_FIELDS})

    print("=" * 68)
    print(f"  Classification report saved  →  {CSV_OUT}")
    print(f"  Files classified             :  {len(results)}")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    main()
