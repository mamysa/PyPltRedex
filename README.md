PLT Redex specification to PyPy RPython compiler, featuring the worst software engineering practices (for now ...)

## Running 

First, install Ply - `pip3 install ply`. I also recommend using venv.

Then, from project's root directory:

```
python3 -m src your-plt-redex-spec.rkt
```

and then 

`python3 rpyout/lang.py`


## Testing

`patmatchtest.rkt` and `inholetest.rkt` provide an overview of what works; it is run the same way mentioned above. Patterns are compared against output produced by Racket Redex.

## What works 
* Built-in patterns: `number` (that act like integers for now), `variable-not-othewise-mentioned`, literal variables.
* `define-language` and `redex-match` forms. 
* Arbitrary patterns involving non-terminals and built-in patterns mentioned above.
* Constraint checking (e.g in pattern `(e_1 ... e_1 ...)` both `e_1` bindings are checked for equality).
* `match-equals?` form (not part of Redex) used for comparing results produced by `redex-match` against expected matches.
* Matching `hole` pattern.
* Matching `in-hole` pattern.
* Plugging terms into terms, including `(in-hole term term)` and python function calls (',' and ',@'). See `plugtest.rkt` for testcases.

## TODOs
From most to least important.
* Refactor pattern code generation - atm `redex-match` forms create `Match` objects by themselves to be fed into pattern matching function. Instead of doing that, create top-level function for the pattern that creates `Match` objects and calls pattern matching function. I.e. something like this:

```
def match_pat(term):
	match = Match(...)
	return match_pat_impl(term, match, 0, 1)
```
Need to figure out how to handle this inside `define-language` patterns too.
* Code cleanup - decide in which order to create pattern matching functions - maybe store them in ordered dict?
* Add `assert-term-throws` to test term plugging that is supposed to fail due to wrong ellipsis match counts.
* Codegen cleanup: Generate class with static methods for `define-language` form. Generate a stand-alone procedure for `redex-let` and such instead of having its functionality in global namespace.
* `reduction-relation` and `apply-reduction-relation`
* Perform input validation:
	* Ellipsis depth checking and constraint checking on `in-hole pat1 pat2` - same bindable symbols in `pat1` and `pat2` must have same ellipsis depth.
	* Ensure `pat1` has exactly one `hole` in `in-hole pat1 pat2`.
	* Non-terminal cycles (?) in `define-language` form - `x ::= y y ::= x` should be invalid.
* `define-metafunction` form.
	* Figure out how to perform plugging bindings back into term "templates". 
* Optimize patterns to reduce number of non-deterministic repetition matches.
* Term level non-terminal / built-in pattern membership caching. For example, when asking if a given term is `e`, store `e` symbol in the set. Thus, next time we try to determine if the term is `e`, we just look it up in the set.
* Replace handwritten parser with Ply? See other considerations below.
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
* DAG Representation and Optimization of Rewriting, Ke Li https://pdfs.semanticscholar.org/68d5/945e1ac0f5a09397612c9ab774d41e41f0f4.pdf
