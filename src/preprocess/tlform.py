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
        self.metafunctions = {}

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
        DefineLanguage_HoleReachabilitySolver(form, graph).run()
        if self.debug_dump_ntgraph:
            graph.dump(form.name)
            print('------ Debug Nt hole counts for language {}: ------'.format(form.name))
            for nt, ntdef in form.nts.items():
                print('{}: {}'.format(nt, repr(ntdef.nt.getmetadata(pattern.PatNumHoles))))
            print('\n') 
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

    def __processdomaincheck(self, pat, languagename):
        lang = self.definelanguages[languagename]
        ntsyms = lang.ntsyms()
        closure = self.definelanguageclosures[languagename]
        pat = Pattern_NtRewriter(pat, ntsyms).run()
        pat = Pattern_IdRewriter(pat).run()
        Pattern_InHoleChecker(lang, pat).run()
        pat = Pattern_EllipsisMatchModeRewriter(lang, pat, closure).run()
        pat = Pattern_AssignableSymbolExtractor(pat).run()
        return pat

    def __processtermtemplate(self, termtemplate, assignments={}):
        idof = self.symgen.get('termtemplate')
        termtemplate = Term_EllipsisDepthChecker(assignments, idof, self.context).transform(termtemplate)
        termtemplate = Term_MetafunctionApplicationRewriter(termtemplate, self.metafunctions, self.symgen).run()
        return termtemplate
    
    def _visitRedexMatch(self, form):
        assert isinstance(form, tlform.RedexMatch)
        form.pat = self.__processpattern(form.pat, form.languagename)
        form.termstr = self.__processtermtemplate(form.termstr)
        return form

    def _visitMatchEqual(self, form):
        assert isinstance(form, tlform.MatchEqual)
        for i, match in enumerate(form.list_of_matches):
            assert isinstance(match, tlform.MatchEqual.Match)
            nbindings = []
            for (ident, term) in match.bindings:
                nterm = self.__processtermtemplate(term)
                nbindings.append((ident, nterm))
            match.bindings = nbindings
            
        form.redexmatch = self._visit(form.redexmatch)
        return form

    def _visitAssertTermsEqual(self, form):
        assert isinstance(form, tlform.AssertTermsEqual)
        variable_assignments = {}
        for ident, term in form.variableassignments.items(): 
            form.variableassignments[ident] = self.__processtermtemplate(term)
            
        form.template = self.__processtermtemplate(form.template, assignments=form.variabledepths)
        form.expected = self.__processtermtemplate(form.expected)
        return form

    def processReductionCase(self, reductioncase, languagename):
        assert isinstance(reductioncase, tlform.DefineReductionRelation.ReductionCase)
        reductioncase.pattern = self.__processpattern(reductioncase.pattern, languagename)
        assignablesymsdepths = reductioncase.pattern.getmetadata(pattern.PatAssignableSymbolDepths)
        reductioncase.termtemplate = self.__processtermtemplate(reductioncase.termtemplate, assignments=assignablesymsdepths.syms)

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
        form.term = self.__processtermtemplate(form.term)
        return form

    def _visitDefineMetafunction(self, form):
        assert isinstance(form, tlform.DefineMetafunction)
        self.metafunctions[form.contract.name] = form

        form.contract.domain = self.__processdomaincheck(form.contract.domain, form.languagename)
        form.contract.codomain = self.__processdomaincheck(form.contract.codomain, form.languagename)

        for i, case in enumerate(form.cases):
            form.cases[i].patternsequence = self.__processpattern(case.patternsequence, form.languagename)
            form.cases[i].termtemplate = self.__processtermtemplate(form.cases[i].termtemplate)

        return form

    def _visitAssertTermListsEqual(self, form):
        assert isinstance(form, tlform.AssertTermListsEqual)
        form.applyreductionrelation = self._visitApplyReductionRelation(form.applyreductionrelation)
        for i, termtemplate in enumerate(form.terms):
            idof = self.symgen.get('term_assert_term_lists_equal')
            form.terms[i] = Term_EllipsisDepthChecker({}, idof, self.context).transform(termtemplate) 
        return form


