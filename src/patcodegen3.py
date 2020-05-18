import src.astdefs as ast
import src.term as TERM 
import src.genterm as genterm
from src.preprocdefinelang import LanguageContext
from src.symgen import SymGen
from src.common import SourceWriter, Var
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



class RetrieveBindableElements(ast.PatternTransformer):
    def __init__(self):
        self.bindables = []

    def transformNt(self, node):
        self.bindables.append(node)
        return node

    def transformCheckConstraint(self, node):
        return node

    def transformBuiltInPat(self, node):
        assert isinstance(node, ast.BuiltInPat)
        if node.kind != ast.BuiltInPatKind.Hole:
            self.bindables.append(node)
        return node

# FIXME should be refactored even more - need a way to generate code in typesafe manner.
# (i.e. as code is written types of variables are checked for errors and such...)
class DefineLanguagePatternCodegen3(ast.PatternTransformer):
    def __init__(self, writer, context):
        assert isinstance(context, LanguageContext)
        assert isinstance(writer, SourceWriter)
        self.symgen = SymGen()
        self.writer = writer 
        self.context = context

        self.modulebuilder = rpy.BlockBuilder()

    def transformDefineLanguage(self, node):
        assert isinstance(node, ast.DefineLanguage)

        var, variables = self.context.get_variables_mentioned()
        self.writer += '{} = set({})'.format(var, list(variables))
        self.writer.newline()


        self.definelanguage = node
        for nt in node.nts.values():
            self.transform(nt)

    def transformMatchEqual(self, me):
        assert isinstance(me, ast.MatchEqual)

        self.transform(me.redexmatch)
        matches = Var('matches') # just because we define matches in redex-match 

        expected_matches, match = Var('expected_matches'), Var('match') 
        processed_matches = []
        for m in me.list_of_matches:
            current_match = self.symgen.get('match_to_compare')
            processed_matches.append(current_match)
            self.writer += '{} = Match()'.format(current_match)
            self.writer.newline()
            for sym, term in m.bindings:
                self.writer += '{} = Parser(\"{}\").parse()'.format(sym, term)
                self.writer.newline()
                self.writer += '{}.{}(\"{}\")'.format(current_match, MatchMethodTable.AddKey, sym)
                self.writer.newline()
                self.writer += '{}.{}(\"{}\", {})'.format(current_match, MatchMethodTable.AddToBinding, sym, sym)
                self.writer.newline()
        
        list_of_matches = self.symgen.get('list_of_matches')
        self.writer += '{} = ['.format(list_of_matches)
        for m in processed_matches:
            self.writer += '{}, '.format(m)
        self.writer += ']'.format()
        self.writer.newline()
        self.writer += 'assert_compare_match_lists({}, {})'.format(matches, list_of_matches)
        self.writer.newline()


    def transformAssertTermsEqual(self, termlet):
        assert isinstance(termlet, ast.AssertTermsEqual)
        idof = self.symgen.get('termlet')
        template = genterm.TermAnnotate(termlet.variable_assignments, idof, self.context).transform(termlet.template)
        for term, sym in self.context._litterms.items():
            self.writer += '{} = Parser(\"{}\").parse()'.format(sym, term)
            self.writer.newline()

        compareto = self.symgen.get('expected')
        self.writer += '{} = Parser(\"{}\").parse()'.format(compareto, termlet.literal)
        self.writer.newline()

        result = self.symgen.get()


        template = genterm.TermCodegen(self.writer, self.context).transform(template)
        funcname = template.getattribute(TERM.TermAttribute.FunctionName)[0]

        match = Var(self.symgen.get('match'))

        self.writer += '{} = Match()'.format(match)
        self.writer.newline()

        for variable, (_, term) in termlet.variable_assignments.items():
            self.writer += '{} = Parser(\"{}\").parse()'.format(variable, term)
            self.writer.newline()
            self.writer += '{}.{}(\"{}\")'.format(match, MatchMethodTable.AddKey, variable)
            self.writer.newline()
            self.writer += '{}.{}(\"{}\", {})'.format(match, MatchMethodTable.AddToBinding, variable, variable)
            self.writer.newline()
        self.writer += '{} = {}({})'.format(result, funcname, match)
        self.writer.newline()
        self.writer += 'print({})'.format(result)
        self.writer.newline()
        self.writer += 'assert {} == {}'.format(result, compareto)
        self.writer.newline()


    def transformRedexMatch(self, node):
        assert isinstance(node, ast.RedexMatch)
        
        self.transform(node.pat)
        fnname = self.context.get_function_for_pattern(repr(node.pat))

        matches, match = Var('matches'), Var('match') 
        term = Var(self.symgen.get('term'))
        self.writer += '{} = Parser(\"{}\").parse()'.format(term, node.termstr)
        self.writer.newline()

        if isinstance(node.pat, ast.BuiltInPat) and node.pat.kind == ast.BuiltInPatKind.InHole:
            self.writer += '{} = {}({})'.format(matches, fnname, term)
            self.writer.newline()
            self.writer += 'print({})'.format(matches)
            self.writer.newline()
            return


        rbe = RetrieveBindableElements()
        rbe.transform(node.pat)
        bindables = list(map(lambda x: x.sym,   rbe.bindables))
        self.writer += '{} = Match({})'.format(match, list(set(bindables)))
        self.writer.newline()
        self.writer += '{} = {}({}, {}, {}, {})'.format(matches, fnname, term, match, 0, 1)
        self.writer.newline()
        self.writer += 'print({})'.format(matches)
        self.writer.newline()

    def transformNtDefinition(self, node):
        assert isinstance(node, ast.NtDefinition)
        if not self.context.get_isa_function_name(node.nt.prefix):
            this_function_name = 'lang_{}_isa_nt_{}'.format('bla', node.nt.prefix)
            self.context.add_isa_function_name(node.nt.prefix, this_function_name)

            # codegen patterns first
            for pat in node.patterns: 
                self.transform(pat)

            term, match, matches = rpy.gen_pyid_for('term', 'match', 'matches')

            # for each pattern in ntdefinition
            # match = Match(...)
            # matches = matchpat(term, match, 0, 1)
            # if len(matches) != 0:
            #   return True
            fb = rpy.BlockBuilder()

            for pat in node.patterns:
                rbe = RetrieveBindableElements()
                rbe.transform(pat)
                bindables = list(map(lambda x: x.sym,   rbe.bindables))
                functionname = self.context.get_function_for_pattern(repr(pat))

                ifb = rpy.BlockBuilder()
                ifb.Return.PyBoolean(True)

                fb.AssignTo(match).New('Match', tuple(set(bindables)))
                fb.AssignTo(matches).FunctionCall(functionname, term, match, rpy.PyInt(0), rpy.PyInt(1))
                fb.If.LengthOf(matches).NotEqual(rpy.PyInt(0)).ThenBlock(ifb)
            fb.Return.PyBoolean(False)

            self.modulebuilder.Function(this_function_name).WithParameters(term).Block(fb)

    def transformPatSequence(self, seq):
        assert isinstance(seq, ast.PatSequence)
        if not self.context.get_function_for_pattern(repr(seq)):
            match_fn = 'match_term_{}'.format(self.symgen.get())
            self.context.add_function_for_pattern(repr(seq), match_fn)
            
            # generate code for all elements of the sequence.
            for pat in seq:
                if not isinstance(pat, ast.CheckConstraint):
                    self.transform(pat)

            # symgen for the function
            symgen = SymGen()
            term, match, head, tail = rpy.gen_pyid_for('term', 'match', 'head', 'tail')
            m, h, t = rpy.gen_pyid_for('m', 'h', 't')
            subhead, subtail = rpy.gen_pyid_for('subhead', 'subtail')

            fb = rpy.BlockBuilder()

            # ensure term is actually a sequence.
            #
            # tmp{i} = term.kind()
            # if tmp{i} != TermKind.Sequence:
            #   return []
            tmpi = rpy.gen_pyid_temporaries(1, symgen)

            ifb = rpy.BlockBuilder()
            ifb.Return.PyList()
            
            fb.AssignTo(tmpi).MethodCall(term, TermMethodTable.Kind)
            fb.If.NotEqual(tmpi, rpy.PyInt(TermKind.Sequence)).ThenBlock(ifb)

            # 'enter' the term
            # subhead = 0
            # subtail = term.length()
            fb.AssignTo(subhead).PyInt(0)
            fb.AssignTo(subtail).MethodCall(term, TermMethodTable.Length)

            # ensure number of terms in the sequence is at least equal to number of non Repeat patterns. 
            # if num_required is zero, condition is always false.
            # tmp{i} = subtail - subhead
            # if tmp{i} < num_required:
            #   return []
            num_required = seq.get_number_of_nonoptional_matches_between(0, len(seq))
            tmpi = rpy.gen_pyid_temporaries(1, symgen)

            ifb = rpy.BlockBuilder()
            ifb.Return.PyList()

            fb.AssignTo(tmpi).Subtract(subhead, subtail).
            fb.If.LessThan(tmpi, rpy.PyInt(num_required)).ThenBlock(ifb)

            # stick initial match object into array - simplifies codegen.
            previousmatches = rpy.gen_pyid_for('matches')
            self.writer += '{} = [({}, {}, {})]'.format(pmatches, match, subhead, subtail)
            self.writer.newline()


            for i, pat in enumerate(seq):
                matches = symgen.get('matches')
                self.writer += '#{}'.format(repr(pat))
                self.writer.newline()

                matches = rpy.gen_pyid_temporary_with_sym('matches', symgen)

                if isinstance(pat, ast.Repeat) or isinstance(pat, ast.PatSequence):
                    # matches{i} = [] # get temporary with symbol
                    # for m,h,t in matches{i-1}:
                    #   tmp{i} = matchfn(term, m, h, t)   // if pat IS repeat
                    #   tmp{j} = term.get(h)              // if pat IS NOT repeat
                    #   tmp{i} = matchfn(tmp{j}, m, h, t) // if pat IS NOT repeat 
                    #   matches{i} = matches{i} + tmp{i}
                    functionname = self.context.get_function_for_pattern(repr(pat))

                    tmpi, tmpj  = rpy.gen_pyid_temporaries(2, symgen)
                    forb = rpy.BlockBuilder()
                    if isinstance(pat, ast.Repeat):
                        forb.AssignTo(tmpi).FunctionCall(functionname, term, m, h, t)
                    else:
                        forb.AssignTo(tmpj).MethodCall(term, TermMethodTable.Get, h)
                        forb.AssignTo(tmpi).FunctionCall(functionname, tmpj, m, h, t)
                    forb.AssignTo(matches).Add(matches, tmpi)
                    fb.For(m, h, t).In(previousmatches)

                    # ensure number of terms in the sequence is at least equal to number of non Repeat patterns after 
                    # this repeat pattern.
                    #
                    # matches{i} = []
                    # for m, h, t in matches{i-1}:
                    #   tmp{i} = t - h
                    #   if tmp{i} >= num_required:
                    #     tmp{j} = matches{i}.append((m, h, t))
                    # if len(matches{i}) == 0:
                    #   return matches{i} 
                    if isinstance(pat, ast.Repeat):
                        num_required = seq.get_number_of_nonoptional_matches_between(i, len(seq))
                        if num_required > 0:
                            matches = rpy.gen_pyid_temporary_with_sym('matches', symgen)
                            tmpi, tmpj  = rpy.gen_pyid_temporaries(2, symgen)

                            ifb1 = rpy.BlockBuilder()
                            ifb1.AssignTo(tmpj).MethodCall(matches, 'append', rpy.PyTuple(m, h, t))

                            forb = rpy.BlockBuilder()
                            forb.AssignTo(tmpi).Subtract(t, h)
                            forb.If.GreaterEqual(tmpi, rpy.PyInt(num_required)).ThenBlock(ifb1)

                            ifb2 = rpy.BlockBuilder()
                            ifb2.Return.PyId(matches)

                            fb.AssignTo(matches).PyList()
                            fb.For(m, h, t).In(previousmatches).Block(forb)
                            fb.If.LengthOf(matches).Equal(rpy.PyInt(0)).ThenBlock(ifb2)

                            previousmatches = matches
                            
                elif isinstance(pat, ast.CheckConstraint):
                    # matches{i} = []
                    # for m, h, t in matches{i-1}:
                    #   tmp{i} = m.CompareKeys(sym1, sym2)
                    #   if tmp{i} == True:
                    #     tmp{j} = matches{i}.append( (m, h, t) )
                    # if len(matches{i}) == 0:
                    #   return matches{i} 
                    tmpi, tmpj  = rpy.gen_pyid_temporaries(2, symgen)

                    ifb1 = rpy.BlockBuilder()
                    ifb1.AssignTo(tmpj).MethodCall(matches, 'append', rpy.PyTuple(m, h, t))

                    forb = rpy.BlockBuilder()
                    forb.AssignTo(tmpi).MethodCall(m, MatchMethodTable.CompareKeys, rpy.PyString(pat.sym1), rpy.PyString(pat.sym2))
                    forb.If.Equal(tmpi, rpy.PyBoolean(True)).ThenBlock(ifb1)

                    ifb2 = rpy.BlockBuilder()
                    ifb2.Return.PyId(matches)

                    fb.AssignTo(matches).PyList()
                    fb.For(m, h, t).In(previousmatches).Block(forb)
                    fb.If.LengthOf(matches).Equal(rpy.PyInt(0)).ThenBlock(ifb2)

                else:
                    # matches{i} = []
                    # for m, h, t in matches{i-1}:
                    #   tmp{i} = func(term, m, h, t)
                    #   matches{i} = matches{i} + tmp{i}
                    # if len(matches{i}) == 0: 
                    #   return  matches{i} 
                    function = self.context.get_function_for_pattern(repr(pat))
                    tmpi = rpy.gen_pyid_temporaries(1, symgen)

                    forb = rpy.BlockBuilder()
                    forb.AssignTo(tmpi).FunctionCall(function, term, m, h, t)
                    forb.AssignTo(matches).Add(matches, tmpi)

                    ifb1 = rpy.BlockBuilder()
                    ifb1.Return.PyId(matches)

                    fb.AssignTo(matches).PyList()
                    fb.For(m, h, t).In(previousmatches).Block(forb)
                    fb.If.LengthOf(matches).Equal(rpy.PyInt(0)).ThenBlock(ifb1)

               previousmatches = matches 

            # exit term
            # 
            # matches{i} = []
            # for m, h, t in matches{i-1}:
            #   if h == t:
            #     head = head + 1
            #     tmp{i} = (m, head, tail)
            #     tmp{j} = matches{i}.append(tmp{i})
            # return matches{i}
            tmpi, tmpj = rpy.gen_pyid_temporaries(2, symgen)
            matches = rpy.gen_pyid_temporary_with_sym('matches', symgen)

            fb.AssignTo(matches).PyList()

            ifb = rpy.BlockBuilder()
            ifb.AssignTo(head).Add(head, rpy.PyInt(1))
            ifb.AssignTo(tmpi).PyTuple(m, head, tail)
            ifb.AssignTo(tmpj).MethodCall(matches, 'append', tmpi)

            forb = rpy.BlockBuilder()
            forb.If.Equal(h, t).ThenBlock(ifb)

            fb.AssignTo(matches).PyList()
            fb.For(m, h, t).In(previousmatches).Block(forb)
            fb.Return.PyId(matches)

            self.modulebuilder.SingleLineComment(repr(seq))
            self.modulebuilder.Function(match_fn).WithParameters(term, match, head, tail).Block(fb)

    def transformRepeat(self, repeat):
        assert isinstance(repeat, ast.Repeat)
        if not self.context.get_function_for_pattern(repr(repeat)):
            match_fn = 'match_term_{}'.format(self.symgen.get())
            self.context.add_function_for_pattern(repr(repeat), match_fn)

            # codegen enclosed pattern 
            self.transform(repeat.pat)

            functionname = self.context.get_function_for_pattern(repr(repeat.pat))

            # retrieve all bindable elements
            rbe = RetrieveBindableElements()
            rbe.transform(repeat.pat)

            symgen = SymGen()
            term, match, head, tail = rpy.gen_pyid_for('term', 'match', 'head', 'tail')
            matches, queue = rpy.gen_pyid_for('matches', 'queue')
            m, h, t = rpy.gen_pyid_for('m', 'h', 't')
            tmp0, tmp1, tmp2, tmp3, tmp4 = rpy.gen_pyid_temporaries(5, symgen)

            # tmp0 = match.increasedepth(...)
            # tmp1 = (match, head, tail)
            # matches = [ tmp1 ]
            # queue   = [ tmp1 ]
            # while len(queue) != 0:
            #   m, h, t = queue.pop(0)
            #   if h == t:
            #      continue
            #   m = m.copy()
            #   tmp2 = term.get[h]
            #   tmp3 = match_term(tmp2, m, h, t)
            #   matches = matches + tmp3
            #   queue   = queue + tmp3
            # for m, h, t in matches:
            #   tmp4 = m.decreasedepth(...)
            # return matches
            ifb = rpy.BlockBuilder()
            ifb.Continue

            wb = rpy.BlockBuilder()
            wb.AssignTo(m, h, t).MethodCall(queue, 'pop', rpy.PyInt(0))
            wb.If.Equal(h, t).ThenBlock(ifb)
            wb.AssignTo(m).MethodCall(m, MatchMethodTable.Copy)
            wb.AssignTo(tmp2).MethodCall(term, TermMethodTable.Get, h)
            wb.AssignTo(tmp3).FunctionCall(functionname, tmp2, m, h, t)
            wb.AssignTo(matches).Add(matches, tmp3)
            wb.AssignTo(queue).Add(queue, tmp3)

            forb = rpy.BlockBuilder()
            for bindable in rbe.bindables:
                forb.AssignTo(tmp4).MethodCall(match, MatchMethodTable.DecreaseDepth, rpy.PyString(bindable.sym))

            fb = rpy.BlockBuilder()
            for bindable in rbe.bindables:
                fb.AssignTo(tmp0).MethodCall(match, MatchMethodTable.IncreaseDepth, rpy.PyString(bindable.sym))
            fb.AssignTo(tmp1).PyTuple(match, head, tail)
            fb.AssignTo(matches).PyList(tmp1)
            fb.AssignTo(queue).PyList(tmp1)
            fb.While.LengthOf(queue).NotEqual(rpy.PyInt(0)).Block(wb)
            fb.For(m, h, t).In(matches).Block(forb)
            fb.Return(matches)

            self.modulebuilder.SingleLineComment('{} non-deterministic'.format(repr(repeat)))
            self.modulebuilder.Function(match_fn).WithParameters(term, match, head, tail).Block(fb)

    # Most matching functions for builtins/nt are the same - call isa function on term and 
    # add binding.
    def _gen_match_function_for_primitive(self, functionname, isafunction, patstr, sym=None):
        # tmp0 = asafunction(term)
        # if tmp0 == True:
        #   tmp1 = match.addtobinding(sym, term) # this is optional of sym != None; useful for holes.
        #   head = head + 1
        #   return [(match, head, tail)]
        # return []
        symgen = SymGen()
        term, match, head, tail = rpy.gen_pyid_for('term', 'match', 'head', 'tail')
        tmp0, tmp1 = rpy.gen_pyid_temporaries(1, symgen)

        ifb1 = rpy.BlockBuilder()
        if sym is not None:
            ifb1.AssignTo(tmp0).MethodCall(match, MatchMethodTable.AddToBinding, rpy.PyString(sym), term)
        ifb1.AssignTo(head).Add(head, rpy.PyInt(1))
        ifb1.Return.PyList( rpy.PyTuple(match, head, tail) )

        fb = rpy.BlockBuilder()
        fb.AssignTo(tmp0).FunctionCall(isafunction, term)
        fb.If.Equal(tmp0, rpy.PyBoolean(True)).ThenBlock(ifb1)
        fb.Return.PyList()

        self.modulebuilder.SingleLineComment(patstr)
        self.modulebuilder.Function(functionname).WithParameters(term, match, head, tail).Block(fb)

    def transformNt(self, nt):
        assert isinstance(nt, ast.Nt)
        if not self.context.get_function_for_pattern(repr(nt)):
            
            # first generate isa for NtDefinition 
            if not self.context.get_isa_function_name(nt.prefix):
                self.transform(self.definelanguage.nts[nt.prefix])

            match_fn = 'lang_{}_match_nt_{}'.format('blah', self.symgen.get())
            self.context.add_function_for_pattern(repr(nt), match_fn)
            isafunction = self.context.get_isa_function_name(nt.prefix)
            self._gen_match_function_for_primitive(match_fn, isafunction, repr(nt), sym=nt.sym

    def transformBuiltInPat(self, pat):
        assert isinstance(pat, ast.BuiltInPat)

        if pat.kind == ast.BuiltInPatKind.Number:
            if not self.context.get_isa_function_name(pat.prefix):
                functionname = 'lang_{}_isa_builtin_{}'.format(self.definelanguage.name, pat.prefix)
                self.context.add_isa_function_name(pat.prefix, functionname)

                # FIXME code duplication
                # tmp0 = term.kind()
                # if tmp0 == TermKind.Integer:
                #  return True
                # return False
                symgen = SymGen()

                term = rpy.gen_pyid_for('term')
                tmp0 = rpy.gen_pyid_temporaries(2, symgen)
                fb = rpy.BlockBuilder()

                ifb = rpy.BlockBuilder()
                ifb.Return.PyBoolean(True)

                fb = rpy.BlockBuilder()
                fb.AssignTo(tmp0).MethodCall(term, TermMethodTable.Kind)
                fb.If.Equal(tmp0, rpy.PyInt(TermKind.Integer)).ThenBlock(ifb)

                self.modulebuilder.SingleLineComment('#Is this term {}?'.format(pat.prefix))
                self.modulebuilder.Function(functionname).WithParameters(term).Block(fb)

            match_fn = 'match_lang_{}_builtin_{}'.format('blah', self.symgen.get())
            isafunc = self.context.get_isa_function_name(pat.prefix)
            self._gen_match_function_for_primitive(match_fn, isafunc, repr(pat), sym=pat.sym)

        if pat.kind == ast.BuiltInPatKind.VariableNotOtherwiseDefined:
            if not self.context.get_isa_function_name(pat.prefix):
                functionname = 'lang_{}_isa_builtin_variable_not_otherwise_mentioned'.format(self.definelanguage.name)
                self.context.add_isa_function_name(pat.prefix, functionname)

                var, _ = self.context.get_variables_mentioned()
                term = rpy.gen_pyid_for('term')
                tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)

                # tmp0 = term.kind()
                # tmp1 = term.value()
                # if tmp0 == TermKind.Variable:
                #   if tmp0 not in var:
                #     return True
                # return False
                # This one is different from other built-in isa funcs because we do set membership test here.
                ifb2 = rpy.BlockBuilder()
                ifb2.Return.PyBoolean(True)

                ifb1 = rpy.BlockBuilder()
                ifb1.If.NotContains(tmp0).In(var).ThenBlock(ifb2)

                fb = rpy.BlockBuilder()
                fb.AssignTo(tmp0).MethodCall(term, TermMethodTable.Kind)
                fb.AssignTo(tmp1).MethodCall(term, TermMethodTable.Value)
                fb.If.Equal(tmp0, PyInt(TermKind.Variable)).ThenBlock(ifb1)
                fb.Return.PyBoolean(False)

                self.modulebuilder.SingleLineComment('#Is this term {}?'.format(pat.prefix))
                self.modulebuilder.Function(functionname).WithParameters(term).Block(fb)

            match_fn = 'match_lang_{}_builtin_{}'.format('blah', self.symgen.get())
            isafunc = self.context.get_isa_function_name(pat.prefix)
            self._gen_match_function_for_primitive(match_fn, isafunc, repr(pat), sym=pat.sym)

        if pat.kind == ast.BuiltInPatKind.InHole:
            if not self.context.get_function_for_pattern(repr(pat)):
                functionname = 'lang_{}_builtin_inhole_{}'.format(self.definelanguage.name, self.symgen.get())
                self.context.add_function_for_pattern(repr(pat), functionname)

                # 1. Look up all the terms that match pat2. Store (term, [match]) pairs.
                # 2. For each matching term,
                #    1. Replace term with hole
                #    2. Try match pat1. If match is successful, copy term recursively starting from hole, 
                #       and add appropriate binding into matches associated with the term.
                #    3. Replace hole with term to restore the whole term to it's original state.

                pat1, pat2 = pat.aux
                self.transform(pat1)
                self.transform(pat2)

                matchpat1 = self.context.get_function_for_pattern(repr(pat1))
                matchpat2 = self.context.get_function_for_pattern(repr(pat2))


                rbe = RetrieveBindableElements()
                rbe.transform(pat1)
                bindablespat1 = list(map(lambda x: x.sym, rbe.bindables))

                rbe = RetrieveBindableElements()
                rbe.transform(pat2)
                bindablespat2 = list(map(lambda x: x.sym, rbe.bindables))

                # def inhole(term, path):
                # matches = []
                # inpat2match = Match(...)
                # pat2matches = pat2matchfunc(term, inpat2match, 0, 1)
                # if len(pat2matches) != 0:
                #     inpat1match = Match(...)
                #     tmp0 = path + [term]
                #     tmp1 = copy_path_and_replace_last(tmp0, hole)
                #     pat1matches = pat1matchfunc(tmp1, inpat1match, 0, 1)
                #     if len(pat1matches) != 0:
                #         for m1, h1, t1 in pat1matches:
                #             for m2, h2, t2 in pat2matches:
                #                 tmp2 = combine_matches(m1, m2)
                #                 tmp3 = matches.append((tmp2, h1, t1))
                # tmp4 = term.kind()
                # if tmp4 == Term.Sequence:
                #     tmp5 = path.append(term)
                #     tmp6 = term.length()
                #     for tmp10 in range(tmp6):
                #         tmp7 = term.get(tmp10)
                #         tmp8 = inhole(tmp7, path)
                #         matches = matches + tmp8
                #     tmp9 = path.pop()
                # return matches 

                symgen = SymGen()
                lookupfuncname = 'lang_{}_inhole_{}_impl'.format(self.definelanguage.name, self.symgen.get())

                matches, hole = rpy.gen_pyid_for('matches', 'hole')

                term, path = rpy.gen_pyid_for('term', 'path')
                m1, h1, h1 = rpy.gen_pyid_for('m1', 'h1', 't1')
                m2, h2, h2 = rpy.gen_pyid_for('m2', 'h2', 't2')

                pat1matches, inpat1match = rpy.gen_pyid_for('pat1matches', 'inpat1match')
                pat2matches, inpat2match = rpy.gen_pyid_for('pat2matches', 'inpat2match')

                tmp0, tmp1, tmp2, tmp3, tmp4 = rpy.gen_pyid_temporaries(5, symgen)
                tmp5, tmp6, tmp7, tmp8, tmp9 = rpy.gen_pyid_temporaries(5, symgen)
                tmp10 = rpy.gen_pyid_temporaries(1, symgen)

                forb2 = rpy.BlockBuilder()
                forb2.AssignTo(tmp2).FunctionCall(MatchHelperFuncs.CombineMatches, m1, m2) 
                forb2.AssignTo(tmp3).MethodCall(matches, 'append', rpy.PyTuple(tmp2, h1, t1))

                forb1 = rpy.BlockBuilder()
                forb1.For(m2, h2, t2).In(pat2matches).Block(forb2)

                ifb1 = rpy.BlockBuilder()
                ifb1.AssignTo(inpat1match).New('Match', rpy.PyList(tuple(set(bindablespat1))))
                ifb1.AssignTo(tmp0).Add(path, rpy.PyList(term))
                ifb1.AssignTo(tmp1).FunctionCall(TermHelperFuncs.CopyPathAndReplaceLast, tmp0, hole)
                ifb1.AssignTo(pat1matches).FunctionCall(matchpat1, tmp1, inpat1match, rpy.PyInt(0), rpy.PyInt(1)) 
                ifb1.If.LengthOf(pat1matches).NotEqual(rpy.PyInt(0)).ThenBlock(forb1)

                # ---------------

                forb1 = rpy.BlockBuilder()
                forb1.AssignTo(tmp7).MethodCall(term, TermMethodTable.Get, tmp10)
                forb1.AssignTo(tmp8).FunctionCall(lookupfuncname, tmp7, path)
                forb1.AssignTo(matches).Add(matches, tmp8)

                ifb3 = rpy.BlockBuilder()
                ifb3.AssignTo(tmp5).MethodCall(path, 'append', term)
                ifb3.AssignTo(tmp6).FunctionCall(term, TermMethodTable.Length)
                ifb3.For(tmp10).InRange(tmp6).Block(forb1)
                ifb3.AssignTo(tmp9).MethodCall(path, 'pop')

                # ----------------

                fb = rpy.BlockBuilder()
                fb.AssignTo(matches).PyList()
                fb.AssignTo(inpat2match).New('Match', rpy.PyList((tuple(set(bindablespat2)))))
                fb.AssignTo(pat2matches).FunctionCall(matchpat2, term, inpat2match, rpy.PyInt(0), rpy.PyInt(1))
                fb.If.LengthOf(pat2matches).NotEqual(rpy.PyInt(0)).Block(ifb1)
                fb.AssignTo(tmp4).MethodCall(term, TermMethodTable.Kind)
                fb.If.Equal(tmp4, rpy.PyInt(TermKind.Sequence)).ThenBlock(ifb3)
                fb.Return.PyId(matches)

        if pat.kind == ast.BuiltInPatKind.Hole:
            if not self.context.get_isa_function_name(pat.prefix):
                functionname = 'lang_{}_isa_builtin_hole'.format(self.definelanguage.name)
                self.context.add_isa_function_name(pat.prefix, functionname)

                # tmp0 = term.kind()
                # if tmp0 == TermKind.Hole
                #   return True
                # return False
                symgen = SymGen()

                term = rpy.gen_pyid_for('term')
                tmp0 = rpy.gen_pyid_temporaries(2, symgen)
                fb = rpy.BlockBuilder()

                ifb = rpy.BlockBuilder()
                ifb.Return.PyBoolean(True)

                fb = rpy.BlockBuilder()
                fb.AssignTo(tmp0).MethodCall(term, TermMethodTable.Kind)
                fb.If.Equal(tmp0, rpy.PyInt(TermKind.Hole)).ThenBlock(ifb)

                self.modulebuilder.SingleLineComment('#Is this term {}?'.format(pat.prefix))
                self.modulebuilder.Function(functionname).WithParameters(term).Block(fb)

                
            if not self.context.get_function_for_pattern(repr(pat)):
                match_fn = 'match_lang_{}_builtin_{}'.format('blah', self.symgen.get())
                self.context.add_function_for_pattern(repr(pat), match_fn)
                isafunc = self.context.get_isa_function_name(pat.prefix)
                self._gen_match_function_for_primitive(match_fn, isafunc, repr(pat))

    def transformLit(self, lit):
        assert isinstance(lit, ast.Lit)
        if lit.kind == ast.LitKind.Variable:
            if not self.context.get_function_for_pattern(repr(lit)):
                match_fn = 'lang_{}_consume_lit{}'.format('blah', self.symgen.get())
                self.context.add_function_for_pattern(repr(lit), match_fn)
                symgen = SymGen()
                term, match, head, tail = rpy.gen_pyid_for('term', 'match', 'head', 'tail')
                tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)

                # tmp0 = term.kind()
                # tmp1 = term.value()
                # if tmp0 == TermKind.Variable:
                #   if tmp1 == sym:
                #     head = head + 1
                #     return [ (match, head, tail) ] 
                # return [] 
                ifb2 = rpy.BlockBuilder()
                ifb2.AssignTo(head).Add(head, rpy.PyInt(1))
                ifb2.Return.PyList( rpy.PyTuple(match, head, tail) )

                ifb1 = rpy.BlockBuilder()
                ifb1.If.Equal(tmp1, rpy.PyString('\"{}\"'.format(lit.lit))).ThenBlock(ifb2)

                fb = rpy.BlockBuilder()
                fb.AssignTo(tmp0).MethodCall(term, TermMethodTable.Kind)
                fb.AssignTo(tmp1).MethodCall(term, TermMethodTable.Value)
                fb.If.Equal(tmp0, PyInt(TermKind.Variable)).ThenBlock(ifb1)
                fb.Return.PyList()

                self.modulebuilder.SingleLineComment('#{}'.format(repr(lit)))
                self.modulebuilder.Function(match_fn).WithParameters(term, match, head, tail).Block(fb)
