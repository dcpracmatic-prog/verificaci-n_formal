; matmul_A: 0 <= i*k+p < m*k < 2^64 para todo el rango del contrato
; Esperado: unsat (la negación de la propiedad no tiene modelo). NO ejecutado en la sesión de generación.
(set-logic NIA)
(declare-const m Int) (declare-const k Int) (declare-const i Int) (declare-const p Int)
(assert (and (<= 1 m 10000) (<= 1 k 10000) (<= 0 i) (< i m) (<= 0 p) (< p k)))
(assert (not (and (<= 0 (+ (* i k) p)) (< (+ (* i k) p) (* m k)) (< (* m k) 18446744073709551616))))
(check-sat)
