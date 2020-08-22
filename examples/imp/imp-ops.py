def variable_not_found_exception(variable):
    assert isinstance(variable, Variable)
    print("Exception: variable %s not found" % (variable.value()))
    raise Exception()

def integer_add(int1, int2):
    assert isinstance(int1, Integer)
    assert isinstance(int2, Integer)
    return Integer(int1.value() + int2.value())

def integer_mul(int1, int2):
    assert isinstance(int1, Integer)
    assert isinstance(int2, Integer)
    return Integer(int1.value() * int2.value())

def integer_lteq(int1, int2):
    assert isinstance(int1, Integer)
    assert isinstance(int2, Integer)
    v = int1.value() <= int2.value()
    if v:
        return Boolean('#t')
    return Boolean('#f')

# FIXME why not just booleans directly?
def boolean_and(b1, b2):
    assert isinstance(b1, Boolean)
    assert isinstance(b2, Boolean)
    if b1.value() == "#f" or b2.value() == "#f": 
        return Boolean("#f")
    return Boolean("#t")

def boolean_or(b1, b2):
    assert isinstance(b1, Boolean)
    assert isinstance(b2, Boolean)
    if b1.value() == "#t" or b2.value() == "#t": 
        return Boolean("#t")
    return Boolean("#f")

def boolean_not(b1):
    assert isinstance(b1, Boolean)
    if b1.value() == "#t":
        return Boolean("#f")
    return Boolean("#t")
