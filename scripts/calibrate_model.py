"""
calibrate_model.py
==================
Probability calibration evaluation (Section 4.4). Evaluates ALL THREE
conditions explicitly, including the uncalibrated baseline:
  (a) uncalibrated model probabilities
  (b) sigmoid / Platt calibration
  (c) isotonic calibration
Calibrators are fitted on the VALIDATION partition only; Brier scores are
reported on the final test partition. Outputs are saved to
results/tables/table_calibration.csv for traceability.
"""
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

def evaluate_calibration(model, X_val, y_val, X_test, y_test, out_csv):
    raw_val = model.predict_proba(X_val)[:, 1]
    raw_test = model.predict_proba(X_test)[:, 1]
    rows = [{"condition": "uncalibrated",
             "brier": brier_score_loss(y_test, raw_test)}]
    # (b) Platt / sigmoid
    platt = LogisticRegression(max_iter=1000).fit(raw_val.reshape(-1, 1), y_val)
    rows.append({"condition": "sigmoid (Platt)",
                 "brier": brier_score_loss(y_test, platt.predict_proba(raw_test.reshape(-1, 1))[:, 1])})
    # (c) isotonic
    iso = IsotonicRegression(out_of_bounds="clip").fit(raw_val, y_val)
    rows.append({"condition": "isotonic",
                 "brier": brier_score_loss(y_test, iso.predict(raw_test))})
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    return df, iso
