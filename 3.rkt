#lang racket
(require redex)
(require pict)
(require redex/pict)

(define-language Lc
  (p ::= (V (o ...)))
  (o ::= (define x e) e) ; top level expressions.
  (e ::= (e e) (+ e ...) v x)
  (v ::= (λ (x t) e) n void)
  (n ::= number)
  (t ::= (t → t) num bool void)

  (V ::= ((x any) ...)) 
  (P ::=  (v ... E o ...))
  (E ::= (v E) (E e) (+ v ... E e ...) (define x E) hole)
  (arithop ::= + - * /)

  (Γ ::= ((x t) ... G (x t) ...))
  (x ::= variable-not-otherwise-mentioned))

(define-metafunction Lc 
  set-contains? : (x ...) x -> boolean 
  [(set-contains? (x_0 ... x x_1 ...) x) #t ]
  [(set-contains? (x_0 ...) x) #f ])

(test-equal (term (set-contains? () a)) #f)
(test-equal (term (set-contains? (a) a)) #t)
(test-equal (term (set-contains? (a) b)) #f)
(test-equal (term (set-contains? (a b c) x)) #f)
(test-equal (term (set-contains? (a b c) b)) #t)


(define-metafunction Lc 
  store-variable : V x v -> V
  [(store-variable ((x_0 any_0) ... (x any_1) (x_2 any_2) ...) x v)
   ((x_0 any_0) ... (x v) (x_2 any_2) ...)]
  [(store-variable ((x_0 any_0) ...) x v)
   ((x_0 any_0) ... (x v))])



(test-equal (term (store-variable ((x 3) (y 6) (z 1)) y 3)) (term ((x 3) (y 3) (z 1))))
(test-equal (term (store-variable ((x 3) (y 6) (z 1)) z 3)) (term ((x 3) (y 6) (z 3))))
(test-equal (term (store-variable ((x 3) (y 6)) z 3)) (term ((x 3) (y 6) (z 3))))
  




;(redex-match Lc (e_1 ... x e_2 ...) (term ((y y) (x x) x (z z) y (m m))))


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
   ----------------------------------"o-list-last"
   (types-expressions Γ (e) (t))]

  [(types Γ e t_1) 
   (types-expressions (define-global Γ x t_1) (o_2 ...) (t_2 ...))
   -----------------------------------------------------------------"o-list-define"
   (types-expressions Γ ((define x e) o_2 ...) (t_1 t_2 ...))]

  [(types Γ e_1 t_1) 
   (types-expressions Γ (o_2 ...) (t_2 ...))
   -------------------------------------"o-list"
   (types-expressions Γ (e_1 o_2 ...) (t_1 t_2 ...))])


; get leftmost matching variable in the context.
(define-metafunction Lc
  lookup : Γ x -> t 
  [(lookup ((x_0 t_0) ... (x t) (x_1 t_1) ... G (x_2 t_2) ...) x) 
   t
   (side-condition (equal? #f (term (set-contains? (x_0 ...) x))))]
  [(lookup ((x_0 t_0) ... G (x_1 t_1) ... (x t) (x_2 t_2) ...) x) 
   t
   (side-condition (equal? #f (term (set-contains? (x_1 ...) x))))]
  [(lookup ((x_0 t_0) ... G (x_1 t_1) ...) x) ,(error 'lookup "not found ~e" (term x))])

(test-equal (term (lookup ((a num) (b num) (x num) G (c num)) x)) (term num))
(test-equal (term (lookup ((a num) (b num) (x bool) (c num) (d num) (x num) (e num) G) x)) (term bool))
(test-equal (term (lookup ((a num) (b num) (x bool) G (c num) (d num) (x num) (e num)) x)) (term bool))
(test-equal (term (lookup ((a num) (b num)  G (c num) (d num) (x num) (e num)) x)) (term num))

(define-metafunction Lc
  extend : Γ x t -> Γ
  [(extend ((x_0 t_0) ... G (x_1 t_1) ...) x t) ((x t) (x_0 t_0) ... G (x_1 t_1) ...)])

(define-metafunction Lc
  define-global : Γ x t -> Γ
  [(define-global ((x_0 t_0) ... G (x_1 t_1) ... (x t_3) (x_2 t_2) ...) x t)
   ,(error 'define-global "global ~e is already defined" (term x))]
  [(define-global ((x_0 t_0) ... G (x_1 t_1) ...) x t)
   ((x_0 t_0) ... G (x_1 t_1) ... (x t))])

(test-equal (term (define-global ((x num) G (a num) (b num) (c num)) x bool)) (term ((x num) G (a num) (b num) (c num) (x bool)))) 
; this is expected to fail.
;(test-equal (term (define-global (G (a num) (b num) (x num) (c num)) x bool)) (term num)) 


;(define x (build-derivations (types () ((λ (y num) (λ (y num) y)) 3) t)))
;(show-pict (derivation->pict Lc (car x)))

;(define x (build-derivations (types () (+ 1 4 5 3) t)))



;(judgment-holds (types-expressions () (1 4 3 2) (t ...)))
;(define x (build-derivations (types-expressions (G) (1 (λ (z num) z) 5 3) (t ...))))
;l(define x (build-derivations (types-expressions (G) ((define var 4) ((λ (x num) (+ var x)) 5)) (t ...))))
;(show-pict (derivation->pict Lc (car x)))
  


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
  do-arith : arithop (n ...) -> n 
  [(do-arith + (n ...)) ,(apply + (term (n ...)))]
  [(do-arith - (n ...)) ,(apply - (term (n ...)))]
  [(do-arith * (n ...)) ,(apply * (term (n ...)))]
  [(do-arith / (n_0 ... 0 n_1 ...)) ,(error 'arith-op "division by zero")]
  [(do-arith / (n ...)) ,(apply / (term (n ...)))])

(test-equal (term (do-arith + (1 2 3))) (term 6))
(test-equal (term (do-arith / (2 4 5))) (term 1/10))
(test-equal (term (do-arith * (2 4 5))) (term 40))


(define-metafunction Lc
  extract-variables : (e ...) -> (x ...)
  [(extract-variables (x e ...)) (union-sets (x) (extract-variables (e ...)))]
  [(extract-variables (e_1 e_2 ...)) (extract-variables (e_2 ...))]
  [(extract-variables ()) ()])


(test-equal (term (extract-variables (1 2 x (λ (p num) z) y m 1))) (term (x y m)))
(test-equal (term (extract-variables (1 2 (λ (p num) z) (p q)))) (term ()))
(test-equal (term (extract-variables ())) (term ()))



(define-metafunction Lc 
  fv : e ->  (x ...)
  [(fv n) () ]
  [(fv x) (x)]
  [(fv (+ e ...)) (extract-variables (e ...))]
  [(fv (e_1 e_2)) 
   (make-set (vars-append (fv e_1) (fv e_2)))]
  [(fv (λ (x t) e)) 
   (remove-from-set (make-set (fv e)) x)])

(test-equal (term (fv 4)) (term ()))
(test-equal (term (fv z)) (term (z)))
(test-equal (term (fv (a 2))) (term (a)))
(test-equal (term (fv (a b))) (term (a b)))
(test-equal (term (fv (+ a b 3 c))) (term (a b c)))
(test-equal (term (fv (λ (x num) (a b)))) (term (a b)))
(test-equal (term (fv (λ (x num) (a (b x))))) (term (a b)))
(test-equal (term (fv (λ (y num) (x (λ (x num) (x y)))))) (term (x)))
(test-equal (term (fv (λ (y num) (λ (x num) (+ x y z 2 t))))) (term (z t)))


(define-metafunction Lc 
  e-append : (e ...) (e ...) -> (e ...)
  [(e-append (e_1 ...) (e_2 ...)) (e_1 ... e_2 ...)])

(test-equal (term (e-append (1) (x))) (term (1 x)))
(test-equal (term (e-append ()  (x))) (term (x)))
(test-equal (term (e-append ((λ (x num) x))  ())) (term ((λ (x num) x))))

(define-metafunction Lc 
  e-contains? : (e ...) e -> boolean 
  [(e-contains? (e_0 ... e e_1 ...) e) #t ]
  [(e-contains? (e_0 ...) e) #f ])

(test-equal (term (e-contains? (2 4 x 1) x)) #t)
(test-equal (term (e-contains? (2 4 (λ (x num) x) 1) x)) #f)
(test-equal (term (e-contains? (2 4 (λ (x num) x) 1) (λ (x num) x))) #t)

(define-metafunction Lc 
  e-subs : x e (e ...) -> (e ...)
  [(e-subs x e (e_1 ... x e_2 ...))
   (e-append (e_1 ... e) (e-subs x e (e_2 ...)))
   (side-condition (equal? #f (term (e-contains? (e_1 ...) x))))]
  [(e-subs x e (e_1 ...)) (e_1 ...)])

(test-equal (term (e-subs z 1337 (2 (λ (z num) z) x z 1 z (z 1)))) (term (2 (λ (z num) z) x 1337 1 1337 (z 1))) )
(test-equal (term (e-subs z 1337 (2 (λ (z num) z) x z 1 z z))) (term (2 (λ (z num) z) x 1337 1 1337 1337)))

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
  [(subs x e (+ e_1 ...)) 
   (+ e_r ...)
   (where (e_r ...) (e-subs x e (e_1 ...)))]
  [(subs x e (λ (x t) e_1)) (λ (x t) e_1)]
  [(subs x_0 e_0 (λ (x_1 t) e_1)) 
   (λ (x_1 t) e_2)
   (where e_2  (subs x_0 e_0 e_1))
   (side-condition (equal? #f (term (set-contains? (fv e_0) x_1))))]
  [(subs x_0 e_0 (λ (x_1 t) e_1))
   (λ (x_fresh t) (subs x_0 e_0 (subs x_1 x_fresh e_1)))
   (where x_fresh ,(variable-not-in (term (union-sets (fv e_0) (fv e_1))) (term r)))])

(test-equal (term (subs x 4 x)) (term 4))
(test-equal (term (subs x 4 z)) (term z))
(test-equal (term (subs x y x)) (term y))
(test-equal (term (subs x y z)) (term z))
(test-equal (term (subs x y (a x))) (term (a y)))
(test-equal (term (subs x y (+ a x 1 4 x))) (term (+ a y 1 4 y)))
(test-equal (term (subs x y (a z))) (term (a z)))
(test-equal (term (subs x y (λ (x num) b))) (term (λ (x num) b)))
(test-equal (term (subs x m (λ (y num) (x y)))) (term (λ (y num) (m y))))
(test-equal (term (subs x y (λ (y num) (x y)))) (term (λ (r num) (y r))))
(test-equal (term (subs x m (λ (y num) (+ x y 1 x 4 x)))) (term (λ (y num) (+ m y 1 m 4 m))))
(test-equal (term (subs x y (λ (y num) (+ x y 1 x 4 x)))) (term (λ (r num) (+ y r 1 y 4 y))))


(define red 
  (reduction-relation Lc 
    #:domain p
    (--> (V (in-hole P ((λ (x t) e) v)))
         (V (in-hole P (subs x v e)))
         "λapp")
    (--> (V (in-hole P (+ n ...)))
         (V (in-hole P (do-arith + (n ...))))
         "arith-op")
    ;(--> (V (in-hole P (define x v)))
    ;     "define-var")
    (--> (V (in-hole P x))
         (V (in-hole P 4))
         "var")))


;(traces red (term ((λ x 5) m)))
;(traces red (term (5 4)))


;(traces red (term (() ((((λ (x num) (λ (y num) (+ 2 x y))) 5) 6)))))
(traces red (term (() ((((λ (x num) (λ (x num) (+ 2 x z x z))) 5) 6)))))



;(traces red (term (() (((λ (x num) (λ (y num) (x y))) y)))))
