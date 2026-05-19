#!/usr/bin/env python3
"""
Train XGBoost model using realistic Kansas Rift training data
Saves trained model for pipeline use
"""

import logging
import csv
import numpy as np
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ml.xgboost_model import ProspectivityModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "local_storage" / "datasets"

def load_training_data():
    """Load training data from CSV"""
    training_file = DATA_DIR / "training_data.csv"

    if not training_file.exists():
        logger.error(f"Training data not found: {training_file}")
        return None, None

    X = []
    y = []

    with open(training_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            features = [
                float(row["fault_density_score"]),
                float(row["ultramafic_fraction"]),
                float(row["gravity_gradient_score"]),
                float(row["magnetic_gradient_score"]),
                float(row["heatflow_score"]),
                float(row["structural_complexity_score"]),
                float(row["seep_proximity_score"]),
                float(row["basin_presence_score"]),
                float(row["caprock_proxy_score"]),
            ]
            X.append(features)
            y.append(float(row["prospectivity_label"]))

    return np.array(X), np.array(y)

def main():
    logger.info("")
    logger.info("=" * 80)
    logger.info("XGBOOST MODEL TRAINING")
    logger.info("=" * 80)
    logger.info("")

    # Load training data
    logger.info(f"Loading training data from: {DATA_DIR / 'training_data.csv'}")
    X_train, y_train = load_training_data()

    if X_train is None:
        logger.error("Failed to load training data")
        return False

    logger.info(f"✅ Loaded {len(X_train)} training samples")
    logger.info(f"   Features: {X_train.shape[1]}")
    logger.info(f"   Target range: [{y_train.min():.3f}, {y_train.max():.3f}]")
    logger.info("")

    # Initialize model
    logger.info("Initializing XGBoost model...")
    model = ProspectivityModel()

    # Train with labeled data
    logger.info("Training XGBoost ensemble...")
    success = model.retrain_with_labeled_data(X_train, y_train)

    if not success:
        logger.error("Model training failed")
        return False

    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ MODEL TRAINING COMPLETE")
    logger.info("=" * 80)
    logger.info("")

    # Show feature importances
    importances = model.get_feature_importance()
    logger.info("Feature Importances:")
    for feature, importance in sorted(importances.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {feature:35s}: {importance:.4f}")

    logger.info("")
    from app.services.ml.xgboost_model import MODEL_PATH, SCALER_PATH
    logger.info(f"Model saved to: {MODEL_PATH}")
    logger.info(f"Scaler saved to: {SCALER_PATH}")
    logger.info("")
    logger.info("Ready for pipeline execution!")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
