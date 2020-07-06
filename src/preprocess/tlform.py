import src.model.tlform as tlform
import src.model.pattern as pattern
from src.preprocess.pattern import *
from src.preprocess.term import *
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
        form, variables = DefineLanguage_NtRewriter(form, form.ntsyms()).run()
        self.context.add_variables_mentioned(form.name, variables)
        form = DefineLanguage_IdRewriter(form).run()
        successors, closures = DefineLanguage_NtClosureSolver(form).run()
        DefineLanguage_NtCycleChecker(form, successors).run()

        graph = NtGraphBuilder(form).run()
        print(graph.getnumberofedges())
        if self.debug_dump_ntgraph:
            graph.dump(form.name)
        import sys
        sys.exit(1)
        #DefineLanguage_HoleReachabilitySolver(form, debug_dump_ntgraph=self.debug_dump_ntgraph).run()
        form = DefineLanguage_EllipsisMatchModeRewriter(form, closures).run()
        form = DefineLanguage_AssignableSymbolExtractor(form).run()
        self.definelanguages[form.name] = form 
        self.definelanguageclosures[form.name] = closures
        return form

    def __processpattern(self, pat, languagename):
        lang = self.definelanguages[languagename]
        closure = self.definelanguageclosures[languagename]
        ntsyms = lang.ntsyms()
        pat = Pattern_NtRewriter(pat, ntsyms).run()
        pat = Pattern_EllipsisDepthChecker(pat).run()
        Pattern_InHoleChecker(lang, pat).run()
        pat = Pattern_EllipsisMatchModeRewriter(lang, pat, closure).run()
        pat = Pattern_ConstraintCheckInserter(pat).run()
        pat = Pattern_AssignableSymbolExtractor(pat).run()
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
        form.template = Term_EllipsisDepthChecker(form.variabledepths, idof, self.context).transform(form.template)
        return form

    def processReductionCase(self, reductioncase, languagename):
        assert isinstance(reductioncase, tlform.DefineReductionRelation.ReductionCase)
        reductioncase.pattern = self.__processpattern(reductioncase.pattern, languagename)
        assignablesymsdepths = reductioncase.pattern.getmetadata(pattern.PatAssignableSymbolDepths)
        idof = self.symgen.get('reductionrelation')
        reductioncase.termtemplate = Term_EllipsisDepthChecker(assignablesymsdepths.syms, idof, self.context).transform(reductioncase.termtemplate)

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
