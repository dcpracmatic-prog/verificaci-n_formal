# Alcance y límites: qué significa "matemáticamente infalible"

## 1. La afirmación, con precisión
"Software 100 % libre de errores bajo cualquier escenario" no es alcanzable como enunciado absoluto, por tres razones independientes:

1. **Especificación.** Una prueba demuestra *programa ⊨ especificación*. Si la especificación omite o malinterpreta algo (p. ej. el `lo > hi` de `scale_clamp`, que el contrato excluía pero el C aceptaba; ya corregido), el programa puede ser "correcto" y aun así hacer lo equivocado. La verificación traslada el riesgo del código a la especificación; no lo elimina.
2. **Base de confianza (TCB).** Toda prueba confía en: el verificador/solver, el compilador, libc, el SO, el firmware y el hardware. Ejemplos reales: seL4 prueba el binario contra su spec, pero asume corrección de hardware y de partes del arranque; CompCert prueba el compilador, no tu spec.
3. **Indecidibilidad (Rice).** No existe un algoritmo que decida *toda* propiedad no trivial de *todo* programa. La verificación funciona porque se escribe el programa y la prueba a la vez, restringiendo el lenguaje/estilo.

Lo que sí existe y funciona: seL4 (microkernel), CompCert (compilador C), CertiKOS, el hipervisor de AWS (s2n, Zelkova), Dafny/Frama-C/SPARK en aeroespacial. Cuestan entre 10× y 30× el esfuerzo de desarrollo convencional, y se aplican a núcleos pequeños y críticos, no a "sistemas masivos" enteros.

## 2. Qué demuestra cada clase de prueba de este paquete

| Clase | Garantía | No garantiza |
|---|---|---|
| Intervalos + identidad polinómica (L1–L8) | Para **todo** el rango del contrato: sin desbordes aritméticos de enteros, índices en `[0, filas·cols)` | Que el llamador reserve `m·k·8` bytes (precondición del contrato, no verificada aquí); punto flotante |
| Exhaustivo en dominio finito | Para **toda** entrada del dominio declarado: correcto vs. oráculo | Entradas fuera del dominio. Es la "hipótesis de cota pequeña": la mayoría de los bugs aparecen con entradas pequeñas, pero **no es una prueba** para tamaños mayores |
| ASan/UBSan dentro del exhaustivo | Sin OOB/UB *en esas ejecuciones* | UB que solo aparece con otros tamaños o con otro compilador/optimización |
| Mutación | El arnés detecta 14 clases de fallo plausibles | Cobertura de fallos no imaginados |
| FormalVerifier en autoheal | El parche cumple las propiedades en el dominio declarado, y el contraejemplo regresa al agente | Parches con bugs fuera del dominio; propiedades omitidas |

Cada `Proof` en `report/certificate.json` lleva su enunciado exacto (incluido el dominio) y su campo `trusted`.

## 3. Estado de las dependencias externas
- **Z3:** las 5 obligaciones `obligations/smt2/*.smt2` se ejecutan con `run_z3.sh` y todas dan `unsat`: re-prueban de forma independiente los lemas de índice (L1–L3) y de suma (L8 en su forma generada).
- **CBMC:** se ejecuta con `run_cbmc.sh` y en el workflow `formal-solvers.yml`. Resultado local: `array_stats`, `histogram_invalid` y `scale_clamp_invalid` pasan; `matmul_*` y `histogram_valid` son demasiado pesados para el tiempo usado; `scale_clamp_valid` falla por NaN/desbordamiento en punto flotante (el contrato no acota los flotantes).
- **`run_all.py`** no invoca Z3 ni CBMC: solo comprueba con gcc que los arneses están bien formados (humo, que no es verificación). Eso es lo que `report/RESUMEN.md` lista como no ejecutado por `run_all.py`.
- Los lemas L1–L8 los prueba el código propio de `fvcore/intervals.py` (≈60 líneas); Z3 aporta la comprobación independiente.
- Dafny y Frama-C no se han usado todavía.

## 4. Ruta hacia una garantía real de "provably correct" (en orden de rendimiento)
1. Mantener `run_z3.sh` en CI (hecho: todas dan `unsat`). Si algún archivo deja de dar `unsat`, hay un error en el lema o en el C.
2. Terminar `run_cbmc.sh` para `matmul` y `histogram_valid` (hoy muy lentos: bajar la cota o dividir los arneses) y acotar los flotantes en el contrato de `scale_clamp` o relajar `--float-overflow-check`/`--nan-check` en ese arnés. Verifica memoria y overflow para *todas* las entradas hasta la cota, sin oráculo.
3. Anotar el C con **ACSL** y probar con **Frama-C/WP** (Alt-Ergo/Z3): da prueba para **tamaños sin cota** (m,k,n hasta 10 000). Requisitos: `\valid(A+(0..m*k-1))`, bucles con invariantes (p. ej. `0 ≤ p ≤ k`), `assigns C[0..m*n-1]`. Los lemas L1–L3 son exactamente las obligaciones de índice que WP generará.
4. Punto flotante: modelar con `--float` en CBMC o probar cotas de error con Gappa/Frama-C (WP + `Flocq`); declarar una cota de error de `matmul` en el contrato (hoy no existe).
5. Para Python (autoheal): migrar las funciones críticas a Dafny/Why3 o a C verificado; en Python puro solo cabe verificación acotada como la de aquí.
6. Enunciar propiedades en el contrato YAML (`requires`/`ensures`) y generar de ahí tanto CBMC como ACSL, de modo que el contrato —ya declarativo en commonweave— sea la única fuente de verdad.

## 5. Cómo leer un `PROVEN` aquí
`PROVEN` = "no existe contraejemplo en el dominio/alcance indicado en `statement`, bajo la base de confianza indicada en `trusted`". Nunca "el software es infalible".

## 6. Brechas abiertas conocidas
- **Solapamiento de buffers:** el contrato de `matmul` no declara si `C` puede solaparse con `A` o `B`; un solapamiento corrompería datos aún necesarios. Hay que añadir la precondición (o `restrict`) y un arnés que la compruebe.
- **Tamaño y validez de buffers y punto flotante:** falta especificar con precisión el tamaño/validez de cada buffer y el comportamiento numérico (NaN, infinitos, cota de error).
- **Prueba completa vs. acotada vs. no resuelta:** los scripts ya distinguen `PROBADO`/`REFUTADO`/`NO RESUELTO`; falta llevar esa misma distinción a `certificate.json`.
- **Trazabilidad contrato → obligación → código:** las obligaciones se generan del YAML, pero falta mostrar que cada propiedad del contrato tiene su obligación y que el certificado registra versiones de herramientas y archivos para cada resultado.
- **Generalización:** los ejemplos son pocos y pequeños; faltan más componentes, errores sembrados de otros tipos y mediciones de tiempo.

## 7. Licencia
El repositorio se distribuye bajo la [Elastic License 2.0](../LICENSE). Es «source-available», no una licencia de código abierto aprobada por la OSI.
