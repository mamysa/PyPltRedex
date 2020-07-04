import src.model.tlform as tlform
import src.model.pattern as pattern
from src.preprocess.pattern import EllipsisDepthChecker, InHoleChecker,                   \
        DefineLanguageNtCycleChecker, AssignableSymbolExtractor, ConstraintCheckInserter, \
        EllipsisMatchModeRewriter, DefineLanguageIdRewriter, NtResolver,                  \
        DefineLanguageCalculateNumberOfHoles, NtGraphBuilder, DefineLanguageNtClosureSolver
from src.preprocess.term import TermAnnotate 
from src.util import SymGen, CompilationError
from src.context import CompilationContext
import enum

class TopLevelProcessor(tlform.TopLevelFormVisitor):
    def __init__(self, module, context, debug_dump_ntgraph=False):
        assert isinstance(module, tlform.Module)
        assert isinstance(context, CompilationContext)
        self.module = module
        self.context = context
        self.symgen = SymGen() 

        self.debug_dump_ntgraph = debug_dump_ntgraph

        # store reference to definelanguage structure for use by redex-match form
        self.definelanguages = {}
        self.definelanguageclosures = {}
        self.reductionrelations = {}

    def run(self):
        forms = []
        for form in self.module.tlforms:
            forms.append( self._visit(form) )
        return tlform.Module(forms), self.context

    def _visitDefineLanguage(self, form):
        assert isinstance(form, tlform.DefineLanguage)

        resolver = NtResolver(form.ntsyms())
        for nt, ntdef in form.nts.items():
            npatterns = []
            for pat in ntdef.patterns:
                pat = resolver.transform(pat)
                npatterns.append(pat)
            ntdef.patterns = npatterns #FIXME all AstNodes should be immutable...

        form = DefineLanguageIdRewriter(form).run()
        successors, closures = DefineLanguageNtClosureSolver(form).run()
        #graph = form.computeclosure()
        DefineLanguageNtCycleChecker(form, successors).run()
        DefineLanguageCalculateNumberOfHoles(form, debug_dump_ntgraph=self.debug_dump_ntgraph).run()

        for nt, ntdef in form.nts.items():
            npatterns = []
            for pat in ntdef.patterns:
                InHoleChecker(form, pat).run()
                pat = EllipsisMatchModeRewriter(form, pat, closures).run()
                pat = AssignableSymbolExtractor(pat).run()
                npatterns.append(pat)
            ntdef.patterns = npatterns #FIXME all AstNodes should be immutable...
        self.context.add_variables_mentioned(form.name, resolver.variables)

        self.definelanguages[form.name] = form 
        self.definelanguageclosures[form.name] = closures
        return form

    def __processpattern(self, pat, languagename):
        ntsyms = self.definelanguages[languagename].ntsyms() #TODO nicer compiler error handling here
        resolver = NtResolver(ntsyms)
        pat = resolver.transform(pat)
        pat = EllipsisDepthChecker(pat).run()
        lang = self.definelanguages[languagename]
        InHoleChecker(lang, pat).run()
        pat = EllipsisMatchModeRewriter(self.definelanguages[languagename], pat, self.definelanguageclosures[languagename]).run()
        pat = ConstraintCheckInserter(pat).run()
        pat = AssignableSymbolExtractor(pat).run()
        return pat

    def _visitRedexMatch(self, form):
        assert isinstance(form, tlform.RedexMatch)
        form.pat = self.__processpattern(form.pat, form.languagename)
        return form

    def _visitMatchEqual(self, form):
        assert isinstance(form, tlform.MatchEqual)
        form.redexmatch = self._visit(form.redexmatch)
        return form

    def _visitAssertTermsEqual(self, form):
        assert isinstance(form, tlform.AssertTermsEqual)
        idof = self.symgen.get('termlet')
        form.template = TermAnnotate(form.variabledepths, idof, self.context).transform(form.template)
        return form

    def processReductionCase(self, reductioncase, languagename):
        assert isinstance(reductioncase, tlform.DefineReductionRelation.ReductionCase)
        reductioncase.pattern = self.__processpattern(reductioncase.pattern, languagename)
        assignablesymsdepths = reductioncase.pattern.getmetadata(pattern.PatAssignableSymbolDepths)
        idof = self.symgen.get('reductionrelation')
        reductioncase.termtemplate = TermAnnotate(assignablesymsdepths.syms, idof, self.context).transform(reductioncase.termtemplate)

    def _visitDefineReductionRelation(self, form):
        assert isinstance(form, tlform.DefineReductionRelation)
        self.reductionrelations[form.name] = form
        for rc in form.reductioncases:
            self.processReductionCase(rc, form.languagename)
        if form.domain != None:
            form.domain = self.__processpattern(form.domain, form.languagename)
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
#        return Falseut99.org/
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
