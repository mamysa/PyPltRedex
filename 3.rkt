#lang racket
(require redex)
(require pict)
(require redex/pict)



(define-language Lc
  (p ::= (e ...))
  (e ::= (e e) (+ e ...)  v x)
  (v ::= (λ (x t) e) n)
  (n ::= number)
  (t ::= (t → t) num bool)
  (E ::= (E e) (v E) hole)

  (Γ ::= ((x t) ...))
  (x ::= variable-not-otherwise-mentioned))


;(redex-match Lc e (term (2 5 1)))

(define-metafunction Lc 
  set-contains? : (x ...) x -> boolean 
  [(set-contains? (x_0 ... x x_1 ...) x) #t ]
  [(set-contains? (x_0 ...) x) #f ])


(test-equal (term (set-contains? () a)) #f)
(test-equal (term (set-contains? (a) a)) #t)
(test-equal (term (set-contains? (a) b)) #f)
(test-equal (term (set-contains? (a b c) x)) #f)
(test-equal (term (set-contains? (a b c) b)) #t)


;(redex-match Lc ((x_0 t_0) ... (z t) (x_1 t_1) ...) (term ((b num) (z num) (a num) (c num) (z bool) (d num))))


;(redex-match Lc G (term ((b num) (z (num → num)  ))))

;(show-pict (render-term Lc ((λ x x) 5)))


;(redex-match Lc t (term (num → num)))
;(redex-match Lc t  (term num))

(define-judgment-form Lc
  #:contract (types Γ e t)
  #:mode (types I I O)
  
  [(types (extend Γ x t_1) e t_2)
   --------------------------------------------------"λ-abstraction" 
   (types Γ (λ (x t_1) e) (t_1 → t_2))]

  [(types Γ e_1 (t_2 → t_3)) 
   (types Γ e_2 t_2) 
   ------------------------"λ-app"
   (types Γ (e_1 e_2) t_3)]

  [(types Γ e num) ...
   -----------------------"+"
   (types Γ (+ e ...) num)]

  [-------------"var"
   (types Γ x (lookup Γ x) )]

  [------------- "num"
   (types Γ number num)])

(define-judgment-form Lc
  #:contract (types-expressions Γ p (t ...))
  #:mode (types-expressions I I O)

  [(types Γ e t) 
   ----------------------------------"e-list-last"
   (types-expressions Γ (e) (t))]

  [(types Γ e_1 t_1) 
   (types-expressions Γ (e_2 ...) (t_2 ...))
   -------------------------------------"e-list"
   (types-expressions Γ (e_1 e_2 ...) (t_1 t_2 ...))])




  


; get leftmost matching variable in the context.
(define-metafunction Lc
  lookup : Γ x -> t 
  [(lookup ((x_0 t_0) ... (x t) (x_1 t_1) ...) x) 
   t
   (side-condition (equal? #f (term (set-contains? (x_0 ...) x))))]
  [(lookup ((x_0 t_0) ...) x) ,(error 'lookup "not found ~e" (term x))])

(define-metafunction Lc
  extend : Γ x t -> Γ
  [(extend ((x_0 t_0) ...) x t) ((x t) (x_0 t_0) ...)])

;(define x (build-derivations (types () ((λ (y num) (λ (y num) y)) 3) t)))
;(show-pict (derivation->pict Lc (car x)))

;(define x (build-derivations (types () (+ 1 4 5 3) t)))



;(judgment-holds (types-expressions () (1 4 3 2) (t ...)))
(define x (build-derivations (types-expressions () (1 (λ (z num) z) 5 3) (t ...))))
(show-pict (derivation->pict Lc (car x)))



  

(test-equal (term (lookup ((a num) (b num) (x num) (c num)) x)) (term num))
(test-equal (term (lookup ((a num) (b num) (x bool) (c num) (d num) (x num) (e num)) x)) (term bool))

;(test-equal (term (extend ((a num) (b num) (x num) (c num)) x num)) (term ()))
;(test-equal (term (extend ((a num) (b num) (c num)) x num)) (term ((a num) (b num) (c num) (x num))))
;(test-equal (term (lookup ((a num) (b num) (x (num → num)) (c num)) x)) (term (num → num)))





;(judgment-holds (types () x t))


;(define x (build-derivations (types () x t)))
;(show-pict (derivation->pict Lc (car x)))

;(judgment-holds (types () (λ (y num) (λ (x num) x)) t) t)



(define-metafunction Lc
  vars-append : (x ...) (x ...) -> (x ...)
  [(vars-append (x_1 ...) (x_2 ...)) (x_1 ... x_2 ...)])

(test-equal (term (vars-append () ())) (term ()))
(test-equal (term (vars-append (a) ())) (term (a)))
(test-equal (term (vars-append () (b))) (term (b)))
(test-equal (term (vars-append (a b c) (x y z))) (term (a b c x y z)))


(define-metafunction Lc 
  make-set : (x ...) -> (x ...)
  [(make-set (x_0 x_1 ... x_0 x_2 ... )) 
   (vars-append (x_0) (make-set (vars-append (x_1 ...) (x_2 ...))))]
  [(make-set (x_0 x_1 ...))
   (vars-append (x_0) (make-set (x_1 ...)))]
  [(make-set (x)) (x)]
  [(make-set ()) ()])

(test-equal (term (make-set ())) (term ()))
(test-equal (term (make-set (a))) (term (a)))
(test-equal (term (make-set (a b c))) (term (a b c)))
(test-equal (term (make-set (a b c b x a y z ))) (term (a b c x y z)))

(define-metafunction Lc 
  remove-from-set : (x ...) x -> (x ...)
  [(remove-from-set (x_0 ... x x_1 ...) x) (vars-append (x_0 ...) (x_1 ...))]
  [(remove-from-set (x_0 ...) x) (x_0 ...)])


(test-equal (term (remove-from-set () a)) (term ()))
(test-equal (term (remove-from-set (a) a)) (term ()))
(test-equal (term (remove-from-set (a) b)) (term (a)))
(test-equal (term (remove-from-set (a b c d) c)) (term (a b d)))
(test-equal (term (remove-from-set (a b c d) d)) (term (a b c)))
(test-equal (term (remove-from-set (a b c d) a)) (term (b c d)))


;(define-metafunction Lc
;  remove-multiple-from-set : (x ...) (x ...) -> (x ...)
;  [(remove-multiple-from-set (x_0 ...) (x_1 x_2 ...))  
;   (remove-multiple-from-set (remove-from-set (x_0 ...) x_1) (x_2 ...))]
;  [(remove-multiple-from-set (x_0 ...) ()) (x_0 ...)])

(define-metafunction Lc
  union-sets : (x ...) (x ...) -> (x ...)
  [(union-sets (x_0 ...) (x_1 ...))
   (make-set (vars-append  (x_0 ...) (x_1 ...)))])


(test-equal (term (union-sets () ())) (term ()))
(test-equal (term (union-sets (a b c) (x y z))) (term (a b c x y z)))
(test-equal (term (union-sets (a b c) (x y a i b z))) (term (a b c x y i z)))


   
(define-metafunction Lc 
  fv : e ->  (x ...)
  [(fv n) () ]
  [(fv x) (x)]
  [(fv (e_1 e_2)) 
   (make-set (vars-append (fv e_1) (fv e_2)))]
  [(fv (λ x e)) 
   (remove-from-set (make-set (fv e)) x)])

;(test-equal (term (fv 4)) (term ()))
;(test-equal (term (fv z)) (term (z)))
;(test-equal (term (fv (a 2))) (term (a)))
;(test-equal (term (fv (a b))) (term (a b)))
;(test-equal (term (fv (λ x (a b)))) (term (a b)))
;(test-equal (term (fv (λ x (a (b x))))) (term (a b)))
;(test-equal (term (fv (λ y (x (λ x (x y)))))) (term (x)))



; Capture avoiding subsitution.
; (1) x[x → e] = e
; (2) y[x → e] = y if x ≠ y
; (3) (t1 t2)[x → e] = (t1[x → e] t2[x → e])
; (4) (λ y.t)[x → e] = λy.(t[x → e]) if x ≠ y and y not in fv(e)
; (5) (λ y.t)[x → e] = λz.(t[y → z][x → e]) if x ≠ y, z is fresh (i.e. z not in fv(e) U fv(t))
; (6) (λ y.t)[x → e] = (λ y.t) if x = y
(define-metafunction Lc 
  subs : x e e -> e
  [(subs x e n) n]
  [(subs x e x) e]
  [(subs x_0 e x_1) x_1]
  [(subs x e (e_1 e_2)) ((subs x e e_1) (subs x e e_2))]
  [(subs x e (λ x e_1)) (λ x e_1)]
  [(subs x_0 e_0 (λ x_1 e_1)) 
   (λ x_1 e_2)
   (where e_2  (subs x_0 e_0 e_1))
   (side-condition (equal? #f (term (set-contains? (fv e_0) x_1))))]
  [(subs x_0 e_0 (λ x_1 e_1))
   (λ x_fresh (subs x_0 e_0 (subs x_1 x_fresh e_1)))
   (where x_fresh ,(variable-not-in (term (union-sets (fv e_0) (fv e_1))) (term r)))])

;(test-equal (term (subs x 4 x)) (term 4))
;(test-equal (term (subs x 4 z)) (term z))
;(test-equal (term (subs x y x)) (term y))
;(test-equal (term (subs x y z)) (term z))
;(test-equal (term (subs x y (a x))) (term (a y)))
;(test-equal (term (subs x y (a z))) (term (a z)))
;(test-equal (term (subs x y (λ x b))) (term (λ x b)))
;(test-equal (term (subs x m (λ y (x y)))) (term (λ y (m y))))
;(test-equal (term (subs x y (λ y (x y)))) (term (λ r (y r))))


(define red 
  (reduction-relation Lc #:domain e
    (--> (in-hole E ((λ x e) v))
         (in-hole E (subs x v e))
         "λapp")
    (--> (in-hole E x)
         (in-hole E 4)
         "var")))

(define t 
  (term 
    ((
      (λ x (λ y (x y)))
      ((λ x (λ y (x y) )) y)) z)))


;(traces red (term ((λ x 5) m)))
;(traces red (term (5 4)))

;(traces red (term ((λ x (λ y (λ z ((x z) x)))) m)))

;(traces red (term ((λ x (λ y (x y))) y)))
;(traces red t)
