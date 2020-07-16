import src.model.tlform as tlform
import src.model.pattern as pattern

def extract_prefix(token):
        # extract prefix i.e. given symbol n_1 retrieve n.
        # in case of no underscore return token itself
        # tokens starting with underscore are invalid...
        # So far we are not supporting patterns such as _!_ so this method may work.
        idx = token.find('_')
        if idx == 0:
            raise Exception('define-language: before underscore must be either a non-terminal or build-in pattern {}'.format(tokenvalue))
        if idx == -1:
            return token
        return token[:idx]

class NtResolver(pattern.PatternTransformer):
    def __init__(self, ntsyms):
        self.ntsyms = ntsyms
        self.variables = set([])

    def transformUnresolvedSym(self, node):
        assert isinstance(node, pattern.UnresolvedSym)
        prefix = extract_prefix(node.sym)
        if prefix in self.ntsyms:
            return pattern.Nt(prefix, node.sym).copymetadatafrom(node)

        # do not allow underscores for holes.
        if prefix == 'hole' and prefix != node.sym:
            raise Exception('before underscore must be either a non-terminal or build-in pattern {}'.format(prefix))

        try:
            case = pattern.BuiltInPatKind(prefix).name
            return pattern.BuiltInPat(pattern.BuiltInPatKind[case], prefix, node.sym).copymetadatafrom(node)
        except ValueError:
            pass

        # not nt or builtin-pat, check if there's underscore
        if prefix != node.sym:
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
