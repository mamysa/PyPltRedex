import copy 

class TermKind:
    Variable = 0
    Integer  = 1
    Sequence = 2 
    Hole = 3 

class Ast:
    def __init__(self, kind):
        self.__kind = kind
        # pointer to a parent term (which is is instance of Sequence)
        # Integer refers to offset of the pointer to this term in the sequence.
        # -1 if this node is a root of the term.
        self.parent = None
        self.offset_in_parent = -1

    def set_parent(self, parent, offset):
        self.parent = parent
        self.offset_in_parent = offset

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

    def copy(self):
        new = Integer(self.__value)
        new.parent, new.offset_in_parent = self.parent, self.offset_in_parent
        if new.parent != None:
            return new.parent.copy_and_set_child(new)
        return new


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

    def copy(self):
        new = Variable(self.__value)
        new.parent, new.offset_in_parent = self.parent, self.offset_in_parent
        if new.parent != None:
            return new.parent.copy_and_set_child(new)
        return new


class Hole(Ast):
    def __init__(self):
        super().__init__(TermKind.Hole)

    def __repr__(self):
        return 'hole'

    def __eq__(self, other):
        return self.kind() == other.kind()

    def copy(self):
        new = Hole()
        new.parent, new.offset_in_parent = self.parent, self.offset_in_parent
        if new.parent != None:
            return new.parent.copy_and_set_child(new)
        return new

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
        seq = Sequence(seq)
        seq.parent, seq.offset_in_parent = self.parent, self.offset_in_parent
        if seq.parent != None:
            return seq.parent.copy_and_set_child(seq)
        return seq

    def copy_and_set_child(self, child_to_replace):
        seq = copy.copy(self.seq)
        i = child_to_replace.offset_in_parent
        assert i > -1
        seq[i] = child_to_replace
        seq = Sequence(seq)
        seq.parent, seq.offset_in_parent = self.parent, self.offset_in_parent
        child_to_replace.set_parent(seq, i)
        if seq.parent != None:
            return seq.parent.copy_and_set_child(seq)
        return seq

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
