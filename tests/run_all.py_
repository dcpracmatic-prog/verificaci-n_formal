"""Punto de entrada único: ejecuta TODAS las pruebas y escribe report/certificate.json (+ RESUMEN.md).
Uso:  python run_all.py            (firma HMAC si defines la variable de entorno FV_KEY)
"""
import json, os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from fvcore import certificate
from proofs import lemmas, run_c_exhaustive, gen_obligations, smoke_cbmc

print("[1/4] Lemas aritméticos (rango completo del contrato)")
L = [p.to_dict() for p in lemmas.all_lemmas()]
print("[2/4] C real: exhaustivo + ASan/UBSan, y mutantes")
C, mut, _ = run_c_exhaustive.run(verbose=True)
print("[3/4] Obligaciones CBMC/SMT-LIB: generación + humo con gcc")
gen_obligations.generate()
smoke = smoke_cbmc.run()
print("[4/4] autoheal + FormalVerifier (función `mean`)")
sys.path.insert(0, os.path.join(ROOT, "examples"))
import demo_autoheal_formal as d
from integration.formal_autoheal import FormalVerifier
fv = FormalVerifier({"mean": d.PROOF})
rej, acc = fv.verify(d.TRICKY, d.SPEC), fv.verify(d.GOOD, d.SPEC)

files = [os.path.join(ROOT, f) for f in (
    "upstream/commonweave_zero/c_src/matmul.c", "upstream/commonweave_zero/c_src/stats.c", "upstream/commonweave_zero/c_src/stats.h",
    "upstream/commonweave_zero/contracts/matmul.yaml", "upstream/commonweave_zero/contracts/stats.yaml",
    "proofs/c_exhaustive/harness.c", "proofs/lemmas.py", "fvcore/exhaustive.py", "fvcore/intervals.py")]
files = [os.path.relpath(f) for f in files]
unrun = [f"obligations/cbmc/*.c (run_all.py no ejecuta CBMC: {len(smoke)} arneses compilan y pasan humo con gcc; CBMC se corre con obligations/run_cbmc.sh y en el workflow formal-solvers)",
         "obligations/smt2/*.smt2 (run_all.py no ejecuta Z3: 5 obligaciones; se corren con obligations/run_z3.sh y en el workflow formal-solvers)"]
cert = certificate.build(L + C + acc.proofs, files, unrun, key=os.environ.get("FV_KEY", "").encode() or None)
cert["mutation_check"] = mut
cert["autoheal_demo"] = {"parche_incorrecto_rechazado": not rej.ok, "contraejemplo": rej.failures[:1], "parche_correcto_aceptado": acc.ok}
cert["smoke_cbmc"] = [{"file": n, "ok": ok} for n, ok, _ in smoke]
os.makedirs(os.path.join(ROOT, "report"), exist_ok=True)
json.dump(cert, open(os.path.join(ROOT, "report", "certificate.json"), "w"), indent=2, ensure_ascii=False)

ok = (cert["summary"]["refuted"] == 0 and not mut["survived"] and all(o for _, o, _ in smoke) and not rej.ok and acc.ok)
lines = ["# Resumen de verificación", "", f"Pruebas PROVEN: **{cert['summary']['proven']}**, REFUTED: **{cert['summary']['refuted']}**",
         f"Mutantes detectados: **{mut['killed']}/{mut['total']}**", "",
         "| Prueba | Tipo | Estado | Casos | Enunciado |", "|---|---|---|---|---|"]
for p in cert["proofs"]:
    lines.append(f"| {p['name']} | {p['kind']} | {p['status']} | {p['cases']} | {p['statement'][:140].replace('|','/')} |")
lines += ["", "## No ejecutado por run_all.py", *[f"- {u}" for u in unrun], "", "## NO probado", *[f"- {n}" for n in cert["not_proven"]]]
open(os.path.join(ROOT, "report", "RESUMEN.md"), "w").write("\n".join(lines) + "\n")
print("\nRESULTADO:", "TODO OK" if ok else "HAY FALLOS", "| proven", cert["summary"]["proven"], "refuted", cert["summary"]["refuted"])
sys.exit(0 if ok else 1)
