# ============================================================
#  ASTRA Cloud -- Model Comparison
#  File   : ml/model_comparison.py
#  Purpose: Tabulate and visualize evaluation results across
#           Random Forest, XGBoost, SVM, and MLP on the HTRU2
#           dataset. Saves CSV and PNG reports.
# ============================================================

import sys
import io
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

# UTF-8 output for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
CSV_PATH    = REPORTS_DIR / "model_comparison.csv"
PNG_PATH    = REPORTS_DIR / "model_comparison.png"

# ------------------------------------------------------------------
# Experiment Results (Exact values from HTRU2 benchmark)
# ------------------------------------------------------------------
RESULTS = [
    {
        "Model": "Random Forest",
        "Accuracy": 0.9810,
        "Precision": 0.9333,
        "Recall": 0.8537,
        "F1": 0.8917,
        "ROC-AUC": 0.9694,
    },
    {
        "Model": "XGBoost",
        "Accuracy": 0.9793,
        "Precision": 0.9224,
        "Recall": 0.8455,
        "F1": 0.8823,
        "ROC-AUC": 0.9741,
    },
    {
        "Model": "SVM",
        "Accuracy": 0.9799,
        "Precision": 0.9571,
        "Recall": 0.8171,
        "F1": 0.8816,
        "ROC-AUC": 0.9572,
    },
    {
        "Model": "MLP",
        "Accuracy": 0.9804,
        "Precision": 0.9388,
        "Recall": 0.8415,
        "F1": 0.8875,
        "ROC-AUC": 0.9733,
    },
]


def generate_comparison() -> pd.DataFrame:
    print("=" * 68)
    print("  ASTRA Cloud -- HTRU2 Classifier Benchmark Comparison")
    print("=" * 68)

    df = pd.DataFrame(RESULTS)
    print("\nEvaluation Results DataFrame:\n")
    print(df.to_string(index=False))

    # ── 1. Save CSV ───────────────────────────────────────────────
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_PATH, index=False)
    print(f"\n[OK] Saved comparison CSV to : {CSV_PATH}")

    # ── 2. Create Visualization ───────────────────────────────────
    metrics = ["Accuracy", "Precision", "Recall", "F1", "ROC-AUC"]
    models  = df["Model"].tolist()

    # Layout: Grouped Bar Chart
    x = np.arange(len(metrics))
    n_models = len(models)
    total_width = 0.76
    bar_width = total_width / n_models

    palette = ["#00d2ff", "#ff007f", "#00f5d4", "#fee440"]

    fig, ax = plt.subplots(figsize=(11, 6.5), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")

    for i, model in enumerate(models):
        row_values = df.loc[df["Model"] == model, metrics].values[0]
        offset = (i - (n_models - 1) / 2) * bar_width
        bars = ax.bar(
            x + offset,
            row_values,
            width=bar_width * 0.92,
            label=model,
            color=palette[i % len(palette)],
            edgecolor="#ffffff",
            linewidth=0.5,
            alpha=0.92,
        )

        # Annotate bar values
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:.4f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7.5,
                color="white",
                rotation=45,
            )

    # Style axes
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, color="white", fontsize=11, fontweight="bold")
    ax.set_ylim(0.75, 1.03)
    ax.set_ylabel("Score", color="white", fontsize=11, labelpad=8)
    ax.tick_params(colors="white", labelsize=9)
    ax.grid(axis="y", color="#30363d", linestyle="--", alpha=0.7)
    for spine in ax.spines.values():
        spine.set_edgecolor("#30363d")

    # Title & Legend
    ax.set_title(
        "ASTRA Cloud  |  HTRU2 Model Performance Comparison",
        color="white",
        fontsize=13,
        fontweight="bold",
        pad=16,
    )
    legend = ax.legend(
        facecolor="#161b22",
        edgecolor="#30363d",
        labelcolor="white",
        fontsize=9.5,
        loc="upper left",
    )
    legend.get_frame().set_alpha(0.9)

    plt.tight_layout()
    plt.savefig(PNG_PATH, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    print(f"[OK] Saved comparison chart to: {PNG_PATH}")
    print("\n" + "=" * 68 + "\n")

    return df


if __name__ == "__main__":
    generate_comparison()
