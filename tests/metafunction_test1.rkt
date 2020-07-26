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

(assert-term-eq ()
  (term (var2int a))
  (term 3))

(assert-term-eq ()
  (term (var2int b))
  (term 1338))

(assert-term-eq ()
  (term (var2int x))
  (term 1338))


(define-metafunction A 
  plusone2 : n -> n
  [(plusone2 1) 2 ]
  [(plusone2 2) 3 ]
  [(plusone2 3) 4 ])

(assert-term-eq 
  ([n 1 (term (1 2 3))])
  (term ((plusone2 n) ...))
  (term (2 3 4)))

(define-metafunction A 
  append-var : (x ...) (x ...) -> (x ...)
  [(append-var (x_1 ...) (x_2 ...)) (x_1 ... x_2 ...)])

(assert-term-eq ()
  (term (append-var () ()))
  (term ()))

(assert-term-eq ()
  (term (append-var (a b c) (x y z)))
  (term (a b c x y z)))

(define-metafunction A
  make-set : (x ...) -> (x ...)
  [(make-set (x_0 x_1 ... x_0 x_2 ... )) 
   (append-var (x_0) (make-set (append-var (x_1 ...) (x_2 ...))))]
  [(make-set (x_0 x_1 ...))
   (append-var (x_0) (make-set (x_1 ...)))]
  [(make-set ()) ()])

(assert-term-eq ()
  (term (make-set ()))
  (term ()))

(assert-term-eq ()
  (term (make-set (a)))
  (term (a)))

(assert-term-eq ()
  (term (make-set (a b c)))
  (term (a b c)))

(assert-term-eq ()
  (term (make-set (a b c b x a y z)))
  (term (a b c x y z)))

(define-metafunction A 
  remove-from-set : (x ...) x -> (x ...)
  [(remove-from-set (x_0 ... x x_1 ...) x) (append-var (x_0 ...) (x_1 ...))]
  [(remove-from-set (x_0 ...) x) (x_0 ...)])

(assert-term-eq ()
  (term (remove-from-set () a))
  (term ()))

(assert-term-eq ()
  (term (remove-from-set (a) a))
  (term ()))

(assert-term-eq ()
  (term (remove-from-set (a) b))
  (term (a)))

(assert-term-eq ()
  (term (remove-from-set (a b c d) c))
  (term (a b d)))

(assert-term-eq ()
  (term (remove-from-set (a b c d) d))
  (term (a b c)))

(define-metafunction A
  union-sets : (x ...) (x ...) -> (x ...)
  [(union-sets (x_0 ...) (x_1 ...))
   (make-set (append-var (x_0 ...) (x_1 ...)))])

(assert-term-eq ()
  (term (union-sets () ()))
  (term ()))

(assert-term-eq ()
  (term (union-sets (a b c) (x y z)))
  (term (a b c x y z)))

(assert-term-eq ()
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

(assert-term-eq ()
  (term (fv 1))
  (term ()))

(assert-term-eq ()
  (term (fv z))
  (term (z)))

(assert-term-eq ()
  (term (fv (lambda x (a b)))) 
  (term (a b)))

(assert-term-eq ()
  (term (fv (lambda x (a (b x))))) 
  (term (a b)))

(assert-term-eq ()
(term (fv (lambda y (x (lambda x (x y)))))) 
(term (x)))

(define-metafunction A 
  return-if-contains : (x ...) x -> (x ...) 
  [(return-if-contains (x_0 ... x x_1 ...) x) (x) ]
  [(return-if-contains (x_0 ...) x) () ])

(assert-term-eq () (term (return-if-contains () a)) (term ()))
(assert-term-eq () (term (return-if-contains (a) a)) (term (a)))
(assert-term-eq () (term (return-if-contains (a) b)) (term ()))
(assert-term-eq () (term (return-if-contains (a b c) x)) (term ()))
(assert-term-eq () (term (return-if-contains (a b c) b)) (term (b)))

(define-metafunction A 
  set-intersection : (x ...) (x ...) -> (x ...)
  [(set-intersection (x_0 x_1 ...) (x_2 ...))
   (union-sets (return-if-contains (x_2 ...) x_0) (set-intersection (x_1 ...) (x_2 ...)))]
  [(set-intersection () (x_2 ...)) ()])

(assert-term-eq () (term (set-intersection (b) (     ))) (term ( )))
(assert-term-eq () (term (set-intersection (b) (a b c))) (term (b)))
(assert-term-eq () (term (set-intersection (x y z) (a b c))) (term ( )))
(assert-term-eq () (term (set-intersection (m x y p z q) (m a p q b c))) (term (m p q)))
(assert-term-eq () (term (set-intersection ( ) (a b c))) (term ( )))
