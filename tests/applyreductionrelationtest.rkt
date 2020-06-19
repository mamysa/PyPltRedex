(define-language Lc3
  (es ::= (e ...))
  (e ::= (+ e e) n)
  (n ::= number)
  (P ::= (e ... E e ...))
  (E ::= hole (+ E e) (+ n E)))

(define-reduction-relation red Lc3 #:domain es
(--> (in-hole P (+ n_1 n_2))
     (in-hole P 1337)
     "add"))

(assert-term-lists-equal
  (apply-reduction-relation red (term (1 (+ 4 5) 3 (+ (+ 1 2) 4) 5)))
  ((term (1 1337 3 (+ (+ 1 2) 4) 5))
   (term (1 (+ 4 5) 3 (+ 1337 4) 5))))

(define-reduction-relation badred Lc3 
(--> (in-hole P 1337)
     x
     "this-doesn't-make-sense!"))

(assert-term-lists-equal
  (apply-reduction-relation badred (term (1 2 1337 (+ 1 2) 3)))
  ((term x)))


(define-language Lc4
  (n ::= number)
  (x ::= variable-not-otherwise-mentioned)
  (E ::= (n hole)))

(define-reduction-relation red3 Lc4 
 (--> ((in-hole E x) ...)
      ((in-hole E 1337) ...) 
      "blah"))

(assert-term-lists-equal
  (apply-reduction-relation red3 (term ((1 a) (2 b))))
  ((term ((1 1337) (2 1337)))))