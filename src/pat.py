import enum
import copy
from functools import reduce
import operator

class LitKind(enum.Enum):
    Integer = 0
    Decimal = 1
    String  = 2
    Boolean = 3
    Variable = 4

class BuiltInPatKind(enum.Enum):
    Number = 'number'
    VariableNotOtherwiseDefined = 'variable-not-otherwise-mentioned'
    VariableExcept = 'variable-except'
    Hole = 'hole'

class Pat:
    def __init__(self):
        self._metadata = {}

    def addmetadata(self, metadata):
        assert isinstance(metadata, PatMetadata)
        self._metadata[type(metadata)] = metadata
        return self

    def removemetadata(self, typ):
        assert typ in self._metadata
        del self._metadata[typ]

    def getmetadata(self, typ):
        return self._metadata[typ]

    def copymetadatafrom(self, node):
        assert isinstance(node, Pat)
        self._metadata = copy.copy(node._metadata)
        return self

class Lit(Pat):
    """
    Represents all literals in the pattern such as numbers, strings, etc.
    """
    def __init__(self, lit, kind):
        assert isinstance(kind, LitKind)
        super().__init__()
        self.lit  = lit
        self.kind = kind

    def __repr__(self):
        return 'Lit({}, {})'.format(self.lit, self.kind)


    def __eq__(self, other):
        if isinstance(other, Lit):
            return self.kind == other.kind and \
                    self.lit == other.lit
        return False

class PatSequence(Pat):
    def __init__(self, seq):
        super().__init__()
        self.seq = seq 

    def exchange(self):
        pass

    def get_number_of_nonoptional_matches_between(self, head, tail):
        """
        Returns a number of patterns excluding repetitions.
        Args:
        head - element to start counting from.
        tail - element to count until, excluding. 
        """
        assert head <  len(self.seq), 'out of bounds'
        assert tail <= len(self.seq), 'out of bounds'
        num_nonoptional = 0
        for i in range(head, tail):
            if not isinstance(self.seq[i], Repeat) and not isinstance(self.seq[i], CheckConstraint):
                num_nonoptional += 1
        return num_nonoptional

    def get_number_of_optional_matches(self):
        return len(self.seq) - self.get_number_of_nonoptional_matches_between(0, len(self.seq))

    def get_nonoptional_matches(self):
        nonoptional = []
        for pat in self.seq:
            if not isinstance(pat, Repeat) and not isinstance(pat, CheckConstraint):
                nonoptional.append(pat)
        return nonoptional 

    def __len__(self):
        return len(self.seq)

    def __repr__(self):
        return 'PatSequence({})'.format(self.seq)

    def __iter__(self):
        return iter(self.seq)

    def __getitem__(self, key):
        return self.seq[key]

    def __eq__(self, other):
        if isinstance(other, PatSequence):
            if len(self.seq) == len(other.seq):
                return reduce(operator.and_, [a == b for a, b in zip(self.seq, other.seq)], True)
        return False


class Nt(Pat):
    """
    reference to non-terminal
    """
    def __init__(self, prefix, sym):
        super().__init__()
        self.prefix = prefix
        self.sym = sym

    def __repr__(self):
        return 'Nt({}, {})'.format(self.prefix, self.sym)

    def __eq__(self, other):
        if isinstance(other, Nt):
            return self.prefix == other.prefix and self.sym == other.sym
        return False

class UnresolvedSym(Pat):
    def __init__(self, prefix, sym):
        """
        Keyword arguments:
        prefix -- non-terminal symbol. (i.e. n in n_1)
        sym    -- symbol as parsed. (i.e. n_1)
        """
        super().__init__()
        self.prefix = prefix
        self.sym = sym

    def __repr__(self):
        return 'UnresolvedSym({})'.format(self.sym)

    def __eq__(self, other):
        if isinstance(other, UnresolvedSym):
            return self.prefix == other.prefix and self.sym == other.sym
        return False

class RepeatMatchMode(enum.IntEnum):
    NonDetermininstic = 0
    Deterministic = 1

class Repeat(Pat):
    def __init__(self, pat, mode=RepeatMatchMode.NonDetermininstic):
        assert isinstance(pat, Pat)
        super().__init__()
        self.pat = pat
        self.matchmode = mode

    def __repr__(self):
        return 'Repeat({}, {})'.format(self.pat, self.matchmode)

    def __eq__(self, other):
        if isinstance(other, Repeat):
            return self.pat == other.pat and  \
                   self.matchmode == other.matchmode
        return False

class BuiltInPat(Pat):
    def __init__(self, kind, prefix, sym, aux=None):
        assert isinstance(kind, BuiltInPatKind)
        super().__init__()
        self.kind = kind
        self.prefix = prefix
        self.sym = sym
        self.aux = aux 

    def __repr__(self):
        if self.aux:
            return 'BuiltInPat({}, {}, {})'.format(self.kind, self.sym, repr(self.aux))
        return 'BuiltInPat({}, {})'.format(self.kind, self.sym)

    def __eq__(self, other):
        if isinstance(other, BuiltInPat):
            return self.kind == other.kind     and \
                   self.prefix == other.prefix and \
                   self.sym == other.sym       and \
                   self.aux == other.aux
        return False

class InHole(Pat):
    def __init__(self, pat1, pat2):
        assert isinstance(pat1, Pat)
        assert isinstance(pat2, Pat)
        super().__init__()
        self.pat1 = pat1
        self.pat2 = pat2
    
    def __repr__(self):
        return 'InHole({}, {})'.format(self.pat1, self.pat2)

    def __eq__(self, other):
        if isinstance(other, InHole):
            return self.pat1 == other.pat1 and \
                   self.pat2 == other.pat2
        return False

class CheckConstraint(Pat):
    def __init__(self, sym1, sym2):
        super().__init__()
        self.sym1 = sym1 
        self.sym2 = sym2 

    def __repr__(self):
        return 'CheckConstraint({} == {})'.format(self.sym1, self.sym2)

    def __eq__(self):
        if isinstance(other, CheckConstraint):
            return self.sym1 == other.sym1 and \
                   self.sym2 == other.sym2
        return False

class PatternTransformer:
    """
    AstNode to AstNode transformer. Returns tree equal to the one being transformed. (i.e. does absolutely nothing!)
    Override required methods to do something useful.
    """
    def transform(self, element):
        assert isinstance(element, Pat)
        method_name = 'transform' + element.__class__.__name__
        method_ref = getattr(self, method_name)
        return method_ref(element)

    def transformPatSequence(self, node):
        assert isinstance(node, PatSequence)
        seq = []
        for n in node.seq:
            seq.append(self.transform(n))
        return PatSequence(seq).copymetadatafrom(node)

    def transformRepeat(self, node):
        assert isinstance(node, Repeat)
        return Repeat(self.transform(node.pat), node.matchmode).copymetadatafrom(node)

    def transformInHole(self, node):
        assert isinstance(node, InHole)
        pat1 = self.transform(node.pat1)
        pat2 = self.transform(node.pat2)
        return InHole(pat1, pat2).copymetadatafrom(node) 

    def transformBuiltInPat(self, node):
        assert isinstance(node, BuiltInPat)
        return node

    def transformUnresolvedSym(self, node):
        return node

    def transformNt(self, node):
        return node

    def transformLit(self, node):
        return node


# --- pattern nodes may store additional info such as line numbers, etc.
# Some of this metadata will be added during analysis process. 
# TODO see how this will interact with pattern optimization ...
class PatMetadata:
    pass

# --- stores all the assignable symbols (i.e. those in Match) seen in the
# pattern
class PatAssignableSymbols(PatMetadata):
    def __init__(self, syms):
        super().__init__()
        self.syms = syms

# stores mapping of sym->ellipsis depth. To be used when generating terms.
class PatAssignableSymbolDepths(PatMetadata):
    def __init__(self, syms):
        super().__init__()
        self.syms = syms

class PatNumHoles(PatMetadata):
    def __init__(self, numholesmin, numholesmax):
        super().__init__()
        self.numholesmin = numholesmin
        self.numholesmax = numholesmax

    def __repr__(self):
        return '({}, {})'.format(self.numholesmin, self.numholesmax)

    def __eq__(self, other):
        if isinstance(other, PatNumHoles):
            return self.numholesmin == other.numholesmin \
               and self.numholesmax == other.numholesmax

