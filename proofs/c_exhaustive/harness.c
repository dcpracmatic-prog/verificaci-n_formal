/* Verificación EXHAUSTIVA del C real de commonweave sobre dominios finitos declarados.
 *
 * El código bajo prueba se compila CON AddressSanitizer + UBSan (-fno-sanitize-recover):
 * cualquier lectura/escritura fuera de rango, overflow con signo, desplazamiento inválido, etc.
 * aborta el programa. Los buffers se reservan con el tamaño EXACTO (malloc), así que un
 * acceso de un solo byte fuera de rango se detecta.
 *
 * Qué es: una prueba de que para TODAS las entradas de los dominios de abajo, la función
 * devuelve el código correcto, calcula el resultado correcto contra un oráculo independiente,
 * no toca el buffer de salida en error y no tiene comportamiento indefinido detectable.
 * Qué NO es: una prueba para entradas fuera de esos dominios (para eso ver CBMC/SMT en obligations/).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include MATMUL_C
#include STATS_C

static long long cases, fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; if (fails <= 5) { printf("  FAIL: "); printf(__VA_ARGS__); printf("\n"); } } } while (0)
#define SENT 12345.5

static void report(const char *name, const char *dom) {
    printf("FN %s cases=%lld fails=%lld domain=%s\n", name, cases, fails, dom);
}
static long long total_fails = 0;

/* ---------------- matmul ---------------- */
static void t_matmul(void) {
    cases = fails = 0;
    const double vals[2] = {-1.0, 2.0};
    for (size_t m = 1; m <= 3; m++) for (size_t k = 1; k <= 3; k++) for (size_t n = 1; n <= 3; n++) {
        size_t na = m * k, nb = k * n, nc = m * n;
        double *A = malloc(na * 8), *B = malloc(nb * 8), *C = malloc(nc * 8);
        for (long code = 0; code < (1L << (na + nb)); code++) {
            for (size_t i = 0; i < na; i++) A[i] = vals[(code >> i) & 1];
            for (size_t j = 0; j < nb; j++) B[j] = vals[(code >> (na + j)) & 1];
            for (size_t c = 0; c < nc; c++) C[c] = SENT;
            int rc = matmul(A, B, C, m, k, n); cases++;
            CHECK(rc == CW_OK, "matmul rc=%d m=%zu k=%zu n=%zu", rc, m, k, n);
            for (size_t i = 0; i < m; i++) for (size_t j = 0; j < n; j++) {
                long long s = 0;
                for (size_t p = 0; p < k; p++) s += (long long)A[i*k+p] * (long long)B[p*n+j];
                CHECK(C[i*n+j] == (double)s, "matmul valor (%zu,%zu) m=%zu k=%zu n=%zu code=%ld", i, j, m, k, n, code);
            }
        }
        free(A); free(B); free(C);
    }
    /* caminos de error: salida intacta, códigos del contrato */
    double a[4] = {1,2,3,4}, b[4] = {1,2,3,4}, c[4];
    for (int i = 0; i < 4; i++) c[i] = SENT;
    #define ERR(call, want) do { int r = (call); cases++; CHECK(r == (want), "matmul err esperado %d obtuvo %d (" #call ")", want, r); \
        for (int q = 0; q < 4; q++) CHECK(c[q] == SENT, "matmul tocó C en error (" #call ")"); } while (0)
    ERR(matmul(NULL, b, c, 2, 2, 2), CW_ERR_NULL);
    ERR(matmul(a, NULL, c, 2, 2, 2), CW_ERR_NULL);
    ERR(matmul(a, b, NULL, 2, 2, 2), CW_ERR_NULL);
    ERR(matmul(a, b, c, 0, 2, 2), CW_ERR_DIM);
    ERR(matmul(a, b, c, 2, 0, 2), CW_ERR_DIM);
    ERR(matmul(a, b, c, 2, 2, 0), CW_ERR_DIM);
    ERR(matmul(a, b, c, 10001, 2, 2), CW_ERR_OVERFLOW);
    ERR(matmul(a, b, c, 2, 10001, 2), CW_ERR_OVERFLOW);
    ERR(matmul(a, b, c, 2, 2, 10001), CW_ERR_OVERFLOW);
    ERR(matmul(a, b, c, (size_t)-1, 2, 2), CW_ERR_OVERFLOW);
    ERR(matmul((double *)((char *)a + 1), b, c, 2, 2, 2), CW_ERR_ALIGN);
    ERR(matmul(a, (double *)((char *)b + 4), c, 2, 2, 2), CW_ERR_ALIGN);
    ERR(matmul(a, b, (double *)((char *)c + 2), 2, 2, 2), CW_ERR_ALIGN);
    report("matmul", "m,k,n in 1..3; entradas en {-1,2}; + 13 caminos de error");
    total_fails += fails;
}

/* ---------------- scale_clamp ---------------- */
static void t_scale_clamp(void) {
    cases = fails = 0;
    const double iv[4] = {-2, 0, 1, 3}, sv[3] = {-1, 0, 2}, lv[3] = {-1, 0, 2};
    for (size_t len = 1; len <= 3; len++) {
        double *in = malloc(len * 8), *out = malloc(len * 8);
        long tot = 1; for (size_t i = 0; i < len; i++) tot *= 4;
        for (long code = 0; code < tot; code++) {
            long cc = code; for (size_t i = 0; i < len; i++) { in[i] = iv[cc % 4]; cc /= 4; }
            for (int s = 0; s < 3; s++) for (int l = 0; l < 3; l++) for (int h = 0; h < 3; h++) {
                for (size_t i = 0; i < len; i++) out[i] = SENT;
                int rc = scale_clamp(in, out, len, sv[s], lv[l], lv[h]); cases++;
                CHECK(rc == CW_OK, "scale_clamp rc=%d", rc);
                for (size_t i = 0; i < len; i++) {
                    double v = in[i] * sv[s];
                    if (lv[l] <= lv[h]) {            /* contrato bien formado: out = clamp(v,lo,hi) */
                        double e = v < lv[l] ? lv[l] : (v > lv[h] ? lv[h] : v);
                        CHECK(out[i] == e && out[i] >= lv[l] && out[i] <= lv[h], "scale_clamp valor");
                    } else {                         /* lo>hi: el contrato NO lo excluye; se fija el comportamiento observado (=hi) */
                        CHECK(out[i] == lv[h], "scale_clamp lo>hi esperaba hi");
                    }
                }
            }
        }
        free(in); free(out);
    }
    double a[2] = {1, 2}, o[2] = {SENT, SENT};
    #define ERR2(call, want) do { int r = (call); cases++; CHECK(r == (want), "scale_clamp err %d vs %d (" #call ")", want, r); \
        CHECK(o[0] == SENT && o[1] == SENT, "scale_clamp tocó out en error"); } while (0)
    ERR2(scale_clamp(NULL, o, 2, 1, 0, 1), CW_ERR_NULL);
    ERR2(scale_clamp(a, NULL, 2, 1, 0, 1), CW_ERR_NULL);
    ERR2(scale_clamp(a, o, 0, 1, 0, 1), CW_ERR_DIM);
    ERR2(scale_clamp(a, o, 1000001, 1, 0, 1), CW_ERR_OVERFLOW);
    ERR2(scale_clamp((double *)((char *)a + 1), o, 2, 1, 0, 1), CW_ERR_ALIGN);
    ERR2(scale_clamp(a, (double *)((char *)o + 4), 2, 1, 0, 1), CW_ERR_ALIGN);
    report("scale_clamp", "len 1..3; in {-2,0,1,3}; scale,lo,hi en {-1,0,2} (incluye lo>hi); + 6 errores");
    total_fails += fails;
}

/* ---------------- array_stats ---------------- */
static void t_array_stats(void) {
    cases = fails = 0;
    const int32_t vals[3] = {-2, 0, 3};
    for (size_t len = 1; len <= 4; len++) {
        int32_t *d = malloc(len * 4); cw_stats *o = malloc(sizeof *o);
        long tot = 1; for (size_t i = 0; i < len; i++) tot *= 3;
        for (long code = 0; code < tot; code++) {
            long cc = code; for (size_t i = 0; i < len; i++) { d[i] = vals[cc % 3]; cc /= 3; }
            int rc = array_stats(d, len, o); cases++;
            CHECK(rc == CW_OK, "array_stats rc=%d", rc);
            long long s = 0; int32_t mn = d[0], mx = d[0];
            for (size_t i = 0; i < len; i++) { s += d[i]; if (d[i] < mn) mn = d[i]; if (d[i] > mx) mx = d[i]; }
            double num = 0; for (size_t i = 0; i < len; i++) { long long t = (long long)d[i] * (long long)len - s; num += (double)(t * t); }
            double var = num / ((double)len * (double)len * (double)len);   /* varianza poblacional exacta (racional) */
            CHECK(o->count == len && o->min == mn && o->max == mx, "array_stats count/min/max");
            CHECK(o->mean == (double)s / (double)len, "array_stats media");
            CHECK(fabs(o->variance - var) <= 1e-12 * (var > 1 ? var : 1), "array_stats varianza %g vs %g", o->variance, var);
        }
        free(d); free(o);
    }
    /* extremos de int32: sin overflow de la suma (int64), min/max exactos, varianza finita y >= 0 */
    const int32_t ex[3] = {INT32_MIN, 0, INT32_MAX};
    for (size_t len = 1; len <= 4; len++) {
        int32_t *d = malloc(len * 4); cw_stats *o = malloc(sizeof *o);
        long tot = 1; for (size_t i = 0; i < len; i++) tot *= 3;
        for (long code = 0; code < tot; code++) {
            long cc = code; for (size_t i = 0; i < len; i++) { d[i] = ex[cc % 3]; cc /= 3; }
            int rc = array_stats(d, len, o); cases++;
            long long s = 0; int32_t mn = d[0], mx = d[0];
            for (size_t i = 0; i < len; i++) { s += d[i]; if (d[i] < mn) mn = d[i]; if (d[i] > mx) mx = d[i]; }
            CHECK(rc == CW_OK && o->min == mn && o->max == mx && o->mean == (double)s / (double)len, "array_stats extremos");
            CHECK(isfinite(o->variance) && o->variance >= 0, "array_stats varianza extrema no finita");
        }
        free(d); free(o);
    }
    int32_t dd[2] = {1, 2}; cw_stats oo; memset(&oo, 0x5a, sizeof oo); cw_stats ref = oo;
    #define ERR3(call, want) do { int r = (call); cases++; CHECK(r == (want), "array_stats err %d vs %d (" #call ")", want, r); \
        CHECK(memcmp(&oo, &ref, sizeof oo) == 0, "array_stats tocó out en error"); } while (0)
    ERR3(array_stats(NULL, 2, &oo), CW_ERR_NULL);
    ERR3(array_stats(dd, 2, NULL), CW_ERR_NULL);
    ERR3(array_stats(dd, 0, &oo), CW_ERR_DIM);
    ERR3(array_stats(dd, 1000001, &oo), CW_ERR_OVERFLOW);
    ERR3(array_stats((int32_t *)((char *)dd + 1), 2, &oo), CW_ERR_ALIGN);
    ERR3(array_stats(dd, 2, (cw_stats *)((char *)&oo + 4)), CW_ERR_ALIGN);
    report("array_stats", "len 1..4; valores {-2,0,3} y {INT32_MIN,0,INT32_MAX}; + 6 errores");
    total_fails += fails;
}

/* ---------------- histogram ---------------- */
/* Oráculo por caracterización (no recalcula la fórmula): el bin b es el único con b*w <= (v-lo)*nbins < (b+1)*w */
static int oracle_bin(int32_t v, int32_t lo, int32_t hi, size_t nbins) {
    __int128 w = (__int128)hi - lo, x = ((__int128)v - lo) * (__int128)nbins;
    int found = -1;
    for (size_t b = 0; b < nbins; b++)
        if ((__int128)b * w <= x && x < ((__int128)b + 1) * w) { if (found >= 0) return -2; found = (int)b; }
    return found;
}
static void check_hist(const int32_t *d, size_t len, int32_t lo, int32_t hi, size_t nbins, uint32_t *bins, uint32_t *exp) {
    for (size_t b = 0; b < nbins; b++) bins[b] = 0xdeadbeef;
    int rc = histogram(d, len, lo, hi, bins, nbins); cases++;
    CHECK(rc == CW_OK, "histogram rc=%d lo=%d hi=%d nbins=%zu", rc, lo, hi, nbins);
    memset(exp, 0, nbins * 4);
    size_t inr = 0;
    for (size_t i = 0; i < len; i++) if (d[i] >= lo && d[i] < hi) {
        int b = oracle_bin(d[i], lo, hi, nbins);
        CHECK(b >= 0 && (size_t)b < nbins, "oráculo: bin único no existe v=%d lo=%d hi=%d nbins=%zu", d[i], lo, hi, nbins);
        if (b >= 0) exp[b]++;
        inr++;
    }
    size_t sum = 0;
    for (size_t b = 0; b < nbins; b++) { CHECK(bins[b] == exp[b], "histogram bin %zu: %u vs %u (lo=%d hi=%d nbins=%zu)", b, bins[b], exp[b], lo, hi, nbins); sum += bins[b]; }
    CHECK(sum == inr, "histogram: la suma de bins (%zu) != valores en rango (%zu)", sum, inr);
}
static void t_histogram(void) {
    cases = fails = 0;
    for (size_t len = 1; len <= 3; len++) {
        int32_t *d = malloc(len * 4);
        long tot = 1; for (size_t i = 0; i < len; i++) tot *= 7;
        for (long code = 0; code < tot; code++) {
            long cc = code; for (size_t i = 0; i < len; i++) { d[i] = (int32_t)(cc % 7) - 3; cc /= 7; }
            for (int32_t lo = -3; lo <= 3; lo++) for (int32_t hi = -3; hi <= 3; hi++) for (size_t nb = 1; nb <= 4; nb++) {
                uint32_t *bins = malloc(nb * 4), *exp = malloc(nb * 4);
                if (hi > lo) check_hist(d, len, lo, hi, nb, bins, exp);
                else {
                    for (size_t b = 0; b < nb; b++) bins[b] = 0xdeadbeef;
                    int rc = histogram(d, len, lo, hi, bins, nb); cases++;
                    CHECK(rc == CW_ERR_DIM, "histogram hi<=lo debe dar DIM, dio %d", rc);
                    for (size_t b = 0; b < nb; b++) CHECK(bins[b] == 0xdeadbeef, "histogram tocó bins con hi<=lo");
                }
                free(bins); free(exp);
            }
        }
        free(d);
    }
    /* extremos de int32: la aritmética intermedia debe caber en int64 */
    const int32_t ev[6] = {INT32_MIN, INT32_MIN + 1, -1, 0, INT32_MAX - 1, INT32_MAX};
    const size_t nbs[4] = {1, 2, 3, 4096};
    for (int a = 0; a < 6; a++) for (int b = 0; b < 6; b++) if (ev[b] > ev[a])
        for (int q = 0; q < 4; q++) {
            int32_t d[6]; for (int i = 0; i < 6; i++) d[i] = ev[i];
            uint32_t *bins = malloc(nbs[q] * 4), *exp = malloc(nbs[q] * 4);
            check_hist(d, 6, ev[a], ev[b], nbs[q], bins, exp);
            free(bins); free(exp);
        }
    int32_t dd[2] = {1, 2}; uint32_t bb[2] = {7, 7};
    #define ERR4(call, want) do { int r = (call); cases++; CHECK(r == (want), "histogram err %d vs %d (" #call ")", want, r); \
        CHECK(bb[0] == 7 && bb[1] == 7, "histogram tocó bins en error"); } while (0)
    ERR4(histogram(NULL, 2, 0, 5, bb, 2), CW_ERR_NULL);
    ERR4(histogram(dd, 2, 0, 5, NULL, 2), CW_ERR_NULL);
    ERR4(histogram(dd, 0, 0, 5, bb, 2), CW_ERR_DIM);
    ERR4(histogram(dd, 2, 0, 5, bb, 0), CW_ERR_DIM);
    ERR4(histogram(dd, 2, 5, 5, bb, 2), CW_ERR_DIM);
    ERR4(histogram(dd, 1000001, 0, 5, bb, 2), CW_ERR_OVERFLOW);
    ERR4(histogram(dd, 2, 0, 5, bb, 4097), CW_ERR_OVERFLOW);
    ERR4(histogram((int32_t *)((char *)dd + 1), 2, 0, 5, bb, 2), CW_ERR_ALIGN);
    ERR4(histogram(dd, 2, 0, 5, (uint32_t *)((char *)bb + 1), 2), CW_ERR_ALIGN);
    report("histogram", "len 1..3; datos y lo,hi en -3..3; nbins 1..4; + extremos int32 con nbins hasta 4096; + 9 errores");
    total_fails += fails;
}

int main(void) {
    t_matmul(); t_scale_clamp(); t_array_stats(); t_histogram();
    printf("TOTAL_FAILS %lld\n", total_fails);
    return total_fails ? 1 : 0;
}
