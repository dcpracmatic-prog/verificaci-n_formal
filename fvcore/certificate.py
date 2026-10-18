"""Certificado de verificación: qué se probó, sobre qué archivos (SHA-256) y qué NO se probó.

Firma opcional HMAC-SHA256 (mismo esquema que lazo.security): demuestra que el
certificado no fue alterado después de generarse; NO demuestra que las pruebas sean correctas.
"""
from __future__ import annotations
import hashlib, hmac, json, platform, sys, time
from typing import Iterable, List, Optional

NOT_PROVEN = [
    "Corrección total del programa respecto a una especificación formal completa (aquí las especificaciones son propiedades parciales).",
    "Comportamiento de punto flotante más allá de lo comprobado (error de redondeo, NaN, inf no modelados salvo donde se indica).",
    "Ausencia de errores en el compilador, el enlazador, libc, el SO o el hardware (base de confianza no verificada).",
    "Entradas fuera de los dominios finitos declarados en cada prueba EXHAUSTIVE.",
    "Concurrencia: ningún componente analizado es concurrente.",
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def build(proofs: Iterable[dict], files: Iterable[str], unrun: Optional[List[str]] = None,
          key: Optional[bytes] = None) -> dict:
    proofs = list(proofs)
    cert = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version.split()[0], "platform": platform.platform(),
        "files_sha256": {p: sha256_file(p) for p in files},
        "proofs": proofs,
        "summary": {
            "proven": sum(p["status"] == "PROVEN" for p in proofs),
            "refuted": sum(p["status"] == "REFUTED" for p in proofs),
        },
        "unrun_obligations": unrun or [],
        "not_proven": NOT_PROVEN,
    }
    if key:
        cert["hmac_sha256"] = _mac(key, cert)
    return cert


def _mac(key: bytes, cert: dict) -> str:
    body = {k: v for k, v in cert.items() if k != "hmac_sha256"}
    return hmac.new(key, json.dumps(body, sort_keys=True).encode(), hashlib.sha256).hexdigest()


def verify_signature(cert: dict, key: bytes) -> bool:
    return "hmac_sha256" in cert and hmac.compare_digest(cert["hmac_sha256"], _mac(key, cert))
