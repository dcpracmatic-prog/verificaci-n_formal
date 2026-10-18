"""Lemas de seguridad aritmética para el C de commonweave, válidos para TODO el rango del contrato.

Cada lema es una prueba: aritmética de intervalos exactos (sin redondeo) + identidades polinómicas
comprobadas en rejilla (ver fvcore/intervals.py). La base de confianza es ese módulo (~60 líneas) y
la traducción manual de las expresiones de C a Python (se indica línea a línea).
Los mismos lemas se emiten como obligaciones SMT-LIB2 (obligations/smt2) para que Z3 los
re-pruebe de forma independiente.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fvcore.intervals import Interval as I, poly_identity
from fvcore.exhaustive import Proof, forall

U64 = (64, False)
S64 = (64, True)
I32 = I(-(1 << 31), (1 << 31) - 1)
TRUST = "fvcore/intervals.py y la traducción manual C→Python de las expresiones"


def _p(name, kind, ok, stmt, trusted=TRUST, cases=0, cx=None):
    return Proof(name, kind, "PROVEN" if ok else "REFUTED", stmt, cases, cx, trusted)


def index_in_bounds(name: str, rows_max: int, cols_max: int, c_expr: str) -> Proof:
    """∀ rows∈[1,R], cols∈[1,C], 0<=r<rows, 0<=c<cols:  0 <= r*cols+c < rows*cols  y no desborda size_t.
    Prueba: r=rows-1-a, c=cols-1-b con a,b>=0  =>  rows*cols-1-(r*cols+c) = a*cols+b >= 0."""
    # (1) identidad polinómica: (rows*cols-1) - ((rows-1-a)*cols + (cols-1-b)) == a*cols + b
    ident = poly_identity(lambda rows, cols, a, b: (rows * cols - 1) - ((rows - 1 - a) * cols + (cols - 1 - b)),
                          lambda rows, cols, a, b: a * cols + b, nvars=4, deg=2)
    # (2) a*cols+b >= 0 por intervalos (a∈[0,R-1], b∈[0,C-1], cols∈[1,C])
    slack = I(0, rows_max - 1) * I(1, cols_max) + I(0, cols_max - 1)
    # (3) ningún intermedio de la expresión desborda size_t (uint64)
    inter_mul = I(0, rows_max - 1) * I(1, cols_max)
    full = inter_mul + I(0, cols_max - 1)
    ok = ident and slack.lo >= 0 and inter_mul.fits(*U64) and full.fits(*U64) and (I(1, rows_max) * I(1, cols_max)).fits(*U64)
    return _p(name, "ALGEBRAIC+INTERVAL", ok,
              f"∀ rows∈[1,{rows_max}], cols∈[1,{cols_max}], 0≤r<rows, 0≤c<cols: 0 ≤ {c_expr} < rows·cols, "
              f"y {c_expr} y rows·cols caben en size_t (máx {full.hi}).")


def matmul_lemmas():
    N = 10000
    return [
        index_in_bounds("L1/matmul: A[i*k+p] en rango", N, N, "i*k+p"),
        index_in_bounds("L2/matmul: B[p*n+j] en rango", N, N, "p*n+j"),
        index_in_bounds("L3/matmul: C[i*n+j] en rango", N, N, "i*n+j"),
    ]


def histogram_lemmas():
    lemmas = []
    w_all = I32 - I32                                   # hi - lo en int64, sin restricción
    w = I(1, w_all.hi)                                  # con hi > lo (el código lo garantiza antes)
    x0 = I(0, w_all.hi)                                 # v - lo con lo <= v < hi  (<= w-1)
    nb = I(1, 4096)
    prod = x0 * nb
    lemmas.append(_p("L4/histogram: (int64)hi-lo y (int64)v-lo caben en int64", "INTERVAL",
                     w_all.fits(*S64) and x0.fits(*S64),
                     f"hi,lo∈int32: hi-lo∈[{w_all.lo},{w_all.hi}] ⊂ int64."))
    lemmas.append(_p("L5/histogram: (v-lo)*nbins cabe en int64", "INTERVAL", prod.fits(*S64),
                     f"(v-lo)∈[0,{x0.hi}], nbins∈[1,4096]: producto ≤ {prod.hi} < 2^63."))
    # índice del bin: 0 <= (v-lo)*nbins / w < nbins
    ident = poly_identity(lambda w_, n_: w_ * n_ - (w_ - 1) * n_, lambda w_, n_: n_, nvars=2, deg=2)
    # (w-1)*nbins = w*nbins - nbins < w*nbins ; q=floor(prod/w) => q*w <= prod < nbins*w => q < nbins (w>0)
    small = forall("aux", {"w": range(1, 256), "nb": range(1, 17)},
                   lambda w, nb: all(x * nb // w < nb and x * nb // w >= 0 for x in range(0, w)),
                   statement="comprobación de cordura (no es la prueba)")
    lemmas.append(_p("L6/histogram: 0 <= bin < nbins", "ALGEBRAIC", ident and prod.lo >= 0 and small.ok(),
                     "∀ w≥1, nbins≥1, 0≤x≤w-1: x·nbins ≤ (w-1)·nbins = w·nbins − nbins < w·nbins ⇒ ⌊x·nbins/w⌋ < nbins, y ≥ 0 por x≥0. "
                     "Paso final (def. de ⌊·⌋: q·w ≤ x·nbins < nbins·w ⇒ q < nbins) es una línea a mano; cordura exhaustiva con w<256, nbins≤16 incluida.",
                     trusted=TRUST + "; paso de definición de ⌊·⌋ demostrado a mano",
                     cases=small.cases))
    # bins[b] += 1: el contador uint32 no desborda mientras len <= 1_000_000
    lemmas.append(_p("L7/histogram: contador uint32 no desborda", "INTERVAL", I(0, 1_000_000).fits(32, False),
                     "cada bin recibe ≤ len ≤ 1 000 000 incrementos < 2^32."))
    return lemmas


def stats_lemmas():
    s = I32 * I(1, 1_000_000)
    return [_p("L8/array_stats: acumulador int64 no desborda", "INTERVAL", s.fits(*S64),
               f"|suma| ≤ len·2^31 ≤ {s.hi} < 2^63 para len ≤ 1 000 000.")]


def all_lemmas():
    return matmul_lemmas() + histogram_lemmas() + stats_lemmas()


if __name__ == "__main__":
    for p in all_lemmas():
        print(("OK  " if p.ok() else "FALLA"), p.name, "—", p.statement)
