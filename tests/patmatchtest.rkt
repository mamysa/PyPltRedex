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

; remove multiple bindings in the end of the matching
(match-equal? 
  (redex-match Lc ((n_1 n_1 n_1) ...)  (term ((1 1 1)(2 2 2)(3 3 3))))
  (match (bind n_1 (1 2 3))))

(match-equal?
  (redex-match Lc ((n_1 ... n_2 ...) ...) (term ((1 2) (3 4))))
  (match (bind n_2 ((1 2) (3 4))) (bind n_1 ((   ) (   ))))
  (match (bind n_2 ((1 2) (  4))) (bind n_1 ((   ) (3  ))))
  (match (bind n_2 ((1 2) (   ))) (bind n_1 ((   ) (3 4))))
  (match (bind n_2 ((  2) (3 4))) (bind n_1 ((1  ) (   ))))
  (match (bind n_2 ((  2) (  4))) (bind n_1 ((1  ) (3  ))))
  (match (bind n_2 ((  2) (   ))) (bind n_1 ((1  ) (3 4))))
  (match (bind n_2 ((   ) (3 4))) (bind n_1 ((1 2) (   ))))
  (match (bind n_2 ((   ) (  4))) (bind n_1 ((1 2) (3  ))))
  (match (bind n_2 ((   ) (   ))) (bind n_1 ((1 2) (3 4))))
)

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

; handle literals under ellipsis correctly 
(match-equal?
  (redex-match Lc (44 ...) (term (44 44 44)))
  (match))

; number, real, natural, integer tests.
(match-equal? 
  (redex-match Lc number_1 (term -1))
  (match (bind number_1 -1)))


(match-equal? 
  (redex-match Lc natural_1 (term -1))
  ())

(match-equal? 
  (redex-match Lc natural_1 (term 1))
  (match (bind natural_1 1)))

(match-equal? 
  (redex-match Lc natural_1 (term -1))
  ())

(match-equal? 
  (redex-match Lc (real_1 ...) (term (1.012 1337.0 1.2 4.0)))
  (match (bind real_1 (1.012 1337.0 1.2 4.0))))


(match-equal? 
  (redex-match Lc (number_1  ...) (term (1.012 1337 1 4.0)))
  (match (bind number_1  (1.012 1337 1 4.0))))


(match-equal? 
  (redex-match Lc (a b c) (term (a b c)))
  (match))

(match-equal? 
  (redex-match Lc ((1337 number_1) ...) (term ((1337 3.0) (1337 2))))
  (match (bind number_1 (3.0 2))))

(match-equal?
  (redex-match Lc (1.25 3.45 6.3) (term (1.25 3.45 6.3)))
  (match))

(match-equal?
  (redex-match Lc (+12.12) (term (-12.12)))
  ())

(match-equal?
  (redex-match Lc (+12.12) (term (12.12)))
  (match))

(match-equal?
  (redex-match Lc (+12) (term (-12)))
  ())

(match-equal?
  (redex-match Lc (+12) (term (12)))
  (match))

; matching strings
(match-equal? 
   (redex-match Lc (string_1 ...) (term ("hello" "world!")))
   (match (bind string_1 ("hello" "world!"))))

; matching literal strings.
(match-equal? 
   (redex-match Lc ("oh no!" ...) (term ("oh no!" "oh no!")))
   (match))

(match-equal? 
   (redex-match Lc ("oh no!" ...) (term ("oh no!" "oh yes!" "oh no!")))
   ())

; booleans
(match-equal?
  (redex-match Lc (boolean_1 ...) (term (#t #true #false)))
  (match (bind boolean_1 (#t #t #f))))
;

(match-equal? 
  (redex-match Lc #t (term #t))
  (match))

(match-equal? 
  (redex-match Lc #t (term #true))
  (match))

(match-equal? 
  (redex-match Lc #t (term #f))
  ())

; any pattern
(match-equal? 
  (redex-match Lc (any_1 ...) (term (1 #false "hello world!" 12.44 (1337) ())))
  (match (bind any_1 (1 #false "hello world!" 12.44 (1337) ()))))
