# needed for implementing Match.equals method. RPython doesn't support sets. 
def string_set_intersection(dict_a, dict_b):
    intersection = {}
    for key in dict_a.keys():
        if key in dict_b:
            intersection[key] = None
    return intersection

def make_string_set(keys):
    stringset = {}
    for k in keys:
        stringset[k] = None
    return stringset

class Binding:
    def __init__(self, var):
        self.var = var
        self.buf = []

    def add(self, value):
        # if stack is empty, add value
        # if stack is not empty and not a compoundarray, raise exception
        # if stack is not empty and is compoundarray, add value to the array.
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
        assert len(self.buf) == 1, 'incomplete match!'
        return self.buf[0]

    def equals(self, other):
        return self.getbinding().equals(other.getbinding())

    def deepcopy(self):
        copyof = Binding(self.var)
        for elem in self.buf:
            copyof.buf.append( elem.deepcopy() )
        return copyof
    
class Match:
    def __init__(self, identifiers=[]): 
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
        return binding1.buf[-1].equals(binding2.buf[-1])

    def getbinding(self, sym):
        return self.bindings[sym].getbinding()

    def equals(self, other):
        if isinstance(other, Match):
            if len(self.bindings) == len(other.bindings):
                lkeys = make_string_set(self.bindings.keys())
                rkeys = make_string_set(other.bindings.keys())
                intersection = string_set_intersection(lkeys, rkeys)
                if len(lkeys) == len(intersection):
                    for key in lkeys:
                        if not self.bindings[key].equals(other.bindings[key]):
                            return False
                    return True
        return False

    def deepcopy(self):
        # import copy
        #a = copy.deepcopy(self.bindings)
        #m = Match([])
        #m.bindings = a
        copyof = Match() 
        for name, binding in self.bindings.items():
            copyof.bindings[name] = binding.deepcopy()
        return copyof

    def tostring(self):
        ## FIXME won't compile under RPython
        string = ''
        if len(self.bindings) > 0:
            for key in self.bindings:
                value = self.bindings[key]
                s = '%s=%s, ' % (key, value.getbinding().tostring())
                string = string + s
        return 'Match(%s)' % string

    def combine_with(self, other):
        assert isinstance(other, Match)
        lkeys = make_string_set(self.bindings.keys())
        rkeys = make_string_set(other.bindings.keys())
        intersection = string_set_intersection(lkeys, rkeys)
        assert len(intersection) == 0
        self.bindings.update(other.bindings)

def combine_matches(match1, match2):
    m1k = make_string_set(match1.bindings.keys())
    m2k = make_string_set(match2.bindings.keys())
    intersection = string_set_intersection(m1k, m2k)
    assert len(intersection) == 0
    nbindings = match1.bindings.copy()   
    nbindings.update(match2.bindings)    
    match = Match([])
    match.bindings = nbindings
    return match

def match_cartesian_product_add_binding_to(matches1, matches2, to, head, tail):
    """
    computes cartesian product between matches in matches1 and matches2. 
    Resulting bindings are added to existing match wth, which is copied beforehand.
    head and tail must be precomputed.
    """
    out = []
    for m1, h1, t1 in matches1:
        for m2, h2, t2 in matches2:
            combined = combine_matches(m1, m2)
            retmatch = to.deepcopy()
            for key in combined.bindings:
                retmatch.addtobinding(key, combined.getbinding(key))
            out.append((retmatch,head,tail))
    return out

def assert_compare_match_lists(m1, m2):
    if len(m1) == len(m2):
        for i, m in enumerate(m1):
            if not m.equals(m2[i]):
                print('assertion error: %s and %s do not match' % (match_list_to_string(m1),  match_list_to_string(m2)))
                assert False 
        return
    print('assertion error: %s and %s do not match' % (match_list_to_string(m1),  match_list_to_string(m2)))
    assert False 

def match_list_to_string(matches):
    string = '['
    if len(matches) > 0:
        for i in range(len(matches) - 1):
            match = matches[i]
            string = string + match.tostring() + ', '
        string = string + matches[-1].tostring()
    string = string + ']'
    return string 

def print_match_list(matches):
    print(match_list_to_string(matches))

