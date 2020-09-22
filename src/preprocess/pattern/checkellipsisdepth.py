import src.model.pattern as pattern

class Pattern_EllipsisDepthChecker(pattern.PatternTransformer):
    """
    Traverses a pattern, locates symbols to be bound while matching,
    and adds [sym, depth] annotation to the pattern. It describes the state of match object 
    by the end of matching process and is required for term term generation functions.
    Perform ellipsis depth checking along the way raising an exception when same symbols have
    different ellipsis depths.
    """
    def __init__(self, pat):
        self.depth = 0
        self.pat = pat 

    def run(self):
        pat, variables = self.transform(self.pat)
        return pat.addattribute(pattern.PatternAttribute.PatternVariableEllipsisDepths, variables)

    def _merge_variable_maps(self, m1, m2):
        m1k = set(list(m1.keys())) 
        m2k = set(list(m2.keys()))
        commonsyms = m1k.intersection(m2k)
        for sym in commonsyms:
            if m1[sym] != m2[sym]:
                raise Exception('found {} under {} ellipses in one place and {} in another'.format(sym, m1[sym], m2[sym]))
        return {**m1, **m2}

    def transformPatSequence(self, node):
        assert isinstance(node, pattern.PatSequence)
        variables = {}
        seq = []
        for pat in node.seq:
            npat, npatvariables = self.transform(pat)
            seq.append(npat)
            variables = self._merge_variable_maps(variables, npatvariables)
        return pattern.PatSequence(seq).copyattributesfrom(node), variables

    def transformRepeat(self, node):
        assert isinstance(node, pattern.Repeat)
        self.depth += 1
        pat, variables = self.transform(node.pat)
        self.depth -= 1
        return pattern.Repeat(pat).copyattributesfrom(node), variables 

    def transformUnresolvedSym(self, node):
        assert False, 'UnresolvedSym not allowed'

    def transformNt(self, node):
        assert isinstance(node, pattern.Nt)
        return node, {node.sym: self.depth}

    def transformInHole(self, node):
        assert isinstance(node, pattern.InHole)
        pat1, pat1variables = self.transform(node.pat1)
        pat2, pat2variables = self.transform(node.pat2)
        variables = self._merge_variable_maps(pat1variables, pat2variables)
        return pattern.InHole(pat1, pat2).copyattributesfrom(node), variables

    def transformBuiltInPat(self, node):
        assert isinstance(node, pattern.BuiltInPat)
        # FIXME introduce separate pat node and for holes?
        if node.kind == pattern.BuiltInPatKind.Hole:
            return node, {}
        return node, {node.sym: self.depth}

    def transformCheckConstraint(self, node):
        assert False, 'unreachable'

    def transformLit(self, node):
        return node, {}
