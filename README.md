# BECF: A Unified Cross-Layer Risk Scoring Framework for Healthcare IoT Security with Blockchain Anomaly Detection and Explainable Intrusion Detection

This repository contains the complete reproducibility package for the manuscript
**"BECF: A Unified Cross-Layer Risk Scoring Framework for Healthcare IoT Security with Blockchain Anomaly Detection and Explainable Intrusion Detection"**
(Blockchain-Enabled Cybersecurity Framework, BECF).

## Authors

Usman Mohyud Din Chaudhary, Humaira Arshad, Muhammad Ismail Mohmand, Usama Ahmed, Usman Ahmad

## Author contributions (CRediT)

- **Conceptualization:** Usman Mohyud Din Chaudhary, Humaira Arshad
- **Methodology:** Usman Mohyud Din Chaudhary
- **Software:** Muhammad Ismail Mohmand, Usman Ahmad
- **Validation:** Muhammad Ismail Mohmand, Usama Ahmed
- **Formal analysis:** Humaira Arshad
- **Investigation:** Usama Ahmed, Usman Ahmad
- **Resources:** Usama Ahmed
- **Data curation:** Usman Ahmad
- **Writing – original draft:** Usman Mohyud Din Chaudhary
- **Writing – review & editing:** Humaira Arshad, Muhammad Ismail Mohmand, Usama Ahmed, Usman Ahmad
- **Visualization:** Muhammad Ismail Mohmand
- **Supervision:** Humaira Arshad
- **Project administration:** Usama Ahmed

## Repository layout

```
├── scripts/
│   ├── protocol_60_20_20.py            # Corrected 60/20/20 chronological protocol + full experiment sequence
│   ├── bayesian_optimize.py            # Bayesian hyperparameter optimization (Section 3.12)
│   ├── calibrate_model.py              # Calibration evaluation: uncalibrated / sigmoid / isotonic (Section 4.4)
│   ├── effect_sizes_78.py              # Cliff's delta + paired Cohen's d for all 78 classifier pairs (Appendix A)
│   └── integration_scenario_generator.py # Deterministic cross-layer scenario generator (Algorithm 3)
├── results/
│   ├── per_window_validation_scores.csv  # 13 models x 10 validation windows (Wilcoxon/Friedman input)
│   ├── table_A1_cliffs_delta.csv         # Table A1 — 78 pairwise Cliff's delta values
│   ├── table_A2_cohens_d.csv             # Table A2 — 78 pairwise Cohen's d values
│   └── integration/                      # Cross-layer integration artifacts (seeds 42-51, dt sweep 60/300/900)
├── docs/
│   ├── Rebuttal_Letter_Reviewer5.docx
│   └── Rebuttal_Letter_Reviewer6.docx
└── manuscript/
    └── BECF_Revised_Manuscript_Reviewer6_Blue_Highlighted.docx  # Revised manuscript (changes highlighted)
```

## Datasets

| Dataset | Source | Notes |
|---|---|---|
| ToN-IoT (`train_test_network.csv`) | https://www.kaggle.com/api/v1/datasets/download/arnobbhowmik/ton-iot-network-dataset | 211,043 flows; no timestamps, grouped by attack type → stratified 60/20/20 split (seed 42), disclosed in Section 3.11 |
| Elliptic | https://data.pyg.org/datasets/elliptic/ | Class 1 = illicit; "unknown" excluded; sorted by time step (column `1`) → strict chronological split |

## Experimental protocol (Section 3.11)

1. Chronological 60/20/20 train/validation/test split (Training < Validation < Final Test).
2. SMOTE applied inside the training partition only.
3. Isotonic calibration fitted on the validation partition only.
4. Fusion weights (α = 0.70, β = 0.15) and alerting threshold (γ = 0.60) selected by grid search on validation only (Table 3 of the manuscript).
5. LightGBM hyperparameters selected by Bayesian optimization (35 calls, EI acquisition, 3-fold CV on training only).
6. The final test set is evaluated exactly once.

## Key reported results (final test set)

| Experiment | Metric | Value |
|---|---|---|
| ToN-IoT IDS (Bayesian-optimized LightGBM) | Accuracy | 99.89% (95% CI [99.85, 99.92]) |
| | F1 / MCC / AUC | 0.9993 / 0.9969 / 0.9999 |
| | Confusion matrix | TN 9,973 · FP 27 · FN 21 · TP 32,188 |
| | Calibration | Brier 0.00104 → 0.00097 (isotonic), ECE 0.0005 |
| Elliptic illicit-detection (LightGBM) | Balanced accuracy | 76.63% |
| | F1 / AUPRC | 0.6290 / 0.5854 |
| | Confusion matrix | TN 8,755 · FP 86 · FN 216 · TP 256 |
| Cross-layer integration (Algorithm 3) | TPR (coordinated) | 74.4% · FPR 0.20% |
| | Scenario detection | 47/47 coordinated scenarios (Wilson 95% CI [92.4%, 100%]) |
| | Seeds 42–51 | 47/47 detected in every seed |
| | Δt sweep (60/300/900 s) | 15/47 · 47/47 · 47/47 |

Best Bayesian-optimized hyperparameters: `num_leaves=41, max_depth=12, learning_rate=0.2663, n_estimators=858, subsample=0.8034` (CV F1 = 0.99897).

## Reproducing

```bash
pip install -r requirements.txt

# 1. Full corrected protocol and experiment sequence
python scripts/protocol_60_20_20.py

# 2. Bayesian hyperparameter optimization (Section 3.12)
python scripts/bayesian_optimize.py

# 3. Calibration: uncalibrated baseline + Platt + isotonic (Section 4.4)
python scripts/calibrate_model.py

# 4. Effect sizes for Appendix A Tables A1-A2
python scripts/effect_sizes_78.py

# 5. Cross-layer integration scenarios (Algorithm 3)
python scripts/integration_scenario_generator.py
```

The integration generator is fully deterministic (seed 42): it regenerates the exact
artifacts in `results/integration/` (10,000 events; 77 accepted pairs including 47/47
coordinated scenarios; 9,923 rejected pairs — 7,505 consent-scope + 2,418 device/session).

## Data availability

All result artifacts needed to verify the manuscript tables are included under `results/`.
Each integration run directory contains `network_events.csv`, `blockchain_events.csv`,
`accepted_pairs.csv`, `rejected_pairs.csv`, and a `manifest.json` with full configuration.
