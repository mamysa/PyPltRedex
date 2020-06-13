PLT Redex specification to PyPy RPython compiler, featuring the worst software engineering practices (for now ...)

## Running 

First, install Ply - `pip3 install ply`. I also recommend using venv.

Then, from project's root directory:

```
python3 -m src your-plt-redex-spec.rkt
```

and then 

`python3 rpyout/out.py`


## Testing
`make test`


## What works 
* Built-in patterns: `number` (that act like integers for now), `variable-not-othewise-mentioned`, literal variables.
* `define-language` and `redex-match` forms. 
* Arbitrary patterns involving non-terminals and built-in patterns mentioned above.
* Constraint checking (e.g in pattern `(e_1 ... e_1 ...)` both `e_1` bindings are checked for equality).
* `match-equals?` form (not part of Redex) used for comparing results produced by `redex-match` against expected matches.
* Matching `hole` pattern.
* Matching `in-hole` pattern.
* Plugging terms into terms, including `(in-hole term term)` and python function calls (`','` and `',@'`). See `plugtest.rkt` for testcases.
* `define-reduction-relation` and `apply-reduction-relation` forms

## TODOs
From most to least important.
* Perform input validation:
	* Ellipsis depth checking and constraint checking on `in-hole pat1 pat2` - same bindable symbols in `pat1` and `pat2` must have same ellipsis depth.
	* Ensure `pat1` has exactly one `hole` in `in-hole pat1 pat2`.
	* Non-terminal cycles (?) in `define-language` form - `x ::= y y ::= x` should be invalid.
	* Ensure `pat1` in `(in-hole pat1 pat2)` has exactly one hole. I am not sure how to handle strange grammars like `((E ::= P) (P :: (E)))` which have circular dependencies. Perhaps turn this problem into graph traversal problem?
* Start outlining the written thesis.
* Start testing if generated code complies with RPython requirements.
* `define-metafunction` form.
* Make specification handling more Racket-like - i.e. instead of hardcoding certain form to expect a certain form as an argument (for example, `assert-term-lists-equal` expects its first argument to be `apply-reduction-relation`), we reason in terms of a return type of the form.
* Term level non-terminal / built-in pattern membership caching. For example, when asking if a given term is `e`, store `e` symbol in the set. Thus, next time we try to determine if the term is `e`, we just look it up in the set.
* Add `assert-term-throws` to test term plugging that is supposed to fail due to wrong ellipsis match counts.
* Optimize patterns to reduce number of non-deterministic repetition matches.
* `define-judgment-form` and `judgment-holds` forms.

## References
* Glynn Winskell The Formal Semantics of Programming Languages, Operational semantics and principles of induction chapters.
* The Revised Reporton theSyntactic Theories of Sequential Control and State, Matthias Felleisen, Robert Hieb https://www2.ccs.neu.edu/racket/pubs/tcs92-fh.pdf
* Term Rewriting with Traversal Functions MARK G.J.VANDENBRAND and PAUL KLINT and JURGEN J. VINJU (need to look into this one)
* http://www.meta-environment.org/doc/books/extraction-transformation/term-rewriting/term-rewriting.html#section.tr-substitution
* DAG Representation and Optimization of Rewriting, Ke Li https://pdfs.semanticscholar.org/68d5/945e1ac0f5a09397612c9ab774d41e41f0f4.pdf
