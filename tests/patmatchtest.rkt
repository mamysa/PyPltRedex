(define-language Lc 
  (e ::= (+ e e) n)
  (n ::= number)
  (x ::= variable-not-otherwise-mentioned)

  (P ::= (n ... E e ...))
  (E ::= (+ E e) (+ n E) hole)

)

(match-equal? (redex-match Lc n (term 1)) (match (bind n 1)))
(match-equal? (redex-match Lc e (term 2)) (match (bind e 2)))
(match-equal? (redex-match Lc e_1 (term (+ 1 2))) (match (bind e_1 (+ 1 2))))
(match-equal? (redex-match Lc x (term n)) (match (bind x n)))
(match-equal? (redex-match Lc x (term +)) ())

(match-equal? (redex-match Lc (+ e_1 e_2) (term (+ (+ 1 2) 3))) 
              (match (bind e_1 (+ 1 2)) (bind e_2 3)))

(match-equal? (redex-match Lc (+ e_1 e_2) (term (+ (+ 1 2) (+ 3 4)))) 
              (match (bind e_1 (+ 1 2)) (bind e_2 (+ 3 4))))

; non-deterministic repetion matching.
(match-equal? (redex-match Lc (n_1 ... n_2 ...) (term (1 2 3)))
             (match (bind n_1 ()) (bind n_2 (1 2 3)))
             (match (bind n_1 (1)) (bind n_2 (2 3)))
             (match (bind n_1 (1 2)) (bind n_2 (3)))
             (match (bind n_1 (1 2 3)) (bind n_2 ())))

; different ellipsis depth
(match-equal? (redex-match Lc ((x n ...) ...) (term ((x 1 2) (y 3 4 5) (z))))
             (match (bind n ((1 2) (3 4 5) ())) (bind x (x y z))))

; contraint checks
(match-equal?
  (redex-match Lc ((n_1 ...) (n_1 ...))  (term ((1 2 3) (1 2 3))))
  (match (bind n_1 (1 2 3))))

(match-equal? 
  (redex-match Lc (((n_1 ...) ... ) ((n_1 ...) ...))  (term (((1 2 3) (4 5)) ((1 2 3) (4 5)))))
  (match (bind n_1 ((1 2 3) (4 5)))))

(match-equal?
  (redex-match Lc ((n_1 ... n_1 ...) n_1 ...)  (term ((1 2 3 1 2 3) 1 2 3))) 
  (match (bind n_1 (1 2 3))))

(match-equal?
  (redex-match Lc (+ e_1 e_1)  (term (+ (+ 3 4) (+ 3 4)))) 
  (match (bind e_1 (+ 3 4))))

; evaluation contextts
(match-equal?
  (redex-match Lc hole (term hole))
  (match))
(match-equal?
  (redex-match Lc E (term (+ hole (+ 1 1))))
  (match (bind E (+ hole (+ 1 1)))))
(match-equal?
  (redex-match Lc E (term (+ 2 hole)))
  (match (bind E (+ 2 hole))))
(match-equal?
  (redex-match Lc E (term (+ (+ 1 1) hole)))
  ())
(match-equal?
  (redex-match Lc P (term ( 1 2 3 (+ 1 hole) (+ 1 2) 5)))
  (match (bind P (1 2 3 (+ 1 hole) (+ 1 2) 5))))

(match-equal?
  (redex-match Lc (n_1 ... hole n_2 ...) (term ( 1 2 hole 3)))
  (match (bind n_1 (1 2)) (bind n_2 (3))))
