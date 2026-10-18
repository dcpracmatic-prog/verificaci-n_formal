"""Comprueba que los arneses CBMC generados COMPILAN con gcc y que, ejecutados con un driver aleatorio
(ASan+UBSan), el código real satisface sus asserts. NO es verificación (solo muestrea); es una prueba de
cordura de que los arneses están bien formados mientras no haya CBMC disponible."""
from __future__ import annotations
import glob, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = r'''
#undef main
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
jmp_buf fv_jb;
int harness_main(void);
int main(void) {
    srand(12345); int ran = 0, assumed_out = 0;
    for (int i = 0; i < 4000; i++) { if (setjmp(fv_jb) == 0) { harness_main(); ran++; } else assumed_out++; }
    printf("ejecuciones=%d descartadas_por_assume=%d\\n", ran, assumed_out);
    return ran > 0 ? 0 : 3;
}
'''


def run():
    res = []
    csrc = os.path.join(ROOT, "upstream", "commonweave_zero", "c_src")
    files = sorted(glob.glob(os.path.join(ROOT, "obligations", "cbmc", "*_*.c")))
    if not files:
        return [("obligations/cbmc", False, "No se encontraron arneses C (*.c); ejecuta gen_obligations.generate() primero.")]
    with tempfile.TemporaryDirectory() as t:
        driver_path = os.path.join(t, "driver.c")
        with open(driver_path, "w", encoding="utf-8") as driver_file:
            driver_file.write(DRIVER)
        for f in files:
            exe = os.path.join(t, "x")
            name = os.path.basename(f)
            cmd = ["gcc", "-std=gnu11", "-g", "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                   "-DFV_GCC_SMOKE", "-Dmain=harness_main", f"-I{csrc}", f"-I{os.path.dirname(f)}",
                   f, driver_path, "-o", exe, "-lm"]
            try:
                c = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if c.returncode:
                    res.append((name, False, "NO COMPILA (gcc exit " + str(c.returncode) + "): " + c.stderr[-1200:]))
                    continue
                r = subprocess.run([exe], capture_output=True, text=True,
                                   env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"), timeout=30)
                msg = (r.stdout + r.stderr).strip()[-1200:]
                res.append((name, r.returncode == 0, msg if msg else f"proceso terminó con código {r.returncode}"))
            except subprocess.TimeoutExpired as exc:
                detail = (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
                res.append((name, False, f"TIMEOUT: el proceso superó el límite. {detail[-800:]}"))
            except OSError as exc:
                res.append((name, False, f"ERROR DE ENTORNO al compilar/ejecutar: {type(exc).__name__}: {exc}"))
    return res


if __name__ == "__main__":
    allok = True
    for n, ok, msg in run():
        print(("OK   " if ok else "FALLA"), n, "|", msg.replace("\\n", " "))
        allok &= ok
    sys.exit(0 if allok else 1)
