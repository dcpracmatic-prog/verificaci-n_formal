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
    printf("ejecuciones=%d descartadas_por_assume=%d\n", ran, assumed_out);
    return ran > 0 ? 0 : 3;
}
'''


def run():
    res = []
    csrc = os.path.join(ROOT, "upstream", "commonweave_zero", "c_src")
    with tempfile.TemporaryDirectory() as t:
        open(os.path.join(t, "driver.c"), "w").write(DRIVER)
        for f in sorted(glob.glob(os.path.join(ROOT, "obligations", "cbmc", "*_*.c"))):
            exe = os.path.join(t, "x")
            c = subprocess.run(["gcc", "-std=gnu11", "-g", "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                                "-DFV_GCC_SMOKE", "-Dmain=harness_main", f"-I{csrc}", f"-I{os.path.dirname(f)}",
                                f, os.path.join(t, "driver.c"), "-o", exe, "-lm"], capture_output=True, text=True)
            name = os.path.basename(f)
            if c.returncode:
                res.append((name, False, "NO COMPILA: " + c.stderr[-300:])); continue
            r = subprocess.run([exe], capture_output=True, text=True, env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0"))
            res.append((name, r.returncode == 0, (r.stdout + r.stderr).strip()[-300:]))
    return res


if __name__ == "__main__":
    allok = True
    for n, ok, msg in run():
        print(("OK   " if ok else "FALLA"), n, "|", msg.replace("\n", " "))
        allok &= ok
    sys.exit(0 if allok else 1)
