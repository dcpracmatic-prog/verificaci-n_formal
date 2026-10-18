; array_stats: la suma acumulada de len<=1e6 int32 cabe en int64
; Esperado: unsat (la negación de la propiedad no tiene modelo). NO ejecutado en la sesión de generación.
(set-logic NIA)
(declare-const len Int) (declare-const s Int)
(assert (and (<= 1 len 1000000) (<= (* (- 2147483648) len) s) (<= s (* 2147483647 len))))
(assert (not (and (<= (- 9223372036854775808) s) (< s 9223372036854775808))))
(check-sat)
