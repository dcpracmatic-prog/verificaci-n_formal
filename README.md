# verificacion-formal — hacia software demostrablemente correcto

Capa de verificación construida sobre tus cuatro paquetes. Responde a la pregunta:
**¿qué se puede demostrar hoy, con qué garantía exacta, y qué falta para "0 errores bajo cualquier escenario"?**

> Lectura obligada antes de citar resultados: [`docs/ALCANCE_Y_LIMITES.md`](docs/ALCANCE_Y_LIMITES.md).
> Ningún software real es "100 % libre de errores" en términos absolutos; lo que existe es *corrección
> demostrada respecto a una especificación, bajo supuestos explícitos*. Este paquete hace explícitos ambos.

## Qué usa de tus archivos
| Tu paquete | Uso aquí |
|---|---|
| `commonweave_zero_v0.3` | **Objeto verificado**: el C real (`matmul`, `scale_clamp`, `array_stats`, `histogram`) y sus contratos YAML (de ahí salen las obligaciones CBMC/SMT). |
| `autoheal-primitiva` | **Punto de integración**: su interfaz `verify` quedaba "lista para Dafny/Z3/CBMC"; aquí se llena con `FormalVerifier`. |
| `lazo-primitiva` | Solo el *patrón* HMAC de `security.py` para firmar el certificado (no se importa código). |
| `modelo_multi_sistema_v03_1` | No aplica (simulación causal sintética, sin código que verificar). |

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

## Qué NO está hecho (honesto)
- **CBMC y Z3 no se ejecutaron**: la sesión no tenía acceso a PyPI/apt. Se generaron 8 arneses CBMC y 5 obligaciones SMT-LIB2; los arneses compilan y pasan una prueba de humo con gcc (muestreo, *no* verificación). Hasta que corras `run_cbmc.sh`/`run_z3.sh`, esas garantías **no existen**.
- Punto flotante (error de redondeo de `matmul`, NaN/inf) no está demostrado.
- No hay prueba mecanizada en Coq/Lean/Isabelle/Dafny/Frama-C (la ruta hacia "provably correct" real; ver roadmap en el documento de límites).

## Hallazgo sobre tu código
`scale_clamp` con `lo > hi` **no está excluido por el contrato** y devuelve `hi` (el orden de los `if`). El arnés fija ese comportamiento, pero el contrato debería declarar `requires: lo <= hi` o definir el resultado.

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
