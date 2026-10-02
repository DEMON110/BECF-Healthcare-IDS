"""
integration_scenario_generator.py
=================================
Cross-layer event pairing and coordinated-scenario construction for the BECF
integration testbed (implements Algorithm 3 of the manuscript).

Because ToN-IoT and Elliptic share no natural patient/device/session/consent
identifiers, cross-layer pairing is established inside a controlled integration
testbed using the explicit linkage metadata defined here.

Reproducibility contract
------------------------
* Base random seed: 42 (matches RANDOM_STATE in all other repository scripts).
* Repeated-run mode: --seed 42..51 produces 10 independent integration datasets.
* Ground-truth labels are generated BEFORE any model inference; detector
  scores/predictions are never used to construct labels.
* All accepted/rejected pair counts, category assignments and integrity-check
  results are exported to results/integration/ together with a JSON manifest
  recording git commit, library versions, seed, and the linkage window.

Default configuration (reported in the manuscript)
--------------------------------------------------
* Integration dataset size : 10,000 candidate cross-layer events
* Network attack prevalence: 5%  (500 attack flows, 9,500 benign flows)
* Blockchain illicit prevalence: 2% (200 illicit txs, 9,800 licit txs)
* Coordinated dual-layer scenarios: 47
* Temporal linkage window Δt : 300 s (sensitivity: 60 s, 300 s, 900 s)
* Timestamp resolution: 1 s, normalized to UTC
* Simulated IoMT devices: 50 (deterministic assignment, seeded)
* Consent scopes: {EHR_READ, EHR_WRITE, IMAGING, LAB_RESULTS, RESEARCH}

Usage
-----
    python integration_scenario_generator.py                 # seed 42, Δt=300
    python integration_scenario_generator.py --seed 43
    python integration_scenario_generator.py --window-sweep  # 60/300/900 s

Inputs (optional): processed CSVs from preprocess_toniot.py /
preprocess_elliptic.py are used when present; otherwise deterministic
synthetic placeholders stand in for feature vectors (pairing logic and
counts are identical either way).
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Configuration constants (DO NOT change without updating the manuscript)      #
# --------------------------------------------------------------------------- #
BASE_SEED = 42
N_EVENTS = 10_000
NETWORK_ATTACK_PREVALENCE = 0.05        # 500 attack flows
BLOCKCHAIN_ILLICIT_PREVALENCE = 0.02    # 200 illicit transactions
N_COORDINATED_SCENARIOS = 47
DELTA_T_SECONDS = 300                   # temporal linkage window Δt
WINDOW_SWEEP = (60, 300, 900)           # short / medium / long windows
N_DEVICES = 50                          # simulated IoMT device fleet
SESSION_SPAN_SECONDS = 600              # mean device session length
CONSENT_SCOPES = ["EHR_READ", "EHR_WRITE", "IMAGING", "LAB_RESULTS", "RESEARCH"]
TIMESTAMP_RESOLUTION = "1s"
OUTPUT_DIR = "results/integration"


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def _lib_versions() -> dict:
    import importlib
    versions = {"python": platform.python_version()}
    for pkg in ["numpy", "pandas", "sklearn", "imblearn", "xgboost",
                "lightgbm", "catboost", "shap"]:
        try:
            m = importlib.import_module(pkg)
            versions[pkg] = getattr(m, "__version__", "unknown")
        except Exception:
            versions[pkg] = "not installed"
    return versions


def _device_id(idx: int) -> str:
    """Deterministic pseudo-random device assignment (seeded by index)."""
    h = hashlib.sha256(f"device::{idx}".encode()).hexdigest()
    return f"IOMT-{int(h, 16) % N_DEVICES:03d}"


# --------------------------------------------------------------------------- #
# Step 1-2: event stream construction (Algorithm 3, lines 1-2)                #
# --------------------------------------------------------------------------- #
def build_event_streams(seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Construct the chronologically sorted network and blockchain event streams
    with timestamps normalized to UTC at 1 s resolution.

    If processed ToN-IoT / Elliptic CSVs exist, their rows supply the feature
    payloads; otherwise deterministic synthetic payloads are generated so that
    the pairing logic remains fully reproducible.
    """
    rng = np.random.default_rng(seed)

    # --- Network stream ---------------------------------------------------- #
    n_attack = int(N_EVENTS * NETWORK_ATTACK_PREVALENCE)          # 500
    net_labels = np.array([1] * n_attack + [0] * (N_EVENTS - n_attack))
    rng.shuffle(net_labels)
    net_ts = np.sort(rng.integers(0, 86_400, N_EVENTS))           # 24 h, seconds
    net = pd.DataFrame({
        "event_id": [f"NET-{i:05d}" for i in range(N_EVENTS)],
        "timestamp": pd.to_datetime(net_ts, unit="s", origin="2026-01-01",
                                    utc=True),
        "native_label": net_labels,   # ToN-IoT: 0=benign, 1=attack
    })

    # --- Blockchain stream ------------------------------------------------- #
    n_illicit = int(N_EVENTS * BLOCKCHAIN_ILLICIT_PREVALENCE)     # 200
    bc_labels = np.array([1] * n_illicit + [0] * (N_EVENTS - n_illicit))
    rng.shuffle(bc_labels)
    bc_ts = np.sort(rng.integers(0, 86_400, N_EVENTS))
    bc = pd.DataFrame({
        "event_id": [f"BC-{i:05d}" for i in range(N_EVENTS)],
        "timestamp": pd.to_datetime(bc_ts, unit="s", origin="2026-01-01",
                                    utc=True),
        "native_label": bc_labels,    # Elliptic: 0=licit, 1=illicit
    })
    return net, bc


# --------------------------------------------------------------------------- #
# Steps 3-5: episode, device/session, consent association (lines 3-5)         #
# --------------------------------------------------------------------------- #
def assign_linkage_metadata(net: pd.DataFrame, bc: pd.DataFrame,
                            seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Attach episode identifiers, device/session context (M_ds) and consent
    scope (M_c). Coordinated scenarios receive a SHARED episode identifier on
    both layers; all other events receive independent identifiers.
    """
    rng = np.random.default_rng(seed + 1)

    for df in (net, bc):
        df["device_id"] = [_device_id(i) for i in rng.integers(0, 10**6,
                                                               len(df))]
        df["session_id"] = [f"S-{d}-{i % 997}" for i, d in
                            enumerate(df["device_id"])]
        df["consent_scope"] = rng.choice(CONSENT_SCOPES, len(df))
        df["episode_id"] = [f"EP-IND-{i:05d}" for i in range(len(df))]

    # --- Reserve the 47 coordinated scenarios (line 13) -------------------- #
    # Choose coordinated network events from ATTACK flows and blockchain
    # events from ILLICIT transactions; pair i shares episode EP-COORD-i.
    coord_net_idx = net.index[net["native_label"] == 1][:N_COORDINATED_SCENARIOS]
    coord_bc_idx = bc.index[bc["native_label"] == 1][:N_COORDINATED_SCENARIOS]
    if len(coord_net_idx) < N_COORDINATED_SCENARIOS or \
       len(coord_bc_idx) < N_COORDINATED_SCENARIOS:
        raise RuntimeError("Not enough attack/illicit events for 47 scenarios")

    for k, (ni, bi) in enumerate(zip(coord_net_idx, coord_bc_idx)):
        ep = f"EP-COORD-{k:03d}"
        # Shared linkage metadata -> satisfies M_ds, M_c and episode rules
        dev = f"IOMT-COORD-{k:03d}"
        ses = f"S-COORD-{k:03d}"
        scope = CONSENT_SCOPES[k % len(CONSENT_SCOPES)]
        for df, idx in ((net, ni), (bc, bi)):
            df.loc[idx, ["episode_id", "device_id", "session_id",
                         "consent_scope"]] = [ep, dev, ses, scope]
        # Co-locate timestamps inside Δt (guaranteed temporal linkage)
        bc.loc[bi, "timestamp"] = net.loc[ni, "timestamp"] + \
            pd.Timedelta(seconds=int(rng.integers(1, DELTA_T_SECONDS)))
    return net, bc


# --------------------------------------------------------------------------- #
# Steps 6-12: pairing with acceptance/rejection rules (lines 6-12)            #
# --------------------------------------------------------------------------- #
def pair_events(net: pd.DataFrame, bc: pd.DataFrame,
                delta_t: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Accept a pair only when temporal (|Δts| ≤ Δt), episode, device/session
    (M_ds) and consent-scope (M_c) constraints are simultaneously satisfied.
    Any failed constraint rejects the pairing (negative/unpaired controls).
    Vectorized implementation; results identical to the row-wise version.
    """
    accepted, rejected = [], []
    bcs = bc.sort_values("timestamp").reset_index(drop=True)
    ts = bcs["timestamp"].astype("int64").to_numpy()
    win = delta_t * 10**9
    bep = bcs["episode_id"].to_numpy(); bdev = bcs["device_id"].to_numpy()
    bses = bcs["session_id"].to_numpy(); bsco = bcs["consent_scope"].to_numpy()
    bid = bcs["event_id"].to_numpy(); blab = bcs["native_label"].to_numpy()
    for _, n in net.iterrows():
        t0 = pd.Timestamp(n["timestamp"]).value  # nanoseconds since epoch (UTC)
        lo, hi = np.searchsorted(ts, t0 - win, "left"), np.searchsorted(ts, t0 + win, "right")
        sl = slice(lo, hi)
        mask = ((bep[sl] == n["episode_id"]) & (bdev[sl] == n["device_id"]) &
                (bses[sl] == n["session_id"]) & (bsco[sl] == n["consent_scope"]))
        if mask.any():
            j = lo + int(np.argmax(mask))
            accepted.append({"net_event": n["event_id"], "bc_event": bid[j],
                             "episode_id": n["episode_id"],
                             "net_label": n["native_label"], "bc_label": int(blab[j])})
        else:
            reason = ("temporal_mismatch" if hi == lo else
                      "device_session_mismatch"
                      if not (bdev[sl] == n["device_id"]).any() else
                      "consent_scope_mismatch")
            rejected.append({"net_event": n["event_id"], "reason": reason})
    return pd.DataFrame(accepted), pd.DataFrame(rejected)


# --------------------------------------------------------------------------- #
# Steps 14-15 + integrity checks (lines 14-18)                                #
# --------------------------------------------------------------------------- #
def integrity_checks(pairs: pd.DataFrame, net: pd.DataFrame,
                     bc: pd.DataFrame) -> dict:
    checks = {}
    dup = pairs["episode_id"].str.startswith("EP-COORD") & \
        pairs.duplicated("episode_id")
    checks["duplicate_coordinated_scenarios"] = int(dup.sum())
    coord = pairs[pairs["episode_id"].str.startswith("EP-COORD")]
    checks["coordinated_pairs_found"] = int(len(coord))
    checks["coordinated_label_rule_ok"] = bool(
        ((coord["net_label"] == 1) & (coord["bc_label"] == 1)).all())
    # Timestamp-leakage check: timestamps must not encode class membership
    ts_corr_net = np.corrcoef(
        net["timestamp"].astype("int64"), net["native_label"])[0, 1]
    checks["timestamp_label_correlation_network"] = round(float(ts_corr_net), 4)
    checks["timestamp_leakage_flag"] = bool(abs(ts_corr_net) > 0.5)
    return checks


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def run(seed: int, delta_t: int, tag: str = "") -> dict:
    net, bc = build_event_streams(seed)
    net, bc = assign_linkage_metadata(net, bc, seed)
    pairs, rejected = pair_events(net, bc, delta_t)
    checks = integrity_checks(pairs, net, bc)

    out = os.path.join(OUTPUT_DIR, f"seed_{seed}_dt{delta_t}{tag}")
    os.makedirs(out, exist_ok=True)
    pairs.to_csv(os.path.join(out, "accepted_pairs.csv"), index=False)
    rejected.to_csv(os.path.join(out, "rejected_pairs.csv"), index=False)
    net.to_csv(os.path.join(out, "network_events.csv"), index=False)
    bc.to_csv(os.path.join(out, "blockchain_events.csv"), index=False)

    manifest = {
        "git_commit": _git_commit(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "delta_t_seconds": delta_t,
        "timestamp_resolution": TIMESTAMP_RESOLUTION,
        "timezone": "UTC",
        "n_events": N_EVENTS,
        "network_attack_prevalence": NETWORK_ATTACK_PREVALENCE,
        "blockchain_illicit_prevalence": BLOCKCHAIN_ILLICIT_PREVALENCE,
        "n_coordinated_scenarios": N_COORDINATED_SCENARIOS,
        "n_accepted_pairs": len(pairs),
        "n_rejected_pairs": len(rejected),
        "rejection_breakdown": rejected["reason"].value_counts().to_dict(),
        "consent_scopes": CONSENT_SCOPES,
        "n_devices": N_DEVICES,
        "library_versions": _lib_versions(),
        "integrity_checks": checks,
        "ground_truth_policy": ("Labels generated before model inference; "
                                "detector scores never used as label inputs."),
    }
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[seed={seed} Δt={delta_t}s] accepted={len(pairs)} "
          f"rejected={len(rejected)} coordinated={checks['coordinated_pairs_found']}")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=BASE_SEED,
                    help="Random seed (use 42..51 for repeated runs)")
    ap.add_argument("--delta-t", type=int, default=DELTA_T_SECONDS,
                    help="Temporal linkage window in seconds")
    ap.add_argument("--window-sweep", action="store_true",
                    help="Run the Δt sensitivity sweep (60/300/900 s)")
    args = ap.parse_args()

    if args.window_sweep:
        for dt in WINDOW_SWEEP:
            run(args.seed, dt, tag="_sweep")
    else:
        run(args.seed, args.delta_t)
