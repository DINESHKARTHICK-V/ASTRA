# ============================================================
#  ASTRA Cloud -- Pulsar Candidate Inference Module
#  File   : ml/predict.py
#  Purpose: Run inference on pulsar candidates using the trained
#           Random Forest model (models/random_forest_pipeline.pkl).
#           Validates that all 8 HTRU2 features are present.
# ============================================================

import sys
import io
import pickle
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

# UTF-8 output formatting for Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ------------------------------------------------------------------
# Paths and Expected Features
# ------------------------------------------------------------------
REPO_ROOT   = Path(__file__).resolve().parent.parent
MODEL_PATH  = REPO_ROOT / "models" / "random_forest_pipeline.pkl"
DATA_PATH   = REPO_ROOT / "data" / "htru2" / "HTRU_2.csv"

REQUIRED_FEATURES = [
    "Profile_Mean",
    "Profile_Std",
    "Profile_Skewness",
    "Profile_Kurtosis",
    "DM_Mean",
    "DM_Std",
    "DM_Skewness",
    "DM_Kurtosis",
]


class PredictionResult(dict):
    """
    Result container that supports:
      - Tuple unpacking:  `pred_class, non_pulsar_prob, pulsar_prob = result`
      - Dictionary keys:  `result["predicted_class"]`
      - Attributes:       `result.predicted_class`
    """
    def __init__(self, predicted_class: int, non_pulsar_probability: float, pulsar_probability: float):
        super().__init__(
            predicted_class=predicted_class,
            non_pulsar_probability=non_pulsar_probability,
            pulsar_probability=pulsar_probability,
        )
        self.predicted_class = predicted_class
        self.non_pulsar_probability = non_pulsar_probability
        self.pulsar_probability = pulsar_probability

    def __iter__(self):
        yield self["predicted_class"]
        yield self["non_pulsar_probability"]
        yield self["pulsar_probability"]

    def __repr__(self) -> str:
        return (
            f"PredictionResult("
            f"predicted_class={self.predicted_class}, "
            f"non_pulsar_probability={self.non_pulsar_probability:.6f}, "
            f"pulsar_probability={self.pulsar_probability:.6f})"
        )


# Global model cache to avoid repeated disk reads
_CACHED_MODEL = None


def load_pipeline_model(model_path: Path | str | None = None):
    """Load the trained RandomForestClassifier without retraining or modifying it."""
    global _CACHED_MODEL
    target_path = Path(model_path) if model_path else MODEL_PATH

    if _CACHED_MODEL is None or model_path is not None:
        if not target_path.exists():
            raise FileNotFoundError(
                f"Trained model not found at {target_path}. "
                "Please run ml/train_pipeline.py first."
            )
        with open(target_path, "rb") as f:
            model = pickle.load(f)
        if model_path is None:
            _CACHED_MODEL = model
        return model

    return _CACHED_MODEL


def validate_features(features: Any) -> pd.DataFrame:
    """
    Validate that the input contains exactly the 8 expected HTRU2 features.
    Raises ValueError on missing or incorrectly named features.
    Raises TypeError if input is not a mapping/DataFrame/Series.
    """
    if isinstance(features, Mapping):
        keys = set(features.keys())
        expected = set(REQUIRED_FEATURES)
        missing = expected - keys
        extra = keys - expected

        errors = []
        if missing:
            errors.append(f"Missing required feature(s): {sorted(missing)}")
        if extra:
            errors.append(f"Incorrect/unrecognized feature(s): {sorted(extra)}")

        if errors:
            raise ValueError(
                "Invalid features provided.\n  " + "\n  ".join(errors) +
                f"\n  Expected exactly these 8 features: {REQUIRED_FEATURES}"
            )

        # Extract values in the exact expected feature order
        row_values = []
        for feat in REQUIRED_FEATURES:
            val = features[feat]
            try:
                numeric_val = float(val)
                if np.isnan(numeric_val) or np.isinf(numeric_val):
                    raise ValueError(f"Feature '{feat}' must be a finite real number, got {val}")
                row_values.append(numeric_val)
            except (TypeError, ValueError) as err:
                raise ValueError(f"Invalid non-numeric value for feature '{feat}': {val!r}") from err

        return pd.DataFrame([row_values], columns=REQUIRED_FEATURES)

    elif isinstance(features, pd.DataFrame):
        missing = set(REQUIRED_FEATURES) - set(features.columns)
        extra = set(features.columns) - set(REQUIRED_FEATURES)
        errors = []
        if missing:
            errors.append(f"Missing required column(s): {sorted(missing)}")
        if extra:
            errors.append(f"Incorrect/unrecognized column(s): {sorted(extra)}")
        if errors:
            raise ValueError(
                "Invalid DataFrame columns.\n  " + "\n  ".join(errors) +
                f"\n  Expected exactly these 8 columns: {REQUIRED_FEATURES}"
            )
        return features[REQUIRED_FEATURES].astype(float)

    elif isinstance(features, pd.Series):
        return validate_features(features.to_dict())

    else:
        raise TypeError(
            f"Unsupported type for 'features': {type(features).__name__}. "
            f"Must be a dict, pandas Series, or pandas DataFrame with keys: {REQUIRED_FEATURES}"
        )


def predict_candidate(features: Mapping[str, Any] | pd.DataFrame | pd.Series) -> PredictionResult:
    """
    Predict whether a candidate is a pulsar or non-pulsar.

    Parameters
    ----------
    features : Mapping or DataFrame containing exactly the 8 HTRU2 features:
               Profile_Mean, Profile_Std, Profile_Skewness, Profile_Kurtosis,
               DM_Mean, DM_Std, DM_Skewness, DM_Kurtosis.

    Returns
    -------
    PredictionResult
        Unpackable as:
        predicted_class, non_pulsar_probability, pulsar_probability
    """
    # ── 1. Validate features ──────────────────────────────────────
    X = validate_features(features)

    # ── 2. Load model (read-only, cached) ─────────────────────────
    model = load_pipeline_model()

    # ── 3. Run inference ──────────────────────────────────────────
    pred = model.predict(X)[0]
    probabilities = model.predict_proba(X)[0]
    non_pulsar_prob = float(probabilities[0])
    pulsar_prob = float(probabilities[1])

    return PredictionResult(
        predicted_class=int(pred),
        non_pulsar_probability=non_pulsar_prob,
        pulsar_probability=pulsar_prob,
    )


# ------------------------------------------------------------------
# Test Routine
# ------------------------------------------------------------------
def test_pipeline() -> None:
    print("=" * 65)
    print("  ASTRA Cloud -- Testing Candidate Prediction")
    print("=" * 65)

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"HTRU2 dataset not found at: {DATA_PATH}")

    # Load first row from HTRU2 dataset
    raw_df = pd.read_csv(DATA_PATH, header=None, nrows=2)
    sample_values = raw_df.iloc[0, :8].tolist()
    sample_true_label = int(raw_df.iloc[0, 8])

    candidate_dict = dict(zip(REQUIRED_FEATURES, sample_values))

    print("\n[Test 1] Candidate features loaded from HTRU_2.csv (Row 0):")
    for k, v in candidate_dict.items():
        print(f"  {k:<18}: {v:.6f}")
    print(f"  True Label (HTRU2): {sample_true_label} ({'Pulsar' if sample_true_label == 1 else 'Non-Pulsar'})")

    # Run prediction
    result = predict_candidate(candidate_dict)

    # Demonstration of tuple unpacking
    predicted_class, non_pulsar_prob, pulsar_prob = result

    print("\n[Prediction Results]")
    print(f"  Predicted Class        : {predicted_class} ({'PULSAR' if predicted_class == 1 else 'NON-PULSAR'})")
    print(f"  Non-Pulsar Probability : {non_pulsar_prob:.6f}")
    print(f"  Pulsar Probability     : {pulsar_prob:.6f}")

    # Demonstration of validation error handling
    print("\n[Test 2] Testing validation with missing/incorrect feature names:")
    invalid_candidate = candidate_dict.copy()
    del invalid_candidate["Profile_Mean"]
    invalid_candidate["Wrong_Feature_Name"] = 42.0

    try:
        predict_candidate(invalid_candidate)
    except ValueError as exc:
        print("  Successfully caught expected error:")
        for line in str(exc).split("\n"):
            print(f"    {line}")

    print("\n" + "=" * 65)
    print("  Test completed successfully.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    test_pipeline()
