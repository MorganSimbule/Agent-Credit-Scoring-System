#!/usr/bin/env python3
"""
train_export.py — Train both binary (default) and multiclass (risk) models,
compute metrics, and export metadata for API consumption.

Usage:
    python train_export.py

Environment:
    DB_PASSWORD — database password (if using database to fetch training data)
    DB_USER, DB_HOST, DB_PORT, DB_NAME — database connection details
"""

import json
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
DATA_PATH = "data/training_data.csv"  # adjust if your data is elsewhere
MODELS_DIR = Path("models")
METADATA_FILE = MODELS_DIR / "metadata.json"

FEATURE_COLUMNS = [
    "LoanCount",
    "AvgLoan",
    "TransactionFrequency",
    "AverageTransactionValue",
    "AuditActivity",
    "Occupation",
]

CATEGORICAL_COLS = ["Occupation"]
NUMERIC_COLS = [
    "LoanCount",
    "AvgLoan",
    "TransactionFrequency",
    "AverageTransactionValue",
    "AuditActivity",
]


def load_training_data() -> pd.DataFrame:
    """Load training dataset from CSV or database."""
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Training data not found at {DATA_PATH}. "
            "Please provide a CSV file with columns: "
            f"{', '.join(FEATURE_COLUMNS + ['default_flag', 'risk_category'])}"
        )
    
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} rows from {DATA_PATH}")
    return df


def build_pipeline():
    """Build sklearn pipeline with preprocessing and model."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_COLS),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS),
        ]
    )
    
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("model", RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)),
    ])
    
    return pipeline


def compute_metrics(y_true, y_pred, y_pred_proba=None) -> dict:
    """Compute classification metrics."""
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
    }
    
    if y_pred_proba is not None and len(set(y_true)) > 1:
        try:
            if y_pred_proba.ndim == 1:
                metrics["roc_auc"] = float(roc_auc_score(y_true, y_pred_proba))
            else:
                # Multiclass: compute one-vs-rest AUC
                metrics["roc_auc"] = float(roc_auc_score(y_true, y_pred_proba, multi_class="ovr", average="weighted"))
        except Exception as e:
            print(f"Warning: Could not compute ROC-AUC: {e}")
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    metrics["confusion_matrix"] = cm.tolist()
    
    return metrics


def train_binary_model(X_train, X_test, y_train, y_test):
    """Train binary default prediction model."""
    print("\n[BINARY] Training default prediction model...")
    
    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)
    
    y_pred = pipeline.predict(X_test)
    y_pred_proba = pipeline.predict_proba(X_test)
    
    metrics = compute_metrics(y_test, y_pred, y_pred_proba[:, 1])
    
    print(f"[BINARY] Accuracy: {metrics['accuracy']:.4f}")
    print(f"[BINARY] F1-Score: {metrics['f1']:.4f}")
    
    return pipeline, metrics


def train_multiclass_model(X_train, X_test, y_train, y_test):
    """Train multiclass risk category model."""
    print("\n[MULTICLASS] Training risk category model...")
    
    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)
    
    y_pred = pipeline.predict(X_test)
    y_pred_proba = pipeline.predict_proba(X_test)
    
    metrics = compute_metrics(y_test, y_pred, y_pred_proba)
    
    print(f"[MULTICLASS] Accuracy: {metrics['accuracy']:.4f}")
    print(f"[MULTICLASS] F1-Score: {metrics['f1']:.4f}")
    
    return pipeline, metrics


def main():
    """Main training and export pipeline."""
    print("=" * 70)
    print("Credit Scoring Model Training & Export")
    print("=" * 70)
    
    # Load data
    ds = load_training_data()
    
    # Validate required columns
    required_cols = FEATURE_COLUMNS + ["default_flag", "risk_category"]
    missing = set(required_cols) - set(ds.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    X = ds[FEATURE_COLUMNS]
    y_binary = ds["default_flag"]
    y_multiclass = ds["risk_category"]
    
    # Train/test split
    X_train, X_test, y_bin_train, y_bin_test, y_multi_train, y_multi_test = train_test_split(
        X, y_binary, y_multiclass, test_size=0.2, random_state=42
    )
    
    # Create models directory
    MODELS_DIR.mkdir(exist_ok=True)
    
    # Train binary model
    bin_pipeline, bin_metrics = train_binary_model(X_train, X_test, y_bin_train, y_bin_test)
    bin_name = "binary_default_pipeline(1).joblib"
    bin_path = MODELS_DIR / bin_name
    joblib.dump(bin_pipeline, bin_path)
    print(f"✓ Saved binary model to {bin_path}")
    
    # Train multiclass model
    multi_pipeline, multi_metrics = train_multiclass_model(X_train, X_test, y_multi_train, y_multi_test)
    multi_name = "multiclass_risk_pipeline(1).joblib"
    multi_path = MODELS_DIR / multi_name
    joblib.dump(multi_pipeline, multi_path)
    print(f"✓ Saved multiclass model to {multi_path}")
    
    # Build metadata with feature baseline
    metadata = {
        "binary_model_name": bin_name,
        "multiclass_model_name": multi_name,
        "binary_metrics": bin_metrics,
        "multiclass_metrics": multi_metrics,
        "occupations": sorted(ds["Occupation"].unique().tolist()),
        "feature_baseline": {
            col: {
                "mean": float(X_train[col].mean()),
                "std": float(X_train[col].std() or 1.0)
            }
            for col in NUMERIC_COLS
        },
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Save metadata
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Saved metadata to {METADATA_FILE}")
    
    print("\n" + "=" * 70)
    print("Training complete!")
    print("=" * 70)
    print(f"\nMetadata:\n{json.dumps(metadata, indent=2)}\n")
    
    return metadata


if __name__ == "__main__":
    main()