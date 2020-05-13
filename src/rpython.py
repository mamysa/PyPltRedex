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
class Stmt:
    pass

class IncludePythonSourceStmt(Stmt):
    def __init__(self, filename):
        self.filename = filename

class FunctionStmt(Stmt):
    def __init__(self, name, parameters):
        assert isinstance(name, str)
        self.name = name
        self.parameters = parameters 
        self.body = []
        self.__frozen = False

    def __repr__(self):
        return repr(self.parameters)

    def __iadd__(self,arg):
        assert not self.__frozen
        self.body.append(arg)
        return self

    def End(self):
        assert self.__frozen == False
        self.__frozen = True
        assert len(self.body) > 0

    def __assert_parameters_unique(self):
        pass

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
    def __init__(self, cond):
        self._cond = cond 
        self.body = [] 

    def End(self):
        assert self.body != None
        assert len(self.body) != 0

    def __iadd__(self,arg):
        self.body.append(arg)
        return self


class IfStmt:
    def __init__(self, cond):
        self._cond = cond 
        self._thenbr = []
        self._elsebr = None
        self.currentbranch = None
    
    def Then(self):
        self.currentbranch = self._thenbr
        return self._thenbr 

    def Else(self):
        self._elsebr = []
        self.currentbranch = self._elsebr
        return self

    def End(self):
        pass

    def __iadd__(self,arg):
        self.currentbranch.append(arg)
        return self


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
class Statement:
    def IncludeFromPythonSource(filename):
        return IncludePythonSourceStmt(filename)

    def Function(name):
        class FunctionPhase1:
            def __init__(self, name):
                self.name = name

            def WithParameters(*parameters):
                class FunctionPhase2:
                    def __init__(self, name, paramteters):
                        self.name = name 
                        self.parameters = paramteters 

                    def Begin(self):
                        return FunctionStmt(name, parameters)
                return FunctionPhase2(name, list(parameters))

            def Begin(self):
                return FunctionStmt(name, [])
        return FunctionPhase1(name)

    
    def For(*variables):

        class ForBegin:
            def __init__(self, ForStmt, iteratorvariables, iterable):
                self.ForStmt = ForStmt
                self.iteratorvariables = iteratorvariables 
                self.iterable = iterable 
            
            def Begin(self):
                return self.ForStmt(self.iteratorvariables, self.iterable)

        class ForCont:
            def __init__(self, variables):
                self.variables = list(variables)

            def In(self, value):
                return ForBegin(ForEachStmt, self.variables, value)

            def InRange(self, value):
                return ForBegin(ForEachInRangeStmt, self.variables, value)

        return ForCont(variables)

    class While:
        # This completes initial While statement creation, creates IfStmt instance
        # with initialized condition.
        class WhileBegin:
            def __init__(self, op, lhs, rhs):
                self.op  = op
                self.lhs = lhs
                self.rhs = rhs 

            def Begin(self):
                return IfStmt(BinaryExpr(BinaryOp.Eq, self.lhs, self.rhs))

        @classmethod
        def Equal(cls, lhs, rhs):
            return cls.WhileBegin(BinaryOp.Eq, lhs, rhs)

        @classmethod
        def NotEqual(cls, lhs, rhs):
            return cls.WhileBegin(BinaryOp.NotEq, lhs, rhs)

        # Special case when we'd want to check length of iterable in the condition.
        # Might only be useful in non-determinstic ellipsis matching where we have the queue...
        @classmethod
        def LengthOf(cls, item):
            class IfPhase1:
                def __init__(self, WhileBegin, of):
                    self.WhileBegin = WhileBegin 
                    self.lengthof = LenExpr(of)
                
                def EqualTo(self, value):
                    return self.WhileBegin(BinaryOp.Eq, self.lengthof, value)

                def NotEqualTo(self, value):
                    return self.WhileBegin(BinaryOp.NotEq, self.lengthof, value)

            return IfPhase1(cls.WhileBegin, item)

    class If:
        # This completes initial If statement creation, creates IfStmt instance
        # with initialized condition.
        class IfBegin:
            def __init__(self, op, lhs, rhs):
                self.op  = op
                self.lhs = lhs
                self.rhs = rhs 
            
            def Then(self):
                return IfStmt(BinaryExpr(BinaryOp.Eq, self.lhs, self.rhs))

        @classmethod
        def Equal(cls, lhs, rhs):
            return cls.IfBegin(BinaryOp.Eq, lhs, rhs)

        @classmethod
        def NotEqual(cls, lhs, rhs):
            return cls.IfBegin(BinaryOp.NotEq, lhs, rhs)

        # Special case when we'd want to check length of iterable in the condition.
        # Might only be useful in non-determinstic ellipsis matching where we have the queue...
        @classmethod
        def LengthOf(cls, item):
            class IfPhase1:
                def __init__(self, IfBegin, of):
                    self.IfBegin = IfBegin 
                    self.lengthof = LenExpr(of)
                
                def EqualTo(self, value):
                    return self.IfBegin(BinaryOp.Eq, self.lengthof, value)

                def NotEqualTo(self, value):
                    return self.IfBegin(BinaryOp.NotEq, self.lengthof, value)

            return IfPhase1(cls.IfBegin, item)
        
    def AssignTo(*args):
        class AssignToPhase1:
            def __init__(self, args):
                self.args = args 

            def Add(self, lhs, rhs):
                return AssignStmt(self.args, BinaryExpr(BinaryOp.Add, lhs, rhs))

            def Subtract(self, lhs, rhs):
                return AssignStmt(self.args, BinaryExpr(BinaryOp.Sub, lhs, rhs))

            def PyInt(self, value):
                return AssignStmt(self.args, PyInt(value))

            def PyList(self, *initializer):
                return AssignStmt(self.args, PyList(initializer))

            def PyTuple(self, *initializer):
                return AssignStmt(self.args, PyTuple(initializer))


            @property
            def Call(self):
                class CallPhase1:
                    def __init__(self, assignments):
                        self.assignments = assignments
                    def WithArguments(self, *args):
                        class CallPhase2:
                            def __init__(self, assignments, args):
                                self.assignments = assignments
                                self.args = args
                            def Function(self, name):
                                return AssignStmt(self.assignments, CallExpr(name, self.args))
                        return CallPhase2(self.assignments, list(args))
                    def Function(self, name):
                        return AssignStmt(self.assignments, CallExpr(name, []))
                return CallPhase1(self.args)

        return AssignToPhase1(list(args))

whilestmt = Statement.While.LengthOf(PyId('x')).EqualTo(PyInt(2)).Begin()
