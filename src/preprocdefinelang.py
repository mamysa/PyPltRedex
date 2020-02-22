
import astdefs as ast



# Preprocessing define-language construct involves the following steps.
# (1) Ensure all non-terminals are defined exactly once and contain no underscores.
# (2) Resolve UnresolvedPat instances to either NtRef or Literal value.
# (3) In each righthand-side pattern, remove underscores from builtin-patterns / NtRefs.
#     Current redex behaviour is that all non-terminal patterns in define-language are 
#     constrained to be different. (I recall seeing it in documentation but I can't find it 
#     anymore... perhaps behaviour has been changed?). Underscores will be re-added later.
# (4) "Optimize" righthand-side patterns i.e. remove adjacent Repeat elements (recursively) 
#     when appropriate. For example, patterns like e ::= (n n... n...) can transformed into 
#     e ::= (n n...) when matching e. Thus, instead computing all possible permutations of lists 
#     containing n, greedy matching can be done.
# (5) Introduce underscores back into right-handside patterns; id after each underscore must be unique.

def check_underscores(node):
    assert isinstance(node, ast.DefineLanguage)
    ntsyms = set([])
    for nt in node.nts:
        if nt.ntsym.find('_') != -1:
            raise Exception('define-language: cannot use _ in a non-terminal name {}'.format(nt.ntsym))
        if nt.ntsym in ntsyms:
            raise Exception('define-language: same non-terminal defined twice {}'.format(nt.ntsym))
        ntsyms.add(nt.ntsym)
    return ntsyms

def resolve_ntref(node, ntsyms):
    assert isinstance(node, ast.DefineLanguage)
    variables = set([])

    class NtResolver(ast.PatternTransformer):
        def transformUnresolvedSym(self, node):
            assert isinstance(node, ast.UnresolvedSym)
            if node.prefix in ntsyms:
                return ast.NtRef(node.prefix, node.sym)
            # not nt, check if there's underscore
            if node.prefix != node.sym:
                raise Exception('define-language: before underscore must be either a non-terminal or build-in pattern {}'.format(node.sym))

            variables.add(node.sym) # for variable-not-defined patterns.
            return ast.Lit(node.sym, ast.LitKind.Variable)

    resolver = NtResolver()
    for nt in node.nts:
        for i, pat in enumerate(nt.patterns):
            nt.patterns[i] = resolver.transform(pat)
    return node, variables
