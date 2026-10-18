"""Un detector no pasa a producción sin vencer baselines triviales (IC95 del delta de AUC > 0)."""
from __future__ import annotations
import random
from typing import Dict, Sequence


def auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def evaluate(model: Sequence[float], baselines: Dict[str, Sequence[float]],
             labels: Sequence[int], n_boot: int = 300, seed: int = 0) -> dict:
    rng, n = random.Random(seed), len(labels)
    out = {"n": n, "model_auc": auc(model, labels), "baselines": {}, "beats_baselines": True}
    for name, b in baselines.items():
        ds = []
        for _ in range(n_boot):
            idx = [rng.randrange(n) for _ in range(n)]
            y = [labels[i] for i in idx]
            d = auc([model[i] for i in idx], y) - auc([b[i] for i in idx], y)
            if d == d:
                ds.append(d)
        ds.sort()
        lo = ds[int(0.025 * len(ds))] if ds else float("nan")
        ok = lo == lo and lo > 0
        out["baselines"][name] = {"auc": auc(b, labels), "delta_lo95": lo, "beaten": ok}
        out["beats_baselines"] &= ok
    return out
