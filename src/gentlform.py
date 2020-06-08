import src.tlform as tlform
import src.term as TERM
import src.rpython as rpy
import src.pat as pattern

import src.genterm as genterm
import src.genpat  as genpat

from src.symgen  import SymGen
from src.context import CompilationContext

from src.gencommon import TermHelperFuncs, MatchHelperFuncs, \
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

    def run(self):
        self.modulebuilder.IncludeFromPythonSource('runtime/term.py')
        self.modulebuilder.IncludeFromPythonSource('runtime/parser.py')
        self.modulebuilder.IncludeFromPythonSource('runtime/match.py')

        # parse all term literals. 
        tmp0, tmp1 = rpy.gen_pyid_temporaries(2, self.symgen)
        for trm, sym1 in self.context._litterms.items():
            sym1 = rpy.gen_pyid_for(sym1)
            self.modulebuilder.AssignTo(tmp0).New('Parser', rpy.PyString(repr(trm)))
            self.modulebuilder.AssignTo(sym1).MethodCall(tmp0, 'parse')

        # variable-not-otherwise-mentioned of given define language
        for ident, variables in self.context.get_variables_mentioned_all():
            ident = rpy.gen_pyid_for(ident)
            variables = map(lambda v: rpy.PyString(v), variables)
            self.modulebuilder.AssignTo(ident).PySet(*variables)

        hole = rpy.gen_pyid_for('hole')
        self.modulebuilder.AssignTo(hole).New('Hole')
        
        for form in self.module.tlforms:
            self._visit(form)

        return rpy.Module(self.modulebuilder.build())

    def _codegenNtDefinition(self, languagename, ntdef):
        assert isinstance(ntdef, tlform.DefineLanguage.NtDefinition)
        for pat in ntdef.patterns:
            if self.context.get_toplevel_function_for_pattern(languagename, repr(pat)) is None:
                genpat.PatternCodegen(self.modulebuilder, pat, self.context, languagename, self.symgen).run()
        
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
        # first insert isa_nt functions intocontext
        for ntsym, ntdef in form.nts.items():
            nameof_this_func = 'lang_{}_isa_nt_{}'.format(form.name, ntsym)
            self.context.add_isa_function_name(form.name, ntdef.nt.prefix, nameof_this_func)

        for nt in form.nts.values():
            self._codegenNtDefinition(form.name, nt)

    def _visitRequirePythonSource(self, form):
        assert isinstance(form, tlform.RequirePythonSource)
        self.modulebuilder.IncludeFromPythonSource(form.filename)

    def _visitRedexMatch(self, form):
        assert isinstance(form, tlform.RedexMatch)
        if self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.pat)) is None:
            genpat.PatternCodegen(self.modulebuilder, form.pat, self.context, form.languagename, self.symgen).run()

        func2call = self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.pat))
        symgen = SymGen()

        matches, match, term = rpy.gen_pyid_for('matches', 'match', 'term') 
        tmp0 = rpy.gen_pyid_temporaries(1, symgen)

        fb = rpy.BlockBuilder()
        fb.AssignTo(tmp0).New('Parser', rpy.PyString(repr(form.termstr)))
        fb.AssignTo(term).MethodCall(tmp0, 'parse') 
        fb.AssignTo(matches).FunctionCall(func2call, term)
        fb.Print(matches)

        # call redex-match itself.
        nameof_this_func = self.symgen.get('redexmatch')
        tmp0 = rpy.gen_pyid_temporaries(1, self.symgen)
        self.modulebuilder.Function(nameof_this_func).Block(fb)
        self.modulebuilder.AssignTo(tmp0).FunctionCall(nameof_this_func)

    def _visitMatchEqual(self, form):
        assert isinstance(form, tlform.MatchEqual)
        if self.context.get_toplevel_function_for_pattern(form.redexmatch.languagename, repr(form.redexmatch.pat)) is None:
            genpat.PatternCodegen(self.modulebuilder, form.redexmatch.pat, self.context, form.redexmatch.languagename, self.symgen).run()

        fb = rpy.BlockBuilder()
        symgen = SymGen()

        # FIXME CODE DUPLICATION - see redex-match
        matches, match, term = rpy.gen_pyid_for('matches', 'match', 'term') 
        tmp0, tmp1, tmp2 = rpy.gen_pyid_temporaries(3, symgen)
        func2call = self.context.get_toplevel_function_for_pattern(form.redexmatch.languagename, repr(form.redexmatch.pat))

        fb = rpy.BlockBuilder()
        fb.AssignTo(tmp0).New('Parser', rpy.PyString(repr(form.redexmatch.termstr)))
        fb.AssignTo(term).MethodCall(tmp0, 'parse') 
        fb.AssignTo(matches).FunctionCall(func2call, term)
        fb.Print(matches)
        # ----- End code duplication
        processedmatches = []
        for m in form.list_of_matches:
            tmp0 = rpy.gen_pyid_temporaries(1, symgen)
            fb.AssignTo(tmp0).New('Match')
            processedmatches.append(tmp0) 

            for sym, termx in m.bindings:
                tmp1, tmp2, tmp3, tmp4 = rpy.gen_pyid_temporaries(4, symgen)

                fb.AssignTo(tmp1).New('Parser', rpy.PyString(repr(termx)))
                fb.AssignTo(tmp2).MethodCall(tmp1, 'parse')
                fb.AssignTo(tmp3).MethodCall(tmp0, MatchMethodTable.AddKey, rpy.PyString(sym))
                fb.AssignTo(tmp4).MethodCall(tmp0, MatchMethodTable.AddToBinding, rpy.PyString(sym), tmp2)

        tmp5, tmp6 = rpy.gen_pyid_temporaries(2, symgen)
        fb.AssignTo(tmp5).PyList(*processedmatches)
        fb.AssignTo(tmp6).FunctionCall('assert_compare_match_lists', matches, tmp5)

        tmp0 = rpy.gen_pyid_temporaries(1, self.symgen)
        nameof_this_func = self.symgen.get('assertmatchequals')
        self.modulebuilder.Function(nameof_this_func).Block(fb)
        self.modulebuilder.AssignTo(tmp0).FunctionCall(nameof_this_func)

    def _visitAssertTermsEqual(self, form):
        assert isinstance(form, tlform.AssertTermsEqual)
        template = form.template
        template = genterm.TermCodegen(self.modulebuilder, self.context).transform(template)

        fb = rpy.BlockBuilder()
        symgen = SymGen()

        expected, match = rpy.gen_pyid_for('expected', 'match')

        tmp0 = rpy.gen_pyid_temporaries(1, symgen)
        fb.AssignTo(tmp0).New('Parser', rpy.PyString(repr(form.literal)))
        fb.AssignTo(expected).MethodCall(tmp0, 'parse') 

        fb.AssignTo(match).New('Match')
        for variable, term in form.variableassignments.items():
            tmp1, tmp2, tmp3, tmp4 = rpy.gen_pyid_temporaries(4, symgen)
            fb.AssignTo(tmp1).New('Parser', rpy.PyString(repr(term)))
            fb.AssignTo(tmp2).MethodCall(tmp1, 'parse')
            fb.AssignTo(tmp3).MethodCall(match, MatchMethodTable.AddKey, rpy.PyString(variable))
            fb.AssignTo(tmp4).MethodCall(match, MatchMethodTable.AddToBinding, rpy.PyString(variable), tmp2)

        funcname = template.getattribute(TERM.TermAttribute.FunctionName)[0]
        tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)
        fb.AssignTo(tmp0).FunctionCall(funcname, match)
        fb.Print(tmp0)
        fb.AssignTo(tmp1).FunctionCall('asserttermsequal', tmp0, expected)

        nameof_this_func = self.symgen.get('asserttermequal')
        self.modulebuilder.Function(nameof_this_func).Block(fb)
        self.modulebuilder.AssignTo(tmp1).FunctionCall(nameof_this_func)

    def _codegenReductionCase(self, rc, languagename, reductionrelationname):
        assert isinstance(rc, tlform.DefineReductionRelation.ReductionCase)

        if self.context.get_toplevel_function_for_pattern(languagename, repr(rc.pattern)) is None:
            genpat.PatternCodegen(self.modulebuilder, rc.pattern, self.context, languagename, self.symgen).run()
        genterm.TermCodegen(self.modulebuilder, self.context).transform(rc.termtemplate)

        nameof_matchfn = self.context.get_toplevel_function_for_pattern(languagename, repr(rc.pattern))
        nameof_termfn  = rc.termtemplate.getattribute(TERM.TermAttribute.FunctionName)[0]

        nameof_rc = self.symgen.get('{}_{}_case'.format(languagename, reductionrelationname))

        symgen = SymGen()
        # terms = []
        # matches = match(term)
        # if len(matches) != 0:
        #   for match in matches:
        #     tmp0 = gen_term(match)
        #     tmp1 = terms.append(tmp0)
        # return terms

        terms, term, matches, match = rpy.gen_pyid_for('terms', 'term', 'matches', 'match')
        tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)

        forb = rpy.BlockBuilder()
        forb.AssignTo(tmp0).FunctionCall(nameof_termfn, match)
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
        if self.context.get_toplevel_function_for_pattern(form.languagename, repr(form.domain)) is None:
            genpat.PatternCodegen(self.modulebuilder, form.domain, self.context, form.languagename, self.symgen).run()

        rcfuncs = []
        for rc in form.reductioncases:
            rcfunc = self._codegenReductionCase(rc, form.languagename, form.name)
            rcfuncs.append(rcfunc)
           
        terms, term = rpy.gen_pyid_for('terms', 'term')
        symgen = SymGen()

        fb = rpy.BlockBuilder()
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

    def _genreductionrelation(self, fb, symgen, nameof_reductionrelation, reprof):
        term, terms = rpy.gen_pyid_for('term', 'terms')
        tmp0 = rpy.gen_pyid_temporaries(1, symgen)
        fb.AssignTo(tmp0).New('Parser', rpy.PyString(reprof))
        fb.AssignTo(term).MethodCall(tmp0, 'parse') 
        fb.AssignTo(terms).FunctionCall(nameof_reductionrelation, term)
        fb.Print(terms)
        return terms

    def _visitApplyReductionRelation(self, form):
        assert isinstance(form, tlform.ApplyReductionRelation)
        nameof_reductionrelation = self.context.get_reduction_relation(form.reductionrelationname)
        assert nameof_reductionrelation != None

        fb = rpy.BlockBuilder()
        symgen = SymGen()
        self._genreductionrelation(fb, symgen, nameof_reductionrelation, repr(form.term))
        tmp1 = rpy.gen_pyid_temporaries(1, symgen)
        nameof_function = self.symgen.get('applyreductionrelation')
        self.modulebuilder.Function(nameof_function).Block(fb)
        self.modulebuilder.AssignTo(tmp1).FunctionCall(nameof_function)

    def _visitAssertTermListsEqual(self, form):
        assert isinstance(form, tlform.AssertTermListsEqual)
        symgen = SymGen()
        expectedterms = rpy.gen_pyid_for('expectedterms')

        fb = rpy.BlockBuilder()
        fb.AssignTo(expectedterms).PyList()
        for term in form.terms:
            tmpi, tmpj, tmpk = rpy.gen_pyid_temporaries(3, symgen)
            fb.AssignTo(tmpi).New('Parser', rpy.PyString(repr(term)))
            fb.AssignTo(tmpj).MethodCall(tmpi, 'parse') 
            fb.AssignTo(tmpk).MethodCall(expectedterms, 'append', tmpj)

        nameof_reductionrelation = self.context.get_reduction_relation(form.applyreductionrelation.reductionrelationname)
        assert nameof_reductionrelation != None
        
        terms = self._genreductionrelation(fb, symgen, nameof_reductionrelation, repr(form.applyreductionrelation.term))

        tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)
        fb.AssignTo(tmp0).FunctionCall(TermHelperFuncs.AssertTermListsEqual, terms, expectedterms)

        nameof_function = self.symgen.get('asserttermlistsequal_')
        self.modulebuilder.Function(nameof_function).Block(fb)
        self.modulebuilder.AssignTo(tmp1).FunctionCall(nameof_function)
