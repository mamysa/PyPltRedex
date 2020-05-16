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

class PyList(PyValue):
    def __init__(self, *initializer):
        self.initializer = list(initializer)

    def __infer_typeof_elements(self):
        pass

class PyTuple(PyValue):
    def __init__(self, *values):
        self.values = list(typ)


class BinaryOp(enum.Enum):
    Add = '+'
    Sub = '-'
    Eq    = '=='
    NotEq = '!='

# Few classes like IfStmt/WhileStmt start out with empty bodies and 
# statements have to be appended to them using +=.
# Calling End "freezes" the object and does not allow any further insertions.


class Module(PyAst):
    def __init__(self, statements):
        self.statements = statements

class SingleLineComment(PyAst):
    def __init__(self, comment):
        self.comment = comment

class Stmt(PyAst):
    pass

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

class Expr(PyAst):
    pass

class NewObject(Expr):
    def __init__(self,  typename, args):
        self.typename = typename
        self.args = args

class BinaryExpr(Expr):
    def __init__(self, op, lhs, rhs):
        assert isinstance(op, BinaryOp)
        assert isinstance(lhs, (PyValue, LenExpr))
        assert isinstance(rhs, PyValue)
        self.op = op
        self.lhs = lhs
        self.rhs = rhs

class IsTrueExpr(Expr):
    def __init__(self, value):
        assert isinstance(value, PyValue)
        self.value = value

class CallExpr(Expr):
    def __init__(self, name, args):
        self.name = name
        self.args = args 

class CallMethodExpr(Expr):
    def __init__(self, instance, name, args):
        self.instance = instance
        self.name = name
        self.args = args 


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


# ------------------------------------------------- 
# Helper functions that take strings and return tuple of PyId.
def gen_pyid_for(*syms):
    return tuple(map(lambda sym: PyId(sym), syms))

def gen_pyid_temporaries(qty, symgen):
    return tuple([PyId(symgen.get()) for i in range(qty)])



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

    def IncludeFromPythonSource(self, filename):
        self.statements.append(IncludePythonSourceStmt(filename))

    def SingleLineComment(self, comment):
        self.statements.append(SingleLineComment(comment))

    @property
    @ensure_not_previously_built
    def Return(self):
        class ReturnPhase1:
            def __init__(self, parent):
                self.parent = parent

            def PyList(self, *initializer):
                stmt = ReturnStmt(PyList(initializer))
                self.parent.statements.append(stmt) 

            def PyTuple(self, *initializer):
                stmt = ReturnStmt(PyTuple(initializer))
                self.parent.statements.append(stmt) 

            def PyBoolean(self, value):
                stmt = ReturnStmt(PyBoolean(value))
                self.parent.statements.append(stmt) 

            def Equal(self, lhs, rhs):
                stmt = ReturnStmt(BinaryExpr(BinaryOp.Eq, lhs, rhs))
                self.parent.statements.append(stmt) 

            def PyId(self, ident):
                stmt = ReturnStmt(PyId(ident))
                self.parent.statements.append(stmt) 

        return ReturnPhase1(parent=self)



    @ensure_not_previously_built
    def AssignTo(self, *args):
        class AssignToPhase1:
            def __init__(self, args, parent):
                self.args = args 
                self.parent = parent

            def MethodCall(self, instance, methodname, *args):
                self.parent.statements.append( CallMethodExpr(instance, name, list(args)) )

            def FunctionCall(self, name, *args):
                self.parent.statements.append( CallExpr(name, list(args)) )

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
                stmt = AssignStmt(self.args, PyList(initializer))
                self.parent.statements.append(stmt) 

            def PyTuple(self, *initializer):
                stmt = AssignStmt(self.args, PyTuple(initializer))
                self.parent.statements.append(stmt) 

            def New(self, typename, *args):
                stmt = AssignStmt(self.args, NewExpr(typename, list(args)))
                self.parent.statements.append(stmt) 


        return AssignToPhase1(list(args), parent=self)

    @ensure_not_previously_built
    def Function(self, name):
        return FunctionBuilderStage1(self.sourcebuilder, name, self.statements)

    def MethodCall(self, instance, methodname, *args):
        self.statements.append( CallMethodExpr(instance, name, list(args)) )

    def FunctionCall(self, name, *args):
        self.statements.append( CallExpr(name, list(args)) )

    @property
    @ensure_not_previously_built
    def If(self):
        return IfOrWhileBuilderPreStage1(IfOrWhileBuilderPreStage1.IfBuilderPreStage4, self.statements)

    @property
    @ensure_not_previously_built
    def While(self):
        return IfOrWhileBuilderPreStage1(IfOrWhileBuilderPreStage1.WhileBuilderPreStage4, self.statements)

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
                self.name = name 
                self.parameters = parameters 
                self.statements = statements

            def Block(self, blockbuilder):
                assert isinstance(blockbuilder, BlockBuilder)
                stmt = FunctionStmt(self.name, list(parameters), blockbuilder.build())
                self.statements.append(stmt)

        return FunctionBuilderStage2(self.sourcebuilder, self.name, list(parameters), self.statements)
    


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

    def Equal(self, lhs, rhs):
        return self.lastprestage(BinaryExpr(BinaryOp.Eq, lhs, rhs), self.statements)

    def NotContains(self, value):
        class IfOrWhileBuilderPreStage3:
            def __init__(self, value, lastprestage, statements):
                self.value = value
                self.lastprestage = lastprestage
                self.statements = statements

            def In(self, iterable):
                return self.lastprestage(InExpr(value, iterable), self.statements)

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

    def visitAssignStmt(self, stmt):
        assert isinstance(stmt, AssignStmt)
        self.emit_indentstring()
        self.emit_comma_separated_list(stmt.names) 
        self.emit_space()
        self.emit('=')
        self.emit_space()
        self.visit(stmt.expr)
        self.emit_newline()

    

    def visitBinaryExpr(self, expr):
        assert isinstance(expr, BinaryExpr)
        self.visit(expr.lhs)
        self.emit_space()
        self.emit(expr.op.value)
        self.emit_space()
        self.visit(expr.rhs)

    def visitPyId(self, ident):
        assert isinstance(ident, PyId)
        self.emit(ident.name)

    def visitPyInt(self, pyint):
        assert isinstance(pyint, PyInt)
        self.emit(str(pyint.value))
