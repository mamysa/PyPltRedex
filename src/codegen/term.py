import src.model.term as term
import src.model.rpython as rpy
from src.util import SymGen
from src.context import CompilationContext

from src.codegen.common import TermHelperFuncs, MatchHelperFuncs, \
                          MatchMethodTable, TermKind, \
                          TermMethodTable

class TermCodegen(term.TermTransformer):
    def __init__(self, modulebuilder, context):
        assert isinstance(modulebuilder, rpy.BlockBuilder)
        assert isinstance(context, CompilationContext)
        self.context = context
        self.modulebuilder = modulebuilder 
        self.symgen = SymGen()

    def _gen_inconsistent_ellipsis_match_counts(self, foreach, bb, symgen):
        # store in the set and assert length of the set is 1
        assert isinstance(bb, rpy.BlockBuilder)
        tmps = []
        for ident, _ in foreach:
            idnt = rpy.gen_pyid_for(ident)
            tmpi = rpy.gen_pyid_temporaries(1, symgen)
            tmps.append(tmpi)
            bb.AssignTo(tmpi).MethodCall(idnt, TermMethodTable.Length)

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
            for paramname in inarg_annotations:
                parameters.append(rpy.PyId(paramname))
        except KeyError:
            pass
        try: 
            matchread_annotations = t.getattribute(term.TermAttribute.MatchRead)
            for sym, paramname in matchread_annotations: 
                matchreads.append((rpy.PyId(paramname), rpy.PyString(sym)))
        except:
            pass
        return match, parameters, matchreads

    def transformPyCall(self, pycall):
        assert isinstance(pycall, term.PyCall)
        # codegen nested terms 
        for t in pycall.termargs:
            self.transform(t)

        match, parameters, matchreads = self._gen_inputs(pycall)
        assert len(matchreads) == 0 and len(parameters) == 0 # expecting only match parameter for pycalls.
        
        # First generate nested terms and then call python function with them as arguments
        symgen = SymGen()
        pycallarguments = [] # will be calling python function with these arguments.


        fb = rpy.BlockBuilder()
        for t in pycall.termargs:
            tmpi = rpy.gen_pyid_temporaries(1, symgen)
            funcname = t.getattribute(term.TermAttribute.FunctionName)[0]
            tmatch, tparameters, _ = self._gen_inputs(t)
            tmpi = rpy.gen_pyid_temporaries(1, symgen)
            pycallarguments.append(tmpi)
            fb.AssignTo(tmpi).FunctionCall(funcname, tmatch, *tparameters)

        funcname = pycall.getattribute(term.TermAttribute.FunctionName)[0]
        tmpi = rpy.gen_pyid_temporaries(1, symgen)

        fb.AssignTo(tmpi).FunctionCall(pycall.functionname, *pycallarguments)
        fb.Return.PyId(tmpi)

        self.modulebuilder.SingleLineComment(repr(pycall))
        self.modulebuilder.Function(funcname).WithParameters(match, *parameters).Block(fb)

        return pycall

    def transformInHole(self, inhole):
        assert isinstance(inhole, term.InHole)
        # T1 = call inhole.term1
        # T2 = call inhole.term2
        # plug(T1, T2)
        self.transform(inhole.term1)
        self.transform(inhole.term2)

        funcname = inhole.getattribute(term.TermAttribute.FunctionName)[0]
        match, parameters, matchreads = self._gen_inputs(inhole)
        #FIXME not sure about this. 
        assert len(matchreads) == 0 

        fb = rpy.BlockBuilder()

        plugholeargs = []
        t1 = rpy.gen_pyid_for('t1')
        t1func = inhole.term1.getattribute(term.TermAttribute.FunctionName)[0]
        t1match, t1parameters, _ = self._gen_inputs(inhole.term1)
        fb.AssignTo(t1).FunctionCall(t1func, t1match, *t1parameters)
        plugholeargs.append(t1)

        t2 = rpy.gen_pyid_for('t2')
        t2func = inhole.term2.getattribute(term.TermAttribute.FunctionName)[0]
        t2match, t2parameters, _ = self._gen_inputs(inhole.term2)
        fb.AssignTo(t2).FunctionCall(t2func, t2match, *t2parameters)
        plugholeargs.append(t2)

        ret = rpy.gen_pyid_for('ret')
        fb.AssignTo(ret).FunctionCall('plughole', *plugholeargs)
        fb.Return.PyId(ret)

        self.modulebuilder.SingleLineComment(repr(inhole))
        self.modulebuilder.Function(funcname).WithParameters(match, *parameters).Block(fb)
        return inhole

    def transformTermSequence(self, termsequence):
        assert isinstance(termsequence, term.TermSequence)
        seqfuncname = termsequence.getattribute(term.TermAttribute.FunctionName)[0]
        symgen = SymGen()

        match, parameters, matchreads = self._gen_inputs(termsequence)
        lst = rpy.gen_pyid_for('lst')
        fb = rpy.BlockBuilder()

        fb.AssignTo(lst).PyList()

        for var, sym in matchreads:
            fb.AssignTo(var).MethodCall(match, MatchMethodTable.GetBinding, sym)

        terms2codegen = [] # we will generate all nested terms after doing this sequence first.
        for t in termsequence.seq:
            if isinstance(t, term.Repeat):

                # for i in range(len(term)):
                #   tmp{i} = term{i}.get{i}
                #   tmp{j} = term{j}.get{i}
                #   ...
                #   tmp{x} = gen_term(tmp{i}, tmp{j} ...)
                #   seq.append(tmp{x})
                
                terms2codegen.append(t)
                foreach = t.getattribute(term.TermAttribute.ForEach)
                self._gen_inconsistent_ellipsis_match_counts(foreach, fb, symgen)

                forb = rpy.BlockBuilder() 
                tmpi = rpy.gen_pyid_temporaries(1, symgen)
                targuments = [] 
                for param, _ in foreach:
                    tmpj, param = rpy.gen_pyid_temporaries(1, symgen), rpy.gen_pyid_for(param)
                    targuments.append(tmpj)
                    forb.AssignTo(tmpj).MethodCall(param, TermMethodTable.Get, tmpi)

                tfunctionname = t.term.getattribute(term.TermAttribute.FunctionName)[0]
                tmpx, tmpy, tmpz = rpy.gen_pyid_temporaries(3, symgen)
                forb.AssignTo(tmpx).FunctionCall(tfunctionname, match, *targuments)
                forb.AssignTo(tmpy).MethodCall(lst, 'append', tmpx)

                fb.AssignTo(tmpz).MethodCall(rpy.gen_pyid_for(foreach[0][0]), TermMethodTable.Length)
                fb.For(tmpi).InRange(tmpz).Block(forb)

            if isinstance(t, term.PatternVariable) or \
               isinstance(t, term.TermSequence)    or \
               isinstance(t, term.TermLiteral)     or \
               isinstance(t, term.InHole)          or \
               isinstance(t, term.MetafunctionApplication):
                terms2codegen.append(t)
                tmatch, tparameters, _ = self._gen_inputs(t)
                func_tocall = t.getattribute(term.TermAttribute.FunctionName)[0]
                tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)

                fb.AssignTo(tmp0).FunctionCall(func_tocall, tmatch, *tparameters)
                fb.AssignTo(tmp1).MethodCall(lst, 'append', tmp0)

            if isinstance(t, term.PyCall):
                terms2codegen.append(t)
                funcname = t.getattribute(term.TermAttribute.FunctionName)[0]
                tmatch, tparameters, _ = self._gen_inputs(t)
                assert len(tparameters) == 0

                if t.mode == term.PyCallInsertionMode.Append:
                    tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)
                    fb.AssignTo(tmp0).FunctionCall(funcname, tmatch, *tparameters)
                    fb.AssignTo(tmp1).MethodCall(lst, 'append', tmp0)
                else:
                    # tmp0 = genterm(...)
                    # tmp1 = tmp0.kind()
                    # if tmp1 != TermKind.Sequence:
                    #  raise Exception(...)
                    # tmp4 = tmp0.length()
                    # for tmp5 in range(tmp4):
                    #   tmp2 = tmp0.get(tmp5)
                    #   tmp3 = lst.append(tmp2)
                    tmp0, tmp1, tmp2, tmp3, tmp4, tmp5 = rpy.gen_pyid_temporaries(6, symgen)

                    ifb = rpy.BlockBuilder()
                    ifb.RaiseException('term is not Sequence!')

                    forb = rpy.BlockBuilder()
                    forb.AssignTo(tmp2).MethodCall(tmp0, TermMethodTable.Get, tmp5)
                    forb.AssignTo(tmp3).MethodCall(lst, 'append', tmp2)

                    fb.AssignTo(tmp0).FunctionCall(funcname, tmatch, *tparameters)
                    fb.AssignTo(tmp1).MethodCall(tmp0, TermMethodTable.Kind)
                    fb.If.NotEqual(tmp1, rpy.PyInt(TermKind.Sequence)).ThenBlock(ifb)
                    fb.AssignTo(tmp4).MethodCall(tmp0, TermMethodTable.Length)
                    fb.For(tmp5).InRange(tmp4).Block(forb)

        tmpi = rpy.gen_pyid_temporaries(1, symgen)
        fb.AssignTo(tmpi).New('Sequence', lst)
        fb.Return.PyId(tmpi)

        self.modulebuilder.SingleLineComment(repr(termsequence))
        self.modulebuilder.Function(seqfuncname).WithParameters(match, *parameters).Block(fb)

        for t in terms2codegen:
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
            bb.Return.PyId(ident)
        else:
            assert len(parameters) == 1
            bb.Return.PyId(parameters[0])

        self.modulebuilder.SingleLineComment(repr(node))
        self.modulebuilder.Function(funcname).WithParameters(match, *parameters).Block(bb)
        return node

    def transformTermLiteral(self, node):
        assert isinstance(node, term.TermLiteral)
        funcname = node.getattribute(term.TermAttribute.FunctionName)[0]
        var = self.context.get_sym_for_lit_term(node)
        fb = rpy.BlockBuilder()
        fb.Return.PyId( rpy.PyId(var) )
        match, parameters, matchreads = self._gen_inputs(node)
        self.modulebuilder.Function(funcname).WithParameters(match).Block(fb)
        return node

    def transformMetafunctionApplication(self, node):
        assert isinstance(node, term.MetafunctionApplication)
        nameof_function = node.getattribute(term.TermAttribute.FunctionName)[0]
        nodematch, nodeparameters, nodematchreads = self._gen_inputs(node)
        assert len(nodematchreads) == 0 

        self.transform(node.termtemplate)

        ttmatch, ttparameters, _ = self._gen_inputs(node.termtemplate)
        func_tocall = node.termtemplate.getattribute(term.TermAttribute.FunctionName)[0]

        metafunctionfunc = self.context.get_metafunction(node.metafunctionname)

        symgen = SymGen()
        tmp0, tmp1 = rpy.gen_pyid_temporaries(2, symgen)

        fb = rpy.BlockBuilder()
        fb.AssignTo(tmp0).FunctionCall(func_tocall, ttmatch, *ttparameters)
        fb.AssignTo(tmp1).FunctionCall(metafunctionfunc, tmp0)
        fb.Return.PyId(tmp1)
        self.modulebuilder.Function(nameof_function).WithParameters(nodematch, *nodeparameters).Block(fb)
