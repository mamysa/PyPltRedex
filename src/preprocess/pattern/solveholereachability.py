import src.model.tlform as tlform
import src.model.pattern as pattern
import enum

from src.util import CompilationError

# This pass annotates non-terminal definitions of a language with minimal-maximal number of holes 
# encountered in patterns making up said non-terminal. This is to be used for raising compilation 
# error while processing (in-hole) patterns.
# I had a hard time figuring out how to do so directly using already existing NtDefinition, so instead
# this problem is solved by constructing a graph where each non-terminal explicitly points to a set of 
# expressions that it matches.
# For example, given language (n ::= number) (P ::= (E)) (E ::= P (E n) hole) we may obtain the following graph.
# (E)
# +---+
# |(.)+-----+---+      (E n)
# +-+-+     |   |     +-----+
#   ^ ^     |   +--+->+(. .)|
#   | +-----+      ^  +-+-+-+
#   |       |      |    | |
#   +-------+------+----+ +---------v
#           |           |       +-------+
#           |           |       |nothole|
#           |           v       +-------+
#           |         +----+
#           +-------> |hole|
#                     +----+
# The graph is modelled as follows:
# (1) Outer nodes that represent actual patterns and come in four kinds: Sequences, Repetitions, LeafHole, LeafNotHole.
#     If top-level pattern happens to contain repetitions/sequences then outer-nodes representing these will be 
#     constructed recursively. 
# (2) Inner nodes that represent elements inside the pattern. Edges are created between inner to outer nodes. For example,
#     in expression (E n) first inner-node points to a hole because E also matches a hole.
# 
# Hole reachability algorithm works in the following way.
# (1) Ensure that after graph construction there's LeafHole outer node. If there's none, immediately annotate all 
#     non-terminal symbols in the language with (zero, zero).
# (2) Otherwise, start breadth-first traversal of the graph starting from leaf node (i.e. in reverse order). 
#     NumHoles values are initialized for leaf nodes with appropriate values.
#     (a) Handle self-loops first and propagate computed values. For example, (E number) is initially unitialized.
#         Starting from leaf number (E number) becomes (zero, zero). Immediately handle self-loop ((E number) number)
#         to update number of holes value of the first element.
#     (b) Handle other edges and propagate computed values to other inner nodes.
#     (c) Continue doing so until convergence.
# Node update logic is self-explanatory.
# 
# This algorithm has a slight defficiency, however. Consider the language defined above. The algorithm finds out that 
# P = (one, one), E = (one, one) n = (zero, zero). This is not entirely correct as language may contain terms like 
# (((((....))))) which are infinite terms by picking pattern (E) at all times. As such terms do not contain any holes,
# P and E should ideally match (zero, one) holes. However, upon testing the language against PltRedex, calling 
# (redex-match L (in-hole P n) (term 1)) returns #f meaning PltRedex thinks that P contains exactly one hole...
# One could interpret computed results as "number of holes in expressions that are expressible".

class NumberOfHoles(enum.IntEnum):
    Zero = 0
    One  = 1
    Many = 2
    Uninitialized = 999

    @staticmethod
    def add(n1, n2):
        assert isinstance(n1, NumberOfHoles)
        assert isinstance(n2, NumberOfHoles)
        if n1 == NumberOfHoles.Uninitialized:
            if n2 == NumberOfHoles.Uninitialized:
                return NumberOfHoles.Uninitialized
            else:
                return n2
        else:
            if n2 == NumberOfHoles.Uninitialized:
                return n1
            else:
                assert n1 in (NumberOfHoles.Zero, NumberOfHoles.One, NumberOfHoles.Many)
                assert n2 in (NumberOfHoles.Zero, NumberOfHoles.One, NumberOfHoles.Many)
                num = min(n1.value + n2.value, NumberOfHoles.Many.value)
                return NumberOfHoles(num)

    @staticmethod
    def min(n1, n2):
        return NumberOfHoles(min(n1.value, n2.value))

    @staticmethod
    def max(n1, n2):
        return NumberOfHoles(max(n1.value, n2.value))

class NtGraph:
    class Node:
        LeafNotHole = 0
        LeafHole = 1
        Repeat = 2
        Sequence = 3

        def __init__(self, kind):
            self.kind = kind
            self.innernodes = []
            self.predecessor_innernodes = []
            self.min_numberof_holes = NumberOfHoles.Uninitialized
            self.max_numberof_holes = NumberOfHoles.Uninitialized
            if self.kind == NtGraph.Node.LeafNotHole:
                self.min_numberof_holes = NumberOfHoles.Zero
                self.max_numberof_holes = NumberOfHoles.Zero
            if self.kind == NtGraph.Node.LeafHole:
                self.min_numberof_holes = NumberOfHoles.One
                self.max_numberof_holes = NumberOfHoles.One

        def update(self):
            if self.kind == NtGraph.Node.Sequence:
                newmin, newmax = NumberOfHoles.Uninitialized, NumberOfHoles.Uninitialized
                for innernode in self.innernodes:
                    newmin = NumberOfHoles.add(newmin, innernode.min_numberof_holes) 
                    newmax = NumberOfHoles.add(newmax, innernode.max_numberof_holes) 
                if (newmin, newmax) != (self.min_numberof_holes, self.max_numberof_holes):
                    self.min_numberof_holes = newmin
                    self.max_numberof_holes = newmax
                    return True
                return False

            if self.kind == NtGraph.Node.Repeat:
                assert len(self.innernodes) == 1
                newmin, newmax = self.innernodes[0].min_numberof_holes, self.innernodes[0].max_numberof_holes
                if (newmin, newmax) != (NumberOfHoles.Uninitialized, NumberOfHoles.Uninitialized):
                    newmin = NumberOfHoles.Zero if newmin in [NumberOfHoles.One, NumberOfHoles.Many] else newmin 
                    newmax = NumberOfHoles.Many if newmax in [NumberOfHoles.One, NumberOfHoles.Many] else newmax 

                if (newmin, newmax) != (self.min_numberof_holes, self.max_numberof_holes):
                    self.min_numberof_holes = newmin
                    self.max_numberof_holes = newmax
                    return True
                return False

            assert False, 'updating leafs'

        def __repr__(self):
            if self.kind == NtGraph.Node.LeafHole:    label = 'Hole'
            if self.kind == NtGraph.Node.LeafNotHole: label = 'NotHole'
            if self.kind == NtGraph.Node.Sequence:    label = 'Sequence'
            if self.kind == NtGraph.Node.Repeat:      label = 'Repeat'
            return 'NtGraph.Node({}, {}, {})'.format(label, self.min_numberof_holes, self.max_numberof_holes)

    class InnerNode:
        def __init__(self, parent):
            assert isinstance(parent, NtGraph.Node)
            self.parent = parent
            self.min_numberof_holes = NumberOfHoles.Uninitialized
            self.max_numberof_holes = NumberOfHoles.Uninitialized

        def update(self, nmin, nmax):
            if (self.min_numberof_holes, self.max_numberof_holes) == (NumberOfHoles.Uninitialized, NumberOfHoles.Uninitialized):
                self.min_numberof_holes = nmin
                self.max_numberof_holes = nmax
            else:
                self.min_numberof_holes = NumberOfHoles.min(self.min_numberof_holes, nmin) 
                self.max_numberof_holes = NumberOfHoles.max(self.max_numberof_holes, nmax) 

    def __init__(self, pattern2node, nt2node, leafs):
        self.pattern2node = pattern2node 
        self.nt2node = nt2node
        self.leafs = leafs 

    def getsuccessors(self, innernode):
        assert isinstance(innernode, NtGraph.InnerNode)
        return innernode.container.successorinnernodes
    
    def getnumberofedges(self):
        num = 0
        return num


    def dump(self, languagename):
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
            sb.append('subgraph cluster_{} {{'.format(id(node)))
            sb.append('label=\"{}\";'.format(repr(node)))
            sb.append('out{} [label=\"\"; shape=point;]'.format(id(node)))
            sb.append('{{ out{} rank=min; }}'.format(id(node)))
            definednodes.add(id(node))
            for innernode in node.innernodes:
                sb.append('inner{} [label=\"\"]'.format(id(innernode)))
            sb.append('}')

        def genedges(node):
            for succ in node.predecessor_innernodes:
                if id(succ.parent) not in definednodes:
                    gennode(succ.parent)
                    genedges(succ.parent)
                edge = (id(node), id(succ))
                if edge not in definededges:
                    definededges.add(edge)
                    sb.append('out{} -> inner{}' .format(id(node),  id(succ)))

        for node in self.leafs:
            if node == None: continue
            if id(node) not in definednodes:
                gennode(node)
                genedges(node)
        for node in self.pattern2node.values():
            if id(node) not in definednodes:
                gennode(node)
                genedges(node)

        sb.append('}')
        s = '\n'.join(sb)

        with open('dump_{}.dot'.format(languagename), 'w') as f:
            f.write(s)


class NtGraphBuilder(pattern.PatternTransformer):
    def __init__(self, definelanguage):
        self.definelanguage = definelanguage
        self.pattern2node = {}
        self.leafs = []
        self.nt2node = {}
        self.equivalentnts = {}
        self.gnodestack = []
        self.graphnodes = []
        self.leafhole = None
        self.leafnothole = None

    def getleaf(self, kind):
        if kind == NtGraph.Node.LeafHole:
            if self.leafhole == None:
                self.leafhole = NtGraph.Node(NtGraph.Node.LeafHole) 
            return self.leafhole
        else:
            if self.leafnothole == None:
                self.leafnothole = NtGraph.Node(NtGraph.Node.LeafNotHole) 
            return self.leafnothole

    def run(self):
        # first construct graph nodes and collect all standalone non-terminals that are not inside pattern sequence. 
        for nt, ntdef in self.definelanguage.nts.items():
            self.nt2node[nt] = []
            self.equivalentnts[nt] = []
            for pat in ntdef.patterns:
                if isinstance(pat, pattern.PatSequence):
                    node = self.getleaf(NtGraph.Node.LeafNotHole) if len(pat.seq) == 0 else NtGraph.Node(NtGraph.Node.Sequence)
                    self.nt2node[nt].append(node)
                    self.pattern2node[repr(pat)] = node
                if isinstance(pat, pattern.BuiltInPat):
                    kind = NtGraph.Node.LeafHole if pat.kind == pattern.BuiltInPatKind.Hole else NtGraph.Node.LeafNotHole
                    node = self.getleaf(kind)
                    self.nt2node[nt].append(node)
                    self.pattern2node[repr(pat)] = node
                if isinstance(pat, pattern.Nt):
                    self.equivalentnts[nt].append(pat.prefix)
                if isinstance(pat, pattern.InHole):
                    raise CompilationError('in-hole pattern in define-language')


        for nt, ntdef in self.definelanguage.nts.items():
            for pat in ntdef.patterns:
                if isinstance(pat, pattern.PatSequence):
                    for p in pat:
                        gn = self.pattern2node[repr(pat)]
                        self.gnodestack.append(gn)
                        self.transform(p)
                        self.gnodestack.pop()

        return NtGraph(self.pattern2node, self.nt2node, [self.leafhole, self.leafnothole])

    def transformNt(self, node):
        assert isinstance(node, pattern.Nt)
        successors = self.nt2node[node.prefix]
        for nt in self.equivalentnts[node.prefix]:
            successors += self.nt2node[nt]
        outernode = self.gnodestack[-1]
        innernode = NtGraph.InnerNode(outernode)
        outernode.innernodes.append(innernode)
        for succ in successors:
            succ.predecessor_innernodes.append(innernode)
        return node

    def transformPatSequence(self, node):
        assert isinstance(node, pattern.PatSequence)
        prevouternode = self.gnodestack[-1]
        previnnernode = NtGraph.InnerNode(prevouternode)
        prevouternode.innernodes.append(previnnernode)

        outernode = self.getleaf(NtGraph.Node.LeafNotHole) if len(node.seq) == 0 else NtGraph.Node(NtGraph.Node.Sequence)
        outernode.predecessor_innernodes.append(previnnernode)

        self.gnodestack.append(outernode)
        for pat in node.seq:
            self.transform(pat)
        self.gnodestack.pop() 
        return node

    def transformRepeat(self, node):
        assert isinstance(node, pattern.Repeat)
        prevouternode = self.gnodestack[-1]
        previnnernode = NtGraph.InnerNode(prevouternode)
        prevouternode.innernodes.append(previnnernode)

        outernode = NtGraph.Node(NtGraph.Node.Repeat)
        outernode.predecessor_innernodes.append(previnnernode)

        self.gnodestack.append(outernode)
        self.transform(node.pat)
        self.gnodestack.pop() 
        return node

    def transformInHole(self, node):
        raise CompilationError('in-hole pattern in define-language')

    def transformBuiltInPat(self, node):
        assert isinstance(node, pattern.BuiltInPat)
        prevouternode = self.gnodestack[-1]
        previnnernode = NtGraph.InnerNode(prevouternode)
        prevouternode.innernodes.append(previnnernode)

        kind = NtGraph.Node.LeafHole if node.kind == pattern.BuiltInPatKind.Hole else NtGraph.Node.LeafNotHole
        outernode = self.getleaf(kind)
        outernode.predecessor_innernodes.append(previnnernode)
        return node

class DefineLanguage_HoleReachabilitySolver:
    def __init__(self, definelanguage, ntgraph):
        assert isinstance(definelanguage, tlform.DefineLanguage)
        assert isinstance(ntgraph, NtGraph)
        self.definelanguage = definelanguage
        self.ntgraph = ntgraph

    def run(self):
        hashole = False
        for leaf in self.ntgraph.leafs:
            if leaf != None:
                if leaf.kind == NtGraph.Node.LeafHole:
                    hashole = True

        if not hashole:
            for ntdef in self.definelanguage.nts.values():
                ntdef.nt.addmetadata(pattern.PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
            return

        for leaf in self.ntgraph.leafs:
            if leaf != None:
                self.bfs([leaf])

        calculatednts = {}
        def calcnt(nt, ntdef):
            if nt in calculatednts:
                return calculatednts[nt]
            ntgraphnodes = self.ntgraph.nt2node[nt]
            ntmin, ntmax = NumberOfHoles.Many, NumberOfHoles.Zero
            for pat in ntdef.patterns:
                try:
                    node = self.ntgraph.pattern2node[repr(pat)]
                    pmin, pmax = node.min_numberof_holes, node.max_numberof_holes
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

    def bfs(self, queue):
        while len(queue) != 0:
            outernode = queue.pop(0)
            for pred in outernode.predecessor_innernodes:
                if pred.parent == outernode:
                    # update links to myself first.  For example while processing (E hole)
                    # Initially after processing hole (E hole) has (one, one) number of holes.
                    # That is incorrect as we can have expressions like ((E hole) hole) hence
                    # we update min-max values locally first.
                    pred.update(outernode.min_numberof_holes, outernode.max_numberof_holes)
                    pred.parent.update()

            for pred in outernode.predecessor_innernodes:
                if pred.parent != outernode:
                    pred.update(outernode.min_numberof_holes, outernode.max_numberof_holes)
                    if pred.parent.update():
                        if pred.parent not in queue:
                            queue.append(pred.parent)

