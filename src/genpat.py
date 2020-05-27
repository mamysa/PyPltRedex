import src.pat as pattern
import src.rpython as rpy

from src.symgen import SymGen
from src.context import CompilationContext

from src.gencommon import TermHelperFuncs, MatchHelperFuncs, \
                          MatchMethodTable, TermKind, \
                          RetrieveBindableElements, TermMethodTable

class PatternCodegen(pattern.PatternTransformer):
    def __init__(self, modulebuilder, pat, context, languagename, symgen):
        assert isinstance(pat, pattern.Pat)
        assert isinstance(context, CompilationContext)
        self.modulebuilder = modulebuilder
        self.pattern = pat 
        self.context = context
        self.languagename = languagename
        self.symgen = symgen

    def run(self):
        if self.context.get_function_for_pattern(repr(self.pattern)) is None:
            self.transform(self.pattern)

        if self.context.get_toplevel_function_for_pattern(repr(self.pattern)) is None:
            nameof_this_func = 'lang_{}_{}_toplevel'.format(self.languagename, self.symgen.get('pat'))
            self.context.add_toplevel_function_for_pattern(repr(self.pattern), nameof_this_func)

            rbe = RetrieveBindableElements()
            rbe.transform(self.pattern)

            symgen = SymGen()

            func2call = self.context.get_function_for_pattern(repr(self.pattern))

            term, match, matches, ret = rpy.gen_pyid_for('term', 'match', 'matches', 'ret')
            m, h, t = rpy.gen_pyid_for('m', 'h', 't')
            tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)

            forb = rpy.BlockBuilder()
            forb.AssignTo(tmp0).MethodCall(ret, 'append', m)

            fb = rpy.BlockBuilder()
            fb.AssignTo(match).New('Match', rbe.get_rpylist())
            fb.AssignTo(matches).FunctionCall(func2call, term, match, rpy.PyInt(0), rpy.PyInt(1))
            fb.AssignTo(ret).PyList()
            fb.For(m, h, t).In(matches).Block(forb)
            fb.Return.PyId(ret)
            
            self.modulebuilder.SingleLineComment('toplevel {}'.format(repr(self.pattern)))
            self.modulebuilder.Function(nameof_this_func).WithParameters(term).Block(fb)

        return self.pattern

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
        tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)

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

    def transformRepeat(self, repeat):
        assert isinstance(repeat, pattern.Repeat)
        if self.context.get_function_for_pattern(repr(repeat)) is None:
            match_fn = 'match_{}_term_{}'.format(self.languagename, self.symgen.get())
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
                forb.AssignTo(tmp4).MethodCall(m, MatchMethodTable.DecreaseDepth, rpy.PyString(bindable.sym))

            fb = rpy.BlockBuilder()
            for bindable in rbe.bindables:
                fb.AssignTo(tmp0).MethodCall(match, MatchMethodTable.IncreaseDepth, rpy.PyString(bindable.sym))
            fb.AssignTo(tmp1).PyTuple(match, head, tail)
            fb.AssignTo(matches).PyList(tmp1)
            fb.AssignTo(queue).PyList(tmp1)
            fb.While.LengthOf(queue).NotEqual(rpy.PyInt(0)).Block(wb)
            fb.For(m, h, t).In(matches).Block(forb)
            fb.Return.PyId(matches)

            self.modulebuilder.SingleLineComment('{} non-deterministic'.format(repr(repeat)))
            self.modulebuilder.Function(match_fn).WithParameters(term, match, head, tail).Block(fb)

    def transformPatSequence(self, seq):
        assert isinstance(seq, pattern.PatSequence)
        if self.context.get_function_for_pattern(repr(seq)) is None:
            match_fn = 'language_{}_match_term_{}'.format(self.languagename, self.symgen.get())
            self.context.add_function_for_pattern(repr(seq), match_fn)
            
            # generate code for all elements of the sequence.
            for pat in seq:
                if not isinstance(pat, pattern.CheckConstraint):
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

            fb.AssignTo(tmpi).Subtract(subtail, subhead)
            fb.If.LessThan(tmpi, rpy.PyInt(num_required)).ThenBlock(ifb)

            # stick initial match object into array - simplifies codegen.
            previousmatches = rpy.gen_pyid_for('matches')
            fb.AssignTo(previousmatches).PyList( rpy.PyTuple(match, subhead, subtail) )

            for i, pat in enumerate(seq):
                matches = rpy.gen_pyid_temporary_with_sym('matches', symgen)

                if isinstance(pat, pattern.Repeat) or isinstance(pat, pattern.PatSequence):
                    # matches{i} = [] # get temporary with symbol
                    # for m,h,t in matches{i-1}:
                    #   tmp{i} = matchfn(term, m, h, t)   // if pat IS repeat
                    #   tmp{j} = term.get(h)              // if pat IS NOT repeat
                    #   tmp{i} = matchfn(tmp{j}, m, h, t) // if pat IS NOT repeat 
                    #   matches{i} = matches{i} + tmp{i}
                    functionname = self.context.get_function_for_pattern(repr(pat))

                    tmpi, tmpj  = rpy.gen_pyid_temporaries(2, symgen)
                    forb = rpy.BlockBuilder()
                    if isinstance(pat, pattern.Repeat):
                        forb.AssignTo(tmpi).FunctionCall(functionname, term, m, h, t)
                    else:
                        forb.AssignTo(tmpj).MethodCall(term, TermMethodTable.Get, h)
                        forb.AssignTo(tmpi).FunctionCall(functionname, tmpj, m, h, t)
                    forb.AssignTo(matches).Add(matches, tmpi)
                    fb.AssignTo(matches).PyList()
                    fb.For(m, h, t).In(previousmatches).Block(forb)

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
                    if isinstance(pat, pattern.Repeat):
                        num_required = seq.get_number_of_nonoptional_matches_between(i, len(seq))
                        if num_required > 0:
                            previousmatches = matches
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

                            
                elif isinstance(pat, pattern.CheckConstraint):
                    # matches{i} = []
                    # for m, h, t in matches{i-1}:
                    #   tmp{i} = m.CompareKeys(sym1, sym2)
                    #   if tmp{i} == True:
                    #     tmp{k} = m.removebinding(sym2)
                    #     tmp{j} = matches{i}.append( (m, h, t) )
                    # if len(matches{i}) == 0:
                    #   return matches{i} 
                    tmpi, tmpj, tmpk  = rpy.gen_pyid_temporaries(3, symgen)

                    ifb1 = rpy.BlockBuilder()
                    ifb1.AssignTo(tmpk).MethodCall(m, MatchMethodTable.RemoveKey, rpy.PyString(pat.sym2))
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
                    #   tmp{j} = term.get(h)
                    #   tmp{i} = func(tmp{j}, m, h, t)
                    #   matches{i} = matches{i} + tmp{i}
                    # if len(matches{i}) == 0: 
                    #   return  matches{i} 
                    function = self.context.get_function_for_pattern(repr(pat))
                    tmpi, tmpj = rpy.gen_pyid_temporaries(2, symgen)

                    forb = rpy.BlockBuilder()

                    forb.AssignTo(tmpj).MethodCall(term, TermMethodTable.Get, h)
                    forb.AssignTo(tmpi).FunctionCall(function, tmpj, m, h, t)
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
            #     tmp{k} = head + 1
            #     tmp{i} = (m, head, tail)
            #     tmp{j} = matches{i}.append(tmp{i})
            # return matches{i}
            tmpi, tmpj, tmpk = rpy.gen_pyid_temporaries(3, symgen)
            matches = rpy.gen_pyid_temporary_with_sym('matches', symgen)

            ifb = rpy.BlockBuilder()
            ifb.AssignTo(tmpk).Add(head, rpy.PyInt(1))
            ifb.AssignTo(tmpi).PyTuple(m, tmpk, tail)
            ifb.AssignTo(tmpj).MethodCall(matches, 'append', tmpi)

            forb = rpy.BlockBuilder()
            forb.If.Equal(h, t).ThenBlock(ifb)

            fb.AssignTo(matches).PyList()
            fb.For(m, h, t).In(previousmatches).Block(forb)
            fb.Return.PyId(matches)

            self.modulebuilder.SingleLineComment(repr(seq))
            self.modulebuilder.Function(match_fn).WithParameters(term, match, head, tail).Block(fb)

    def transformNt(self, nt):
        assert isinstance(nt, pattern.Nt)
        # first generate isa for NtDefinition 
        if self.context.get_isa_function_name(nt.prefix) is None:
            assert False, 'define-language should have been generated by now'

        if self.context.get_function_for_pattern(repr(nt)) is None:
            match_fn = 'lang_{}_match_nt_{}'.format('blah', self.symgen.get())
            self.context.add_function_for_pattern(repr(nt), match_fn)
            isafunction = self.context.get_isa_function_name(nt.prefix)
            self._gen_match_function_for_primitive(match_fn, isafunction, repr(nt), sym=nt.sym)

    # FIXME will introduce explicit inhole pattern later.
    def _visitInHole(self, pat):
        if not self.context.get_function_for_pattern(repr(pat)):
            functionname = 'lang_{}_builtin_inhole_{}'.format(self.languagename, self.symgen.get())
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


            rbe1 = RetrieveBindableElements()
            rbe1.transform(pat1)

            rbe2 = RetrieveBindableElements()
            rbe2.transform(pat2)

            # def inhole(term, match, head, tail, path):
            # matches = []
            # inpat2match = Match(...)
            # pat2matches = pat2matchfunc(term, inpat2match, 0, 1)
            # if len(pat2matches) != 0:
            #     inpat1match = Match(...)
            #     tmp0 = path + [term]
            #     tmp1 = copy_path_and_replace_last(tmp0, hole)
            #     pat1matches = pat1matchfunc(tmp1, inpat1match, 0, 1)
            #     if len(pat1matches) != 0:
            #         tmp11 = head + 1
            #         for m1, h1, t1 in pat1matches:
            #             for m2, h2, t2 in pat2matches:
            #                 tmp2 = combine_matches(m1, m2)
            #                 tmp{i} = match.copy()
            #                 tmp{j} = tmp2.getbinding(...)              ; same for inpat2match
            #                 tmp{k} = tmp{i}.addtobinding(..., tmp{j})  ; same for inpat2match
            #                 tmp3 = matches.append((tmp{i}, tmp11, tail))
            # tmp4 = term.kind()
            # if tmp4 == Term.Sequence:
            #     tmp5 = path.append(term)
            #     tmp6 = term.length()
            #     for tmp10 in range(tmp6):
            #         tmp7 = term.get(tmp10)
            #         tmp8 = inhole(tmp7, match, head, tail, path)
            #         matches = matches + tmp8
            #     tmp9 = path.pop()
            # return matches 

            symgen = SymGen()
            lookupfuncname = 'lang_{}_inhole_{}_impl'.format(self.languagename, self.symgen.get())

            matches, hole = rpy.gen_pyid_for('matches', 'hole')

            term, match, head, tail, path = rpy.gen_pyid_for('term', 'match', 'head', 'tail', 'path')
            m1, h1, t1 = rpy.gen_pyid_for('m1', 'h1', 't1')
            m2, h2, t2 = rpy.gen_pyid_for('m2', 'h2', 't2')

            pat1matches, inpat1match = rpy.gen_pyid_for('pat1matches', 'inpat1match')
            pat2matches, inpat2match = rpy.gen_pyid_for('pat2matches', 'inpat2match')

            tmp0, tmp1, tmp2, tmp3, tmp4 = rpy.gen_pyid_temporaries(5, symgen)
            tmp5, tmp6, tmp7, tmp8, tmp9 = rpy.gen_pyid_temporaries(5, symgen)
            tmp10, tmp11, tmp12 = rpy.gen_pyid_temporaries(3, symgen)

            tmpm = rpy.gen_pyid_temporaries(1, symgen)
            rbes = rbe1.as_set().union(rbe2.as_set())

            forb2 = rpy.BlockBuilder()
            forb2.AssignTo(tmp2).FunctionCall(MatchHelperFuncs.CombineMatches, m1, m2) 
            forb2.AssignTo(tmpm).MethodCall(match, MatchMethodTable.Copy)
            for sym in rbes:
                tmpi, tmpj = rpy.gen_pyid_temporaries(2, symgen)
                forb2.AssignTo(tmpi).MethodCall(tmp2, MatchMethodTable.GetBinding, rpy.PyString(sym))
                forb2.AssignTo(tmpj).MethodCall(tmpm, MatchMethodTable.AddToBinding, rpy.PyString(sym), tmpi)
            forb2.AssignTo(tmp3).MethodCall(matches, 'append', rpy.PyTuple(tmpm, tmp11, tail))

            forb1 = rpy.BlockBuilder()
            forb1.For(m2, h2, t2).In(pat2matches).Block(forb2)

            forb0 = rpy.BlockBuilder()
            forb0.AssignTo(tmp11).Add(head, rpy.PyInt(1))
            forb0.For(m1, h1, t1).In(pat1matches).Block(forb1)

            ifb1 = rpy.BlockBuilder()
            ifb1.AssignTo(inpat1match).New('Match', rbe1.get_rpylist())
            ifb1.AssignTo(tmp0).Add(path, rpy.PyList(term))
            ifb1.AssignTo(tmp1).FunctionCall(TermHelperFuncs.CopyPathAndReplaceLast, tmp0, hole)
            ifb1.AssignTo(pat1matches).FunctionCall(matchpat1, tmp1, inpat1match, rpy.PyInt(0), rpy.PyInt(1)) 
            ifb1.If.LengthOf(pat1matches).NotEqual(rpy.PyInt(0)).ThenBlock(forb0)

            # ---------------

            forb1 = rpy.BlockBuilder()
            forb1.AssignTo(tmp7).MethodCall(term, TermMethodTable.Get, tmp10)
            forb1.AssignTo(tmp8).FunctionCall(lookupfuncname, tmp7, match, head, tail, path)
            forb1.AssignTo(matches).Add(matches, tmp8)

            ifb3 = rpy.BlockBuilder()
            ifb3.AssignTo(tmp5).MethodCall(path, 'append', term)
            ifb3.AssignTo(tmp6).MethodCall(term, TermMethodTable.Length)
            ifb3.For(tmp10).InRange(tmp6).Block(forb1)
            ifb3.AssignTo(tmp9).MethodCall(path, 'pop')

            # ----------------

            fb = rpy.BlockBuilder()
            fb.AssignTo(matches).PyList()
            fb.AssignTo(inpat2match).New('Match', rbe2.get_rpylist())
            fb.AssignTo(pat2matches).FunctionCall(matchpat2, term, inpat2match, rpy.PyInt(0), rpy.PyInt(1))
            fb.If.LengthOf(pat2matches).NotEqual(rpy.PyInt(0)).ThenBlock(ifb1)
            fb.AssignTo(tmp4).MethodCall(term, TermMethodTable.Kind)
            fb.If.Equal(tmp4, rpy.PyInt(TermKind.Sequence)).ThenBlock(ifb3)
            fb.Return.PyId(matches)

            self.modulebuilder.SingleLineComment('#Is this term {}?'.format(pat.prefix))
            self.modulebuilder.Function(lookupfuncname).WithParameters(term, match, head, tail, path).Block(fb)

            fb = rpy.BlockBuilder()
            fb.AssignTo(tmp0).FunctionCall(lookupfuncname, term, match, head, tail, rpy.PyList())
            fb.Return.PyId(tmp0)

            self.modulebuilder.Function(functionname).WithParameters(term, match, head, tail).Block(fb)

    def transformBuiltInPat(self, pat):
        assert isinstance(pat, pattern.BuiltInPat) 
        if pat.kind == pattern.BuiltInPatKind.Number:
            ##----- generate isA_NUMBER func ----
            if self.context.get_isa_function_name(pat.prefix) is None:
                nameof_this_func = 'lang_{}_isa_builtin_{}'.format(self.languagename, pat.prefix)
                self.context.add_isa_function_name(pat.prefix, nameof_this_func)
                # FIXME code duplication
                # tmp0 = term.kind()
                # if tmp0 == TermKind.Integer:
                #  return True
                # return False
                symgen = SymGen()

                term = rpy.gen_pyid_for('term')
                tmp0 = rpy.gen_pyid_temporaries(1, symgen)
                fb = rpy.BlockBuilder()

                ifb = rpy.BlockBuilder()
                ifb.Return.PyBoolean(True)

                fb = rpy.BlockBuilder()
                fb.AssignTo(tmp0).MethodCall(term, TermMethodTable.Kind)
                fb.If.Equal(tmp0, rpy.PyInt(TermKind.Integer)).ThenBlock(ifb)

                self.modulebuilder.SingleLineComment('#Is this term {}?'.format(pat.prefix))
                self.modulebuilder.Function(nameof_this_func).WithParameters(term).Block(fb)
            ##----- End isA_NUMBER func ----
            
            ##----- generate actual match function
            if self.context.get_function_for_pattern(repr(pat)) is None:
                nameof_this_func = 'match_lang_{}_builtin_{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(repr(pat), nameof_this_func)
                isafunc = self.context.get_isa_function_name(pat.prefix)
                self._gen_match_function_for_primitive(nameof_this_func, isafunc, repr(pat), sym=pat.sym)
            return pat

        if pat.kind == pattern.BuiltInPatKind.VariableNotOtherwiseDefined:
            if self.context.get_isa_function_name(pat.prefix) is None:
                nameof_this_func = 'lang_{}_isa_builtin_variable_not_othewise_mentioned'.format(self.languagename)
                self.context.add_isa_function_name(pat.prefix, nameof_this_func)

                symgen = SymGen()

                var, _ = self.context.get_variables_mentioned()
                var = rpy.gen_pyid_for(var)
                term = rpy.gen_pyid_for('term')
                tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)

                # tmp0 = term.kind()
                # if tmp0 == TermKind.Variable:
                #   tmp1 = term.value()
                #   if tmp1 not in var:
                #     return True
                # return False
                # This one is different from other built-in isa funcs because we do set membership test here.
                ifb2 = rpy.BlockBuilder()
                ifb2.Return.PyBoolean(True)

                ifb1 = rpy.BlockBuilder()
                ifb1.AssignTo(tmp1).MethodCall(term, TermMethodTable.Value)
                ifb1.If.NotContains(tmp1).In(var).ThenBlock(ifb2)

                fb = rpy.BlockBuilder()
                fb.AssignTo(tmp0).MethodCall(term, TermMethodTable.Kind)
                fb.If.Equal(tmp0, rpy.PyInt(TermKind.Variable)).ThenBlock(ifb1)
                fb.Return.PyBoolean(False)

                self.modulebuilder.SingleLineComment('#Is this term {}?'.format(pat.prefix))
                self.modulebuilder.Function(nameof_this_func).WithParameters(term).Block(fb)

            ##----- generate actual match function
            if self.context.get_function_for_pattern(repr(pat)) is None:
                nameof_this_func = 'match_lang_{}_builtin_{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(repr(pat), nameof_this_func)
                isafunc = self.context.get_isa_function_name(pat.prefix)
                self._gen_match_function_for_primitive(nameof_this_func, isafunc, repr(pat), sym=pat.sym)
            return pat

        if pat.kind == pattern.BuiltInPatKind.InHole:
            self._visitInHole(pat)
            return pat

        if pat.kind == pattern.BuiltInPatKind.Hole:
            if self.context.get_isa_function_name(pat.prefix) is None:
                nameof_this_func = 'lang_{}_isa_builtin_{}'.format(self.languagename, pat.prefix)
                self.context.add_isa_function_name(pat.prefix, nameof_this_func)

                # tmp0 = term.kind()
                # if tmp0 == TermKind.Hole
                #   return True
                # return False
                symgen = SymGen()

                term = rpy.gen_pyid_for('term')
                tmp0 = rpy.gen_pyid_temporaries(1, symgen)

                ifb = rpy.BlockBuilder()
                ifb.Return.PyBoolean(True)

                fb = rpy.BlockBuilder()
                fb.AssignTo(tmp0).MethodCall(term, TermMethodTable.Kind)
                fb.If.Equal(tmp0, rpy.PyInt(TermKind.Hole)).ThenBlock(ifb)
                fb.Return.PyBoolean(False)

                self.modulebuilder.SingleLineComment('#Is this term {}?'.format(pat.prefix))
                self.modulebuilder.Function(nameof_this_func).WithParameters(term).Block(fb)

            ##----- generate actual match function
            if self.context.get_function_for_pattern(repr(pat)) is None:
                nameof_this_func = 'match_lang_{}_builtin_{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(repr(pat), nameof_this_func)
                isafunc = self.context.get_isa_function_name(pat.prefix)
                self._gen_match_function_for_primitive(nameof_this_func, isafunc, repr(pat))
            return pat
        assert False, 'unsupported pattern' 

    def transformLit(self, lit):
        assert isinstance(lit, pattern.Lit)
        if lit.kind == pattern.LitKind.Variable:
            if self.context.get_function_for_pattern(repr(lit)) is None:
                match_fn = 'lang_{}_consume_lit{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(repr(lit), match_fn)
                symgen = SymGen()
                term, match, head, tail = rpy.gen_pyid_for('term', 'match', 'head', 'tail')
                tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)

                # tmp0 = term.kind()
                # if tmp0 == TermKind.Variable:
                #   tmp1 = term.value()
                #   if tmp1 == sym:
                #     head = head + 1
                #     return [ (match, head, tail) ] 
                # return [] 
                ifb2 = rpy.BlockBuilder()
                ifb2.AssignTo(head).Add(head, rpy.PyInt(1))
                ifb2.Return.PyList( rpy.PyTuple(match, head, tail) )

                ifb1 = rpy.BlockBuilder()
                ifb1.AssignTo(tmp1).MethodCall(term, TermMethodTable.Value)
                ifb1.If.Equal(tmp1, rpy.PyString(lit.lit)).ThenBlock(ifb2)

                fb = rpy.BlockBuilder()
                fb.AssignTo(tmp0).MethodCall(term, TermMethodTable.Kind)
                fb.If.Equal(tmp0, rpy.PyInt(TermKind.Variable)).ThenBlock(ifb1)
                fb.Return.PyList()

                self.modulebuilder.SingleLineComment('#{}'.format(repr(lit)))
                self.modulebuilder.Function(match_fn).WithParameters(term, match, head, tail).Block(fb)
            return lit
        assert False, 'unknown literal kind ' + str(lit.kind)
