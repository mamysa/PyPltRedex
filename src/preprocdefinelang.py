import src.astdefs as ast
from src.symgen import SymGen

# Preprocessing define-language construct involves the following steps.
# (1) Ensure all non-terminals are defined exactly once and contain no underscores. 
#     This bit is done at parsing phase.
# (2) Resolve UnresolvedPat instances to either NtRef or Literal value.
# (3) In each righthand-side pattern, remove underscores from builtin-patterns / NtRefs.
#     Current redex behaviour is that all non-terminal patterns in define-language are 
#     constrained to be different. (I recall seeing it in documentation but I can't find it 
#     anymore... perhaps behaviour has been changed?). Underscores will be re-added later.
# (4) "Optimize" righthand-side patterns i.e. remove adjacent Repeat elements (recursively) 
#     when appropriate. For example, patterns like e ::= (n n... n...) can transformed into 
#     e ::= (n n...) when matching e.  FIXME this does not work as expected.
# (5) Introduce underscores back into right-handside bindable patterns(i.e. nts and builtin-pats); 
#     id after each underscore must be unique.

# TODO Need to check for non-terminal cycles in define-language patterns 
# such as (y ::= x) (x ::= y) or even (x ::= x)

class LanguageContext:
    def __init__(self):
        self.__variables_mentioned = None
        self.__isa_functions = {}
        self.__pattern_code = {}
        self.__term_template_funcs = {}

        self._litterms = {}

        self.symgen = SymGen()

    def add_variables_mentioned(self, variables):
        self.__variables_mentioned = ('variables_mentioned', variables)

    def get_variables_mentioned(self):
        return self.__variables_mentioned

    def add_isa_function_name(self, prefix, function):
        assert prefix not in self.__isa_functions
        self.__isa_functions[prefix] = function
    
    def get_isa_function_name(self, prefix):
        if prefix in self.__isa_functions:
            return self.__isa_functions[prefix]
        return None

    def add_lit_term(self, term):
        self._litterms[term] = self.symgen.get('literal_term_') 

    def get_sym_for_lit_term(self, term):
        return self._litterms[term]

    # FIXME this should be in module-level context?
    def add_function_for_pattern(self, prefix, function):
        assert prefix not in self.__pattern_code, 'function for {} is present'.format(prefix)
        self.__pattern_code[prefix] = function
    
    def get_function_for_pattern(self, prefix):
        if prefix in self.__pattern_code:
            return self.__pattern_code[prefix]
        return None

    def add_function_for_term_template(self, prefix, function):
        assert prefix not in self.__term_template_funcs, 'function for {} is present'.format(prefix)
        self.__term_template_funcs[prefix] = function

    def get_function_for_term_template(self, prefix):
        if prefix in self.__term_template_funcs:
            return self.__term_template_funcs[prefix]
        return None

class NtResolver(ast.PatternTransformer):
    def __init__(self, ntsyms):
        self.ntsyms = ntsyms
        self.variables = set([])

    def transformUnresolvedSym(self, node):
        assert isinstance(node, ast.UnresolvedSym)
        if node.prefix in self.ntsyms:
            return ast.Nt(node.prefix, node.sym)
        # not nt, check if there's underscore
        if node.prefix != node.sym:
            raise Exception('define-language: before underscore must be either a non-terminal or build-in pattern {}'.format(node.sym))

        self.variables.add(node.sym) # for variable-not-defined patterns.
        return ast.Lit(node.sym, ast.LitKind.Variable)

class UnderscoreRemover(ast.PatternTransformer):
    """
    Transformer that removes underscores from all non-terminals / built-in patterns in the pattern.
    (since underscores in define-language patterns don't matter)
    This needs to be done AFTER resolving non-terminals and detecting literals containing underscores.
    """

    def transformBuiltInPat(self, node):
        node.sym = node.prefix
        return node

    def transformNt(self, node):
        node.sym = node.prefix
        return node


class UnderscoreIdUniquify(ast.PatternTransformer):
    def __init__(self):
        self.id = 0

    def transformDefineLanguage(self, node):
        assert isinstance(node, ast.DefineLanguage)
        for nt, ntdef in node.nts.items():
            node.nts[nt] = self.transform(ntdef)
        return node

    def transformNtDefinition(self, node):
        assert isinstance(node, ast.NtDefinition)
        for i, pat in enumerate(node.patterns):
            node.patterns[i] = self.transform(pat)
        return node

    def transformBuiltInPat(self, node):
        node.sym = '{}_{}'.format(node.prefix, self.id)
        self.id += 1
        return node

    def transformNt(self, node):
        node.sym = '{}_{}'.format(node.prefix, self.id)
        self.id += 1
        return node

def module_preprocess(node):
    assert isinstance(node, ast.Module)
    node.definelanguage, context = definelanguage_preprocess(node.definelanguage)
    for redexmatch in node.redexmatches:
        redexmatch.pat = pattern_preprocess(redexmatch.pat, node.definelanguage.ntsyms())
    for me in node.matchequals:
        me.redexmatch.pat = pattern_preprocess(me.redexmatch.pat, node.definelanguage.ntsyms())
    return node, context

def definelanguage_preprocess(node):
    """
    Resolves all non-terminal symbols and removes underscores from patterns in define-language.
    """
    assert isinstance(node, ast.DefineLanguage)
    resolver = NtResolver(node.ntsyms())
    remover = UnderscoreRemover()
    #simplifier = DefineLanguagePatternSimplifier()
    for nt, ntdef in node.nts.items():
        patterns = ntdef.patterns
        new_patterns = []
        for pat in patterns:
            pat = resolver.transform(pat)
            pat = remover.transform(pat)
            #pat = simplifier.transform(pat)
            new_patterns.append(pat)
        ntdef.patterns = new_patterns

    node = UnderscoreIdUniquify().transform(node)

    context = LanguageContext()
    context.add_variables_mentioned(resolver.variables)
    return node, context    # resolver.variables 

def pattern_preprocess(pat, ntsyms):
    assert isinstance(pat, ast.Pat)
    resolver = NtResolver(ntsyms)
    checker = EllipsisDepthChecker()
    pat = resolver.transform(pat)
    pat = checker.transform(pat)
    bindablesyms = pat.collect_bindable_syms()
    for sym in bindablesyms:
        pat, _ = ConstraintCheckInserter(sym).transform(pat)
    return pat

class EllipsisDepthChecker(ast.PatternTransformer):
    def __init__(self):
        self.depth = 0
        self.vars = {}

    def transformRepeat(self, node):
        assert isinstance(node, ast.Repeat)
        self.depth += 1
        node.pat = self.transform(node.pat)
        self.depth -= 1
        return node

    def transformNt(self, node):
        assert isinstance(node, ast.Nt)
        if node.sym not in self.vars:
            self.vars[node.sym] = self.depth
            return node
        if self.vars[node.sym] != self.depth:
            raise Exception('found {} under {} ellipses in one place and {} in another'.format(node.sym, self.vars[node.sym], self.depth))
        return node

    def transformUnresolvedSym(self, node):
        assert False, 'UnresolvedSym not allowed'

# Patterns like ((n_1 ... n_1 ...) (n_1 ... n_1 ...)) require all n_1 ... values to be equal.
# This is done by creating temporary bindings for each n_1 encountered. More specifically,
# (1) ((n_1 ... n_1#2 ... CheckEquality(n_1 n_1#0) (n_1 ... n_1 ...))
# (2) ((n_1 ... n_1#0 ... CheckEquality(n_1 n_1#0) (n_1 ... n_1#1 ... CheckEquality(n_1 n_1#1)))
# (3) ((n_1 ... n_1#0 ... CheckEquality(n_1 n_1#0) (n_1#2 ... n_1#1 ... CheckEquality(n_1 n_1#1)) CheckEquality(n_1, n_1#2))
# This class (1) renames all occurences of bindable symbol (except the first one)
# (2) Inserts contraint checks when at least two syms have been seen in the sequence.
class ConstraintCheckInserter(ast.PatternTransformer):
    def __init__(self, sym):
        self.sym = sym
        self.symgen = SymGen()

    def transformPatSequence(self, seq):
        assert isinstance(seq, ast.PatSequence) 
        nseq = [] 
        syms = []
        for pat in seq:
            node, sym = self.transform(pat)
            nseq.append(node)
            if sym != None: 
                syms.append(sym)

            if len(syms) == 2:
                nseq.append( ast.CheckConstraint(syms[0], syms[1]) )
                syms.pop()

        assert len(syms) < 2
        nseq = ast.PatSequence(nseq)
        if len(syms) == 0:
            return nseq, None
        return nseq, syms[0]

    def transformRepeat(self, repeat):
        pat, sym = self.transform(repeat.pat)
        return ast.Repeat(pat), sym

    def transformBuiltInPat(self, pat):
        assert isinstance(pat, ast.BuiltInPat)
        if pat.kind == ast.BuiltInPatKind.InHole:
            pat1, _ = self.transform(pat.aux[0])
            pat2, _ = self.transform(pat.aux[1])
            pat.aux = (pat1, pat2)
        return pat, None

        if pat.sym == self.sym:
            nsym = self.symgen.get('{}#'.format(self.sym))
            # First time we see desired symbol we do not rename it - we will keep it in the end.
            if nsym != '{}#0'.format(self.sym):
                pat.sym = nsym
                return pat, nsym
            return pat, pat.sym
        return pat, None

    def transformNt(self, pat):
        assert isinstance(pat, ast.Nt)
        if pat.sym == self.sym:
            nsym = self.symgen.get('{}#'.format(self.sym))
            # First time we see desired symbol we do not rename it - we will keep it in the end.
            if nsym != '{}#0'.format(self.sym):
                pat.sym = nsym
                return pat, nsym
            return pat, pat.sym
        return pat, None

    def transformLit(self, pat):
        return pat, None

    def transformCheckConstraint(self, node):
        return node, None

class PatternComparator:
    """
    Compares patterns. Underscores are ignored.
    """
    def compare(self, this, other):
        assert isinstance(this, ast.Pat)
        assert isinstance(other, ast.Pat)
        method_name = 'compare' + this.__class__.__name__
        method_ref = getattr(self, method_name)
        return method_ref(this, other)

    def compareUnresolvedSym(self, this, other):
        assert False, 'not allowed'

    def compareLit(self, this, other):
        if isinstance(other, ast.Lit):
            return this.kind == other.kind and this.lit == other.lit
        return False

    def compareNt(self, this, other):
        if isinstance(other, ast.Nt):
            return this.prefix == other.prefix
        return False

    def compareRepeat(self, this, other):
        if isinstance(other, ast.Repeat):
            return self.compare(this.pat, other.pat)
        return False

    def compareBuiltInPat(self, this, other):
        if isinstance(other, ast.BuiltInPat):
            return this.kind == other.kind and this.prefix == other.prefix
        return False

    def comparePatSequence(self, this, other):
        if isinstance(other, ast.PatSequence):
            if len(this) == len(other):
                match = True
                for i, elem in enumerate(this):
                    match = self.compare(elem, other[i])
                    if not match:
                        break
                return match
        return False


class InsertTermEqualityChecking:
    pass

# This does not work as expected. For example, 
# given language (e ::= (e ... n n ...) (+ e e) n) (n ::= number) matching e greedily 
# in the first pattern also consumes all n if they are present in the term.
# Matching e ... needs to return all permutations.

# Perhaps we could also do (e ... n n ...) -> ( e ... n ... n) -> (e ... n) (because n is e),
# match n in the end of the term first and then match e ...  greedily?

# FIXME always return fresh ast node instances.
class DefineLanguagePatternSimplifier(ast.PatternTransformer):
    """
    The goal of this pass is to simplify patterns in define-language. For example, given pattern
    e ::= (n ... n ... n n ... n) we do not need to match each repitition of n to establish that some term
    is actually e (and individually matched items aren't bound). 
    All that is needed is for the term to contain at least two n. Thus,
    (n ... n ... n n ... n)  ---> (n ... n  n ... n)   [merge two n ...]
    (n ... n n ... n) --> (n n ... n ... n)            [shuffle]
    (n n ... n ... n) --> (n n ... n)                  [merge]
    (n n ... n) --> (n n n...)                         [shuffle]
    This way, instead of producing multiple matches that no one needs (as required by n ...) 
    all sub-patterns can be matched 'greedily'.
    """

    def transformPatSequence(self, node):
        assert isinstance(node, ast.PatSequence)
        # not very pythonic....
        newseq = []
        for e in node.seq:
            newseq.append(self.transform(e))
        
        i = 0
        newseq2 = []
        while i < len(newseq):
            num_repeats = 0
            num_required = 0

            if isinstance(newseq[i], ast.Repeat):
                elem = newseq[i].pat
                num_repeats += 1
            else:
                elem = newseq[i]
                num_required += 1

            j = i + 1
            while j < len(newseq):
                if isinstance(newseq[j], ast.Repeat):
                    if PatternComparator().compare(elem, newseq[j].pat):
                        num_repeats += 1
                    else:
                        break
                else:
                    if PatternComparator().compare(elem, newseq[j]):
                        num_required += 1
                    else:
                        break
                j += 1
            i = j

            # push required matches first, optional repetiton after if present in original pattern.
            for k in range(num_required):
                newseq2.append(elem)
            if num_repeats > 0:
                newseq2.append(ast.Repeat(elem))

        node.seq = newseq2
        return node
