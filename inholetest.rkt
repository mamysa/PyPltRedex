(define-language HoleTest
  (n  ::= number)
  (e ::= (+ e e) n)
  (P ::= (n ... E e ...))
  (E  ::= (+ E e) ( + n E) hole))

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

(match-equal?
  (redex-match HoleTest (in-hole (n_1 ... hole n_2 ...) n) (term (1 2 3) ))
  (match (bind n 1) (bind n_1 ()) (bind n_2 (2 3)))
  (match (bind n 2) (bind n_1 (1)) (bind n_2 (3)))
  (match (bind n 3) (bind n_1 (1 2)) (bind n_2 ())))
