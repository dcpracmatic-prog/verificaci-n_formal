"""
COMMONWEAVE Zero — generated adapter for matmul
DO NOT EDIT BY HAND. Regenerated from the declarative contract.
"""

from __future__ import annotations
import ctypes
from pathlib import Path
from typing import Optional

_LIB_PATH = Path(r"/home/workdir/artifacts/commonweave_zero/c_src/libmatmul.so")

class CWError(Exception):
    """Raised when the native component returns a non-zero error code."""
    def __init__(self, code: int, message: str = ""):
        self.code = code
        super().__init__(message or f"native error {code}")

_ERROR_MAP = {
    0: "OK",
    1: "NULL_POINTER",
    2: "INVALID_DIMENSION",
    3: "OVERFLOW",
    4: "ALIGNMENT",
}

def _load_lib() -> ctypes.CDLL:
    if not _LIB_PATH.is_file():
        raise FileNotFoundError(f"Shared library not found: {_LIB_PATH}")
    lib = ctypes.CDLL(str(_LIB_PATH))
    return lib

_lib = _load_lib()

# --- matmul ---
_lib.matmul.argtypes = [
    ctypes.POINTER(ctypes.c_double),  # A
    ctypes.POINTER(ctypes.c_double),  # B
    ctypes.POINTER(ctypes.c_double),  # C
    ctypes.c_size_t,                  # m
    ctypes.c_size_t,                  # k
    ctypes.c_size_t,                  # n
]
_lib.matmul.restype = ctypes.c_int

def matmul(A, B, C, m: int, k: int, n: int) -> None:
    """
    C = A @ B  (row-major, float64).
    A, B, C must be contiguous buffers of appropriate length.
    Raises CWError on native failure; validates dimensions before call.
    """
    if m < 1 or k < 1 or n < 1 or m > 10000 or k > 10000 or n > 10000:
        raise CWError(2, "INVALID_DIMENSION")
    if A is None or B is None or C is None:
        raise CWError(1, "NULL_POINTER")

    # Accept list/tuple or array-like; convert to ctypes array
    def to_c(buf, expected_len):
        if hasattr(buf, "__len__") and len(buf) < expected_len:
            raise CWError(2, f"buffer too short: need {expected_len}")
        arr = (ctypes.c_double * expected_len)(*buf)
        return arr

    a_arr = to_c(A, m * k)
    b_arr = to_c(B, k * n)
    c_arr = (ctypes.c_double * (m * n))()

    rc = _lib.matmul(a_arr, b_arr, c_arr, m, k, n)
    if rc != 0:
        raise CWError(rc, _ERROR_MAP.get(rc, "UNKNOWN"))

    # Write results back if C is a mutable sequence
    if hasattr(C, "__setitem__"):
        for i in range(m * n):
            C[i] = c_arr[i]
    else:
        # Return a list if C was not mutable
        return list(c_arr)
    return None

# --- scale_clamp ---
_lib.scale_clamp.argtypes = [
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.c_size_t,
    ctypes.c_double,
    ctypes.c_double,
    ctypes.c_double,
]
_lib.scale_clamp.restype = ctypes.c_int

def scale_clamp(in_buf, out_buf, length: int, scale: float, lo: float, hi: float) -> None:
    if length < 1:
        raise CWError(2, "INVALID_DIMENSION")
    if in_buf is None or out_buf is None:
        raise CWError(1, "NULL_POINTER")
    in_arr = (ctypes.c_double * length)(*in_buf)
    out_arr = (ctypes.c_double * length)()
    rc = _lib.scale_clamp(in_arr, out_arr, length, scale, lo, hi)
    if rc != 0:
        raise CWError(rc, _ERROR_MAP.get(rc, "UNKNOWN"))
    for i in range(length):
        out_buf[i] = out_arr[i]

# End of generated adapter