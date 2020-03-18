
import enum

class AstNode:
    """
    Parent class of all Racket expressions.
    """
    pass
    """
    def __init__(self):
        self.__frozen = True  
    
    # __frozen and __setattr__ are silly hacks to make immutable objects work.
    def __setattr__(self, name, value):
        if getattr(self, '_AstNode__frozen', False):
            if name != '_annotations':
                raise AttributeError('modifying immutable object! ' + name)
        super().__setattr__(name, value)

    def copyattributesfrom(self, node):
        assert isinstance(node, AstNode)
        self._annotations = copy.copy(node._annotations)
        return self
    """

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

class Pat(AstNode):
    """
    Represents all pattern expressions.
    """
    def __init__(self):
        super().__init__()

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
            if not isinstance(self.seq[i], Repeat):
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
        self.prefix = prefix
        self.sym = sym

    def __repr__(self):
        return 'Nt({}, {})'.format(self.prefix, self.sym)

class NtDefinition(Pat):
    def __init__(self, nt, patterns):
        assert isinstance(nt, Nt)
        self.nt = nt
        self.patterns = patterns

    def __repr__(self):
        return 'NtDefinition({}, {})'.format(repr(self.nt), repr(self.patterns))



class UnresolvedSym(Pat):
    def __init__(self, prefix, sym):
        """
        Keyword arguments:
        prefix -- non-terminal symbol. (i.e. n in n_1)
        sym    -- symbol as parsed. (i.e. n_1)
        """
        self.prefix = prefix
        self.sym = sym

    def __repr__(self):
        return 'UnresolvedSym({})'.format(self.sym)

class Repeat(Pat):
    def __init__(self, pat):
        assert isinstance(pat, Pat)
        self.pat = pat

    def __repr__(self):
        return 'Repeat({})'.format(self.pat)

class BuiltInPat(Pat):
    def __init__(self, kind, prefix, sym, aux=None):
        assert isinstance(kind, BuiltInPatKind)
        self.kind = kind
        self.prefix = prefix
        self.sym = sym
        self.aux = aux 

    def __repr__(self):
        if self.aux:
            return 'BuiltInPat({}, {}, {})'.format(self.kind, self.sym, repr(self.aux))
        return 'BuiltInPat({}, {})'.format(self.kind, self.sym)

class DefineLanguage(AstNode):
    def __init__(self, name, nts):
        self.name = name 
        self.nts = nts

    def ntsyms(self):
        return set(self.nts.keys())

    def __repr__(self):
        return 'DefineLanguage({}, {})'.format(self.name, self.nts)


class RedexMatch(AstNode):
    def __init__(self, languagename, pat, termstr):
        self.languagename = languagename
        self.pat = pat
        self.termstr = termstr 

    def __repr__(self):
        return 'RedexMatch({}, {}, {})'.format(self.languagename, repr(self.pat), self.termstr)

class Module(AstNode):
    def __init__(self, definelanguage, redexmatches):
        self.definelanguage = definelanguage
        self.redexmatches = redexmatches

class PatternTransformer:
    """
    AstNode to AstNode transformer. Returns tree equal to the one being transformed. (i.e. does absolutely nothing!)
    Override required methods to do something useful.
    """
    def transform(self, element):
        assert isinstance(element, AstNode)
        method_name = 'transform' + element.__class__.__name__
        method_ref = getattr(self, method_name)
        return method_ref(element)

    def transformPatSequence(self, node):
        assert isinstance(node, PatSequence)
        seq = []
        for node in node.seq:
            seq.append(self.transform(node))
        return PatSequence(seq)

    def transformRepeat(self, node):
        assert isinstance(node, Repeat)
        return Repeat(self.transform(node.pat))

    def transformBuiltInPat(self, node):
        return node

    def transformUnresolvedSym(self, node):
        return node

    def transformNt(self, node):
        return node

    def transformLit(self, node):
        return node
