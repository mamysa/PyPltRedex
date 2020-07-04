import src.model.pattern as pattern
from src.preprocess.pattern.solveholereachability import NumberOfHoles
from src.util import CompilationError

# FIXME according to the algorithm patterns like (P ::= (E)) (E ::= P (E (in-hole P n) hole))) are valid
# because P matches exactly one hole. Maybe should set max value of in-hole to many? Validating 
# such patterns in Redex raises exception.
class PatternNumHolesChecker(pattern.PatternTransformer):
    def __init__(self, definelanguage, pattern):
        self.definelanguage = definelanguage
        self.pattern = pattern

    def run(self):
        return self.transform(self.pattern)

    def transformPatSequence(self, node):
        assert isinstance(node, pattern.PatSequence)
        psmin, psmax = NumberOfHoles.Zero, NumberOfHoles.Zero
        for pat in node.seq:
            pmin, pmax = self.transform(pat)
            psmin = NumberOfHoles.add(psmin, pmin)
            psmax = NumberOfHoles.add(psmax, pmax)
        return psmin, psmax

    def transformRepeat(self, node):
        assert isinstance(node, pattern.Repeat)
        pmin, pmax = self.transform(node.pat)
        pmin = NumberOfHoles.Zero if pmin in [NumberOfHoles.One, NumberOfHoles.Many] else pmin
        pmax = NumberOfHoles.Many if pmax in [NumberOfHoles.One, NumberOfHoles.Many] else pmax 
        return pmin, pmax

    def transformInHole(self, node):
        assert isinstance(node, pattern.InHole)
        return NumberOfHoles.Zero, NumberOfHoles.Zero

    def transformBuiltInPat(self, node):
        assert isinstance(node, pattern.BuiltInPat)
        if node.kind == pattern.BuiltInPatKind.Hole:
            return NumberOfHoles.One, NumberOfHoles.One
        return NumberOfHoles.Zero, NumberOfHoles.Zero

    def transformNt(self, node):
        assert isinstance(node, pattern.Nt)
        ntdef = self.definelanguage.nts[node.prefix]
        n = ntdef.nt.getmetadata(pattern.PatNumHoles)
        return n.numholesmin, n.numholesmax

    def transformLit(self, node):
        return NumberOfHoles.Zero, NumberOfHoles.Zero

class Pattern_InHoleChecker(pattern.PatternTransformer):
    def __init__(self, definelanguage, pattern):
        self.definelanguage = definelanguage
        self.pattern = pattern

    def run(self):
        return self.transform(self.pattern)

    def transformInHole(self, node):
        assert isinstance(node, pattern.InHole)
        pat1 = self.transform(node.pat1)
        minholes, maxholes = PatternNumHolesChecker(self.definelanguage, node.pat1).run()
        if not (minholes == NumberOfHoles.One and maxholes == NumberOfHoles.One):
            raise CompilationError('First pattern {} does not match exactly one hole'.format(repr(node)))
        return node
