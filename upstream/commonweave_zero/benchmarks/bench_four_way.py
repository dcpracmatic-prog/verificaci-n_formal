#!/usr/bin/env python3
"""
COMMONWEAVE Zero — four-way benchmark
Compares:
  1. Pure Python reference
  2. Manual ctypes binding (hand-written, minimal)
  3. Generated adapter (COMMONWEAVE)
  4. Separate process + IPC (multiprocessing Pipe)

Reports cold-start cost and hot-path latency (median / p99),
bytes copied estimates, and a simple human-effort proxy.
"""

from __future__ import annotations
import argparse
import json
import multiprocessing as mp
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verifier.reference import matmul_ref
from generated.matmul_adapter import matmul as matmul_gen, CWError

# ---------------------------------------------------------------------------
# Manual binding (conventional baseline)
# ---------------------------------------------------------------------------
import ctypes
_LIB = ctypes.CDLL(str(Path(__file__).resolve().parents[1] / "c_src" / "libmatmul.so"))
_LIB.matmul.argtypes = [
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.c_size_t, ctypes.c_size_t, ctypes.c_size_t,
]
_LIB.matmul.restype = ctypes.c_int


def matmul_manual(A: Sequence[float], B: Sequence[float],
                  C: List[float], m: int, k: int, n: int) -> None:
    a = (ctypes.c_double * (m * k))(*A)
    b = (ctypes.c_double * (k * n))(*B)
    c = (ctypes.c_double * (m * n))()
    rc = _LIB.matmul(a, b, c, m, k, n)
    if rc != 0:
        raise RuntimeError(f"manual binding error {rc}")
    for i in range(m * n):
        C[i] = c[i]


# ---------------------------------------------------------------------------
# IPC worker
# ---------------------------------------------------------------------------
def _ipc_worker(conn):
    while True:
        msg = conn.recv()
        if msg is None:
            break
        A, B, m, k, n = msg
        C = matmul_ref(A, B, m, k, n)
        conn.send(C)


def matmul_ipc(A, B, m, k, n, conn) -> List[float]:
    conn.send((list(A), list(B), m, k, n))
    return conn.recv()


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------
def timed(fn: Callable, *args, repeats: int = 30) -> Dict[str, float]:
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn(*args)
        times.append(time.perf_counter() - t0)
    times.sort()
    return {
        "median": statistics.median(times),
        "p99": times[min(len(times) - 1, int(0.99 * len(times)))],
        "mean": statistics.mean(times),
        "min": times[0],
        "max": times[-1],
        "n": len(times),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="8,16,32,64", help="comma-separated matrix sizes (square)")
    parser.add_argument("--repeats", type=int, default=40)
    parser.add_argument("--out", type=Path, default=Path("report/benchmark.json"))
    args = parser.parse_args()

    sizes = [int(s) for s in args.sizes.split(",")]
    report: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repeats": args.repeats,
        "implementations": {},
        "notes": {
            "pure_python": "Reference implementation (no native code)",
            "manual_ctypes": "Hand-written conventional binding",
            "generated": "COMMONWEAVE-generated adapter from contract",
            "ipc": "Separate process + Pipe (isolation baseline)",
        },
    }

    # Cold-start cost (import / process spawn)
    t0 = time.perf_counter()
    _ = matmul_ref([1.0], [1.0], 1, 1, 1)
    cold_pure = time.perf_counter() - t0

    t0 = time.perf_counter()
    Ctmp = [0.0]
    matmul_manual([1.0], [1.0], Ctmp, 1, 1, 1)
    cold_manual = time.perf_counter() - t0

    t0 = time.perf_counter()
    Ctmp = [0.0]
    matmul_gen([1.0], [1.0], Ctmp, 1, 1, 1)
    cold_gen = time.perf_counter() - t0

    parent_conn, child_conn = mp.Pipe()
    proc = mp.Process(target=_ipc_worker, args=(child_conn,))
    t0 = time.perf_counter()
    proc.start()
    _ = matmul_ipc([1.0], [1.0], 1, 1, 1, parent_conn)
    cold_ipc = time.perf_counter() - t0

    report["cold_start_seconds"] = {
        "pure_python": cold_pure,
        "manual_ctypes": cold_manual,
        "generated": cold_gen,
        "ipc": cold_ipc,
    }

    for N in sizes:
        m = k = n = N
        import random
        rng = random.Random(42 + N)
        A = [rng.uniform(-1, 1) for _ in range(m * k)]
        B = [rng.uniform(-1, 1) for _ in range(k * n)]

        # Pure
        def pure():
            matmul_ref(A, B, m, k, n)
        t_pure = timed(pure, repeats=args.repeats)

        # Manual
        C = [0.0] * (m * n)
        def manual():
            matmul_manual(A, B, C, m, k, n)
        t_manual = timed(manual, repeats=args.repeats)

        # Generated
        C = [0.0] * (m * n)
        def gen():
            matmul_gen(A, B, C, m, k, n)
        t_gen = timed(gen, repeats=args.repeats)

        # IPC
        def ipc():
            matmul_ipc(A, B, m, k, n, parent_conn)
        t_ipc = timed(ipc, repeats=args.repeats)

        # Rough bytes-copied estimate (input + output for the non-zero-copy paths)
        bytes_per_call = (m * k + k * n + m * n) * 8

        report["implementations"][str(N)] = {
            "pure_python": t_pure,
            "manual_ctypes": t_manual,
            "generated": t_gen,
            "ipc": t_ipc,
            "bytes_estimate": bytes_per_call,
        }

    # Shutdown IPC
    parent_conn.send(None)
    proc.join(timeout=2)

    # Human-effort proxy (lines of glue code that had to be written)
    report["effort_proxy"] = {
        "pure_python": {"loc_glue": 0, "note": "rewrite of algorithm"},
        "manual_ctypes": {"loc_glue": 25, "note": "hand-written argtypes + conversion"},
        "generated": {"loc_glue": 0, "note": "contract only; adapter emitted"},
        "ipc": {"loc_glue": 40, "note": "process + serialisation boilerplate"},
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Human-readable summary
    print("=== COMMONWEAVE Zero — Four-way Benchmark ===")
    print(f"Cold-start (s): pure={cold_pure:.4f}  manual={cold_manual:.4f}  "
          f"gen={cold_gen:.4f}  ipc={cold_ipc:.4f}")
    for N in sizes:
        block = report["implementations"][str(N)]
        print(f"\nSize {N}x{N}  (bytes≈{block['bytes_estimate']})")
        for name in ("pure_python", "manual_ctypes", "generated", "ipc"):
            t = block[name]
            print(f"  {name:16s}  median={t['median']*1e6:8.1f} µs  "
                  f"p99={t['p99']*1e6:8.1f} µs")


if __name__ == "__main__":
    main()
