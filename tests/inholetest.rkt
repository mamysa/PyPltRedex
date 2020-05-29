(define-language HoleTest
  (n  ::= number)
  (e ::= (+ e e) n)
  (x ::= variable-not-otherwise-mentioned)
  (P ::= (n ... E e ...))
  (E  ::= (+ E e) ( + n E) hole)
  (E2 ::= (n hole))
  (E3 ::= (n ... hole)))

(match-equal? 
  (redex-match HoleTest (in-hole P n) (term (1 2 3)))
  (match (bind n 1) (bind P (hole 2 3)))
  (match (bind n 2) (bind P (1 hole 3)))
  (match (bind n 3) (bind P (1 2 hole))))

(match-equal? 
  (redex-match HoleTest (in-hole P n) (term (1 2 (+ (+ 3 4) 5) 6)))
  (match (bind n 1) (bind P (hole 2 (+ (+ 3 4) 5) 6)))
  (match (bind n 2) (bind P (1 hole (+ (+ 3 4) 5) 6)))
  (match (bind n 3) (bind P (1 2 (+ (+ hole 4) 5) 6)))
  (match (bind n 4) (bind P (1 2 (+ (+ 3 hole) 5) 6))))

(match-equal?
  (redex-match HoleTest (in-hole P e) (term (1 2 (+ (+ 3 4) 5) 6)))
  (match (bind e 1) (bind P (hole 2 (+ (+ 3 4) 5) 6)))
  (match (bind e 2) (bind P (1 hole (+ (+ 3 4) 5) 6)))
  (match (bind e (+ (+ 3 4) 5)) (bind P (1 2 hole 6)))
  (match (bind e (+ 3 4)) (bind P (1 2 (+ hole 5) 6)))
  (match (bind e 3) (bind P (1 2 (+ (+ hole 4) 5) 6)))
  (match (bind e 4) (bind P (1 2 (+ (+ 3 hole) 5) 6))))


(match-equal?
  (redex-match HoleTest (in-hole E e) (term (+ 1 2)))
  (match (bind e (+ 1 2)) (bind E hole))
  (match (bind e 1) (bind E (+ hole 2)))
  (match (bind e 2) (bind E (+ 1 hole))))

; non-determinism tests 
(match-equal?
  (redex-match HoleTest (in-hole (n_1 ... hole n_2 ...) n) (term (1 2 3) ))
  (match (bind n 1) (bind n_1 ()) (bind n_2 (2 3)))
  (match (bind n 2) (bind n_1 (1)) (bind n_2 (3)))
  (match (bind n 3) (bind n_1 (1 2)) (bind n_2 ())))

(match-equal?
  (redex-match HoleTest (in-hole hole (n_1 ... n_2 ...)) (term (1 2)))
  (match (bind n_1 ())    (bind n_2 (1 2)))
  (match (bind n_1 (1))   (bind n_2 (2)))
  (match (bind n_1 (1 2)) (bind n_2 ())))

(match-equal?
  (redex-match HoleTest (in-hole ((n_1 ...) ... hole (n_2 ...) ...) (n_3 ...)) (term ((1 2) (3) () (4)) ))
  (match (bind n_1 ()) (bind n_2 ((3) () (4))) (bind n_3 (1 2)))
  (match (bind n_1 ((1 2))) (bind n_2 (() (4))) (bind n_3 (3)))
  (match (bind n_1 ((1 2) (3))) (bind n_2 ((4))) (bind n_3 ()))
  (match (bind n_1 ((1 2) (3) ())) (bind n_2 ()) (bind n_3 (4))))

; in-hole pat under ellipsis
(match-equal?
  (redex-match HoleTest ((in-hole E2 x) ...) (term ((1 a) (2 b))))
  (match (bind E2 ((1 hole) (2 hole))) (bind x (a b))))

(match-equal?
  (redex-match HoleTest (n (in-hole E2 x) ...) (term (1337 (1 a) (2 b))))
  (match (bind E2 ((1 hole) (2 hole))) (bind x (a b)) (bind n 1337)))

(match-equal?
  (redex-match HoleTest (n (in-hole E2 x) n) (term (1337 (1 a) 1337)))
  (match (bind E2 (1 hole)) (bind n 1337) (bind x a)))

(match-equal?
  (redex-match HoleTest (((in-hole E3 x) ...) ...) (term (((1 2 a)(3 b))((c)(4 5 d)))))
  (match (bind E3 (((1 2 hole) (3 hole)) ((hole) (4 5 hole)))) (bind x ((a b) (c d)))))

(match-equal?
  (redex-match HoleTest ((in-hole ((n_1 ...) ... hole (n_2 ...) ...) (n_3 ...)) ...) (term (((1) (2 3))((4)))))
  (match (bind n_1 (() ())) (bind n_2 (((2 3)) ())) (bind n_3 ((1) (4))))
  (match (bind n_1 (((1)) ())) (bind n_2 (() ())) (bind n_3 ((2 3) (4)))))
