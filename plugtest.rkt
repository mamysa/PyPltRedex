(define-language Lc 
  (n ::= number)
  (x ::= variable-not-otherwise-mentioned))

(assert-term-eq
  ([n 0 (term 1337)]
   [x 2 (term ((x y) (a b)))])
  (term ((n  x ...) ...))
  (term ((1337 x y) (1337 a b))))

(assert-term-eq
  ([n_1 1 (term (1 2))]
   [n_2 1 (term (3 4 5))])
  (term ((n_1 ...  n_2 ...) (n_2 ... n_1 ...)))
  (term ((1 2 3 4 5) (3 4 5 1 2))))

(assert-term-eq 
  ([n 1 (term (1 2 3))])
  (term ((y n) ...))
  (term ((y 1) (y 2) (y 3))))

(assert-term-eq
  ([n 1 (term (1 2))]
   [x 2 (term ((x y) (a b)))])
  (term ((n  x ...) ...))
  (term ((1 x y) (2 a b))))

(assert-term-eq
  ([n 2 (term ((1 2) (3 4)))]
   [x 2 (term ((a b) (c d)))])
  (term (((n ... x) ... n ...) ...))
  (term (((1 2 a) (3 4 b) 1 2) ((1 2 c) (3 4 d) 3 4))))

(assert-term-eq
  ([n 2 (term ((1 2 3) (4)))]
   [x 2 (term ((x y) (a b)))])
  (term ((n ... (n ... x ...) ...) ...))
  (term ((1 2 3 (1 2 3 x y) (4 a b)) (4 (1 2 3 x y) (4 a b)))))

(assert-term-eq
  ([n 1 (term (1 2))]
   [x 2 (term (()(a)))])
  (term ((n  x ...) ...))
  (term ((1) (2 a))))
