"""Lazo de autorreparación: detectar -> aislar -> proponer -> verificar -> aplicar -> probar -> (rollback)."""
from __future__ import annotations
import json
from collections import deque
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Protocol, Tuple

from .detect import ErrorRateDetector
from .ledger import Ledger
from .spec import Spec
from .verify import SubprocessVerifier


class ServiceDegraded(RuntimeError):
    """Se lanza si el aislamiento está activo y no hay fallback."""


class Autonomy(str, Enum):
    SHADOW = "shadow"     # detecta, propone y verifica; no cambia nada
    PROPOSE = "propose"   # aísla y deja el parche verificado pendiente de aprobación humana
    AUTO = "auto"         # aplica el parche verificado y vigila con rollback automático


class Proposer(Protocol):
    """Aquí se enchufa el agente (LLM). Recibe intención, código y evidencia; devuelve código nuevo."""
    def propose(self, spec: Spec, current_src: str, evidence: Dict[str, Any]) -> str: ...


def _jsonable(x: Any) -> bool:
    try:
        json.dumps(x); return True
    except Exception:
        return False


class SelfHealing:
    def __init__(self, spec: Spec, src: str, proposer: Proposer,
                 autonomy: Autonomy = Autonomy.SHADOW,
                 verifier: Optional[SubprocessVerifier] = None,
                 detector: Optional[ErrorRateDetector] = None,
                 fallback: Optional[Callable[..., Any]] = None,
                 ledger: Optional[Ledger] = None,
                 max_attempts: int = 3, keep: int = 50,
                 probation_calls: int = 20, probation_max_error_rate: float = 0.3):
        self.spec, self.proposer, self.autonomy = spec, proposer, Autonomy(autonomy)
        self.verifier = verifier or SubprocessVerifier()
        self.detector = detector or ErrorRateDetector()
        self.fallback, self.ledger = fallback, ledger or Ledger()
        self.max_attempts, self.prob_calls, self.prob_rate = max_attempts, probation_calls, probation_max_error_rate
        self.failures: Deque[Tuple[list, str]] = deque(maxlen=keep)
        self.successes: Deque[Tuple[list, Any]] = deque(maxlen=keep)
        self.versions: List[str] = []
        self.pending: Optional[str] = None
        self.breaker_open = False
        self._prob: Optional[Dict[str, int]] = None
        self._shadow_reported: Optional[str] = None
        self.src = ""
        self._load(src)
        self.ledger.log("loaded", autonomy=self.autonomy.value)

    # ---- ejecución ----
    def _load(self, src: str) -> None:
        ns: Dict[str, Any] = {}
        exec(src, ns)
        self._fn = ns[self.spec.entrypoint]
        self.src = src

    def __call__(self, *args: Any) -> Any:
        if self.breaker_open:
            if self.fallback:
                return self.fallback(*args)
            raise ServiceDegraded(self.spec.name)
        try:
            out = self._fn(*args)
        except Exception as e:
            self._after(False, args, type(e).__name__)
            raise
        self._after(True, args, out)
        return out

    # ---- observación ----
    def _after(self, ok: bool, args: tuple, payload: Any) -> None:
        a = list(args)
        if _jsonable(a):
            if ok and _jsonable(payload):
                self.successes.append((a, payload))
            elif not ok:
                self.failures.append((a, payload))
        flagged = self.detector.add(ok)
        if self._prob is not None:
            self._prob["calls"] += 1
            self._prob["errors"] += int(not ok)
            c, e = self._prob["calls"], self._prob["errors"]
            if flagged or (c >= 5 and e / c >= self.prob_rate):
                self.rollback(f"anomalía en probation ({e}/{c} errores)"); return
            if c >= self.prob_calls:
                self._prob = None; self.ledger.log("probation_passed")
        if flagged and not self.breaker_open and self._shadow_reported != self.src:
            self.heal_now()

    # ---- reparación ----
    def heal_now(self) -> bool:
        evidence = {"failures": list(self.failures)[-10:], "rejections": []}
        self.ledger.log("anomaly_detected", failures=len(self.failures))
        if self.autonomy is Autonomy.SHADOW:
            self._shadow_reported = self.src      # en shadow se reporta una vez por versión
        if self.autonomy is not Autonomy.SHADOW:
            self.breaker_open = True
            self.ledger.log("isolated")
        for attempt in range(1, self.max_attempts + 1):
            cand = self.proposer.propose(self.spec, self.src, evidence)
            self.ledger.log("proposed", attempt=attempt)
            res = self.verifier.verify(cand, self.spec,
                                       regression=[a for a, _ in self.failures],
                                       replay=list(self.successes))
            self.ledger.log("verified", attempt=attempt, ok=res.ok, failures=res.failures)
            if not res.ok:
                evidence["rejections"].append(res.failures)
                continue
            if self.autonomy is Autonomy.SHADOW:
                self.ledger.log("would_apply"); self.detector.reset(); return True
            if self.autonomy is Autonomy.PROPOSE:
                self.pending = cand; self.ledger.log("pending_approval"); return True
            self._install(cand); return True
        self.ledger.log("gave_up", attempts=self.max_attempts)   # queda aislado: decide un humano
        return False

    def approve(self) -> bool:
        if self.pending is None:
            return False
        cand, self.pending = self.pending, None
        self.ledger.log("approved"); self._install(cand); return True

    def _install(self, cand: str) -> None:
        self.versions.append(self.src)
        self._load(cand)
        self.breaker_open = False
        self.detector.reset()
        self._prob = {"calls": 0, "errors": 0}
        self.ledger.log("applied", version=len(self.versions))

    def rollback(self, reason: str) -> None:
        if self.versions:
            self._load(self.versions.pop())
        self._prob = None
        self.breaker_open = True          # queda aislado hasta que un humano decida
        self.detector.reset()
        self.ledger.log("rolled_back", reason=reason)
