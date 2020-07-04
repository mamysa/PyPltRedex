import src.model.tlform as tlform
import src.model.pattern as pattern


class AssignableSymbolExtractor(pattern.PatternTransformer):
    def transformPatSequence(self, node):
        assert isinstance(node, pattern.PatSequence)
        variables = set([]) 
        for pat in node.seq:
            _, patvariables = self.transform(pat)
            variables = variables.union(patvariables)
        return node, variables

    def transformRepeat(self, node):
        assert isinstance(node, pattern.Repeat)
        _, variables = self.transform(node.pat)
        return node.addmetadata(pattern.PatAssignableSymbols(variables)), variables

    def transformCheckConstraint(self, node):
        return node, set([])

    def transformNt(self, node):
        assert isinstance(node, pattern.Nt)
        return node, set([node.sym])

    def transformInHole(self, node):
        assert isinstance(node, pattern.InHole)
        _, pat1variables = self.transform(node.pat1)
        _, pat2variables = self.transform(node.pat2)
        node.pat1.addmetadata(pattern.PatAssignableSymbols(pat1variables))
        node.pat2.addmetadata(pattern.PatAssignableSymbols(pat2variables))
        variables = pat1variables.union(pat2variables)
        return node, variables

    def transformBuiltInPat(self, node):
        assert isinstance(node, pattern.BuiltInPat)
        if node.kind == pattern.BuiltInPatKind.Hole:
            return node, set([]) 
        return node, set([node.sym])

    def transformLit(self, node):
        return node, set([]) 


class Pattern_AssignableSymbolExtractor(AssignableSymbolExtractor):
    def __init__(self, pat):
        assert isinstance(pat, pattern.Pat)
        self.pat = pat

    def run(self):
        pat, variables = self.transform(self.pat)
        return pat.addmetadata(pattern.PatAssignableSymbols(variables))
        return pat 

class DefineLanguage_AssignableSymbolExtractor(AssignableSymbolExtractor):
    def __init__(self, definelanguage):
        self.definelanguage = definelanguage 

    def run(self):
        ntdefs = []
        for nt, ntdef in self.definelanguage.nts.items():
            npats = []
            for pat in ntdef.patterns:
                npat, variables = self.transform(pat)
                npat.copymetadatafrom(pat).addmetadata(pattern.PatAssignableSymbols(variables))
                npats.append(npat)
            ntdefs.append(tlform.DefineLanguage.NtDefinition(ntdef.nt, npats))
        return tlform.DefineLanguage(self.definelanguage.name, ntdefs)
