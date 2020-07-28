(term-let-assert-equal () 
  (term ,(variable_not_in (term (a1 a2 a11 a5)) (term a)))
  (term a3))

(term-let-assert-equal () 
  (term ,(variable_not_in (term (a1 a2 (a3 a4))) (term a)))
  (term a5))

(term-let-assert-equal () 
  (term ,(variable_not_in (term (a1 a2 (a3 a4))) (term b)))
  (term b))

(term-let-assert-equal () 
  (term ,(variable_not_in (term ()) (term a)))
  (term a))
