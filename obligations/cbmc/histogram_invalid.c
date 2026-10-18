/* GENERADO por proofs/gen_obligations.py desde contracts/stats.yaml. NO editar a mano.
 * Estado: NO ejecutado con CBMC en la sesión de generación (CBMC no disponible). Compila y corre con smoke_cbmc.py.
 * Ejecutar:  cbmc histogram_invalid.c -I upstream/commonweave_zero/c_src --bounds-check --pointer-check --signed-overflow-check \
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
#include "stats.c"
int main(void) {
    size_t len = nondet_size_t();
    int32_t lo = nondet_int32();
    int32_t hi = nondet_int32();
    size_t nbins = nondet_size_t();
    __CPROVER_assume((len < 1 || len > 1000000) || (nbins < 1 || nbins > 4096) || !(hi > lo));
    int32_t *data = malloc((1) * sizeof(int32_t));
    __CPROVER_assume(data != NULL);
    uint32_t *bins = malloc((1) * sizeof(uint32_t));
    __CPROVER_assume(bins != NULL);
    int rc = histogram(data, len, lo, hi, bins, nbins);
    __CPROVER_assert(rc >= 2 && rc <= 3, "violación de rango debe devolver DIM (2) u OVERFLOW (3) y no tocar memoria");
    return 0;
}
