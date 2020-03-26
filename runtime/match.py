import copy
from term import TermKind, Sequence

class Binding:
    def __init__(self, var):
        self.var = var
        self.buf = []

    def add(self, value):
        # if stack is empty, add value
        # if stack is not empty and not a compoundarray, raise exception
        # if stack is not empty and is compoundarray, add value.
        if len(self.buf) == 0:
            self.buf.append(value)
        else:
            if self.buf[-1].kind() != TermKind.Sequence:
                assert False, 'not compound array'
            else:
                self.buf[-1].append(value)

    def increasedepth(self):
        # preceding element must be compound array, raise exception otherwise.
        if len(self.buf) != 0:
            if self.buf[-1].kind() != TermKind.Sequence: 
                assert False, 'previous element is not compoundarray'
        self.buf.append( Sequence([]) )

    def decreasedepth(self):
        # if stack is empty, raise exception
        # if stack size is 1 and topmost element is not compoundarray raise exception.
        # if stack size is 1 and topmost element is compoundarray do nothing.
        # if stack size > 1, pop topmost element and append it to element below. ( works because increasedepth must be called beforehand)
        if len(self.buf) == 0: 
            assert False, 'empty stack'
        if len(self.buf) == 1 :
            if self.buf[-1].kind() != TermKind.Sequence: 
                assert False, 'previous element is not compoundarray'
            else:
                return
        top = self.buf.pop()
        self.buf[-1].append(top)

    def getbinding(self):
        if len(self.buf) != 1:
            assert False, 'something went wrong'
        return self.buf[0]

class Match:
    def __init__(self, identifiers): 
        self.bindings = {} 
        for ident in identifiers:
            self.bindings[ident] = Binding(ident)

    def create_binding(self, var):
        assert var not in self.bindings.keys()
        self.bindings[var] = Binding(var)

    def increasedepth(self, var):
        self.bindings[var].increasedepth()

    def decreasedepth(self, var):
        self.bindings[var].decreasedepth()

    def addtobinding(self, var, val):
        self.bindings[var].add(val)

    def removebinding(self, var):
        self.bindings.pop(var, None)

    def comparekeys(self, var1, var2):
        binding1 = self.bindings[var1]
        binding2 = self.bindings[var2]
        assert len(binding1.buf) > 0
        assert len(binding2.buf) > 0
        return binding1.buf[-1] == binding2.buf[-1]

    def copy(self):
        a = copy.deepcopy(self.bindings)
        m = Match([])
        m.bindings = a
        return m

    def __repr__(self):
        b = []
        for key, val in self.bindings.items():
            b.append('(bind {} {})'.format(key, repr(val.getbinding())))
        if len(b) == 0:
            return '(match ())'
        return '(match (list {}))'.format('\n'.join(b))

def print_match_list(matches):
    if len(matches) == 0:
        print('#f')
        return
    m = []
    for match, _, _ in matches:
        m.append(repr(match))
    print(('(list {})'.format(' '.join(m))))
