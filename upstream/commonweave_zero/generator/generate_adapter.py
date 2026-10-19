#!/usr/bin/env python3
"""
COMMONWEAVE Zero — adapter generator
Reads a declarative YAML contract and emits a minimal, inspectable ctypes adapter.
"""

from __future__ import annotations
import argparse
import json
import textwrap
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def load_contract(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError("PyYAML required for YAML contracts. Install with: pip install pyyaml")
        return yaml.safe_load(text)
    return json.loads(text)


def emit_ctypes_adapter(contract: dict, lib_path: str) -> str:
    """Generate a self-contained Python module using ctypes."""
    name = contract["name"]
    functions = contract.get("functions", [])

    lines = [
        '"""',
        f'COMMONWEAVE Zero — generated adapter for {name}',
        'DO NOT EDIT BY HAND. Regenerated from the declarative contract.',
        '"""',
        '',
        'from __future__ import annotations',
        'import ctypes',
        'from pathlib import Path',
        'from typing import Optional',
        '',
        f'_LIB_PATH = Path(r"{lib_path}")',
        '',
        'class CWError(Exception):',
        '    """Raised when the native component returns a non-zero error code."""',
        '    def __init__(self, code: int, message: str = ""):',
        '        self.code = code',
        '        super().__init__(message or f"native error {code}")',
        '',
        '_ERROR_MAP = {',
        '    0: "OK",',
        '    1: "NULL_POINTER",',
        '    2: "INVALID_DIMENSION",',
        '    3: "OVERFLOW",',
        '    4: "ALIGNMENT",',
        '}',
        '',
        'def _load_lib() -> ctypes.CDLL:',
        '    if not _LIB_PATH.is_file():',
        '        raise FileNotFoundError(f"Shared library not found: {_LIB_PATH}")',
        '    lib = ctypes.CDLL(str(_LIB_PATH))',
        '    return lib',
        '',
        '_lib = _load_lib()',
        '',
    ]

    for fn in functions:
        fname = fn["name"]
        if fname == "matmul":
            lines.extend([
                '# --- matmul ---',
                '_lib.matmul.argtypes = [',
                '    ctypes.POINTER(ctypes.c_double),  # A',
                '    ctypes.POINTER(ctypes.c_double),  # B',
                '    ctypes.POINTER(ctypes.c_double),  # C',
                '    ctypes.c_size_t,                  # m',
                '    ctypes.c_size_t,                  # k',
                '    ctypes.c_size_t,                  # n',
                ']',
                '_lib.matmul.restype = ctypes.c_int',
                '',
                'def matmul(A, B, C, m: int, k: int, n: int) -> None:',
                '    """',
                '    C = A @ B  (row-major, float64).',
                '    A, B, C must be contiguous buffers of appropriate length.',
                '    Raises CWError on native failure; validates dimensions before call.',
                '    """',
                '    if m < 1 or k < 1 or n < 1 or m > 10000 or k > 10000 or n > 10000:',
                '        raise CWError(2, "INVALID_DIMENSION")',
                '    if A is None or B is None or C is None:',
                '        raise CWError(1, "NULL_POINTER")',
                '',
                '    # Accept list/tuple or array-like; convert to ctypes array',
                '    def to_c(buf, expected_len):',
                '        if hasattr(buf, "__len__") and len(buf) < expected_len:',
                '            raise CWError(2, f"buffer too short: need {expected_len}")',
                '        arr = (ctypes.c_double * expected_len)(*buf)',
                '        return arr',
                '',
                '    a_arr = to_c(A, m * k)',
                '    b_arr = to_c(B, k * n)',
                '    c_arr = (ctypes.c_double * (m * n))()',
                '',
                '    rc = _lib.matmul(a_arr, b_arr, c_arr, m, k, n)',
                '    if rc != 0:',
                '        raise CWError(rc, _ERROR_MAP.get(rc, "UNKNOWN"))',
                '',
                '    # Write results back if C is a mutable sequence',
                '    if hasattr(C, "__setitem__"):',
                '        for i in range(m * n):',
                '            C[i] = c_arr[i]',
                '    else:',
                '        # Return a list if C was not mutable',
                '        return list(c_arr)',
                '    return None',
                '',
            ])
        elif fname == "scale_clamp":
            lines.extend([
                '# --- scale_clamp ---',
                '_lib.scale_clamp.argtypes = [',
                '    ctypes.POINTER(ctypes.c_double),',
                '    ctypes.POINTER(ctypes.c_double),',
                '    ctypes.c_size_t,',
                '    ctypes.c_double,',
                '    ctypes.c_double,',
                '    ctypes.c_double,',
                ']',
                '_lib.scale_clamp.restype = ctypes.c_int',
                '',
                'def scale_clamp(in_buf, out_buf, length: int, scale: float, lo: float, hi: float) -> None:',
                '    if length < 1:',
                '        raise CWError(2, "INVALID_DIMENSION")',
                '    if in_buf is None or out_buf is None:',
                '        raise CWError(1, "NULL_POINTER")',
                '    in_arr = (ctypes.c_double * length)(*in_buf)',
                '    out_arr = (ctypes.c_double * length)()',
                '    rc = _lib.scale_clamp(in_arr, out_arr, length, scale, lo, hi)',
                '    if rc != 0:',
                '        raise CWError(rc, _ERROR_MAP.get(rc, "UNKNOWN"))',
                '    for i in range(length):',
                '        out_buf[i] = out_arr[i]',
                '',
            ])

    lines.append('# End of generated adapter')
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="COMMONWEAVE Zero adapter generator")
    parser.add_argument("--contract", required=True, type=Path, help="Path to YAML/JSON contract")
    parser.add_argument("--lib", required=True, type=Path, help="Path to shared library")
    parser.add_argument("--out", required=True, type=Path, help="Output Python module path")
    args = parser.parse_args()

    contract = load_contract(args.contract)
    code = emit_ctypes_adapter(contract, str(args.lib.resolve()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(code, encoding="utf-8")
    print(f"Generated adapter: {args.out}")


if __name__ == "__main__":
    main()
