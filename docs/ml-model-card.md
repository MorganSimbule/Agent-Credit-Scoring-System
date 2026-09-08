# ML Model Card

## Intended use

The system provides decision-support signals for mobile money agent credit-risk assessment. It produces a binary default estimate and a four-class risk category from agent activity features.

The outputs should support review and prioritization. They should not be treated as an automatic approval, denial, or legal determination without appropriate human and institutional controls.

## Models

| Model | Artifact | Output |
| --- | --- | --- |
| Binary default model | `backend/models/binary_default_pipeline(1).joblib` | Default probability and `0/1` flag |
| Multiclass risk model | `backend/models/multiclass_risk_pipeline(1).joblib` | Risk code and category probabilities |

Both artifacts are scikit-learn pipelines with numeric scaling, categorical one-hot encoding, and a random forest classifier.

## Features

| Feature | Type | Description |
| --- | --- | --- |
| `LoanCount` | Integer | Number of loans |
| `AvgLoan` | Numeric | Average loan amount |
| `TransactionFrequency` | Numeric | Transaction frequency/count |
| `AverageTransactionValue` | Numeric | Average transaction value |
| `AuditActivity` | Integer | Audit activity events |
| `Occupation` | Categorical | Agent occupation |

The API also accepts `ClientID` for audit traceability; it is not a model feature.

## Risk labels

| Code | Label |
| --- | --- |
| `0` | `LOW RISK` |
| `1` | `MEDIUM RISK` |
| `2` | `HIGH RISK` |
| `3` | `VERY HIGH RISK` |

## Current evaluation metadata

Values are recorded in `backend/models/metadata.json` and were produced from the current train/test split:

| Model | Accuracy | F1 | ROC-AUC |
| --- | ---: | ---: | ---: |
| Binary | 0.800 | 0.798 | 0.839 |
| Multiclass | 0.695 | 0.676 | 0.788 |

These are evaluation metrics, not guarantees of live performance. The multiclass confusion matrix currently contains no test examples correctly classified in the `VERY HIGH RISK` class, so that class requires particular caution.

## Training process

1. Load `backend/data/training_data.csv`.
2. Validate feature and target columns.
3. Split data into training and test sets with `test_size=0.2` and `random_state=42`.
4. Fit separate binary and multiclass pipelines.
5. Export joblib artifacts and `metadata.json`.
6. Record numeric feature means and standard deviations for drift monitoring.

Run from `backend/`:

```bash
python generate_training_data.py
python train_export.py
```

## Limitations and risks

- Training data is synthetic in the supplied repository.
- Model performance may change when real traffic differs from training data.
- Unknown occupations are accepted but may carry no learned categorical signal.
- Drift detection is a coarse z-score signal, not a full statistical monitoring system.
- Historical prediction rows retain model output but do not automatically reproduce the model artifact.
- Fairness, calibration, subgroup performance, and production validation should be assessed before high-impact use.
