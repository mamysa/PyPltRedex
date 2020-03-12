import src.astdefs as ast
import enum

class Module:
    def __init__(self, nodes):
        self.nodes = nodes


class Function:
    def __init__(self, name, parameters, body):
        self.name = name
        self.parameters = parameters
        self.body = body 

    def get_parameter_at_position(self, key):
        return self.parameters[key]

    def add(self, stmt):
        self.body.append(stmt)

class LitArray:
    def __init__(self, contents):
        self.contents = contents

class Break:
    pass

class MatchTuple:
    def __init__(self, match, head, tail):
        self.match = match
        self.head  = head
        self.tail  = tail

class ForEach:
    def __init__(self, varset, where, stmts):
        self.vars = varset 
        self.where = where 
        self.stmts = stmts 

class LengthOfMatchList:
    def __init__(self, match):
        self.match = match

class NewSet:
    def __init__(self, contents):
        self.contents = contents

class ItemNotInSet:
    def __init__(self, key, setobj):
        self.key = key
        self.setobj = setobj

class Call:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

class Var:
    def __init__(self, name):
        self.name = name

class NewMatch:
    def __init__(self, bindables):
        self.bindables = bindables

class ConstantInt:
    def __init__(self, constant):
        self.constant = constant

class Return:
    def __init__(self, returnvalues):
        self.returnvalues = returnvalues 

Null = Var('None')

class SymGen:
    def __init__(self):
        self.syms = {}

    def get(self, var='tmp'):
        if var not in self.syms:
            self.syms[var] = 0
        val = self.syms[var]
        self.syms[var] += 1
        return '{}{}'.format(var, val)

class Assign:
    def __init__(self, ident, expr):
        self.idents = ident
        self.expressions = expr 

class Binary:
    def __init__(self, op, lhs, rhs):
        self.op  = op
        self.lhs = lhs
        self.rhs = rhs

class BinaryOp(enum.Enum):
    Add = '+'
    Sub = '-'
    And = ' and ' 
    EqEqual = '=='
    NotEqual = '!='
    GrEq = '>='
    Lt = '<'

class If:
    def __init__(self, cond, thenbr, elsebr):
        self.cond = cond
        self.thenbr = thenbr
        self.elsebr = elsebr


class While:
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body


class ReturnTrueIfNotNull:
    def __init__(self, matchlist):
        self.matchlist = matchlist

class ConstantBoolean:
    def __init__(self, value):
        self.value = value


class StringLiteral:
    def __init__(self, value):
        self.value = value

class ArrayConcat:
    def __init__(self, array, expr):
        self.array = array
        self.expr = expr

class ArrayAppend:
    def __init__(self, array, expr):
        self.array = array
        self.expr = expr

class TermLength:
    def __init__(self, term):
        self.term = term


class TermInvokeMethod:
    def __init__(self, term, methodname, args=[]):
        self.term = term 
        self.methodname = methodname 
        self.args = args

class AstDump:
    def __init__(self):
        self.indents = 0
        self.buf = []
        self.should_insert_tabs = True 

    def indent(self):
        self.indents += 1

    def newline(self):
        self.buf.append('\n')
        self.should_insert_tabs = True

    def dedent(self):
        self.indents -= 1

    def emit(self, string):
        if self.should_insert_tabs:
            self.buf.append(' '*self.indents*4)
            self.should_insert_tabs = False
        self.buf.append(string)

    def comma_separated_list(self, lst):
        if len(lst) == 0: 
            return
        for elem in lst[:-1]:
            self.write(elem)
            self.emit(', ')
        self.write(lst[-1])


    def write(self, element):
        #assert isinstance(element, ast.AstNode)
        method_name = 'write' + element.__class__.__name__
        method_ref = getattr(self, method_name)
        return method_ref(element)

    def writeBreak(self, node):
        self.emit('break')

    def writeModule(self, module):
        self.emit('from match import Match') # FIXME HANDLE IMPORTS SEPARATELY
        self.newline()
        for n in module.nodes:
            self.write(n)
            self.newline()

    def writeNewSet(self, node):
        assert isinstance(node, NewSet)
        self.emit('set ')
        self.emit('(')
        self.emit(repr(list(node.contents)))
        self.emit(')')

    def writeMatchTuple(self, node):
        assert isinstance(node, MatchTuple)
        self.emit('(')
        self.comma_separated_list([node.match, node.head, node.tail])
        self.emit(')')


    def writeNewMatch(self, node):
        assert isinstance(node, NewMatch)
        self.emit('Match')
        self.emit('(')
        self.emit(repr(list(node.bindables)))
        self.emit(')')

    def writeForEach(self, node):
        assert isinstance(node, ForEach)
        self.emit('for ')
        self.comma_separated_list(node.vars)
        self.emit(' in ')
        self.write(node.where)
        self.emit(':')
        self.newline()
        self.indent()
        for b in node.stmts:
            self.write(b)
            self.newline()
        self.dedent()

    def writeArrayConcat(self, node):
        assert isinstance(node, ArrayConcat)
        self.write(node.array)
        self.emit(' += ') 
        self.write(node.expr)

    def writeArrayAppend(self, node):
        assert isinstance(node, ArrayAppend)
        self.write(node.array)
        self.emit('.append(') 
        self.write(node.expr)
        self.emit(')') 

    def writeLengthOfMatchList(self, node):
        assert isinstance(node, LengthOfMatchList)
        self.emit('len(')
        self.write(node.match)
        self.emit(')')

    def writeItemNotInSet(self, node):
        assert isinstance(node, ItemNotInSet)
        self.write(node.key)
        self.emit(' not in ')
        self.write(node.setobj)

    def writeComment(self, comment):
        self.emit('# ')
        self.emit(comment.contents)
        self.newline()

    def writeFunction(self, function):
        assert isinstance(function, Function)
        self.emit('def {}'.format(function.name))
        self.emit('(')
        self.comma_separated_list(function.parameters)
        self.emit(')')
        self.emit(':')

        self.newline()

        self.indent()
        for b in function.body:
            self.write(b)
            self.newline()
        self.dedent()
        self.newline()

    def writeStringLiteral(self, expr):
        self.emit('"')
        self.emit(expr.value)
        self.emit('"')

    def writeBinary(self, expr):
        assert isinstance(expr, Binary)

        self.write(expr.lhs) 
        self.emit(expr.op.value)
        self.write(expr.rhs)

    def writeAssign(self, stmt):
        assert isinstance(stmt, Assign)
        self.write(stmt.idents)
        self.emit(' = ')
        self.write(stmt.expressions)

    def writeIf(self, stmt):
        assert isinstance(stmt, If)
        self.emit('if ')
        self.write(stmt.cond)
        self.emit(':')
        
        self.newline()
        self.indent()

        for b in stmt.thenbr:
            self.write(b)
            self.newline()
        self.dedent()

        if stmt.elsebr != None:
            self.emit('else :')
            self.newline()
            self.indent()
            for b in stmt.elsebr:
                self.write(b)
                self.newline()
            self.dedent()

    def writeWhile(self, stmt):
        assert isinstance(stmt, While)
        self.emit('while ')
        self.write(stmt.cond)
        self.emit(':')

        self.newline()
        self.indent()

        for b in stmt.body:
            self.write(b)
            self.newline()
        self.dedent()

    def writeLitArray(self, array):
        assert isinstance(array, LitArray)
        self.emit('[')
        self.comma_separated_list(array.contents)
        self.emit(']')

    def writeCall(self, stmt):
        assert isinstance(stmt, Call)
        self.emit(stmt.name)
        self.emit('(')
        self.comma_separated_list(stmt.arguments)
        self.emit(')')

    def writeReturn(self, stmt):
        self.emit('return ')
        self.comma_separated_list(stmt.returnvalues)

    def writeReturnTrueIfNotNull(self, expr):
        assert isinstance(expr, ReturnTrueIfNotNull)
        self.emit('if ')
        self.write(expr.matchlist)
        self.emit(' != None:')
        self.newline()
        self.indent()
        self.emit('return True')
        self.dedent()

    # MERGE ALL THESE INTO ONE CLASS
    def writeConstantInt(self, stmt): 
        assert isinstance(stmt, ConstantInt)
        self.emit(str(stmt.constant))

    def writeConstantBoolean(self, stmt):
        assert isinstance(stmt, ConstantBoolean)
        self.emit(str(stmt.value))

    def writeVar(self, var):
        assert isinstance(var, Var)
        return self.emit(str(var.name))

    def writeTermInvokeMethod(self, term):
        assert isinstance(term, TermInvokeMethod)
        self.write(term.term)
        self.emit('.')
        self.emit(term.methodname)
        self.emit('(')
        self.comma_separated_list(term.args)
        self.emit(')')


class TermKind:
    Variable = 0
    Integer  = 1
    TermList = 2 


class DefineLanguagePatFunctionParameterIndex:
    Term = 0
    Match = 1
    Head = 2
    Tail = 3

class IsANtFunctionParameterIndex:
    Term = 0

class Comment:
    def __init__(self, contents):
        self.contents = contents

class ModuleBuilder:
    def __init__(self):
        self.nodes = []

    def add_comment(self, comment):
        self.nodes.append(Comment(comment))
        return self

    def add_function(self, f):
        self.nodes.append(f)
        return self

    def add_global(self, var, expr):
        self.nodes.append( Assign(var, expr) )

    def build(self):
        return Module(self.nodes)

class FunctionBuilder:
    def __init__(self):
        self.name = None
        self.parameters = None
        self.symgen = SymGen()
        self.statements = []

    def with_name(self, name):
        self.name = name
        return self

    def with_number_of_parameters(self, num):
        self.parameters = [ None ] * num
        return self

    def set_parameter(self, offset, var):
        assert isinstance(var, Var)
        self.parameters[offset] = var
        return self

    def get_fresh_local(self, var):
        return Var(self.symgen.get(var))

    def add(self, stmt):
        self.statements.append(stmt)
        return self

    def build(self):
        return Function(self.name, self.parameters, self.statements)

def gen_functionname_for(lang, nt):
    return 'match_lang_{}_pat_nt_{}'.format(lang, nt.prefix)


class DefineLanguagePatternCodegen(ast.PatternTransformer):
    def __init__(self):
        self.modulebuilder = ModuleBuilder()
        self.processed = {}  # map of repr(pat) -> function-name
        self.symgen = SymGen() 

    def transformDefineLanguage(self, node):
        assert isinstance(node, ast.DefineLanguage)
        self.definelanguage = node

        for nt in node.nts.values():
            self.transform(nt)

    def transformNtDefinition(self, node):
        assert isinstance(node, ast.NtDefinition)
        if repr(node.nt) not in self.processed:
            functionname = gen_functionname_for(self.definelanguage.name, node.nt)
            self.processed[repr(node.nt)] = functionname

            term, head, tail = Var('term'), Var('head'), Var('tail')
            fb = FunctionBuilder().with_name(functionname)       \
                                  .with_number_of_parameters(3)  \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Term, term) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Head, head) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Tail, tail) 
                                  
            for pat in node.patterns:
                self.transform(pat)
                patfunctionname = self.processed[repr(pat)]
                result, nhead, ntail = fb.get_fresh_local('result'), fb.get_fresh_local('head'), fb.get_fresh_local('tail')

                fb.add(Call([result, nhead, ntail], patfunctionname, [term, head, tail]))
                fb.add(If( Binary(BinaryOp.EqEqual, result, ConstantBoolean(True)), [
                        Return([ConstantBoolean(True), nhead, ntail])
                    ], None))


            fb.add(Return([ConstantBoolean(False), head, tail]))

            self.modulebuilder.add_comment(repr(node))
            self.modulebuilder.add_function(fb.build())

    def transformPatSequence(self, node):
        assert isinstance(node, ast.PatSequence)
        if repr(node) in self.processed:
            return 
        
        functionname = 'match_term_{}'.format(self.symgen.get())
        self.processed[repr(node)] = functionname

        term, head, tail = Var('term'), Var('head'), Var('tail')
        fb = FunctionBuilder().with_name(functionname)       \
                              .with_number_of_parameters(3)  \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Term, term) \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Head, head) \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Tail, tail) 

        fb.add(If(Binary(BinaryOp.NotEqual, TermInvokeMethod(term, 'kind'), ConstantInt(TermKind.TermList)), [Return([ConstantBoolean(False), head, tail])], None))

        # need to "enter" term (i.e. extract term at index head), 
        # set new subterm_head = 0 and subterm_tail = len(term[head])
        subterm, subhead, subtail = Var('subterm'), Var('subhead'), Var('subtail')
        fb.add(Assign(subhead, ConstantInt(0)))
        fb.add(Assign(subtail, TermInvokeMethod(term, 'length')))

        # ensure number of terms in the sequence is at least equal to number of non-repeated patterns. 
        # if num_required is zero, condition is always false.
        num_required = node.get_number_of_nonoptional_matches_between(0, len(node))
        if num_required != 0: 
            cond = Binary(BinaryOp.Sub, Binary(BinaryOp.Sub, subtail, subhead), ConstantInt(1))
            cond = Binary(BinaryOp.Lt, cond, ConstantInt(num_required))
            fb.add(If(cond, [ Return([ConstantBoolean(False), head, tail]) ], None))

        for i, pat in enumerate(node.seq):
            self.transform(pat)
            patfunctionname = self.processed[repr(pat)]
            subresult, nsubhead, nsubtail = fb.get_fresh_local('subresult'), fb.get_fresh_local('subhead'), fb.get_fresh_local('subtail')

            if isinstance(pat, ast.Repeat):
                fb.add(Call([subresult, nsubhead, nsubtail], patfunctionname, [term, subhead, subtail]))

                # after matching optional repetition, ensure there are still enough terms in sequence
                # to produce a successful match.
                num_required = node.get_number_of_nonoptional_matches_between(i, len(node))
                if len(node) - 1 > i and num_required != 0:
                    cond = Binary(BinaryOp.Sub, Binary(BinaryOp.Sub, nsubtail, nsubhead), ConstantInt(1))
                    cond = Binary(BinaryOp.Lt, cond, ConstantInt(num_required))
                    fb.add(If(cond, [ Return([ConstantBoolean(False), head, tail]) ], None))
            else:
                fb.add(Call([subresult, nsubhead, nsubtail], patfunctionname, [TermInvokeMethod(term, 'get', [subhead]), subhead, subtail]))
                fb.add(If(Binary(BinaryOp.NotEqual, subresult, ConstantBoolean(True)), [Return([ConstantBoolean(False), head, tail])], None))
            subhead, subtail = nsubhead, nsubtail 

        # ensure the end of the term has been reached.
        fb.add(If(Binary(BinaryOp.NotEqual, nsubhead, nsubtail), [Return([ConstantBoolean(False), head, tail])], None))

        # need to "leave" term 
        fb.add(Assign(head, Binary(BinaryOp.Add, head, ConstantInt(1))))
        fb.add(Return([ConstantBoolean(True), head, tail]))


        self.modulebuilder.add_comment(repr(node))
        self.modulebuilder.add_function(fb.build())


    def transformBuiltInPat(self, node):
        assert isinstance(node, ast.BuiltInPat)
        if repr(node) in self.processed:
            return node

        if node.kind == ast.BuiltInPatKind.Number:
            functionname = 'lang_{}_match_number'.format(self.definelanguage.name)
            self.processed[repr(node)] = functionname 

            term, head, tail = Var('term'), Var('head'), Var('tail')
            fb = FunctionBuilder().with_name(functionname)       \
                                  .with_number_of_parameters(3)  \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Term, term) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Head, head) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Tail, tail) 


            cond = Binary(BinaryOp.EqEqual, TermInvokeMethod(term, 'kind'), ConstantInt(TermKind.Integer))
            thenbr = [ Assign(head, Binary(BinaryOp.Add, head, ConstantInt(1))),
                       Return([ConstantBoolean(True),  head, tail]) ]
            fb.add(If(cond, thenbr, None))
            fb.add( Return([ConstantBoolean(False), head, tail]) )
            self.modulebuilder.add_comment(repr(node))
            self.modulebuilder.add_function(fb.build())
            return node

        if node.kind == ast.BuiltInPatKind.VariableExcept:
            functionname = 'lang_{}_match_variable_except'.format(self.definelanguage.name)

            setglobal = Var(self.symgen.get())
            self.modulebuilder.add_global(setglobal, NewSet(list(node.aux)))

            self.processed[repr(node)] = functionname 

            term, head, tail = Var('term'), Var('head'), Var('tail')
            fb = FunctionBuilder().with_name(functionname)       \
                                  .with_number_of_parameters(3)  \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Term, term) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Head, head) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Tail, tail) 


            cond1 = Binary(BinaryOp.EqEqual, TermInvokeMethod(term, 'kind'), ConstantInt(TermKind.Variable))
            cond2 = ItemNotInSet(TermInvokeMethod(term, 'value'), setglobal)
            cond  = Binary(BinaryOp.And, cond1, cond2)
            thenbr = [ Assign(head, Binary(BinaryOp.Add, head, ConstantInt(1))),
                       Return([ConstantBoolean(True),  head, tail]) ]
            fb.add(If(cond, thenbr, None))
            fb.add( Return([ConstantBoolean(False), head, tail]) )
            self.modulebuilder.add_comment(repr(node))
            self.modulebuilder.add_function(fb.build())
            return node


        assert node.kind != ast.BuiltInPatKind.VariableNotOtherwiseDefined
        assert False, 'unknown built-in pattern type'

    def transformNt(self, node):
        assert isinstance(node, ast.Nt)
        if repr(node) not in self.processed:
            self.transform(self.definelanguage.nts[node.sym])

    def transformRepeat(self, node):
        assert isinstance(node, ast.Repeat)
        if repr(node) not in self.processed:
            functionname = 'lang_{}_match_rep_{}'.format(self.definelanguage.name, self.symgen.get())
            self.processed[repr(node)] = functionname 

            term, head, tail = Var('term'), Var('head'), Var('tail')
            fb = FunctionBuilder().with_name(functionname)       \
                                  .with_number_of_parameters(3)  \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Term, term) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Head, head) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Tail, tail) 


            self.transform(node.pat)
            patfunctionname = self.processed[repr(node.pat)]


            match = fb.get_fresh_local('match')

            loop = While(Binary(BinaryOp.Lt, head, tail), [
                Call([match, head, tail], patfunctionname, [TermInvokeMethod(term, 'get', [head]), head, tail]),
                If(Binary(BinaryOp.NotEqual, match, ConstantBoolean(True)), [
                    Return([ConstantBoolean(True), head, tail])
                ], None)
            ])
            fb.add(loop)
            fb.add(Return([ConstantBoolean(True), head, tail]))

            self.modulebuilder.add_comment(repr(node))
            self.modulebuilder.add_function(fb.build())


    def transformLit(self, node):
        assert isinstance(node, ast.Lit)

        if node.kind == ast.LitKind.Variable:
            functionname = 'lang_{}_match_lit_{}'.format(self.definelanguage.name, self.symgen.get())
            self.processed[repr(node)] = functionname 

            term, head, tail = Var('term'), Var('head'), Var('tail')
            fb = FunctionBuilder().with_name(functionname)       \
                                  .with_number_of_parameters(3)  \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Term, term) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Head, head) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Tail, tail) 


            cond1 = Binary(BinaryOp.EqEqual, TermInvokeMethod(term, 'kind'), ConstantInt(TermKind.Variable))
            cond2 = Binary(BinaryOp.EqEqual, TermInvokeMethod(term, 'value'), StringLiteral(node.lit))
            cond  = Binary(BinaryOp.And, cond1, cond2)
            thenbr = [ Assign(head, Binary(BinaryOp.Add, head, ConstantInt(1))),
                       Return([ConstantBoolean(True),  head, tail]) ]
            fb.add(If(cond, thenbr, None))
            fb.add( Return([ConstantBoolean(False), head, tail]) )
            self.modulebuilder.add_comment(repr(node))
            self.modulebuilder.add_function(fb.build())
            return node
        
        assert False, 'unknown lit kind ' + str(node.kind)


class RetrieveBindableElements(ast.PatternTransformer):
    
    def __init__(self):
        self.bindables = []

    def transformNt(self, node):
        self.bindables.append(node)
        return node

    def transformBuiltInPat(self, node):
        self.bindables.append(node)
        return node

class DefineLanguagePatternCodegen2(ast.PatternTransformer):

    def __init__(self):
        self.modulebuilder = ModuleBuilder()
        self.isa_nt_functionnames = {} # mapping of Nt.sym to is_a function name
        self.symgen = SymGen()
        self.processed_patterns = {} 

    def transformDefineLanguage(self, node):
        assert isinstance(node, ast.DefineLanguage)
        self.definelanguage = node

        for nt in node.nts.values():
            self.transform(nt)

    def transformNtDefinition(self, node):
        assert isinstance(node, ast.NtDefinition)
        if node.nt.prefix not in self.isa_nt_functionnames:
            functionname = 'lang_{}_isa_nt_{}'.format(self.definelanguage.name, node.nt.prefix)
            self.isa_nt_functionnames[node.nt.prefix] = functionname

            term = Var('term')
            fb = FunctionBuilder().with_name(functionname)      \
                                  .with_number_of_parameters(1) \
                                  .set_parameter(IsANtFunctionParameterIndex.Term, term)

            for pat in node.patterns:
                rbe = RetrieveBindableElements()
                rbe.transform(pat)
                lst = list(map(lambda x: x.sym,   rbe.bindables))

                self.transform(pat)
                functionname = self.processed_patterns[repr(pat)]
                match = fb.get_fresh_local('match')
                fb.add( Assign(match, NewMatch(set(lst))) )
                matches = fb.get_fresh_local('matches')
                fb.add( Assign(matches, Call(functionname, [term, match, ConstantInt(0), ConstantInt(1)])) ) 
                fb.add( ReturnTrueIfNotNull(matches) )

            fb.add( Return([ConstantBoolean(False)]) )
            self.modulebuilder.add_function(fb.build())


    def transformRepeat(self, node):
        assert isinstance(node, ast.Repeat)
        # FIXME this is incorrect, need match queue


        """
    matches = [ match ]
    extents = [ extent]

    matches_q = [ match ]
    extents_q = [ extent ]

    while len(matches_q) != 0:
        match = matches_q.pop(0)
        extent = extents_q.pop(0)

        e = extent.copy()
        m = match.copy()


        ms, es = match_exact_n(term, e, m)
        if ms != None:
            extents += es
            matches += ms
            matches_q += ms
            extents_q += es



        """

        # match.increasedepth(...)
        # matches.append(match)
        # match = match.copy()
        # while head < tail:
        #   tmp = match_term(term[head], match, head, tail)
        #   if tmp == None: 
        #     break 
        # else: 
        #   matches += tmp
        #   match = match.copy()
        # 
        # for m in matches:
        #   m.decreasedepth(...)

        

        if repr(node) in self.processed_patterns:
            return 

        functionname = 'match_term_{}'.format(self.symgen.get())
        self.processed_patterns[repr(node)] = functionname

        rbe = RetrieveBindableElements()
        rbe.transform(node.pat)

        term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')
        fb = FunctionBuilder().with_name(functionname)       \
                              .with_number_of_parameters(4)  \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Term, term) \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Match, match) \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Head, head) \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Tail, tail) 

        for bindable in rbe.bindables:
            fb.add(TermInvokeMethod(match, 'increasedepth', [ StringLiteral(bindable.sym) ]))
        matches, tmp = Var('matches'), Var('tmp')
        fb.add( Assign(matches, LitArray([MatchTuple(match, head, tail) ])))
        fb.add( Assign(match, TermInvokeMethod(match, 'copy')))

        self.transform(node.pat)
        functionname = self.processed_patterns[repr(node.pat)]

        fb.add( While( Binary(BinaryOp.Lt, head, tail), [
            Assign(tmp, Call(functionname, [TermInvokeMethod(term, 'get', [ head ]), match, head, tail ])),
            If( Binary(BinaryOp.EqEqual, tmp, Null), [
                Break()
                ], [
                ArrayConcat(matches, tmp), 
                Assign(match, TermInvokeMethod(match, 'copy')),
                Assign(head, Binary(BinaryOp.Add, head, ConstantInt(1))),
            ]),
        ]))

        m,h,t = Var('m'), Var('h'), Var('t')
        decrease = []
        for bindable in rbe.bindables:
            decrease.append( TermInvokeMethod(m, 'decreasedepth', [ StringLiteral(bindable.sym) ]) )
        fb.add( ForEach([m,h,t], matches, decrease))
        fb.add( Return( [ matches ] ) )

        self.modulebuilder.add_function(fb.build())
            

    def transformPatSequence(self, node):
        assert isinstance(node, ast.PatSequence)
        if repr(node) in self.processed_patterns:
            return 

        functionname = 'match_term_{}'.format(self.symgen.get())
        self.processed_patterns[repr(node)] = functionname

        term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')
        fb = FunctionBuilder().with_name(functionname)       \
                              .with_number_of_parameters(4)  \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Term, term) \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Match, match) \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Head, head) \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Tail, tail) 



        # ensure this is indeed datum.
        fb.add(If(Binary(BinaryOp.NotEqual, TermInvokeMethod(term, 'kind'), ConstantInt(TermKind.TermList)), [Return([Null])], None))

        # need to "enter" term (i.e. extract term at index head), 
        # set new subterm_head = 0 and subterm_tail = len(term[head])
        subterm, subhead, subtail = Var('subterm'), Var('subhead'), Var('subtail')
        fb.add(Assign(subhead, ConstantInt(0)))
        fb.add(Assign(subtail, TermInvokeMethod(term, 'length')))

        # ensure number of terms in the sequence is at least equal to number of non-repeated patterns. 
        # if num_required is zero, condition is always false.
        num_required = node.get_number_of_nonoptional_matches_between(0, len(node))
        if num_required != 0: 
            cond = Binary(BinaryOp.Sub, subtail, subhead)
            cond = Binary(BinaryOp.Lt, cond, ConstantInt(num_required))
            fb.add(If(cond, [ Return([Null]) ], None))

        

        def codegen_subpattern(pat, index, previous_matches):
            matches = fb.get_fresh_local('matches')
            if isinstance(pat, ast.Nt) or isinstance(pat, ast.BuiltInPat):
                isa_functionname = self.isa_nt_functionnames[pat.prefix]
                if index == 0:
                    # matches = []
                    # if isa_blah(term.get(subhead)):
                    #   match.addtobinding(..., term.get(subhead))
                    #   matches.append((match, subhead+1, subtail))
                    # if Len(matches) == 0: return None
                    fb.add(Assign(matches, LitArray([])))
                    cond = Binary(BinaryOp.EqEqual, Call(isa_functionname, [TermInvokeMethod(term, 'get', [subhead])]), ConstantBoolean(True))
                    thenbr = [
                        TermInvokeMethod(match, 'addtobinding', [ StringLiteral(pat.sym), TermInvokeMethod(term, 'get', [subhead]) ]) ,
                        ArrayAppend(matches, MatchTuple(match, Binary(BinaryOp.Add, subhead, ConstantInt(1)), subtail))
                    ]
                    fb.add(If(cond, thenbr, None))
                    fb.add(If(Binary(BinaryOp.EqEqual, LengthOfMatchList(matches), ConstantInt(0)), [
                        Return([Null])
                    ], None))
                else:
                    # matches = []
                    # for match, subhead, subtail in previous_matches:
                        # if isa_blah(term.get(subhead)):
                        #   match.addtobinding(..., term.get(subhead))
                        #   matches.append((match, subhead+1, subtail))
                    # if Len(matches) == 0: return None
                    m, h, t = Var('m'), Var('h'), Var('t')
                    fb.add(Assign(matches, LitArray([])))
                    fb.add(ForEach([m, h, t], previous_matches, [
                        If(Binary(BinaryOp.EqEqual, Call(isa_functionname, [TermInvokeMethod(term, 'get', [h])]), ConstantBoolean(True)),
                            [
                                TermInvokeMethod(match, 'addtobinding', [ StringLiteral(pat.sym), TermInvokeMethod(term, 'get', [h])]) ,
                                ArrayAppend(matches, MatchTuple(match, Binary(BinaryOp.Add, h, ConstantInt(1)), t))
                            ], None)
                    ]))
                    fb.add(If(Binary(BinaryOp.EqEqual, LengthOfMatchList(matches), ConstantInt(0)), [
                        Return([Null])
                    ], None))
                return matches


            elif isinstance(pat, ast.Repeat):
                
                self.transform(pat)
                functionname = self.processed_patterns[repr(pat)]

                if index == 0:
                    fb.add( Assign( matches, Call(functionname, [term, match, subhead, subtail])))
                else:
                    m, h, t = Var('m'), Var('h'), Var('t')
                    tmp = Var('tmp')

                    fb.add(Assign(matches, LitArray([])))
                    fb.add(ForEach([m, h, t], previous_matches, [
                        Assign(tmp, Call(functionname, [term, m, h, t])),
                        ArrayConcat(matches, tmp)
                    ]))

                return matches



            else:
                functionname = self.processed_patterns[repr(pat)]

                if index == 0:
                    # matches = match_func(term.get(subhead), match, subhead, subtail)
                    # if matches == None: return None
                    fb.add(Assign(matches, Call( functionname, [TermInvokeMethod(term, 'get', [subhead]), match, subhead, subtail])))
                    cond = Binary(BinaryOp.EqEqual, matches, Null)
                    thenbr = [ Return([Null]) ]
                    fb.add(If(cond,thenbr, None))
                else:
                    # have previous match array to work with. 
                    # matches = []
                    # for match, subhead, subtail in previous_matches:
                    #   matches += match_func(term.get(subhead), match, subhead, subtail)
                    # if len(matches) == 0:
                    #   return None
                    m, h, t = Var('m'), Var('h'), Var('t')
                    tmp = Var('tmp')
                    fb.add(Assign(matches, LitArray([])))
                    fb.add(ForEach([m, h, t], previous_matches, [
                        Assign(tmp, Call(functionname, [TermInvokeMethod(term, 'get', [h]), m, h, t])),
                        If( Binary(BinaryOp.NotEqual, tmp, Null), [
                        ArrayConcat(matches, tmp) ], None)
                    ]))
                    fb.add(If(Binary(BinaryOp.EqEqual, LengthOfMatchList(matches), ConstantInt(0)), [
                        Return([Null])
                    ], None))
                return matches

        previous_matches = None 
        for i, pat in enumerate(node.seq):
            self.transform(pat)
            previous_matches = codegen_subpattern(pat, i,previous_matches)


        # exit term 
        matches = fb.get_fresh_local('matches')
        m, h, t = Var('m'), Var('h'), Var('t')
        fb.add(Assign(matches, LitArray([])))
        fb.add(ForEach([m, h, t], previous_matches, [
            If( Binary(BinaryOp.EqEqual, h, t), [
                ArrayAppend(matches, MatchTuple(m, Binary(BinaryOp.Add, head, ConstantInt(1)), tail))
            ], None)
        ]))
        fb.add(If(Binary(BinaryOp.EqEqual, LengthOfMatchList(matches), ConstantInt(0)), [
            Return([Null])
        ], None))
        fb.add( Return([matches]) )

        self.modulebuilder.add_function(fb.build())


    def transformNt(self, nt):
        assert isinstance(nt, ast.Nt)
        term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')
        functionname = 'match_lang_{}_nt_{}'.format(self.definelanguage.name, nt.sym)
        self.processed_patterns[repr(nt)] = functionname
        fb = FunctionBuilder().with_name(functionname)      \
                              .with_number_of_parameters(4) \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Term, term)   \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Match, match) \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Head, head)   \
                              .set_parameter(DefineLanguagePatFunctionParameterIndex.Tail, tail)

        if nt.prefix not in self.isa_nt_functionnames:
            self.transform(self.definelanguage.nts[nt.prefix])

        isa_functionname = self.isa_nt_functionnames[nt.prefix]

        # call isa_nt(term) function,
        # if it returns True, call match.bind(nt.sym), increment head. 
        cond = Binary(BinaryOp.EqEqual, Call(isa_functionname, [term]), ConstantBoolean(True))
        thenbr = [
           TermInvokeMethod(match, 'addtobinding', [ StringLiteral(nt.sym), term ]) ,
           Return( [LitArray([MatchTuple(match, Binary(BinaryOp.Add, head, ConstantInt(1)), tail)])] )
        ]
        fb.add(If(cond, thenbr, None))
        fb.add(Return([Null]))
        self.modulebuilder.add_function(fb.build())

    def transformBuiltInPat(self, node):
        assert isinstance(node, ast.BuiltInPat)


        if node.kind == ast.BuiltInPatKind.Number:
            # also generate isa_ function for this 
            if node.prefix not in self.isa_nt_functionnames:
                functionname = 'lang_{}_isa_builtin_{}'.format(self.definelanguage.name, node.prefix)
                self.isa_nt_functionnames[node.prefix] = functionname

                term = Var('term')
                fb = FunctionBuilder().with_name(functionname)      \
                                      .with_number_of_parameters(1) \
                                      .set_parameter(IsANtFunctionParameterIndex.Term, term)
                cond = Binary(BinaryOp.EqEqual, TermInvokeMethod(term, 'kind'), ConstantInt(TermKind.Integer))
                thenbr = [ 
                    Return( [ConstantBoolean(True)] )
                ]

                fb.add(If(cond, thenbr, None))
                fb.add(Return([ConstantBoolean(False)]))
                self.modulebuilder.add_function(fb.build())



            functionname = 'match_lang_{}_builtin_{}'.format(self.definelanguage.name, self.symgen.get())
            self.processed_patterns[repr(node)] = functionname

            term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')
            fb = FunctionBuilder().with_name(functionname)      \
                                  .with_number_of_parameters(4) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Term, term)   \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Match, match) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Head, head)   \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Tail, tail)

            functionname = self.isa_nt_functionnames[node.prefix]
            cond = Binary(BinaryOp.EqEqual, Call(functionname, [ term ]), ConstantBoolean(True))
            thenbr = [ 
                TermInvokeMethod(match, 'addtobinding', [ StringLiteral(node.sym), term ]) ,
                Return( [LitArray([MatchTuple(match, Binary(BinaryOp.Add, head, ConstantInt(1)), tail)])] )
            ]
            fb.add(If(cond, thenbr, None))
            fb.add(Return([Null]))
            self.modulebuilder.add_function(fb.build())
            return node
        assert False, 'unreachable'

    def transformLit(self, node):
        assert isinstance(node, ast.Lit)

        if node.kind == ast.LitKind.Variable:
            functionname = 'lang_{}_consume_lit_{}'.format(self.definelanguage.name, self.symgen.get())
            self.processed_patterns[repr(node)] = functionname 

            term, match, head, tail = Var('term'), Var('match'), Var('head'), Var('tail')
            fb = FunctionBuilder().with_name(functionname)       \
                                  .with_number_of_parameters(4)  \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Term, term) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Match, match) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Head, head) \
                                  .set_parameter(DefineLanguagePatFunctionParameterIndex.Tail, tail) 


            cond1 = Binary(BinaryOp.EqEqual, TermInvokeMethod(term, 'kind'), ConstantInt(TermKind.Variable))
            cond2 = Binary(BinaryOp.EqEqual, TermInvokeMethod(term, 'value'), StringLiteral(node.lit))
            cond  = Binary(BinaryOp.And, cond1, cond2)
            thenbr = [ 
                Return( [LitArray([MatchTuple(match, Binary(BinaryOp.Add, head, ConstantInt(1)), tail)])] )
            ]
            fb.add(If(cond, thenbr, None))
            fb.add(Return([Null]))
            self.modulebuilder.add_comment(repr(node))
            self.modulebuilder.add_function(fb.build())
            return node
        assert False, 'unreachable'
