class TermKind:
    Variable = 0
    Integer  = 1
    Sequence = 2 

class Ast:
    def __init__(self, kind):
        self.__kind = kind

    def kind(self):
        return self.__kind

class Integer(Ast):
    def __init__(self, value):
        super().__init__(TermKind.Integer)
        self.__value = value

    def __repr__(self):
        return 'Integer({})'.format(self.__value)

class Variable(Ast):
    def __init__(self, value):
        super().__init__(TermKind.Variable)
        self.__value = value

    def value(self):
        return self.__value

    def __repr__(self):
        return 'Variable({})'.format(self.__value)

class Sequence(Ast):
    def __init__(self, seq):
        super().__init__(TermKind.Sequence)
        self.seq = seq

    def get(self, key):
        return self.seq[key]

    def append(self, val):
        self.seq.append(val)

    def length(self):
        return len(self.seq)

    def __repr__(self):
        seq = ', '.join(map(repr, self.seq))
        return 'Sequence({})'.format(seq)

