import src.model.pattern as pattern
import src.model.rpython as rpy

from src.util import SymGen
from src.context import CompilationContext

from src.codegen.common import TermHelperFuncs, MatchHelperFuncs, \
                          MatchMethodTable, TermKind, \
                          TermMethodTable

class PatternCodegen(pattern.PatternTransformer):
    def __init__(self, modulebuilder, pat, context, languagename, symgen):
        assert isinstance(pat, pattern.Pat)
        assert isinstance(context, CompilationContext)
        self.modulebuilder = modulebuilder
        self.pattern = pat 
        self.context = context
        self.languagename = languagename
        self.symgen = symgen

    def _assignable_symbols_to_rpylist(self, assignable_symbols):
        assignable_syms = map(lambda s: rpy.PyString(s), assignable_symbols)
        return rpy.PyList(*assignable_syms)

    def run(self):
        if self.context.get_function_for_pattern(self.languagename, repr(self.pattern)) is None:
            self.transform(self.pattern)

        if self.context.get_toplevel_function_for_pattern(self.languagename, repr(self.pattern)) is None:
            nameof_this_func = 'lang_{}_{}_toplevel'.format(self.languagename, self.symgen.get('pat'))
            self.context.add_toplevel_function_for_pattern(self.languagename, repr(self.pattern), nameof_this_func)

            assignable_symbols = self.pattern.getmetadata(pattern.PatAssignableSymbols)
            assignable_symbols = assignable_symbols.syms
            symgen = SymGen()

            func2call = self.context.get_function_for_pattern(self.languagename, repr(self.pattern))

            term, match, matches, ret = rpy.gen_pyid_for('term', 'match', 'matches', 'ret')
            m, h, t = rpy.gen_pyid_for('m', 'h', 't')
            tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)

            forb = rpy.BlockBuilder()
            try: 
                symstoremove = self.pattern.getmetadata(pattern.PatConstraintCheckSymsToRemove)
                for sym in symstoremove.arr:
                    tmpi = rpy.gen_pyid_temporaries(1, symgen)
                    forb.AssignTo(tmpi).MethodCall(m, MatchMethodTable.RemoveKey, rpy.PyString(sym))
            except: 
                pass
            forb.AssignTo(tmp0).MethodCall(ret, 'append', m)
            fb = rpy.BlockBuilder()
            fb.AssignTo(match).New('Match', self._assignable_symbols_to_rpylist(assignable_symbols))
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
        if self.context.get_function_for_pattern(self.languagename, repr(repeat)) is None:
            match_fn = 'match_{}_term_{}'.format(self.languagename, self.symgen.get())
            self.context.add_function_for_pattern(self.languagename, repr(repeat), match_fn)

            # codegen enclosed pattern 
            self.transform(repeat.pat)

            functionname = self.context.get_function_for_pattern(self.languagename, repr(repeat.pat))

            # retrieve all bindable elements
            assignable_symbols = repeat.getmetadata(pattern.PatAssignableSymbols)
            assignable_symbols = assignable_symbols.syms


            symgen = SymGen()
            term, match, head, tail = rpy.gen_pyid_for('term', 'match', 'head', 'tail')
            if repeat.matchmode == pattern.RepeatMatchMode.Deterministic:
                
                tmp0, tmp1, tmp2, tmp3, tmp4 = rpy.gen_pyid_temporaries(5, symgen)

                # tmp0 = match.increasedepth(...)
                # while True:
                #   if head == tail:
                #     break
                #   tmp1 = term.get[head]
                #   tmp2 = match_term(tmp1, match, head, tail)
                #   if len(tmp2) == 0:
                #     break
                #   if len(tmp2) != 1:
                #     raise Exception
                #   tmp3 = tmp2[0]
                #   match = tmp3[0]
                #   head  = tmp3[1]
                # tmp4 = match.decreasedepth(...)
                # return (match, head, tail)

                # tmp0 = match.increasedepth(...)
                # outmatches = []
                # matches = [(tmp0, head, tail)]
                # while len(matches) != 0:
                #   nmatches = []
                #   for m, h, t in matches:
                #     if h == t:
                #       tmp1 = (m,h,t)
                #       tmp1 = completedmatches.append()
                #       continue
                #     tmp2 = term.get[h]
                #     tmp3 = match_term(tmp2, m, h, t) 
                #     if len(tmp3) == 0:
                #       completedmatches.append((m,h,t))
                #       continue
                #     nmatches = nmatches + tmp3
                #   matches = nmatches 
                # for match in outmatches:
                #   tmp4 = match.decreasedepth(...)
                # return outmatches
                matches, nmatches, outmatches = rpy.gen_pyid_for('matches', 'nmatches', 'outmatches')
                m, h, t = rpy.gen_pyid_for('m', 'h', 't')

                ifb1 = rpy.BlockBuilder()
                ifb1.AssignTo(tmp1).PyTuple(m, h, t)
                ifb1.AssignTo(tmp1).MethodCall(outmatches, 'append', tmp1)
                ifb1.Continue

                ifb2 = rpy.BlockBuilder()
                ifb2.AssignTo(tmp4).PyTuple(m, h, t)
                ifb2.AssignTo(tmp4).MethodCall(outmatches, 'append', tmp4)
                ifb2.Continue

                forb1 = rpy.BlockBuilder()
                forb1.If.Equal(h, t).ThenBlock(ifb1)
                forb1.AssignTo(tmp2).MethodCall(term, TermMethodTable.Get, h)
                forb1.AssignTo(tmp3).FunctionCall(functionname, tmp2, m, h, t)
                forb1.If.LengthOf(tmp3).Equal(rpy.PyInt(0)).ThenBlock(ifb2)
                forb1.AssignTo(nmatches).Add(nmatches, tmp3)

                whb = rpy.BlockBuilder()
                whb.AssignTo(nmatches).PyList()
                whb.For(m,h,t).In(matches).Block(forb1)
                whb.AssignTo(matches).PyId(nmatches)


                if len(assignable_symbols) != 0:
                    forb2 = rpy.BlockBuilder()
                    for bindable in assignable_symbols:
                        forb2.AssignTo(tmp4).MethodCall(m, MatchMethodTable.DecreaseDepth, rpy.PyString(bindable))


                fb = rpy.BlockBuilder()
                for bindable in assignable_symbols:
                    fb.AssignTo(tmp0).MethodCall(match, MatchMethodTable.IncreaseDepth, rpy.PyString(bindable))
                fb.AssignTo(outmatches).PyList()
                fb.AssignTo(matches).PyList( rpy.PyTuple(match, head, tail) )
                fb.While.LengthOf(matches).NotEqual(rpy.PyInt(0)).Block(whb)
                if len(assignable_symbols) != 0:
                    fb.For(m,h,t).In(outmatches).Block(forb2)
                fb.Return.PyId(outmatches)

                self.modulebuilder.SingleLineComment('{} deterministic'.format(repr(repeat)))
                self.modulebuilder.Function(match_fn).WithParameters(term, match, head, tail).Block(fb)

            if repeat.matchmode == pattern.RepeatMatchMode.NonDetermininstic:
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

                if len(assignable_symbols) != 0:
                    forb = rpy.BlockBuilder()
                    for bindable in assignable_symbols:
                        forb.AssignTo(tmp4).MethodCall(m, MatchMethodTable.DecreaseDepth, rpy.PyString(bindable))

                fb = rpy.BlockBuilder()
                for bindable in assignable_symbols:
                    fb.AssignTo(tmp0).MethodCall(match, MatchMethodTable.IncreaseDepth, rpy.PyString(bindable))
                fb.AssignTo(tmp1).PyTuple(match, head, tail)
                fb.AssignTo(matches).PyList(tmp1)
                fb.AssignTo(queue).PyList(tmp1)
                fb.While.LengthOf(queue).NotEqual(rpy.PyInt(0)).Block(wb)
                if len(assignable_symbols) != 0:
                    fb.For(m, h, t).In(matches).Block(forb)
                fb.Return.PyId(matches)

                self.modulebuilder.SingleLineComment('{} non-deterministic'.format(repr(repeat)))
                self.modulebuilder.Function(match_fn).WithParameters(term, match, head, tail).Block(fb)

    def transformPatSequence(self, seq):
        assert isinstance(seq, pattern.PatSequence)
        if self.context.get_function_for_pattern(self.languagename, repr(seq)) is None:
            match_fn = 'language_{}_match_term_{}'.format(self.languagename, self.symgen.get())
            self.context.add_function_for_pattern(self.languagename, repr(seq), match_fn)
            
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

                if isinstance(pat, pattern.Repeat) :
                    # matches{i} = [] # get temporary with symbol
                    # for m,h,t in matches{i-1}:
                    #   tmp{i} = matchfn(term, m, h, t)   
                    #   matches{i} = matches{i} + tmp{i}
                    functionname = self.context.get_function_for_pattern(self.languagename, repr(pat))

                    tmpi, tmpj  = rpy.gen_pyid_temporaries(2, symgen)
                    forb = rpy.BlockBuilder()
                    forb.AssignTo(tmpi).FunctionCall(functionname, term, m, h, t)
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
                    #     tmp{j} = matches{i}.append( (m, h, t) )
                    # if len(matches{i}) == 0:
                    #   return matches{i} 
                    tmpi, tmpj, tmpk  = rpy.gen_pyid_temporaries(3, symgen)

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
                    #   tmp{j} = term.get(h)
                    #   tmp{i} = func(tmp{j}, m, h, t)
                    #   matches{i} = matches{i} + tmp{i}
                    # if len(matches{i}) == 0: 
                    #   return  matches{i} 
                    function = self.context.get_function_for_pattern(self.languagename, repr(pat))
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
        if self.context.get_isa_function_name(self.languagename, nt.prefix) is None:
            assert False, 'define-language should have been generated by now'

        if self.context.get_function_for_pattern(self.languagename, repr(nt)) is None:
            match_fn = 'lang_{}_match_nt_{}'.format(self.languagename, self.symgen.get())
            self.context.add_function_for_pattern(self.languagename, repr(nt), match_fn)
            isafunction = self.context.get_isa_function_name(self.languagename, nt.prefix)
            self._gen_match_function_for_primitive(match_fn, isafunction, repr(nt), sym=nt.sym)

    # FIXME will introduce explicit inhole pattern later.
    def transformInHole(self, pat):
        assert isinstance(pat, pattern.InHole)
        if not self.context.get_function_for_pattern(self.languagename, repr(pat)):
            functionname = 'lang_{}_builtin_inhole_{}'.format(self.languagename, self.symgen.get())
            self.context.add_function_for_pattern(self.languagename, repr(pat), functionname)
            # 1. Look up all the terms that match pat2. Store (term, [match]) pairs.
            # 2. For each matching term,
            #    1. Replace term with hole
            #    2. Try match pat1. If match is successful, copy term recursively starting from hole, 
            #       and add appropriate binding into matches associated with the term.
            #    3. Replace hole with term to restore the whole term to it's original state.

            pat1, pat2 = pat.pat1, pat.pat2
            self.transform(pat1)
            self.transform(pat2)

            matchpat1 = self.context.get_function_for_pattern(self.languagename, repr(pat1))
            matchpat2 = self.context.get_function_for_pattern(self.languagename, repr(pat2))


            assignable_syms1 = pat1.getmetadata(pattern.PatAssignableSymbols)
            assignable_syms1 = assignable_syms1.syms
            assignable_syms2 = pat2.getmetadata(pattern.PatAssignableSymbols)
            assignable_syms2 = assignable_syms2.syms
            assignable_syms_all = assignable_syms1.union(assignable_syms2)

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

            forb2 = rpy.BlockBuilder()
            forb2.AssignTo(tmp2).FunctionCall(MatchHelperFuncs.CombineMatches, m1, m2) 
            forb2.AssignTo(tmpm).MethodCall(match, MatchMethodTable.Copy)
            for sym in assignable_syms_all:
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
            ifb1.AssignTo(inpat1match).New('Match', self._assignable_symbols_to_rpylist(assignable_syms1))
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
            fb.AssignTo(inpat2match).New('Match', self._assignable_symbols_to_rpylist(assignable_syms2))
            fb.AssignTo(pat2matches).FunctionCall(matchpat2, term, inpat2match, rpy.PyInt(0), rpy.PyInt(1))
            fb.If.LengthOf(pat2matches).NotEqual(rpy.PyInt(0)).ThenBlock(ifb1)
            fb.AssignTo(tmp4).MethodCall(term, TermMethodTable.Kind)
            fb.If.Equal(tmp4, rpy.PyInt(TermKind.Sequence)).ThenBlock(ifb3)
            fb.Return.PyId(matches)

            self.modulebuilder.SingleLineComment('{}'.format(repr(pat)))
            self.modulebuilder.Function(lookupfuncname).WithParameters(term, match, head, tail, path).Block(fb)

            #-------- this produces top-level function with empty list representing the path.
            # We do constraint checking here also.
            symgen = SymGen()

            m, h, t = rpy.gen_pyid_for('m', 'h', 't')
            forb = rpy.BlockBuilder()
            if pat.constraintchecks != None:
                for chck in pat.constraintchecks:
                    tmpi = rpy.gen_pyid_temporaries(1, symgen)
                    ifb = rpy.BlockBuilder()
                    ifb.Continue

                    forb.AssignTo(tmpi).MethodCall(m, MatchMethodTable.CompareKeys, rpy.PyString(chck.sym1), rpy.PyString(chck.sym2))
                    forb.If.NotEqual(tmpi, rpy.PyBoolean(True)).ThenBlock(ifb)

                tmp = rpy.gen_pyid_temporaries(1, symgen)
                forb.AssignTo(tmp).MethodCall(matches, 'append', rpy.PyTuple(m, h, t))

            fb = rpy.BlockBuilder()
            fb.AssignTo(matches).PyList()
            fb.AssignTo(tmp0).FunctionCall(lookupfuncname, term, match, head, tail, rpy.PyList())
            fb.For(m, h, t).In(tmp0).Block(forb)
            fb.Return.PyId(matches)

            self.modulebuilder.Function(functionname).WithParameters(term, match, head, tail).Block(fb)

    def transformBuiltInPat(self, pat):
        assert isinstance(pat, pattern.BuiltInPat) 
        if pat.kind == pattern.BuiltInPatKind.Number:
            if self.context.get_function_for_pattern(self.languagename, repr(pat)) is None:
                nameof_this_func = 'match_lang_{}_builtin_{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(self.languagename, repr(pat), nameof_this_func)
                isafunc = self.context.get_isa_function_name(self.languagename, pat.prefix)
                self._gen_match_function_for_primitive(nameof_this_func, TermHelperFuncs.TermIsNumber, repr(pat), sym=pat.sym)
            return pat

        if pat.kind == pattern.BuiltInPatKind.Integer:
            if self.context.get_function_for_pattern(self.languagename, repr(pat)) is None:
                nameof_this_func = 'match_lang_{}_builtin_{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(self.languagename, repr(pat), nameof_this_func)
                self._gen_match_function_for_primitive(nameof_this_func, TermHelperFuncs.TermIsInteger, repr(pat), sym=pat.sym)
            return pat

        if pat.kind == pattern.BuiltInPatKind.Natural:
            if self.context.get_function_for_pattern(self.languagename, repr(pat)) is None:
                nameof_this_func = 'match_lang_{}_builtin_{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(self.languagename, repr(pat), nameof_this_func)
                self._gen_match_function_for_primitive(nameof_this_func, TermHelperFuncs.TermIsNatural, repr(pat), sym=pat.sym)
            return pat

        if pat.kind == pattern.BuiltInPatKind.Float:
            if self.context.get_function_for_pattern(self.languagename, repr(pat)) is None:
                nameof_this_func = 'match_lang_{}_builtin_{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(self.languagename, repr(pat), nameof_this_func)
                self._gen_match_function_for_primitive(nameof_this_func, TermHelperFuncs.TermIsFloat, repr(pat), sym=pat.sym)
            return pat

        if pat.kind == pattern.BuiltInPatKind.String:
            if self.context.get_function_for_pattern(self.languagename, repr(pat)) is None:
                nameof_this_func = 'match_lang_{}_builtin_{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(self.languagename, repr(pat), nameof_this_func)
                self._gen_match_function_for_primitive(nameof_this_func, TermHelperFuncs.TermIsString, repr(pat), sym=pat.sym)
            return pat

        if pat.kind == pattern.BuiltInPatKind.Boolean:
            if self.context.get_function_for_pattern(self.languagename, repr(pat)) is None:
                nameof_this_func = 'match_lang_{}_builtin_{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(self.languagename, repr(pat), nameof_this_func)
                self._gen_match_function_for_primitive(nameof_this_func, TermHelperFuncs.TermIsBoolean, repr(pat), sym=pat.sym)
            return pat

        if pat.kind == pattern.BuiltInPatKind.VariableNotOtherwiseDefined:
            # generate isa function for variable-not-otherwise-mentioned here because we need to reference
            # compile-time generated language-specific array 'langname_variable_mentioned'
            if self.context.get_isa_function_name(self.languagename, pat.prefix) is None:
                nameof_this_func = 'lang_{}_isa_builtin_variable_not_othewise_mentioned'.format(self.languagename)
                self.context.add_isa_function_name(self.languagename, pat.prefix, nameof_this_func)

                symgen = SymGen()

                var, _ = self.context.get_variables_mentioned(self.languagename)
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
            if self.context.get_function_for_pattern(self.languagename, repr(pat)) is None:
                nameof_this_func = 'match_lang_{}_builtin_{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(self.languagename, repr(pat), nameof_this_func)
                isafunc = self.context.get_isa_function_name(self.languagename, pat.prefix)
                self._gen_match_function_for_primitive(nameof_this_func, isafunc, repr(pat), sym=pat.sym)
            return pat

        if pat.kind == pattern.BuiltInPatKind.Hole:
            if self.context.get_function_for_pattern(self.languagename, repr(pat)) is None:
                nameof_this_func = 'match_lang_{}_builtin_{}'.format(self.languagename, self.symgen.get())
                self.context.add_function_for_pattern(self.languagename, repr(pat), nameof_this_func)
                isafunc = self.context.get_isa_function_name(self.languagename, pat.prefix)
                self._gen_match_function_for_primitive(nameof_this_func, TermHelperFuncs.TermIsHole, repr(pat))
            return pat
        assert False, 'unsupported pattern' 


    def gen_procedure_for_lit(self, lit, consumeprocedure, exactvalue):
        if self.context.get_function_for_pattern(self.languagename, repr(lit)) is not None:
            return lit

        nameof_this_func = 'lang_{}_consume_lit{}'.format(self.languagename, self.symgen.get())
        self.context.add_function_for_pattern(self.languagename, repr(lit), nameof_this_func)

        symgen = SymGen()
        term, match, head, tail = rpy.gen_pyid_for('term', 'match', 'head', 'tail')
        tmp0 = rpy.gen_pyid_temporaries(1, symgen)

        fb = rpy.BlockBuilder()
        fb.AssignTo(tmp0).FunctionCall(consumeprocedure, term, match, head, tail, exactvalue)
        fb.Return.PyId(tmp0)

        self.modulebuilder.SingleLineComment('#{}'.format(repr(lit)))
        self.modulebuilder.Function(nameof_this_func).WithParameters(term, match, head, tail).Block(fb)
        return lit

    def transformLit(self, lit):
        assert isinstance(lit, pattern.Lit)
        if lit.kind == pattern.LitKind.Variable:
            return self.gen_procedure_for_lit(lit, TermHelperFuncs.ConsumeVariable, rpy.PyString(lit.lit))
        if lit.kind == pattern.LitKind.Integer:
            return self.gen_procedure_for_lit(lit, TermHelperFuncs.ConsumeInteger, rpy.PyInt(int(lit.lit)))
        if lit.kind == pattern.LitKind.Float:
            return self.gen_procedure_for_lit(lit, TermHelperFuncs.ConsumeFloat, rpy.PyFloat(float(lit.lit)))
        if lit.kind == pattern.LitKind.String:
            return self.gen_procedure_for_lit(lit, TermHelperFuncs.ConsumeString, rpy.PyString(lit.lit))
        if lit.kind == pattern.LitKind.Boolean:
            return self.gen_procedure_for_lit(lit, TermHelperFuncs.ConsumeBoolean, rpy.PyString(lit.lit))

        assert False, 'unknown literal kind ' + str(lit.kind)
