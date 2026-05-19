"""
XGBoost ML Model for Prospectivity Scoring
Trains and loads XGBoost ensemble for hydrogen prospectivity prediction
"""

import logging
import pickle
from pathlib import Path
from typing import Optional
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "prospectivity_xgboost_v1.pkl"
SCALER_PATH = MODEL_DIR / "feature_scaler.pkl"


class ProspectivityModel:
    """XGBoost model for hydrogen prospectivity scoring"""

    def __init__(self):
        self.model: Optional[xgb.XGBRegressor] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names = [
            "fault_density_score",
            "ultramafic_fraction",
            "gravity_gradient_score",
            "magnetic_gradient_score",
            "heatflow_score",
            "structural_complexity_score",
            "seep_proximity_score",
            "basin_presence_score",
            "caprock_proxy_score",
        ]
        self.is_trained = False

    def load_or_train(self, force_train: bool = False) -> bool:
        """
        Load pre-trained model or train from scratch if needed.

        Args:
            force_train: If True, always retrain the model

        Returns:
            True if model loaded/trained successfully
        """
        if not force_train and MODEL_PATH.exists():
            return self.load()

        logger.warning("No pre-trained model found. Training from synthetic data...")
        return self.train_from_synthetic()

    def load(self) -> bool:
        """Load pre-trained model from disk"""
        try:
            if not MODEL_PATH.exists():
                logger.error(f"Model file not found: {MODEL_PATH}")
                return False

            self.model = joblib.load(MODEL_PATH)
            self.scaler = joblib.load(SCALER_PATH)
            self.is_trained = True

            logger.info(f"✅ Loaded XGBoost model from {MODEL_PATH}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def train_from_synthetic(self, n_samples: int = 100) -> bool:
        """
        Train model from synthetic data (for demo/testing).
        In production, this would use labeled training data.

        Args:
            n_samples: Number of synthetic samples to generate

        Returns:
            True if training successful
        """
        try:
            logger.info(f"Training XGBoost model from {n_samples} synthetic samples...")

            # Generate synthetic training data
            X_train = np.random.rand(n_samples, len(self.feature_names)) * 100
            # Target: high prospectivity where certain features are high
            y_train = (
                X_train[:, 0] * 0.25  # fault_density_score weight
                + X_train[:, 1] * 0.15  # ultramafic_fraction weight
                + X_train[:, 3] * 0.20  # magnetic_gradient_score weight
                + X_train[:, 4] * 0.15  # heatflow_score weight
                + X_train[:, 5] * 0.15  # structural_complexity_score weight
                + np.random.normal(0, 5, n_samples)  # noise
            ) / 100

            # Normalize
            y_train = np.clip(y_train, 0, 1)

            # Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)

            # Train XGBoost
            self.model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                objective="reg:squarederror",
                random_state=42,
                verbosity=0,
            )

            self.model.fit(X_train_scaled, y_train)

            # Save model
            joblib.dump(self.model, MODEL_PATH)
            joblib.dump(self.scaler, SCALER_PATH)

            self.is_trained = True
            logger.info(f"✅ Trained and saved XGBoost model to {MODEL_PATH}")

            # Log feature importances
            importances = self.model.feature_importances_
            for name, imp in zip(self.feature_names, importances):
                logger.info(f"   {name}: {imp:.4f}")

            return True
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False

    def predict(self, features: dict) -> Optional[float]:
        """
        Predict prospectivity score for a set of features.

        Args:
            features: Dict with keys matching self.feature_names

        Returns:
            Predicted score [0, 1] or None if model not available
        """
        if not self.is_trained or self.model is None:
            logger.warning("Model not trained. Cannot predict.")
            return None

        try:
            # Extract features in correct order
            X = np.array(
                [features.get(name, 0.5) for name in self.feature_names]
            ).reshape(1, -1)

            # Scale
            X_scaled = self.scaler.transform(X)

            # Predict
            y_pred = self.model.predict(X_scaled)[0]

            # Clamp to [0, 1]
            return float(np.clip(y_pred, 0, 1))
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return None

    def get_feature_importance(self) -> dict:
        """
        Get feature importances from the trained model.

        Returns:
            Dict mapping feature names to importance scores
        """
        if not self.is_trained or self.model is None:
            return {}

        importances = self.model.feature_importances_
        return {name: float(imp) for name, imp in zip(self.feature_names, importances)}

    def retrain_with_labeled_data(self, X_train, y_train):
        """
        Retrain model with real labeled training data.

        Args:
            X_train: Training features (n_samples, n_features)
            y_train: Training targets (n_samples,)

        Returns:
            True if training successful
        """
        try:
            logger.info(f"Retraining with {len(X_train)} labeled samples...")

            # Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)

            # Train
            self.model = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=7,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                objective="reg:squarederror",
                random_state=42,
            )

            self.model.fit(X_train_scaled, y_train)

            # Save
            joblib.dump(self.model, MODEL_PATH)
            joblib.dump(self.scaler, SCALER_PATH)

            self.is_trained = True
            logger.info("✅ Model retrained and saved")
            return True
        except Exception as e:
            logger.error(f"Retraining failed: {e}")
            return False


# Global model instance
_model_instance: Optional[ProspectivityModel] = None


def get_model() -> ProspectivityModel:
    """Get or initialize the global model instance"""
    global _model_instance
    if _model_instance is None:
        _model_instance = ProspectivityModel()
        _model_instance.load_or_train()
    return _model_instance
