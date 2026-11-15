# ============================================================
#  ASTRA Cloud -- Step 13: Radio Data Visualization
#  File   : ml/radio_visualizer.py
#  Purpose: Generate integrated pulse profile and dynamic
#           spectrum visualizations for valid radio PSRFITS files.
#  Outputs: reports/radio_plots/*.png
#           reports/radio_visualization_index.csv
# ============================================================

import sys
import io
import csv
import warnings
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
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
PLOTS_DIR   = REPORTS_DIR / "radio_plots"
INDEX_CSV   = REPORTS_DIR / "radio_visualization_index.csv"

INDEX_FIELDS = ["file_name", "plot_type", "plot_path", "description"]


def visualize_radio_data() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 13: Radio Data Visualization")
    print("=" * 68)

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fits_files = sorted(RADIO_DIR.glob("*.fits"))

    if not fits_files:
        print(f"[WARN] No files found in {RADIO_DIR}")
        return

    index_records = []

    for i, fp in enumerate(fits_files, start=1):
        file_prefix = f"file{i:03d}"
        stem = fp.stem

        print(f"\nProcessing [{file_prefix}] {fp.name} ...")

        try:
            with fits.open(fp, mode="readonly", memmap=True) as hdul:
                subint = None
                for h in hdul:
                    if h.name.upper() == "SUBINT":
                        subint = h
                        break

                if subint is None or "DATA" not in subint.columns.names:
                    print(f"  [SKIP] No SUBINT DATA table in {fp.name}")
                    continue

                d = subint.data
                raw_data = d["DATA"][0]  # shape: (4, 128, 2048)

                # Check if file has non-zero signal (e.g. not blank zero frame)
                if np.all(raw_data == 0):
                    print(f"  [SKIP] All pixels zero in {fp.name}")
                    continue

                # Apply calibration scaling if available
                if "DAT_SCL" in subint.columns.names and "DAT_OFFS" in subint.columns.names:
                    scl = d["DAT_SCL"][0].reshape(4, 128, 1)
                    offs = d["DAT_OFFS"][0].reshape(4, 128, 1)
                    cal_data = raw_data.astype(np.float64) * scl + offs
                    # Stokes I = Total Intensity (pol 0 + pol 1)
                    stokes_i = cal_data[0] + cal_data[1]  # shape: (128, 2048)
                else:
                    stokes_i = raw_data[0].astype(np.float64) + raw_data[1].astype(np.float64)

                # Frequency axis if available
                freq_axis = None
                if "DAT_FREQ" in subint.columns.names:
                    freq_axis = d["DAT_FREQ"][0]

                # Integrated 1D profile across all 128 channels
                integrated_profile = stokes_i.mean(axis=0)  # shape: (2048,)
                nbins = len(integrated_profile)
                phase = np.linspace(0.0, 1.0, nbins, endpoint=False)

                target = hdul[0].header.get("SRC_NAME", "J1713+0747")
                telescope = hdul[0].header.get("TELESCOP", "GBT")
                obs_date = hdul[0].header.get("DATE-OBS", "N/A")
                center_freq = hdul[0].header.get("OBSFREQ", "820.0")

                # ─────────────────────────────────────────────────────────────
                # Plot 1: Integrated Pulse Profile
                # ─────────────────────────────────────────────────────────────
                profile_filename = f"{file_prefix}_profile.png"
                profile_path = PLOTS_DIR / profile_filename

                fig, ax = plt.subplots(figsize=(8, 4.5), facecolor="#0d1117")
                ax.set_facecolor("#0d1117")

                ax.plot(phase, integrated_profile, color="#00d2ff", linewidth=1.2, label=f"Stokes I ({target})")
                ax.set_title(
                    f"{telescope} / VEGAS  |  Target: {target}  |  Integrated Profile\n"
                    f"Obs Date: {obs_date}  |  Freq: {center_freq} MHz",
                    color="white", fontsize=11, fontweight="bold", pad=12
                )
                ax.set_xlabel("Pulse Phase", color="white", fontsize=10, labelpad=8)
                ax.set_ylabel("Calibrated Flux (Arbitrary Units)", color="white", fontsize=10, labelpad=8)
                ax.tick_params(colors="white", labelsize=9)
                ax.set_xlim(0.0, 1.0)
                ax.grid(True, color="#30363d", linestyle="--", alpha=0.6)
                for spine in ax.spines.values():
                    spine.set_edgecolor("#30363d")

                ax.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="white", loc="upper right")
                plt.tight_layout()
                plt.savefig(profile_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
                plt.close(fig)

                index_records.append({
                    "file_name": fp.name,
                    "plot_type": "Integrated Pulse Profile",
                    "plot_path": f"reports/radio_plots/{profile_filename}",
                    "description": f"Folded pulse profile intensity averaged over 128 channels and polarizations across 2048 phase bins for {target}.",
                })
                print(f"  [SAVED] {profile_filename}")

                # ─────────────────────────────────────────────────────────────
                # Plot 2: Dynamic Spectrum (Frequency Channels vs Pulse Phase)
                # ─────────────────────────────────────────────────────────────
                spec_filename = f"{file_prefix}_dynamic_spectrum.png"
                spec_path = PLOTS_DIR / spec_filename

                fig, ax = plt.subplots(figsize=(9, 5.5), facecolor="#0d1117")
                ax.set_facecolor("#0d1117")

                # Baseline subtract per channel for dynamic spectrum contrast
                chan_medians = np.median(stokes_i, axis=1, keepdims=True)
                stokes_i_sub = stokes_i - chan_medians

                vmin, vmax = np.percentile(stokes_i_sub, [2, 98])
                if vmin == vmax:
                    vmin -= 1.0
                    vmax += 1.0

                extent = [0.0, 1.0, 0, stokes_i.shape[0]]
                if freq_axis is not None and len(freq_axis) == stokes_i.shape[0]:
                    extent = [0.0, 1.0, freq_axis.min(), freq_axis.max()]
                    y_label = "Radio Frequency (MHz)"
                else:
                    y_label = "Channel Index"

                im = ax.imshow(
                    stokes_i_sub,
                    origin="lower",
                    aspect="auto",
                    cmap="inferno",
                    extent=extent,
                    vmin=vmin,
                    vmax=vmax,
                    interpolation="nearest",
                )

                cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                cbar.set_label("Relative Pulse Intensity", color="white", fontsize=9, labelpad=8)
                cbar.ax.yaxis.set_tick_params(color="white", labelsize=8)
                plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

                ax.set_title(
                    f"{telescope} / VEGAS  |  Target: {target}  |  Frequency vs Phase\n"
                    f"Obs Date: {obs_date}  |  Channels: {stokes_i.shape[0]}",
                    color="white", fontsize=11, fontweight="bold", pad=12
                )
                ax.set_xlabel("Pulse Phase", color="white", fontsize=10, labelpad=8)
                ax.set_ylabel(y_label, color="white", fontsize=10, labelpad=8)
                ax.tick_params(colors="white", labelsize=9)
                for spine in ax.spines.values():
                    spine.set_edgecolor("#30363d")

                plt.tight_layout()
                plt.savefig(spec_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
                plt.close(fig)

                index_records.append({
                    "file_name": fp.name,
                    "plot_type": "Dynamic Spectrum",
                    "plot_path": f"reports/radio_plots/{spec_filename}",
                    "description": f"2D phase vs frequency dynamic spectrum (128 channels x 2048 phase bins) for {target}.",
                })
                print(f"  [SAVED] {spec_filename}")

        except Exception as exc:
            print(f"  [ERROR] Could not visualize {fp.name}: {exc}")

    # Write visualization index
    with open(INDEX_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INDEX_FIELDS)
        writer.writeheader()
        writer.writerows(index_records)

    print(f"\n[OK] Visualization index saved → {INDEX_CSV}")
    print(f"Total visualizations generated: {len(index_records)}\n")


if __name__ == "__main__":
    visualize_radio_data()
