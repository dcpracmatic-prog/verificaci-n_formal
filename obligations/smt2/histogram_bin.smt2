; histogram: 0 <= bin < nbins y sin overflow de int64, para todo int32 lo<hi, v en [lo,hi), nbins en [1,4096]
; Esperado: unsat (la negación de la propiedad no tiene modelo). NO ejecutado en la sesión de generación.
(set-logic NIA)
(declare-const lo Int) (declare-const hi Int) (declare-const v Int) (declare-const nbins Int)
(assert (and (<= -2147483648 lo 2147483647) (<= -2147483648 hi 2147483647) (<= -2147483648 v 2147483647)))
(assert (and (> hi lo) (>= v lo) (< v hi) (<= 1 nbins 4096)))
(define-fun x () Int (* (- v lo) nbins))
(define-fun b () Int (div x (- hi lo)))
(assert (not (and (<= 0 b) (< b nbins) (< x 9223372036854775808) (< (- hi lo) 9223372036854775808))))
(check-sat)
