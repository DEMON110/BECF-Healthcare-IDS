# Cross-Layer Integration Testbed (BECF)

This folder contains the executable artifacts backing Section 4.6 and Table 11 of the manuscript.

## Files
- `integration_scenario_generator.py` — deterministic implementation of Algorithm 3 (cross-layer event pairing and scenario construction).
- `results/integration/` — generated outputs:
  - `seed_42_dt300/` — base run reported in the manuscript (seed 42, Δt = 300 s)
  - `seed_43_dt300/` … `seed_51_dt300/` — repeated independent runs (seeds 42–51)
  - `seed_42_dt{60,300,900}_sweep/` — temporal-window sensitivity sweep

Each run folder contains `accepted_pairs.csv`, `rejected_pairs.csv`, `network_events.csv`, `blockchain_events.csv`, and a `manifest.json` recording seed, Δt, counts, library versions, and integrity checks.

## Reproduce
```bash
python integration_scenario_generator.py --seed 42        # base run
python integration_scenario_generator.py --seed 43        # ... through --seed 51
python integration_scenario_generator.py --seed 42 --window-sweep   # Δt = 60/300/900 s
```

## Key results (seed 42, Δt = 300 s)
- 10,000 candidate cross-layer events (5% network attack prevalence, 2% blockchain illicit prevalence)
- 77 accepted cross-layer pairs, including all 47 coordinated dual-layer scenarios (47/47)
- 9,923 rejected negative/unpaired controls (7,505 consent-scope mismatch; 2,418 device/session mismatch)
- Integrity checks: 0 duplicate coordinated scenarios; coordinated label rule satisfied; timestamp–label correlation 0.0008 (no timestamp leakage)

## Repeated runs (seeds 42–51, Δt = 300 s)
All 10 independent runs recovered 47/47 coordinated scenarios; accepted-pair counts ranged 53–83.

## Window sensitivity (seed 42)
| Δt | Accepted pairs | Coordinated scenarios found |
|----|----------------|-----------------------------|
| 60 s  | 30 | 15/47 |
| 300 s | 77 | 47/47 |
| 900 s | 85 | 47/47 |

Ground-truth policy: labels are generated before model inference; detector scores are never used as label inputs.
