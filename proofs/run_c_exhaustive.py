"""Compila el C real de commonweave con ASan+UBSan, lo ejecuta en el arnés exhaustivo y
comprueba con MUTANTES que el arnés realmente detecta C roto (un verificador que no puede
fallar no prueba nada)."""
from __future__ import annotations
import os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSRC = os.path.join(ROOT, "upstream", "commonweave_zero", "c_src")
HARNESS = os.path.join(ROOT, "proofs", "c_exhaustive", "harness.c")

# (nombre, archivo, texto original, texto mutado)
MUTANTS = [
    ("matmul: bucle p<=k (lectura fuera de rango)", "matmul.c", "p < k", "p <= k"),
    ("matmul: índice A[i*n+p] (valor incorrecto)", "matmul.c", "A[i * k + p]", "A[i * n + p]"),
    ("matmul: sin chequeo de alineación", "matmul.c", "if (((uintptr_t)A | (uintptr_t)B | (uintptr_t)C) & 7u)", "if (0)"),
    ("matmul: límite 10000 -> 10001", "matmul.c", "m > 10000 || k > 10000 || n > 10000", "m > 10001 || k > 10000 || n > 10000"),
    ("scale_clamp: sin cota superior", "matmul.c", "if (v > hi) v = hi;", ""),
    ("scale_clamp: sin cota inferior", "matmul.c", "if (v < lo) v = lo;", ""),
    ("array_stats: suma en int32 (overflow)", "stats.c", "int64_t sum = 0;", "int32_t sum = 0;"),
    ("array_stats: varianza muestral (len-1)", "stats.c", "out->variance = acc / (double)len;", "out->variance = acc / (double)(len > 1 ? len - 1 : 1);"),
    ("array_stats: min mal calculado", "stats.c", "if (data[i] < mn) mn = data[i];", "if (data[i] > mn) mn = data[i];"),
    ("histogram: incluye hi (v > hi) -> bin fuera de rango", "stats.c", "if (v < lo || v >= hi) continue;", "if (v < lo || v > hi) continue;"),
    ("histogram: resta en int32 (overflow UB)", "stats.c", "((int64_t)v - (int64_t)lo)", "((int32_t)v - (int32_t)lo)"),
    ("histogram: bins += 2", "stats.c", "bins[b] += 1;", "bins[b] += 2;"),
    ("histogram: no pone bins a cero", "stats.c", "for (size_t b = 0; b < nbins; ++b) bins[b] = 0;", ""),
    ("histogram: límite nbins 4096 -> 4097", "stats.c", "nbins > 4096", "nbins > 4097"),
]


def _build_run(csrc_dir: str, workdir: str, cc: str = "gcc"):
    exe = os.path.join(workdir, "harness")
    cmd = [cc, "-O1", "-g", "-std=gnu11", "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
           f"-I{csrc_dir}", f'-DMATMUL_C="{csrc_dir}/matmul.c"', f'-DSTATS_C="{csrc_dir}/stats.c"',
           HARNESS, "-o", exe, "-lm"]
    try:
        b = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, f"COMPILER ERROR ({type(exc).__name__}): {exc}"
    if b.returncode != 0:
        return -1, "COMPILE ERROR:\\n" + b.stderr[-1500:]
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")
    try:
        r = subprocess.run([exe], capture_output=True, text=True, env=env, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, f"EXECUTION ERROR ({type(exc).__name__}): {exc}"
    return r.returncode, r.stdout + r.stderr


def run(verbose: bool = True):
    with tempfile.TemporaryDirectory() as tmp:
        code, out = _build_run(CSRC, tmp)
        proofs = []
        fn_lines = re.findall(r"FN (\\w+) cases=(\\d+) fails=(\\d+) domain=(.*)", out)
        for name, cases, fails, dom in fn_lines:
            ok = code == 0 and int(fails) == 0
            proofs.append({
                "name": f"C/{name}: exhaustivo + ASan/UBSan", "kind": "EXHAUSTIVE_C_ASAN",
                "status": "PROVEN" if ok else "REFUTED",
                "statement": f"Para TODA entrada de [{dom}]: código de retorno correcto, resultado = oráculo independiente, "
                             f"salida intacta en error, sin UB/OOB detectable.",
                "cases": int(cases), "counterexample": None if ok else {"salida": out[-600:]},
                "trusted": "gcc, ASan/UBSan, libc, oráculo escrito en el arnés"})
        if not fn_lines:
            proofs.append({"name": "C: arnés", "kind": "EXHAUSTIVE_C_ASAN", "status": "REFUTED",
                           "statement": "el arnés no produjo resultados", "cases": 0,
                           "counterexample": {"salida": out[-800:]}, "trusted": ""})
        killed, survived, mut = 0, [], []
        for desc, fname, old, new in MUTANTS:
            d = os.path.join(tmp, "m")
            shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(CSRC, d)
            p = os.path.join(d, fname)
            with open(p, encoding="utf-8") as source_file:
                s = source_file.read()
            if s.count(old) != 1:
                raise RuntimeError(f"mutante mal definido ({desc}): {s.count(old)} apariciones de {old!r}")
            with open(p, "w", encoding="utf-8") as target_file:
                target_file.write(s.replace(old, new))
            c2, o2 = _build_run(d, tmp)
            dead = c2 != 0
            killed += dead
            if not dead:
                survived.append(desc)
            how = "no compila" if c2 == -1 else ("sanitizer" if "ERROR: AddressSanitizer" in o2 or "runtime error" in o2
                                                  else ("fallo de aserción" if dead else "SOBREVIVIÓ"))
            mut.append((desc, dead, how))
        if verbose:
            for desc, dead, how in mut:
                print(f"  mutante {'MUERTO   ' if dead else 'SOBREVIVE '} [{how}] {desc}")
        return proofs, {"total": len(MUTANTS), "killed": killed, "survived": survived,
                        "detail": [{"mutant": d, "killed": k, "how": h} for d, k, h in mut]}, out


if __name__ == "__main__":
    proofs, mut, out = run()
    print(out)
    print(f"mutantes: {mut['killed']}/{mut['total']} detectados")
    sys.exit(0 if all(p["status"] == "PROVEN" for p in proofs) and not mut["survived"] else 1)
