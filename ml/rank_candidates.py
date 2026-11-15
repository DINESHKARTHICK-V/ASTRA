# ============================================================
#  ASTRA Cloud -- Step 28: Candidate Prioritization
#  File   : ml/rank_candidates.py
#  Purpose: Sorts radio observation candidates by their ACIS
#           score and assigns priority groups (HIGH / MEDIUM / LOW).
#           Priority groups indicate recommended inspection order
#           only — they are NOT scientific classification labels.
#  Input  : reports/acis_results.csv
#           reports/radio_predictions.csv
#  Output : reports/candidate_ranking.csv
# ============================================================

import sys
import io
import csv
from pathlib import Path

import pandas as pd

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT       = Path(__file__).resolve().parent.parent
REPORTS_DIR     = REPO_ROOT / "reports"
ACIS_CSV        = REPORTS_DIR / "acis_results.csv"
PREDICTIONS_CSV = REPORTS_DIR / "radio_predictions.csv"
RANKING_CSV     = REPORTS_DIR / "candidate_ranking.csv"

# ACIS priority thresholds (see ACIS_methodology.md)
HIGH_THRESHOLD   = 0.65
MEDIUM_THRESHOLD = 0.40

CSV_FIELDS = [
    "rank",
    "file_name",
    "prediction",
    "ml_probability",
    "acis_score",
    "priority_group",
    "evidence_available",
    "notes",
]


def _assign_priority(acis_score: float) -> str:
    if acis_score >= HIGH_THRESHOLD:
        return "HIGH"
    elif acis_score >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    else:
        return "LOW"


def rank_candidates() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 28: Candidate Prioritization")
    print("=" * 68)

    if not ACIS_CSV.exists():
        raise FileNotFoundError(f"ACIS results not found: {ACIS_CSV}")

    acis_df = pd.read_csv(ACIS_CSV)

    # Merge with prediction status
    pred_df = None
    if PREDICTIONS_CSV.exists():
        pred_df = pd.read_csv(PREDICTIONS_CSV)[["file_name", "prediction", "prediction_probability"]]

    if pred_df is not None:
        merged = acis_df.merge(pred_df, on="file_name", how="left")
    else:
        acis_df["prediction"] = "NOT_AVAILABLE"
        acis_df["prediction_probability"] = "NOT_AVAILABLE"
        merged = acis_df

    # Sort by ACIS score descending
    merged = merged.sort_values("acis_score", ascending=False).reset_index(drop=True)

    results = []
    for i, row in merged.iterrows():
        acis_score = float(row["acis_score"])
        priority   = _assign_priority(acis_score)
        ml_prob    = str(row.get("prediction_probability", "NOT_AVAILABLE"))
        prediction = str(row.get("prediction", "NOT_AVAILABLE"))
        ev_avail   = str(row.get("evidence_available", "NOT_AVAILABLE"))

        notes = (
            f"Priority '{priority}' means ASTRA recommends this candidate receive "
            f"rank #{i+1} in human inspection order. It does NOT indicate pulsar discovery."
        )

        results.append({
            "rank":              i + 1,
            "file_name":         row["file_name"],
            "prediction":        prediction,
            "ml_probability":    ml_prob,
            "acis_score":        f"{acis_score:.4f}",
            "priority_group":    priority,
            "evidence_available":ev_avail,
            "notes":             notes,
        })

        print(f"  Rank {i+1:2d} | ACIS={acis_score:.4f} | {priority:6s} | {prediction:20s} | {row['file_name']}")

    with open(RANKING_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(results)

    # Print priority group summary
    high_count   = sum(1 for r in results if r["priority_group"] == "HIGH")
    medium_count = sum(1 for r in results if r["priority_group"] == "MEDIUM")
    low_count    = sum(1 for r in results if r["priority_group"] == "LOW")

    print(f"\n  Priority Summary:")
    print(f"    HIGH   (ACIS >= {HIGH_THRESHOLD}): {high_count} observations")
    print(f"    MEDIUM (ACIS >= {MEDIUM_THRESHOLD}): {medium_count} observations")
    print(f"    LOW    (ACIS <  {MEDIUM_THRESHOLD}): {low_count} observations")
    print(f"\n[OK] Candidate ranking saved → {RANKING_CSV}")
    print("=" * 68)


if __name__ == "__main__":
    rank_candidates()
