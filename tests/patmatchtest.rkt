(define-language Lc 
  (e ::= (+ e e) n)
  (n ::= number)
  (x ::= variable-not-otherwise-mentioned)
  (P ::= (n ... E e ...))
  (E ::= (+ E e) (+ n E) hole))

(redex-match-assert-equal Lc n (term 1) ((match (bind n 1))))
(redex-match-assert-equal Lc e (term 2) ((match (bind e 2))))
(redex-match-assert-equal Lc e_1 (term (+ 1 2)) ((match (bind e_1 (+ 1 2)))))
(redex-match-assert-equal Lc x (term n) ((match (bind x n))))
(redex-match-assert-equal Lc x (term +) ())

(redex-match-assert-equal Lc (+ e_1 e_2) (term (+ (+ 1 2) 3))
            ((match (bind e_1 (+ 1 2)) (bind e_2 3))))

(redex-match-assert-equal Lc (+ e_1 e_2) (term (+ (+ 1 2) (+ 3 4)))
              ((match (bind e_1 (+ 1 2)) (bind e_2 (+ 3 4)))))

; non-deterministic repetion matching.
(redex-match-assert-equal Lc (n_1 ... n_2 ...) (term (1 2 3))
  ((match (bind n_1 ()) (bind n_2 (1 2 3)))
   (match (bind n_1 (1)) (bind n_2 (2 3)))
   (match (bind n_1 (1 2)) (bind n_2 (3)))
   (match (bind n_1 (1 2 3)) (bind n_2 ()))))

; different ellipsis depth
(redex-match-assert-equal Lc ((x n ...) ...) (term ((x 1 2) (y 3 4 5) (z)))
             ((match (bind n ((1 2) (3 4 5) ())) (bind x (x y z)))))

; contraint checks
(redex-match-assert-equal Lc ((n_1 ...) (n_1 ...))  (term ((1 2 3) (1 2 3)))
  ((match (bind n_1 (1 2 3)))))

(redex-match-assert-equal Lc (((n_1 ...) ... ) ((n_1 ...) ...))  (term (((1 2 3) (4 5)) ((1 2 3) (4 5))))
  ((match (bind n_1 ((1 2 3) (4 5))))))

(redex-match-assert-equal Lc ((n_1 ... n_1 ...) n_1 ...)  (term ((1 2 3 1 2 3) 1 2 3))
  ((match (bind n_1 (1 2 3)))))

; remove multiple bindings in the end of the matching
(redex-match-assert-equal Lc ((n_1 n_1 n_1) ...)  (term ((1 1 1)(2 2 2)(3 3 3)))
  ((match (bind n_1 (1 2 3)))))

(redex-match-assert-equal Lc ((n_1 ... n_2 ...) ...) (term ((1 2) (3 4)))
  ((match (bind n_2 ((1 2) (3 4))) (bind n_1 ((   ) (   ))))
   (match (bind n_2 ((1 2) (  4))) (bind n_1 ((   ) (3  ))))
   (match (bind n_2 ((1 2) (   ))) (bind n_1 ((   ) (3 4))))
   (match (bind n_2 ((  2) (3 4))) (bind n_1 ((1  ) (   ))))
   (match (bind n_2 ((  2) (  4))) (bind n_1 ((1  ) (3  ))))
   (match (bind n_2 ((  2) (   ))) (bind n_1 ((1  ) (3 4))))
   (match (bind n_2 ((   ) (3 4))) (bind n_1 ((1 2) (   ))))
   (match (bind n_2 ((   ) (  4))) (bind n_1 ((1 2) (3  ))))
   (match (bind n_2 ((   ) (   ))) (bind n_1 ((1 2) (3 4))))))

(redex-match-assert-equal Lc ((n_1 ... n_2 ...) ... (n_3 ... n_4 ...) ...)
  (term ((1)(3)))
  ((match (bind n_1 ()) (bind n_2 ()) (bind n_3 (() ())) (bind n_4 ((1) (3))))
   (match (bind n_1 ()) (bind n_2 ()) (bind n_3 (() (3))) (bind n_4 ((1) ())))
   (match (bind n_1 ()) (bind n_2 ()) (bind n_3 ((1) ())) (bind n_4 (() (3))))
   (match (bind n_1 ()) (bind n_2 ()) (bind n_3 ((1) (3))) (bind n_4 (() ())))
   (match (bind n_1 (())) (bind n_2 ((1))) (bind n_3 (())) (bind n_4 ((3))))
   (match (bind n_1 (())) (bind n_2 ((1))) (bind n_3 ((3))) (bind n_4 (())))
   (match (bind n_1 ((1))) (bind n_2 (())) (bind n_3 (())) (bind n_4 ((3))))
   (match (bind n_1 ((1))) (bind n_2 (())) (bind n_3 ((3))) (bind n_4 (()))) 
   (match (bind n_1 (() ())) (bind n_2 ((1) (3))) (bind n_3 ()) (bind n_4 ()))
   (match (bind n_1 (() (3))) (bind n_2 ((1) ())) (bind n_3 ()) (bind n_4 ()))
   (match (bind n_1 ((1) ())) (bind n_2 (() (3))) (bind n_3 ()) (bind n_4 ()))
   (match (bind n_1 ((1) (3))) (bind n_2 (() ())) (bind n_3 ()) (bind n_4 ()))))

(redex-match-assert-equal Lc (+ e_1 e_1)  (term (+ (+ 3 4) (+ 3 4)))
  ((match (bind e_1 (+ 3 4)))))

; evaluation contexts
(redex-match-assert-equal Lc hole (term hole)
  ((match)))

(redex-match-assert-equal Lc E (term (+ hole (+ 1 1)))
  ((match (bind E (+ hole (+ 1 1))))))

(redex-match-assert-equal Lc E (term (+ 2 hole))
  ((match (bind E (+ 2 hole)))))

(redex-match-assert-equal Lc E (term (+ (+ 1 1) hole))
  ())

(redex-match-assert-equal Lc P (term ( 1 2 3 (+ 1 hole) (+ 1 2) 5))
  ((match (bind P (1 2 3 (+ 1 hole) (+ 1 2) 5)))))

(redex-match-assert-equal Lc (n_1 ... hole n_2 ...) (term ( 1 2 hole 3))
  ((match (bind n_1 (1 2)) (bind n_2 (3)))))

; handle literals under ellipsis correctly 
(redex-match-assert-equal Lc (44 ...) (term (44 44 44))
  ((match)))

; number, real, natural, integer tests.
(redex-match-assert-equal Lc number_1 (term -1)
  ((match (bind number_1 -1))))

(redex-match-assert-equal Lc natural_1 (term -1)
  ())

(redex-match-assert-equal Lc natural_1 (term 1)
  ((match (bind natural_1 1))))

(redex-match-assert-equal Lc natural_1 (term -1)
  ())

(redex-match-assert-equal Lc (real_1 ...) (term (1.012 1337.0 1.2 4.0))
  ((match (bind real_1 (1.012 1337.0 1.2 4.0)))))

(redex-match-assert-equal Lc (number_1  ...) (term (1.012 1337 1 4.0))
  ((match (bind number_1  (1.012 1337 1 4.0)))))

(redex-match-assert-equal Lc (a b c) (term (a b c))
  ((match)))

(redex-match-assert-equal Lc ((1337 number_1) ...) (term ((1337 3.0) (1337 2)))
  ((match (bind number_1 (3.0 2)))))

(redex-match-assert-equal Lc (1.25 3.45 6.3) (term (1.25 3.45 6.3))
  ((match)))

(redex-match-assert-equal Lc (+12.12) (term (-12.12))
  ())

(redex-match-assert-equal Lc (+12.12) (term (12.12))
  ((match)))

(redex-match-assert-equal Lc (+12) (term (-12))
  ())

(redex-match-assert-equal Lc (+12) (term (12))
  ((match)))

; matching strings
(redex-match-assert-equal Lc (string_1 ...) (term ("hello" "world!"))
   ((match (bind string_1 ("hello" "world!")))))

; matching literal strings.
(redex-match-assert-equal Lc ("oh no!" ...) (term ("oh no!" "oh no!"))
   ((match)))

(redex-match-assert-equal Lc ("oh no!" ...) (term ("oh no!" "oh yes!" "oh no!"))
   ())

; booleans
(redex-match-assert-equal Lc (boolean_1 ...) (term (#t #true #false))
  ((match (bind boolean_1 (#t #t #f)))))
;

(redex-match-assert-equal Lc #t (term #t)
  ((match)))

(redex-match-assert-equal Lc #t (term #true)
  ((match)))

(redex-match-assert-equal Lc #t (term #f)
  ())

;any pattern
(redex-match-assert-equal Lc (any_1 ...) (term (1 #false "hello world!" 12.44 (1337) ()))
  ((match (bind any_1 (1 #false "hello world!" 12.44 (1337) ())))))

(redex-match-assert-equal Lc 
  (number_1 -12 real_1 -0.1 string_1 "hello world!" boolean_1 #t variable-not-otherwise-mentioned_1 ohno) 
  (term (24 -12 1.0 -0.1 "this is a string" "hello world!" #f #t ohyes ohno))
  ((match (bind number_1 24) 
          (bind real_1 1.0) 
          (bind string_1 "this is a string") 
          (bind boolean_1 #f)
          (bind variable-not-otherwise-mentioned_1 ohyes))))
