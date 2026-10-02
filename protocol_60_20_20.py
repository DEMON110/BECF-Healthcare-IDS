"""
protocol_60_20_20.py
====================
Corrected leakage-free evaluation protocol required by Reviewer 6, Comment 4.

Replaces the 80/20 chronological split with:

    Chronologically sorted dataset
        -> 60% Training   : model fitting, Bayesian hyperparameter optimization,
                            internal temporal CV, SMOTE (inside folds ONLY),
                            feature selection, scaler fitting
        -> 20% Validation : isotonic probability calibration, alpha/beta grid
                            search, gamma threshold selection, model selection
        -> 20% Final test : ONE-TIME evaluation only

Ordering guarantee: Training < Validation < Final Test (both datasets).

IMPORTANT: Running this script regenerates ALL quantitative results.
Every number in the manuscript derived from the old 80/20 protocol must be
replaced with the regenerated values (see regeneration checklist printed at
the end of the run).
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder

RANDOM_STATE = 42
TRAIN_FRAC, VAL_FRAC, TEST_FRAC = 0.60, 0.20, 0.20


def chronological_three_way_split(df, label_col):
    """Contiguous chronological 60/20/20 split. Returns dict of partitions."""
    n = len(df)
    i1, i2 = int(TRAIN_FRAC * n), int((TRAIN_FRAC + VAL_FRAC) * n)
    parts = {"train": df.iloc[:i1], "val": df.iloc[i1:i2], "test": df.iloc[i2:]}
    # chronological ordering guarantee
    assert len(parts["train"]) + len(parts["val"]) + len(parts["test"]) == n
    return parts


def preprocess_toniot_602020(raw_path, output_dir):
    df = pd.read_csv(raw_path)
    drop_cols = ["src_ip", "dst_ip", "src_mac", "dst_mac", "timestamp_raw"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    df = df.sort_values("timestamp").reset_index(drop=True)   # chronological
    cat_cols = [c for c in df.select_dtypes(include=["object"]).columns if c != "label"]
    for c in cat_cols:
        df[c] = LabelEncoder().fit_transform(df[c].astype(str))
    parts = chronological_three_way_split(df, "label")
    # scaler fit on TRAINING ONLY (no leakage)
    scaler = StandardScaler()
    feats = [c for c in df.columns if c != "label"]
    scaler.fit(parts["train"][feats])
    for name, part in parts.items():
        X = scaler.transform(part[feats])
        pd.DataFrame(X, columns=feats).to_csv(f"{output_dir}/toniot_{name}.csv", index=False)
        part["label"].to_csv(f"{output_dir}/toniot_{name}_labels.csv", index=False)
        print(f"[ToN-IoT] {name}: {part.shape}")


def preprocess_elliptic_602020(features_path, classes_path, output_dir):
    X = pd.read_csv(features_path)
    y = pd.read_csv(classes_path)
    df = X.merge(y, on="txId")
    df = df[df["class"] != 2].copy()
    df["label"] = (df["class"] == 1).astype(int)
    df = df.drop(columns=["txId", "class"])
    df = df.sort_values("1").reset_index(drop=True)           # chronological
    parts = chronological_three_way_split(df, "label")
    zero_var = [c for c in parts["train"].columns
                if c != "label" and parts["train"][c].var() == 0]
    scaler = StandardScaler()
    feats = [c for c in df.columns if c not in ("label",) and c not in zero_var]
    scaler.fit(parts["train"][feats])                          # TRAINING ONLY
    for name, part in parts.items():
        Xs = scaler.transform(part[feats])
        pd.DataFrame(Xs, columns=feats).to_csv(f"{output_dir}/elliptic_{name}.csv", index=False)
        part["label"].to_csv(f"{output_dir}/elliptic_{name}_labels.csv", index=False)
        print(f"[Elliptic] {name}: {part.shape}")


EXPERIMENT_SEQUENCE = """
EXACT EXPERIMENT SEQUENCE (run in order, RANDOM_STATE = 42 everywhere):
 1. python protocol_60_20_20.py                      # regenerate 60/20/20 partitions
 2. baseline_benchmark.py  --train toniot_train --val toniot_val
       # 13 classifiers; SMOTE inside training folds ONLY;
       # EXPORT per-window/per-fold validation F1 scores (needed for Comment 6!)
 3. bayesian_optimize.py   --train-only               # hyperparameters from training data only
 4. calibrate_model.py     --fit-on val               # isotonic calibration fit on VALIDATION only
 5. risk_scoring.py        --weights-on val           # alpha/beta grid search on VALIDATION only
 6. threshold_selection.py --gamma-on val             # gamma on VALIDATION only
 7. final_evaluate.py      --test-once                # single evaluation on final test partition
 8. effect_sizes_78.py     --input results/per_window_validation_scores.csv

OUTPUT FILES REQUIRED:
 toniot_{train,val,test}.csv, elliptic_{train,val,test}.csv (+ *_labels.csv)
 results/per_window_validation_scores.csv   (columns: model, window, f1)
 results/tables/final_test_metrics.csv      (accuracy, F1, MCC, ROC-AUC, AUPRC, Brier, ECE)
 results/tables/confusion_matrix_final.csv
 results/tables/alpha_beta_gamma_selected.csv
 results/tables/table_A1_cliffs_delta.csv, table_A2_cohens_d.csv

MANUSCRIPT SECTIONS REQUIRING NUMERICAL UPDATES AFTER RERUN:
 Abstract; 3.5.1 (alpha=0.50, beta=0.30); 3.5.2 + Table 3 (gamma=0.70 row values);
 4.2 (91.35%, 0.9332, 0.8205, CIs, confusion matrix TN/FP/FN/TP, Fig. 6, Fig. 7);
 4.3 (89.04%, 0.8045, 0.7250, TP=637, FP=135); 4.4 (Brier 0.0438, ECE 0.012, Fig. 8);
 4.5 (SHAP ablation 99.4%, 86.85%, Fig. 9); 4.6 (TPR/FPR, Tables 9-10);
 3.13 (Cliff's delta 0.42 / 0.08); 5.1, 5.3; Conclusion.
"""

if __name__ == "__main__":
    import os
    os.makedirs("data/processed", exist_ok=True)
    preprocess_toniot_602020("data/raw/toniot/Train_Test_Network.csv", "data/processed")
    preprocess_elliptic_602020("data/raw/elliptic/elliptic_txs_features.csv",
                               "data/raw/elliptic/elliptic_txs_classes.csv", "data/processed")
    print(EXPERIMENT_SEQUENCE)
