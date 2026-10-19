#!/bin/sh
# Requiere CBMC (https://github.com/diffblue/cbmc). Ejecutar desde la raíz del paquete.
# Estado por arnés: PROBADO (cbmc sale 0), REFUTADO (sale 10: contraejemplo) o NO RESUELTO (timeout u otro error).
# Código de salida: 0 todo PROBADO | 1 hay algún REFUTADO | 2 sin refutados pero con NO RESUELTO.
# Variables: CBMC_TIMEOUT (segundos por arnés, 600 por defecto), CBMC_ONLY (filtro por nombre).
TMO=${CBMC_TIMEOUT:-600}
proven=0; refuted=0; unresolved=0
for f in obligations/cbmc/*_valid.c obligations/cbmc/*_invalid.c; do
  case "$f" in *"${CBMC_ONLY:-}"*) ;; *) continue ;; esac
  log=$(mktemp)
  timeout "$TMO" cbmc "$f" -I upstream/commonweave_zero/c_src -I obligations/cbmc \
       --bounds-check --pointer-check --signed-overflow-check --unsigned-overflow-check --conversion-check \
       --float-overflow-check --nan-check --unwind 8 --unwinding-assertions --object-bits 12 > "$log" 2>&1
  rc=$?
  if [ $rc -eq 0 ] && grep -q "VERIFICATION SUCCESSFUL" "$log"; then
    echo "PROBADO      $f"; proven=$((proven+1))
  elif [ $rc -eq 10 ]; then
    echo "REFUTADO     $f"; refuted=$((refuted+1)); grep "FAILURE" "$log" | head -5
  elif [ $rc -eq 124 ] || [ $rc -eq 137 ]; then
    echo "NO RESUELTO  $f (tiempo agotado: ${TMO}s)"; unresolved=$((unresolved+1))
  else
    echo "NO RESUELTO  $f (cbmc salió con código $rc)"; tail -3 "$log"; unresolved=$((unresolved+1))
  fi
  rm -f "$log"
done
echo "RESUMEN CBMC: PROBADO=$proven REFUTADO=$refuted NO_RESUELTO=$unresolved"
[ $refuted -gt 0 ] && exit 1
[ $unresolved -gt 0 ] && exit 2
exit 0
