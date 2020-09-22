import src.model.pattern as pattern
from src.util import SymGen

# Patterns like ((n_1 ... n_1 ...) (n_1 ... n_1 ...)) require all n_1 ... values to be equal.
# This is done by creating temporary bindings for each n_1 encountered. More specifically,
# (1) ((n_1 ... n_1#0 ... CheckEquality(n_1 n_1#0) (n_1 ... n_1 ...))
# (2) ((n_1 ... n_1#0 ... CheckEquality(n_1 n_1#0) (n_1 ... n_1#1 ... CheckEquality(n_1 n_1#1)))
# (3) ((n_1 ... n_1#0 ... CheckEquality(n_1 n_1#0) (n_1#2 ... n_1#1 ... CheckEquality(n_1 n_1#1)) CheckEquality(n_1, n_1#2))
# This class (1) renames all occurences of bindable symbol (except the first one)
# (2) Inserts contraint checks when at least two syms have been seen in the sequence.
class Pattern_ConstraintCheckInserter(pattern.PatternTransformer):
    def __init__(self, pattern):
        self.pattern = pattern
        self.symgen = SymGen()
        self.symstoremove = []

    def run(self):
        pat, _ = self.transform(self.pattern)
        pat.addattribute(pattern.PatternAttribute.PatternVariablesToRemove, self.symstoremove)
        return pat

    def _merge_variable_maps(self, m1, m2):
        m1k = set(list(m1.keys()))
        m2k = set(list(m2.keys()))
        intersection = m1k.intersection(m2k)
        nmap, syms2check = {}, []
        for k in intersection:
            syms2check.append((m1[k], m2[k]))
            nmap[k] = m2[k]
        for k in m1k:
            if k not in intersection:
                nmap[k] = m1[k]
        for k in m2k:
                nmap[k] = m2[k]
        return nmap, syms2check

    def transformInHole(self, node):
        assert isinstance(node, pattern.InHole)
        npat1, syms1 = self.transform(node.pat1)
        npat2, syms2 = self.transform(node.pat2)
        constraintchecks = []
        syms, syms2check = self._merge_variable_maps(syms1, syms2)
        for sym1, sym2 in syms2check:
            constraintchecks.append(pattern.CheckConstraint(sym1, sym2))
        return pattern.InHole(npat1, npat2, constraintchecks).copyattributesfrom(node), syms
    
    def transformPatSequence(self, node):
        assert isinstance(node, pattern.PatSequence)
        if len(node.seq) == 0:
            return node, {}
        nseq = []
        npat, syms = self.transform(node.seq[0])
        nseq.append(npat)
        for pat in node.seq[1:]:
            npat, nsyms = self.transform(pat)
            nseq.append(npat)
            syms, syms2check = self._merge_variable_maps(syms, nsyms)
            for sym1, sym2 in syms2check:
                nseq.append(pattern.CheckConstraint(sym1, sym2))
        return pattern.PatSequence(nseq).copyattributesfrom(node), syms

    def transformRepeat(self, node):
        assert isinstance(node, pattern.Repeat)
        pat, syms = self.transform(node.pat)
        return pattern.Repeat(pat, node.matchmode).copyattributesfrom(node), syms

    def transformNt(self, node):
        assert isinstance(node, pattern.Nt)
        # First time we see desired symbol we do not rename it - we will keep it in the end.
        nsym = self.symgen.get('{}#'.format(node.sym))
        if nsym == '{}#0'.format(node.sym):
            nsym = node.sym
        else:
            self.symstoremove.append(nsym)
        return pattern.Nt(node.prefix, nsym).copyattributesfrom(node), {node.sym : nsym}

    def transformBuiltInPat(self, node):
        assert isinstance(node, pattern.BuiltInPat)
        # First time we see desired symbol we do not rename it - we will keep it in the end.
        # Also we never bind holes.
        if node.kind != pattern.BuiltInPatKind.Hole:
            nsym = self.symgen.get('{}#'.format(node.sym))
            if nsym == '{}#0'.format(node.sym):
                nsym = node.sym
            else:
                self.symstoremove.append(nsym)
            return pattern.BuiltInPat(node.kind, node.prefix, nsym).copyattributesfrom(node), {node.sym : nsym}
        return node, {}

    def transformLit(self, pat):
        return pat, {} 

    def transformCheckConstraint(self, node):
        return node, {} 
