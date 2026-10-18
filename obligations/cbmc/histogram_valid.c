/* GENERADO por proofs/gen_obligations.py desde contracts/stats.yaml. NO editar a mano.
 * Estado: NO ejecutado con CBMC en la sesión de generación (CBMC no disponible). Compila y corre con smoke_cbmc.py.
 * Ejecutar:  cbmc histogram_valid.c -I upstream/commonweave_zero/c_src --bounds-check --pointer-check --signed-overflow-check \
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
    __CPROVER_assume(len >= 1 && len <= 3);
    __CPROVER_assume(nbins >= 1 && nbins <= 3);
    __CPROVER_assume(hi > lo);    /* requires del contrato */
    int32_t *data = malloc((len) * sizeof(int32_t));
    __CPROVER_assume(data != NULL);
    uint32_t *bins = malloc((nbins) * sizeof(uint32_t));
    __CPROVER_assume(bins != NULL);
    int rc = histogram(data, len, lo, hi, bins, nbins);
    __CPROVER_assert(rc == 0, "entrada válida debe devolver CW_OK");
    return 0;
}
