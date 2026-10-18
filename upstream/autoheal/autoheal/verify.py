"""Verificador de parches. Corre el candidato en un SUBPROCESO con timeout.

Comprueba tres cosas: (1) el contrato de la intención, (2) que las entradas que
fallaron ya no fallan, (3) que el comportamiento observado en tráfico exitoso
no cambió (replay).

LÍMITES HONESTOS:
- Esto es verificación por propiedades aleatorias + regresión, NO prueba formal.
  La interfaz `verify` permite enchufar Dafny/Z3/CBMC/TLA+ en su lugar.
- El subproceso aísla caídas y bucles infinitos, no es un sandbox de seguridad:
  para código no confiable usa contenedor/gVisor/Firecracker.
"""
from __future__ import annotations
import json, os, subprocess, sys, tempfile
from dataclasses import dataclass, field
from typing import Any, List, Sequence, Tuple

from .spec import Spec

HARNESS = r'''
import json, math, sys
p = json.load(open(sys.argv[1]))
fails = []
try:
    ns = {}
    exec(p["candidate"], ns)
    fn = ns[p["entrypoint"]]
    c = {}
    exec(p["contract"], c)
    fails += list(c["check"](fn))
    for args in p["regression"]:
        try:
            fn(*args)
        except Exception as e:
            fails.append("regresion %r: %s" % (args, type(e).__name__))
    for args, exp in p["replay"]:
        try:
            got = fn(*args)
        except Exception as e:
            fails.append("replay %r: %s" % (args, type(e).__name__)); continue
        num = isinstance(exp, (int, float)) and isinstance(got, (int, float))
        ok = math.isclose(got, exp, rel_tol=1e-9, abs_tol=1e-12) if num else got == exp
        if not ok:
            fails.append("replay %r: esperado %r, obtuvo %r" % (args, exp, got))
except BaseException as e:
    fails.append("harness: %s: %s" % (type(e).__name__, e))
print(json.dumps(fails[:20]))
'''


@dataclass
class VerifyResult:
    ok: bool
    failures: List[str] = field(default_factory=list)


class SubprocessVerifier:
    def __init__(self, timeout_s: float = 5.0):
        self.timeout_s = timeout_s

    def verify(self, candidate: str, spec: Spec,
               regression: Sequence[Sequence[Any]] = (),
               replay: Sequence[Tuple[Sequence[Any], Any]] = ()) -> VerifyResult:
        with tempfile.TemporaryDirectory() as d:
            hp, pp = os.path.join(d, "h.py"), os.path.join(d, "p.json")
            open(hp, "w").write(HARNESS)
            json.dump({"candidate": candidate, "entrypoint": spec.entrypoint,
                       "contract": spec.contract_src,
                       "regression": [list(a) for a in regression],
                       "replay": [[list(a), o] for a, o in replay]}, open(pp, "w"))
            try:
                r = subprocess.run([sys.executable, "-I", hp, pp], cwd=d, capture_output=True,
                                   text=True, timeout=self.timeout_s)
            except subprocess.TimeoutExpired:
                return VerifyResult(False, [f"timeout > {self.timeout_s}s"])
            if r.returncode != 0:
                return VerifyResult(False, ["proceso falló: " + r.stderr.strip()[-200:]])
            try:
                fails = json.loads(r.stdout.strip().splitlines()[-1])
            except Exception:
                return VerifyResult(False, ["salida del harness ilegible"])
            return VerifyResult(not fails, fails)
