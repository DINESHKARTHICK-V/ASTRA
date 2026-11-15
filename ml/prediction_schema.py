# ============================================================
#  ASTRA Cloud -- Candidate Prediction Schema
#  File   : ml/prediction_schema.py
#  Purpose: Standard dictionary structure and factory functions
#           for ASTRA pulsar candidate prediction results.
#           (Decoupled from PostgreSQL and backend storage).
# ============================================================

import sys
import io
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, TypedDict

# UTF-8 output for Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass



class CandidatePredictionSchema(TypedDict):
    """Standard TypedDict structure for a candidate prediction record."""
    candidate_id: str
    source_file: str
    predicted_class: int
    pulsar_probability: float
    non_pulsar_probability: float
    model_name: str
    model_version: str
    prediction_timestamp: str


REQUIRED_SCHEMA_KEYS = {
    "candidate_id",
    "source_file",
    "predicted_class",
    "pulsar_probability",
    "non_pulsar_probability",
    "model_name",
    "model_version",
    "prediction_timestamp",
}


def create_candidate_result(
    predicted_class: int,
    pulsar_probability: float,
    non_pulsar_probability: float,
    source_file: str = "unknown",
    candidate_id: Optional[str] = None,
    model_name: str = "random_forest_pipeline",
    model_version: str = "1.0.0",
    prediction_timestamp: Optional[str] = None,
) -> dict:
    """
    Construct a standard ASTRA candidate prediction result dictionary.

    Parameters
    ----------
    predicted_class : int
        Binary classification (1 for pulsar candidate, 0 for non-pulsar).
    pulsar_probability : float
        Posterior probability of being a pulsar, P(pulsar).
    non_pulsar_probability : float
        Posterior probability of being non-pulsar, P(non-pulsar).
    source_file : str, optional
        Name or path of the source observation file (e.g. FITS or CSV).
    candidate_id : str, optional
        Unique candidate identifier. If None, a UUID4 string is generated.
    model_name : str, optional
        Name of the classifier model used.
    model_version : str, optional
        Version string of the classifier.
    prediction_timestamp : str, optional
        ISO 8601 formatted timestamp string in UTC. If None, current UTC time is used.

    Returns
    -------
    dict
        Dictionary containing all 8 standard candidate result fields.
    """
    if candidate_id is None:
        candidate_id = f"cand_{uuid.uuid4().hex[:12]}"

    if prediction_timestamp is None:
        prediction_timestamp = datetime.now(timezone.utc).isoformat()

    result: dict = {
        "candidate_id": str(candidate_id),
        "source_file": str(source_file),
        "predicted_class": int(predicted_class),
        "pulsar_probability": round(float(pulsar_probability), 6),
        "non_pulsar_probability": round(float(non_pulsar_probability), 6),
        "model_name": str(model_name),
        "model_version": str(model_version),
        "prediction_timestamp": str(prediction_timestamp),
    }

    return result


def create_result_from_prediction(
    prediction: Mapping[str, Any],
    source_file: str = "unknown",
    candidate_id: Optional[str] = None,
    model_name: str = "random_forest_pipeline",
    model_version: str = "1.0.0",
) -> dict:
    """
    Convenience builder: creates a standard candidate result from a
    prediction object (such as the PredictionResult from ml.predict).
    """
    predicted_class = prediction["predicted_class"]
    pulsar_prob = prediction["pulsar_probability"]
    non_pulsar_prob = prediction["non_pulsar_probability"]

    return create_candidate_result(
        predicted_class=predicted_class,
        pulsar_probability=pulsar_prob,
        non_pulsar_probability=non_pulsar_prob,
        source_file=source_file,
        candidate_id=candidate_id,
        model_name=model_name,
        model_version=model_version,
    )


def validate_candidate_result(result: Mapping[str, Any]) -> bool:
    """
    Validate that a dictionary contains all required fields of the
    standard ASTRA prediction schema.
    """
    missing = REQUIRED_SCHEMA_KEYS - set(result.keys())
    if missing:
        raise ValueError(f"Candidate result is missing required schema keys: {sorted(missing)}")
    return True


# ------------------------------------------------------------------
# Self-test Demonstration
# ------------------------------------------------------------------
def _demo() -> None:
    print("=" * 65)
    print("  ASTRA Cloud -- Prediction Schema Demonstration")
    print("=" * 65)

    # 1. Direct creation
    sample_result = create_candidate_result(
        predicted_class=1,
        pulsar_probability=0.942150,
        non_pulsar_probability=0.057850,
        source_file="HTRU_2.csv:row_19",
        model_name="random_forest_pipeline",
        model_version="1.0.0",
    )

    print("\nCreated Standard Candidate Result Dictionary:\n")
    for k, v in sample_result.items():
        print(f"  {k:<24}: {v}")

    # 2. Validation check
    is_valid = validate_candidate_result(sample_result)
    print(f"\nSchema validation check: {'PASSED ✓' if is_valid else 'FAILED ✗'}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    _demo()
