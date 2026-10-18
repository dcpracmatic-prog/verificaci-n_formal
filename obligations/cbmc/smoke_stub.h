/* Solo para FV_GCC_SMOKE: simula nondet con rand() y assume con longjmp. NO es verificación. */
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
extern jmp_buf fv_jb;
static inline size_t nondet_size_t(void) { return (size_t)(rand() % 9) + (rand() % 7 == 0 ? 10000u : 0u) + (rand() % 11 == 0 ? 1000000u : 0u); }
static inline int32_t nondet_int32(void) { int c = rand() % 4; return c == 0 ? INT32_MIN : c == 1 ? INT32_MAX : (int32_t)(rand() % 21) - 10; }
static inline double nondet_double(void) { return (double)(rand() % 21) - 10.0; }
#define __CPROVER_assume(c) do { if (!(c)) longjmp(fv_jb, 1); } while (0)
#define __CPROVER_assert(c, m) do { if (!(c)) { fprintf(stderr, "ASSERT FALLÓ: %s\n", m); abort(); } } while (0)
