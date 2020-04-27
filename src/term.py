class TermLiteralKind:
    Integer = 0
    Variable = 1
    Hole = 2
    List = 3

class TermLiteral:
    def __init__(self, kind, value):
        self.kind = kind
        self.value = value

    def __repr__(self):
        if self.kind in [TermLiteralKind.Integer, TermLiteralKind.Variable, TermLiteralKind.Hole]: 
            return str(self.value)
        # is a list, 
        return '({})'.format(' '.join(map(repr, self.value)))


class CompiledTerm:
    pass

class TermSequence(CompiledTerm):
    def __init__(self, seq):
        self.seq = seq 

    def __repr__(self):
        return 'TermSequence({})'.format(self.seq)

class Repeat(CompiledTerm):
    def __init__(self, term):
        assert isinstance(term, CompiledTerm )
        self.term = term 

    def __repr__(self):
        return 'Repeat({})'.format(self.term)

class UnresolvedSym(CompiledTerm):
    def __init__(self, sym):
        """
        Keyword arguments:
        sym    -- symbol as parsed. (i.e. n_1)
        """
        self.sym = sym

    def __repr__(self):
        return 'UnresolvedSym({})'.format(self.sym)

class PatternVariable(CompiledTerm):
    def __init__(self, sym):
        self.sym = sym

    def __repr__(self):
        return 'PatternVariable({})'.format(self.sym)
