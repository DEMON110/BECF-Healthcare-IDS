"""
effect_sizes_78.py
==================
Computes the complete 78-pair effect-size tables required by Reviewer 6,
Comment 6, from the SAME paired per-window temporal validation scores used
for the Wilcoxon signed-rank analysis.

NO AGGREGATE OR FINAL-TEST VALUES ARE USED. Aggregate F1, final-test F1,
or one score per model cannot support paired effect sizes.

Required input
--------------
results/per_window_validation_scores.csv with columns:
    model,window,f1
- model  : classifier name (exactly 13 unique models)
- window : temporal validation window/fold identifier
- f1     : F1-score of that model on that window
Every model must have the SAME set of windows (paired design).

Outputs
-------
results/tables/table_A1_cliffs_delta.csv  (No., Model A, Model B, Cliff's delta, Magnitude)
results/tables/table_A2_cohens_d.csv      (No., Model A, Model B, Cohen's d, Magnitude)

Sign convention (as required):
    positive = Model A performs higher than Model B
    negative = Model B performs higher than Model A
"""

import itertools
import sys

import numpy as np
import pandas as pd

EXPECTED_MODELS = 13
EXPECTED_PAIRS = EXPECTED_MODELS * (EXPECTED_MODELS - 1) // 2  # 78


def cliffs_delta(a, b):
    """Cliff's delta: P(a>b) - P(a<b), computed exactly over all pairs."""
    a, b = np.asarray(a), np.asarray(b)
    gt = sum(np.sum(ai > b) for ai in a)
    lt = sum(np.sum(ai < b) for ai in a)
    return (gt - lt) / (len(a) * len(b))


def cohens_d_paired(a, b):
    """Cohen's d for paired differences: mean(a-b) / sd(a-b)."""
    diff = np.asarray(a) - np.asarray(b)
    sd = diff.std(ddof=1)
    if sd == 0:
        return np.nan  # identical paired scores; d undefined
    return diff.mean() / sd


def magnitude_cliff(d):
    a = abs(d)
    return ("negligible" if a < 0.147 else "small" if a < 0.33
            else "medium" if a < 0.474 else "large")


def magnitude_cohen(d):
    a = abs(d)
    return ("negligible" if a < 0.2 else "small" if a < 0.5
            else "medium" if a < 0.8 else "large")


def main(path="results/per_window_validation_scores.csv"):
    df = pd.read_csv(path)

    # ---- validation checks ------------------------------------------------ #
    models = sorted(df["model"].unique())
    assert len(models) == EXPECTED_MODELS, \
        f"Expected {EXPECTED_MODELS} models, found {len(models)}"
    windows = df.groupby("model")["window"].apply(set)
    ref = windows.iloc[0]
    assert all(w == ref for w in windows), \
        "Models do not share identical validation windows (not paired)"
    assert not df.duplicated(["model", "window"]).any(), "Duplicate model-window rows"
    assert df["f1"].between(0, 1).all(), "F1 values out of [0,1]"

    piv = df.pivot(index="window", columns="model", values="f1")
    print(f"Paired design verified: {len(models)} models x {piv.shape[0]} windows")

    # ---- compute all 78 pairs -------------------------------------------- #
    rows_c, rows_d = [], []
    for k, (A, B) in enumerate(itertools.combinations(models, 2), 1):
        a, b = piv[A].to_numpy(), piv[B].to_numpy()
        cd = cliffs_delta(a, b)
        dz = cohens_d_paired(a, b)
        rows_c.append([k, A, B, round(cd, 4), magnitude_cliff(cd)])
        rows_d.append([k, A, B, round(dz, 4) if not np.isnan(dz) else "undefined",
                       magnitude_cohen(dz) if not np.isnan(dz) else "undefined"])

    assert len(rows_c) == EXPECTED_PAIRS and len(rows_d) == EXPECTED_PAIRS
    pairs = {(r[1], r[2]) for r in rows_c}
    assert len(pairs) == EXPECTED_PAIRS, "Duplicate pair detected"

    tA1 = pd.DataFrame(rows_c, columns=["No.", "Model A", "Model B",
                                        "Cliff's delta", "Magnitude interpretation"])
    tA2 = pd.DataFrame(rows_d, columns=["No.", "Model A", "Model B",
                                        "Cohen's d", "Magnitude interpretation"])
    tA1.to_csv("results/tables/table_A1_cliffs_delta.csv", index=False)
    tA2.to_csv("results/tables/table_A2_cohens_d.csv", index=False)

    # ---- independent verification ---------------------------------------- #
    spot = rows_c[0]
    a = piv[spot[1]].to_numpy(); b = piv[spot[2]].to_numpy()
    manual = np.mean([np.sign(ai - bj) for ai in a for bj in b])
    assert abs(manual - spot[3]) < 1e-3, "Independent verification failed"
    print("Independent verification passed.")
    print(f"Table A1 (78 pairs) and Table A2 (78 pairs) written to results/tables/")
    print("\nDistribution summary (use this to replace any broad claims):")
    print(tA1["Magnitude interpretation"].value_counts().to_string())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/per_window_validation_scores.csv")
