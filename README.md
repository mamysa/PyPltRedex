PLT Redex specification to PyPy RPython compiler, featuring the worst software engineering practices (for now ...)

## Running 

From project's root directory:

```
python3 -m src your-plt-redex-spec.rkt
```

and then 

`python3 rpyout/lang.py`

## What works 
* Built-in patterns: `number` (that act like integers for now), `variable-not-othewise-mentioned`, literal variables.
* `define-language` and `redex-match` forms. 
* Arbitrary patterns involving non-terminals and built-in patterns mentioned above.
* Constraint checking (e.g in pattern `(e_1 ... e_1 ...)` both `e_1` bindings are checked for equality).

## TODOs
From most to least important.

* `in-hole` pattern matching.
* Code cleanup  - improve codegen, decide on AST to represent PltRedex syntax (a bit all over the place for now), either improve `PatternTransformer` or do something completely different.
* `define-metafunction` form.
* `reduction-relation` form.
* `define-judgment-form` and `judgment-holds` forms.

## Other Considerations
* Force user to replace all unquotes with arbitrary Racket code with Python? E.g. in metafunction

```
; snip
[(do-arith * (n ...)) ,(apply * (term (n ...)))]
; snip
```

spec would contain

```
[(do-arith * (n ...)) (python3 multiply n ... )]
```

and user-provided python file would contain something like

```
def multiply(sequence_of_n):
	if len(sequence_of_n) == 0:
	return 0
	n = sequence_of_n[0]
	for i in sequence_of_n[1:]:
		n *= i
	return n
```
