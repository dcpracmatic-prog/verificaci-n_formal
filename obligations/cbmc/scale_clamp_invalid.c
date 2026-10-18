/* GENERADO por proofs/gen_obligations.py desde contracts/matmul.yaml. NO editar a mano.
 * Estado: NO ejecutado con CBMC en la sesión de generación (CBMC no disponible). Compila y corre con smoke_cbmc.py.
 * Ejecutar:  cbmc scale_clamp_invalid.c -I upstream/commonweave_zero/c_src --bounds-check --pointer-check --signed-overflow-check \
 *            --unsigned-overflow-check --conversion-check --float-overflow-check --nan-check --unwind 6 --unwinding-assertions
 */
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#ifdef FV_GCC_SMOKE
#  include "smoke_stub.h"
#else
size_t nondet_size_t(void); int32_t nondet_int32(void); double nondet_double(void);
#endif
#include "matmul.c"
int main(void) {
    size_t len = nondet_size_t();
    double scale = nondet_double();
    double lo = nondet_double();
    double hi = nondet_double();
    __CPROVER_assume((len < 1 || len > 1000000));
    double *in = malloc((1) * sizeof(double));
    __CPROVER_assume(in != NULL);
    double *out = malloc((1) * sizeof(double));
    __CPROVER_assume(out != NULL);
    int rc = scale_clamp(in, out, len, scale, lo, hi);
    __CPROVER_assert(rc >= 2 && rc <= 3, "violación de rango debe devolver DIM (2) u OVERFLOW (3) y no tocar memoria");
    return 0;
}
