import src.pat as pattern
import src.rpython as rpy
class TermMethodTable:
    Kind = 'kind'
    Value = 'value'
    Length = 'length'
    Get = 'get'
    ReplaceWith = 'replacewith'
    CopyToRoot  = 'copy'

class TermHelperFuncs:
    CopyPathAndReplaceLast = 'copy_path_and_replace_last'

class MatchHelperFuncs:
    CombineMatches = 'combine_matches'

class MatchMethodTable:
    AddToBinding ='addtobinding'
    AddKey = 'create_binding'
    IncreaseDepth = 'increasedepth'
    DecreaseDepth = 'decreasedepth'
    Copy = 'copy'
    CompareKeys = 'comparekeys'
    RemoveKey   = 'removebinding'
    GetBinding = 'getbinding'

class TermKind:
    Variable = 0
    Integer  = 1
    Sequence = 2 
    Hole = 3

# we will remove this eventually, will annotate patterns with assignable symbols instead!
class RetrieveBindableElements(pattern.PatternTransformer):
    def __init__(self):
        self.bindables = []

    def get_rpylist(self):
        bindables = set(map(lambda x: x.sym,   self.bindables))
        bindables = map(lambda x: rpy.PyString(x), bindables)
        return rpy.PyList(*bindables)

    def as_set(self):
        return set(map(lambda x: x.sym, self.bindables))

    def transformNt(self, node):
        self.bindables.append(node)
        return node

    def transformCheckConstraint(self, node):
        return node

    def transformBuiltInPat(self, node):
        assert isinstance(node, pattern.BuiltInPat)
        if node.kind == pattern.BuiltInPatKind.InHole:
            pat1, pat2 = node.aux
            rbe1 = RetrieveBindableElements(); rbe1.transform(pat1)
            rbe2 = RetrieveBindableElements(); rbe2.transform(pat2)
            self.bindables += rbe1.bindables
            self.bindables += rbe2.bindables
            return node

        if node.kind != pattern.BuiltInPatKind.Hole: 
            self.bindables.append(node)
        return node
