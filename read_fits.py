# ============================================================
#  ASTRA Cloud -- FITS File Reader
#  File   : read_fits.py
#  Purpose: Open, inspect, and visualise a FITS observation
#           file using Astropy and Matplotlib.
#  FITS   : WFPC2u5780205r_c0fx.fits  (HST / WFPC2 image)
# ============================================================

# Force UTF-8 output so special chars print cleanly on Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import matplotlib
matplotlib.use("Agg")          # non-interactive backend: saves to file, no window needed
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.visualization import ZScaleInterval, ImageNormalize

# ----------------------------------------------------------------
# STEP 1 -- Open the FITS file
# ----------------------------------------------------------------
# astropy.io.fits.open() returns an HDUList object, which is
# like a list of "Header+Data Units" stored inside the file.
# memmap=True means the data is read lazily (only when needed),
# which is efficient for large files.

FITS_FILE = "WFPC2u5780205r_c0fx.fits"

print("=" * 60)
print("  ASTRA Cloud -- FITS Reader")
print("=" * 60)

hdul = fits.open(FITS_FILE, memmap=True)
print(f"\n[OK]  Opened file : {FITS_FILE}")

# ----------------------------------------------------------------
# STEP 2 -- Print the FITS file structure (HDU info table)
# ----------------------------------------------------------------
# hdul.info() prints a table with:
#   No.   Name   Ver   Type        Cards  Dimensions  Format

print("\n" + "-" * 60)
print("  STEP 2 -- FITS File Structure")
print("-" * 60)
hdul.info()

# ----------------------------------------------------------------
# STEP 3 -- Print the primary header information
# ----------------------------------------------------------------
# The primary HDU (index 0) carries global observation metadata.
# hdul[0].header holds all keyword=value pairs.

print("\n" + "-" * 60)
print("  STEP 3 -- Primary Header (HDU 0)")
print("-" * 60)
primary_header = hdul[0].header
print(repr(primary_header))

# ----------------------------------------------------------------
# STEP 4 -- Extract key metadata
# ----------------------------------------------------------------
# .get(keyword, default) safely returns a fallback value when
# the keyword is absent so the script never crashes on missing
# metadata fields.

print("\n" + "-" * 60)
print("  STEP 4 -- Key Observation Metadata")
print("-" * 60)

def find_keyword(*keywords, headers=None, default="N/A"):
    """Return the first matching value across a list of headers."""
    for hdr in (headers or []):
        for kw in keywords:
            val = hdr.get(kw, None)
            if val not in (None, "", " "):
                return val
    return default

# Collect all available headers for the lookup
all_headers = [hdul[i].header for i in range(len(hdul))]

telescope     = find_keyword("TELESCOP",               headers=all_headers)
instrument    = find_keyword("INSTRUME",               headers=all_headers)
object_name   = find_keyword("TARGNAME", "OBJECT",     headers=all_headers)
obs_date      = find_keyword("DATE-OBS", "DATE_OBS",   headers=all_headers)
exposure_time = find_keyword("EXPTIME",  "EXPOSURE",   headers=all_headers)

# Image size: look for NAXIS1 / NAXIS2 in any image-bearing HDU
img_width  = find_keyword("NAXIS1", headers=all_headers)
img_height = find_keyword("NAXIS2", headers=all_headers)
image_size = (
    f"{img_width} x {img_height} pixels"
    if img_width != "N/A" and img_height != "N/A"
    else "N/A"
)

print(f"  Telescope       : {telescope}")
print(f"  Instrument      : {instrument}")
print(f"  Object Name     : {object_name}")
print(f"  Observation Date: {obs_date}")
print(f"  Exposure Time   : {exposure_time} s")
print(f"  Image Size      : {image_size}")

# ----------------------------------------------------------------
# STEP 5 -- Detect which HDU(s) contain image data
# ----------------------------------------------------------------
# An HDU has actual 2-D image data when its .data attribute is
# a NumPy ndarray with at least 2 dimensions.

print("\n" + "-" * 60)
print("  STEP 5 -- Detecting Image HDU(s)")
print("-" * 60)

# image_panels stores (label, 2-D array) tuples ready for plotting
image_panels = []
image_hdus   = []   # raw (index, HDU) pairs kept for Step 7

for idx, hdu in enumerate(hdul):
    if hdu.data is not None and isinstance(hdu.data, np.ndarray) and hdu.data.ndim >= 2:
        print(f"  [IMAGE] HDU {idx}  |  Name: {hdu.name:<10}  |  Shape: {hdu.data.shape}  |  dtype: {hdu.data.dtype}")
        image_hdus.append((idx, hdu))

        data = hdu.data
        if data.ndim == 2:
            # Simple 2-D image
            image_panels.append((f"HDU {idx} | {hdu.name}", data))
        elif data.ndim == 3:
            # 3-D cube: first axis = frame/chip number
            # WFPC2 stores 4 chips as shape (4, 200, 200)
            chip_labels = ["PC1", "WF2", "WF3", "WF4"]
            for chip_idx in range(data.shape[0]):
                label_suffix = chip_labels[chip_idx] if chip_idx < len(chip_labels) else str(chip_idx)
                image_panels.append(
                    (f"HDU {idx} | {hdu.name} | {label_suffix}", data[chip_idx])
                )
        else:
            # Higher-dimensional: just take the first 2-D slice
            image_panels.append((f"HDU {idx} | {hdu.name} [slice]", data.reshape(-1, data.shape[-1])[:data.shape[-2], :])) 

if not image_hdus:
    print("  [WARN] No 2-D image data found in this FITS file.")

# ----------------------------------------------------------------
# STEP 6 -- Display the image(s) using Matplotlib
# ----------------------------------------------------------------
# ZScaleInterval mimics the contrast stretch used in DS9:
# it clips extreme outliers so faint structures are visible.

print("\n" + "-" * 60)
print("  STEP 6 -- Displaying Image(s)")
print("-" * 60)

if image_panels:
    n_images = len(image_panels)
    ncols = min(n_images, 4)
    nrows = (n_images + ncols - 1) // ncols

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(6 * ncols, 5 * nrows),
        squeeze=False,
        facecolor="#0d1117"
    )
    fig.suptitle(
        f"ASTRA Cloud  |  {object_name}  |  {instrument} / {telescope}",
        color="white", fontsize=14, fontweight="bold", y=1.01
    )

    for panel_idx, (label, img_2d) in enumerate(image_panels):
        ax = axes[panel_idx // ncols][panel_idx % ncols]

        img_data = np.array(img_2d, dtype=float)

        # ZScale stretch for visually pleasing contrast (DS9-style)
        interval = ZScaleInterval(contrast=0.25)
        try:
            vmin, vmax = interval.get_limits(img_data)
        except Exception:
            vmin, vmax = np.nanpercentile(img_data, [1, 99])

        norm = ImageNormalize(img_data, vmin=vmin, vmax=vmax)

        im = ax.imshow(
            img_data,
            cmap="inferno",       # vibrant astronomy colour map
            norm=norm,
            origin="lower",       # FITS convention: row 0 = bottom
            interpolation="nearest"
        )

        # Colour bar
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.yaxis.set_tick_params(color="white")
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
        cbar.set_label("Pixel Value (ADU)", color="white", fontsize=9)

        # Panel title and axis labels
        ax.set_title(label, color="white", fontsize=9)
        ax.set_xlabel("X (pixels)", color="white", fontsize=9)
        ax.set_ylabel("Y (pixels)", color="white", fontsize=9)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")
        ax.set_facecolor("#0d1117")

    # Hide any unused subplot panels
    for panel_idx in range(n_images, nrows * ncols):
        axes[panel_idx // ncols][panel_idx % ncols].set_visible(False)

    plt.tight_layout()
    plt.savefig("astra_fits_image.png", dpi=150, bbox_inches="tight",
                facecolor="#0d1117")
    plt.close(fig)   # release memory; no window shown (Agg backend)
    print("  [OK]  Image saved as : astra_fits_image.png")
else:
    print("  [WARN] No image panels to display.")

# ----------------------------------------------------------------
# STEP 7 -- Image statistics (shape, dtype, min/max/mean)
# ----------------------------------------------------------------

print("\n" + "-" * 60)
print("  STEP 7 -- Image Statistics")
print("-" * 60)

for hdu_idx, hdu in image_hdus:
    img_data = np.squeeze(hdu.data).astype(float)

    print(f"\n  HDU {hdu_idx}  --  {hdu.name}")
    print(f"    Shape           : {img_data.shape}")
    print(f"    Data Type       : {img_data.dtype}")
    print(f"    Min Pixel Value : {np.nanmin(img_data):.4f}")
    print(f"    Max Pixel Value : {np.nanmax(img_data):.4f}")
    print(f"    Avg Pixel Value : {np.nanmean(img_data):.4f}")

# ----------------------------------------------------------------
# STEP 8 -- Close the FITS file
# ----------------------------------------------------------------
# Always close the file to release system file handles and
# free any memory-mapped resources.

hdul.close()

print("\n" + "-" * 60)
print("  STEP 8 -- FITS file closed successfully.")
print("-" * 60)
print("\n  ASTRA Cloud -- Done!\n")
