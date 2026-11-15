# ============================================================
#  ASTRA Cloud -- Step 27: ASTRA Candidate Intelligence Score
#  File   : ml/acis.py
#  Purpose: Computes the ASTRA Candidate Intelligence Score (ACIS)
#           for each radio observation using all available physical
#           evidence channels. Missing evidence is handled by
#           proportional weight redistribution. Values are never
#           silently substituted with zero.
#  Input  : reports/candidate_evidence.csv
#  Output : reports/acis_results.csv
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

REPO_ROOT      = Path(__file__).resolve().parent.parent
REPORTS_DIR    = REPO_ROOT / "reports"
EVIDENCE_CSV   = REPORTS_DIR / "candidate_evidence.csv"
ACIS_CSV       = REPORTS_DIR / "acis_results.csv"

# ---------------------------------------------------------------
# Configurable weight table (must sum to 1.0)
# Weights reflect documented scientific priority per channel.
# ---------------------------------------------------------------
DEFAULT_WEIGHTS = {
    "ml_probability":      0.35,
    "signal_quality":      0.20,
    "rfi_indicator":       0.15,
    "periodicity_evidence":0.10,
    "dm_evidence":         0.10,
    "profile_evidence":    0.10,
}

CSV_FIELDS = [
    "file_name",
    "ml_probability",
    "signal_quality",
    "rfi_indicator",
    "periodicity_evidence",
    "dm_evidence",
    "profile_evidence",
    "acis_score",
    "evidence_available",
    "score_status",
    "notes",
]


def _normalize_evidence(channel_name: str, value: str, availability: str) -> float | None:
    """
    Convert raw evidence value to a normalised score in [0, 1].
    Returns None if evidence is genuinely unavailable.
    """
    val = str(value).strip()
    avail = str(availability).strip().upper()

    if avail == "NO" or val in ("NOT_AVAILABLE", "INCOMPATIBLE_DATA (Inference Halted)"):
        return None  # Genuinely unavailable

    if channel_name == "ml_probability":
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    if channel_name == "signal_quality":
        if "VALID" in val.upper():
            return 1.0
        if "BLANK" in val.upper():
            return 0.0
        return 0.5  # PARTIAL or UNKNOWN

    if channel_name == "rfi_indicator":
        try:
            return 1.0 - float(val)  # Lower RFI → higher score
        except (ValueError, TypeError):
            return None

    if channel_name == "periodicity_evidence":
        if avail == "PARTIAL" and "EPHEMERIS" in val.upper():
            return 0.70  # Known period from ephemeris — partial credit
        if avail == "YES":
            return 1.0
        return 0.0

    if channel_name == "dm_evidence":
        if "NOT_AVAILABLE" in val.upper():
            return None
        if "NOMINAL" in val.upper() or "DM=" in val.upper():
            return 0.70  # Known DM from ephemeris — partial credit
        if avail == "PARTIAL":
            return 0.50
        return 0.0

    if channel_name == "profile_evidence":
        if "BLANK" in val.upper():
            return 0.0
        if "VALID_PROFILE" in val.upper():
            # Extract skewness and kurtosis for scoring
            try:
                import re
                skew_match = re.search(r"skewness=([-\d.]+)", val)
                kurt_match = re.search(r"kurtosis=([-\d.]+)", val)
                skew = float(skew_match.group(1)) if skew_match else 0.0
                kurt = float(kurt_match.group(1)) if kurt_match else 0.0
                # Pulsar profiles tend to have low skewness and low/moderate kurtosis
                # Score based on proximity to "pulse-like" profile shape
                skew_score = max(0.0, 1.0 - abs(skew) / 2.0)
                kurt_score = max(0.0, 1.0 - abs(kurt) / 5.0)
                return round((skew_score + kurt_score) / 2.0, 4)
            except Exception:
                return 0.60  # Fallback: valid profile but cannot parse details
        return 0.0

    return None  # Unknown channel


def compute_acis() -> None:
    print("=" * 68)
    print("  ASTRA Cloud -- Step 27: Compute ACIS Scores")
    print("=" * 68)

    if not EVIDENCE_CSV.exists():
        raise FileNotFoundError(f"Candidate evidence file not found: {EVIDENCE_CSV}")

    ev_df = pd.read_csv(EVIDENCE_CSV)

    # Pivot evidence table: file_name → channel → {value, availability}
    files = ev_df["file_name"].unique()
    ev_lookup = {}
    for _, row in ev_df.iterrows():
        fn = row["file_name"]
        ch = row["evidence_name"]
        if fn not in ev_lookup:
            ev_lookup[fn] = {}
        ev_lookup[fn][ch] = {"value": row["value"], "availability": row["availability"]}

    results = []

    for fn in files:
        channels = ev_lookup.get(fn, {})
        channel_scores = {}
        channel_avail  = {}

        for ch, w in DEFAULT_WEIGHTS.items():
            entry = channels.get(ch, {})
            raw_val  = entry.get("value", "NOT_AVAILABLE")
            raw_avail = entry.get("availability", "NO")
            score = _normalize_evidence(ch, raw_val, raw_avail)
            channel_scores[ch] = score
            channel_avail[ch]  = score is not None

        # Compute renormalized weights for available channels
        available_channels = [ch for ch, ok in channel_avail.items() if ok]
        total_available_weight = sum(DEFAULT_WEIGHTS[ch] for ch in available_channels)

        if total_available_weight == 0.0:
            acis_score = 0.0
            score_status = "NO_EVIDENCE_AVAILABLE"
            notes = "No evidence channel returned a computable value."
        else:
            acis_score = 0.0
            for ch in available_channels:
                renorm_w = DEFAULT_WEIGHTS[ch] / total_available_weight
                acis_score += renorm_w * channel_scores[ch]
            acis_score = round(acis_score, 4)
            score_status = "PARTIAL_EVIDENCE" if len(available_channels) < len(DEFAULT_WEIGHTS) else "FULL_EVIDENCE"
            notes = (
                f"ACIS computed from {len(available_channels)}/{len(DEFAULT_WEIGHTS)} evidence channels. "
                f"Unavailable: {[ch for ch, ok in channel_avail.items() if not ok]}. "
                f"Weights renormalized to sum to 1.0."
            )

        # Build result row
        row_data = {
            "file_name":            fn,
            "ml_probability":       channel_scores.get("ml_probability") if channel_avail.get("ml_probability") else "NOT_AVAILABLE",
            "signal_quality":       round(channel_scores.get("signal_quality", 0.0), 4) if channel_avail.get("signal_quality") else "NOT_AVAILABLE",
            "rfi_indicator":        round(channel_scores.get("rfi_indicator", 0.0), 4) if channel_avail.get("rfi_indicator") else "NOT_AVAILABLE",
            "periodicity_evidence": round(channel_scores.get("periodicity_evidence", 0.0), 4) if channel_avail.get("periodicity_evidence") else "NOT_AVAILABLE",
            "dm_evidence":          round(channel_scores.get("dm_evidence", 0.0), 4) if channel_avail.get("dm_evidence") else "NOT_AVAILABLE",
            "profile_evidence":     round(channel_scores.get("profile_evidence", 0.0), 4) if channel_avail.get("profile_evidence") else "NOT_AVAILABLE",
            "acis_score":           acis_score,
            "evidence_available":   f"{len(available_channels)}/{len(DEFAULT_WEIGHTS)}",
            "score_status":         score_status,
            "notes":                notes,
        }
        results.append(row_data)

        print(f"[{fn}]")
        print(f"  ACIS Score: {acis_score:.4f}  |  Evidence: {len(available_channels)}/{len(DEFAULT_WEIGHTS)}  |  {score_status}")

    with open(ACIS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[OK] ACIS results saved → {ACIS_CSV}")
    print(f"  Total candidates scored: {len(results)}")
    print("=" * 68)


if __name__ == "__main__":
    compute_acis()
