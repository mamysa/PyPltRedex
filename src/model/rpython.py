import enum
#from src.symgen import SymGen

# Classes representing Python abstract syntax tree. 
# Complex nested expressions are not allowed and something similar to 
# 'Three-adress-code' is used instead - instances of PyValue class are operands.
# AST is not meant to be created directly (it's very tedious) and fluent interfaces to 
# create them are provided below. 
# Some AST elements are specialized and combine multiple functionalities into one. 
# For an example, see ForEachInRange (prettyprinting it would result in 'for ... in range(...)')

# PyValue represents variables, literal arrays, tuples and other goodies.
class PyAst:
    pass 

class  PyValue(PyAst):
    def typeof(self):
        raise Exception('unimplemented')

class PyNone(PyValue): 
    pass

class PyVarArg(PyValue):
    def __init__(self, name):
        assert isinstance(name, str)
        self.name = name 

class PyId(PyValue):
    def __init__(self, name):
        assert isinstance(name, str)
        self.name = name 

    def __repr__(self):
        return 'PyId({})'.format(self.name)

class PyInt(PyValue):
    def __init__(self, value):
        assert isinstance(value, int)
        self.value = value

class PyFloat(PyValue):
    def __init__(self, value):
        assert isinstance(value, float)
        self.value = value

class PyBoolean(PyValue):
    def __init__(self, value):
        assert isinstance(value, bool)
        self.value = value

class PyString(PyValue):
    def __init__(self, value):
        assert isinstance(value, str)
        self.value = value

class PySet(PyValue):
    def __init__(self, *initializer):
        self.initializer = list(initializer)

class PyList(PyValue):
    def __init__(self, *initializer):
        self.initializer = list(initializer)

class PyTuple(PyValue):
    def __init__(self, *values):
        self.values = list(values)


class BinaryOp(enum.Enum):
    Add = '+'
    Sub = '-'
    Eq    = '=='
    NotEq = '!='
    GrEq = '>='
    Lt   = '<'

# Few classes like IfStmt/WhileStmt start out with empty bodies and 
# statements have to be appended to them using +=.
# Calling End "freezes" the object and does not allow any further insertions.

class Module(PyAst):
    def __init__(self, statements):
        self.statements = statements

class Stmt(PyAst):
    pass

class SingleLineComment(Stmt):
    def __init__(self, comment):
        self.comment = comment

class IncludePythonSourceStmt(Stmt):
    def __init__(self, filename):
        self.filename = filename

class FunctionStmt(Stmt):
    def __init__(self, name, parameters, body):
        assert isinstance(name, str)
        self.name = name
        self.parameters = parameters 
        self.body = body 


class AssignStmt(Stmt):
    def __init__(self, names, expr):
        assert [isinstance(n, PyId) for n in names]
        self.names = names
        self.expr  = expr

class ReturnStmt(Stmt):
    def __init__(self, expr):
        self.expr = expr

class ForEachStmt(Stmt):
    def __init__(self, variables, iterable, body):
        self.variables = variables
        self.iterable = iterable
        self.body = body

class ForEachInRangeStmt(Stmt):
    def __init__(self, variables, _range, body):
        self.variables = variables
        self.range = _range 
        self.body = body

class WhileStmt(Stmt):
    def __init__(self, cond, body):
        self.cond = cond 
        self.body = body 

class IfStmt(Stmt):
    def __init__(self, cond, thenbr, elsebr):
        self.cond = cond 
        self.thenbr = thenbr
        self.elsebr = elsebr 

class ContinueStmt(Stmt):
    pass

class BreakStmt(Stmt):
    pass

class PrintStmt(Stmt):
    def __init__(self, value):
        self.value = value 

class RaiseExceptionStmt(Stmt):
    def __init__(self, message, formatelems):
        assert isinstance(message, str)
        self.message = message
        self.formatelems = formatelems

class Expr(PyAst):
    pass

class BinaryExpr(Expr):
    def __init__(self, op, lhs, rhs):
        assert isinstance(op, BinaryOp)
        assert isinstance(lhs, (PyValue, LenExpr))
        assert isinstance(rhs, PyValue)
        self.op = op
        self.lhs = lhs
        self.rhs = rhs

class CallExpr(Expr):
    def __init__(self, name, args):
        assert isinstance(name, str)
        self.name = name
        self.args = args 

class CallMethodExpr(Expr):
    def __init__(self, instance, name, args):
        assert isinstance(instance, PyId)
        self.instance = instance
        self.name = name
        self.args = args 

class ArrayGetExpr(Expr):
    def __init__(self, array, index):
        assert isinstance(array, PyId)
        assert isinstance(array, (PyId, PyInt))
        self.array = array
        self.index = index

class NewExpr(Expr):
    def __init__(self, typename, args):
        self.typename = typename 
        self.args = args

class InExpr(Expr):
    def __init__(self, lhs, rhs, neg=False):
        self.lhs = lhs
        self.rhs = rhs
        self.neg = neg

class LenExpr(Expr):
    def __init__(self, value):
        assert isinstance(value, PyValue)
        self.value = value 

class IsInstanceExpr(Expr):
    def __init__(self, var, classname, neg=False):
        assert isinstance(var, PyId)
        self.var = var
        self.classname = classname
        self.neg = neg


# ------------------------------------------------- 
# Helper functions that take strings and return tuple of PyId.
def gen_pyid_for(*syms):
    if len(syms) > 1:
        return tuple(map(lambda sym: PyId(sym), syms))
    return PyId(syms[0])

def gen_pyid_temporaries(qty, symgen):
    if qty > 1:
        return tuple([PyId(symgen.get()) for i in range(qty)])
    return PyId(symgen.get())

def gen_pyid_temporary_with_sym(sym, symgen):
    return PyId(symgen.get(sym))

# ------------------------------------------------------------
# RPython AST creation helpers. Instead of directly instantiating classes above to create statements, 
# we use fluent interfaces to constrain kinds of expressions that could be created otherwise (i.e. to enforce 
# three-address-code style).
# 
# Instead of writing AssignStmt([x,y,z], BinaryExpr(BinaryOperator.Add, x, y))  (which is very tedious!) one would write
# Statement.AssignTo(x, y, z).Add(x, y) instead.
def ensure_not_previously_built(func):
    def wrapper(*args):
        assert isinstance(args[0], BlockBuilder)
        if args[0]._frozen:
            raise Exception('modifying already built block')
        return func(*args)
    return wrapper

class BlockBuilder:
    def __init__(self):
        self.statements = []
        self._frozen = False

    @ensure_not_previously_built
    def build(self):
        self._frozen = True
        return self.statements

    @ensure_not_previously_built
    def IncludeFromPythonSource(self, filename):
        self.statements.append(IncludePythonSourceStmt(filename))

    @ensure_not_previously_built
    def SingleLineComment(self, comment):
        self.statements.append(SingleLineComment(comment))

    def RaiseException(self, message, *args):
        self.statements.append(RaiseExceptionStmt(message, list(args)))

    @ensure_not_previously_built
    def Return(self, value):
        assert isinstance(value, PyValue)
        stmt = ReturnStmt(value)
        self.statements.append(stmt) 

    @ensure_not_previously_built
    def AssignTo(self, *args):
        class AssignToPhase1:
            def __init__(self, args, parent):
                self.args = args 
                self.parent = parent

            def MethodCall(self, instance, methodname, *args):
                expr = CallMethodExpr(instance, methodname, list(args)) 
                stmt = AssignStmt(self.args, expr)
                self.parent.statements.append(stmt)

            def FunctionCall(self, name, *args):
                expr = CallExpr(name, list(args)) 
                stmt = AssignStmt(self.args, expr)
                self.parent.statements.append(stmt)

            def Add(self, lhs, rhs):
                stmt = AssignStmt(self.args, BinaryExpr(BinaryOp.Add, lhs, rhs))
                self.parent.statements.append(stmt) 

            def Subtract(self, lhs, rhs):
                stmt = AssignStmt(self.args, BinaryExpr(BinaryOp.Sub, lhs, rhs))
                self.parent.statements.append(stmt) 

            def PyInt(self, value):
                stmt = AssignStmt(self.args, PyInt(value))
                self.parent.statements.append(stmt) 

            def PyList(self, *initializer):
                stmt = AssignStmt(self.args, PyList(*initializer))
                self.parent.statements.append(stmt) 

            def PySet(self, *initializer):
                stmt = AssignStmt(self.args, PySet(*initializer))
                self.parent.statements.append(stmt) 

            def PyTuple(self, *initializer):
                stmt = AssignStmt(self.args, PyTuple(*initializer))
                self.parent.statements.append(stmt) 

            def PyId(self, ident):
                stmt = AssignStmt(self.args, ident)
                self.parent.statements.append(stmt) 



            def New(self, typename, *args):
                stmt = AssignStmt(self.args, NewExpr(typename, list(args)))
                self.parent.statements.append(stmt) 

            def ArrayGet(self, array, index):
                stmt = AssignStmt(self.args, ArrayGetExpr(array, index))
                self.parent.statements.append(stmt) 


        return AssignToPhase1(list(args), parent=self)

    @ensure_not_previously_built
    def Function(self, name):
        return FunctionBuilderStage1(name, self.statements)

    @property
    @ensure_not_previously_built
    def If(self):
        return IfOrWhileBuilderPreStage1(IfOrWhileBuilderPreStage1.IfBuilderPreStage4, self.statements)

    @property
    @ensure_not_previously_built
    def While(self):
        return IfOrWhileBuilderPreStage1(IfOrWhileBuilderPreStage1.WhileBuilderPreStage4, self.statements)

    @property
    @ensure_not_previously_built
    def Continue(self):
        self.statements.append( ContinueStmt() )


    @property
    @ensure_not_previously_built
    def Break(self):
        self.statements.append( BreakStmt() )

    @ensure_not_previously_built
    def Print(self, value):
        self.statements.append( PrintStmt(value) )

    @ensure_not_previously_built
    def For(self, *iteratorvariables):
        class ForPrePhase1:
            class ForPrePhase2:
                def __init__(self, iteratorvariables, iterable, statements, inrange=False):
                    self.iteratorvariables = iteratorvariables 
                    self.iterable = iterable
                    self.statements = statements
                    self.inrange = inrange

                def Block(self, blockbuilder):
                    assert isinstance(blockbuilder, BlockBuilder)
                    block = blockbuilder.build()
                    if self.inrange:
                        stmt = ForEachInRangeStmt(self.iteratorvariables, self.iterable, block)
                    else:
                        stmt = ForEachStmt(self.iteratorvariables, self.iterable, block)

                    self.statements.append(stmt)



            def __init__(self, iteratorvariables, statements):
                self.iteratorvariables = iteratorvariables
                self.statements = statements

            def In(self, iterable):
                return self.ForPrePhase2(self.iteratorvariables, iterable, self.statements)

            def InRange(self, _range):
                return self.ForPrePhase2(self.iteratorvariables, _range, self.statements, inrange=True)

        return ForPrePhase1( list(iteratorvariables), self.statements)

class FunctionBuilderStage1:
    def __init__(self, name, statements):
        self.name = name
        self.statements = statements 

    def Block(self, blockbuilder):
        assert isinstance(blockbuilder, BlockBuilder)
        stmt = FunctionStmt(self.name, [], blockbuilder.build())
        self.statements.append(stmt)

    def WithParameters(self, *parameters):
        class FunctionBuilderStage2:
            def __init__(self, name, parameters, statements):
                for p in parameters:
                    assert isinstance(p, (PyId, PyVarArg))
                self.name = name 
                self.parameters = parameters 
                self.statements = statements

            def Block(self, blockbuilder):
                assert isinstance(blockbuilder, BlockBuilder)
                stmt = FunctionStmt(self.name, list(parameters), blockbuilder.build())
                self.statements.append(stmt)

        return FunctionBuilderStage2(self.name, list(parameters), self.statements)

# If/While statements use same condition writing logic. The only bit that differs is that 
# for While statements we need to write Begin() and for If we need to write Then().
# Pass classes around for that.
class IfOrWhileBuilderPreStage1:
    class IfBuilderPreStage4:
        def __init__(self, cond, statements):
            self.cond = cond
            self.statements = statements 

        def ThenBlock(self, blockbuilder):
            assert isinstance(blockbuilder, BlockBuilder)
            stmt = IfStmt(self.cond, blockbuilder.build(), None)
            self.statements.append(stmt)

    class WhileBuilderPreStage4:
        def __init__(self, cond, statements):
            self.cond = cond
            self.statements = statements 

        def Block(self, blockbuilder):
            assert isinstance(blockbuilder, BlockBuilder)
            stmt = WhileStmt(self.cond, blockbuilder.build())
            self.statements.append(stmt)


    def __init__(self, lastprestage, statements):
        self.lastprestage = lastprestage 
        self.statements = statements 

    def IsInstance(self, var, classname):
        return self.lastprestage(IsInstanceExpr(var, classname), self.statements)

    def NotIsInstance(self, var, classname):
        return self.lastprestage(IsInstanceExpr(var, classname, neg=True), self.statements)

    def Equal(self, lhs, rhs):
        return self.lastprestage(BinaryExpr(BinaryOp.Eq, lhs, rhs), self.statements)

    def LessThan(self, lhs, rhs):
        return self.lastprestage(BinaryExpr(BinaryOp.Lt, lhs, rhs), self.statements)

    def GreaterEqual(self, lhs, rhs):
        return self.lastprestage(BinaryExpr(BinaryOp.GrEq, lhs, rhs), self.statements)

    def NotContains(self, value):
        class IfOrWhileBuilderPreStage3:
            def __init__(self, value, lastprestage, statements):
                self.value = value
                self.lastprestage = lastprestage
                self.statements = statements

            def In(self, iterable):
                return self.lastprestage(InExpr(value, iterable, neg=True), self.statements)

        return IfOrWhileBuilderPreStage3(value, self.lastprestage, self.statements)

    def NotEqual(self, lhs, rhs):
        return self.lastprestage(BinaryExpr(BinaryOp.NotEq, lhs, rhs), self.statements)

    def LengthOf(self, item):
        class IfBuilderPreStage2:
            def __init__(self, lastprestage, iterable, statements):
                self.lastprestage = lastprestage 
                self.lengthof = LenExpr(iterable)
                self.statements = statements
            
            def Equal(self, value):
                return self.lastprestage( BinaryExpr(BinaryOp.Eq, self.lengthof, value), self.statements )

            def NotEqual(self, value):
                return self.lastprestage( BinaryExpr(BinaryOp.NotEq, self.lengthof, value), self.statements )

        return IfBuilderPreStage2(self.lastprestage, item, self.statements)

# Rpython Dump
class RPythonWriter:
    def __init__(self):
        self.indents = 0
        self.buf = []
        self.indentstr = ''

    def write(self, module):
        self.visit(module)
        return ''.join(self.buf)

    def _indent(self):
        self.indents += 1
        self.indentstr = ' '*self.indents*4
        return self

    def _dedent(self):
        self.indents -= 1
        self.indentstr = ' '*self.indents*4
        assert self.indents >= 0
        return self

    def emit(self, string):
        assert isinstance(string, str)
        self.buf.append(string)

    def emit_space(self):
        self.buf.append(' ')

    def emit_indentstring(self):
        self.buf.append(self.indentstr)

    def emit_comma_separated_list(self, lst):
        if len(lst) > 0:
            for element in lst[:-1]:
                self.visit(element)
                self.buf.append(', ')
            self.visit(lst[-1])

    def emit_newline(self):
        self.buf.append('\n')

    def visit(self, element):
        assert isinstance(element, PyAst)
        method_name = 'visit' + element.__class__.__name__
        method_ref = getattr(self, method_name)
        return method_ref(element)

    def visitModule(self, module):
        assert isinstance(module, Module)
        for stmt in module.statements:
            self.visit(stmt)

    def visitSingleLineComment(self, comment):
        self.emit('#')
        self.emit(comment.comment)
        self.emit_newline()

    def visitIncludePythonSourceStmt(self, stmt):
        assert isinstance(stmt, IncludePythonSourceStmt)

        self.emit('###------------------------------')
        self.emit_newline()
        self.emit('### Contents of {}'.format(stmt.filename))
        self.emit_newline()
        self.emit('###------------------------------')
        self.emit_newline()
        f = open(stmt.filename, 'r')
        self.emit( f.read() )
        self.emit_newline()
        f.close()

    def visitFunctionStmt(self, stmt):
        assert isinstance(stmt, FunctionStmt)
        self.emit_indentstring()
        self.emit('def')
        self.emit_space()
        self.emit(stmt.name)
        self.emit('(')
        self.emit_comma_separated_list(stmt.parameters)
        self.emit(')')
        self.emit(':')
        self.emit_newline()
        self._indent()
        for s in stmt.body:
            self.visit(s)
        self._dedent()
        self.emit_newline()

    def visitAssignStmt(self, stmt):
        assert isinstance(stmt, AssignStmt)
        self.emit_indentstring()
        self.emit_comma_separated_list(stmt.names) 
        self.emit_space()
        self.emit('=')
        self.emit_space()
        self.visit(stmt.expr)
        self.emit_newline()

    def visitReturnStmt(self, stmt):
        self.emit_indentstring()
        self.emit('return')
        self.emit_space()
        self.visit(stmt.expr)
        self.emit_newline()

    def visitForEachStmt(self, stmt):
        assert isinstance(stmt, ForEachStmt)
        self.emit_indentstring()
        self.emit('for')
        self.emit_space()
        self.emit_comma_separated_list(stmt.variables)
        self.emit_space()
        self.emit('in')
        self.emit_space()
        self.visit(stmt.iterable)
        self.emit(':')
        self.emit_newline()
        self._indent()
        for s in stmt.body:
            self.visit(s)
        self._dedent()

    def visitForEachInRangeStmt(self, stmt):
        assert isinstance(stmt, ForEachInRangeStmt)
        self.emit_indentstring()
        self.emit('for')
        self.emit_space()
        self.emit_comma_separated_list(stmt.variables)
        self.emit_space()
        self.emit('in')
        self.emit_space()
        self.emit('range(')
        self.visit(stmt.range)
        self.emit(')')
        self.emit(':')
        self.emit_newline()
        self._indent()
        for s in stmt.body:
            self.visit(s)
        self._dedent()

    def visitWhileStmt(self, stmt):
        assert isinstance(stmt, WhileStmt)
        self.emit_indentstring()
        self.emit('while')
        self.emit_space()
        self.visit(stmt.cond)
        self.emit(':')
        self.emit_newline()

        self._indent()
        for s in stmt.body:
            self.visit(s)
        self._dedent()

    def visitIfStmt(self, stmt):
        assert isinstance(stmt, IfStmt)
        self.emit_indentstring()
        self.emit('if')
        self.emit_space()
        self.visit(stmt.cond)
        self.emit(':')
        self.emit_newline()

        self._indent()
        for s in stmt.thenbr:
            self.visit(s)
        self._dedent()
        
        if stmt.elsebr != None:
            self.emit_indentstring()
            self.emit('else:')
            self.emit_newline()
            self._indent()
            for s in stmt.elsebr:
                self.visit(s)
            self._dedent()

    def visitContinueStmt(self, stmt):
        self.emit_indentstring()
        self.emit('continue')
        self.emit_newline()

    def visitBreakStmt(self, stmt):
        self.emit_indentstring()
        self.emit('break')
        self.emit_newline()

    def visitPrintStmt(self, stmt):
        assert isinstance(stmt, PrintStmt)
        self.emit_indentstring()
        self.emit('print')
        self.emit('(')
        self.visit(stmt.value)
        self.emit(')')
        self.emit_newline()

    def visitRaiseExceptionStmt(self, stmt):
        assert isinstance(stmt, RaiseExceptionStmt)
        self.emit_indentstring()
        self.emit('raise')
        self.emit_space()
        self.emit('Exception(')
        self.emit('"')
        self.emit(stmt.message)
        self.emit('"')
        if len(stmt.formatelems) != 0:
            self.emit_space()
            self.emit('%')
            self.emit_space()
            # tuple
            self.emit('(')
            self.emit_comma_separated_list(stmt.formatelems)
            self.emit(',')
            self.emit(')')
        self.emit(')')
        self.emit_newline()

    def visitBinaryExpr(self, expr):
        assert isinstance(expr, BinaryExpr)
        self.visit(expr.lhs)
        self.emit_space()
        self.emit(expr.op.value)
        self.emit_space()
        self.visit(expr.rhs)

    def visitCallExpr(self, expr):
        self.emit(expr.name)
        self.emit('(')
        self.emit_comma_separated_list(expr.args)
        self.emit(')')

    def visitCallMethodExpr(self, expr):
        self.visit(expr.instance)
        self.emit('.')
        self.emit(expr.name)
        self.emit('(')
        self.emit_comma_separated_list(expr.args)
        self.emit(')')

    def visitNewExpr(self, expr):
        self.emit(expr.typename)
        self.emit('(')
        self.emit_comma_separated_list(expr.args)
        self.emit(')')

    def visitInExpr(self, expr):
        self.visit(expr.lhs)
        self.emit_space()
        if expr.neg:
            self.emit('not')
            self.emit_space()
        self.emit('in')
        self.emit_space()
        self.visit(expr.rhs)

    def visitLenExpr(self, expr):
        assert isinstance(expr, LenExpr)
        self.emit('len')
        self.emit('(')
        self.visit(expr.value)
        self.emit(')')

    def visitIsInstanceExpr(self, expr):
        assert isinstance(expr, IsInstanceExpr)
        if expr.neg:
            self.emit('not ')
        self.emit('isinstance')
        self.emit('(')
        self.visit(expr.var)
        self.emit(', ')
        self.emit(expr.classname)
        self.emit(')')

    def visitArrayGetExpr(self, expr):
        assert isinstance(expr, ArrayGetExpr)
        self.visit(expr.array)
        self.emit('[')
        self.visit(expr.index)
        self.emit(']')

    def visitPyId(self, ident):
        assert isinstance(ident, PyId)
        self.emit(ident.name)

    def visitPyVarArg(self, ident):
        assert isinstance(ident, PyVarArg)
        self.emit('*')
        self.emit(ident.name)
    
    def visitPyInt(self, pyint):
        assert isinstance(pyint, PyInt)
        self.emit(str(pyint.value))

    def visitPyFloat(self, pyfloat):
        self.emit(str(pyfloat.value))

    def visitPyBoolean(self, pybool):
        assert isinstance(pybool, PyBoolean)
        self.emit(str(pybool.value))

    def visitPyString(self, pystr):
        assert isinstance(pystr, PyString)
        self.emit('\'')
        self.emit(pystr.value)
        self.emit('\'')

    def visitPySet(self, pyset):
        assert isinstance(pyset, PySet)
        self.emit('{')
        for elem in pyset.initializer:
            self.visit(elem)
            self.emit(': None')
            self.emit(',')
        self.emit('}')

    def visitPyList(self, pylist):
        assert isinstance(pylist, PyList)
        self.emit('[')
        self.emit_comma_separated_list(list(pylist.initializer))
        self.emit(']')

    def visitPyTuple(self, pytuple):
        assert isinstance(pytuple, PyTuple)
        self.emit('(')
        self.emit_comma_separated_list(pytuple.values)
        self.emit(',')
        self.emit(')')

    def visitPyNone(self, pynone):
        self.emit('None')
