# ============================================================
#  ASTRA Cloud -- Step 21: Compare Feature Distributions
#  File   : ml/compare_feature_distributions.py
#  Purpose: Compare statistical distributions of HTRU2 benchmark
#           data against extracted real-radio observational features.
#  Outputs: reports/feature_distribution_comparison.csv
#           reports/feature_comparison/*.png
# ============================================================

import sys
import io
import csv
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

warnings.filterwarnings("ignore", category=UserWarning)

REPO_ROOT   = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
DATA_DIR    = REPO_ROOT / "data"

HTRU2_CSV   = DATA_DIR / "htru2" / "HTRU_2.csv"
RADIO_CSV   = REPORTS_DIR / "radio_master_features.csv"
CSV_OUT     = REPORTS_DIR / "feature_distribution_comparison.csv"
PLOTS_DIR   = REPORTS_DIR / "feature_comparison"

HTRU2_COLUMNS = [
    "Profile_Mean",
    "Profile_Std",
    "Profile_Skewness",
    "Profile_Kurtosis",
    "DM_Mean",
    "DM_Std",
    "DM_Skewness",
    "DM_Kurtosis",
    "Target",
]

CSV_FIELDS = [
    "feature_name",
    "htru2_mean",
    "htru2_std",
    "htru2_min",
    "htru2_max",
    "htru2_median",
    "htru2_range",
    "radio_mean",
    "radio_std",
    "radio_min",
    "radio_max",
    "radio_median",
    "radio_range",
    "distribution_note",
]


def compare_distributions() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 21: Compare Feature Distributions")
    print("=" * 68)

    if not HTRU2_CSV.exists() or not RADIO_CSV.exists():
        raise FileNotFoundError("Missing HTRU2 or radio master feature dataset.")

    # 1. Load HTRU2 with automatic header detection
    first_line = pd.read_csv(HTRU2_CSV, nrows=1)
    if "Profile_Mean" in first_line.columns or "mean_ip" in first_line.columns:
        htru2_df = pd.read_csv(HTRU2_CSV)
        htru2_df.columns = HTRU2_COLUMNS
    else:
        # Check if first row contains non-numeric strings
        if any(isinstance(c, str) and any(char.isalpha() for char in str(c)) for c in first_line.columns):
            htru2_df = pd.read_csv(HTRU2_CSV)
            htru2_df.columns = HTRU2_COLUMNS
        else:
            htru2_df = pd.read_csv(HTRU2_CSV, header=None, names=HTRU2_COLUMNS)
    print(f"Loaded HTRU2 dataset: {len(htru2_df)} samples")

    # 2. Load Real Radio features
    radio_df = pd.read_csv(RADIO_CSV)
    # Filter out blank frame (file003) for meaningful statistical comparison
    active_radio = radio_df[radio_df["mean"] != "0.0000"].copy()
    print(f"Loaded Real Radio observations: {len(radio_df)} total, {len(active_radio)} active\n")

    feature_mapping = [
        ("Profile_Mean", "profile_mean", "Severe Domain Shift: Real radio flux is in unnormalized GBT ADU counts (~17,000) vs HTRU2 normalized candidate mean (~111.0)."),
        ("Profile_Std", "profile_std", "Scale Shift: High-resolution timing bins (2048) yield lower std (~3.9) than 64-bin search candidate profiles (~46.5)."),
        ("Profile_Skewness", "profile_skewness", "Partially Aligned: Real radio profile skewness (~0.20) falls within the HTRU2 skewness domain range [-1.98, +8.07]."),
        ("Profile_Kurtosis", "profile_kurtosis", "Partially Aligned: Real radio profile excess kurtosis (~-0.22) falls within the HTRU2 kurtosis domain range [-1.98, +34.54]."),
        ("DM_Mean", "dm_mean", "Not Comparable: DM trials unavailable in single-DM folded timing archive."),
        ("DM_Std", "dm_std", "Not Comparable: DM trials unavailable in single-DM folded timing archive."),
        ("DM_Skewness", "dm_skewness", "Not Comparable: DM trials unavailable in single-DM folded timing archive."),
        ("DM_Kurtosis", "dm_kurtosis", "Not Comparable: DM trials unavailable in single-DM folded timing archive."),
    ]

    records = []

    for h_name, r_name, note in feature_mapping:
        h_vals = htru2_df[h_name].astype(float)
        h_min, h_max = float(h_vals.min()), float(h_vals.max())
        h_mean, h_std = float(h_vals.mean()), float(h_vals.std())
        h_med = float(h_vals.median())
        h_range = h_max - h_min

        # Radio values
        radio_series = active_radio[r_name]
        valid_radio = pd.to_numeric(radio_series, errors="coerce").dropna()

        if len(valid_radio) > 0:
            r_min, r_max = float(valid_radio.min()), float(valid_radio.max())
            r_mean, r_std = float(valid_radio.mean()), float(valid_radio.std())
            r_med = float(valid_radio.median())
            r_range = r_max - r_min

            r_min_str = f"{r_min:.4f}"
            r_max_str = f"{r_max:.4f}"
            r_mean_str = f"{r_mean:.4f}"
            r_std_str = f"{r_std:.4f}"
            r_med_str = f"{r_med:.4f}"
            r_range_str = f"{r_range:.4f}"
        else:
            r_min_str = r_max_str = r_mean_str = r_std_str = r_med_str = r_range_str = "NOT_AVAILABLE"

        row = {
            "feature_name": h_name,
            "htru2_mean": f"{h_mean:.4f}",
            "htru2_std": f"{h_std:.4f}",
            "htru2_min": f"{h_min:.4f}",
            "htru2_max": f"{h_max:.4f}",
            "htru2_median": f"{h_med:.4f}",
            "htru2_range": f"{h_range:.4f}",
            "radio_mean": r_mean_str,
            "radio_std": r_std_str,
            "radio_min": r_min_str,
            "radio_max": r_max_str,
            "radio_median": r_med_str,
            "radio_range": r_range_str,
            "distribution_note": note,
        }
        records.append(row)
        print(f"Feature: {h_name:<18} | HTRU2 Mean: {h_mean:<10.2f} | Radio Mean: {r_mean_str:<10}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    # 3. Generate Comparative Distribution Plots for Available Profile Features
    profile_features = ["Profile_Skewness", "Profile_Kurtosis"]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), facecolor="#0d1117")
    fig.suptitle("ASTRA Cloud  |  HTRU2 vs Real Radio Profile Moment Distributions", color="white", fontsize=12, fontweight="bold")

    for idx, feat_name in enumerate(profile_features):
        ax = axes[idx]
        ax.set_facecolor("#0d1117")

        h_data = htru2_df[feat_name].values
        r_col = "profile_skewness" if "Skew" in feat_name else "profile_kurtosis"
        r_data = pd.to_numeric(active_radio[r_col], errors="coerce").dropna().values

        # Histogram comparison
        ax.hist(h_data, bins=50, density=True, alpha=0.55, color="#00d2ff", label="HTRU2 Benchmark")
        ax.axvline(np.mean(h_data), color="#00d2ff", linestyle="--", linewidth=1.2, label=f"HTRU2 Mean ({np.mean(h_data):.2f})")

        # Scatter points for real radio observations
        ax.scatter(r_data, [0.05] * len(r_data), color="#ff007f", s=45, zorder=5, label=f"Real GBT Radio (N={len(r_data)})")
        ax.axvline(np.mean(r_data), color="#ff007f", linestyle=":", linewidth=1.5, label=f"Radio Mean ({np.mean(r_data):.2f})")

        ax.set_title(feat_name, color="white", fontsize=11, fontweight="bold")
        ax.set_xlabel("Feature Value", color="white", fontsize=9)
        ax.set_ylabel("Probability Density", color="white", fontsize=9)
        ax.tick_params(colors="white", labelsize=8)
        ax.grid(True, color="#30363d", linestyle="--", alpha=0.5)
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")
        ax.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="white", fontsize=8)

    plt.tight_layout()
    plot_path = PLOTS_DIR / "profile_moments_distribution_comparison.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    print(f"\n[OK] Distribution comparison table saved → {CSV_OUT}")
    print(f"[OK] Distribution comparison plot saved  → {plot_path}")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    compare_distributions()
