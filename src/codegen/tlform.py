import src.model.tlform as tlform
import src.model.term as TERM
import src.model.rpython as rpy
import src.model.pattern as pattern

from src.codegen.pattern import PatternCodegen
from src.codegen.term    import TermCodegen

from src.util import SymGen
from src.context import CompilationContext

from src.codegen.common import TermHelperFuncs, MatchHelperFuncs, \
                          MatchMethodTable, TermKind, \
                          TermMethodTable

#------------------------------
# Top-level form codegen
#------------------------------
class TopLevelFormCodegen(tlform.TopLevelFormVisitor):
    def __init__(self, module, context):
        assert isinstance(module, tlform.Module)
        assert isinstance(context, CompilationContext)
        self.module = module
        self.context = context
        self.symgen = SymGen()
        self.modulebuilder = rpy.BlockBuilder() 

        self.main_procedurecalls = []

    def run(self):
        self.modulebuilder.IncludeFromPythonSource('runtime/term.py')
        self.modulebuilder.IncludeFromPythonSource('runtime/parser.py')
        self.modulebuilder.IncludeFromPythonSource('runtime/fresh.py')
        self.modulebuilder.IncludeFromPythonSource('runtime/match.py')

        # parse all term literals. 
        # ~~ 26.07.2020 disable lit terms for now, need to implement
        # nt caching acceleration technique first.
        """
        tmp0, tmp1 = rpy.gen_pyid_temporaries(2, self.symgen)
        for trm, sym1 in self.context._litterms.items():
            sym1 = rpy.gen_pyid_for(sym1)
            self.modulebuilder.AssignTo(tmp0).New('Parser', rpy.PyString(repr(trm)))
            self.modulebuilder.AssignTo(sym1).MethodCall(tmp0, 'parse')
        """

        # variable-not-otherwise-mentioned of given define language
        for ident, variables in self.context.get_variables_mentioned_all():
            ident = rpy.gen_pyid_for(ident)
            variables = map(lambda v: rpy.PyString(v), variables)
            self.modulebuilder.AssignTo(ident).PySet(*variables)

        
        for form in self.module.tlforms:
            self._visit(form)


        # generate main
        fb = rpy.BlockBuilder()
        symgen = SymGen()
        for procedure in self.main_procedurecalls:
            tmpi = rpy.gen_pyid_temporaries(1, symgen)
            fb.AssignTo(tmpi).FunctionCall(procedure)
        fb.Return.PyInt(0)
        self.modulebuilder.Function('entrypoint').Block(fb)

        #required entry procedure for Rpython.
        fb = rpy.BlockBuilder()
        fb.Return.PyTuple(rpy.PyId('entrypoint'), rpy.PyNone())
        self.modulebuilder.Function('target').WithParameters(rpy.PyVarArg('args')).Block(fb)

        # if __name__ == '__main__': entrypoint() 
        # for python2.7 compatibility.
        ifb = rpy.BlockBuilder()
        tmp = rpy.gen_pyid_temporaries(1, self.symgen)
        ifb.AssignTo(tmp).FunctionCall('entrypoint')
        self.modulebuilder.If.Equal(rpy.PyId('__name__'), rpy.PyString('__main__')).ThenBlock(ifb)

        return rpy.Module(self.modulebuilder.build())

    def _codegenNtDefinition(self, languagename, ntdef):
        assert isinstance(ntdef, tlform.DefineLanguage.NtDefinition)
        for pat in ntdef.patterns:
            if self.context.get_toplevel_function_for_pattern(languagename, repr(pat)) is None:
                PatternCodegen(self.modulebuilder, pat, self.context, languagename, self.symgen).run()
        
        nameof_this_func = 'lang_{}_isa_nt_{}'.format(languagename, ntdef.nt.prefix)
        term, match, matches = rpy.gen_pyid_for('term', 'match', 'matches')
        # for each pattern in ntdefinition
        # match = Match(...)
        # matches = matchpat(term, match, 0, 1)
        # if len(matches) != 0:
        #   return True
        fb = rpy.BlockBuilder()

        for pat in ntdef.patterns:
            func2call = self.context.get_toplevel_function_for_pattern(languagename, repr(pat))

            ifb = rpy.BlockBuilder()
            ifb.Return.PyBoolean(True)

            fb.AssignTo(matches).FunctionCall(func2call, term)
            fb.If.LengthOf(matches).NotEqual(rpy.PyInt(0)).ThenBlock(ifb)
        fb.Return.PyBoolean(False)

        self.modulebuilder.Function(nameof_this_func).WithParameters(term).Block(fb)
    
    def _visitDefineLanguage(self, form):
        assert isinstance(form, tlform.DefineLanguage)
        # generate hole for each language.  Need this for term annotation.
        hole = rpy.gen_pyid_for('{}_hole'.format(form.name))
        self.modulebuilder.AssignTo(hole).New('Hole')

        # first insert isa_nt functions intocontext
        for ntsym, ntdef in form.nts.items():
            nameof_this_func = 'lang_{}_isa_nt_{}'.format(form.name, ntsym)
            self.context.add_isa_function_name(form.name, ntdef.nt.prefix, nameof_this_func)

        for nt in form.nts.values():
            self._codegenNtDefinition(form.name, nt)

    def _visitRequirePythonSource(self, form):
        assert isinstance(form, tlform.RequirePythonSource)
        self.modulebuilder.IncludeFromPythonSource(form.filename)

    def _visitRedexMatch(self, form, callself=True):
        assert isinstance(form, tlform.RedexMatch)
        assert False
        if self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.pat)) is None:
            PatternCodegen(self.modulebuilder, form.pat, self.context, form.languagename, self.symgen).run()

        TermCodegen(self.modulebuilder, self.context).transform(form.termstr)
        termfunc = self.context.get_function_for_term_template(form.termstr)

        matchfunc = self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.pat))
        symgen = SymGen()

        matches, match, term = rpy.gen_pyid_for('matches', 'match', 'term') 
        tmp0 = rpy.gen_pyid_temporaries(1, symgen)

        fb = rpy.BlockBuilder()
        fb.AssignTo(tmp0).New('Match')
        fb.AssignTo(term).FunctionCall(termfunc, tmp0)
        fb.AssignTo(matches).FunctionCall(matchfunc, term)
        fb.Print(matches)
        fb.Return.PyId(matches)

        # call redex-match itself.
        nameof_this_func = self.symgen.get('redexmatch')
        self.context.add_redexmatch_for(form, nameof_this_func)
        self.modulebuilder.Function(nameof_this_func).Block(fb)


        if callself:
            tmp0 = rpy.gen_pyid_temporaries(1, self.symgen)
            self.modulebuilder.AssignTo(tmp0).FunctionCall(nameof_this_func)

    def _visitRedexMatchAssertEqual(self, form):
        def gen_matches(expectedmatches, fb, symgen):
            processedmatches = []
            for m in expectedmatches:
                tmp0 = rpy.gen_pyid_temporaries(1, symgen)
                fb.AssignTo(tmp0).New('Match')
                processedmatches.append(tmp0) 
                for sym, termx in m.bindings:
                    tmp1, tmp2, tmp3, tmp4 = rpy.gen_pyid_temporaries(4, symgen)
                    TermCodegen(self.modulebuilder, self.context).transform(termx)
                    termfunc = self.context.get_function_for_term_template(termx)
                    fb.AssignTo(tmp1).New('Match')
                    fb.AssignTo(tmp2).FunctionCall(termfunc, tmp1)
                    fb.AssignTo(tmp3).MethodCall(tmp0, MatchMethodTable.AddKey, rpy.PyString(sym))
                    fb.AssignTo(tmp4).MethodCall(tmp0, MatchMethodTable.AddToBinding, rpy.PyString(sym), tmp2)
            tmpi = rpy.gen_pyid_temporaries(1, symgen)
            fb.AssignTo(tmpi).PyList(*processedmatches)
            return tmpi

        assert isinstance(form, tlform.RedexMatchAssertEqual)
        if self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.pat)) is None:
            PatternCodegen(self.modulebuilder, form.pat, self.context, form.languagename, self.symgen).run()
        TermCodegen(self.modulebuilder, self.context).transform(form.termtemplate)
        matchfunc = self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.pat))
        termfunc  = self.context.get_function_for_term_template(form.termtemplate)
        symgen = SymGen()

        matches, match, term = rpy.gen_pyid_for('matches', 'match', 'term') 
        fb = rpy.BlockBuilder()
        expectedmatches = gen_matches(form.expectedmatches, fb, symgen)
        tmp0, tmp1, tmp2 = rpy.gen_pyid_temporaries(3, symgen)
        fb.AssignTo(tmp0).New('Match')
        fb.AssignTo(term).FunctionCall(termfunc, tmp0)
        fb.AssignTo(matches).FunctionCall(matchfunc, term)
        fb.AssignTo(tmp1).FunctionCall('assert_compare_match_lists', matches, expectedmatches)
        fb.AssignTo(tmp2).FunctionCall(MatchHelperFuncs.PrintMatchList, matches)
        fb.Return.PyId(matches)

        nameof_this_func = self.symgen.get('redexmatchassertequal')
        self.context.add_redexmatch_for(form, nameof_this_func)
        self.modulebuilder.Function(nameof_this_func).Block(fb)

        self.main_procedurecalls.append(nameof_this_func)

    def _visitTermLetAssertEqual(self, form):
        assert isinstance(form, tlform.TermLetAssertEqual)

        template = form.template
        TermCodegen(self.modulebuilder, self.context).transform(template)
        templatetermfunc = self.context.get_function_for_term_template(template)

        TermCodegen(self.modulebuilder, self.context).transform(form.expected)
        expectedtermfunc = self.context.get_function_for_term_template(form.expected)

        fb = rpy.BlockBuilder()
        symgen = SymGen()

        expected, match = rpy.gen_pyid_for('expected', 'match')
        tmp0 = rpy.gen_pyid_temporaries(1, symgen)


        fb.AssignTo(tmp0).New('Match')
        fb.AssignTo(expected).FunctionCall(expectedtermfunc, tmp0) 
        
        fb.AssignTo(match).New('Match')
        for variable, term in form.variableassignments.items():
            tmp1, tmp2, tmp3, tmp4 = rpy.gen_pyid_temporaries(4, symgen)

            TermCodegen(self.modulebuilder, self.context).transform(term)
            termfunc = self.context.get_function_for_term_template(term)

            fb.AssignTo(tmp1).New('Match')
            fb.AssignTo(tmp2).FunctionCall(termfunc, tmp1) 
            fb.AssignTo(tmp3).MethodCall(match, MatchMethodTable.AddKey, rpy.PyString(variable))
            fb.AssignTo(tmp4).MethodCall(match, MatchMethodTable.AddToBinding, rpy.PyString(variable), tmp2)

        tmp0, tmp1, tmp2 = rpy.gen_pyid_temporaries(3, symgen)
        fb.AssignTo(tmp0).FunctionCall(templatetermfunc, match)
        fb.AssignTo(tmp1).FunctionCall('asserttermsequal', tmp0, expected)
        fb.AssignTo(tmp2).FunctionCall(TermHelperFuncs.PrintTerm, tmp0)

        nameof_this_func = self.symgen.get('asserttermequal')
        self.modulebuilder.Function(nameof_this_func).Block(fb)
        self.main_procedurecalls.append(nameof_this_func)

    def _codegenReductionCase(self, rc, languagename, reductionrelationname, nameof_domaincheck=None):
        assert isinstance(rc, tlform.DefineReductionRelation.ReductionCase)

        if self.context.get_toplevel_function_for_pattern(languagename, repr(rc.pattern)) is None:
            PatternCodegen(self.modulebuilder, rc.pattern, self.context, languagename, self.symgen).run()
        TermCodegen(self.modulebuilder, self.context).transform(rc.termtemplate)

        nameof_matchfn = self.context.get_toplevel_function_for_pattern(languagename, repr(rc.pattern))
        nameof_termfn = self.context.get_function_for_term_template(rc.termtemplate)

        nameof_rc = self.symgen.get('{}_{}_case'.format(languagename, reductionrelationname))

        symgen = SymGen()
        # terms = []
        # matches = match(term)
        # if len(matches) != 0:
        #   for match in matches:
        #     tmp0 = gen_term(match)
        #     tmp2 = match_domain(tmp0)
        #     if len(tmp2) == 0:
        #       raise Exception('reduction-relation {}: term reduced from {} to {} via rule {} and is outside domain')
        #     tmp1 = terms.append(tmp0)
        # return terms

        terms, term, matches, match = rpy.gen_pyid_for('terms', 'term', 'matches', 'match')
        tmp0, tmp1, tmp2 = rpy.gen_pyid_temporaries(3, symgen)

        forb = rpy.BlockBuilder()
        forb.AssignTo(tmp0).FunctionCall(nameof_termfn, match)
        if nameof_domaincheck is not None:
            ifb = rpy.BlockBuilder()
            ifb.RaiseException('reduction-relation \\"{}\\": term reduced from %s to %s via rule \\"{}\\" is outside domain' \
                    .format(reductionrelationname, rc.name), 
                    term, tmp0)
            forb.AssignTo(tmp2).FunctionCall(nameof_domaincheck, tmp0)
            forb.If.LengthOf(tmp2).Equal(rpy.PyInt(0)).ThenBlock(ifb)
        forb.AssignTo(tmp1).MethodCall(terms, 'append', tmp0)

        ifb = rpy.BlockBuilder()
        ifb.For(match).In(matches).Block(forb)

        fb = rpy.BlockBuilder()
        fb.AssignTo(terms).PyList()
        fb.AssignTo(matches).FunctionCall(nameof_matchfn, term)
        fb.If.LengthOf(matches).NotEqual(rpy.PyInt(0)).ThenBlock(ifb)
        fb.Return.PyId(terms)

        self.modulebuilder.Function(nameof_rc).WithParameters(term).Block(fb)
        return nameof_rc

    def _visitDefineReductionRelation(self, form):
        assert isinstance(form, tlform.DefineReductionRelation)
        # def reduction_relation_name(term):
        #   outterms = []
        # {for each case}
        # tmpi = rc(term)
        # outterms = outterms + tmp{i} 
        # return outterms
        if form.domain != None:
            if self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.domain)) is None:
                PatternCodegen(self.modulebuilder, form.domain, self.context, form.languagename, self.symgen).run()

        nameof_domaincheck = None
        if form.domain != None:
            nameof_domaincheck = self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.domain))

        rcfuncs = []
        for rc in form.reductioncases:
            rcfunc = self._codegenReductionCase(rc, form.languagename, form.name, nameof_domaincheck)
            rcfuncs.append(rcfunc)
           
        terms, term = rpy.gen_pyid_for('terms', 'term')
        symgen = SymGen()

        fb = rpy.BlockBuilder()

        if nameof_domaincheck != None:
            tmp0 = rpy.gen_pyid_temporaries(1, symgen)
            ifb = rpy.BlockBuilder()
            ifb.RaiseException('reduction-relation not defined for %s', term)

            fb.AssignTo(tmp0).FunctionCall(nameof_domaincheck, term)
            fb.If.LengthOf(tmp0).Equal(rpy.PyInt(0)).ThenBlock(ifb)

        fb.AssignTo(terms).PyList()
        for rcfunc in rcfuncs:
            tmpi = rpy.gen_pyid_temporaries(1, symgen)
            fb.AssignTo(tmpi).FunctionCall(rcfunc, term)
            fb.AssignTo(terms).Add(terms, tmpi)
        fb.Return.PyId(terms)

        nameof_function = '{}_{}'.format(form.languagename, form.name)
        self.context.add_reduction_relation(form.name, nameof_function)
        self.modulebuilder.Function(nameof_function).WithParameters(term).Block(fb)
        return form

    # This generates call to reduction relation. Used by multiple other tlforms.
    def _genreductionrelation(self, fb, symgen, nameof_reductionrelation, term):
        TermCodegen(self.modulebuilder, self.context).transform(term)
        termfunc = self.context.get_function_for_term_template(term)

        term, terms = rpy.gen_pyid_for('term', 'terms')

        tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)
        fb.AssignTo(tmp0).New('Match')
        fb.AssignTo(term).FunctionCall(termfunc, tmp0)
        fb.AssignTo(terms).FunctionCall(nameof_reductionrelation, term)
        fb.AssignTo(tmp1).FunctionCall(TermHelperFuncs.PrintTermList, terms)
        return terms

    def _visitApplyReductionRelationAssertEqual(self, form):
        assert isinstance(form, tlform.ApplyReductionRelationAssertEqual)
        def gen_terms(termtemplates, fb, symgen):
            processed = []
            for expectedterm in termtemplates:
                TermCodegen(self.modulebuilder, self.context).transform(expectedterm)
                expectedtermfunc = self.context.get_function_for_term_template(expectedterm)
                tmpi, tmpj = rpy.gen_pyid_temporaries(2, symgen)
                fb.AssignTo(tmpi).New('Match')
                fb.AssignTo(tmpj).FunctionCall(expectedtermfunc, tmpi) 
                processed.append(tmpj)
            tmpi = rpy.gen_pyid_temporaries(1, symgen)
            fb.AssignTo(tmpi).PyList(*processed)
            return tmpi

        nameof_reductionrelation = self.context.get_reduction_relation(form.reductionrelationname)

        fb = rpy.BlockBuilder()
        symgen = SymGen()
        tmp0 = rpy.gen_pyid_temporaries(1, symgen)
        expectedterms = gen_terms(form.expected_termtemplates, fb, symgen)
        terms = self._genreductionrelation(fb, symgen, nameof_reductionrelation, form.term)
        fb.AssignTo(tmp0).FunctionCall(TermHelperFuncs.AssertTermListsEqual, terms, expectedterms)

        nameof_function = self.symgen.get('applyreductionrelationassertequal')
        self.modulebuilder.Function(nameof_function).Block(fb)
        self.main_procedurecalls.append(nameof_function)


    def _visitApplyReductionRelation(self, form):
        assert isinstance(form, tlform.ApplyReductionRelation)
        nameof_reductionrelation = self.context.get_reduction_relation(form.reductionrelationname)
        assert nameof_reductionrelation != None

        fb = rpy.BlockBuilder()
        symgen = SymGen()
        self._genreductionrelation(fb, symgen, nameof_reductionrelation, form.term)
        tmp1 = rpy.gen_pyid_temporaries(1, symgen)
        nameof_function = self.symgen.get('applyreductionrelation')
        self.modulebuilder.Function(nameof_function).Block(fb)
        self.modulebuilder.AssignTo(tmp1).FunctionCall(nameof_function)

    # metafunction case may produce multiple matches but after term plugging all terms
    # must be the same.
    def _codegenMetafunctionCase(self, metafunction, case, caseid, mfname):
        assert isinstance(metafunction, tlform.DefineMetafunction)
        assert isinstance(case, tlform.DefineMetafunction.MetafunctionCase)
        #def mfcase(argterm):
        #  tmp0 = matchfunc(argterm)
        #  tmp1 = []
        #  if len(tmp0) == 0:
        #    return tmp1 
        #  for tmp2 in tmp0:
        #    tmp3 = termfunc(tmp2)
        #    tmp4 = tmp1.append(tmp3)
        #  tmp5 = aretermsequalpairwise(tmp1)
        #  if tmp5 != True:
        #    raise Exception('mfcase 1 matched (term) in len(tmp{i}) ways, single match is expected')
        #  tmp6 = tmp1[0]
        #  return tmp6
        if self.context.get_toplevel_function_for_pattern(metafunction.languagename, repr(case.patternsequence)) is None:
            PatternCodegen(self.modulebuilder, case.patternsequence, self.context, metafunction.languagename, self.symgen).run()
        TermCodegen(self.modulebuilder, self.context).transform(case.termtemplate)
        matchfunc = self.context.get_toplevel_function_for_pattern(metafunction.languagename, repr(case.patternsequence))
        termfunc = self.context.get_function_for_term_template(case.termtemplate)

        symgen = SymGen()
        argterm = rpy.gen_pyid_for('argterm')
        tmp0, tmp1, tmp2, tmp3, tmp4, tmp5, tmp6 = rpy.gen_pyid_temporaries(7, symgen)

        ifb1 = rpy.BlockBuilder()
        ifb1.Return.PyId(tmp1)

        forb = rpy.BlockBuilder()
        forb.AssignTo(tmp3).FunctionCall(termfunc, tmp2)
        forb.AssignTo(tmp4).MethodCall(tmp1, 'append', tmp3)

        ifb2 = rpy.BlockBuilder()
        ifb2.RaiseException('meta-function {}: clause {} produced multiple terms when matching term %s' \
                           .format(metafunction.contract.name, caseid), argterm)

        fb = rpy.BlockBuilder()
        fb.AssignTo(tmp0).FunctionCall(matchfunc, argterm)
        fb.AssignTo(tmp1).PyList()
        fb.If.LengthOf(tmp0).Equal(rpy.PyInt(0)).ThenBlock(ifb1)
        fb.For(tmp2).In(tmp0).Block(forb)
        fb.AssignTo(tmp5).FunctionCall(TermHelperFuncs.AreTermsEqualPairwise, tmp1)
        fb.If.NotEqual(tmp5, rpy.PyBoolean(True)).ThenBlock(ifb2)
        fb.AssignTo(tmp6).ArrayGet(tmp1, rpy.PyInt(0))
        fb.Return.PyList(tmp6)

        nameof_function = self.symgen.get('{}_case'.format(mfname))
        self.modulebuilder.Function(nameof_function).WithParameters(argterm).Block(fb)
        return nameof_function

    def _visitDefineMetafunction(self, form):
        assert isinstance(form, tlform.DefineMetafunction)
        #def mf(argterm):
        #  tmp0 = domaincheck(argterm)
        #  if len(tmp0) == 0:
        #    raise Exception('mfname: term is not in my domain')
        #  { foreach reductioncase
        #  tmp{i} = mfcase(term)
        #  if len(tmp{i}) == 1:
        #    tmp{j} = tmp{i}[0]
        #    tmp{k} = codomaincheck(tmp{j})
        #    if len(tmp{k}) == 0:
        #      raise Exception('mfname: term not in my codomain')
        #    return tmp{j}
        #  }
        #  raise Exception('no metafuncion cases matched for term')
        mfname = form.contract.name
        nameof_function = self.symgen.get('metafunction')
        self.context.add_metafunction(mfname, nameof_function)

        if self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.contract.domain)) is None:
            PatternCodegen(self.modulebuilder, form.contract.domain, self.context, form.languagename, self.symgen).run()
        domainmatchfunc = self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.contract.domain))
        if self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.contract.codomain)) is None:
            PatternCodegen(self.modulebuilder, form.contract.codomain, self.context, form.languagename, self.symgen).run()
        codomainmatchfunc = self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.contract.codomain))


        symgen = SymGen()
        argterm = rpy.gen_pyid_for('argterm')
        tmp0, tmp1, tmp2 = rpy.gen_pyid_temporaries(3, symgen)

        ifbd = rpy.BlockBuilder()
        ifbd.RaiseException('meta-function {}: term %s not in my domain'.format(mfname), argterm)

        fb = rpy.BlockBuilder()
        fb.AssignTo(tmp0).FunctionCall(domainmatchfunc, argterm)
        fb.If.LengthOf(tmp0).Equal(rpy.PyInt(0)).ThenBlock(ifbd)
        
        for i, mfcase in enumerate(form.cases):
            tmpi, tmpj, tmpk = rpy.gen_pyid_temporaries(3, symgen)
            mfcasefunc = self._codegenMetafunctionCase(form, mfcase, i, nameof_function)

            ifbi1 = rpy.BlockBuilder()
            ifbi1.RaiseException('meta-function {}: term %s not in my codomain'.format(mfname), tmpj)

            ifbi2 = rpy.BlockBuilder()
            ifbi2.AssignTo(tmpj).ArrayGet(tmpi, rpy.PyInt(0))
            ifbi2.AssignTo(tmpk).FunctionCall(codomainmatchfunc, tmpj)
            ifbi2.If.LengthOf(tmpk).Equal(rpy.PyInt(0)).ThenBlock(ifbi1)
            ifbi2.Return.PyId(tmpj)

            fb.AssignTo(tmpi).FunctionCall(mfcasefunc, argterm)
            fb.If.LengthOf(tmpi).Equal(rpy.PyInt(1)).ThenBlock(ifbi2)

        fb.RaiseException('meta-function \\"{}\\": no clauses matches'.format(mfname))

        self.modulebuilder.Function(nameof_function).WithParameters(argterm).Block(fb)
        return nameof_function
