"""Prueba por exhaustión sobre un dominio finito DECLARADO.

Si `forall` devuelve PROVEN, la propiedad se cumple para TODAS las entradas del
dominio declarado (no una muestra). Eso es una prueba real, pero SOLO sobre ese
dominio: el dominio forma parte del enunciado y queda registrado en la prueba.
Nunca muestrea: si el dominio excede `max_cases`, lanza error en vez de recortar.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from itertools import product
from typing import Any, Callable, Dict, Iterable, Optional


@dataclass
class Proof:
    name: str
    kind: str                      # EXHAUSTIVE | INTERVAL | ALGEBRAIC | EXHAUSTIVE_C_ASAN
    status: str                    # PROVEN | REFUTED
    statement: str                 # enunciado exacto, incluyendo el dominio
    cases: int = 0
    counterexample: Optional[Dict[str, Any]] = None
    trusted: str = ""              # qué hay que creer para aceptar esta prueba

    def ok(self) -> bool:
        return self.status == "PROVEN"

    def to_dict(self):
        return asdict(self)


class DomainTooLarge(Exception):
    pass


def forall(name: str, domains: Dict[str, Iterable], prop: Callable[..., bool],
           assume: Optional[Callable[..., bool]] = None, max_cases: int = 5_000_000,
           statement: str = "") -> Proof:
    doms = {k: list(v) for k, v in domains.items()}
    size = 1
    for v in doms.values():
        size *= len(v)
    if size > max_cases:
        raise DomainTooLarge(f"{name}: {size} casos > {max_cases}; reduce el dominio (no se muestrea)")
    keys = list(doms)
    n = 0
    desc = ", ".join(f"{k}∈{_brief(v)}" for k, v in doms.items())
    st = statement or f"∀ {desc}: se cumple «{name}»"
    for vals in product(*(doms[k] for k in keys)):
        kw = dict(zip(keys, vals))
        if assume is not None and not assume(**kw):
            continue
        n += 1
        try:
            good = bool(prop(**kw))
        except Exception as e:          # una excepción es un contraejemplo
            kw["__exception__"] = f"{type(e).__name__}: {e}"
            good = False
        if not good:
            return Proof(name, "EXHAUSTIVE", "REFUTED", st, n, kw,
                         "intérprete de Python y la propiedad escrita")
    return Proof(name, "EXHAUSTIVE", "PROVEN", st, n, None,
                 "intérprete de Python y que la propiedad exprese la intención")


def _brief(v):
    v = list(v)
    if len(v) <= 6:
        return "{" + ",".join(map(str, v)) + "}"
    return f"[{v[0]}..{v[-1]}] ({len(v)} valores)"
