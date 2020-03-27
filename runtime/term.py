class TermKind:
    Variable = 0
    Integer  = 1
    Sequence = 2 
    Hole = 3 

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
        return '{}'.format(self.__value)

    def value(self):
        return self.__value

    def __eq__(self, other):
        if self.kind() == other.kind():
            return self.value() == other.value()
        return False

class Variable(Ast):
    def __init__(self, value):
        super().__init__(TermKind.Variable)
        self.__value = value

    def value(self):
        return self.__value

    def __repr__(self):
        return '{}'.format(self.__value)

    def __eq__(self, other):
        if self.kind() == other.kind():
            return self.value() == other.value()
        return False

class Hole(Ast):
    def __init__(self):
        super().__init__(TermKind.Hole)

    def __repr__(self):
        return 'hole'

    def __eq__(self, other):
        return self.kind() == other.kind()

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
        seq = ' '.join(map(repr, self.seq))
        return '({})'.format(seq)

    def __eq__(self, other):
        if self.kind() == other.kind():
            if self.length() == other.length():
                for i in range(self.length()):
                    if not (self.get(i) == other.get(i)):
                        return False
                return True
        return False
