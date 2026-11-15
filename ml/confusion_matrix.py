# ============================================================
#  ASTRA Cloud -- Random Forest Confusion Matrix
#  File   : ml/confusion_matrix.py
#  Purpose: Visualize test set confusion matrix for the Random
#           Forest classifier evaluated on the HTRU2 dataset:
#             TN = 4848, FP = 30, FN = 72, TP = 420
# ============================================================

import sys
import io
from pathlib import Path

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
OUTPUT_PNG  = REPORTS_DIR / "random_forest_confusion_matrix.png"

# ------------------------------------------------------------------
# Confusion Matrix Counts
# ------------------------------------------------------------------
# Row 0: True Non-Pulsar  -> [TN, FP]
# Row 1: True Pulsar      -> [FN, TP]
TN = 4848
FP = 30
FN = 72
TP = 420

CM = np.array([
    [TN, FP],
    [FN, TP]
])

CLASS_LABELS = ["Non-Pulsar", "Pulsar"]
CELL_ANNOTATIONS = [
    [f"TN\n{TN:,}", f"FP\n{FP:,}"],
    [f"FN\n{FN:,}", f"TP\n{TP:,}"]
]


def plot_confusion_matrix() -> None:
    print("=" * 65)
    print("  ASTRA Cloud -- Random Forest Confusion Matrix")
    print("=" * 65)

    print("\nConfusion Matrix Values:")
    print(f"  True Negatives  (TN) : {TN}")
    print(f"  False Positives (FP) : {FP}")
    print(f"  False Negatives (FN) : {FN}")
    print(f"  True Positives  (TP) : {TP}")
    total = TN + FP + FN + TP
    print(f"  Total Samples        : {total}")
    print(f"  Accuracy             : {(TN + TP) / total:.4f}")
    print(f"  Precision            : {TP / (TP + FP):.4f}")
    print(f"  Recall               : {TP / (TP + FN):.4f}")

    # ── Figure Layout ─────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 6.2), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")

    # Use log-norm or linear display
    # Using Linear with inferno/Blues colormap
    cmap = plt.cm.Blues
    im = ax.imshow(CM, interpolation="nearest", cmap=cmap)

    # Add Colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Number of Candidates", color="white", fontsize=10, labelpad=10)
    cbar.ax.yaxis.set_tick_params(color="white", labelsize=9)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    # Ticks and Labels
    tick_marks = np.arange(len(CLASS_LABELS))
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(CLASS_LABELS, color="white", fontsize=11, fontweight="bold")
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(CLASS_LABELS, color="white", fontsize=11, fontweight="bold")

    ax.set_xlabel("Predicted Label", color="white", fontsize=12, labelpad=10, fontweight="bold")
    ax.set_ylabel("True Label", color="white", fontsize=12, labelpad=10, fontweight="bold")

    # Spines styling
    for spine in ax.spines.values():
        spine.set_edgecolor("#30363d")

    # Title
    ax.set_title(
        "Random Forest Confusion Matrix (HTRU2 Test Set)",
        color="white",
        fontsize=13,
        fontweight="bold",
        pad=18,
    )

    # ── Add Text Annotations ──────────────────────────────────────
    thresh = (CM.max() + CM.min()) / 2.0
    for i in range(2):
        for j in range(2):
            cell_text = CELL_ANNOTATIONS[i][j]
            color = "white" if CM[i, j] > thresh else "black"
            ax.text(
                j, i, cell_text,
                ha="center", va="center",
                color=color,
                fontsize=13,
                fontweight="bold",
            )

    plt.tight_layout()

    # ── Save File ─────────────────────────────────────────────────
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    print(f"\n[OK] Confusion matrix plot saved to: {OUTPUT_PNG}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    plot_confusion_matrix()
