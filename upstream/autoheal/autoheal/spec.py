"""Intención convertida en contrato ejecutable (frontera 1 + 2)."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Spec:
    name: str
    entrypoint: str          # nombre de la función a gestionar
    contract_src: str        # código que define check(fn) -> list[str] de fallos
    intent: str = ""         # el "qué" en lenguaje natural (lo lee el proponente)
