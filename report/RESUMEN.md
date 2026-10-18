# Resumen de verificación

Pruebas PROVEN: **17**, REFUTED: **0**
Mutantes detectados: **14/14**

| Prueba | Tipo | Estado | Casos | Enunciado |
|---|---|---|---|---|
| L1/matmul: A[i*k+p] en rango | ALGEBRAIC+INTERVAL | PROVEN | 0 | ∀ rows∈[1,10000], cols∈[1,10000], 0≤r<rows, 0≤c<cols: 0 ≤ i*k+p < rows·cols, y i*k+p y rows·cols caben en size_t (máx 99999999). |
| L2/matmul: B[p*n+j] en rango | ALGEBRAIC+INTERVAL | PROVEN | 0 | ∀ rows∈[1,10000], cols∈[1,10000], 0≤r<rows, 0≤c<cols: 0 ≤ p*n+j < rows·cols, y p*n+j y rows·cols caben en size_t (máx 99999999). |
| L3/matmul: C[i*n+j] en rango | ALGEBRAIC+INTERVAL | PROVEN | 0 | ∀ rows∈[1,10000], cols∈[1,10000], 0≤r<rows, 0≤c<cols: 0 ≤ i*n+j < rows·cols, y i*n+j y rows·cols caben en size_t (máx 99999999). |
| L4/histogram: (int64)hi-lo y (int64)v-lo caben en int64 | INTERVAL | PROVEN | 0 | hi,lo∈int32: hi-lo∈[-4294967295,4294967295] ⊂ int64. |
| L5/histogram: (v-lo)*nbins cabe en int64 | INTERVAL | PROVEN | 0 | (v-lo)∈[0,4294967295], nbins∈[1,4096]: producto ≤ 17592186040320 < 2^63. |
| L6/histogram: 0 <= bin < nbins | ALGEBRAIC | PROVEN | 4080 | ∀ w≥1, nbins≥1, 0≤x≤w-1: x·nbins ≤ (w-1)·nbins = w·nbins − nbins < w·nbins ⇒ ⌊x·nbins/w⌋ < nbins, y ≥ 0 por x≥0. Paso final (def. de ⌊·⌋: q· |
| L7/histogram: contador uint32 no desborda | INTERVAL | PROVEN | 0 | cada bin recibe ≤ len ≤ 1 000 000 incrementos < 2^32. |
| L8/array_stats: acumulador int64 no desborda | INTERVAL | PROVEN | 0 | /suma/ ≤ len·2^31 ≤ 2147483647000000 < 2^63 para len ≤ 1 000 000. |
| C/matmul: exhaustivo + ASan/UBSan | EXHAUSTIVE_C_ASAN | PROVEN | 348321 | Para TODA entrada de [m,k,n in 1..3; entradas en {-1,2}; + 13 caminos de error]: código de retorno correcto, resultado = oráculo independien |
| C/scale_clamp: exhaustivo + ASan/UBSan | EXHAUSTIVE_C_ASAN | PROVEN | 2274 | Para TODA entrada de [len 1..3; in {-2,0,1,3}; scale,lo,hi en {-1,0,2} (incluye lo>hi); + 6 errores]: código de retorno correcto, resultado  |
| C/array_stats: exhaustivo + ASan/UBSan | EXHAUSTIVE_C_ASAN | PROVEN | 246 | Para TODA entrada de [len 1..4; valores {-2,0,3} y {INT32_MIN,0,INT32_MAX}; + 6 errores]: código de retorno correcto, resultado = oráculo in |
| C/histogram: exhaustivo + ASan/UBSan | EXHAUSTIVE_C_ASAN | PROVEN | 78273 | Para TODA entrada de [len 1..3; datos y lo,hi en -3..3; nbins 1..4; + extremos int32 con nbins hasta 4096; + 9 errores]: código de retorno c |
| mean(ints) == media exacta | EXHAUSTIVE | PROVEN | 780 | ∀ xs∈[[-2]..[2, 2, 2, 2]] (780 valores): se cumple «mean(ints) == media exacta» |
| mean(floats) == media exacta | EXHAUSTIVE | PROVEN | 84 | ∀ xs∈[[-1.5]..[2.0, 2.0, 2.0]] (84 valores): se cumple «mean(floats) == media exacta» |
| min <= mean <= max | EXHAUSTIVE | PROVEN | 780 | ∀ xs∈[[-2]..[2, 2, 2, 2]] (780 valores): se cumple «min <= mean <= max» |
| mean invariante al orden | EXHAUSTIVE | PROVEN | 780 | ∀ xs∈[[-2]..[2, 2, 2, 2]] (780 valores): se cumple «mean invariante al orden» |
| mean([]) is None | EXHAUSTIVE | PROVEN | 1 | ∀ xs∈{[]}: se cumple «mean([]) is None» |

## No ejecutado por run_all.py
- obligations/cbmc/*.c (run_all.py no ejecuta CBMC: 8 arneses compilan y pasan humo con gcc; CBMC se corre con obligations/run_cbmc.sh y en el workflow formal-solvers)
- obligations/smt2/*.smt2 (run_all.py no ejecuta Z3: 5 obligaciones; se corren con obligations/run_z3.sh y en el workflow formal-solvers)

## NO probado
- Corrección total del programa respecto a una especificación formal completa (aquí las especificaciones son propiedades parciales).
- Comportamiento de punto flotante más allá de lo comprobado (error de redondeo, NaN, inf no modelados salvo donde se indica).
- Ausencia de errores en el compilador, el enlazador, libc, el SO o el hardware (base de confianza no verificada).
- Entradas fuera de los dominios finitos declarados en cada prueba EXHAUSTIVE.
- Concurrencia: ningún componente analizado es concurrente.
