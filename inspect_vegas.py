"""Inspect the VEGAS FITS files and the Parkes .sf file structure."""
from astropy.io import fits
import os, json
from pathlib import Path

PROJECT = Path(r"e:\ASTRA CLOUD")

def inspect_fits(fpath):
    result = {"file": str(fpath), "hdus": []}
    with fits.open(fpath, memmap=True, ignore_missing_simple=True) as hdul:
        for i, hdu in enumerate(hdul):
            hdu_info = {
                "index": i,
                "name": hdu.name,
                "type": type(hdu).__name__,
                "header_keys": {},
                "columns": [],
                "data_shape": None
            }
            if hasattr(hdu, 'header'):
                interesting_keys = [
                    'NAXIS', 'NAXIS1', 'NAXIS2', 'NAXIS3', 'NAXIS4',
                    'OBSFREQ', 'OBSBW', 'NCHAN', 'NPOL', 'NBIN',
                    'TSAMP', 'TSUBINT', 'TELESCOP', 'BACKEND',
                    'SRC_NAME', 'RA', 'DEC', 'STT_IMJD', 'FITSTYPE',
                    'BITPIX', 'SIMPLE', 'DATE-OBS', 'EQUINOX',
                    'OBS_MODE', 'HDRVER', 'INSTRUME', 'FREQ',
                    'IMJD', 'SMJD', 'RA_STR', 'DEC_STR'
                ]
                for k in interesting_keys:
                    if k in hdu.header:
                        try:
                            hdu_info["header_keys"][k] = str(hdu.header[k])
                        except Exception:
                            pass
            if hasattr(hdu, 'columns') and hdu.columns is not None:
                hdu_info["columns"] = [c.name for c in hdu.columns]
            if hasattr(hdu, 'data') and hdu.data is not None:
                try:
                    if hasattr(hdu.data, 'shape'):
                        hdu_info["data_shape"] = list(hdu.data.shape)
                except Exception:
                    pass
            result["hdus"].append(hdu_info)
    return result

# Inspect all radio_fits files (just first one in detail, others briefly)
radio_fits_dir = PROJECT / "data/radio_fits"
print("=== VEGAS FITS File Inspection ===")
files = sorted(radio_fits_dir.glob("*.fits"))
for fpath in files:
    print(f"\n--- {fpath.name} ---")
    try:
        info = inspect_fits(fpath)
        for hdu in info["hdus"]:
            print(f"  HDU {hdu['index']} ({hdu['name']}, {hdu['type']}):")
            for k, v in hdu['header_keys'].items():
                print(f"    {k}: {v}")
            if hdu['columns']:
                print(f"    Columns: {hdu['columns']}")
            if hdu['data_shape']:
                print(f"    Data shape: {hdu['data_shape']}")
    except Exception as e:
        print(f"  ERROR: {e}")
    # Only do first file in full detail
    break

# Quick scan remaining files for consistency
print("\n=== Quick scan of remaining VEGAS files ===")
for fpath in files[1:]:
    try:
        with fits.open(fpath, memmap=True, ignore_missing_simple=True) as hdul:
            nhdu = len(hdul)
            src = hdul[0].header.get('SRC_NAME', hdul[1].header.get('SRC_NAME', '?') if nhdu > 1 else '?')
            date_obs = hdul[0].header.get('DATE-OBS', '?')
            print(f"  {fpath.name}: {nhdu} HDUs, SRC={src}, DATE={date_obs}")
    except Exception as e:
        print(f"  {fpath.name}: ERROR {e}")
