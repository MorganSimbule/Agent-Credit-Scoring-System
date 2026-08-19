#!/usr/bin/env python3
"""
generate_training_data.py — Generate synthetic training data for model development.
Creates realistic correlations between features and both binary (default) and multiclass (risk) targets.
"""

import numpy as np
import pandas as pd
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)

# Configuration
N_SAMPLES = 1000
OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "training_data.csv"

# Feature ranges
OCCUPATIONS = ["Trader", "Farmer", "Vendor", "Driver", "Unspecified"]

def generate_training_data(n_samples: int) -> pd.DataFrame:
    """
    Generate synthetic credit scoring training data with realistic correlations.
    """
    data = {
        "LoanCount": np.random.randint(0, 101, n_samples),
        "AvgLoan": np.random.exponential(scale=50000, size=n_samples).clip(0, 500000),
        "TransactionFrequency": np.random.exponential(scale=50, size=n_samples).clip(0, 500),
        "AverageTransactionValue": np.random.exponential(scale=10000, size=n_samples).clip(0, 100000),
        "AuditActivity": np.random.randint(0, 100, n_samples),
        "Occupation": np.random.choice(OCCUPATIONS, n_samples),
    }
    
    df = pd.DataFrame(data)
    
    # Generate targets with realistic correlations
    # Higher loan count, higher avg loan, lower transaction frequency -> higher default risk
    default_risk = (
        (df["LoanCount"] / 100) * 0.3 +
        (df["AvgLoan"] / 500000) * 0.3 +
        (1 - df["TransactionFrequency"] / 500) * 0.2 +
        (df["AuditActivity"] / 100) * 0.2 +
        np.random.normal(0, 0.1, n_samples)  # Noise
    ).clip(0, 1)
    
    # Binary default flag (0 = no default, 1 = default)
    df["default_flag"] = (default_risk > 0.5).astype(int)
    
    # Risk category (0 = LOW, 1 = MEDIUM, 2 = HIGH, 3 = VERY HIGH)
    # Based on similar logic to default_risk
    df["risk_category"] = pd.cut(
        default_risk,
        bins=[0, 0.25, 0.5, 0.75, 1.0],
        labels=[0, 1, 2, 3],
        include_lowest=True,
    ).astype(int)
    
    return df


def main():
    """Generate and save training data."""
    print(f"Generating {N_SAMPLES} synthetic training samples...")
    
    # Generate data
    df = generate_training_data(N_SAMPLES)
    
    # Create data directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Save CSV
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✓ Saved training data to {OUTPUT_FILE}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("Training Data Summary")
    print("=" * 70)
    print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"\nColumns:\n{df.dtypes}")
    print(f"\nFirst 5 rows:\n{df.head()}")
    print(f"\nDefault flag distribution:\n{df['default_flag'].value_counts()}")
    print(f"\nRisk category distribution:\n{df['risk_category'].value_counts().sort_index()}")
    print(f"\nOccupation distribution:\n{df['Occupation'].value_counts()}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
