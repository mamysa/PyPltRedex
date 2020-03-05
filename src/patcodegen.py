import src.astdefs as ast
import enum


class Function:
    def __init__(self, name, parameters, body):
        self.name = name
        self.parameters = parameters
        self.body = body 

    def get_parameter_at_position(self, key):
        return self.parameters[key]

    def add(self, stmt):
        self.body.append(stmt)


class Call:
    def __init__(self, returnvalues, name, arguments):
        self.name = name
        self.arguments = arguments
        self.returnvalues = returnvalues

class Var:
    def __init__(self, name):
        self.name = name

class ConstantInt:
    def __init__(self, constant):
        self.constant = constant

class Return:
    def __init__(self, returnvalues):
        self.returnvalues = returnvalues 

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


class ConstantBoolean:
    def __init__(self, value):
        self.value = value

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
            self.buf.append('\t'*self.indents)
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

    def writeCall(self, stmt):
        assert isinstance(stmt, Call)

        self.comma_separated_list(stmt.returnvalues)
        self.emit(' = ')
        self.emit(stmt.name)
        self.emit('(')
        self.comma_separated_list(stmt.arguments)
        self.emit(')')

    def writeReturn(self, stmt):
        self.emit('return ')
        self.comma_separated_list(stmt.returnvalues)

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
    Head = 1
    Tail = 2


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
        self.processed = {}  # map of repr(pat) -> function-name
        self.symgen = SymGen() 
        self.functions = []

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
            self.functions.append(fb.build())

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

        #fb.add(Assign(subterm, TermGetField(term, 'get({})'.format(head))))
        fb.add(Assign(subhead, ConstantInt(0)))
        fb.add(Assign(subtail, TermInvokeMethod(term, 'sequence_length')))
        
        for pat in node.seq:
            self.transform(pat)
            patfunctionname = self.processed[repr(pat)]
            subresult, nsubhead, nsubtail = fb.get_fresh_local('subresult'), fb.get_fresh_local('subhead'), fb.get_fresh_local('subtail')

            if isinstance(pat, ast.Repeat):
                fb.add(Call([subresult, nsubhead, nsubtail], patfunctionname, [term, subhead, subtail]))
            else:
                fb.add(Call([subresult, nsubhead, nsubtail], patfunctionname, [TermInvokeMethod(term, 'get', [subhead]), subhead, subtail]))
                fb.add(If(Binary(BinaryOp.NotEqual, subresult, ConstantBoolean(True)), [Return([ConstantBoolean(False), head, tail])], None))
            subhead, subtail = nsubhead, nsubtail 

        # ensure the end of the term has been reached.
        fb.add(If(Binary(BinaryOp.NotEqual, nsubhead, nsubtail), [Return([ConstantBoolean(False), head, tail])], None))

        # need to "leave" term 
        fb.add(Assign(head, Binary(BinaryOp.Add, head, ConstantInt(1))))
        fb.add(Return([ConstantBoolean(True), head, tail]))


        self.functions.append(fb.build())


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
            self.functions.append(fb.build())
            return node

            

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
                Call([match, head, tail], patfunctionname, [term, head, tail]),
                If(Binary(BinaryOp.NotEqual, match, ConstantBoolean(True)), [
                    Return([ConstantBoolean(True), head, tail])
                ], None)
            ])
            fb.add(loop)
            fb.add(Return([ConstantBoolean(True), head, tail]))
            self.functions.append(fb.build())

