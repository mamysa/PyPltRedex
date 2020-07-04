import src.model.tlform as tlform
import src.model.pattern as pattern

class NtResolver(pattern.PatternTransformer):
    def __init__(self, ntsyms):
        self.ntsyms = ntsyms
        self.variables = set([])

    def transformUnresolvedSym(self, node):
        assert isinstance(node, pattern.UnresolvedSym)
        if node.prefix in self.ntsyms:
            return pattern.Nt(node.prefix, node.sym).copymetadatafrom(node)
        # not nt, check if there's underscore
        if node.prefix != node.sym:
            raise Exception('define-language: before underscore must be either a non-terminal or build-in pattern {}'.format(node.sym))

        self.variables.add(node.sym) # for variable-not-defined patterns.
        return pattern.Lit(node.sym, pattern.LitKind.Variable).copymetadatafrom(node)


class Pattern_NtRewriter(NtResolver):
    def __init__(self, pattern, ntsyms):
        super().__init__(ntsyms)
        self.pattern = pattern

    def run(self):
        return self.transform(self.pattern)

class DefineLanguage_NtRewriter(NtResolver):
    def __init__(self, definelanguage, ntsyms):
        super().__init__(ntsyms)
        self.definelanguage = definelanguage 

    def run(self):
        ntdefs = []
        for nt, ntdef in self.definelanguage.nts.items():
            npats = []
            for pat in ntdef.patterns:
                npat = self.transform(pat)
                npat.copymetadatafrom(pat)
                npats.append(npat)
            ntdefs.append(tlform.DefineLanguage.NtDefinition(ntdef.nt, npats))
        return tlform.DefineLanguage(self.definelanguage.name, ntdefs), self.variables
