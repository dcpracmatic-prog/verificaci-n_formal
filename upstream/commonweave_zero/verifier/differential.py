#!/usr/bin/env python3
"""
COMMONWEAVE Zero — differential verifier
Compares the generated adapter against the pure-Python reference on
random inputs and edge cases. Produces a reproducible report fragment.
"""

from __future__ import annotations
import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verifier.reference import matmul_ref
from generated.matmul_adapter import matmul as matmul_gen, CWError


def almost_equal(a: List[float], b: List[float], tol: float = 1e-9) -> bool:
    if len(a) != len(b):
        return False
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def run_case(m: int, k: int, n: int, seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    A = [rng.uniform(-10, 10) for _ in range(m * k)]
    B = [rng.uniform(-10, 10) for _ in range(k * n)]
    C_gen = [0.0] * (m * n)

    t0 = time.perf_counter()
    try:
        matmul_gen(A, B, C_gen, m, k, n)
        gen_ok = True
        gen_err = None
    except CWError as e:
        gen_ok = False
        gen_err = str(e)
        C_gen = []
    t_gen = time.perf_counter() - t0

    t0 = time.perf_counter()
    try:
        C_ref = matmul_ref(A, B, m, k, n)
        ref_ok = True
        ref_err = None
    except Exception as e:
        ref_ok = False
        ref_err = str(e)
        C_ref = []
    t_ref = time.perf_counter() - t0

    match = gen_ok and ref_ok and almost_equal(C_gen, C_ref)
    return {
        "m": m, "k": k, "n": n, "seed": seed,
        "gen_ok": gen_ok, "ref_ok": ref_ok,
        "match": match,
        "gen_err": gen_err, "ref_err": ref_err,
        "t_gen": t_gen, "t_ref": t_ref,
    }


def edge_cases() -> List[Dict[str, Any]]:
    cases = []
    # Empty / invalid dimensions (should raise)
    for dims in [(0, 1, 1), (1, 0, 1), (1, 1, 0)]:
        m, k, n = dims
        try:
            matmul_gen([1.0], [1.0], [0.0], m, k, n)
            cases.append({"case": f"invalid_dim_{dims}", "passed": False, "note": "should have raised"})
        except CWError:
            cases.append({"case": f"invalid_dim_{dims}", "passed": True})
        except Exception as e:
            cases.append({"case": f"invalid_dim_{dims}", "passed": False, "note": str(e)})

    # 1x1 identity-like
    r = run_case(1, 1, 1, 42)
    cases.append({"case": "1x1", **r})

    # Small rectangular
    r = run_case(2, 3, 4, 99)
    cases.append({"case": "2x3x4", **r})

    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20261018)
    parser.add_argument("--out", type=Path, default=Path("report/differential.json"))
    args = parser.parse_args()

    random.seed(args.seed)
    results = []
    passed = 0
    for i in range(args.trials):
        m = random.randint(1, 16)
        k = random.randint(1, 16)
        n = random.randint(1, 16)
        r = run_case(m, k, n, args.seed + i)
        results.append(r)
        if r["match"]:
            passed += 1

    edges = edge_cases()
    edge_pass = sum(1 for e in edges if e.get("passed") or e.get("match"))

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": args.seed,
        "trials": args.trials,
        "passed": passed,
        "failed": args.trials - passed,
        "pass_rate": passed / args.trials if args.trials else 0.0,
        "edge_cases": edges,
        "edge_passed": edge_pass,
        "edge_total": len(edges),
        "results_sample": results[:5],  # keep report small
        "verdict": "PASS" if passed == args.trials and edge_pass == len(edges) else "FAIL",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "verdict": report["verdict"],
        "pass_rate": report["pass_rate"],
        "edge_passed": f"{edge_pass}/{len(edges)}",
    }, indent=2))


if __name__ == "__main__":
    main()
