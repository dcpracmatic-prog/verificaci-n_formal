"""FormalVerifier: enchufa pruebas por exhaustión (fvcore) al lazo de autoheal.

autoheal ya dejaba el hueco ("la interfaz `verify` permite enchufar Dafny/Z3/CBMC/TLA+"). Esto lo llena
con lo que SÍ se puede demostrar sin dependencias: para cada función se registra un `proof_src` que define
`prove(fn, forall) -> [Proof, ...]`. El parche candidato solo se acepta si (1) pasa el verificador base de
autoheal (contrato + regresión + replay) Y (2) TODAS las pruebas resultan PROVEN. Un contraejemplo
refutado vuelve al agente en `rejections`, así que el proponente recibe el caso exacto que rompe su parche.

Las pruebas corren en un SUBPROCESO con timeout (aísla caídas y bucles infinitos; NO es un sandbox de
seguridad: para código no confiable usar contenedor).
"""
from __future__ import annotations
import json, os, subprocess, sys, tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "upstream", "autoheal"))
sys.path.insert(0, ROOT)
from autoheal.verify import SubprocessVerifier, VerifyResult   # noqa: E402
from autoheal.spec import Spec                                  # noqa: E402

PROOF_HARNESS = r'''
import json, sys
p = json.load(open(sys.argv[1]))
sys.path.insert(0, p["root"])
from fvcore.exhaustive import forall
out = {"proofs": [], "error": None}
try:
    ns = {}
    exec(p["candidate"], ns)
    fn = ns[p["entrypoint"]]
    ps = {}
    exec(p["proof"], ps)
    out["proofs"] = [x.to_dict() for x in ps["prove"](fn, forall)]
except BaseException as e:
    out["error"] = "%s: %s" % (type(e).__name__, e)
print(json.dumps(out, default=str))
'''


@dataclass
class FormalResult(VerifyResult):
    proofs: List[dict] = field(default_factory=list)


class FormalVerifier(SubprocessVerifier):
    def __init__(self, proofs: Dict[str, str], timeout_s: float = 5.0, proof_timeout_s: float = 60.0,
                 require_proof: bool = True, ledger=None):
        super().__init__(timeout_s)
        self.proofs, self.proof_timeout_s, self.require_proof, self.ledger = proofs, proof_timeout_s, require_proof, ledger
        self.history: List[FormalResult] = []

    def verify(self, candidate: str, spec: Spec, regression: Sequence[Sequence[Any]] = (),
               replay: Sequence[Tuple[Sequence[Any], Any]] = ()) -> FormalResult:
        base = super().verify(candidate, spec, regression, replay)
        if not base.ok:                                       # barato primero
            return self._done(FormalResult(False, base.failures, []), spec, "base")
        proof_src = self.proofs.get(spec.name)
        if proof_src is None:
            if self.require_proof:
                return self._done(FormalResult(False, ["sin prueba formal registrada para " + spec.name], []), spec, "sin_prueba")
            return self._done(FormalResult(True, [], []), spec, "sin_prueba_permitido")
        with tempfile.TemporaryDirectory() as d:
            hp, pp = os.path.join(d, "h.py"), os.path.join(d, "p.json")
            open(hp, "w").write(PROOF_HARNESS)
            json.dump({"candidate": candidate, "entrypoint": spec.entrypoint, "proof": proof_src, "root": ROOT}, open(pp, "w"))
            try:
                r = subprocess.run([sys.executable, "-I", hp, pp], cwd=d, capture_output=True, text=True,
                                   timeout=self.proof_timeout_s)
            except subprocess.TimeoutExpired:
                return self._done(FormalResult(False, [f"prueba formal: timeout > {self.proof_timeout_s}s"], []), spec, "timeout")
            if r.returncode != 0:
                return self._done(FormalResult(False, ["prueba formal: proceso falló: " + r.stderr.strip()[-200:]], []), spec, "crash")
            try:
                out = json.loads(r.stdout.strip().splitlines()[-1])
            except Exception:
                return self._done(FormalResult(False, ["prueba formal: salida ilegible"], []), spec, "ilegible")
        if out["error"]:
            return self._done(FormalResult(False, ["prueba formal: " + out["error"]], []), spec, "error")
        fails = [f"REFUTADA «{p['name']}» tras {p['cases']} casos; contraejemplo: {p['counterexample']}"
                 for p in out["proofs"] if p["status"] != "PROVEN"]
        if not out["proofs"] and self.require_proof:
            fails.append("la función prove() no devolvió ninguna prueba")
        return self._done(FormalResult(not fails, fails, out["proofs"]), spec, "formal")

    def _done(self, res: FormalResult, spec: Spec, stage: str) -> FormalResult:
        self.history.append(res)
        if self.ledger is not None:
            self.ledger.log("formal_check", stage=stage, ok=res.ok,
                            proofs=[{"name": p["name"], "status": p["status"], "cases": p["cases"], "statement": p["statement"]}
                                    for p in res.proofs])
        return res
