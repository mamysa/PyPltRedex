
(term-let-assert-equal () 
  (term ,(variable_not_in (term (a1 a2 a11 a5)) (term a)))
  (term a))

(term-let-assert-equal () 
  (term ,(variable_not_in (term (a a1 a2 a11 a5)) (term a)))
  (term a3))

(term-let-assert-equal () 
  (term ,(variable_not_in (term (a1 a2 (a3 a a4))) (term a)))
  (term a5))

(term-let-assert-equal () 
  (term ,(variable_not_in (term (a1 a2 (a3 a a4))) (term b)))
  (term b))

(term-let-assert-equal () 
  (term ,(variable_not_in (term ()) (term a)))
  (term a))

(term-let-assert-equal () 
  (term ,(variable_not_in (term a0) (term a)))
  (term a))

(term-let-assert-equal () 
  (term ,(variable_not_in (term a) (term a)))
  (term a1))

(term-let-assert-equal () 
  (term ,(variable_not_in (term (a a0)) (term a)))
  (term a1))

(term-let-assert-equal () 
  (term ,(variable_not_in (term (a a0)) (term a0)))
  (term a1))

(term-let-assert-equal () 
  (term ,(variable_not_in (term (a a0)) (term a00)))
  (term a00))

(term-let-assert-equal () 
  (term ,(variable_not_in (term (a a00)) (term a00)))
  (term a1))
