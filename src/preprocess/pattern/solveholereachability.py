import src.model.tlform as tlform
import src.model.pattern as pattern
import enum

from src.util import CompilationError

# generates graphviz... graph. 

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

        def __repr__(self):
            if self.kind == NtGraph.Node.LeafHole:    label = 'Hole'
            if self.kind == NtGraph.Node.LeafNotHole: label = 'NotHole'
            if self.kind == NtGraph.Node.Sequence:    label = 'Sequence'
            if self.kind == NtGraph.Node.Repeat:      label = 'Repeat'
            return 'NtGraph.Node({}, {})'.format(label, len(self.predecessor_innernodes))

    class InnerNode:
        def __init__(self, parent):
            assert isinstance(parent, NtGraph.Node)
            self.parent = parent
            self.min_numberof_holes = NumberOfHoles.Uninitialized
            self.max_numberof_holes = NumberOfHoles.Uninitialized

        def update(self, nmin, nmax):
            self.min_numberof_holes = nmin
            self.max_numberof_holes = nmax

    def __init__(self, pattern2node, leafs):
        self.pattern2node = pattern2node 
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
                print(node, succ.parent)
                if id(succ.parent) not in definednodes:
                    gennode(succ.parent)
                    genedges(succ.parent)
                edge = (id(node), id(succ))
                if edge not in definededges:
                    definededges.add(edge)
                    sb.append('out{} -> inner{}' .format(id(node),  id(succ)))

        for node in self.leafs:
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
        self.leafhole = NtGraph.Node(NtGraph.Node.LeafHole) 
        self.leafnothole = NtGraph.Node(NtGraph.Node.LeafNotHole) 

    def run(self):
        # first construct graph nodes and collect all standalone non-terminals that are not inside pattern sequence. 
        for nt, ntdef in self.definelanguage.nts.items():
            self.nt2node[nt] = []
            self.equivalentnts[nt] = []
            for pat in ntdef.patterns:
                if isinstance(pat, pattern.PatSequence):
                    node = NtGraph.Node(NtGraph.Node.Sequence)
                    self.nt2node[nt].append(node)
                    self.pattern2node[repr(pat)] = node
                    self.graphnodes.append(node)
                if isinstance(pat, pattern.BuiltInPat):
                    node = self.leafhole if pat.kind == pattern.BuiltInPatKind.Hole else self.leafnothole
                    self.nt2node[nt].append(node)
                    self.pattern2node[repr(pat)] = node
                    self.leafs.append(node)
                if isinstance(pat, pattern.Nt):
                    self.equivalentnts[nt].append(pat.prefix)
                if isinstance(pat, pattern.InHole):
                    raise CompilationError('in-hole pattern in define-language')


        for nt, ntdef in self.definelanguage.nts.items():
            print('nt', nt)
            for pat in ntdef.patterns:
                if isinstance(pat, pattern.PatSequence):
                    for p in pat:
                        gn = self.pattern2node[repr(pat)]
                        self.gnodestack.append(gn)
                        self.transform(p)
                        self.gnodestack.pop()

        return NtGraph(self.pattern2node, [self.leafhole, self.leafnothole])

    def transformNt(self, node):
        assert isinstance(node, pattern.Nt)
        successors = self.nt2node[node.prefix]
        print(node, successors)
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
        print(node)

        outernode = NtGraph.Node(NtGraph.Node.Sequence)
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
        outernode = self.leafhole if node.kind == pattern.BuiltInPatKind.Hole else self.leafnothole
        outernode.predecessor_innernodes.append(previnnernode)
        return node


class DefineLanguage_HoleReachabilitySolver:
    def __init__(self, ntgraph):
        assert isinstance(ntgraph, NtGraph)
        self.ntgraph = ntgraph

    def run(self):
        pass

