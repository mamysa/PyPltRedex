
import enum

class LitKind(enum.Enum):
    Integer = 0
    Decimal = 1
    String  = 2
    Boolean = 3

class BuiltInPatKind(enum.Enum):
    Number = 'number'
    VariableNotOtherwiseDefined = 'variable-not-otherwise-mentioned'


class Lit:
    def __init__(self, lit, kind):
        assert isinstance(kind, LitKind)
        self.lit  = lit
        self.kind = kind

    def __repr__(self):
        return 'Lit({}, {})'.format(self.lit, self.kind)


class Nt:
    def __init__(self, ntsym, patterns):
        self.ntsym = ntsym
        self.patterns = patterns

class Pat:
    def __init__(self, pat):
        self.pat = pat 

    def exchange(self):
        pass

class NtRef:
    def __init__(self, ntsym):
        self.ntsym = ntsym

class UnresolvedSym:
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

class Repeat:
    def __init__(self, pat):
        #assert isinstance(pat, Pat)
        self.pat = pat

    def __repr__(self):
        return 'Repeat({})'.format(self.pat)

class BuiltInPat:
    def __init__(self, kind, sym, aux=None):
        assert isinstance(kind, BuiltInPatKind)
        self.kind = kind
        self.sym = sym
        self.aux = aux 

    def __repr__(self):
        return 'BuiltInPat({}, {})'.format(self.kind, self.sym)

class DefineLanguage:
    def __init__(self, nts):
        pass

    



