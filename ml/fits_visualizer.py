# ============================================================
#  ASTRA Cloud -- FITS Visualizer
#  File   : ml/fits_visualizer.py
#  Purpose: Read the primary HDU (shape 4 x 200 x 200) from
#           WFPC2u5780205r_c0fx.fits and produce:
#             - reports/fits_preview/group_1.png  … group_4.png
#             - reports/fits_preview/all_groups.png
#  Deps   : astropy, numpy, matplotlib
#  NOTE   : Read-only — the FITS file is never modified.
# ============================================================

import sys
import io
import warnings
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")          # non-interactive backend — no window needed
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from astropy.io import fits
from astropy.utils.exceptions import AstropyWarning

# UTF-8 output for clean printing on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Suppress benign astropy warnings (HIERARCH, VerifyWarning, etc.)
warnings.filterwarnings("ignore", category=AstropyWarning)

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent.parent   # e:\ASTRA CLOUD
FITS_PATH   = REPO_ROOT / "data" / "fits" / "WFPC2u5780205r_c0fx.fits"
PREVIEW_DIR = REPO_ROOT / "reports" / "fits_preview"

CMAP        = "inferno"         # perceptually uniform, works in B&W print too
DPI         = 150

# WFPC2 chip labels (PC1 + three Wide Field chips)
CHIP_LABELS = ["PC1", "WF2", "WF3", "WF4"]

# ------------------------------------------------------------------
# Helper: compute vmin / vmax from finite pixels only
# ------------------------------------------------------------------
def _auto_scale(data2d: np.ndarray, low_pct: float = 1.0, high_pct: float = 99.0):
    """Return (vmin, vmax) clipped to the finite-pixel percentile range."""
    finite = data2d[np.isfinite(data2d)]
    if finite.size == 0:
        return 0.0, 1.0
    vmin = float(np.percentile(finite, low_pct))
    vmax = float(np.percentile(finite, high_pct))
    if vmin == vmax:          # flat image guard
        vmin -= 0.5
        vmax += 0.5
    return vmin, vmax


# ------------------------------------------------------------------
# Helper: render a single 200×200 frame into an Axes
# ------------------------------------------------------------------
def _render_panel(ax: plt.Axes, img: np.ndarray, group_idx: int,
                  add_colorbar: bool = True, fig: plt.Figure = None) -> None:
    """
    Draw *img* (200×200 float array) into *ax* with automatic scaling,
    axis labels and a colourbar.
    """
    group_num   = group_idx + 1                      # 1-based for display
    chip_label  = CHIP_LABELS[group_idx] if group_idx < len(CHIP_LABELS) else str(group_idx)
    vmin, vmax  = _auto_scale(img)

    im = ax.imshow(
        img,
        cmap=CMAP,
        origin="lower",               # FITS convention: row 0 = bottom
        interpolation="nearest",
        vmin=vmin,
        vmax=vmax,
    )

    ax.set_title(f"Group {group_num}  ({chip_label})", color="white", fontsize=11, pad=6)
    ax.set_xlabel("X  (pixels)",  color="white", fontsize=9)
    ax.set_ylabel("Y  (pixels)",  color="white", fontsize=9)
    ax.tick_params(colors="white", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#555")
    ax.set_facecolor("#0d1117")

    if add_colorbar and fig is not None:
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Pixel Value (ADU)", color="white", fontsize=8)
        cbar.ax.yaxis.set_tick_params(color="white", labelsize=7)
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    return im


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> None:
    print("=" * 65)
    print("  ASTRA Cloud  --  FITS Visualizer")
    print("=" * 65)

    # ── Open FITS (read-only) ─────────────────────────────────────
    print(f"\n  Opening : {FITS_PATH}")
    hdul = fits.open(FITS_PATH, mode="readonly", memmap=True,
                     ignore_missing_simple=True)

    try:
        primary_data = hdul[0].data      # shape: (4, 200, 200), dtype: >f4

        if primary_data is None:
            raise ValueError("Primary HDU contains no array data.")

        print(f"  Primary HDU shape : {primary_data.shape}")
        print(f"  Primary HDU dtype : {primary_data.dtype}")

        n_groups = primary_data.shape[0]
        if n_groups != 4:
            print(f"  [WARN] Expected 4 groups, found {n_groups}. "
                  "Proceeding with all available groups.")

        # Convert to float64 for safe statistics (copy to detach from mmap)
        cube = primary_data.astype(np.float64)

    finally:
        hdul.close()     # release file handle immediately after loading data

    # ── Ensure output directory exists ────────────────────────────
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1.  Individual images  →  group_1.png … group_4.png
    # ------------------------------------------------------------------
    print(f"\n  Saving individual group images to: {PREVIEW_DIR}\n")

    for idx in range(n_groups):
        img        = cube[idx]                          # (200, 200)
        group_num  = idx + 1
        chip_label = CHIP_LABELS[idx] if idx < len(CHIP_LABELS) else str(idx)
        out_path   = PREVIEW_DIR / f"group_{group_num}.png"

        fig, ax = plt.subplots(
            figsize=(6, 5.5),
            facecolor="#0d1117",
        )

        _render_panel(ax, img, idx, add_colorbar=True, fig=fig)

        # Super-title with file + chip info
        fig.suptitle(
            f"WFPC2  |  Group {group_num} / {n_groups}  ({chip_label})",
            color="white", fontsize=12, fontweight="bold", y=1.01,
        )

        plt.tight_layout()
        plt.savefig(out_path, dpi=DPI, bbox_inches="tight",
                    facecolor="#0d1117")
        plt.close(fig)

        # Per-group statistics (finite pixels only)
        finite = img[np.isfinite(img)]
        print(f"  [OK] group_{group_num}.png  |  chip={chip_label}"
              f"  min={finite.min():.3f}"
              f"  max={finite.max():.3f}"
              f"  mean={finite.mean():.3f}"
              f"  std={finite.std():.3f}")

    # ------------------------------------------------------------------
    # 2.  Combined 4-panel  →  all_groups.png
    # ------------------------------------------------------------------
    all_path = PREVIEW_DIR / "all_groups.png"
    print(f"\n  Saving combined panel  →  {all_path}")

    fig, axes = plt.subplots(
        2, 2,
        figsize=(13, 11),
        facecolor="#0d1117",
    )
    fig.suptitle(
        "ASTRA Cloud  |  WFPC2u5780205r_c0fx.fits  |  All Groups",
        color="white", fontsize=14, fontweight="bold", y=1.01,
    )

    for idx, ax in enumerate(axes.flat):
        if idx < n_groups:
            _render_panel(ax, cube[idx], idx, add_colorbar=True, fig=fig)
        else:
            ax.set_visible(False)   # hide any surplus panels

    plt.tight_layout()
    plt.savefig(all_path, dpi=DPI, bbox_inches="tight",
                facecolor="#0d1117")
    plt.close(fig)

    print("\n" + "=" * 65)
    print("  Done!  Files written:")
    for idx in range(1, n_groups + 1):
        p = PREVIEW_DIR / f"group_{idx}.png"
        print(f"    {p}")
    print(f"    {all_path}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
