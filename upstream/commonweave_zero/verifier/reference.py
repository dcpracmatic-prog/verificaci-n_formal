"""Pure-Python reference model for differential verification."""

from __future__ import annotations
from typing import List, Sequence


def matmul_ref(A: Sequence[float], B: Sequence[float],
               m: int, k: int, n: int) -> List[float]:
    """Reference: C = A @ B, row-major float64 semantics."""
    if m < 1 or k < 1 or n < 1:
        raise ValueError("INVALID_DIMENSION")
    if len(A) < m * k or len(B) < k * n:
        raise ValueError("buffer too short")
    C = [0.0] * (m * n)
    for i in range(m):
        for j in range(n):
            s = 0.0
            for p in range(k):
                s += A[i * k + p] * B[p * n + j]
            C[i * n + j] = s
    return C


def scale_clamp_ref(in_buf: Sequence[float], length: int,
                    scale: float, lo: float, hi: float) -> List[float]:
    out = []
    for i in range(length):
        v = in_buf[i] * scale
        if v < lo:
            v = lo
        if v > hi:
            v = hi
        out.append(v)
    return out
