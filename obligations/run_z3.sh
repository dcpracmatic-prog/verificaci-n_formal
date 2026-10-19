#!/bin/sh
# Requiere Z3. Cada archivo debe responder 'unsat' (la negación de la propiedad es insatisfacible = propiedad probada).
# Estado: PROBADO (unsat), REFUTADO (sat: contraejemplo) o NO RESUELTO (unknown, timeout o error).
# Código de salida: 0 todo PROBADO | 1 hay algún REFUTADO | 2 sin refutados pero con NO RESUELTO.
proven=0; refuted=0; unresolved=0
for f in obligations/smt2/*.smt2; do
  r=$(z3 -T:120 "$f" 2>&1 | head -1)
  case "$r" in
    unsat) echo "PROBADO      $f"; proven=$((proven+1)) ;;
    sat)   echo "REFUTADO     $f"; refuted=$((refuted+1)) ;;
    *)     echo "NO RESUELTO  $f ($r)"; unresolved=$((unresolved+1)) ;;
  esac
done
echo "RESUMEN Z3: PROBADO=$proven REFUTADO=$refuted NO_RESUELTO=$unresolved"
[ $refuted -gt 0 ] && exit 1
[ $unresolved -gt 0 ] && exit 2
exit 0
