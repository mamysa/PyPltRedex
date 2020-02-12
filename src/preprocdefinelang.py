
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

class NtUnderscoreChecker(ast.AstIdentityTransformer):
    def __init__(self):
        super().__init__()
        self.ntsyms = set([])

    def run(self, node):
        assert isinstance(node, ast.AstNode)
        return self.transform(node), self.ntsyms

    def transformNt(self, node):
        assert isinstance(node, ast.Nt)
        if node.ntsym.find('_') != -1:
            raise Exception('define-language: cannot use _ in a non-terminal name {}'.format(node.ntsym))

        if node.ntsym in self.ntsyms:
            raise Exception('define-language: same non-terminal defined twice {}'.format(node.ntsym))

        self.ntsyms.add(node.ntsym)
        return node


class NtResolver(ast.AstIdentityTransformer):
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







