"""Un parche que PASA las pruebas aleatorias de autoheal pero es incorrecto.

El agente (stub) propone primero un parche con un fallo que el contrato original no puede ver
(solo prueba listas de floats): para listas de enteros usa división entera. Con el verificador
base se instala; con FormalVerifier se rechaza con el contraejemplo exacto y luego se acepta el correcto.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from integration.formal_autoheal import FormalVerifier   # fija sys.path hacia upstream/autoheal
from autoheal import SelfHealing, Autonomy, Spec, Ledger, SubprocessVerifier

BUGGY = "def mean(xs):\n    return sum(xs) / len(xs)\n"
TRICKY = ("def mean(xs):\n    if not xs:\n        return None\n"
          "    if all(isinstance(x, int) for x in xs):\n        return sum(xs) // len(xs)\n"
          "    return sum(xs) / len(xs)\n")
GOOD = "def mean(xs):\n    if not xs:\n        return None\n    return sum(xs) / len(xs)\n"

CONTRACT = '''
import random
def check(fn):
    f, r = [], random.Random(0)
    if fn([]) is not None:
        f.append("lista vacia debe devolver None")
    for _ in range(200):
        xs = [r.uniform(-100, 100) for _ in range(r.randint(1, 20))]
        m = fn(xs)
        if not (min(xs) - 1e-9 <= m <= max(xs) + 1e-9):
            f.append("la media debe estar entre min y max"); break
        if abs(m - sum(xs) / len(xs)) > 1e-9:
            f.append("la media debe ser sum/len"); break
    return f
'''

PROOF = '''
from fractions import Fraction
from itertools import product

def lists(vals, maxlen):
    return [list(t) for n in range(1, maxlen + 1) for t in product(vals, repeat=n)]

def prove(fn, forall):
    ints = lists(range(-2, 3), 4)                  # 780 listas: TODAS las de longitud 1..4 con valores en -2..2
    dyad = lists([-1.5, 0.0, 0.25, 2.0], 3)        # 84 listas de floats diádicos (suma exacta en binario)
    return [
        forall("mean(ints) == media exacta", {"xs": ints}, lambda xs: fn(xs) == float(Fraction(sum(xs), len(xs)))),
        forall("mean(floats) == media exacta", {"xs": dyad}, lambda xs: fn(xs) == float(sum(Fraction(x) for x in xs) / len(xs))),
        forall("min <= mean <= max", {"xs": ints}, lambda xs: min(xs) <= fn(xs) <= max(xs)),
        forall("mean invariante al orden", {"xs": ints}, lambda xs: fn(xs) == fn(list(reversed(xs)))),
        forall("mean([]) is None", {"xs": [[]]}, lambda xs: fn(xs) is None),
    ]
'''
SPEC = Spec("mean", "mean", CONTRACT, intent="Media aritmética; lista vacía -> None, nunca lanza.")


class Stub:
    def __init__(self): self.replies = [TRICKY, GOOD]
    def propose(self, spec, src, ev):
        for r in ev["rejections"]:
            print("   agente recibe rechazo:", r[0][:160])
        return self.replies.pop(0)


def traffic(svc, n=60):
    errs = 0
    for i in range(n):
        xs = [] if i % 4 == 3 else [float(i), float(i + 1), float(i + 2)]
        try: svc(xs)
        except Exception: errs += 1
    return errs


def run(label, verifier):
    print(f"\n== {label} ==")
    ledger = Ledger()
    svc = SelfHealing(SPEC, BUGGY, Stub(), autonomy=Autonomy.AUTO, ledger=ledger, verifier=verifier,
                      fallback=lambda xs: None)
    traffic(svc)
    print("   eventos:", " > ".join(ledger.events()))
    final = "CORRECTO" if "isinstance" not in svc.src and "if not xs" in svc.src else "INCORRECTO (con bug de enteros)"
    print("   versión instalada:", final, "| mean([0, 1]) =", svc._fn([0, 1]), "(esperado 0.5)")
    return svc


if __name__ == "__main__":
    run("verificador base de autoheal (pruebas aleatorias)", SubprocessVerifier())
    run("FormalVerifier (exhaustivo en dominio declarado)", FormalVerifier({"mean": PROOF}))
