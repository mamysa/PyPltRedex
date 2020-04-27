import enum
from functools import reduce

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
    Hole = 'hole'
    InHole = 'in-hole'

class Pat(AstNode):
    """
    Represents all pattern expressions.
    """
    def __init__(self):
        super().__init__()

    def collect_bindable_syms(self): ## should be a visitor.
        return set([])

class Match(AstNode):
    def __init__(self, bindings):
        self.bindings = bindings

    def __repr__(self):
        return 'Match({})'.format(repr(self.bindings))

class MatchEqual(AstNode):
    def __init__(self, redexmatch, list_of_matches, equality=True):
        self.redexmatch = redexmatch
        self.list_of_matches = list_of_matches

    def __repr__(self):
        return 'MatchEqual({} {})'.format(self.redexmatch, self.list_of_matches)

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
            if not isinstance(self.seq[i], Repeat) and not isinstance(self.seq[i], CheckConstraint):
                num_nonoptional += 1
        return num_nonoptional

    def collect_bindable_syms(self):
        return reduce(lambda s, pat: s.union(pat.collect_bindable_syms()), self.seq, set([])) 

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

    def collect_bindable_syms(self):
        return set([self.sym])

    def __repr__(self):
        return 'Nt({}, {})'.format(self.prefix, self.sym)

class NtDefinition(AstNode):
    def __init__(self, nt, patterns):
        assert isinstance(nt, Nt)
        self.nt = nt
        self.patterns = patterns

    def get_nt_sym(self):
        return self.nt.sym

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

    def collect_bindable_syms(self):
        assert False, 'unreachable'

    def __repr__(self):
        return 'UnresolvedSym({})'.format(self.sym)

class Repeat(Pat):
    def __init__(self, pat):
        assert isinstance(pat, Pat)
        self.pat = pat

    def collect_bindable_syms(self):
        return self.pat.collect_bindable_syms()

    def __repr__(self):
        return 'Repeat({})'.format(self.pat)

class BuiltInPat(Pat):
    def __init__(self, kind, prefix, sym, aux=None):
        assert isinstance(kind, BuiltInPatKind)
        self.kind = kind
        self.prefix = prefix
        self.sym = sym
        self.aux = aux 

    def collect_bindable_syms(self):
        if self.kind == BuiltInPatKind.InHole:
            s0 = self.aux[0].collect_bindable_syms()
            s1 = self.aux[1].collect_bindable_syms()
            return s0.union(s1)
        return set([self.sym])

    def __repr__(self):
        if self.aux:
            return 'BuiltInPat({}, {}, {})'.format(self.kind, self.sym, repr(self.aux))
        return 'BuiltInPat({}, {})'.format(self.kind, self.sym)

class CheckConstraint(Pat):
    def __init__(self, sym1, sym2):
        self.sym1 = sym1 
        self.sym2 = sym2 

    def __repr__(self):
        return 'CheckConstraint({} == {})'.format(self.sym1, self.sym2)


class TermLet(AstNode):
    def __init__(self, variable_assignments, template):
        self.variable_assignments = variable_assignments
        self.template = template

    def __repr__(self):
        return 'TermLet({}, {})'.format(repr(self.variable_assignments), repr(self.template))

class DefineLanguage(AstNode):
    def __init__(self, name, ntdefs):
        self.name = name 
        self.nts = {} 

        # non-terminal-definitions must not contain underscores and each symbol can only appear once.
        for ntdef in ntdefs:
            ntsym = ntdef.get_nt_sym()
            if ntsym.find('_') != -1:
                raise ValueError('define-language: cannot use _ in a non-terminal name {}'.format(ntsym))

            if ntsym in self.nts.keys():
                raise ValueError('define-language: same non-terminal defined twice: {}'.format(ntsym))
            self.nts[ntsym] = ntdef



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
    def __init__(self, definelanguage, redexmatches, matchequals, termlet):
        self.definelanguage = definelanguage
        self.redexmatches = redexmatches
        self.matchequals = matchequals
        self.termlet = termlet

    def __repr__(self):
        out = []
        out.append(repr(self.definelanguage))
        for rm in self.redexmatches:
            out.append(repr(rm))
        for me in self.matchequals:
            out.append(repr(me))
        for tl in self.termlet:
            out.append(repr(tl))
        return "\n".join(out)

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

    def transformMatch(self, match):
        return match
