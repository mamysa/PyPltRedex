(require-python-source "examples/cbv-lambda/utils.py")

(define-language LambdaCalculus
  (e ::= (e e) v)
  (v ::= (lambda x e) n x)
  (x ::= variable-not-otherwise-mentioned)
  (n ::= number))

(define-metafunction LambdaCalculus
  concat-xs : (x ...) (x ...) -> (x ...)
  [(concat-xs (x_1 ...) (x_2 ...)) (x_1 ... x_2 ...)])


(term-let-assert-equal () (term (concat-xs ( ) ( ))) (term ( )))
(term-let-assert-equal () (term (concat-xs (a) ( ))) (term (a)))
(term-let-assert-equal () (term (concat-xs ( ) (b))) (term (b)))
(term-let-assert-equal () (term (concat-xs (a b c) (x y z))) (term (a b c x y z)))

(define-metafunction LambdaCalculus   
  make-set : (x ...) -> (x ...)
  [(make-set (x_0 x_1 ... x_0 x_2 ... )) 
   (concat-xs (x_0) (make-set (concat-xs (x_1 ...) (x_2 ...))))]
  [(make-set (x_0 x_1 ...))
   (concat-xs (x_0) (make-set (x_1 ...)))]
  [(make-set ()) ()])

(term-let-assert-equal () (term (make-set ( ))) (term ( )))
(term-let-assert-equal () (term (make-set (a))) (term (a)))
(term-let-assert-equal () (term (make-set (a b c))) (term (a b c)))
(term-let-assert-equal () (term (make-set (a b c b x a y z ))) (term (a b c x y z)))


(define-metafunction LambdaCalculus   
  set-union : (x ...) (x ...) -> (x ...)
  [(set-union (x_0 ...) (x_1 ...))
   (make-set (concat-xs (x_0 ...) (x_1 ...)))])

(term-let-assert-equal () (term (set-union () ())) (term ()))
(term-let-assert-equal () (term (set-union (a b c) (x y z))) (term (a b c x y z)))
(term-let-assert-equal () (term (set-union (a b c) (x y a i b z))) (term (a b c x y i z)))

(define-metafunction LambdaCalculus 
  set-remove : (x ...) x -> (x ...)
  [(set-remove (x_0 ... x x_1 ...) x) (concat-xs (x_0 ...) (x_1 ...))]
  [(set-remove (x_0 ...) x) (x_0 ...)])

(term-let-assert-equal () (term (set-remove () a)) (term ()))
(term-let-assert-equal () (term (set-remove (a) a)) (term ()))
(term-let-assert-equal () (term (set-remove (a) b)) (term (a)))
(term-let-assert-equal () (term (set-remove (a b c d) c)) (term (a b d)))
(term-let-assert-equal () (term (set-remove (a b c d) d)) (term (a b c)))
(term-let-assert-equal () (term (set-remove (a b c d) a)) (term (b c d)))

(define-metafunction LambdaCalculus 
  set-contains? : (x ...) x -> boolean 
  [(set-contains? (x_0 ... x x_1 ...) x) #t ]
  [(set-contains? (x_0 ...) x) #f ])

(term-let-assert-equal () (term (set-contains? () a)) (term #f))
(term-let-assert-equal () (term (set-contains? (a) a)) (term #t))
(term-let-assert-equal () (term (set-contains? (a) b)) (term #f))
(term-let-assert-equal () (term (set-contains? (a b c) x)) (term #f))
(term-let-assert-equal () (term (set-contains? (a b c) b)) (term #t))

(define-metafunction LambdaCalculus
  fv : e ->  (x ...)
  [(fv x) (x)]
  [(fv (e_1 e_2)) 
   (make-set (concat-xs (fv e_1) (fv e_2)))]
  [(fv (lambda x e)) 
   (set-remove (make-set (fv e)) x)])

(term-let-assert-equal () (term (fv z)) (term (z)))
(term-let-assert-equal () (term (fv (a b))) (term (a b)))
(term-let-assert-equal () (term (fv (lambda x (a b)))) (term (a b)))
(term-let-assert-equal () (term (fv (lambda x (a (b x))))) (term (a b)))
(term-let-assert-equal () (term (fv (lambda y (x (lambda x (x y)))))) (term (x)))

; x - variable to be replaced
; e - value x has to be replaced with
; e - in expression.
; Capture avoiding subsitution.
; (1) x[x → e] = e
; (2) y[x → e] = y if x ≠ y
; (3) (t1 t2)[x → e] = (t1[x → e] t2[x → e])
; (4) (λ y.t)[x → e] = (λ y.t) if x = y
; (5) (λ y.t)[x → e] = λy.(t[x → e]) if x ≠ y and y not in fv(e)
; (6) (λ y.t)[x → e] = λz.(t[y → z][x → e]) if x ≠ y, z is fresh (i.e. z not in fv(e) U fv(t))
; FIXME really need side-conditions and where.
(define-metafunction LambdaCalculus
  subs : x e e -> e
  [(subs x e x) e]        ;(1)
  [(subs x_0 e x_1) x_1]  ;(2)
  [(subs x e (e_1 e_2)) ((subs x e e_1) (subs x e e_2))] ;(3)
  [(subs x e (lambda x e_1)) (lambda x e_1)] ;(4)
  [(subs x_0 e_0 (lambda x_1 e_1)) 
   ,(subs_check_is_false_1 (term (lambda x_1 (subs x_0 e_0 e_1))) 
                         (term (set-contains? (fv e_0) x_1)))]
  [(subs x_0 e_0 (lambda x_1 e_1))
   (lambda ,(variable_not_in (term (union-sets (fv e_0) (fv e_1))) (term r))
     (subs x_0 e_0 
       (subs x_1 ,(variable_not_in (term (union-sets (fv e_0) (fv e_1))) (term r))  e_1)))])

(term-let-assert-equal () (term (subs x y x)) (term y))
(term-let-assert-equal () (term (subs x y z)) (term z))
(term-let-assert-equal () (term (subs x y (a x))) (term (a y)))
(term-let-assert-equal () (term (subs x y (a z))) (term (a z)))
(term-let-assert-equal () (term (subs x y (lambda x b))) (term (lambda x b)))
(term-let-assert-equal () (term (subs x m (lambda y (x y)))) (term (lambda y (m y))))
(term-let-assert-equal () (term (subs x y (lambda y (x y)))) (term (lambda r (y r))))
