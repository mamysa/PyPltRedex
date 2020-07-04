import src.model.tlform as tlform
import src.model.pattern as pattern
import enum

from src.util import CompilationError

# generates graphviz... graph. 
def dumpgraph(languagename, graph):
    sb = []
    sb.append('digraph {')
    sb.append('compound = true;')
    sb.append('node [style=filled; shape=record;];')
    sb.append('nodesep=1.0;')
    sb.append('ranksep=1.0;')
    sb.append('graph[style=solid;];')

    definednodes = set([])
    definededges = set([]) 

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

    def genedges(node):
        for succgroup in node.successors:
            for succ in succgroup:
                if id(succ) not in definednodes:
                    gennode(succ)
                edge = (id(succgroup), id(succ))
                if edge not in definededges:
                    definededges.add(edge)
                    sb.append('v{} -> v{}' .format(id(succgroup),  id(succ)))
                    genedges(succ)

    for nt, nodes in graph.items():
        for patrepr, node in nodes.items():
            if id(node) not in definednodes:
                gennode(node)
                genedges(node)

    sb.append('}')
    s = '\n'.join(sb)

    with open('dump_{}.dot'.format(languagename), 'w') as f:
        f.write(s)

# Vertex in NtGraph.
class NtGraphNode:
    LeafNotHole = 0
    LeafHole = 1
    Repeat = 2
    Sequence = 3

    def __init__(self, kind):
        self.kind = kind
        self.numholes = (NumberOfHoles.Uninitialized, NumberOfHoles.Uninitialized)
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

class NumberOfHoles(enum.IntEnum):
    Zero = 0
    One  = 1
    Many = 2
    Uninitialized = 999

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

class NtGraphBuilder(pattern.PatternTransformer):
    def __init__(self, definelanguage):
        self.definelanguage = definelanguage
        self.gnodestack = []
        self.graph = {}
        self.equivalentnts = {}  

    def run(self):
        # first construct graph nodes and collect all standalone non-terminals that are not inside pattern sequence. 
        for nt, ntdef in self.definelanguage.nts.items():
            self.graph[nt] = {}
            self.equivalentnts[nt] = []
            for pat in ntdef.patterns:
                if isinstance(pat, pattern.Nt):
                    self.equivalentnts[nt].append(pat.prefix)
                if isinstance(pat, pattern.PatSequence):
                    n = NtGraphNode(NtGraphNode.Sequence)
                    self.graph[nt][repr(pat)] = n
                if isinstance(pat, pattern.InHole):
                    raise CompilationError('in-hole pattern in define-language')
                if isinstance(pat, pattern.BuiltInPat):
                    kind = NtGraphNode.LeafHole if pat.kind == pattern.BuiltInPatKind.Hole else NtGraphNode.LeafNotHole
                    n = NtGraphNode(kind)
                    self.graph[nt][repr(pat)] = n

        for nt, ntdef in self.definelanguage.nts.items():
            for pat in ntdef.patterns:
                if isinstance(pat, pattern.PatSequence):
                    for p in pat:
                        gnode = self.graph[nt][repr(pat)]
                        self.gnodestack.append(gnode)
                        self.transform(p)
                        self.gnodestack.pop()
        return self.graph

    def transformNt(self, node):
        assert isinstance(node, pattern.Nt)
        successors = list(self.graph[node.prefix].values())
        for nt in self.equivalentnts[node.prefix]:
            successors += self.graph[nt].values()
        self.gnodestack[-1].addsuccessor(successors)
        return node

    def transformPatSequence(self, node):
        assert isinstance(node, pattern.PatSequence)
        gn = NtGraphNode(NtGraphNode.Sequence)
        self.gnodestack.append(gn)
        for pat in node.seq:
            self.transform(pat)
        self.gnodestack.pop() 
        self.gnodestack[-1].addsuccessor([gn])

    def transformRepeat(self, node):
        assert isinstance(node, pattern.Repeat)
        gn = NtGraphNode(NtGraphNode.Repeat)
        self.gnodestack.append(gn)
        self.transform(node.pat)
        self.gnodestack.pop() 
        self.gnodestack[-1].addsuccessor([gn])
        return node

    def transformInHole(self, node):
        raise CompilationError('in-hole pattern in define-language')

    def transformBuiltInPat(self, node):
        assert isinstance(node, pattern.BuiltInPat)
        # don't really care about elements that are not holes here.
        if node.kind == pattern.BuiltInPatKind.Hole:
            self.gnodestack[-1].addsuccessor([NtGraphNode(NtGraphNode.LeafHole)])
        return node


# This pass annotates non-terminal definitions of a language with minimal-maximal number of holes 
# encountered in patterns making up said non-terminal. This is to be used for raising compilation 
# error while processing (in-hole) patterns.
# Previous implementation of relied on transitive closure computed during cycle-checking pass and 
# iterative computation but it solely using the closure results in incorrect min-max value initialization.
# For example, in language (n ::= number) (P ::= (E)) (E ::= P (E n) hole) and its transitive closure 
# n -> {number} P -> {} E -> { P } we have
#         min  max 
# (E)     one  one
# (E n)   one  one
# P       one  one 
# E       zero one <--- zero is because of non-terminal P in definition of E has empty transitive closure and hence
# n       zero zero     while computing min-max for E we have min(P, (E n), hole) = min(zero, one, one) = zero.
# For second iteration, 
#         min  max 
# (E)     zero one
# (E n)   zero one <--- becase E is zero one
# P       zero one  
# E       zero one 
# n       zero zero     
# and this is also incorrect.
# We need to take the shape of patterns into account and handle contents of pattern sequences. Instead of assigning some
# initial values to non-terminal symbols we construct a graph where each non-terminal is connected to a set of pattern it matches.
# Thus, the language defined above becomes 
# (E)
# +---+
# |(.)+-----+---+      (E n)
# +-+-+     |   |     +-----+
#   ^ ^     |   +--+->+(. .)|
#   | +-----+      ^  +-+-+-+
#   |       |      |    | |
#   +-------+------+----+ +---------v
#           |           |       +-------+
#           |           |       |number |
#           |           v       +-------+
#           |         +----+
#           +-------> |hole|
#                     +----+
# Since each node in the graph corresponds to some pattern in NtDefinition, number of holes each expression
# matches can be found by iteratively applying DFS procedure that searches for nodes labelled 'hole' and returns 
# said min-max values. During iteration nodes that have already been visited are not revisited. 
# In the first iteration (Unitialized, Unitialized) number of holes may be returned (happens when there are cycles 
# in the graph - we simply disregard these values.)
# For example, language (P ::= (E E)) (E ::= P (E n)  hole) requires two iterations to converge -
# in the first iteration E = (1 1) and the second iteration E = (2 2) since E is P and P = (2 2)
class DefineLanguage_HoleReachabilitySolver:
    def __init__(self, definelanguage, debug_dump_ntgraph=False):
        assert isinstance(definelanguage, tlform.DefineLanguage)
        self.definelanguage = definelanguage
        self.graph = None
        self.visited = None
        self.changed = True

        self.debug_dump_ntgraph = debug_dump_ntgraph

    def run(self):
        self.graph = NtGraphBuilder(self.definelanguage).run()
        if self.debug_dump_ntgraph:
            dumpgraph(self.definelanguage.name, self.graph)

        while self.changed:
            self.changed = False
            self.visited = set([])
            for nt, nodes in self.graph.items():
                for patrepr, node in nodes.items():
                    if node not in self.visited:
                        self.dfsvisit(node)

        calculatednts = {}
        def calcnt(nt, ntdef):
            if nt in calculatednts:
                return calculatednts[nt]
            ntgraphnodes = self.graph[nt]
            ntmin, ntmax = NumberOfHoles.Many, NumberOfHoles.Zero
            for pat in ntdef.patterns:
                try:
                    pmin, pmax = ntgraphnodes[repr(pat)].numholes
                except KeyError:
                    assert isinstance(pat, pattern.Nt)
                    # we can do this because language grammar is not allowed to have non-terminal cycles.
                    rntdef = self.definelanguage.nts[pat.prefix]
                    pmin, pmax = calcnt(pat.prefix, rntdef)
                ntmin = NumberOfHoles.min(ntmin, pmin)
                ntmax = NumberOfHoles.max(ntmax, pmax)

            calculatednts[nt] = (ntmin, ntmax)
            ntdef.nt.addmetadata(pattern.PatNumHoles(ntmin, ntmax))
            return ntmin, ntmax

        for nt, ntdef in self.definelanguage.nts.items():
            calcnt(nt, ntdef)

    def dfsvisit(self, node):
        assert isinstance(node, NtGraphNode)
        if node in self.visited:
            return node.numholes
        self.visited.add(node)
        if node.kind == NtGraphNode.LeafNotHole:
            self.changed = node.update(NumberOfHoles.Zero, NumberOfHoles.Zero) or self.changed
            return node.numholes
        if node.kind == NtGraphNode.LeafHole:
            self.changed = node.update(NumberOfHoles.One, NumberOfHoles.One) or self.changed
            return node.numholes

        if node.kind == NtGraphNode.Repeat:
            assert len(node.successors) == 1
            sgmin, sgmax = NumberOfHoles.Many, NumberOfHoles.Zero
            for succ in node.successors[0]:
                pmin, pmax = self.dfsvisit(succ) 
                if (pmin, pmax) != (NumberOfHoles.Uninitialized, NumberOfHoles.Uninitialized):
                    sgmin = NumberOfHoles.min(sgmin, pmin)
                    sgmax = NumberOfHoles.max(sgmax, pmax)
            sgmin = NumberOfHoles.Zero if sgmin in [NumberOfHoles.One, NumberOfHoles.Many] else sgmin 
            sgmax = NumberOfHoles.Many if sgmax in [NumberOfHoles.One, NumberOfHoles.Many] else sgmax 
            if (sgmin, sgmax) == (NumberOfHoles.Many, NumberOfHoles.Zero):
                self.changed = node.update(NumberOfHoles.Uninitialized, NumberOfHoles.Uninitialized) or self.changed
                return NumberOfHoles.Uninitialized, NumberOfHoles.Uninitialized
            self.changed = node.update(sgmin, sgmax) or self.changed
            return sgmin, sgmax

        # sequence
        if len(node.successors) == 0:
            return NumberOfHoles.Zero, NumberOfHoles.Zero

        # So here we need to iterate twice over node.successors. For example, consider language,
        # (P ::= (E)) (E :: P (E hole)). Consider first iteration of DFS visit 
        # (.) --> (.(E) hole) -> (.(E) hole). Since last node has already been visited, uninitialized values 
        # are returned, and (one, one) is returned for the whole expression. This is incorrect as it doesn't 
        # resolve local reference to expressions defined by E. Thus, doing the second iteration we now know that
        # (.(E) hole) matches one hole and it also contains a hole by itself - hence (many many) holes are matched.
        # TLDR: we want local convergence first. 
        # btw this was totally not a bug. Totally. I promise ;)
        changed = True
        while changed:
            changed = False
            nmin, nmax = NumberOfHoles.Zero, NumberOfHoles.Zero
            for succgroup in node.successors:
                sgmin, sgmax = NumberOfHoles.Many, NumberOfHoles.Zero
                for succ in succgroup:
                    pmin, pmax = self.dfsvisit(succ) 
                    if (pmin, pmax) != (NumberOfHoles.Uninitialized, NumberOfHoles.Uninitialized):
                        sgmin = NumberOfHoles.min(sgmin, pmin)
                        sgmax = NumberOfHoles.max(sgmax, pmax)
                if (sgmin, sgmax) != (NumberOfHoles.Many, NumberOfHoles.Zero):
                    nmin = NumberOfHoles.add(nmin, sgmin)
                    nmax = NumberOfHoles.add(nmax, sgmax)
            changed = node.update(nmin, nmax) or changed
        return nmin, nmax
