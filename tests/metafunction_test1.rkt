(require-python-source "tests/runtime_python_ops.py")

(define-language A 
    (e ::= (e e) v)
    (v ::= (lambda x e) n x)
    (n ::= number)      
    (x ::= variable-not-otherwise-mentioned))

(define-metafunction A 
  plusone : n -> n
  [(plusone 2) 3]
  [(plusone 1337) 1338])

(define-metafunction A 
  var2int : x -> n
  [(var2int a) (plusone 2)]
  [(var2int x) (plusone 1337)])

(term-let-assert-equal ()
  (term (var2int a))
  (term 3))

(term-let-assert-equal ()
  (term (var2int b))
  (term 1338))

(term-let-assert-equal ()
  (term (var2int x))
  (term 1338))


(define-metafunction A 
  plusone2 : n -> n
  [(plusone2 1) 2 ]
  [(plusone2 2) 3 ]
  [(plusone2 3) 4 ])

(term-let-assert-equal 
  ([n 1 (term (1 2 3))])
  (term ((plusone2 n) ...))
  (term (2 3 4)))

(define-metafunction A 
  append-var : (x ...) (x ...) -> (x ...)
  [(append-var (x_1 ...) (x_2 ...)) (x_1 ... x_2 ...)])

(term-let-assert-equal ()
  (term (append-var () ()))
  (term ()))

(term-let-assert-equal ()
  (term (append-var (a b c) (x y z)))
  (term (a b c x y z)))

(define-metafunction A
  make-set : (x ...) -> (x ...)
  [(make-set (x_0 x_1 ... x_0 x_2 ... )) 
   (append-var (x_0) (make-set (append-var (x_1 ...) (x_2 ...))))]
  [(make-set (x_0 x_1 ...))
   (append-var (x_0) (make-set (x_1 ...)))]
  [(make-set ()) ()])

(term-let-assert-equal ()
  (term (make-set ()))
  (term ()))

(term-let-assert-equal ()
  (term (make-set (a)))
  (term (a)))

(term-let-assert-equal ()
  (term (make-set (a b c)))
  (term (a b c)))

(term-let-assert-equal ()
  (term (make-set (a b c b x a y z)))
  (term (a b c x y z)))

(define-metafunction A 
  remove-from-set : (x ...) x -> (x ...)
  [(remove-from-set (x_0 ... x x_1 ...) x) (append-var (x_0 ...) (x_1 ...))]
  [(remove-from-set (x_0 ...) x) (x_0 ...)])

(term-let-assert-equal ()
  (term (remove-from-set () a))
  (term ()))

(term-let-assert-equal ()
  (term (remove-from-set (a) a))
  (term ()))

(term-let-assert-equal ()
  (term (remove-from-set (a) b))
  (term (a)))

(term-let-assert-equal ()
  (term (remove-from-set (a b c d) c))
  (term (a b d)))

(term-let-assert-equal ()
  (term (remove-from-set (a b c d) d))
  (term (a b c)))

(define-metafunction A
  union-sets : (x ...) (x ...) -> (x ...)
  [(union-sets (x_0 ...) (x_1 ...))
   (make-set (append-var (x_0 ...) (x_1 ...)))])

(term-let-assert-equal ()
  (term (union-sets () ()))
  (term ()))

(term-let-assert-equal ()
  (term (union-sets (a b c) (x y z)))
  (term (a b c x y z)))

(term-let-assert-equal ()
  (term (union-sets (a b z c) (x y a i b z)))
  (term (a b z c x y i)))

(define-metafunction A 
  fv : e ->  (x ...)
  [(fv n) () ]
  [(fv x) (x)]
  [(fv (e_1 e_2)) 
   (make-set (append-var (fv e_1) (fv e_2)))]
  [(fv (lambda x e)) 
   (remove-from-set (make-set (fv e)) x)])

(term-let-assert-equal ()
  (term (fv 1))
  (term ()))

(term-let-assert-equal ()
  (term (fv z))
  (term (z)))

(term-let-assert-equal ()
  (term (fv (lambda x (a b)))) 
  (term (a b)))

(term-let-assert-equal ()
  (term (fv (lambda x (a (b x))))) 
  (term (a b)))

(term-let-assert-equal ()
(term (fv (lambda y (x (lambda x (x y)))))) 
(term (x)))

(define-metafunction A 
  return-if-contains : (x ...) x -> (x ...) 
  [(return-if-contains (x_0 ... x x_1 ...) x) (x) ]
  [(return-if-contains (x_0 ...) x) () ])

(term-let-assert-equal () (term (return-if-contains () a)) (term ()))
(term-let-assert-equal () (term (return-if-contains (a) a)) (term (a)))
(term-let-assert-equal () (term (return-if-contains (a) b)) (term ()))
(term-let-assert-equal () (term (return-if-contains (a b c) x)) (term ()))
(term-let-assert-equal () (term (return-if-contains (a b c) b)) (term (b)))

(define-metafunction A 
  set-intersection : (x ...) (x ...) -> (x ...)
  [(set-intersection (x_0 x_1 ...) (x_2 ...))
   (union-sets (return-if-contains (x_2 ...) x_0) (set-intersection (x_1 ...) (x_2 ...)))]
  [(set-intersection () (x_2 ...)) ()])

(term-let-assert-equal () (term (set-intersection (b) (     ))) (term ( )))
(term-let-assert-equal () (term (set-intersection (b) (a b c))) (term (b)))
(term-let-assert-equal () (term (set-intersection (x y z) (a b c))) (term ( )))
(term-let-assert-equal () (term (set-intersection (m x y p z q) (m a p q b c))) (term (m p q)))
(term-let-assert-equal () (term (set-intersection ( ) (a b c))) (term ( )))

(define-metafunction A
  nums2vars_2 : n ... -> (x ...) 
  [(nums2vars_2 2 1337) (p q)])

(define-metafunction A
  var2int_2 : x -> n
  [(var2int_2 a) 2]
  [(var2int_2 b) 1337])

(term-let-assert-equal ()
  (term (nums2vars_2 (var2int_2 a) (var2int_2 b)))
  (term (p q)))


; Testing sideconditions

(define-metafunction A 
  mf-with-sideconditions-1 : (n ...) -> (n ...)
  [(mf-with-sideconditions-1 (n_1 ... n_2 ...)) (n_1 ...)
  (side-condition ,(b_length_equal (term (n_1 ...)) (term 4)))]
  [(mf-with-sideconditions-1 (n_1 ... n_2 ...)) (n_1 ...)
  (side-condition ,(b_length_equal (term (n_2 ...)) (term 2)))]
  [(mf-with-sideconditions-1 (n_1 ... n_2 ...)) (1339)])

(define-metafunction A
  mf-with-sideconditions-2 : (n ... n) -> (n)
  [(mf-with-sideconditions-2 (n_1 ... n_2)) (,(sequence_int_sum (term (n_1 ...))))
   (side-condition ,(b_length_equal (term (n_1 ...)) (term 3)))
   (side-condition ,(b_int_is_even (term n_2)))]
  [(mf-with-sideconditions-2 (n_1 ... n_2)) (1337)
   (side-condition ,(b_int_is_even (term n_2)))]
  [(mf-with-sideconditions-2 (n ...)) (-1)])

(term-let-assert-equal ()
  (term (mf-with-sideconditions-1( 1 2 3 4 5 6 7)))
  (term (1 2 3 4)))

(term-let-assert-equal ()
  (term (mf-with-sideconditions-1 (1337 2 3)))
  (term (1337)))

(term-let-assert-equal ()
  (term (mf-with-sideconditions-1 (1337)))
  (term (1339)))

(term-let-assert-equal ()
	(term (mf-with-sideconditions-2 (7 2 3 4)))
	(term (12)))

(term-let-assert-equal ()
	(term (mf-with-sideconditions-2 (7 4 3 4)))
	(term (14)))


(term-let-assert-equal ()
	(term (mf-with-sideconditions-2 (7 2 4)))
	(term (1337)))

(term-let-assert-equal ()
	(term (mf-with-sideconditions-2 (7 2 3 5)))
	(term (-1)))

