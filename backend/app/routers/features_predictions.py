# ============================================================
#  ASTRA Cloud — Features & Predictions Router
#  File   : backend/app/routers/features_predictions.py
#  Purpose: Read-only endpoints for extracted scientific features
#           and machine learning inference records.
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.database import get_db
from backend.app.models import Observation, Feature, Prediction
from backend.app.schemas import FeatureResponse, PredictionResponse

router = APIRouter(prefix="/api/observations", tags=["Features & Predictions"])


@router.get(
    "/{observation_id}/features",
    response_model=Optional[FeatureResponse],
    summary="Get observation scientific features",
    description="Retrieve all extracted scientific features (profile moments, DM parameters, RFI, noise) for an observation."
)
def get_observation_features(
    observation_id: int,
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation with ID {observation_id} was not found."
        )

    feature = db.query(Feature).filter(Feature.observation_id == observation_id).first()
    return feature


@router.get(
    "/{observation_id}/predictions",
    response_model=List[PredictionResponse],
    summary="Get observation ML predictions",
    description="Retrieve all machine learning predictions, probability estimates, and inference statuses for an observation."
)
def get_observation_predictions(
    observation_id: int,
    db: Session = Depends(get_db),
):
    obs = db.query(Observation).filter(Observation.id == observation_id).first()
    if not obs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation with ID {observation_id} was not found."
        )

    preds = (
        db.query(Prediction)
        .filter(Prediction.observation_id == observation_id)
        .order_by(Prediction.id.asc())
        .all()
    )
    return preds
