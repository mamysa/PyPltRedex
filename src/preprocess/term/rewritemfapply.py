import src.model.term as term

# If term sequence begins with literal variable and identifier is 
# in the set of known metafunctions, rewrite sequence as 
# MetafunctionApplication with sequence as an argument.
class Term_MetafunctionApplicationRewriter(term.TermTransformer):
    def __init__(self, termtemplate, metafunctions, symgen):
        self.termtemplate = termtemplate
        self.symgen = symgen
        self.metafunctions = metafunctions

    def run(self):
        return self.transform(self.termtemplate)

    def transformTermSequence(self, node):
        assert isinstance(node, term.TermSequence)
        nseq = []
        for termtemplate in node.seq:
            ntermtemplate = self.transform(termtemplate)
            nseq.append(ntermtemplate)
        nnode = term.TermSequence(nseq).copyattributesfrom(node)
        if len(nnode.seq) > 0 and isinstance(nnode.seq[0], term.TermLiteral):
            lit = nnode.seq[0]
            if lit.kind == term.TermLiteralKind.Variable and lit.value in self.metafunctions:
                return term.MetafunctionApplication(lit.value, nnode).copyattributesfrom(node)
        return nnode
