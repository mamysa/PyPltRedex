import enum 
import copy

from src.model.astbase import ASTBase 

class TermLiteralKind:
    Variable = 0
    Integer = 1
    Float = 2
    List = 3
    Hole = 4
    String = 5
    Boolean = 6

class TermAttribute(enum.Enum):
    MatchRead = 'MatchRead'
    InArg   = 'InArg'
    ForEach = 'ForEach'

class Term(ASTBase):
    def __init__(self):
        ASTBase.__init__(self)

class InHole(Term):
    def __init__(self, term1, term2):
        super().__init__()
        self.term1 = term1
        self.term2 = term2

    def __repr__(self):
        return 'InHole({}, {}, {})'.format(self.term1, self.term2, self._attributes)

class TermLiteral(Term):
    def __init__(self, kind, value):
        super().__init__()
        self.kind = kind
        self.value = value

    def __repr__(self):
        if self.kind == TermLiteralKind.List: 
            return '({})'.format(' '.join(map(repr, self.value)))
        return '{}'.format(self.value)

class TermSequence(Term):
    def __init__(self, seq):
        super().__init__()
        self.seq = seq 

    def __repr__(self):
        return 'TermSequence({}, {})'.format(self.seq, self._attributes)

class Repeat(Term):
    def __init__(self, term):
        assert isinstance(term, Term), 'expecte {}'.format(type(term))
        super().__init__()
        self.term = term 

    def __repr__(self):
        return 'Repeat({}, {})'.format(self.term, self._attributes)

class UnresolvedSym(Term):
    def __init__(self, sym):
        """
        Keyword arguments:
        sym    -- symbol as parsed. (i.e. n_1)
        """
        super().__init__()
        self.sym = sym

    def __repr__(self):
        return 'UnresolvedSym({})'.format(self.sym)

class PatternVariable(Term):
    def __init__(self, sym):
        super().__init__()
        self.sym = sym

    def __repr__(self):
        return 'PatternVariable({}, {})'.format(self.sym, self._attributes)

class PyCallInsertionMode(enum.Enum):
    Append = 0
    Extend = 1

class PyCall(Term):
    def __init__(self, mode, functionname, termargs):
        assert isinstance(mode, PyCallInsertionMode)
        super().__init__()
        self.mode = mode
        self.functionname = functionname
        self.termargs = termargs 

    def __repr__(self):
        return 'PythonFunctionCall({}, {}, {}, {})'.format(self.mode, self.functionname, self.termargs, self._attributes)

class MetafunctionApplication(Term):
    def __init__(self, metafunctionname, termtemplate):
        super().__init__()
        self.metafunctionname = metafunctionname
        self.termtemplate = termtemplate

    def __repr__(self):
        return 'MetafunctionApplication({}, {}, {})'.format(self.metafunctionname, self.termtemplate, self._attributes)

class TermTransformer:
    def transform(self, element):
        assert isinstance(element, Term)
        method_name = 'transform' + element.__class__.__name__
        method_ref = getattr(self, method_name)
        return method_ref(element)

    def transformTermSequence(self, node):
        assert isinstance(node, TermSequence)
        seq = []
        for n in node.seq:
            seq.append(self.transform(n))
        return TermSequence(seq).copyattributesfrom(node)

    def transformRepeat(self, node):
        assert isinstance(node, Repeat)
        return Repeat(self.transform(node.term)).copyattributesfrom(node)

    def transformUnresolvedSym(self, node):
        return node

    def transformPatternVariable(self, node):
        return node

    def transformInHole(self, inhole):
        t1 = self.transform(inhole.term1)
        t2 = self.transform(inhole.term2)
        return InHole(t1, t2).copyattributesfrom(inhole)

    def transformPyCall(self, pycall):
        assert isinstance(pycall, PyCall)
        ntermargs = []
        for termtemplate in pycall.termargs:
            ntermargs.append( self.transform(termtemplate) )
        return PyCall(pycall.mode, pycall.functionname, ntermargs).copyattributesfrom(pycall)

    def transformTermLiteral(self, node):
        return node

    def transformMetafunctionApplication(self, node):
        return node


