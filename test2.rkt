#lang racket
(require redex)
(define-language Lc 
  (e ::= (+ e e) n)
  (n ::= number)
)

;(redex-match Lc ((n_1 ...) (n_1 ...))  (term ((1 2 3) (1 2 3))))
;(redex-match Lc (((n_1 ...) ... ) ((n_1 ...) ...))  (term (((1 2 3) (4 5)) ((1 2 3) (4 5))  )))
;(redex-match Lc ((n_1 ... n_1 ...) n_1 ...)  (term ((1 2 3 1 2 3) 1 2 3))) 
;(redex-match Lc e  (term (+ 4 2))) 
;(redex-match Lc (+ e_1 e_2)  (term (+ (+ 3 4) 2))) 
;(redex-match Lc (+ e_1 e_1)  (term (+ (+ 3 4) (+ 3 4)))) 


(redex-match Lc (n ... ...) ( 1 2 3))
