#!/bin/sh
# Requiere CBMC (https://github.com/diffblue/cbmc). Ejecutar desde la raíz del paquete.
set -e
for f in obligations/cbmc/*_valid.c obligations/cbmc/*_invalid.c; do
  echo "== $f"
  cbmc "$f" -I upstream/commonweave_zero/c_src -I obligations/cbmc \
       --bounds-check --pointer-check --signed-overflow-check --unsigned-overflow-check --conversion-check \
       --float-overflow-check --nan-check --unwind 8 --unwinding-assertions --object-bits 12 | tail -3
done
