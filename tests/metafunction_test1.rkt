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
