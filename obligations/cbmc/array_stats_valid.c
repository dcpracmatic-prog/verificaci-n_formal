/* GENERADO por proofs/gen_obligations.py desde contracts/stats.yaml. NO editar a mano.
 * Estado: NO ejecutado con CBMC en la sesión de generación (CBMC no disponible). Compila y corre con smoke_cbmc.py.
 * Ejecutar:  cbmc array_stats_valid.c -I upstream/commonweave_zero/c_src --bounds-check --pointer-check --signed-overflow-check \
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
    __CPROVER_assume(len >= 1 && len <= 3);
    int32_t *data = malloc((len) * sizeof(int32_t));
    __CPROVER_assume(data != NULL);
    cw_stats *out = malloc((1) * sizeof(cw_stats));
    __CPROVER_assume(out != NULL);
    int rc = array_stats(data, len, out);
    __CPROVER_assert(rc == 0, "entrada válida debe devolver CW_OK");
    return 0;
}
