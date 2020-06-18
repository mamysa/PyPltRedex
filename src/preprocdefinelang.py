import src.tlform as tlform
import src.pat as pattern
import src.genterm as genterm
from src.symgen import SymGen
import sys
from src.context import CompilationContext
from src.digraph import DiGraph
import enum

#FIXME Ellipsis depth checker should not annotate terms - need to annotate terms 
# AFTER performing contraint checks.

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

# We have two kinds of functions
# (1) So called "IsA" functions. ...
class NtResolver(pattern.PatternTransformer):
    def __init__(self, ntsyms):
        self.ntsyms = ntsyms
        self.variables = set([])

    def transformUnresolvedSym(self, node):
        assert isinstance(node, pattern.UnresolvedSym)
        if node.prefix in self.ntsyms:
            return pattern.Nt(node.prefix, node.sym).copymetadatafrom(node)
        # not nt, check if there's underscore
        if node.prefix != node.sym:
            raise Exception('define-language: before underscore must be either a non-terminal or build-in pattern {}'.format(node.sym))

        self.variables.add(node.sym) # for variable-not-defined patterns.
        return pattern.Lit(node.sym, pattern.LitKind.Variable).copymetadatafrom(node)

class UnderscoreRemover(pattern.PatternTransformer):
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

class EllipsisDepthChecker(pattern.PatternTransformer):
    """
    Traverses a pattern, locates symbols to be bound while matching,
    and adds [sym, depth] annotation to the pattern. It describes the state of match object 
    by the end of matching process and is required for term term generation functions.
    Perform ellipsis depth checking along the way raising an exception when same symbols have
    different ellipsis depths.
    """
    def __init__(self, pat):
        self.depth = 0
        self.pat = pat 

    def run(self):
        pat, variables = self.transform(self.pat)
        return pat.addmetadata(pattern.PatAssignableSymbolDepths(variables))

    def _merge_variable_maps(self, m1, m2):
        m1k = set(list(m1.keys())) 
        m2k = set(list(m2.keys()))
        commonsyms = m1k.intersection(m2k)
        for sym in commonsyms:
            if m1[sym] != m2[sym]:
                raise Exception('found {} under {} ellipses in one place and {} in another'.format(sym, m1[sym], m2[sym]))
        return {**m1, **m2}

    def transformPatSequence(self, node):
        assert isinstance(node, pattern.PatSequence)
        variables = {}
        seq = []
        for pat in node.seq:
            npat, npatvariables = self.transform(pat)
            seq.append(npat)
            variables = self._merge_variable_maps(variables, npatvariables)
        return pattern.PatSequence(seq).copymetadatafrom(node), variables

    def transformRepeat(self, node):
        assert isinstance(node, pattern.Repeat)
        self.depth += 1
        pat, variables = self.transform(node.pat)
        self.depth -= 1
        return pattern.Repeat(pat).copymetadatafrom(node), variables 

    def transformUnresolvedSym(self, node):
        assert False, 'UnresolvedSym not allowed'

    def transformNt(self, node):
        assert isinstance(node, pattern.Nt)
        return node, {node.sym: self.depth}

    def transformBuiltInPat(self, node):
        assert isinstance(node, pattern.BuiltInPat)
        # FIXME need to introduce explicit Pat node for in-hole patterns
        if node.kind == pattern.BuiltInPatKind.InHole:
            pat1, pat2 = node.aux
            pat1, pat1variables = self.transform(pat1)
            pat2, pat2variables = self.transform(pat2)
            variables = self._merge_variable_maps(pat1variables, pat2variables)
            return pattern.BuiltInPat(node.kind, node.prefix, node.sym, (pat1, pat2)) \
                          .copymetadatafrom(node), variables
        # and for holes!
        if node.kind == pattern.BuiltInPatKind.Hole:
            return node, {}
        return node, {node.sym: self.depth}

    def transformCheckConstraint(self, node):
        assert False, 'unreachable'

    def transformLit(self, node):
        return node, {}

class UnderscoreIdUniquify(pattern.PatternTransformer):
    def __init__(self):
        self.id = 0

    def transformBuiltInPat(self, node):
        node.sym = '{}_{}'.format(node.prefix, self.id)
        self.id += 1
        return node

    def transformNt(self, node):
        node.sym = '{}_{}'.format(node.prefix, self.id)
        self.id += 1
        return node

# Patterns like ((n_1 ... n_1 ...) (n_1 ... n_1 ...)) require all n_1 ... values to be equal.
# This is done by creating temporary bindings for each n_1 encountered. More specifically,
# (1) ((n_1 ... n_1#2 ... CheckEquality(n_1 n_1#0) (n_1 ... n_1 ...))
# (2) ((n_1 ... n_1#0 ... CheckEquality(n_1 n_1#0) (n_1 ... n_1#1 ... CheckEquality(n_1 n_1#1)))
# (3) ((n_1 ... n_1#0 ... CheckEquality(n_1 n_1#0) (n_1#2 ... n_1#1 ... CheckEquality(n_1 n_1#1)) CheckEquality(n_1, n_1#2))
# This class (1) renames all occurences of bindable symbol (except the first one)
# (2) Inserts contraint checks when at least two syms have been seen in the sequence.
class ConstraintCheckInserter(pattern.PatternTransformer):
    def __init__(self, pattern, sym):
        self.sym = sym
        self.pattern = pattern
        self.symgen = SymGen()

    def run(self):
        pat, _ = self.transform(self.pattern)
        return pat

    def transformPatSequence(self, seq):
        assert isinstance(seq, pattern.PatSequence) 
        nseq = [] 
        syms = []
        for pat in seq:
            node, sym = self.transform(pat)
            nseq.append(node)
            if sym != None: 
                syms.append(sym)

            if len(syms) == 2:
                nseq.append( pattern.CheckConstraint(syms[0], syms[1]) )
                syms.pop()

        assert len(syms) < 2
        nseq = pattern.PatSequence(nseq).copymetadatafrom(seq)
        if len(syms) == 0:
            return nseq, None
        return nseq, syms[0] 

    def transformRepeat(self, repeat):
        pat, sym = self.transform(repeat.pat)
        nrepeat = pattern.Repeat(pat).copymetadatafrom(repeat)
        return nrepeat, sym

    def transformBuiltInPat(self, pat):
        assert isinstance(pat, pattern.BuiltInPat)
        # FIXME is this correct?
        if pat.kind == pattern.BuiltInPatKind.InHole:
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
        assert isinstance(pat, pattern.Nt)
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

# pattern is not modified during this pass.
# TODO seems to be very similar to EllipsisDepthChecker, merge them together?
class AssignableSymbolExtractor(pattern.PatternTransformer):
    def __init__(self, pat):
        self.pat = pat 

    def run(self):
        pat, variables = self.transform(self.pat)
        return pat.addmetadata(pattern.PatAssignableSymbols(variables))
        return pat 

    def transformPatSequence(self, node):
        assert isinstance(node, pattern.PatSequence)
        variables = set([]) 
        for pat in node.seq:
            _, patvariables = self.transform(pat)
            variables = variables.union(patvariables)
        return node, variables

    def transformRepeat(self, node):
        assert isinstance(node, pattern.Repeat)
        _, variables = self.transform(node.pat)
        return node.addmetadata(pattern.PatAssignableSymbols(variables)), variables

    def transformCheckConstraint(self, node):
        return node, set([])

    def transformNt(self, node):
        assert isinstance(node, pattern.Nt)
        return node, set([node.sym])

    def transformBuiltInPat(self, node):
        assert isinstance(node, pattern.BuiltInPat)
        # FIXME need to introduce explicit Pat node for in-hole patterns
        if node.kind == pattern.BuiltInPatKind.InHole:
            pat1, pat2 = node.aux
            _, pat1variables = self.transform(pat1)
            _, pat2variables = self.transform(pat2)
            pat1.addmetadata(pattern.PatAssignableSymbols(pat1variables))
            pat2.addmetadata(pattern.PatAssignableSymbols(pat2variables))
            variables = pat1variables.union(pat2variables)
            return node, variables
        # and for holes!
        if node.kind == pattern.BuiltInPatKind.Hole:
            return node, set([]) 
        return node, set([node.sym])

    def transformLit(self, node):
        return node, set([]) 


# This pass attempts to make consecutive ellipses match deterministically.
# Here's the example:
# Given language (m ::= (* m m) e) (e ::= (+ e e) n) (n ::= number), ellipses in pattern 
# (m_1 ... e_1 ... n_1 ... e_2) cannot match deterministically - because m_1, e_1 and e_2 can also be numbers.
# We have {e} ⊆ m, {n} ⊆ e, and {number} ⊆ n. If we compute transitive "closure" for each non-terminal we get the following:
# {number, n, e} ⊆ m; {number, n} ⊆ e; {number} ⊆ n. Two patterns p1,p2 cannot be made deterministic 
# if closure(p1) ∩ closure(p2) is not empty.
#FIXME this is not true for duplicate definitions that are not used anywhere, add extra (z ::= number) rule and 
# while computing closure z is not in e. We need to introduce a graph, perform dfs and see if common nodes can be reached.


# This should handle primitive cases of Nt and BuiltInPat. 
 
# Otherwise, we should check if patterns being compared are structurally identical and leafs of patterns
# pass closure membership test from above.
# In ((m_1 e_1) ... (e_2 n_1) ...) subpatterns  (m_1 e_1) and (e_2 n_1)
# are structurally identical and for pair (m_1, e_2) e ∈ closure(m), for (e_1, n_1) n ∈ closure(e)

# Now we consider pattern ((x_1 ...) ... (n_1 ...) ...). (x_1 ...) ... pattern cannot be matched deterministically since even though
# patterns x and n match competely different terms  both subpatterns may match (). 
#For example, for term (a b) () (1 2 3) there are two matches match1: x_1=((a b) ()) n_1=((1 2 3)) match2: x_1=((a b))  n_1=(() (1 2 3)).
# This should be initial term check.

# What about ((x_1 ... n_1) ... (s_1 ... n_2) ...)? Both subterms under ellipsis have the same structure. Term ((x y z 1) (1 2 3 4)) matches 
# the pattern but since (x y z) and (1 2 3) are optional, the term without these becomes ((1) (4)) which has to be matched non-deterministically.
# Similarly, by adding (y ::= string) rule to the language the pattern ((x_1 ... y_1) ... (x_1 ... n_1) ...) CAN BE matched deterministically, 
# for example ((x y z "helloworld") (x 1)). 
# TLDR we ignore ellipsis and make decision based on elements of the sequence that have to matched. If closure test fails then pattern matching can
# be made deterministic.



# TODO in-hole treatment?  
class MakeEllipsisDeterministic(pattern.PatternTransformer):
    # Given two patterns pat1 and pat2, both under ellipsis, return True if pat1
    # can be matched deterministically.
    class PatternStructuralChecker:
        def __init__(self, closures):
            self.closures = closures

        def check(self, pat1, pat2):
            assert isinstance(pat1, pattern.Pat)
            assert isinstance(pat2, pattern.Pat)
            method_name = 'check' + pat1.__class__.__name__
            method_ref = getattr(self, method_name)
            return method_ref(pat1, pat2)

        def checkPatSequence(self, pat1, pat2):
            assert isinstance(pat1, pattern.PatSequence)
            if isinstance(pat2, pattern.PatSequence):
                p1 = pat1.get_nonoptional_matches()
                p2 = pat2.get_nonoptional_matches()
                if len(p1) != len(p2):
                    return True
                for i in range(len(p1)):
                    if self.check(p1[i], p2[i]):
                        return True
                return False
            return True

        def checkNt(self, pat1, pat2):
            assert isinstance(pat1, pattern.Nt)
            if isinstance(pat2, pattern.Nt):
                pat1cl = self.closures[pat1.prefix]
                pat2cl = self.closures[pat2.prefix]
                return len(pat1cl.intersection(pat2cl)) == 0
            if isinstance(pat2, pattern.BuiltInPat):
                pat1cl = self.closures[pat1.prefix]
                return not pat2.prefix in pat1cl
            return True

        def checkBuiltInPat(self, pat1, pat2):
            assert isinstance(pat1, pattern.BuiltInPat)
            if pat1.kind == pattern.BuiltInPatKind.InHole: # TODO
                return False
            if isinstance(pat2, pattern.BuiltInPat):
                return pat1.kind != pat2.kind
            if isinstance(pat2, pattern.Nt):
                pat2cl = self.closures[pat2.prefix]
                return not pat1.prefix in pat2cl
            return True

        def checkLit(self, pat1, pat2):
            assert isinstance(pat1, pattern.Lit)
            if isinstance(pat2, pattern.Lit):
                if pat1.kind == pat2.kind:
                    return pat1.lit != pat2.lit
                return True
            return True

    def __init__(self, definelanguage, pat):
        assert isinstance(definelanguage, tlform.DefineLanguage)
        self.definelanguage = definelanguage 
        self.pat = pat

    ## Should move this out of here 
    def _compute_closure(self):
        # compute initial sets.
        closureof = {}
        for ntdef in self.definelanguage.nts.values():
            syms = []
            assert isinstance(ntdef, tlform.DefineLanguage.NtDefinition)
            for pat in ntdef.patterns:
                if isinstance(pat, pattern.Nt):
                    syms.append(pat.prefix)
                if isinstance(pat, pattern.BuiltInPat):
                    if pat.kind != pattern.BuiltInPatKind.InHole:
                        syms.append(pat.prefix)
            closureof[ntdef.get_nt_sym()] = set(syms)

        # iteratively compute closure.
        changed = True
        while changed:
            changed = False
            for sym, closure in closureof.items():
                for elem in closure:
                    closureof_elem = closureof.get(elem, set([])) # might be built-in pattern.
                    closureof_sym = closure.union(closureof_elem)
                    if closureof_sym != closure:
                        changed = True
                    closure = closureof_sym 
                closureof[sym] = closure
        return closureof

    # Partitions sequence of terms 
    def _partitionseq(self, seq):
        matching_ellipsis = False
        partitions = [] 
        partition = []
        for i, pat in enumerate(seq):
            if isinstance(pat, pattern.Repeat):
                if matching_ellipsis:
                    partition.append(pat)
                else:
                    # flush previous partition
                    matching_ellipsis = True
                    if len(partition) > 0:
                        partitions.append((False, partition))
                    partition = [ pat ]
            else:
                partition.append(pat)
                if matching_ellipsis:
                    assert len(partition) > 1
                    matching_ellipsis = False
                    partitions.append((True, partition))
                    partition = []

        if len(partition) > 0:
            if matching_ellipsis:
                partitions.append((True, partition))
            else:
                partitions.append((False, partition))

        return partitions

    def run(self):
        return self.transform(self.pat)

    def transformPatSequence(self, sequence):
        assert isinstance(sequence, pattern.PatSequence)
        closures = self._compute_closure()

        # recursively transform patterns first.
        tseq = []
        for pat in sequence.seq:
            tseq.append( self.transform(pat) )
            
        nseq = []
        partitions = self._partitionseq(tseq)
        for contains_ellipsis, partition in partitions:
            if contains_ellipsis:
                for i in range(len(partition) - 1):
                    pat1, pat2 = partition[i], partition[i+1]
                    if isinstance(pat1, pattern.Repeat):
                        psc = self.PatternStructuralChecker(closures)
                        if isinstance(pat2, pattern.Repeat):
                            p1, p2 = pat1.pat, pat2.pat
                        else:
                            p1, p2 = pat1.pat, pat2
                        if psc.check(p1, p2):
                            nrep = pattern.Repeat(p1, pattern.RepeatMatchMode.Deterministic).copymetadatafrom(pat1)
                            nseq.append(nrep)
                        else:
                            nseq.append(pat1)
                # append the last unprocessed element
                last = partition[-1]
                if isinstance(last, pattern.Repeat):
                    last = pattern.Repeat(last.pat, pattern.RepeatMatchMode.Deterministic).copymetadatafrom(last)
                nseq.append(last)
            else: 
                nseq += partition
        return pattern.PatSequence(nseq).copymetadatafrom(sequence)

class TopLevelProcessor(tlform.TopLevelFormVisitor):
    def __init__(self, module, context):
        assert isinstance(module, tlform.Module)
        assert isinstance(context, CompilationContext)
        self.module = module
        self.context = context
        self.symgen = SymGen() 

        # store reference to definelanguage structure for use by redex-match form
        self.definelanguages = {}
        self.reductionrelations = {}

    def run(self):
        forms = []
        for form in self.module.tlforms:
            forms.append( self._visit(form) )
        return tlform.Module(forms), self.context

    def _visitDefineLanguage(self, form):
        assert isinstance(form, tlform.DefineLanguage)
        self.definelanguages[form.name] = form 

        resolver = NtResolver(form.ntsyms())
        remover = UnderscoreRemover()
        uniquify = UnderscoreIdUniquify()
        for nt, ntdef in form.nts.items():
            npatterns = []
            for pat in ntdef.patterns:
                pat = resolver.transform(pat)
                pat = remover.transform(pat)
                pat = uniquify.transform(pat)
                pat = AssignableSymbolExtractor(pat).run()
                npatterns.append(pat)
            ntdef.patterns = npatterns #FIXME all AstNodes should be immutable...
        self.context.add_variables_mentioned(form.name, resolver.variables)
        return form

    def __processpattern(self, pat, ntsyms):
        resolver = NtResolver(ntsyms)
        pat = resolver.transform(pat)
        pat = EllipsisDepthChecker(pat).run()
        symbols = pat.getmetadata(pattern.PatAssignableSymbolDepths)
        for sym in symbols.syms:
            pat = ConstraintCheckInserter(pat, sym).run()
        pat = AssignableSymbolExtractor(pat).run()
        return pat

    def _visitRedexMatch(self, form):
        assert isinstance(form, tlform.RedexMatch)
        ntsyms = self.definelanguages[form.languagename].ntsyms() #TODO nicer compiler error handling here
        form.pat = self.__processpattern(form.pat, ntsyms)
        return form

    def _visitMatchEqual(self, form):
        assert isinstance(form, tlform.MatchEqual)
        form.redexmatch = self._visit(form.redexmatch)
        return form

    def _visitAssertTermsEqual(self, form):
        assert isinstance(form, tlform.AssertTermsEqual)
        idof = self.symgen.get('termlet')
        form.template = genterm.TermAnnotate(form.variabledepths, idof, self.context).transform(form.template)
        return form

    def processReductionCase(self, reductioncase, ntsyms):
        assert isinstance(reductioncase, tlform.DefineReductionRelation.ReductionCase)
        reductioncase.pattern = self.__processpattern(reductioncase.pattern, ntsyms)
        assignablesymsdepths = reductioncase.pattern.getmetadata(pattern.PatAssignableSymbolDepths)
        idof = self.symgen.get('reductionrelation')
        reductioncase.termtemplate = genterm.TermAnnotate(assignablesymsdepths.syms, idof, self.context).transform(reductioncase.termtemplate)

    def _visitDefineReductionRelation(self, form):
        assert isinstance(form, tlform.DefineReductionRelation)
        self.reductionrelations[form.name] = form
        ntsyms = self.definelanguages[form.languagename].ntsyms() #TODO nicer compiler error handling here
        for rc in form.reductioncases:
            self.processReductionCase(rc, ntsyms)
        if form.domain != None:
            form.domain = self.__processpattern(form.domain, ntsyms)
        return form

    def _visitApplyReductionRelation(self, form):
        assert isinstance(form, tlform.ApplyReductionRelation)
        reductionrelation = self.reductionrelations[form.reductionrelationname]
        return form








#class PatternComparator:
#    """
#    Compares patterns. Underscores are ignored.
#    """
#    def compare(self, this, other):
#        assert isinstance(this, ast.Pat)
#        assert isinstance(other, ast.Pat)
#        method_name = 'compare' + this.__class__.__name__
#        method_ref = getattr(self, method_name)
#        return method_ref(this, other)
#
#    def compareUnresolvedSym(self, this, other):
#        assert False, 'not allowed'
#
#    def compareLit(self, this, other):
#        if isinstance(other, ast.Lit):
#            return this.kind == other.kind and this.lit == other.lit
#        return False
#
#    def compareNt(self, this, other):
#        if isinstance(other, ast.Nt):
#            return this.prefix == other.prefix
#        return False
#
#    def compareRepeat(self, this, other):
#        if isinstance(other, ast.Repeat):
#            return self.compare(this.pat, other.pat)
#        return False
#
#    def compareBuiltInPat(self, this, other):
#        if isinstance(other, ast.BuiltInPat):
#            return this.kind == other.kind and this.prefix == other.prefix
#        return False
#
#    def comparePatSequence(self, this, other):
#        if isinstance(other, ast.PatSequence):
#            if len(this) == len(other):
#                match = True
#                for i, elem in enumerate(this):
#                    match = self.compare(elem, other[i])
#                    if not match:
#                        break
#                return match
#        return False
#
#
#class InsertTermEqualityChecking:
#    pass
#
## This does not work as expected. For example, 
## given language (e ::= (e ... n n ...) (+ e e) n) (n ::= number) matching e greedily 
## in the first pattern also consumes all n if they are present in the term.
## Matching e ... needs to return all permutations.
#
## Perhaps we could also do (e ... n n ...) -> ( e ... n ... n) -> (e ... n) (because n is e),
## match n in the end of the term first and then match e ...  greedily?
#
## FIXME always return fresh ast node instances.
#class DefineLanguagePatternSimplifier(pat.PatternTransformer):
#    """
#    The goal of this pass is to simplify patterns in define-language. For example, given pattern
#    e ::= (n ... n ... n n ... n) we do not need to match each repitition of n to establish that some term
#    is actually e (and individually matched items aren't bound). 
#    All that is needed is for the term to contain at least two n. Thus,
#    (n ... n ... n n ... n)  ---> (n ... n  n ... n)   [merge two n ...]
#    (n ... n n ... n) --> (n n ... n ... n)            [shuffle]
#    (n n ... n ... n) --> (n n ... n)                  [merge]
#    (n n ... n) --> (n n n...)                         [shuffle]
#    This way, instead of producing multiple matches that no one needs (as required by n ...) 
#    all sub-patterns can be matched 'greedily'.
#    """
#
#    def transformPatSequence(self, node):
#        assert isinstance(node, ast.PatSequence)
#        # not very pythonic....
#        newseq = []
#        for e in node.seq:
#            newseq.append(self.transform(e))
#        
#        i = 0
#        newseq2 = []
#        while i < len(newseq):
#            num_repeats = 0
#            num_required = 0
#
#            if isinstance(newseq[i], ast.Repeat):
#                elem = newseq[i].pat
#                num_repeats += 1
#            else:
#                elem = newseq[i]
#                num_required += 1
#
#            j = i + 1
#            while j < len(newseq):
#                if isinstance(newseq[j], ast.Repeat):
#                    if PatternComparator().compare(elem, newseq[j].pat):
#                        num_repeats += 1
#                    else:
#                        break
#                else:
#                    if PatternComparator().compare(elem, newseq[j]):
#                        num_required += 1
#                    else:
#                        break
#                j += 1
#            i = j
#
#            # push required matches first, optional repetiton after if present in original pattern.
#            for k in range(num_required):
#                newseq2.append(elem)
#            if num_repeats > 0:
#                newseq2.append(ast.Repeat(elem))
#
#        node.seq = newseq2
#        return node
