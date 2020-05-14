import enum

# Classes representing Python abstract syntax tree. 
# Complex nested expressions are not allowed and something similar to 
# 'Three-adress-code' is used instead - instances of PyValue class are operands.
# AST is not meant to be created directly (it's very tedious) and fluent interfaces to 
# create them are provided below. 
# Some AST elements are specialized and combine multiple functionalities into one. 
# For an example, see ForEachInRange (prettyprinting it would result in 'for ... in range(...)')

# PyValue represents variables, literal arrays, tuples and other goodies.
class  PyValue:
    def typeof(self):
        raise Exception('unimplemented')

class PyId(PyValue):
    def __init__(self, name):
        assert isinstance(name, str)
        self.name = name 

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
class Module:
    def __init__(self, statements):
        self.statements = statements

class Stmt:
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

class ForEachStmt(Stmt):
    def __init__(self, variables, iterable):
        self.variables = variables
        self.iterable = iterable

    def __iadd__(self, stmt):
        assert isinstance(stmt, Stmt)
        self.stmt.append(stmt)
        return self

    def End(self):
        assert self.body != None
        assert len(self.body) != 0

class ForEachInRangeStmt(Stmt):
    def __init__(self, variables, _range):
        self.variables = variables
        self.range = _range 
        self.body = []

    def __iadd__(self, stmt):
        assert isinstance(stmt, Stmt)
        self.stmt.append(stmt)
        return self

    def End(self):
        assert self.body != None
        assert len(self.body) != 0

class WhileStmt:
    def __init__(self, cond, body):
        self.cond = cond 
        self.body = body 

class IfStmt:
    def __init__(self, cond, thenbr, elsebr):
        self.cond = cond 
        self.thenbr = thenbr
        self.elsebr = elsebr 

class Expr:
    pass

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

class NewExpr(Expr):
    def __init__(self, typename, args):
        self.typename = typename 
        self.args = args


class LenExpr(Expr):
    def __init__(self, value):
        assert isinstance(value, PyValue)
        self.value = value 

# ------------------------------------------------------------
# RPython AST creation helpers. Instead of directly instantiating classes above to create statements, 
# we use fluent interfaces to constrain kinds of expressions that could be created otherwise (i.e. to enforce 
# three-address-code style).
# 
# Instead of writing AssignStmt([x,y,z], BinaryExpr(BinaryOperator.Add, x, y))  (which is very tedious!) one would write
# Statement.AssignTo(x, y, z).Add(x, y) instead.

def ensure_no_active_nested_builders(func):
    def wrapper(*args):
        assert isinstance(args[0], BlockBuilder)
        if args[0].building_nested_block:
            raise Exception('unable to add statement while building nested block')
        return func(*args)
    return wrapper


def ensure_not_previously_built(func):
    def wrapper(*args):
        assert isinstance(args[0], BlockBuilder)
        if args[0]._frozen:
            raise Exception('modifying already built block')
        return func(*args)
    return wrapper

class BlockBuilder:
    def __init__(self, parent=None):
        self.parent = parent
        self.building_nested_block = False
        self.statements = []
        self._frozen = False

    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def IncludeFromPythonSource(self, filename):
        self.statements.append(IncludePythonSourceStmt(filename))

    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def AssignTo(self, *args):
        class AssignToPhase1:
            def __init__(self, args, parent):
                self.args = args 
                self.parent = parent

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

        return AssignToPhase1(list(args), parent=self)

    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def Function(self, name):
        self.building_nested_block = True
        return FunctionBuilderStage1(name, parent=self)

    @property
    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def If(self):
        self.building_nested_block = True
        return IfOrWhileBuilderPreStage1(IfOrWhileBuilderPreStage1.IfBuilderPreStage3, parent=self)

    @property
    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def While(self):
        self.building_nested_block = True
        return IfOrWhileBuilderPreStage1(IfOrWhileBuilderPreStage1.WhileBuilderPreStage3, parent=self)

    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def For(self, *iteratorvariables):
        class ForPrePhase1:
            class ForPrePhase2:
                def __init__(self, iteratorvariables, iterable, parent, inrange=False):
                    self.iteratorvariables = iteratorvariables 
                    self.iterable = iterable
                    self.inrange = inrange
                    self.parent = parent

                def Begin(self):
                    return ForBuilder(self.iteratorvariables, self.iterable, inrange=True, parent=self.parent)

            def __init__(self, iteratorvariables, parent):
                self.iteratorvariables = iteratorvariables
                self.parent = parent

            def In(self, iterable):
                return self.ForPrePhase2(self.iteratorvariables, iterable, parent=self.parent)

            def InRange(self, _range):
                return self.ForPrePhase2(self.iteratorvariables, _range, parent=self.parent, inrange=True)

        self.building_nested_block = True
        return ForPrePhase1( list(iteratorvariables), parent=self )

    @property
    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def Call(self):
        class CallPrePhase1:
            def __init__(self, parent):
                self.parent = parent

            def WithArguments(self, *args):
                class CallPrePhase2:
                    def __init__(self, args, parent):
                        self.args = args
                        self.parent = parent

                    def Function(self, name):
                        self.parent.statements.append( CallExpr(name, self.args) )
                
                return CallPrePhase2( list(args), self.parent )

            def Function(self, name):
                self.parent.statements.append( CallExpr(name, []) )

        return CallPrePhase1(parent=self)

    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def End(self):
        raise Exception('Unable to build generic block.')

    def _appendnested(self, obj):
        assert self.building_nested_block 
        self.statements.append(obj)
        self.building_nested_block = False 

class FunctionBuilderStage1:
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent

    def WithParameters(self, *parameters):
        class FunctionBuilderStage2:
            def __init__(self, name, parameters, parent):
                self.name = name 
                self.parameters = parameters 
                self.parent = parent

            def Begin(self):
                return FunctionBuilder(self.name, list(parameters), self.parent)

        return FunctionBuilderStage2(self.name, list(parameters), self.parent)

    def Begin(self):
        return FunctionBuilder(self.name, [], self.parent)

class FunctionBuilder(BlockBuilder):
    def __init__(self, name, parameters, parent=None):
        BlockBuilder.__init__(self, parent)
        self.name = name
        self.parameters = parameters

    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def End(self):
        f = FunctionStmt(self.name, self.parameters, self.statements)
        if self.parent != None:
            self.parent._appendnested(f)
        self._frozen = True

class ModuleBuilder(BlockBuilder):
    def __init__(self, parent=None):
        BlockBuilder.__init__(self, parent)

    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def End(self):
        self._frozen = True
        return Module(self.statements)

# If/While statements use same condition writing logic. The only bit that differs is that 
# for While statements we need to write Begin() and for If we need to write Then().
# Pass classes around for that.
class IfOrWhileBuilderPreStage1:
    class IfBuilderPreStage3:
        def __init__(self, cond, parent):
            self.cond = cond
            self.parent = parent

        def Then(self):
            return IfBuilder(self.cond, parent=self.parent)

    class WhileBuilderPreStage3:
        def __init__(self, cond, parent):
            self.cond = cond
            self.parent = parent

        def Begin(self):
            return WhileBuilder(self.cond, parent=self.parent)

    def __init__(self, lastprestage, parent):
        self.lastprestage = lastprestage 
        self.parent = parent

    def Equal(self, lhs, rhs):
        return self.lastprestage(BinaryExpr(BinaryOp.Eq, lhs, rhs), parent=self.parent)

    def NotEqual(self, lhs, rhs):
        return self.lastprestage(BinaryExpr(BinaryOp.NotEq, lhs, rhs), parent=self.parent)

    def LengthOf(self, item):
        class IfBuilderPreStage2:
            def __init__(self, lastprestage, iterable, parent):
                self.lastprestage = lastprestage 
                self.lengthof = LenExpr(iterable)
                self.parent = parent
            
            def EqualTo(self, value):
                return self.lastprestage( BinaryExpr(BinaryOp.Eq, self.lengthof, value), parent=self.parent )

        return IfBuilderPreStage2(self.lastprestage, item, parent=self.parent)

class IfBuilder(BlockBuilder):
    def __init__(self, cond, parent=None):
        BlockBuilder.__init__(self, parent)
        self.cond = cond
        self._thenbr = self.statements 
        self._elsebr = None

    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def Else(self):
        assert self._elsebr == None
        self._elsebr = []
        self.statements = self._elsebr
        return self

    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def End(self):
        assert self._thenbr != None and len(self._thenbr) != 0, 'then branch must not be empty'
        if self._elsebr != None:
            assert len(self._elsebr) != 0, 'optional else branch must not be empty'
        ifstmt = IfStmt(self.cond, self._thenbr, self._elsebr)
        if self.parent != None:
            self.parent._appendnested(ifstmt)
        self._frozen = True

class WhileBuilder(BlockBuilder):
    def __init__(self, cond, parent=None):
        BlockBuilder.__init__(self, parent)
        self.cond = cond

    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def End(self):
        assert len(self.statements) > 0, 'loop body must not empty'
        stmt = WhileStmt(self.cond, self.statements)
        if self.parent != None:
            self.parent._appendnested(stmt)
        self._frozen = True

class ForBuilder(BlockBuilder):
    def __init__(self, iteratorvariables, iterable, inrange=False, parent=None):
        BlockBuilder.__init__(self, parent)
        self.iteratorvariables = iteratorvariables 
        self.iterable = iterable
        self.inrange = inrange

    @ensure_not_previously_built
    @ensure_no_active_nested_builders
    def End(self):
        assert len(self.statements) > 0, 'loop body must not empty'
        if self.inrange:
            stmt = ForEachInRangeStmt(self.iteratorvariables, self.iterable)
        else: 
            stmt = ForEachStmt(self.iteratorvariables, self.iterable)
        if self.parent != None:
            self.parent._appendnested(stmt)
        self._frozen = True
