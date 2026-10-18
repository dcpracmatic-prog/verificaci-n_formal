; matmul_C: 0 <= i*n+j < m*n < 2^64 para todo el rango del contrato
; Esperado: unsat (la negación de la propiedad no tiene modelo). NO ejecutado en la sesión de generación.
(set-logic NIA)
(declare-const m Int) (declare-const n Int) (declare-const i Int) (declare-const j Int)
(assert (and (<= 1 m 10000) (<= 1 n 10000) (<= 0 i) (< i m) (<= 0 j) (< j n)))
(assert (not (and (<= 0 (+ (* i n) j)) (< (+ (* i n) j) (* m n)) (< (* m n) 18446744073709551616))))
(check-sat)
