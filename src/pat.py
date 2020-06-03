import enum
import copy
from functools import reduce

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
    InHole = 'in-hole'

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

    def __len__(self):
        return len(self.seq)

    def __repr__(self):
        return 'PatSequence({})'.format(self.seq)

    def __iter__(self):
        return iter(self.seq)

    def __getitem__(self, key):
        return self.seq[key]

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

class Repeat(Pat):
    def __init__(self, pat):
        assert isinstance(pat, Pat)
        super().__init__()
        self.pat = pat

    def __repr__(self):
        return 'Repeat({})'.format(self.pat)

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

class CheckConstraint(Pat):
    def __init__(self, sym1, sym2):
        super().__init__()
        self.sym1 = sym1 
        self.sym2 = sym2 

    def __repr__(self):
        return 'CheckConstraint({} == {})'.format(self.sym1, self.sym2)

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
        return Repeat(self.transform(node.pat)).copymetadatafrom(node)

    def transformBuiltInPat(self, node):
        assert isinstance(node, BuiltInPat)
        if node.kind == BuiltInPatKind.InHole:
            node.aux = (self.transform(node.aux[0]), self.transform(node.aux[1]))
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








