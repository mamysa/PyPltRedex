import src.term as term
import src.astdefs as ast
import src.rpython as rpy
from src.symgen import SymGen
from src.preprocdefinelang import LanguageContext

# Need to annotate term template to ease code generation. Given a pattern variable n
# and associated ellipsis depth, we keep track of the path to the pattern variable in the term 
# and annotate terms on the path as follows:
# (1) Set depth to zero after discovering pattern variable.
# (2) if path(term) == Repeat:        annotate term with ForEach(n, depth + 1)
# (3) if path(term) == TermSequence:  annotate term with InArg(n, symgen(n), from-match)
#     from-match indicates where term to be plugged to come from - either is a function argument or 
#     should be taken directly from match object that is passed around.
# Ensure the number of elllipses equal to ellipsis depth of n has been consumed on the path.
# Once all pattern variables all been resolved, ensure that there are no-unannotated ellipses. Along the way
# collect all literal terms and assign a variable to them - this way there will be only a single instance of the term.

class TermAnnotate(term.TermTransformer):

    def __init__(self, variables, idof, context):
        self.idof = idof
        self.path = []
        self.context = context
        self.variables = variables
        self.symgen = SymGen()

    def transform(self, element):
        assert isinstance(element, term.Term)
        method_name = 'transform' + element.__class__.__name__
        method_ref = getattr(self, method_name)
        self.path.append(element)
        result = method_ref(element)
        self.path.pop()
        return result 

    def transformTermLiteral(self, literal):
        assert isinstance(literal, term.TermLiteral)
        self.context.add_lit_term(literal)
        return literal

    def transformPyCall(self, pycall):
        assert isinstance(pycall, term.PyCall)
        sym = self.symgen.get('{}_gen_term'.format(self.idof))
        terms = []
        for t in pycall.termargs:
            idof = self.symgen.get('{}_pycall_gen_term_'.format(self.idof))
            transformer = TermAnnotate(self.variables, idof, self.context)
            terms.append( transformer.transform(t) )

        return term.PyCall(pycall.mode, pycall.functionname, terms) \
                   .addattribute(term.TermAttribute.FunctionName, sym)

    def transformRepeat(self, repeat):
        assert isinstance(repeat, term.Repeat)
        nrepeat = term.Repeat(self.transform(repeat.term)).copyattributesfrom(repeat)
        if len(nrepeat.getattribute(term.TermAttribute.ForEach)) == 0:
            raise Exception('too many ellipses in template {}'.format(repr(repeat)))
        return nrepeat

    def transformTermSequence(self, termsequence):
        ntermsequence = super().transformTermSequence(termsequence)
        sym = self.symgen.get('{}_gen_term'.format(self.idof))
        return ntermsequence.addattribute(term.TermAttribute.FunctionName, sym)

    def transformInHole(self, inhole):
        ninhole = super().transformInHole(inhole)
        sym = self.symgen.get('{}_gen_term'.format(self.idof))
        return ninhole.addattribute(term.TermAttribute.FunctionName, sym)

    def transformUnresolvedSym(self, node):
        assert isinstance(node, term.UnresolvedSym)
        if node.sym not in self.variables:
            t = term.TermLiteral(term.TermLiteralKind.Variable, node.sym)
            self.context.add_lit_term(t)
            return t
        expecteddepth, _ = self.variables[node.sym] 
        actualdepth = 0

        param = self.symgen.get(node.sym)
        # definitely a pattern variable now, topmost entry on the stack is this node. 
        for t in reversed(self.path): 
            if isinstance(t, term.UnresolvedSym): 
                if expecteddepth == 0:
                    t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, True))
                    break
                t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, False))
            if isinstance(t, term.TermSequence) or isinstance(t, term.InHole):
                if expecteddepth == actualdepth:
                    t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, True))
                    break
                else:
                    t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, False))
            if isinstance(t, term.Repeat):
                actualdepth += 1
                t.addattribute(term.TermAttribute.ForEach, (param, actualdepth))

        if actualdepth != expecteddepth:
            raise Exception('inconsistent ellipsis depth for pattern variable {}: expected {} actual {}'.format(node.sym, expecteddepth, actualdepth))

        sym = self.symgen.get('{}_gen_term'.format(self.idof))
        return term.PatternVariable(node.sym).copyattributesfrom(node).addattribute(term.TermAttribute.FunctionName, sym)


# ---- FIXME code duplication from patcodegen
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

#---End code duplication

class TermCodegen(term.TermTransformer):
    def __init__(self, writer, context):
        assert isinstance(modulebuilder, rpy.BlockBuilder)
        self.context = context
        self.modulebuilder = modulebuilder 
        self.symgen = SymGen()

    def _check_inconsistent_ellipsis_match_counts(self, foreach, bb, symgen):
        # store in the set and assert length of the set is 1
        assert isinstance(bb, rpy.BlockBuilder)
        tmps = []
        for ident, _ in foreach:
            idnt = rpy.gen_pyid_for(ident)
            tmpi = rpy.gen_pyid_temporaries(1, symgen)
            tmps.append(tmpi)
            bb.AssignTo(tmpi).MethodCall(ident, TermMethodTable.Length)

        
        ifb = rpy.BlockBuilder()
        ifb.RaiseException('inconsistent ellipsis match counts')

        lengths = rpy.gen_pyid_for('lengths')
        bb.AssignTo(lengths).PySet(*tmps)
        bb.If.LengthOf(lengths).NotEqual(rpy.PyInt(1)).ThenBlock(ifb)

    # Reads InArg annotation and creates two arrays - one with function parameters 
    # and another one with (PyID(paramname), PyString(sym)) pairs that will be used to create
    # paramname = match.getbinding(sym) statements.
    def _gen_inputs(self, t):
        match = rpy.PyId('match') 
        parameters = []
        matchreads = []
        try:
            inarg_annotations = t.getattribute(term.TermAttribute.InArg)
            for sym, paramname, depth, frommatch in inarg_annotations:
                if frommatch:
                    matchreads.append((rpy.PyId(paramname), rpy.PyString(sym)))
                else:
                    parameters.append(rpy.PyId(paramname))
        except KeyError:
            pass
        return match, parameters, matchreads

    def transformPyCall(self, pycall):
        assert isinstance(pycall, term.PyCall)
        # codegen nested terms 
        for t in pycall.termargs:
            self.transform(t)

        funcname = pycall.getattribute(term.TermAttribute.FunctionName)[0]
        match, parameters, matchreads = self._gen_inputs(pycall)
        assert len(matchreads) == 0 and len(parameters) == 0 # expecting only match parameter for pycalls.
        
        # First generate nested terms and then call python function with them as arguments
        symgen = SymGen()
        pycallarguments = [] # will be calling python function with these arguments.


        fb = rpy.BlockBuilder()
        for t in pycall.termargs:
            tmpi = rpy.gen_pyid_temporaries(1, symgen)
            if isinstance(t, term.TermLiteral):
                litterm = rpy.gen_pyid_for( self.context.get_sym_for_lit_term(t) )
                pycallarguments.append(litterm)
            else:
                funcname = t.getattribute(term.TermAttribute.FunctionName)[0]
                tmatch, tparameters, _ = self._gen_inputs(t)
                tmpi = rpy.gen_pyid_temporaries(1, symgen)
                fb.AssignTo(tmpi).FunctionCall(funcname, tmatch, *tparameters)


        tmpi = rpy.gen_pyid_temporaries(1, symgen)

        fb.AssignTo(tmpi).FunctionCall(pycall.functionname, match, *pycallarguments)
        fb.Return.PyId(tmpi)

        self.modulebuilder.SingleLineComment(repr(pycall))
        self.modulebuilder.Function(funcname).WithParameters(match, *parameters)

        return pycall

    def transformInHole(self, inhole):
        assert isinstance(inhole, term.InHole)
        # T1 = call inhole.term1
        # T2 = call inhole.term2
        # plug(T1, T2)
        funcname = inhole.getattribute(term.TermAttribute.FunctionName)[0]
        parameters, _ = self._gen_params(inhole) 

        self.writer += '# {}'.format(repr(inhole))
        self.writer.newline()
        self.writer += 'def {}({}):'.format(funcname, parameters)
        self.writer.newline().indent()

        term1var = self.symgen.get('term1_')
        if isinstance(inhole.term1, term.TermLiteral):
            sym = self.context.get_sym_for_lit_term(inhole.term1)
            self.writer += '{} = {}'.format(term1var, sym)
            self.writer.newline()
        else:
            term1func = inhole.term1.getattribute(term.TermAttribute.FunctionName)[0]
            term1parameters, _ = self._gen_params(inhole.term1)
            self.writer += '{} = {}({})'.format(term1var, term1func, term1parameters)
            self.writer.newline()


        term2var = self.symgen.get('term2_')
        if isinstance(inhole.term2, term.TermLiteral):
            sym = self.context.get_sym_for_lit_term(inhole.term2)
            self.writer += '{} = {}'.format(term2var, sym)
            self.writer.newline()
        else:
            term2func = inhole.term2.getattribute(term.TermAttribute.FunctionName)[0]
            term2parameters, _ = self._gen_params(inhole.term2)
            self.writer += '{} = {}({})'.format(term2var, term2func, term2parameters)
            self.writer.newline()

        self.writer += 'return plughole({}, {})'.format(term1var, term2var)
        self.writer.newline().dedent().newline()
        self.transform(inhole.term1)
        self.transform(inhole.term2)
        return inhole

    def transformTermSequence(self, termsequence):
        assert isinstance(termsequence, term.TermSequence)
        funcname = termsequence.getattribute(term.TermAttribute.FunctionName)[0]
        parameters, _ = self._gen_params(termsequence)

        seq = common.Var('seq')

        self.writer += '# {}'.format(repr(termsequence))
        self.writer.newline()
        self.writer += 'def {}({}):'.format(funcname, parameters)
        self.writer.newline().indent()
        self.writer += '{} = []'.format(seq)
        self.writer.newline()

        match_reads = self._get_reads_from_match(termsequence)
        for sym, paramname in match_reads:
            self.writer += '{} = {}.{}(\'{}\')'.format(paramname, 'match', 'getbinding', sym)
            self.writer.newline()

        entries_to_transform = []

        for t in termsequence.seq:
            if isinstance(t, term.Repeat):
                entries_to_transform.append(t.term)
                foreach = t.getattribute(term.TermAttribute.ForEach)
                self._check_inconsistent_ellipsis_match_counts(foreach)
                i = common.Var('i')
                first = foreach[0][0]


                self.writer += 'for {} in range({}.length()):'.format(i, first)
                self.writer.newline().indent()
                tmps = ['match']

                for param, _ in foreach:
                    tmp, param = common.Var(self.symgen.get()), common.Var(param)
                    self.writer += '{} = {}.get({})'.format(tmp, param, i)
                    self.writer.newline()
                    tmps.append(tmp.name)

                tmps = ', '.join(tmps)
                func_tocall = t.term.getattribute(term.TermAttribute.FunctionName)[0]
                self.writer += '{}.append( {}({}) )'.format(seq, func_tocall, tmps)
                self.writer.newline().dedent()

            if isinstance(t, term.PatternVariable) or \
               isinstance(t, term.TermSequence)    or \
               isinstance(t, term.InHole):
                entries_to_transform.append(t)
                parameters, _ = self._gen_params(t)
                func_tocall = t.getattribute(term.TermAttribute.FunctionName)[0]
                self.writer += '{}.append( {}({}) )'.format(seq, func_tocall, parameters)
                self.writer.newline()

            if isinstance(t, term.PyCall):
                entries_to_transform.append(t)
                funcname = t.getattribute(term.TermAttribute.FunctionName)[0]
                parameters, numparameters = self._gen_params(t)
                assert numparameters == 1

                if t.mode == term.PyCallInsertionMode.Append:
                    self.writer += '{}.append( {}({}) )'.format(seq, funcname, parameters)
                    self.writer.newline()
                else:
                    var = self.symgen.get()
                    self.writer += '{} = {}({})'.format(var, funcname, parameters)
                    self.writer.newline()
                    self.writer += 'assert {}.kind() == TermKind.Sequence'.format(var)
                    self.writer.newline()
                    it = self.symgen.get()
                    self.writer += 'for {} in range({}.length()):'.format(it, var)
                    self.writer.newline().indent()
                    self.writer += '{}.append( {}.get({}) )'.format(seq, var, it)
                    self.writer.newline().dedent()

            if isinstance(t, term.TermLiteral):
                self.writer += '{}.append( {} )'.format(seq, self.context.get_sym_for_lit_term(t))
                self.writer.newline()


        self.writer += 'return Sequence({})'.format(seq)
        self.writer.newline().dedent().newline()

        for t in entries_to_transform:
            self.transform(t)
        return termsequence

    def transformPatternVariable(self, node):
        funcname = node.getattribute(term.TermAttribute.FunctionName)[0]
        match, parameters, matchreads = self._gen_inputs(node)

        bb = rpy.BlockBuilder()

        if len(parameters) == 0:
            # must be of ellipsis depth 0
            assert len(matchreads) == 1
            ident, sym = matchreads[0]
            bb.AssignTo(ident).MethodCall(match, MatchMethodTable.GetBinding, sym)
            bb.Return(ident)
        else:
            assert len(parameters) == 1
            bb.Return(parameters[0])


        self.modulebuilder.SingleLineComment(repr(node))
        self.modulebuilder.Function(funcname).WithParameters(module, *parameters).Block(bb)
        return node
