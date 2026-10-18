[![Dependency Graph](https://github.com/dcpracmatic-prog/verificacion_formal/actions/workflows/dependabot/update-graph/badge.svg)](https://github.com/dcpracmatic-prog/verificacion_formal/actions/workflows/dependabot/update-graph)
[![CI — pruebas y regresión](https://github.com/dcpracmatic-prog/verificacion_formal/actions/workflows/ci.yml/badge.svg)](https://github.com/dcpracmatic-prog/verificacion_formal/actions/workflows/ci.yml)

## Ejecutar (solo Python ≥ 3.10 + gcc; sin dependencias externas para correr)
```bash
python run_all.py                       # todo + report/certificate.json + report/RESUMEN.md
python -m unittest discover -s tests -v # 13 tests
python examples/demo_autoheal_formal.py
sh obligations/run_cbmc.sh              # SI tienes CBMC  (pendiente, ver abajo)
sh obligations/run_z3.sh                # SI tienes Z3    (pendiente, ver abajo)
```
`pyyaml` solo se necesita para regenerar obligaciones (`proofs/gen_obligations.py`).

## Qué se demostró (17 pruebas, 0 refutadas) y de qué clase es cada una
| Clase | Qué | Alcance de la garantía |
|---|---|---|
| **Lemas aritméticos** (L1–L8) | Ningún índice sale de rango y ningún intermedio desborda (`size_t`/`int64`/`uint32`) en `matmul`, `histogram`, `array_stats` | **Todo el rango del contrato** (m,k,n ≤ 10 000; int32 completo; len ≤ 10⁶) |
| **Exhaustivo sobre el C real + ASan/UBSan** | Código de retorno, resultado vs. oráculo independiente, salida intacta en error, sin UB/OOB | **Todas** las entradas de dominios pequeños declarados (p. ej. matmul ≤ 3×3×3, 348 321 casos) |
| **Mutación** | 14 versiones deliberadamente rotas del C: el arnés detectó 14/14 | Demuestra que el verificador *puede* fallar |
| **autoheal + FormalVerifier** | Un parche que pasa las pruebas aleatorias de autoheal (`mean([0,1]) == 0`) es rechazado con contraejemplo | Dominio declarado (780 listas de enteros + 84 de floats) |

## Estructura
```
fvcore/        exhaustive.py (forall sobre dominio finito), intervals.py (intervalos + identidades), certificate.py
proofs/        harness.c, run_c_exhaustive.py (+mutantes), lemmas.py, gen_obligations.py, smoke_cbmc.py
obligations/   CBMC (.c) y SMT-LIB2 generados desde los YAML + scripts run_*.sh
integration/   formal_autoheal.py (FormalVerifier)
examples/      demo_autoheal_formal.py
upstream/      copias sin modificar de c_src, contracts y autoheal
report/        certificate.json, RESUMEN.md (generados)
```
# verificacion-formal — hacia software demostrablemente correcto

Capa de verificación construida sobre tus cuatro paquetes. Responde a la pregunta:
**¿qué se puede demostrar hoy, con qué garantía exacta, y qué falta para "0 errores bajo cualquier escenario"?**

> Lectura obligada antes de citar resultados: [`docs/ALCANCE_Y_LIMITES.md`](docs/ALCANCE_Y_LIMITES.md).
> Ningún software real es "100 % libre de errores" en términos absolutos; lo que existe es *corrección
> demostrada respecto a una especificación, bajo supuestos explícitos*. Este paquete hace explícitos ambos.
