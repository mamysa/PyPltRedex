(assert-term-eq () 
  (term ,(variable_not_in (term (a1 a2 a11 a5)) (term a)))
  (term a3))

(assert-term-eq () 
  (term ,(variable_not_in (term (a1 a2 (a3 a4))) (term a)))
  (term a5))

(assert-term-eq () 
  (term ,(variable_not_in (term (a1 a2 (a3 a4))) (term b)))
  (term b))

(assert-term-eq () 
  (term ,(variable_not_in (term ()) (term a)))
  (term a))
