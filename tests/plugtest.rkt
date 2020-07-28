(define-language Lc 
  (n ::= number)
  (x ::= variable-not-otherwise-mentioned))

(require-python-source "runtime/termops.py")

(term-let-assert-equal
  ([n 0 (term 1337)]
   [x 2 (term ((x y) (a b)))])
  (term ((n  x ...) ...))
  (term ((1337 x y) (1337 a b))))

(term-let-assert-equal
  ([n_1 1 (term (1 2))]
   [n_2 1 (term (3 4 5))])
  (term ((n_1 ...  n_2 ...) (n_2 ... n_1 ...)))
  (term ((1 2 3 4 5) (3 4 5 1 2))))

(term-let-assert-equal 
  ([n 1 (term (1 2 3))])
  (term ((y n) ...))
  (term ((y 1) (y 2) (y 3))))

(term-let-assert-equal
  ([n 1 (term (1 2))]
   [x 2 (term ((x y) (a b)))])
  (term ((n  x ...) ...))
  (term ((1 x y) (2 a b))))

(term-let-assert-equal
  ([n 2 (term ((1 2) (3 4)))]
   [x 2 (term ((a b) (c d)))])
  (term (((n ... x) ... n ...) ...))
  (term (((1 2 a) (3 4 b) 1 2) ((1 2 c) (3 4 d) 3 4))))

(term-let-assert-equal
  ([n 2 (term ((1 2 3) (4)))]
   [x 2 (term ((x y) (a b)))])
  (term ((n ... (n ... x ...) ...) ...))
  (term ((1 2 3 (1 2 3 x y) (4 a b)) (4 (1 2 3 x y) (4 a b)))))

(term-let-assert-equal
  ([n 1 (term (1 2))]
   [x 2 (term (()(a)))])
  (term ((n  x ...) ...))
  (term ((1) (2 a))))

(term-let-assert-equal 
  ([E 0 (term (1 hole))]
   [n 1 (term (5 6))])
  (term ((in-hole E n) ...))
  (term ((1 5) (1 6))))

(term-let-assert-equal 
  ([E 1 (term ((1 hole) (2 hole))) ]
   [n 1 (term (5 6) )])
   (term ((in-hole E n) ...))
   (term ((1 5) (2 6))))

(term-let-assert-equal 
  ([E 1 (term ((1 hole) (2 hole))) ]
   [n 0  (term 12)])
   (term ((in-hole (E) n) ...))
   (term (((1 12)) ((2 12)))))

(term-let-assert-equal 
  ([E 1 (term ((1 hole) (2 hole))) ]
   [n 0  (term 12)])
   (term ((in-hole E n) ...))
   (term ((1 12) (2 12))))

(term-let-assert-equal 
  ([n 0 (term 2)])
  (term (in-hole (1 hole (hole x)) n))
  (term (1 2 (hole x))))

(term-let-assert-equal
  ([E 1 (term (1 2 3))])
  (term ((in-hole E x) ...))
  (term (1 2 3)))

(term-let-assert-equal
  ([E 1 (term (1 2 3))])
  (term (in-hole 35 x))
  (term 35))

; Python Function Call Tests of the form ,(function-name term-template ...)
(term-let-assert-equal
  ([n1 0 (term 4)])
  (term ,(number_add (term n1) (term 1333)))
  (term 1337))

(term-let-assert-equal
  ([n1 0 (term 4)])
  (term (n1 ,(number_add (term n1) (term 1333))))
  (term (4 1337)))

(term-let-assert-equal
  ([n1 0 (term 4)]
   [n2 1 (term (1 2))])
  (term ((n2 ,(number_add (term n1) (term 1333))) ...))
  (term ((1 1337) (2 1337))))

(term-let-assert-equal
  ([n 1 (term (1 2 3))]
   [x 1 (term (x y z))])
  (term ,(zzip (term ((n x) ...))))
  (term (x_1 y_2 z_3)))

; nested evaluation
(term-let-assert-equal
  ([n_1 0 (term 6)]
   [n_2 0 (term -2)]
   [n_3 0 (term 4)])
  (term ,(number_add (term ,(number_add (term n_1) (term n_2))) (term n_3)))
  (term 8))

(term-let-assert-equal
  ([n_1 0 (term 1)]
   [n_2 0 (term 2)]
   [n_3 0 (term 3)])
  (term (n_1 n_2 n_3 ,(mmap3mul2 (term n_1) (term n_2) (term n_3))))
  (term (1 2 3 (2 4 6))))

(term-let-assert-equal
  ([n_1 0 (term 1)]
   [n_2 0 (term 2)]
   [n_3 0 (term 3)])
  (term (n_1 n_2 n_3 ,@(mmap3mul2 (term n_1) (term n_2) (term n_3))))
  (term (1 2 3 2 4 6)))

