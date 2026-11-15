# ml/fits_inspector.py
# ASTRA Cloud — FITS File Inspector
#
# Purpose  : Inspect and visualize astronomical FITS files before connecting
#            them to the ML model.
# Scans    : data/fits/   (*.fits, *.fit, *.fits.gz)
# Outputs  : console report + preview images in reports/fits_preview/
#
# NOTE: This script does NOT modify any FITS file.
#       It does NOT classify files as pulsar/radio data.
#       FITS is a general-purpose data format used across all of astronomy.
#       Do NOT connect this script to the ML model.

import os
import sys
import glob
import traceback

import numpy as np
import matplotlib
matplotlib.use("Agg")          # non-interactive backend — safe on all platforms
import matplotlib.pyplot as plt

try:
    from astropy.io import fits
except ImportError:
    sys.exit(
        "\n[fits_inspector] ERROR: astropy is not installed.\n"
        "Install it with:  pip install astropy\n"
    )

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR     = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FITS_DIR     = os.path.join(ROOT_DIR, "data", "fits")
PREVIEW_DIR  = os.path.join(ROOT_DIR, "reports", "fits_preview")

# Header keywords to extract when available
USEFUL_KEYS = [
    "OBJECT", "DATE-OBS", "TELESCOP", "INSTRUME",
    "RA", "DEC", "FILTER", "FREQUENCY", "BAND",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _separator(char="─", width=68):
    print(char * width)


def _find_fits_files(directory: str) -> list[str]:
    """Return sorted list of *.fits / *.fit / *.fits.gz in `directory`."""
    patterns = ["*.fits", "*.fit", "*.fits.gz"]
    found = []
    for pat in patterns:
        found.extend(glob.glob(os.path.join(directory, pat)))
        # also search one level deep
        found.extend(glob.glob(os.path.join(directory, "**", pat),
                               recursive=True))
    # deduplicate and sort
    return sorted(set(found))


def _classify_hdu(hdu) -> str:
    """Return a human-readable classification for one HDU."""
    if isinstance(hdu, (fits.BinTableHDU, fits.TableHDU)):
        return "table-like data"
    if hdu.data is None:
        return "no data"
    if isinstance(hdu, fits.ImageHDU) or isinstance(hdu, fits.PrimaryHDU):
        ndim = hdu.data.ndim
        if ndim == 1:
            return "image-like data (1D)"
        if ndim == 2:
            return "image-like data (2D)"
        return f"image-like data ({ndim}D)"
    return "other data"


def _data_stats(data: np.ndarray) -> dict:
    """Compute min, max, NaN count, Inf count for a numeric array."""
    flat = data.astype(float).ravel()
    return {
        "min":       float(np.nanmin(flat))  if flat.size else None,
        "max":       float(np.nanmax(flat))  if flat.size else None,
        "nan_count": int(np.isnan(flat).sum()),
        "inf_count": int(np.isinf(flat).sum()),
    }


# ── Visualization ─────────────────────────────────────────────────────────────

def _save_preview(data: np.ndarray, title: str, save_path: str) -> None:
    """
    Save a preview image for a numeric data array.
      1D → line plot
      2D → imshow
      3D+ → representative 2D slice (middle index of axis 0)
    """
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("#0f0f1a")
    ax.set_facecolor("#0f0f1a")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")

    try:
        if data.ndim == 1:
            ax.plot(data, linewidth=0.8, color="#4fc3f7")
            ax.set_xlabel("Sample index", color="white")
            ax.set_ylabel("Value", color="white")
            ax.set_title(title + "  [1D]", color="white", fontsize=10)

        elif data.ndim == 2:
            vmin = np.nanpercentile(data, 2)
            vmax = np.nanpercentile(data, 98)
            im = ax.imshow(data, aspect="auto", origin="lower",
                           vmin=vmin, vmax=vmax, cmap="inferno")
            cbar = fig.colorbar(im, ax=ax)
            cbar.ax.yaxis.set_tick_params(color="white")
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
            ax.set_xlabel("Axis 1", color="white")
            ax.set_ylabel("Axis 0", color="white")
            ax.set_title(title + "  [2D]", color="white", fontsize=10)

        else:
            # 3D+: take middle slice along axis 0
            mid = data.shape[0] // 2
            slice_2d = data[mid]
            # flatten to 2D if still > 2D
            if slice_2d.ndim > 2:
                slice_2d = slice_2d.reshape(slice_2d.shape[0], -1)
            vmin = np.nanpercentile(slice_2d, 2)
            vmax = np.nanpercentile(slice_2d, 98)
            im = ax.imshow(slice_2d, aspect="auto", origin="lower",
                           vmin=vmin, vmax=vmax, cmap="inferno")
            cbar = fig.colorbar(im, ax=ax)
            cbar.ax.yaxis.set_tick_params(color="white")
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
            ax.set_title(
                title + f"  [{data.ndim}D — slice {mid} of axis 0]",
                color="white", fontsize=10,
            )

    except Exception as e:
        ax.text(0.5, 0.5, f"Preview failed:\n{e}",
                ha="center", va="center", color="red",
                transform=ax.transAxes, fontsize=9)

    fig.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)


# ── Per-file inspection ───────────────────────────────────────────────────────

def inspect_file(filepath: str) -> dict:
    """
    Inspect one FITS file.

    Returns a summary dict:
        file, num_hdus, hdus[], header_meta, previews_saved, errors, classification
    """
    filename = os.path.basename(filepath)
    result = {
        "file":          filename,
        "filepath":      filepath,
        "num_hdus":      0,
        "hdus":          [],
        "header_meta":   {},
        "previews_saved":[],
        "errors":        [],
        "classification": [],
    }

    _separator("═")
    print(f"  FILE : {filename}")
    print(f"  PATH : {filepath}")
    _separator("═")

    try:
        with fits.open(filepath, memmap=True, ignore_missing_simple=True) as hdul:

            result["num_hdus"] = len(hdul)
            print(f"  Number of HDUs : {len(hdul)}\n")

            # ── Extract useful header keys from PRIMARY HDU ──────────────────
            primary_header = hdul[0].header
            meta = {}
            for key in USEFUL_KEYS:
                val = primary_header.get(key, None)
                if val is not None:
                    meta[key] = val
            result["header_meta"] = meta

            if meta:
                print("  ── Useful Header Keywords ──────────────────────────────")
                for k, v in meta.items():
                    print(f"    {k:<12}: {v}")
                print()
            else:
                print("  ── Useful Header Keywords ──────────────────────────────")
                print("    (none of the target keywords found in PRIMARY header)")
                print()

            # ── Inspect each HDU ─────────────────────────────────────────────
            for idx, hdu in enumerate(hdul):
                hdu_info = {
                    "index":          idx,
                    "name":           hdu.name,
                    "type":           type(hdu).__name__,
                    "naxis":          hdu.header.get("NAXIS", None),
                    "dimensions":     None,
                    "data_type":      None,
                    "data_shape":     None,
                    "min":            None,
                    "max":            None,
                    "nan_count":      None,
                    "inf_count":      None,
                    "classification": _classify_hdu(hdu),
                }

                print(f"  ── HDU {idx}  [{hdu.name}]  ({type(hdu).__name__}) ──────────────")

                # NAXIS / dimensions from header
                naxis = hdu.header.get("NAXIS", 0)
                dims  = [hdu.header.get(f"NAXIS{i}", "?") for i in range(1, naxis + 1)]
                hdu_info["naxis"]      = naxis
                hdu_info["dimensions"] = dims
                print(f"    NAXIS      : {naxis}")
                print(f"    Dimensions : {dims if dims else 'N/A'}")

                # ── Image / Primary HDU ──────────────────────────────────────
                if isinstance(hdu, (fits.PrimaryHDU, fits.ImageHDU)):
                    if hdu.data is not None:
                        data = hdu.data
                        hdu_info["data_type"]  = str(data.dtype)
                        hdu_info["data_shape"] = list(data.shape)
                        print(f"    Data type  : {data.dtype}")
                        print(f"    Data shape : {data.shape}")

                        try:
                            stats = _data_stats(data)
                            hdu_info.update(stats)
                            print(f"    Min value  : {stats['min']}")
                            print(f"    Max value  : {stats['max']}")
                            print(f"    NaN count  : {stats['nan_count']}")
                            print(f"    Inf count  : {stats['inf_count']}")
                        except Exception as e:
                            print(f"    WARNING: Could not compute stats — {e}")

                        # Preview
                        try:
                            stem = os.path.splitext(
                                os.path.splitext(filename)[0])[0]
                            preview_name = f"{stem}_hdu{idx}.png"
                            preview_path = os.path.join(PREVIEW_DIR, preview_name)
                            title = f"{filename}  HDU {idx}"
                            _save_preview(
                                data.astype(float) if data.dtype.kind not in ("c",) else np.abs(data),
                                title, preview_path,
                            )
                            result["previews_saved"].append(preview_path)
                            print(f"    Preview    : reports/fits_preview/{preview_name}")
                        except Exception as e:
                            print(f"    WARNING: Preview failed — {e}")
                    else:
                        print("    Data       : (empty / no data array)")

                # ── Table HDU ────────────────────────────────────────────────
                elif isinstance(hdu, (fits.BinTableHDU, fits.TableHDU)):
                    cols  = hdu.columns.names if hdu.columns else []
                    nrows = hdu.header.get("NAXIS2", "?")
                    print(f"    Data type  : Table ({type(hdu).__name__})")
                    print(f"    Rows       : {nrows}")
                    print(f"    Columns    : {len(cols)}  →  {cols}")
                    hdu_info["data_type"]  = "table"
                    hdu_info["data_shape"] = [nrows, len(cols)]

                # ── Unknown / empty ──────────────────────────────────────────
                else:
                    print(f"    Data       : {hdu.data!r}")

                print(f"    Content    : {hdu_info['classification']}")
                print()

                result["hdus"].append(hdu_info)
                result["classification"].append(hdu_info["classification"])

    except Exception as e:
        msg = f"Failed to open {filename}: {e}"
        result["errors"].append(msg)
        print(f"  ERROR: {msg}")
        traceback.print_exc()

    return result


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(reports: list[dict]) -> None:
    """Print a compact summary table of all inspected files."""
    _separator("═")
    print("  INSPECTION SUMMARY")
    _separator("═")
    print(f"  {'#':<4}  {'File':<35}  {'HDUs':<6}  {'Content types'}")
    _separator()
    for i, r in enumerate(reports, 1):
        types = ", ".join(sorted(set(r["classification"]))) or "—"
        errors = "  !! ERROR" if r["errors"] else ""
        print(f"  {i:<4}  {r['file']:<35}  {r['num_hdus']:<6}  {types}{errors}")
    _separator()
    print(f"\n  Total files inspected : {len(reports)}")
    total_previews = sum(len(r["previews_saved"]) for r in reports)
    print(f"  Total previews saved  : {total_previews}")
    if total_previews:
        print(f"  Preview directory     : {PREVIEW_DIR}")
    total_errors = sum(len(r["errors"]) for r in reports)
    if total_errors:
        print(f"\n  FILES WITH ERRORS ({total_errors}):")
        for r in reports:
            for e in r["errors"]:
                print(f"    - {e}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main(fits_dir: str | None = None) -> list[dict]:
    if fits_dir is None:
        fits_dir = FITS_DIR

    fits_dir = os.path.abspath(fits_dir)

    print()
    _separator("═")
    print("  ASTRA Cloud — FITS File Inspector")
    print(f"  Scanning : {fits_dir}")
    _separator("═")
    print()

    files = _find_fits_files(fits_dir)

    if not files:
        print(f"  No FITS files found in: {fits_dir}")
        print(f"  Supported extensions: *.fits  *.fit  *.fits.gz")
        print(f"\n  Drop your FITS files into  data/fits/  and re-run.")
        print()
        return []

    print(f"  Found {len(files)} FITS file(s):\n")
    for f in files:
        print(f"    {os.path.relpath(f, ROOT_DIR)}")
    print()

    reports = []
    for fp in files:
        report = inspect_file(fp)
        reports.append(report)

    print_summary(reports)
    return reports


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="ASTRA Cloud — FITS File Inspector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan default data/fits/ folder
  python ml/fits_inspector.py

  # Scan a custom directory
  python ml/fits_inspector.py --dir path/to/my/fits/
        """,
    )
    parser.add_argument(
        "--dir", type=str, default=None,
        help="Directory to scan for FITS files. Default: data/fits/",
    )
    args = parser.parse_args()
    main(fits_dir=args.dir)
