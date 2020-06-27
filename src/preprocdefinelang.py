import src.tlform as tlform
import src.pat as pattern
import src.genterm as genterm
from src.util import SymGen, CompilationError
import sys
from src.context import CompilationContext
import enum

#FIXME Ellipsis depth checker should not annotate terms - need to annotate terms 
# AFTER performing contraint checks.

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
#     e ::= (n n...) when matching e.  FIXME this does not work as expected.
# (5) Introduce underscores back into right-handside bindable patterns(i.e. nts and builtin-pats); 
#     id after each underscore must be unique.

# TODO Need to check for non-terminal cycles in define-language patterns 
# such as (y ::= x) (x ::= y) or even (x ::= x)

# We have two kinds of functions
# (1) So called "IsA" functions. ...
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

class UnderscoreRemover(pattern.PatternTransformer):
    """
    Transformer that removes underscores from all non-terminals / built-in patterns in the pattern.
    (since underscores in define-language patterns don't matter)
    This needs to be done AFTER resolving non-terminals and detecting literals containing underscores.
    """
    def transformBuiltInPat(self, node):
        node.sym = node.prefix
        return node

    def transformNt(self, node):
        node.sym = node.prefix
        return node

class EllipsisDepthChecker(pattern.PatternTransformer):
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
        return pat.addmetadata(pattern.PatAssignableSymbolDepths(variables))

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
        return pattern.PatSequence(seq).copymetadatafrom(node), variables

    def transformRepeat(self, node):
        assert isinstance(node, pattern.Repeat)
        self.depth += 1
        pat, variables = self.transform(node.pat)
        self.depth -= 1
        return pattern.Repeat(pat).copymetadatafrom(node), variables 

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
        return pattern.InHole(pat1, pat2).copymetadatafrom(node), variables

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

class UnderscoreIdUniquify(pattern.PatternTransformer):
    def __init__(self):
        self.id = 0

    def transformBuiltInPat(self, node):
        node.sym = '{}_{}'.format(node.prefix, self.id)
        self.id += 1
        return node

    def transformNt(self, node):
        node.sym = '{}_{}'.format(node.prefix, self.id)
        self.id += 1
        return node

# Patterns like ((n_1 ... n_1 ...) (n_1 ... n_1 ...)) require all n_1 ... values to be equal.
# This is done by creating temporary bindings for each n_1 encountered. More specifically,
# (1) ((n_1 ... n_1#2 ... CheckEquality(n_1 n_1#0) (n_1 ... n_1 ...))
# (2) ((n_1 ... n_1#0 ... CheckEquality(n_1 n_1#0) (n_1 ... n_1#1 ... CheckEquality(n_1 n_1#1)))
# (3) ((n_1 ... n_1#0 ... CheckEquality(n_1 n_1#0) (n_1#2 ... n_1#1 ... CheckEquality(n_1 n_1#1)) CheckEquality(n_1, n_1#2))
# This class (1) renames all occurences of bindable symbol (except the first one)
# (2) Inserts contraint checks when at least two syms have been seen in the sequence.
class ConstraintCheckInserter(pattern.PatternTransformer):
    def __init__(self, pattern, sym):
        self.sym = sym
        self.pattern = pattern
        self.symgen = SymGen()

    def run(self):
        pat, _ = self.transform(self.pattern)
        return pat

    def transformPatSequence(self, seq):
        assert isinstance(seq, pattern.PatSequence) 
        nseq = [] 
        syms = []
        for pat in seq:
            node, sym = self.transform(pat)
            nseq.append(node)
            if sym != None: 
                syms.append(sym)

            if len(syms) == 2:
                nseq.append( pattern.CheckConstraint(syms[0], syms[1]) )
                syms.pop()

        assert len(syms) < 2
        nseq = pattern.PatSequence(nseq).copymetadatafrom(seq)
        if len(syms) == 0:
            return nseq, None
        return nseq, syms[0] 

    def transformRepeat(self, repeat):
        assert isinstance(repeat, pattern.Repeat)
        pat, sym = self.transform(repeat.pat)
        nrepeat = pattern.Repeat(pat, repeat.matchmode).copymetadatafrom(repeat)
        return nrepeat, sym

    def transformInHole(self, inhole):
        assert isinstance(inhole, pattern.InHole)
        pat1, _ = self.transform(inhole.pat1)
        pat2, _ = self.transform(inhole.pat2)
        return pattern.InHole(pat1, pat2).copymetadatafrom(inhole), None

    def transformBuiltInPat(self, pat):
        if pat.sym == self.sym:
            nsym = self.symgen.get('{}#'.format(self.sym))
            # First time we see desired symbol we do not rename it - we will keep it in the end.
            if nsym != '{}#0'.format(self.sym):
                pat.sym = nsym
                return pat, nsym
            return pat, pat.sym
        return pat, None

    def transformNt(self, pat):
        assert isinstance(pat, pattern.Nt)
        if pat.sym == self.sym:
            nsym = self.symgen.get('{}#'.format(self.sym))
            # First time we see desired symbol we do not rename it - we will keep it in the end.
            if nsym != '{}#0'.format(self.sym):
                pat.sym = nsym
                return pat, nsym
            return pat, pat.sym
        return pat, None

    def transformLit(self, pat):
        return pat, None

    def transformCheckConstraint(self, node):
        return node, None

# pattern is not modified during this pass.
# TODO seems to be very similar to EllipsisDepthChecker, merge them together?
class AssignableSymbolExtractor(pattern.PatternTransformer):
    def __init__(self, pat):
        self.pat = pat 

    def run(self):
        pat, variables = self.transform(self.pat)
        return pat.addmetadata(pattern.PatAssignableSymbols(variables))
        return pat 

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

# --------------------------------------------------------------------
class NumberOfHoles(enum.IntEnum):
    Zero = 0
    One  = 1
    Many = 2

    @staticmethod
    def add(n1, n2):
        assert isinstance(n1, NumberOfHoles)
        assert isinstance(n2, NumberOfHoles)
        num = min(n1.value + n2.value, NumberOfHoles.Many.value)
        return NumberOfHoles(num)

    @staticmethod
    def min(n1, n2):
        return NumberOfHoles(min(n1.value, n2.value))

    @staticmethod
    def max(n1, n2):
        return NumberOfHoles(max(n1.value, n2.value))

class NtGraphNode:
    Sequence = 0
    Repeat = 1
    LeafHole = 2
    LeafNotHole = 3

    def __init__(self, kind):
        self.kind = kind
        self.numholes = (0, 0)
        self.successors = []

    def addsuccessor(self, node):
        assert self.kind in [NtGraphNode.Sequence, NtGraphNode.Repeat]
        self.successors.append(node) 

    def __repr__(self):
        return '({}, {})'.format(self.kind, self.successors)

    def update(self, pmin, pmax):
        v = (pmin, pmax)
        if self.numholes != v:
            self.numholes = v
            return True
        return False

def constructgraph(definelanguage):
    assert isinstance(definelanguage, tlform.DefineLanguage)
    graph = {}
    equivalentnts = {}
    # first construct graph nodes.
    for nt, ntdef in definelanguage.nts.items():
        graph[nt] = {} 
        equivalentnts[nt] = []
        for pat in ntdef.patterns:
            if isinstance(pat, pattern.Nt):
                equivalentnts[nt].append(pat.prefix)
            if isinstance(pat, pattern.PatSequence):
                n = NtGraphNode(NtGraphNode.Sequence)
                graph[nt][repr(pat)] = n
            if isinstance(pat, pattern.BuiltInPat):
                if pat.kind == pattern.BuiltInPatKind.Hole:
                    n = NtGraphNode(NtGraphNode.LeafHole)
                else:
                    n = NtGraphNode(NtGraphNode.LeafNotHole)
                graph[nt][repr(pat)] = n


    # add successors
    for nt, ntdef in definelanguage.nts.items():
        for pat in ntdef.patterns:
            if isinstance(pat, pattern.PatSequence):
                gnode = graph[nt][repr(pat)]
                for p in pat.seq: ## FIXME need to handle this recursively.
                    if isinstance(p, pattern.PatSequence):
                        assert False
                    if isinstance(p, pattern.Nt):
                        successors = list(graph[p.prefix].values())
                        for nt2 in equivalentnts[p.prefix]:
                            successors += graph[nt2].values()
                        gnode.addsuccessor(successors)
                    if isinstance(p, pattern.BuiltInPat):
                        if p.kind == pattern.BuiltInPatKind.Hole:
                            gnode.addsuccessor([NtGraphNode(NtGraphNode.LeafHole)])

    """
    if isinstance(p, pattern.Repeat):
        gn = NtGraphNode(NtGraphNode.Repeat)
        if isinstance(p.pat, pattern.Nt):
            gn.addsuccessors(graph[p.prefix])
        elif isinstance(p.pat, pattern.BuiltInPatKind):
            gn.addsuccessor(NtGraphNode(NtGraphNode.LeafHole))
        else:
            assert False
        graph[nt][i].addsuccessor(gn)
    """
    dumpgraph(graph)
"""
digraph {
  compound=true;
	subgraph cluster_0{
		node [style=filled; shape=record; ];
		graph[style=solid;];
		Meh
		T
	}


	c -> T [lhead=cluster_0;];
	T -> a
}
"""



def dumpgraph(graph):
    sb = []
    sb.append('digraph {')
    sb.append('compound = true;')
    sb.append('node [style=filled; shape=record;];')
    sb.append('nodesep=1.0;')
    sb.append('ranksep=1.0;')
    sb.append('graph[style=solid;];')
    definednodes = set([])

    def gennode(node):
        if node.kind == NtGraphNode.LeafHole:    label = 'Hole'
        if node.kind == NtGraphNode.LeafNotHole: label = 'NotHole'
        if node.kind == NtGraphNode.Sequence:    label = 'Sequence'
        if node.kind == NtGraphNode.Repeat:      label = 'Repeat'
        sb.append('subgraph cluster_{} {{'.format(id(node)))
        sb.append('label=\"{}\";'.format(label))
        sb.append('v{} [label=\"\"; shape=point;]'.format(id(node)))
        sb.append('{{ v{} rank=min; }}'.format(id(node)))
        definednodes.add(id(node))
        for succgroup in node.successors:
            sb.append('v{} [label=\"\"]'.format(id(succgroup)))
        sb.append('}')

    for nt, nodes in graph.items():
        for patrepr, node in nodes.items():
            if id(node) not in definednodes:
                gennode(node)
            for succgroup in node.successors:
                for succ in succgroup:
                    if id(succ) not in definednodes:
                        gennode(succ)
                    sb.append('v{} -> v{}' .format(id(succgroup),  id(succ)))
    sb.append('}')
    print('\n'.join(sb))












# Annotate each pattern with number of holes it matches.
# First: for each pattern in the language compute min-number of holes and max-number of holes
#        based on nt closure used for nt cycle checking. This gives a nt->(min, max) mapping for 
#        each non-terminal in the language.
# Second: do the same thing iteratively but this instead read min-max numbers from the mapping above.
#         I am pretty sure one iteration is enough to propagate nt values.
class DefineLanguageCalculateNumberOfHoles(pattern.PatternTransformer):
    def __init__(self, definelanguage, closure):
        assert isinstance(definelanguage, tlform.DefineLanguage)
        self.definelanguage = definelanguage
        self.closure = closure
        self.nts = {}
        self.use_closure_for_nts = True

    def run(self):
        for nt, ntdef in self.definelanguage.nts.items():
            ntmin, ntmax = NumberOfHoles.Many, NumberOfHoles.Zero
            for pat in ntdef.patterns:
                pmin, pmax = self.transform(pat)
                print(pat, pmin, pmax)
                ntmin = NumberOfHoles.min(ntmin, pmin)
                ntmax = NumberOfHoles.max(ntmax, pmax)
            self.nts[nt] = (ntmin, ntmax)

        self.use_closure_for_nts = False
        print(self.nts)

        changed = True
        while changed:
            changed = False
            newnts = {}
            for nt, ntdef in self.definelanguage.nts.items():
                ntmin, ntmax = NumberOfHoles.Many, NumberOfHoles.Zero
                for pat in ntdef.patterns:
                    pmin, pmax = self.transform(pat)
                    ntmin = NumberOfHoles.min(ntmin, pmin)
                    ntmax = NumberOfHoles.max(ntmax, pmax)
                pnums = (ntmin, ntmax)
                newnts[nt] = pnums 
                if pnums != self.nts[nt]:
                    changed = True
            self.nts = newnts

        print(self.nts)

        for ntdef in self.definelanguage.nts.values():
            assert isinstance(ntdef, tlform.DefineLanguage.NtDefinition)
            ntmin, ntmax = self.nts[ntdef.nt.prefix]
            ntdef.nt.addmetadata( pattern.PatNumHoles(ntmin, ntmax) )
        return self.definelanguage

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
        pmin = NumberOfHoles.Many if pmin == NumberOfHoles.One else pmin
        pmax = NumberOfHoles.Many if pmax == NumberOfHoles.One else pmax 
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
        if self.use_closure_for_nts:
            if 'hole' in self.closure[node.prefix]:
                return NumberOfHoles.One, NumberOfHoles.One
            return NumberOfHoles.Zero, NumberOfHoles.Zero
        return self.nts[node.prefix]

    def transformLit(self, node):
        return NumberOfHoles.Zero, NumberOfHoles.Zero


# This pass traverses the pattern looking for (in-hole pat1 pat2) and applies PatternChecker to pat1.
class InHoleChecker(pattern.PatternTransformer):
    # Same as DefineLanguageCalculateNumberofHoles but we read min/max numbers
    # from annotation and we do not do fixpoint computation. :))
    class PatternChecker(DefineLanguageCalculateNumberOfHoles):
        def __init__(self, definelanguage, pattern):
            self.definelanguage = definelanguage
            self.pattern = pattern

        def run(self):
            return self.transform(self.pattern)

        def transformNt(self, node):
            assert isinstance(node, pattern.Nt)
            n = self.definelanguage.nts[node.prefix].nt.getmetadata(pattern.PatNumHoles)
            return n.numholesmin, n.numholesmax

    def __init__(self, definelanguage, pattern):
        self.definelanguage = definelanguage
        self.pattern = pattern

    def run(self):
        return self.transform(self.pattern)

    def transformInHole(self, node):
        assert isinstance(node, pattern.InHole)
        pat1 = self.transform(node.pat1)
        minholes, maxholes = InHoleChecker.PatternChecker(self.definelanguage, node.pat1).run()
        print(minholes, maxholes)
        if not (minholes == NumberOfHoles.One and maxholes == NumberOfHoles.One):
            raise CompilationError('Pattern {} in {} does not match exactly one hole'.format(repr(node.pat1), repr(node)))
        return node


# This pass attempts to make consecutive ellipses match deterministically.
# Here's the example:
# Given language (m ::= (* m m) e) (e ::= (+ e e) n) (n ::= number), ellipses in pattern 
# (m_1 ... e_1 ... n_1 ... e_2) cannot match deterministically - because m_1, e_1 and e_2 can also be numbers.
# We have {e} ⊆ m, {n} ⊆ e, and {number} ⊆ n. If we compute transitive "closure" for each non-terminal we get the following:
# {number, n, e} ⊆ m; {number, n} ⊆ e; {number} ⊆ n. Two patterns p1,p2 cannot be made deterministic 
# if closure(p1) ∩ closure(p2) is not empty.
#FIXME this is not true for duplicate definitions that are not used anywhere, add extra (z ::= number) rule and 
# while computing closure z is not in e. We need to introduce a graph, perform dfs and see if common nodes can be reached.

# This should handle primitive cases of Nt and BuiltInPat. 
 
# Otherwise, we should check if patterns being compared are structurally identical and leafs of patterns
# pass closure membership test from above.
# In ((m_1 e_1) ... (e_2 n_1) ...) subpatterns  (m_1 e_1) and (e_2 n_1)
# are structurally identical and for pair (m_1, e_2) e ∈ closure(m), for (e_1, n_1) n ∈ closure(e)

# Now we consider pattern ((x_1 ...) ... (n_1 ...) ...). (x_1 ...) ... pattern cannot be matched deterministically since even though
# patterns x and n match competely different terms  both subpatterns may match (). 
#For example, for term (a b) () (1 2 3) there are two matches match1: x_1=((a b) ()) n_1=((1 2 3)) match2: x_1=((a b))  n_1=(() (1 2 3)).
# This should be initial term check.

# What about ((x_1 ... n_1) ... (s_1 ... n_2) ...)? Both subterms under ellipsis have the same structure. Term ((x y z 1) (1 2 3 4)) matches 
# the pattern but since (x y z) and (1 2 3) are optional, the term without these becomes ((1) (4)) which has to be matched non-deterministically.
# Similarly, by adding (y ::= string) rule to the language the pattern ((x_1 ... y_1) ... (x_1 ... n_1) ...) CAN BE matched deterministically, 
# for example ((x y z "helloworld") (x 1)). 
# TLDR we ignore ellipsis and make decision based on elements of the sequence that have to matched. If closure test fails then pattern matching can
# be made deterministic.



# TODO in-hole treatment?  
class MakeEllipsisDeterministic(pattern.PatternTransformer):
    # Given two patterns pat1 and pat2, both under ellipsis, return True if pat1
    # can be matched deterministically.
    class PatternStructuralChecker:
        def __init__(self, closures):
            self.closures = closures

        def aredifferent(self, pat1, pat2):
            assert isinstance(pat1, pattern.Pat)
            assert isinstance(pat2, pattern.Pat)
            method_name = 'aredifferent' + pat1.__class__.__name__
            method_ref = getattr(self, method_name)
            return method_ref(pat1, pat2)

        def aredifferentPatSequence(self, pat1, pat2):
            assert isinstance(pat1, pattern.PatSequence)
            if isinstance(pat2, pattern.PatSequence):
                p1 = pat1.get_nonoptional_matches()
                p2 = pat2.get_nonoptional_matches()
                if len(p1) != len(p2):
                    return True
                for i in range(len(p1)):
                    if self.aredifferent(p1[i], p2[i]):
                        return True
                return False 
            return True

        def aredifferentNt(self, pat1, pat2):
            assert isinstance(pat1, pattern.Nt)
            if isinstance(pat2, pattern.Nt):
                pat1cl = self.closures[pat1.prefix]
                pat2cl = self.closures[pat2.prefix]
                return len(pat1cl.intersection(pat2cl)) == 0
            if isinstance(pat2, pattern.BuiltInPat):
                pat1cl = self.closures[pat1.prefix]
                return not pat2.prefix in pat1cl
            return True

        # TODO figure out how to handle adjacent in-hole patterns properly.
        def aredifferentInHole(self, pat1, pat2):
            assert isinstance(pat1, pattern.InHole)
            return False

        def aredifferentBuiltInPat(self, pat1, pat2):
            assert isinstance(pat1, pattern.BuiltInPat)
            if isinstance(pat2, pattern.BuiltInPat):
                return pat1.kind != pat2.kind
            if isinstance(pat2, pattern.Nt):
                pat2cl = self.closures[pat2.prefix]
                return not pat1.prefix in pat2cl
            return True

        def aredifferentLit(self, pat1, pat2):
            assert isinstance(pat1, pattern.Lit)
            if isinstance(pat2, pattern.Lit):
                if pat1.kind == pat2.kind:
                    return pat1.lit != pat2.lit
                return True
            return True

    def __init__(self, definelanguage, pat):
        assert isinstance(definelanguage, tlform.DefineLanguage)
        self.definelanguage = definelanguage 
        self.pat = pat


    # Partitions sequence of terms 
    def _partitionseq(self, seq):
        matching_ellipsis = False
        partitions = [] 
        partition = []
        for i, pat in enumerate(seq):
            if isinstance(pat, pattern.Repeat):
                if matching_ellipsis:
                    partition.append(pat)
                else:
                    # flush previous partition
                    matching_ellipsis = True
                    if len(partition) > 0:
                        partitions.append((False, partition))
                    partition = [ pat ]
            else:
                partition.append(pat)
                if matching_ellipsis:
                    assert len(partition) > 1
                    matching_ellipsis = False
                    partitions.append((True, partition))
                    partition = []

        if len(partition) > 0:
            if matching_ellipsis:
                partitions.append((True, partition))
            else:
                partitions.append((False, partition))

        return partitions

    def run(self):
        return self.transform(self.pat)

    def transformPatSequence(self, sequence):
        assert isinstance(sequence, pattern.PatSequence)
        closures = self.definelanguage.closure
        assert self.definelanguage.closure != None

        # recursively transform patterns first.
        tseq = []
        for pat in sequence.seq:
            tseq.append( self.transform(pat) )
            
        nseq = []
        partitions = self._partitionseq(tseq)
        for contains_ellipsis, partition in partitions:
            if contains_ellipsis:
                for i in range(len(partition) - 1):
                    pat1, pat2 = partition[i], partition[i+1]
                    if isinstance(pat1, pattern.Repeat):
                        psc = self.PatternStructuralChecker(closures)
                        if isinstance(pat2, pattern.Repeat):
                            p1, p2 = pat1.pat, pat2.pat
                        else:
                            p1, p2 = pat1.pat, pat2
                        if psc.aredifferent(p1, p2):
                            nrep = pattern.Repeat(p1, pattern.RepeatMatchMode.Deterministic).copymetadatafrom(pat1)
                            nseq.append(nrep)
                        else:
                            nseq.append(pat1)
                # append the last unprocessed element
                last = partition[-1]
                if isinstance(last, pattern.Repeat):
                    if not isinstance(last.pat, pattern.InHole):
                        last = pattern.Repeat(last.pat, pattern.RepeatMatchMode.Deterministic).copymetadatafrom(last)
                nseq.append(last)
            else: 
                nseq += partition
        return pattern.PatSequence(nseq).copymetadatafrom(sequence)

class TopLevelProcessor(tlform.TopLevelFormVisitor):
    def __init__(self, module, context):
        assert isinstance(module, tlform.Module)
        assert isinstance(context, CompilationContext)
        self.module = module
        self.context = context
        self.symgen = SymGen() 

        # store reference to definelanguage structure for use by redex-match form
        self.definelanguages = {}
        self.reductionrelations = {}

    def run(self):
        forms = []
        for form in self.module.tlforms:
            forms.append( self._visit(form) )
        return tlform.Module(forms), self.context


    def __definelanguage_checkntcycles(self, form, graph):
        assert isinstance(form, tlform.DefineLanguage)

        class DfsVisitor:
            def __init__(self, nts, graph):
                self.nts = nts
                self.time = 0
                self.graph = graph
                self.d = dict((g, -1) for g in graph.keys())
                self.f = dict((g, -1) for g in graph.keys())

            def gettime(self):
                t = self.time 
                self.time += 1
                return t

            def reportcycle(self, path, v):
                idx = path.index(v)
                assert v in self.nts 
                for p in path[idx:]:
                    assert p in self.nts
                cyclepath = path[idx:] + [v]
                raise CompilationError('nt cycle {}'.format(cyclepath))

            def visit(self, v):
                self.__visitimpl(v, [])

            def __visitimpl(self, v, path):
                if self.d[v] == -1: 
                    path.append(v)
                    self.d[v] = self.gettime()
                    for adjv in self.graph.get(v, set([])):
                        self.__visitimpl(adjv, path)
                        if self.f[adjv] == -1:
                            self.reportcycle(path, adjv)
                    self.f[v] = self.gettime()
                    path.pop()

        nts = form.ntsyms()
        for nt in nts:
            v = DfsVisitor(nts, graph)
            v.visit(nt)

    def _visitDefineLanguage(self, form):
        assert isinstance(form, tlform.DefineLanguage)
        self.definelanguages[form.name] = form 

        resolver = NtResolver(form.ntsyms())
        remover = UnderscoreRemover()
        uniquify = UnderscoreIdUniquify()
        for nt, ntdef in form.nts.items():
            npatterns = []
            for pat in ntdef.patterns:
                pat = resolver.transform(pat)
                pat = remover.transform(pat)
                pat = uniquify.transform(pat)
                npatterns.append(pat)
            ntdef.patterns = npatterns #FIXME all AstNodes should be immutable...

        graph = form.computeclosure()
        self.__definelanguage_checkntcycles(form, graph)
        #DefineLanguageCalculateNumberOfHoles(form, form.closure).run()
        constructgraph(form)
        sys.exit(1)

        for nt, ntdef in form.nts.items():
            npatterns = []
            for pat in ntdef.patterns:
                assert form.closure != None
                pat = MakeEllipsisDeterministic(form, pat).run()
                pat = AssignableSymbolExtractor(pat).run()
                npatterns.append(pat)
            ntdef.patterns = npatterns #FIXME all AstNodes should be immutable...
        self.context.add_variables_mentioned(form.name, resolver.variables)

        return form

    def __processpattern(self, pat, languagename):
        ntsyms = self.definelanguages[languagename].ntsyms() #TODO nicer compiler error handling here
        resolver = NtResolver(ntsyms)
        pat = resolver.transform(pat)
        pat = EllipsisDepthChecker(pat).run()
        assert self.definelanguages[languagename].closure != None
        lang = self.definelanguages[languagename]
        InHoleChecker(lang, pat).run()
        pat = MakeEllipsisDeterministic(self.definelanguages[languagename], pat).run()
        symbols = pat.getmetadata(pattern.PatAssignableSymbolDepths)
        for sym in symbols.syms:
            pat = ConstraintCheckInserter(pat, sym).run()
        pat = AssignableSymbolExtractor(pat).run()
        return pat

    def _visitRedexMatch(self, form):
        assert isinstance(form, tlform.RedexMatch)
        form.pat = self.__processpattern(form.pat, form.languagename)
        return form

    def _visitMatchEqual(self, form):
        assert isinstance(form, tlform.MatchEqual)
        form.redexmatch = self._visit(form.redexmatch)
        return form

    def _visitAssertTermsEqual(self, form):
        assert isinstance(form, tlform.AssertTermsEqual)
        idof = self.symgen.get('termlet')
        form.template = genterm.TermAnnotate(form.variabledepths, idof, self.context).transform(form.template)
        return form

    def processReductionCase(self, reductioncase, languagename):
        assert isinstance(reductioncase, tlform.DefineReductionRelation.ReductionCase)
        reductioncase.pattern = self.__processpattern(reductioncase.pattern, languagename)
        assignablesymsdepths = reductioncase.pattern.getmetadata(pattern.PatAssignableSymbolDepths)
        idof = self.symgen.get('reductionrelation')
        reductioncase.termtemplate = genterm.TermAnnotate(assignablesymsdepths.syms, idof, self.context).transform(reductioncase.termtemplate)

    def _visitDefineReductionRelation(self, form):
        assert isinstance(form, tlform.DefineReductionRelation)
        self.reductionrelations[form.name] = form
        for rc in form.reductioncases:
            self.processReductionCase(rc, form.languagename)
        if form.domain != None:
            form.domain = self.__processpattern(form.domain, form.languagename)
        return form

    def _visitApplyReductionRelation(self, form):
        assert isinstance(form, tlform.ApplyReductionRelation)
        reductionrelation = self.reductionrelations[form.reductionrelationname]
        return form








#class PatternComparator:
#    """
#    Compares patterns. Underscores are ignored.
#    """
#    def compare(self, this, other):
#        assert isinstance(this, ast.Pat)
#        assert isinstance(other, ast.Pat)
#        method_name = 'compare' + this.__class__.__name__
#        method_ref = getattr(self, method_name)
#        return method_ref(this, other)
#
#    def compareUnresolvedSym(self, this, other):
#        assert False, 'not allowed'
#
#    def compareLit(self, this, other):
#        if isinstance(other, ast.Lit):
#            return this.kind == other.kind and this.lit == other.lit
#        return False
#
#    def compareNt(self, this, other):
#        if isinstance(other, ast.Nt):
#            return this.prefix == other.prefix
#        return Falseut99.org/
#
#    def compareRepeat(self, this, other):
#        if isinstance(other, ast.Repeat):
#            return self.compare(this.pat, other.pat)
#        return False
#
#    def compareBuiltInPat(self, this, other):
#        if isinstance(other, ast.BuiltInPat):
#            return this.kind == other.kind and this.prefix == other.prefix
#        return False
#
#    def comparePatSequence(self, this, other):
#        if isinstance(other, ast.PatSequence):
#            if len(this) == len(other):
#                match = True
#                for i, elem in enumerate(this):
#                    match = self.compare(elem, other[i])
#                    if not match:
#                        break
#                return match
#        return False
#
#
#class InsertTermEqualityChecking:
#    pass
#
## This does not work as expected. For example, 
## given language (e ::= (e ... n n ...) (+ e e) n) (n ::= number) matching e greedily 
## in the first pattern also consumes all n if they are present in the term.
## Matching e ... needs to return all permutations.
#
## Perhaps we could also do (e ... n n ...) -> ( e ... n ... n) -> (e ... n) (because n is e),
## match n in the end of the term first and then match e ...  greedily?
#
## FIXME always return fresh ast node instances.
#class DefineLanguagePatternSimplifier(pat.PatternTransformer):
#    """
#    The goal of this pass is to simplify patterns in define-language. For example, given pattern
#    e ::= (n ... n ... n n ... n) we do not need to match each repitition of n to establish that some term
#    is actually e (and individually matched items aren't bound). 
#    All that is needed is for the term to contain at least two n. Thus,
#    (n ... n ... n n ... n)  ---> (n ... n  n ... n)   [merge two n ...]
#    (n ... n n ... n) --> (n n ... n ... n)            [shuffle]
#    (n n ... n ... n) --> (n n ... n)                  [merge]
#    (n n ... n) --> (n n n...)                         [shuffle]
#    This way, instead of producing multiple matches that no one needs (as required by n ...) 
#    all sub-patterns can be matched 'greedily'.
#    """
#
#    def transformPatSequence(self, node):
#        assert isinstance(node, ast.PatSequence)
#        # not very pythonic....
#        newseq = []
#        for e in node.seq:
#            newseq.append(self.transform(e))
#        
#        i = 0
#        newseq2 = []
#        while i < len(newseq):
#            num_repeats = 0
#            num_required = 0
#
#            if isinstance(newseq[i], ast.Repeat):
#                elem = newseq[i].pat
#                num_repeats += 1
#            else:
#                elem = newseq[i]
#                num_required += 1
#
#            j = i + 1
#            while j < len(newseq):
#                if isinstance(newseq[j], ast.Repeat):
#                    if PatternComparator().compare(elem, newseq[j].pat):
#                        num_repeats += 1
#                    else:
#                        break
#                else:
#                    if PatternComparator().compare(elem, newseq[j]):
#                        num_required += 1
#                    else:
#                        break
#                j += 1
#            i = j
#
#            # push required matches first, optional repetiton after if present in original pattern.
#            for k in range(num_required):
#                newseq2.append(elem)
#            if num_repeats > 0:
#                newseq2.append(ast.Repeat(elem))
#
#        node.seq = newseq2
#        return node
