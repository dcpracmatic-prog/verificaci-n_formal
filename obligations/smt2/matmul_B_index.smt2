; matmul_B: 0 <= p*n+j < k*n < 2^64 para todo el rango del contrato
; Esperado: unsat (la negación de la propiedad no tiene modelo). NO ejecutado en la sesión de generación.
(set-logic NIA)
(declare-const k Int) (declare-const n Int) (declare-const p Int) (declare-const j Int)
(assert (and (<= 1 k 10000) (<= 1 n 10000) (<= 0 p) (< p k) (<= 0 j) (< j n)))
(assert (not (and (<= 0 (+ (* p n) j)) (< (+ (* p n) j) (* k n)) (< (* k n) 18446744073709551616))))
(check-sat)
