"""Aritmética de intervalos sobre enteros exactos (sin redondeo) + identidades polinómicas.

Sirve para demostrar, para TODO el rango del contrato (no una muestra), que una
expresión entera de C no desborda su tipo. Es un análisis sobre-aproximado:
si dice "cabe", cabe; si dice "no cabe", puede ser falsa alarma.

Identidad polinómica: un polinomio con grado <= d en cada variable que se anula
en la rejilla {0..d}^n es idénticamente cero sobre los enteros (lema estándar).
Eso nos da una prueba real de identidades como (m-1)*k + (k-1) == m*k - 1.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from typing import Callable


@dataclass(frozen=True)
class Interval:
    lo: int
    hi: int

    def __post_init__(self):
        assert self.lo <= self.hi

    def __add__(self, o):
        o = _iv(o); return Interval(self.lo + o.lo, self.hi + o.hi)
    __radd__ = __add__

    def __sub__(self, o):
        o = _iv(o); return Interval(self.lo - o.hi, self.hi - o.lo)

    def __rsub__(self, o):
        return _iv(o) - self

    def __mul__(self, o):
        o = _iv(o)
        c = [self.lo * o.lo, self.lo * o.hi, self.hi * o.lo, self.hi * o.hi]
        return Interval(min(c), max(c))
    __rmul__ = __mul__

    def floordiv(self, d: "Interval") -> "Interval":
        d = _iv(d)
        assert d.lo > 0, "divisor debe ser estrictamente positivo en todo el intervalo"
        c = [self.lo // d.lo, self.lo // d.hi, self.hi // d.lo, self.hi // d.hi]
        return Interval(min(c), max(c))

    def fits(self, bits: int, signed: bool) -> bool:
        lo, hi = (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if signed else (0, (1 << bits) - 1)
        return lo <= self.lo and self.hi <= hi


def _iv(x):
    return x if isinstance(x, Interval) else Interval(x, x)


def poly_identity(f: Callable[..., int], g: Callable[..., int], nvars: int, deg: int) -> bool:
    """f == g como polinomios (enteros) si coinciden en {0..deg}^nvars y deg_i(f-g) <= deg."""
    return all(f(*pt) == g(*pt) for pt in product(range(deg + 1), repeat=nvars))
