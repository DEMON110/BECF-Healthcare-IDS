"""
bayesian_optimize.py
====================
Bayesian hyperparameter optimization for the deployed ToN-IoT IDS classifier
(Section 3.12 of the manuscript). Optimization uses TRAINING DATA ONLY
(3-fold stratified CV on the 60% training partition); the validation and
final-test partitions are never accessed.

Protocol: scikit-optimize gp_minimize, 35 evaluations (10 initial points),
expected-improvement acquisition, random_state = 42.
Best result (CV F1 = 0.99897):
    num_leaves=41, max_depth=12, learning_rate=0.2663,
    n_estimators=858, subsample=0.8034
"""
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score
from skopt import gp_minimize
from skopt.space import Integer, Real

RANDOM_STATE = 42
SEARCH_SPACE = [Integer(20, 100, name="num_leaves"), Integer(3, 12, name="max_depth"),
                Real(0.01, 0.3, name="learning_rate"), Integer(100, 1000, name="n_estimators"),
                Real(0.6, 1.0, name="subsample")]

def optimize(X_train, y_train, n_calls=35):
    cv = StratifiedKFold(3, shuffle=True, random_state=RANDOM_STATE)
    def objective(params):
        nl, md, lr, ne, ss = params
        f1s = []
        for tr, te in cv.split(X_train, y_train):
            m = LGBMClassifier(num_leaves=int(nl), max_depth=int(md), learning_rate=float(lr),
                               n_estimators=int(ne), subsample=float(ss),
                               random_state=RANDOM_STATE, verbose=-1, n_jobs=-1)
            m.fit(X_train[tr], y_train[tr])
            f1s.append(f1_score(y_train[te], m.predict(X_train[te])))
        return -float(np.mean(f1s))
    res = gp_minimize(objective, SEARCH_SPACE, n_calls=n_calls, acq_func="EI",
                      random_state=RANDOM_STATE, n_initial_points=10)
    best = dict(zip(["num_leaves", "max_depth", "learning_rate", "n_estimators", "subsample"],
                    [int(res.x[0]), int(res.x[1]), float(res.x[2]), int(res.x[3]), float(res.x[4])]))
    best["cv_f1"] = float(-res.fun)
    return best

if __name__ == "__main__":
    X = np.load("data/processed/toniot_train_raw.npy")
    y = np.load("data/processed/toniot_train_labels_raw.npy")
    print(optimize(X, y))
