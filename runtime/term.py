import copy 

class TermKind:
    Root = -1
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
        if other == None:
            return False
        if self.kind() == other.kind():
            return self.value() == other.value()
        return False

    def copy(self):
        return Integer(self.__value)


class Variable(Ast):
    def __init__(self, value):
        super().__init__(TermKind.Variable)
        self.__value = value

    def value(self):
        return self.__value

    def __repr__(self):
        return '{}'.format(self.__value)

    def __eq__(self, other):
        if other == None:
            return False
        if self.kind() == other.kind():
            return self.value() == other.value()
        return False

    def copy(self):
        return Variable(self.__value)

class Hole(Ast):
    def __init__(self):
        super().__init__(TermKind.Hole)

    def __repr__(self):
        return 'hole'

    def __eq__(self, other):
        if other == None:
            return False
        return self.kind() == other.kind()

    def copy(self):
        return Hole()

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

    def copy(self):
        seq = copy.copy(self.seq)
        return Sequence(seq)

    def __eq__(self, other):
        if other == None:
            return False
        if self.kind() == other.kind():
            if self.length() == other.length():
                for i in range(self.length()):
                    if not (self.get(i) == other.get(i)):
                        return False
                return True
        return False


def copy_path_and_replace_last(path, withterm):
    """
    Takes a list of terms (which are assumed to be a valid term - term i is a parent of term i+1)
    copies all terms on path, modifies terms to point to copies, and replaces last term on the path
    with supplied term. 

    returns: root of the term.
    """
    assert len(path) > 0

    if len(path) == 1:
        return withterm 

    i = len(path) - 2
    child = withterm
    while i >= 0:
        parent = path[i]
        parentcopy = parent.copy()
        assert isinstance(parentcopy, Sequence)

        childfound = False 
        for j, node in enumerate(parentcopy.seq):
            if id(node) == id(path[i+1]):
                childfound = True
                parentcopy.seq[j] = child
                break
        if not childfound:
            assert False, 'malformed term'
        child = parentcopy
        i -= 1
    return child
