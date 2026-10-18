[![Dependency Graph](https://github.com/dcpracmatic-prog/verificacion_formal/actions/workflows/dependabot/update-graph/badge.svg)](https://github.com/dcpracmatic-prog/verificacion_formal/actions/workflows/dependabot/update-graph)
[![CI — pruebas y regresión](https://github.com/dcpracmatic-prog/verificacion_formal/actions/workflows/ci.yml/badge.svg)](https://github.com/dcpracmatic-prog/verificacion_formal/actions/workflows/ci.yml)

# verificacion-formal — hacia software demostrablemente correcto

Capa de verificación construida sobre tus cuatro paquetes. Responde a la pregunta:
**¿qué se puede demostrar hoy, con qué garantía exacta, y qué falta para "0 errores bajo cualquier escenario"?**

> Lectura obligada antes de citar resultados: [`docs/ALCANCE_Y_LIMITES.md`](docs/ALCANCE_Y_LIMITES.md).
> Ningún software real es "100 % libre de errores" en términos absolutos; lo que existe es *corrección
> demostrada respecto a una especificación, bajo supuestos explícitos*. Este paquete hace explícitos ambos.

## Ejecutar (Python ≥ 3.10 + gcc)
```bash
python run_all.py                       # todo + report/certificate.json + report/RESUMEN.md
python -m unittest discover -s tests -v # 13 tests
python examples/demo_autoheal_formal.py
sh obligations/run_z3.sh                # requiere Z3   (5 obligaciones; todas dan unsat)
sh obligations/run_cbmc.sh              # requiere CBMC (ver "Estado de CBMC y Z3"; algunos arneses son lentos)
```
Dependencias de Python: `pip install -r requirements.txt` (`pyyaml`, necesario para `proofs/gen_obligations.py`, que `run_all.py` y los tests usan). Z3 y CBMC son opcionales y solo se necesitan para los scripts `obligations/run_*.sh`.

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
upstream/      c_src, contracts y autoheal (copia de trabajo; `matmul.c` incluye la corrección de `scale_clamp`)
report/        certificate.json, RESUMEN.md (generados)
```

## Estado de CBMC y Z3
- **Z3:** las 5 obligaciones SMT-LIB dan `unsat` (propiedad probada). Se ejecutan con `sh obligations/run_z3.sh` y en el workflow `formal-solvers.yml`.
- **CBMC:** `array_stats_valid/invalid`, `histogram_invalid` y `scale_clamp_invalid` pasan. `matmul_*` y `histogram_valid` son muy pesados y no terminaron en las pruebas locales (dependen del tiempo límite). `scale_clamp_valid` falla a propósito de las comprobaciones de punto flotante: CBMC encuentra NaN y desbordamiento en `in[i] * scale` porque el contrato no acota los flotantes. No es un error nuevo del código: es la limitación de punto flotante ya declarada abajo.
- `run_all.py` no ejecuta Z3 ni CBMC; solo comprueba con gcc que los arneses compilan y pasan humo, y lo indica en `report/RESUMEN.md`.

## Hallazgo corregido: `scale_clamp` con `lo > hi`
El contrato declara `requires: hi >= lo` (código 2), pero el C lo aceptaba y devolvía `hi`. Corregido: ahora `scale_clamp` devuelve `CW_ERR_DIM` (también si hay NaN) sin tocar `out`, y el arnés exhaustivo y los arneses CBMC lo verifican.

## Licencia
[Elastic License 2.0](LICENSE) (ELv2), «source-available»: puedes usar, copiar, distribuir y modificar el software, pero no ofrecerlo a terceros como servicio gestionado/hospedado ni quitar los avisos de licencia. No es una licencia de código abierto aprobada por la OSI. Salvo que un archivo indique otra cosa, todo el repositorio, incluido `upstream/`, se distribuye bajo esta licencia.
