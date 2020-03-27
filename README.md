PLT Redex specification to PyPy RPython compiler, featuring the worst software engineering practices (for now ...)

## Running 

From project's root directory:

```
python3 -m src your-plt-redex-spec.rkt
```

and then 

`python3 rpyout/lang.py`


## Testing

`patmatchtest.rkt` provides an overview of what works; it is run the same way mentioned above.

## What works 
* Built-in patterns: `number` (that act like integers for now), `variable-not-othewise-mentioned`, literal variables.
* `define-language` and `redex-match` forms. 
* Arbitrary patterns involving non-terminals and built-in patterns mentioned above.
* Constraint checking (e.g in pattern `(e_1 ... e_1 ...)` both `e_1` bindings are checked for equality).
* `match-equals?` form (not part of Redex) used for comparing results produced by `redex-match` against expected matches.
* Matching `hole` pattern.

## TODOs
From most to least important.
* `in-hole` pattern matching. Algorithm for matching `(in-hole pat1 pat2)` I have so far is:
	1. Traverse the term and filter out subterms matching `pat2`.
	2. For each such matched subterm 
		1. Replace subterm with `hole`.
		2. Run matching function for `pat1`.  If match is successful, copy terms recursively starting from the hole all the way to the root, create bindings in the `Match` object. 
		3. Replace hole with matched subterm (i.e. restore term to its original state - we only copy once `pat1` has been matched successfully.
	This reduces copying but memory fragmentation could be an issue?
	This requires to rethink AST representation - need to be able to access subterm's parent and be able to replace it with `hole`. Use some sort of `TermLink` object storing references between terms?
* Code cleanup  - improve codegen, decide on AST to represent PltRedex syntax (a bit all over the place for now), either improve `PatternTransformer` or do something completely different.
* Term level non-terminal / built-in pattern membership caching. For example, when asking if a given term is `e`, store `e` symbol in the set. Thus, next time we try to determine if the term is `e`, we just look it up in the set.
* Replace handwritten parser with Ply? 
* `define-metafunction` form.
* `reduction-relation` form.
* `define-judgment-form` and `judgment-holds` forms.

## Other Considerations
* Seeing that current implementation is quite different from PLT Redex (e.g. `match-equal?` form - looking at PLT Redex test cases creation of matches is not as straight-forward https://github.com/racket/redex/blob/master/redex-test/redex/tests/matcher-test.rkt), may as well introduce more Python-like syntax to specifications while ensuring that behaviour is identical? 
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


## References
* Glynn Winskell The Formal Semantics of Programming Languages, Operational semantics and principles of induction chapters.
* The Revised Reporton theSyntactic Theories of Sequential Control and State, Matthias Felleisen, Robert Hieb https://www2.ccs.neu.edu/racket/pubs/tcs92-fh.pdf
* Term Rewriting with Traversal Functions MARK G.J.VANDENBRAND and PAUL KLINT and JURGEN J. VINJU (need to look into this one)
* http://www.meta-environment.org/doc/books/extraction-transformation/term-rewriting/term-rewriting.html#section.tr-substitution

