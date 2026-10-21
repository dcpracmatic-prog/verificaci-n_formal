"""Genera obligaciones de prueba para herramientas externas a partir de los contratos YAML:

  obligations/cbmc/<fn>_valid.c    CBMC: para entradas válidas (dims acotadas) rc==OK y sin violaciones de memoria/overflow
  obligations/cbmc/<fn>_invalid.c  CBMC: para CUALQUIER valor de size_t fuera de contrato -> rc de error, sin tocar memoria
  obligations/smt2/*.smt2          Z3: los lemas aritméticos de lemmas.py, re-probados por un solver (esperado: unsat)

IMPORTANTE: en la sesión que generó este paquete no había CBMC ni Z3 (PyPI/apt bloqueados). Lo único que se
comprobó aquí es que los arneses COMPILAN y se comportan bien con un driver concreto (smoke_cbmc.py).
Nadie ha ejecutado CBMC/Z3 sobre ellos todavía: ver obligations/run_cbmc.sh y run_z3.sh.
"""
from __future__ import annotations
import os, sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACTS = os.path.join(ROOT, "upstream", "commonweave_zero", "contracts")
OUT = os.path.join(ROOT, "obligations")
BOUND = 3        # cota de dimensiones para CBMC (documentada; subirla aumenta el costo)
CT = {"float64": "double", "int32": "int32_t", "uint32": "uint32_t", "size_t": "size_t", "int": "int"}
SRC_OF = {"matmul.yaml": "matmul.c", "stats.yaml": "stats.c"}
HEADER = """/* GENERADO por proofs/gen_obligations.py desde contracts/{yaml}. NO editar a mano.
 * Estado: NO ejecutado con CBMC en la sesión de generación (CBMC no disponible). Compila y corre con smoke_cbmc.py.
 * Ejecutar:  cbmc {file} -I upstream/commonweave_zero/c_src --bounds-check --pointer-check --signed-overflow-check \\
 *            --unsigned-overflow-check --conversion-check --float-overflow-check --nan-check --unwind {unwind} --unwinding-assertions
 */
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#ifdef FV_GCC_SMOKE
#  include "smoke_stub.h"
#else
size_t nondet_size_t(void); int32_t nondet_int32(void); double nondet_double(void);
#endif
#include "{src}"
"""


def _elem(p, structs):
    e = p["element"]
    return CT.get(e, e) if e in CT or e in structs else (_ for _ in ()).throw(ValueError(f"tipo no soportado: {e}"))


def _alloc_size(p):
    shape = p.get("shape")
    return " * ".join(shape) if shape else "1"


def gen_function(contract: dict, fn: dict, valid: bool, yaml_name: str) -> str:
    structs = {s["name"] for s in contract.get("structs", [])}
    L = []
    consts = {}                       # nombre -> (lo, hi) de parámetros escalares restringidos
    for p in fn["parameters"]:
        if p["type"] == "size_t" and "constraints" in p:
            consts[p["name"]] = tuple(p["constraints"])
    L.append(f"int main(void) {{")
    # escalares
    for p in fn["parameters"]:
        if p["type"] == "pointer":
            continue
        t = CT[p["type"]]
        nd = {"size_t": "nondet_size_t", "int32": "nondet_int32", "float64": "nondet_double"}[p["type"]]
        L.append(f"    {t} {p['name']} = {nd}();")
    if valid:
        for n, (lo, hi) in consts.items():
            L.append(f"    __CPROVER_assume({n} >= {lo} && {n} <= {min(hi, BOUND)});")
        for r in fn.get("requires", []):
            L.append(f"    __CPROVER_assume({r['expr']});    /* requires del contrato */")
    else:
        # fuera de contrato: al menos un parámetro restringido viola su rango; los demás válidos y pequeños
        viol = " || ".join(f"({n} < {lo} || {n} > {hi})" for n, (lo, hi) in consts.items())
        if fn.get("requires"):
            viol = " || ".join([viol] + [f"!({r['expr']})" for r in fn["requires"]])
        L.append(f"    __CPROVER_assume({viol});")
    # buffers: tamaño exacto (válido) o mínimo de 1 elemento (inválido: la función NO debe tocarlos)
    for p in fn["parameters"]:
        if p["type"] != "pointer":
            continue
        t = _elem(p, structs)
        cnt = _alloc_size(p) if valid else "1"
        L.append(f"    {t} *{p['name']} = malloc(({cnt}) * sizeof({t}));")
        L.append(f"    __CPROVER_assume({p['name']} != NULL);")
    args = ", ".join(p["name"] for p in fn["parameters"])
    L.append(f"    int rc = {fn['name']}({args});")
    if valid:
        L.append('    __CPROVER_assert(rc == 0, "entrada válida debe devolver CW_OK");')
    else:
        L.append('    __CPROVER_assert(rc >= 2 && rc <= 3, "violación de rango debe devolver DIM (2) u OVERFLOW (3) y no tocar memoria");')
    L.append("    return 0;\n}")
    return "\n".join(L)


def generate():
    os.makedirs(os.path.join(OUT, "cbmc"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "smt2"), exist_ok=True)
    made = []
    for yn, src in SRC_OF.items():
        contract = yaml.safe_load(open(os.path.join(CONTRACTS, yn)))
        for fn in contract["functions"]:
            for valid in (True, False):
                suffix = "valid" if valid else "invalid"
                fname = f"{fn['name']}_{suffix}.c"
                body = HEADER.format(yaml=yn, file=fname, src=src, unwind=BOUND + 3) + gen_function(contract, fn, valid, yn) + "\n"
                open(os.path.join(OUT, "cbmc", fname), "w").write(body)
                made.append(os.path.join("cbmc", fname))
    # stub para compilar con gcc (smoke)
    open(os.path.join(OUT, "cbmc", "smoke_stub.h"), "w").write(STUB)
    made += gen_smt()
    open(os.path.join(OUT, "run_cbmc.sh"), "w").write(RUN_CBMC)
    open(os.path.join(OUT, "run_z3.sh"), "w").write(RUN_Z3)
    for s in ("run_cbmc.sh", "run_z3.sh"):
        os.chmod(os.path.join(OUT, s), 0o755)
    return made


STUB = r'''/* Solo para FV_GCC_SMOKE: simula nondet con rand() y assume con longjmp. NO es verificación. */
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
extern jmp_buf fv_jb;
static inline size_t nondet_size_t(void) { return (size_t)(rand() % 9) + (rand() % 7 == 0 ? 10000u : 0u) + (rand() % 11 == 0 ? 1000000u : 0u); }
static inline int32_t nondet_int32(void) { int c = rand() % 4; return c == 0 ? INT32_MIN : c == 1 ? INT32_MAX : (int32_t)(rand() % 21) - 10; }
static inline double nondet_double(void) { return (double)(rand() % 21) - 10.0; }
#define __CPROVER_assume(c) do { if (!(c)) longjmp(fv_jb, 1); } while (0)
#define __CPROVER_assert(c, m) do { if (!(c)) { fprintf(stderr, "ASSERT FALLÓ: %s\n", m); abort(); } } while (0)
'''

RUN_CBMC = r"""#!/bin/sh
# Requiere CBMC (https://github.com/diffblue/cbmc). Ejecutar desde la raíz del paquete.
# Estado por arnés: PROBADO (cbmc sale 0), REFUTADO (sale 10: contraejemplo) o NO RESUELTO (timeout u otro error).
# Código de salida: 0 todo PROBADO | 1 hay algún REFUTADO | 2 sin refutados pero con NO RESUELTO.
# Variables: CBMC_TIMEOUT (segundos por arnés, 600 por defecto), CBMC_ONLY (filtro por nombre).
TMO=${CBMC_TIMEOUT:-600}
proven=0; refuted=0; unresolved=0
for f in obligations/cbmc/*_valid.c obligations/cbmc/*_invalid.c; do
  case "$f" in *"${CBMC_ONLY:-}"*) ;; *) continue ;; esac
  log=$(mktemp)
  timeout "$TMO" cbmc "$f" -I upstream/commonweave_zero/c_src -I obligations/cbmc \
       --bounds-check --pointer-check --signed-overflow-check --unsigned-overflow-check --conversion-check \
       --float-overflow-check --nan-check --unwind 8 --unwinding-assertions --object-bits 12 > "$log" 2>&1
  rc=$?
  if [ $rc -eq 0 ] && grep -q "VERIFICATION SUCCESSFUL" "$log"; then
    echo "PROBADO      $f"; proven=$((proven+1))
  elif [ $rc -eq 10 ]; then
    echo "REFUTADO     $f"; refuted=$((refuted+1)); grep "FAILURE" "$log" | head -5
  elif [ $rc -eq 124 ] || [ $rc -eq 137 ]; then
    echo "NO RESUELTO  $f (tiempo agotado: ${TMO}s)"; unresolved=$((unresolved+1))
  else
    echo "NO RESUELTO  $f (cbmc salió con código $rc)"; tail -3 "$log"; unresolved=$((unresolved+1))
  fi
  rm -f "$log"
done
echo "RESUMEN CBMC: PROBADO=$proven REFUTADO=$refuted NO_RESUELTO=$unresolved"
[ $refuted -gt 0 ] && exit 1
[ $unresolved -gt 0 ] && exit 2
exit 0
"""

RUN_Z3 = r"""#!/bin/sh
# Requiere Z3. Cada archivo debe responder 'unsat' (la negación de la propiedad es insatisfacible = propiedad probada).
# Estado: PROBADO (unsat), REFUTADO (sat: contraejemplo) o NO RESUELTO (unknown, timeout o error).
# Código de salida: 0 todo PROBADO | 1 hay algún REFUTADO | 2 sin refutados pero con NO RESUELTO.
proven=0; refuted=0; unresolved=0
for f in obligations/smt2/*.smt2; do
  r=$(z3 -T:120 "$f" 2>&1 | head -1)
  case "$r" in
    unsat) echo "PROBADO      $f"; proven=$((proven+1)) ;;
    sat)   echo "REFUTADO     $f"; refuted=$((refuted+1)) ;;
    *)     echo "NO RESUELTO  $f ($r)"; unresolved=$((unresolved+1)) ;;
  esac
done
echo "RESUMEN Z3: PROBADO=$proven REFUTADO=$refuted NO_RESUELTO=$unresolved"
[ $refuted -gt 0 ] && exit 1
[ $unresolved -gt 0 ] && exit 2
exit 0
"""



def gen_smt():
    d = os.path.join(OUT, "smt2")
    files = []

    def w(name, body, desc):
        open(os.path.join(d, name), "w").write(f"; {desc}\n; Esperado: unsat (la negación de la propiedad no tiene modelo). NO ejecutado en la sesión de generación.\n{body}")
        files.append("smt2/" + name)

    for nm, (rows, cols, r, c) in {"matmul_A": ("m", "k", "i", "p"), "matmul_B": ("k", "n", "p", "j"), "matmul_C": ("m", "n", "i", "j")}.items():
        w(f"{nm}_index.smt2", f"""(set-logic NIA)
(declare-const {rows} Int) (declare-const {cols} Int) (declare-const {r} Int) (declare-const {c} Int)
(assert (and (<= 1 {rows} 10000) (<= 1 {cols} 10000) (<= 0 {r}) (< {r} {rows}) (<= 0 {c}) (< {c} {cols})))
(assert (not (and (<= 0 (+ (* {r} {cols}) {c})) (< (+ (* {r} {cols}) {c}) (* {rows} {cols})) (< (* {rows} {cols}) 18446744073709551616))))
(check-sat)
""", f"{nm}: 0 <= {r}*{cols}+{c} < {rows}*{cols} < 2^64 para todo el rango del contrato")
    w("histogram_bin.smt2", """(set-logic NIA)
(declare-const lo Int) (declare-const hi Int) (declare-const v Int) (declare-const nbins Int)
(assert (and (<= -2147483648 lo 2147483647) (<= -2147483648 hi 2147483647) (<= -2147483648 v 2147483647)))
(assert (and (> hi lo) (>= v lo) (< v hi) (<= 1 nbins 4096)))
(define-fun x () Int (* (- v lo) nbins))
(define-fun b () Int (div x (- hi lo)))
(assert (not (and (<= 0 b) (< b nbins) (< x 9223372036854775808) (< (- hi lo) 9223372036854775808))))
(check-sat)
""", "histogram: 0 <= bin < nbins y sin overflow de int64, para todo int32 lo<hi, v en [lo,hi), nbins en [1,4096]")
    w("array_stats_sum.smt2", """(set-logic NIA)
(declare-const len Int) (declare-const s Int)
(assert (and (<= 1 len 1000000) (<= (* (- 2147483648) len) s) (<= s (* 2147483647 len))))
(assert (not (and (<= (- 9223372036854775808) s) (< s 9223372036854775808))))
(check-sat)
""", "array_stats: la suma acumulada de len<=1e6 int32 cabe en int64")
    return files


if __name__ == "__main__":
    for f in generate():
        print("generado", f)
