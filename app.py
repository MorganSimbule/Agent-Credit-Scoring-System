from pathlib import Path
import joblib
import pandas as pd

# 1. Dynamically locate and load your model
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "binary_default_pipeline(1).joblib"
binary_pipeline = joblib.load(MODEL_PATH)

# 2. Provide sample input with all 6 required features
# (Adjust the values below to test different inputs)
new_customer_data = pd.DataFrame([{
    'LoanCount': 2,
    'AvgLoan': 1500.0,
    'TransactionFrequency': 12,
    'AverageTransactionValue': 450.50,
    'AuditActivity': 1,
    'Occupation': 'Teacher'
}])

# 3. Predict probabilities
risk_probabilities = binary_pipeline.predict_proba(new_customer_data)

# 4. Extract default probability (Class 1)
default_risk = risk_probabilities[0][1]
print(f"Risk score: {default_risk * 100:.1f}%")