#!/bin/sh
# Requiere Z3. Cada archivo debe responder 'unsat' (la negación de la propiedad es insatisfacible = propiedad probada).
fail=0
for f in obligations/smt2/*.smt2; do
  r=$(z3 -T:120 "$f" | head -1)
  echo "$f: $r"
  [ "$r" = "unsat" ] || fail=1
done
exit $fail
