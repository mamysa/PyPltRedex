import src.astdefs as ast
import src.term as TERM 
import src.genterm as genterm
from src.preprocdefinelang import LanguageContext
from src.symgen import SymGen
from src.common import SourceWriter, Var


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

            term, match, matches = Var('term'), Var('match'), Var('matches')
            self.writer += 'def {}({}):'.format(this_function_name, term)
            self.writer.newline().indent()

            for pat in node.patterns:
                rbe = RetrieveBindableElements()
                rbe.transform(pat)
                bindables = list(map(lambda x: x.sym,   rbe.bindables))

                functionname = self.context.get_function_for_pattern(repr(pat))
                self.writer += '{} = Match({})'.format(match, list(set(bindables)))
                self.writer.newline()
                self.writer += '{} = {}({}, {}, {}, {})'.format(matches, functionname, term, match, 0, 1)
                self.writer.newline()
                self.writer += 'if len({}) != {}:'.format(matches, 0)

                self.writer.newline().indent()
                self.writer += 'return True'
                self.writer.newline().dedent()

            self.writer += 'return False'
            self.writer.newline().dedent().newline()

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
            # function parameters

            term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')
            m, h, t = Var('m'), Var('h'), Var('t')

            # ensure the term is actually a sequence
            self.writer += '#{}'.format(repr(seq))
            self.writer.newline()
            self.writer += 'def {}({}, {}, {}, {}):'.format(match_fn, term, match, head, tail)
            self.writer.newline().indent()
            self.writer += 'if {}.{}() != {}:'.format(term, TermMethodTable.Kind, TermKind.Sequence)
            self.writer.newline().indent()
            self.writer += 'return []'
            self.writer.newline().dedent()

            subhead, subtail = Var('subhead'), Var('subtail')
            tmp = Var('tmp')

            # 'enter' the term
            self.writer += '{} = {}'.format(subhead, 0)
            self.writer.newline()
            self.writer += '{} = {}.{}()'.format(subtail, term, TermMethodTable.Length)
            self.writer.newline()


            # ensure number of terms in the sequence is at least equal to number of non Repeat patterns. 
            # if num_required is zero, condition is always false.
            num_required = seq.get_number_of_nonoptional_matches_between(0, len(seq))
            if num_required != 0:
                self.writer += 'if {} - {} < {}:'.format(subtail, subhead, num_required)
                self.writer.newline().indent()
                self.writer += 'return []'
                self.writer.newline().dedent()

            # stick intial match object into array - simplifies codegen.
            pmatches = Var('matches')
            self.writer += '{} = [({}, {}, {})]'.format(pmatches, match, subhead, subtail)
            self.writer.newline()

            for i, pat in enumerate(seq):
                matches = symgen.get('matches')
                self.writer += '#{}'.format(repr(pat))
                self.writer.newline()

                if isinstance(pat, ast.Repeat) or isinstance(pat, ast.PatSequence):
                    functionname = self.context.get_function_for_pattern(repr(pat))
                    self.writer += '{} = []'.format(matches)
                    self.writer.newline()
                    self.writer += 'for {}, {}, {} in {}:'.format(m, h, t, pmatches)
                    self.writer.newline().indent()
                    if isinstance(pat, ast.Repeat):
                        self.writer += '{} += {}({}, {}, {}, {})'.format(matches, functionname, term, m, h, t)
                    else:
                        self.writer += '{} += {}({}.{}({}), {}, {}, {})'.format(matches, functionname, term, TermMethodTable.Get, h, m, h, t)
                    self.writer.newline().dedent()

                    # ensure number of terms in the sequence is at least equal to number of non Repeat patterns after 
                    # this repeat pattern. 
                    if isinstance(pat, ast.Repeat):
                        num_required = seq.get_number_of_nonoptional_matches_between(i, len(seq))
                        if num_required > 0:
                            pmatches = matches
                            matches = symgen.get('matches')
                            self.writer += '{} = []'.format(matches)
                            self.writer.newline()
                            self.writer += 'for {}, {}, {} in {}:'.format(m, h, t, pmatches)
                            self.writer.newline().indent()
                            self.writer += 'if {} - {} >= {}:'.format(t, h, num_required)
                            self.writer.newline().indent()
                            self.writer += '{}.append(({}, {}, {}))'.format(matches, m, h, t)
                            self.writer.newline().dedent().dedent()

                elif isinstance(pat, ast.CheckConstraint):
                    self.writer += '{} = []'.format(matches)
                    self.writer.newline()
                    self.writer += 'for {}, {}, {} in {}:'.format(m, h, t, pmatches)
                    self.writer.newline().indent()
                    self.writer += 'if {}.{}(\"{}\", \"{}\"):'.format(m, MatchMethodTable.CompareKeys, pat.sym1, pat.sym2)
                    self.writer.newline().indent()
                    self.writer += '{}.{}(\"{}\")'.format(m, MatchMethodTable.RemoveKey, pat.sym2)
                    self.writer.newline()
                    self.writer += '{}.append(({}, {}, {}))'.format(matches, m, h, t)
                    self.writer.newline().dedent().dedent()

                    self.writer += 'if len({}) == 0:'.format(matches)
                    self.writer.newline().indent()
                    self.writer += 'return {}'.format(matches)
                    self.writer.newline().dedent()

                else:
                    # matches = []
                    # for m, h, t in matches:
                    # if isa_blah(term.get(h)):
                    #   m.addtobinding(m, term.get(h)) if pat is Builtin or Nt 
                    #   matches.append((m, h+1, t))
                    # if len(matches) == 0: return None
                    isa_functionname = self.context.get_function_for_pattern(repr(pat))
                    self.writer += '{} = []'.format(matches)
                    self.writer.newline()
                    self.writer += 'for {}, {}, {} in {}:'.format(m, h, t, pmatches)
                    self.writer.newline().indent()

                    if isinstance(pat, ast.Nt) or isinstance(pat, ast.BuiltInPat):
                        isa_functionname = self.context.get_isa_function_name(pat.prefix)
                        self.writer += 'if {}({}.{}({})):'.format(isa_functionname, term, TermMethodTable.Get, h)
                    else: 
                        functionname = self.context.get_function_for_pattern(repr(pat))
                        self.writer += 'if {}({}.{}({}), {}, {}, {}):'.format(functionname, term, TermMethodTable.Get, h, m, h, t)

                    self.writer.newline().indent()

                    if isinstance(pat, ast.Nt): 
                        self.writer += '{}.{}({}, {}.{}({}))'.format(m, MatchMethodTable.AddToBinding, '\"{}\"'.format(pat.sym), term, TermMethodTable.Get, h)
                        self.writer.newline()

                    if isinstance(pat, ast.BuiltInPat) and pat.kind != ast.BuiltInPatKind.Hole:
                        self.writer += '{}.{}({}, {}.{}({}))'.format(m, MatchMethodTable.AddToBinding, '\"{}\"'.format(pat.sym), term, TermMethodTable.Get, h)
                        self.writer.newline()

                    self.writer += '{}.append(({}, {}+1, {}))'.format(matches, m, h, t)
                    self.writer.newline().dedent().dedent()

                    self.writer += 'if len({}) == 0:'.format(matches)
                    self.writer.newline().indent()
                    self.writer += 'return {}'.format(matches)
                    self.writer.newline().dedent()

                pmatches = matches

            # exit term
            matches = symgen.get('matches')
            self.writer += '{} = []'.format(matches)
            self.writer.newline()
            self.writer += 'for {}, {}, {} in {}:'.format(m, h, t, pmatches)
            self.writer.newline().indent()
            self.writer += 'if {} == {}:'.format(h, t)
            self.writer.newline().indent()
            self.writer += '{}.append(({}, {}+1, {}))'.format(matches, m, head, tail)
            self.writer.newline().dedent().dedent()
            self.writer += 'return {}'.format(matches)
            self.writer.newline().dedent().newline()


    def transformRepeat(self, repeat):
        assert isinstance(repeat, ast.Repeat)
        # match.increasedepth(...)
        # matches = [ match ]
        # queue   = [ match ]
        # while len(queue) != 0:
        #   m, h, t = queue.pop(0)
        #   if h == t:
        #      continue
        #   m = m.copy()
        #   tmp = match_term(term[h], m, h, t)
        #   if tmp != None:
        #      matches += tmp
        #      queue   += tmp 
        # for m, h, t in matches:
        #   m.decreasedepth(...)
        if not self.context.get_function_for_pattern(repr(repeat)):
            match_fn = 'match_term_{}'.format(self.symgen.get())
            self.context.add_function_for_pattern(repr(repeat), match_fn)

            # codegen enclosed pattern 
            self.transform(repeat.pat)


            functionname = self.context.get_function_for_pattern(repr(repeat.pat))

            # retrieve all bindable elements
            rbe = RetrieveBindableElements()
            rbe.transform(repeat.pat)


            term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')
            matches, queue = Var('matches'), Var('queue')
            tmp = Var('tmp')
            m, h, t = Var('m'), Var('h'), Var('t')

            self.writer += '#{} non-deterministic'.format(repr(repeat))
            self.writer.newline()
            self.writer += 'def {}({}, {}, {}, {}):'.format(match_fn, term, match, head, tail)
            self.writer.newline().indent()
            for bindable in rbe.bindables:
                self.writer += '{}.{}(\"{}\")'.format(match, MatchMethodTable.IncreaseDepth, bindable.sym)
                self.writer.newline()
            self.writer += '{} = [ ({}, {}, {}) ]'.format(matches, match, head, tail)
            self.writer.newline()
            self.writer += '{} = [ ({}, {}, {}) ]'.format(queue, match, head, tail)
            self.writer.newline()
            self.writer += 'while len({}) != 0:'.format(queue)
            self.writer.newline().indent()
            self.writer += '{}, {}, {} = {}.pop({})'.format(m, h, t, queue, 0)
            self.writer.newline()
            self.writer += 'if {} == {}: continue'.format(h, t)
            self.writer.newline()
            self.writer += '{} = {}.{}()'.format(m, m, MatchMethodTable.Copy)
            self.writer.newline()
            self.writer += '{} = {}({}.{}({}), {}, {}, {})'.format(tmp, functionname, term, TermMethodTable.Get, h, m, h, t)
            self.writer.newline()
            self.writer += '{} += {}'.format(queue, tmp)
            self.writer.newline()
            self.writer += '{} += {}'.format(matches, tmp)
            self.writer.newline().dedent()

            self.writer += 'for {}, {}, {} in {}:'.format(m, h, t, matches)
            self.writer.newline().indent()
            for bindable in rbe.bindables:
                self.writer += '{}.{}(\"{}\")'.format(m, MatchMethodTable.DecreaseDepth, bindable.sym)
                self.writer.newline()
            self.writer.newline().dedent()
            self.writer += 'return {}'.format(matches)
            self.writer.newline().newline().dedent()


    def transformNt(self, nt):
        assert isinstance(nt, ast.Nt)
        if not self.context.get_function_for_pattern(repr(nt)):
            match_fn = 'lang_{}_match_nt_{}'.format('blah', self.symgen.get())
            self.context.add_function_for_pattern(repr(nt), match_fn)

            # first generate isa for NtDefinition 
            if not self.context.get_isa_function_name(nt.prefix):
                self.transform(self.definelanguage.nts[nt.prefix])

            isa_functionname = self.context.get_isa_function_name(nt.prefix)

            term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')
            self.writer += '#{}'.format(repr(nt))
            self.writer.newline()
            self.writer += 'def {}({}, {}, {}, {}):'.format(match_fn, term, match, head, tail)
            self.writer.newline().indent()
            self.writer += 'if {}({}):'.format(isa_functionname, term)
            self.writer.newline().indent()
            self.writer += '{}.{}({}, {})'.format(match, MatchMethodTable.AddToBinding, '\"{}\"'.format(nt.sym), term)
            self.writer.newline()
            self.writer += 'return [({}, {}+1, {})]'.format(match, head, tail)
            self.writer.newline().dedent()
            self.writer += 'return []'
            self.writer.newline().dedent().newline()


    def transformBuiltInPat(self, pat):
        assert isinstance(pat, ast.BuiltInPat)

        if pat.kind == ast.BuiltInPatKind.Number:
            if not self.context.get_isa_function_name(pat.prefix):
                functionname = 'lang_{}_isa_builtin_{}'.format(self.definelanguage.name, pat.prefix)
                self.context.add_isa_function_name(pat.prefix, functionname)

                term = Var('term')
                self.writer += '#Is this term {}?'.format(pat.prefix)
                self.writer.newline()
                self.writer += 'def {}({}):'.format(functionname, term)
                self.writer.newline().indent()
                self.writer += 'if {}.{}() == {}:'.format(term, TermMethodTable.Kind, TermKind.Integer)
                self.writer.newline().indent()
                self.writer += 'return True'
                self.writer.newline().dedent()
                self.writer += 'return False'
                self.writer.newline().dedent().newline()


            term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')
            self.writer += '#{}'.format(repr(pat))
            self.writer.newline()
            match_fn = 'match_lang_{}_builtin_{}'.format('blah', self.symgen.get())
            self.context.add_function_for_pattern(repr(pat), match_fn)
            self.writer += 'def {}({}, {}, {}, {}):'.format(match_fn, term, match, head, tail)
            self.writer.newline().indent()
            self.writer += 'if {}({}):'.format(self.context.get_isa_function_name(pat.prefix), term) #context.findisa_method_forpat FIXME maybe add context object?
            self.writer.newline().indent()
            self.writer += '{}.{}({}, {})'.format(match, MatchMethodTable.AddToBinding, '\"{}\"'.format(pat.sym), term)
            self.writer.newline()
            self.writer += 'return [({}, {}+1, {})]'.format(match,head, tail)
            self.writer.newline().dedent()
            self.writer += 'return []'
            self.writer.newline().dedent().newline()

        if pat.kind == ast.BuiltInPatKind.VariableNotOtherwiseDefined:
            if not self.context.get_isa_function_name(pat.prefix):
                functionname = 'lang_{}_isa_builtin_variable_not_otherwise_mentioned'.format(self.definelanguage.name)
                self.context.add_isa_function_name(pat.prefix, functionname)

                var, _ = self.context.get_variables_mentioned()

                term = Var('term')
                self.writer += '#Is this term {}?'.format(pat.prefix)
                self.writer.newline()
                self.writer += 'def {}({}):'.format(functionname, term)
                self.writer.newline().indent()
                self.writer += 'if  {}.{}() == {} '.format(term, TermMethodTable.Kind, TermKind.Variable)
                self.writer += 'and {}.{}() not in {}:'.format(term, TermMethodTable.Value, var)
                self.writer.newline().indent()
                self.writer += 'return True'
                self.writer.newline().dedent()
                self.writer += 'return False'
                self.writer.newline().dedent().newline()

            # FIXME code duplication; same as above
            term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')
            self.writer += '#{}'.format(repr(pat))
            self.writer.newline()
            match_fn = 'match_lang_{}_builtin_{}'.format('blah', self.symgen.get())
            self.context.add_function_for_pattern(repr(pat), match_fn)
            self.writer += 'def {}({}, {}, {}, {}):'.format(match_fn, term, match, head, tail)
            self.writer.newline().indent()
            self.writer += 'if {}({}):'.format(self.context.get_isa_function_name(pat.prefix), term) #context.findisa_method_forpat FIXME maybe add context object?
            self.writer.newline().indent()
            self.writer += '{}.{}({}, {})'.format(match, MatchMethodTable.AddToBinding, '\"{}\"'.format(pat.sym), term)
            self.writer.newline()
            self.writer += 'return [({}, {}+1, {})]'.format(match,head, tail)
            self.writer.newline().dedent()
            self.writer += 'return []'
            self.writer.newline().dedent().newline()

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

                
                # create lookup function.
                lookupfuncname = 'lang_{}_inhole_{}_impl'.format(self.definelanguage.name, self.symgen.get())
                term, nterm, match, matches = Var('term'), Var('nterm'), Var('match'), Var('matches')
                matches0 = Var('matches0')
                match2 = Var('match2')
                path = Var('path')
                i, hole = Var('i'), Var('hole')

                outmatches = Var('outmatches')
                m, h, t = Var('m'), Var('h'), Var('t')
                m2, h2, t2 = Var('m2'), Var('h2'), Var('t2')
                m3 = Var('m3')

                self.writer += 'def {}({}, {}):'.format(lookupfuncname, term, path)
                self.writer.newline().indent()
                self.writer += '{} = []'.format(outmatches)
                self.writer.newline()
                self.writer += '{} = Match({})'.format(match, list(set(bindablespat2)))
                self.writer.newline()
                self.writer += '{} = {}({}, {}, {}, {})'.format(matches, matchpat2, term, match, 0, 1)
                self.writer.newline()
                self.writer += 'if len({}) != {}:'.format(matches, 0)
                self.writer.newline().indent()
                self.writer += '{} = {}({} + [{}], {})'.format(nterm, TermHelperFuncs.CopyPathAndReplaceLast, path, term, hole)
                self.writer.newline()
                self.writer += '{} = Match({})'.format(match2, list(set(bindablespat1)))
                self.writer.newline()
                self.writer += '{} = {}({}, {}, {}, {})'.format(matches0, matchpat1, nterm, match2, 0, 1)
                self.writer.newline()
                self.writer += 'if len({}) != 0:'.format(matches0)
                self.writer.newline().indent()
                self.writer += 'for {}, {}, {} in {}:'.format(m, h, t, matches)
                self.writer.newline().indent()
                self.writer += 'for {}, {}, {} in {}:'.format(m2, h2, t2, matches0)
                self.writer.newline().indent()
                self.writer += '{} = {}({}, {})'.format(m3, MatchHelperFuncs.CombineMatches, m, m2)
                self.writer.newline()
                self.writer += '{}.append(({}, {}, {}))'.format(outmatches, m3, h, t)
                self.writer.newline().dedent().dedent().dedent().dedent()
                self.writer += "if {}.{}() == {}:".format(term, TermMethodTable.Kind, TermKind.Sequence)
                self.writer.newline().indent()
                self.writer += '{}.append({})'.format(path, term)
                self.writer.newline()
                self.writer += 'for {} in range({}.{}()):'.format(i, term, TermMethodTable.Length)
                self.writer.newline().indent()
                self.writer += '{} += {}({}.{}({}), {})'.format(outmatches, lookupfuncname, term, TermMethodTable.Get, i, path)
                self.writer.newline().dedent()
                self.writer += '{}.pop()'.format(path)
                self.writer.dedent().newline()
                self.writer += 'return {}'.format(outmatches)
                self.writer.newline().dedent().newline()

                self.writer += 'def {}({}):'.format(functionname, term)
                self.writer.newline().indent()
                self.writer += 'return {}({}, [])'.format(lookupfuncname, term)
                self.writer.newline().dedent()


        if pat.kind == ast.BuiltInPatKind.Hole:
            if not self.context.get_isa_function_name(pat.prefix):
                functionname = 'lang_{}_isa_builtin_hole'.format(self.definelanguage.name)
                self.context.add_isa_function_name(pat.prefix, functionname)

                term = Var('term')
                self.writer += '#Is this term {}?'.format(pat.prefix)
                self.writer.newline()
                self.writer += 'def {}({}):'.format(functionname, term)
                self.writer.newline().indent()
                self.writer += 'if  {}.{}() == {}:'.format(term, TermMethodTable.Kind, TermKind.Hole)
                self.writer.newline().indent()
                self.writer += 'return True'
                self.writer.newline().dedent()
                self.writer += 'return False'
                self.writer.newline().dedent().newline()

            if not self.context.get_function_for_pattern(repr(pat)):
                match_fn = 'match_lang_{}_builtin_{}'.format('blah', self.symgen.get())
                self.context.add_function_for_pattern(repr(pat), match_fn)
                # FIXME code duplication; same as above, but do not bind anything...
                term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')
                self.writer += '#{}'.format(repr(pat))
                self.writer.newline()
                self.writer += 'def {}({}, {}, {}, {}):'.format(match_fn, term, match, head, tail)
                self.writer.newline().indent()
                self.writer += 'if {}({}):'.format(self.context.get_isa_function_name(pat.prefix), term) #context.findisa_method_forpat FIXME maybe add context object?
                self.writer.newline().indent()
                self.writer += 'return [({}, {}+1, {})]'.format(match,head, tail)
                self.writer.newline().dedent()
                self.writer += 'return []'
                self.writer.newline().dedent().newline()

    def transformLit(self, lit):
        assert isinstance(lit, ast.Lit)
        if lit.kind == ast.LitKind.Variable:
            if not self.context.get_function_for_pattern(repr(lit)):
                match_fn = 'lang_{}_consume_lit{}'.format('blah', self.symgen.get())
                self.context.add_function_for_pattern(repr(lit), match_fn)
                term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')

                self.writer += '#{}'.format(repr(lit))
                self.writer.newline()
                self.writer += 'def {}({}, {}, {}, {}):'.format(match_fn, term, match, head, tail)
                self.writer.newline().indent()
                self.writer += 'if  {}.{}() == {} '.format(term, TermMethodTable.Kind, TermKind.Variable)
                self.writer += 'and {}.{}() == {}:'.format(term, TermMethodTable.Value, '\"{}\"'.format(lit.lit))
                self.writer.newline().indent()
                self.writer += 'return [({}, {}+1, {})]'.format(match, head, tail)
                self.writer.newline().dedent()
                self.writer += 'return []'
                self.writer.newline().dedent().newline()
