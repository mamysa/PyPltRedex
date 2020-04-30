import enum 
import copy

class TermLiteralKind:
    Integer = 0
    Variable = 1
    Hole = 2
    List = 3


class TermAttribute(enum.Enum):
    FunctionName = 'FunctionName'
    InArg   = 'InArg'
    ForEach = 'ForEach'

class Term:
    def __init__(self):
        self._attributes = {} 

    def addattribute(self, key, val):
        assert isinstance(key, TermAttribute)
        if key not in self._attributes:
            self._attributes[key] = []
        self._attributes[key].append(val)
        return self

    def getattribute(self, key):
        return self._attributes[key]

    def copyattributesfrom(self, node):
        assert isinstance(node, Term)
        self._attributes = copy.copy(node._attributes)
        return self


class TermLiteral(Term):
    def __init__(self, kind, value):
        self.kind = kind
        self.value = value

    def __repr__(self):
        if self.kind in [TermLiteralKind.Integer, TermLiteralKind.Variable, TermLiteralKind.Hole]: 
            return str(self.value)
        # is a list, 
        return '({})'.format(' '.join(map(repr, self.value)))



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

    def transformTermLiteral(self, node):
        return node
