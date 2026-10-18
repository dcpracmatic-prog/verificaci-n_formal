/* GENERADO por proofs/gen_obligations.py desde contracts/matmul.yaml. NO editar a mano.
 * Estado: NO ejecutado con CBMC en la sesión de generación (CBMC no disponible). Compila y corre con smoke_cbmc.py.
 * Ejecutar:  cbmc matmul_invalid.c -I upstream/commonweave_zero/c_src --bounds-check --pointer-check --signed-overflow-check \
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
    size_t m = nondet_size_t();
    size_t k = nondet_size_t();
    size_t n = nondet_size_t();
    __CPROVER_assume((m < 1 || m > 10000) || (k < 1 || k > 10000) || (n < 1 || n > 10000));
    double *A = malloc((1) * sizeof(double));
    __CPROVER_assume(A != NULL);
    double *B = malloc((1) * sizeof(double));
    __CPROVER_assume(B != NULL);
    double *C = malloc((1) * sizeof(double));
    __CPROVER_assume(C != NULL);
    int rc = matmul(A, B, C, m, k, n);
    __CPROVER_assert(rc >= 2 && rc <= 3, "violación de rango debe devolver DIM (2) u OVERFLOW (3) y no tocar memoria");
    return 0;
}
