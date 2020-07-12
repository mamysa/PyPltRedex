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
* `define-metafunction` and metafunction application. Metafunction applications are detected statically when processing terms. 

## TODOs
From most to least important.
* Fix bug in `EllipsisMatchModeRewriter`. [See here](https://github.com/mamysa/PyPltRedex/issues/1#issuecomment-656267262). Aside from general `PatSequence` structural checking logic being incorrect, I also suspect `NtClosure` computation is not sufficient.
* More reasonable copying in `in-hole` pattern. 
* Term level non-terminal / built-in pattern membership caching. For example, when asking if a given term is `e`, store `e` symbol in the set. Thus, next time we try to determine if the term is `e`, we just look it up in the set.
* RPython compatibility.
* More testing.
* Sample languages as examples (and evaluation).
* Compile `reduction-relation` in smarter way - instead of pattern matching rule-by-rule, find common subpatterns  and run for a set of rules with said subpattern matcher only once. Also want to merge multiple in-hole into one. `(in-hole V (+ n_1 n_2)` and `(in-hole V (- n_1 n_2))` --> `(in-hole V [(+ n_1 n_2) (- n_1 n_2)]) to traverse term only once while looking for redexes.
* Start outlining the written thesis.
* Start testing if generated code complies with RPython requirements.
* Make specification handling more Racket-like - i.e. instead of hardcoding certain form to expect a certain form as an argument (for example, `assert-term-lists-equal` expects its first argument to be `apply-reduction-relation`), we reason in terms of a return type of the form.
* Add `assert-term-throws` to test term plugging that is supposed to fail due to wrong ellipsis match counts.

## References
* Glynn Winskell The Formal Semantics of Programming Languages, Operational semantics and principles of induction chapters.
* The Revised Reporton theSyntactic Theories of Sequential Control and State, Matthias Felleisen, Robert Hieb https://www2.ccs.neu.edu/racket/pubs/tcs92-fh.pdf
* Term Rewriting with Traversal Functions MARK G.J.VANDENBRAND and PAUL KLINT and JURGEN J. VINJU (need to look into this one)
* http://www.meta-environment.org/doc/books/extraction-transformation/term-rewriting/term-rewriting.html#section.tr-substitution
* DAG Representation and Optimization of Rewriting, Ke Li https://pdfs.semanticscholar.org/68d5/945e1ac0f5a09397612c9ab774d41e41f0f4.pdf
