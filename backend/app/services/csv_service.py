# ============================================================
#  ASTRA Cloud — CSV Analysis Service
#  File   : backend/app/services/csv_service.py
#  Purpose: Statistical, correlation, and ML pulsar classification
#           workflows for uploaded CSV tabular data files.
# ============================================================

import io
import math
import time
import base64
import pickle
import joblib
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODELS_DIR = REPO_ROOT / "models"

# ── HTRU2 feature mapping ────────────────────────────────────
# Map canonical model feature names → flexible column name substrings
HTRU2_FEATURE_MAP: Dict[str, List[str]] = {
    "Profile_Mean":     ["profile_mean", "mean of the integrated profile", "mean_integrated", "profile mean"],
    "Profile_Std":      ["profile_std", "standard deviation of the integrated profile", "std_integrated", "profile std"],
    "Profile_Skewness": ["profile_skewness", "skewness of the integrated profile", "profile skewness"],
    "Profile_Kurtosis": ["profile_kurtosis", "kurtosis of the integrated profile", "excess kurtosis of the integrated profile", "profile kurtosis"],
    "DM_Mean":          ["dm_mean", "mean of the dm", "dm mean", "mean dm"],
    "DM_Std":           ["dm_std", "standard deviation of the dm", "dm std", "dm-snr std"],
    "DM_Skewness":      ["dm_skewness", "skewness of the dm", "dm skewness"],
    "DM_Kurtosis":      ["dm_kurtosis", "kurtosis of the dm", "excess kurtosis of the dm", "dm kurtosis"],
}

HTRU2_CANONICAL = list(HTRU2_FEATURE_MAP.keys())


def _safe(v: Any) -> Any:
    """Turn NaN / Inf into None for JSON safety."""
    if v is None:
        return None
    try:
        if math.isnan(float(v)) or math.isinf(float(v)):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode("utf-8")


# ── Helpers ───────────────────────────────────────────────────
def _map_htru2_columns(df: pd.DataFrame) -> Optional[Dict[str, str]]:
    """
    Try to map dataframe columns to HTRU2 canonical feature names.
    Returns {canonical_name: actual_col} or None if not all 8 found.
    """
    col_lower = {c: c.lower().strip() for c in df.columns}
    mapping: Dict[str, str] = {}

    for canonical, variants in HTRU2_FEATURE_MAP.items():
        found = None
        for actual_col, lower_col in col_lower.items():
            if any(v in lower_col for v in variants):
                found = actual_col
                break
        if found:
            mapping[canonical] = found

    # Fallback: if at least 8 numeric columns exist (positional mapping)
    if len(mapping) < 8:
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        candidate_cols = [
            c for c in num_cols
            if c.lower().strip() not in {"target_class", "target", "class", "label", "is_pulsar"}
        ]
        if len(candidate_cols) >= 8:
            mapping = {canonical: candidate_cols[i] for i, canonical in enumerate(HTRU2_CANONICAL)}

    return mapping if len(mapping) == 8 else None


def get_csv_workflows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Return list of available analysis workflows for a CSV dataframe."""
    workflows = [
        {
            "id": "csv_statistics",
            "name": "Statistical Summary",
            "description": "Compute descriptive statistics (mean, std, min/max, quartiles) and distribution histograms for all numeric columns.",
            "category": "statistics",
            "enabled": True,
        },
        {
            "id": "csv_correlation",
            "name": "Correlation Matrix",
            "description": "Generate a Pearson correlation heatmap for numeric features to identify co-linear variables.",
            "category": "visualization",
            "enabled": True,
        },
    ]

    # Only show pulsar inference if HTRU2 columns can be mapped
    htru2_map = _map_htru2_columns(df)
    if htru2_map:
        workflows.append({
            "id": "csv_pulsar_inference",
            "name": "Pulsar ML Classification",
            "description": "Run HTRU2-trained Random Forest classifier on each row. Outputs per-row pulsar probability and candidate count.",
            "category": "ml",
            "enabled": True,
        })

    return workflows


# ── Workflow Executors ────────────────────────────────────────
def run_csv_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """Descriptive statistics + distribution histograms for numeric columns."""
    start = time.time()
    numeric_df = df.select_dtypes(include="number")

    if numeric_df.empty:
        return {
            "status": "HALTED",
            "summary": "No numeric columns found in the CSV.",
            "details": {},
            "elapsed_seconds": round(time.time() - start, 3),
        }

    desc = numeric_df.describe().round(6)
    stats_dict = desc.to_dict()

    # Generate histograms (max 9 columns)
    cols_to_plot = list(numeric_df.columns[:9])
    n = len(cols_to_plot)
    ncols = min(3, n)
    nrows = math.ceil(n / ncols)

    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 4, nrows * 3),
                              facecolor="#0d121f")
    axes_flat = np.array(axes).flatten() if n > 1 else [axes]

    for i, col in enumerate(cols_to_plot):
        ax = axes_flat[i]
        ax.set_facecolor("#070a12")
        data = numeric_df[col].dropna()
        ax.hist(data, bins=30, color="#6366f1", edgecolor="#0d121f", alpha=0.85)
        ax.set_title(col[:28], color="#f8fafc", fontsize=8, pad=5)
        ax.tick_params(colors="#94a3b8", labelsize=7)
        for sp in ax.spines.values():
            sp.set_color("#1e293b")
        ax.set_xlabel("", color="#94a3b8", fontsize=7)
        ax.set_ylabel("Count", color="#94a3b8", fontsize=7)

    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle("Feature Distributions", color="#f8fafc", fontsize=12, y=1.01)
    plt.tight_layout()
    histogram_url = _fig_to_b64(fig)

    return {
        "status": "COMPLETED",
        "summary": (
            f"Statistical summary computed for {len(numeric_df.columns)} numeric columns "
            f"across {len(df)} rows."
        ),
        "details": {
            "stats": stats_dict,
            "histogram_url": histogram_url,
            "numeric_columns": list(numeric_df.columns),
            "total_rows": len(df),
            "null_counts": numeric_df.isnull().sum().to_dict(),
        },
        "elapsed_seconds": round(time.time() - start, 3),
    }


def run_csv_correlation(df: pd.DataFrame) -> Dict[str, Any]:
    """Pearson correlation heatmap for numeric columns."""
    start = time.time()
    numeric_df = df.select_dtypes(include="number")

    if numeric_df.shape[1] < 2:
        return {
            "status": "HALTED",
            "summary": "Need at least 2 numeric columns to compute a correlation matrix.",
            "details": {},
            "elapsed_seconds": round(time.time() - start, 3),
        }

    corr = numeric_df.corr(method="pearson").round(4)
    corr_dict = corr.to_dict()

    n = len(corr.columns)
    fig_size = max(6, n * 0.8)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size * 0.85), facecolor="#0d121f")
    ax.set_facecolor("#0d121f")

    cmap = mcolors.LinearSegmentedColormap.from_list(
        "astra_corr", ["#ef4444", "#0d121f", "#6366f1"]
    )
    im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1, aspect="auto")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    short_labels = [c[:20] for c in corr.columns]
    ax.set_xticklabels(short_labels, rotation=45, ha="right", fontsize=7, color="#94a3b8")
    ax.set_yticklabels(short_labels, fontsize=7, color="#94a3b8")

    # Annotate cells
    for i in range(n):
        for j in range(n):
            v = corr.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    fontsize=6.5, color="#f8fafc" if abs(v) > 0.5 else "#94a3b8")

    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.ax.yaxis.set_tick_params(color="#94a3b8", labelcolor="#94a3b8", labelsize=8)
    cbar.set_label("Pearson r", color="#94a3b8", fontsize=9)

    ax.set_title("Feature Correlation Matrix (Pearson)", color="#f8fafc", fontsize=11, pad=12)
    for sp in ax.spines.values():
        sp.set_color("#1e293b")

    plt.tight_layout()
    heatmap_url = _fig_to_b64(fig)

    # Find top correlations
    top_pairs = []
    seen = set()
    flat = corr.stack().reset_index()
    flat.columns = ["col_a", "col_b", "r"]
    flat = flat[flat["col_a"] != flat["col_b"]].copy()
    flat["abs_r"] = flat["r"].abs()
    flat = flat.sort_values("abs_r", ascending=False)
    for _, row in flat.iterrows():
        pair = tuple(sorted([row["col_a"], row["col_b"]]))
        if pair not in seen:
            seen.add(pair)
            top_pairs.append({"col_a": row["col_a"], "col_b": row["col_b"], "r": round(row["r"], 4)})
        if len(top_pairs) >= 8:
            break

    return {
        "status": "COMPLETED",
        "summary": (
            f"Pearson correlation matrix computed for {n} numeric columns. "
            f"Strongest correlation: {top_pairs[0]['col_a'][:20]} <-> {top_pairs[0]['col_b'][:20]} "
            f"(r={top_pairs[0]['r']})" if top_pairs else "No correlations found."
        ),
        "details": {
            "heatmap_url": heatmap_url,
            "correlation_matrix": corr_dict,
            "top_correlations": top_pairs,
            "n_features": n,
        },
        "elapsed_seconds": round(time.time() - start, 3),
    }


def run_csv_pulsar_inference(df: pd.DataFrame) -> Dict[str, Any]:
    """Run HTRU2 Random Forest classifier on CSV rows."""
    start = time.time()

    htru2_map = _map_htru2_columns(df)
    if not htru2_map:
        return {
            "status": "HALTED",
            "summary": "CSV does not contain recognisable HTRU2 pulsar features.",
            "details": {"inference_status": "INFERENCE_HALTED",
                        "halt_reason": "Could not map 8 required HTRU2 feature columns."},
            "elapsed_seconds": round(time.time() - start, 3),
        }

    # Build feature matrix
    feature_df = pd.DataFrame({
        canonical: df[htru2_map[canonical]] for canonical in HTRU2_CANONICAL
    }).apply(pd.to_numeric, errors="coerce")

    valid_mask = feature_df.notna().all(axis=1)
    valid_df = feature_df[valid_mask]
    skipped = int((~valid_mask).sum())

    if valid_df.empty:
        return {
            "status": "HALTED",
            "summary": "All rows contain NaN values in feature columns — cannot run inference.",
            "details": {"inference_status": "INFERENCE_HALTED",
                        "halt_reason": "All rows had missing feature values."},
            "elapsed_seconds": round(time.time() - start, 3),
        }

    # Load model
    model_path = MODELS_DIR / "random_forest_pipeline.pkl"
    if not model_path.exists():
        model_path = MODELS_DIR / "random_forest.joblib"
    if not model_path.exists():
        return {
            "status": "HALTED",
            "summary": "ML model file not found.",
            "details": {"inference_status": "INFERENCE_HALTED",
                        "halt_reason": "Model file missing from models/ directory."},
            "elapsed_seconds": round(time.time() - start, 3),
        }

    model = joblib.load(model_path)
    X = valid_df[HTRU2_CANONICAL]

    proba = model.predict_proba(X)[:, 1]   # P(pulsar)
    preds = (proba >= 0.5).astype(int)

    n_total = len(valid_df)
    n_pulsar = int(preds.sum())
    n_noise = n_total - n_pulsar
    pulsar_rate = round(100 * n_pulsar / n_total, 2) if n_total > 0 else 0

    # Probability distribution plot
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor="#0d121f")

    ax1 = axes[0]
    ax1.set_facecolor("#070a12")
    ax1.hist(proba[preds == 0], bins=30, color="#94a3b8", alpha=0.75, label="RFI/Noise")
    ax1.hist(proba[preds == 1], bins=30, color="#6366f1", alpha=0.9, label="Pulsar")
    ax1.axvline(0.5, color="#f59e0b", linestyle="--", linewidth=1.2, label="Threshold (0.5)")
    ax1.set_title("Pulsar Probability Distribution", color="#f8fafc", fontsize=10, pad=8)
    ax1.set_xlabel("P(Pulsar)", color="#94a3b8", fontsize=9)
    ax1.set_ylabel("Count", color="#94a3b8", fontsize=9)
    ax1.tick_params(colors="#94a3b8", labelsize=8)
    ax1.legend(fontsize=8, facecolor="#1e293b", labelcolor="#f8fafc")
    for sp in ax1.spines.values():
        sp.set_color("#1e293b")

    ax2 = axes[1]
    ax2.set_facecolor("#070a12")
    labels = ["Pulsar\nCandidates", "RFI / Noise"]
    sizes = [n_pulsar, n_noise]
    colors = ["#6366f1", "#374151"]
    wedges, texts, autotexts = ax2.pie(
        sizes, labels=labels, colors=colors, autopct="%1.1f%%",
        startangle=90, textprops={"color": "#f8fafc", "fontsize": 9}
    )
    for at in autotexts:
        at.set_color("#f8fafc")
        at.set_fontsize(9)
    ax2.set_title("Classification Breakdown", color="#f8fafc", fontsize=10, pad=8)

    plt.tight_layout()
    chart_url = _fig_to_b64(fig)

    # Top 10 highest-probability candidates
    top_candidates = []
    sorted_idx = np.argsort(proba)[::-1][:10]
    for rank, idx in enumerate(sorted_idx):
        row_data = {c: _safe(float(valid_df.iloc[idx][c])) for c in HTRU2_CANONICAL}
        top_candidates.append({
            "rank": rank + 1,
            "row_index": int(valid_df.index[idx]),
            "pulsar_probability": round(float(proba[idx]), 4),
            "predicted_class": int(preds[idx]),
            "features": row_data,
        })

    return {
        "status": "COMPLETED",
        "summary": (
            f"ML inference complete on {n_total} rows ({skipped} skipped due to NaN). "
            f"Detected {n_pulsar} pulsar candidates ({pulsar_rate}% detection rate)."
        ),
        "details": {
            "inference_status": "COMPLETED",
            "total_rows_scored": n_total,
            "rows_skipped": skipped,
            "pulsar_candidates": n_pulsar,
            "noise_rfi": n_noise,
            "pulsar_rate_pct": pulsar_rate,
            "model_used": model_path.name,
            "feature_mapping": htru2_map,
            "chart_url": chart_url,
            "top_candidates": top_candidates,
        },
        "elapsed_seconds": round(time.time() - start, 3),
    }


# ── Dispatch ──────────────────────────────────────────────────
def execute_csv_analysis(file_path: Path, workflow_id: str) -> Dict[str, Any]:
    """Load CSV and dispatch to the requested workflow."""
    df = pd.read_csv(file_path)

    if workflow_id == "csv_statistics":
        return run_csv_statistics(df)
    elif workflow_id == "csv_correlation":
        return run_csv_correlation(df)
    elif workflow_id == "csv_pulsar_inference":
        return run_csv_pulsar_inference(df)
    else:
        return {
            "status": "HALTED",
            "summary": f"Unknown CSV workflow: '{workflow_id}'.",
            "details": {},
            "elapsed_seconds": 0.0,
        }
