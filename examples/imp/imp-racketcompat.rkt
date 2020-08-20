#lang racket
(require redex)



(define-language Imp
  (Loc ::= ((var int) ...))
  (Program := (Loc (Com ...)))

  (Com  := skip
           (var = Aexp)
           (if Bexp (Com ...) else (Com ...))
           (while Bexp (Com ...))
        
        )
  (Aexp := var int (Aexp + Aexp) (Aexp * Aexp))
  (Bexp := bool (Aexp <= Aexp) (Bexp and Bexp) (Bexp or Bexp) (not Bexp))
  (var := variable-not-otherwise-mentioned)
  (int := integer)
  (bool := boolean) 

  (P ::= (var = E) (while E (Com ...)) (if E (Com ...) else (Com ...)) hole)
  (E ::= (E + Aexp) (int + E) (E * Aexp) (int * E) hole 
         (E <= Aexp) (int <= E)  (not E)     
         (E and Bexp) (bool and E)
         (E or  Bexp) (bool or  E)
         ) )
     

(define-metafunction Imp 
  arithmetic-op : Aexp -> int 
  [(arithmetic-op (int_1 + int_2)) ,(+ (term int_1) (term int_2))]
  [(arithmetic-op (int_1 * int_2)) ,(* (term int_1) (term int_2))])

(define-metafunction Imp 
  boolean-op : Bexp -> bool 
  [(boolean-op (int_1 <= int_2)) ,(<= (term int_1) (term int_2))])

(define-metafunction Imp
  var-lookup : Loc var -> int
  [(var-lookup ((var_1 int_1) ... (var int) (var_2 int_2) ...) var) int]
  [(var-lookup ((var_1 int_1) ...) var) ,(raise "variable not found")])

(define-metafunction Imp
    var-assign : Loc var int -> Loc 
  [(var-assign ((var_1 int_1) ... (var int_3) (var_2 int_2) ...) var int)
   ((var_1 int_1) ... (var int) (var_2 int_2) ...)]
  [(var-assign ((var_1 int_1) ...) var int)
   ((var_1 int_1) ... (var int))])

(define imp-red 
  (reduction-relation Imp
  #:domain Program 
    [ --> (Loc ((in-hole P (var = int)) Com ...))
          ((var-assign Loc var int) (Com ...))
          "var-assign"]

    [ --> (Loc (skip Com ...))
          (Loc (Com ...))
          "skip"]

    [--> (Loc ((in-hole P var) Com ...))
         (Loc ((in-hole P (var-lookup Loc var)) Com ...))
         "var-lookup"]

    [--> (Loc ((in-hole P (if #t (Com_1 ...) else (Com_2 ...))) Com ...))
         (Loc (Com_1 ... Com ...))
         "if-true"]

    [--> (Loc ((in-hole P (if #f (Com_1 ...) else (Com_2 ...))) Com ...))
         (Loc (Com_2 ... Com ...))
         "if-false"]

    [--> (Loc ((in-hole P (int_1 + int_2)) Com ...))
         (Loc ((in-hole P ,(+ (term int_1) (term int_2))) Com ...))
         "integer-add"]

    [--> (Loc ((in-hole P (bool_1 and bool_2)) Com ...))
         (Loc ((in-hole P ,(and (term bool_1) (term bool_2))) Com ...))
         "boolean-and"]

    [--> (Loc ((in-hole P (bool_1 or bool_2)) Com ...))
         (Loc ((in-hole P ,(or (term bool_1) (term bool_2))) Com ...))
         "boolean-or"]

    [--> (Loc ((in-hole P (not bool_1)) Com ...))
         (Loc ((in-hole P ,(not (term bool_1))) Com ...))
         "boolean-not"]

    [--> (Loc ((in-hole P (int_1 <= int_2)) Com ...))
         (Loc ((in-hole P ,(<= (term int_1) (term int_2))) Com ...))
         "less-equal"]))



(redex-match Imp Com (term (if (1 <= 34) ((x = 1)) else ())))


(traces imp-red (term (() 
  ( 
    (if (not ((5 <= 4) or #f))
      (skip)
      else 
      ((x = 12)))
    (z = 3) ))))
;(traces imp-red (term ((2 + 1) <= (3 * -5))))

  





  
