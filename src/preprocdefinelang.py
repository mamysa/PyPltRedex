import src.astdefs as ast

# Preprocessing define-language construct involves the following steps.
# (1) Ensure all non-terminals are defined exactly once and contain no underscores. 
#     This bit is done at parsing phase.
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


class NtResolver(ast.PatternTransformer):
    def __init__(self, ntsyms):
        self.ntsyms = ntsyms
        self.variables = set([])

    def transformUnresolvedSym(self, node):
        assert isinstance(node, ast.UnresolvedSym)
        if node.prefix in self.ntsyms:
            return ast.NtRef(node.prefix, node.sym)
        # not nt, check if there's underscore
        if node.prefix != node.sym:
            raise Exception('define-language: before underscore must be either a non-terminal or build-in pattern {}'.format(node.sym))

        self.variables.add(node.sym) # for variable-not-defined patterns.
        return ast.Lit(node.sym, ast.LitKind.Variable)


def resolve_ntref_in_definelanguage(node, ntsyms):
    assert isinstance(node, ast.DefineLanguage)
    resolver = NtResolver(ntsyms)
    for nt in node.nts:
        for i, pat in enumerate(nt.patterns):
            nt.patterns[i] = resolver.transform(pat)
    return node, resolver.variables 



class EllipsisDepthChecker(ast.PatternTransformer):
    def __init__(self):
        self.depth = 0
        self.vars = {}

    def transformRepeat(self, node):
        assert isinstance(node, ast.Repeat)
        self.depth += 1
        self.transform(node.pat)
        self.depth -= 1

    def transformNtRef(self, node):
        assert isinstance(node, ast.NtRef)
        if node.sym not in self.vars:
            self.vars[node.sym] = self.depth
            return node
        if self.vars[node.sym] != self.depth:
            raise Exception('found {} under {} ellipses in one place and {} in another'.format(node.sym, self.vars[node.sym], self.depth))
        return node

    def transformUnresolvedSym(self, node):
        assert False, 'UnresolvedSym not allowed'
