import src.model.tlform as tlform 
import src.model.pattern as pattern
from src.util import SymGen

#DefineLanguageIdRewriter
class DefineLanguageIdRewriter(pattern.PatternTransformer):
    def __init__(self, definelanguage):
        assert isinstance(definelanguage, tlform.DefineLanguage)
        super().__init__()
        self.definelanguage = definelanguage
        self.symgen = SymGen()

    def run(self):
        ntdefs = []
        for nt, ntdef in self.definelanguage.nts.items():
            npats = []
            for pat in ntdef.patterns:
                npat = self.transform(pat)
                npat.copymetadatafrom(pat)
                npats.append(npat)
            ntdefs.append(tlform.DefineLanguage.NtDefinition(ntdef.nt, npats))
        return tlform.DefineLanguage(self.definelanguage.name, ntdefs)

    def transformBuiltInPat(self, node):
        assert isinstance(node, pattern.BuiltInPat)
        nsym = self.symgen.get(node.prefix)
        return pattern.BuiltInPat(node.kind, node.prefix, nsym).copymetadatafrom(node)

    def transformNt(self, node):
        assert isinstance(node, pattern.Nt)
        nsym = self.symgen.get(node.prefix)
        return pattern.Nt(node.prefix, nsym).copymetadatafrom(node)
