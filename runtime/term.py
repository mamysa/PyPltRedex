import copy 

class TermKind:
    Variable = 0
    Integer  = 1
    Float = 2
    Sequence = 3 
    Hole = 4 
    String = 5
    Boolean = 6

class Term:
    def __init__(self, kind):
        self.__kind = kind

    def kind(self):
        return self.__kind

    def append(self, term):
        raise Exception('unsupported operation')

class Integer(Term):
    def __init__(self, value):
        assert isinstance(value, int) 
        Term.__init__(self, TermKind.Integer)
        self.__value = value

    def tostring(self):
        return '%d' % self.__value

    def value(self):
        return self.__value

    def equals(self, other):
        if isinstance(other, Integer):
            return self.value() == other.value()
        return False

    def shallowcopy(self):
        return Integer(self.__value)

    def deepcopy(self):
        return Integer(self.__value)

class Float(Term):
    def __init__(self, value):
        assert isinstance(value, float) 
        Term.__init__(self, TermKind.Float)
        self.__value = value
        
    def tostring(self):
        return '%f' % self.__value

    def value(self):
        return self.__value

    def equals(self, other):
        if isinstance(other, Float):
            return abs(self.value() - other.value()) <= 0.001
        return False

    def shallowcopy(self):
        return Float(self.__value)

    def deepcopy(self):
        return Float(self.__value)

class String(Term):
    def __init__(self, value):
        assert isinstance(value, str) 
        Term.__init__(self, TermKind.String)
        self.__value = value

    def value(self):
        return self.__value

    def tostring(self):
        return self.__value

    def equals(self, other):
        if isinstance(other, String):
            return self.value() == other.value()
        return False

    def shallowcopy(self):
        return String(self.__value)

    def deepcopy(self):
        return String(self.__value)

class Boolean(Term):
    def __init__(self, value):
        assert isinstance(value, str) 
        Term.__init__(self, TermKind.Boolean)
        self.__value = value

    def value(self):
        return self.__value

    def tostring(self):
        return self.__value

    def equals(self, other):
        if isinstance(other, Boolean):
            return self.value() == other.value()
        return False

    def shallowcopy(self):
        return Boolean(self.__value)

    def deepcopy(self):
        return Boolean(self.__value)

class Variable(Term):
    def __init__(self, value):
        assert isinstance(value, str) 
        Term.__init__(self, TermKind.Variable)
        self.__value = value

    def value(self):
        return self.__value

    def tostring(self):
        return self.__value

    def equals(self, other):
        if isinstance(other, Variable):
            return self.value() == other.value()
        return False

    def shallowcopy(self):
        return Variable(self.__value)

    def deepcopy(self):
        return Variable(self.__value)

class Hole(Term):
    def __init__(self):
        Term.__init__(self, TermKind.Hole)

    def tostring(self):
        return 'hole'

    def equals(self, other):
        return isinstance(other, Hole)

    def shallowcopy(self):
        return Hole()

    def deepcopy(self):
        return Hole()

class Sequence(Term):
    def __init__(self, seq):
        Term.__init__(self, TermKind.Sequence)
        self.seq = seq

    def get(self, key):
        return self.seq[key]

    def append(self, val):
        self.seq.append(val)

    def length(self):
        return len(self.seq)

    def tostring(self):
        string = ''
        if len(self.seq) > 0:
            string = ''
            for i in range(len(self.seq) - 1):
                elem = self.seq[i]
                string = string + elem.tostring() + ' '
            string = string + self.seq[len(self.seq)-1].tostring()
        return '(%s)' % string
    
    def shallowcopy(self):
        nseq = [] * len(self.seq)
        for i, elem in enumerate(self.seq):
            nseq.append(elem)
        return Sequence(nseq)

    def deepcopy(self):
        nseq = [] * len(self.seq)
        for i, elem in enumerate(self.seq):
            nseq.append( elem.deepcopy() )
        return Sequence(nseq)

    def equals(self, other):
        if isinstance(other, Sequence):
            if self.length() == other.length():
                for i in range(self.length()):
                    if not self.get(i).equals(other.get(i)):
                        return False
                return True
        return False

def term_is_number(term):
    return isinstance(term, Float) or isinstance(term, Integer)

def term_is_integer(term):
    return isinstance(term, Integer) 

def term_is_float(term):
    return isinstance(term, Float) 

def term_is_natural_number(term):
    return isinstance(term, Integer) and term.value() >= 0

def term_is_hole(term):
    return isinstance(term, Hole) 

def term_is_string(term):
    return isinstance(term, String) 

def term_is_boolean(term):
    return isinstance(term, Boolean) 

def consume_literal_integer(term, match, head, tail, literal):
    if isinstance(term, Integer) and term.value() == literal:
        return [ (match, head+1, tail) ]
    return []

def consume_literal_float(term, match, head, tail, literal):
    if isinstance(term, Float) and abs(literal - term.value()) < 0.001:
        return [ (match, head+1, tail) ]
    return []

def consume_literal_string(term, match, head, tail, literal):
    if isinstance(term, String) and term.value() == literal:
        return [ (match, head+1, tail) ]
    return []

def consume_literal_boolean(term, match, head, tail, literal):
    if isinstance(term, Boolean) and term.value() == literal:
        return [ (match, head+1, tail) ]
    return []

def consume_variable(term, match, head, tail, literal):
    if isinstance(term, Variable) and term.value() == literal:
        return [ (match, head+1, tail) ]
    return []

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
        parentcopy = parent.shallowcopy()
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


def locatehole(term, path):
    """
    Traverses the term and locates the hole.
    returns: path to the hole.
    """
    assert isinstance(term, Term)
    if term.kind() == TermKind.Hole:
        path.append(term)
        return True
    if term.kind() == TermKind.Sequence:
        path.append(term)
        for i in range(term.length()):
            if locatehole(term.get(i), path):
                return True
        path.pop()
        return False

def plughole(into, term):
    path = []
    locatehole(into, path)
    if len(path) != 0:
        return copy_path_and_replace_last(path, term)
    return into

def asserttermsequal(t1, t2):
    assert isinstance(t1, Term)
    assert isinstance(t2, Term)
    assert t1.equals(t2), 'term %s not equal to %s' % (t1.tostring(), t2.tostring())

def asserttermlistsequal(lst1, lst2):
    if len(lst1) == len(lst2):
        for i, t in enumerate(lst1):
            asserttermsequal(t, lst2[i])
        return
    assert False, 'lengths of lists do not match'

def aretermsequalpairwise(terms):
    if len(terms) == 1:
        return True
    for i in range(len(terms) - 1):
        t1, t2 = terms[i], terms[i+1]
        if not t1.equals(t2):
            return False 
    return True

def print_term(term):
    print( term.tostring() )

def print_term_list(terms):
    string = '['
    if len(terms) > 0:
        for i in range(len(terms) - 1):
            term = terms[i]
            string = string + term.tostring() + ', '
        string = string + terms[-1].tostring()
    string = string + ']'
    print(string)

