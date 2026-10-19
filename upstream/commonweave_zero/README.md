# COMMONWEAVE Zero (pipeline estabilizado + sello CSG)

Prototipo mínimo de falsación de la hipótesis COMMONWEAVE:

> La integración de componentes heterogéneos puede transformarse de trabajo artesanal en una operación declarativa, verificable y económicamente ventajosa.

## Qué incluye esta versión

1. **Componente nativo** — `matmul` + `scale_clamp` en C (float64, contratos explícitos).
2. **Contrato declarativo** — `contracts/matmul.yaml` (única fuente de verdad).
3. **Generador** — emite adaptador `ctypes` inspeccionable.
4. **Verificador diferencial** — contra modelo de referencia en Python puro + casos límite.
5. **Benchmark de cuatro vías** — pure Python / binding manual / generado / IPC.
6. **Certificado de aceptación** — enunciados explícitos, dominio, base de confianza y límites.
7. **Sello de integridad (CSG)** — Ed25519 + SHA3-256 sobre los artefactos clave. El resultado deja de ser un JSON editable y pasa a ser un objeto firmado y verificable por terceros.

## Ejecutar

```bash
cd commonweave_zero
python run_zero.py
```

El pipeline:

1. Compila `libmatmul.so`
2. Regenera el adaptador desde el contrato
3. Ejecuta 60 ensayos diferenciales + edge cases
4. Ejecuta el benchmark (tamaños 4/8/16/32)
5. Emite `report/acceptance.json` (certificado)
6. Sella los artefactos → `report/sello.json`
7. Auto-verifica el sello

Código de salida: `0` solo si el veredicto diferencial es PASS **y** el sello es válido.

## Verificar un sello ya emitido

```bash
python seal/sello.py --verify report/sello.json --base .
```

## Estructura

```
commonweave_zero/
├── c_src/              # Native + Makefile
├── contracts/          # YAML contracts
├── generator/          # Contract → adapter
├── generated/          # Generated (inspectable) code
├── verifier/           # Reference + differential
├── benchmarks/         # Four-way harness
├── seal/               # CSG-inspired integrity seal (Ed25519 + SHA3-256)
├── report/             # acceptance, differential, benchmark, sello
└── run_zero.py         # Single entry point
```

## Criterios de aceptación (del documento original)

- **Viabilidad**: generación automática de un adaptador funcional para el conjunto delimitado.
- **Ventaja demostrada**: menor esfuerzo humano que un binding convencional, sin sacrificar corrección y con rendimiento competitivo.
- **Generalización**: se pospone hasta tener resultados consecutivos en componentes no usados para desarrollar el prototipo.

## Límites explícitos

`PROVEN` significa: no se encontró contraejemplo en el dominio indicado, bajo la base de confianza listada.  
No significa “software libre de errores bajo cualquier escenario”.

Véase el campo `limits` del certificado y, en el ecosistema más amplio, `verificacion_formal/docs/ALCANCE_Y_LIMITES.md`.

## Integración CSG

El módulo `seal/sello.py` implementa la intención del **Sello de Integridad** de CSG:

- Firmas Ed25519
- Huellas SHA3-256 de cada artefacto
- Payload canónico firmado
- Verificación de firma + integridad de ficheros
- La clave privada nunca se escribe en el sello

En esta versión se usa una seed de demo para reproducibilidad del prototipo. En uso real se debe generar o cargar una clave privada fuera del repositorio.
