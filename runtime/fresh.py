# # Very useful procedure to generate fresh identifiers.
# Let Variables(t) be a set of all variables in term t. Given a term t and a prefix p, 
# it will produce a fresh variable v with prefix p and some suffix s s.t. v is not in Variables(term).
# Suffix s is numerical.

# Initialize a map of prefix -> [ suffix ].
# Each variable v in Variables(t) is decomposed into prefix p and suffix n. If p is not present in the map,
# initialize it with empty list and store suffix n. If p is present, simply add n to the list.
# If such decomposition is impossible (i.e. identifier doesn't end with number), then v is added to the mapping with -1. -1 is used to represent occurence of variable v s.t. v == p.

# Given prefix p, attempt to find pprime in the mapping such that p == pprime. Retrieve appropriate list of suffixes interpreted as integers.
# If list is empty, then p is fresh and simply return p.
# Otherwise, sort the list in the ascending order. If first element in the list is not -1, this means that prefix # p is itself a fresh variable and return p.
# Otherwise , our goal is to find the smallest number i>0 that is not in the sorted list. Starting from the second element j of the list (since the first one must be -1) and initializing suffix s to 1, there are several cases to consider.

# s < suffixes[j]: return s
# s > suffixes[j]: increment j. This only happens when 0 is in the list.
# s == suffixes[j]: increment j and s by 1.
# Iterate until the end of the list.
# Return string prefix + s.
def decompose_variable(var):
    i = len(var) - 1
    if not (ord(var[i]) >= 48 and ord(var[i]) <= 57):
        return False, None, None
    while ord(var[i]) >= 48 and ord(var[i]) <= 57:
        i -= 1
    i = i + 1
    return True, var[:i], var[i:]

def variable_not_in(term, variable):
    if variable.kind() != TermKind.Variable:
        raise Exception('variable_not_in: contract violation - expected variable')

    prefixes = find_variables(term) 
    variable_prefix = variable.value()
    success, prefix, number = decompose_variable(variable_prefix)
    if success:
        variable_prefix = prefix
        if variable_prefix not in prefixes:
            return Variable(variable_prefix+number)
        if number not in prefixes[variable_prefix]:
            return Variable(variable_prefix+number)
    else:
        if variable_prefix not in prefixes:
            return Variable(variable_prefix)

    numbers = [0] * len(prefixes[variable_prefix])
    for i, n in enumerate(prefixes[variable_prefix]):
        numbers[i] = int(n)
    numbers = sorted(numbers)
    if numbers[0] != -1:
        return Variable(variable_prefix)
    i, j = 1, 1
    while j < len(numbers):
        if i < numbers[j]:
            break
        if i > numbers[j]:
            j += 1
            continue
        if i == numbers[j]:
            i += 1
            j += 1
    return Variable(variable_prefix + str(i))


def find_variables(term):
    assert isinstance(term, Term)
    prefixes = {}
    stack = []
    stack.append(term)
    while len(stack) != 0:
        term = stack.pop()
        if term.kind() == TermKind.Variable:
            variable_name = term.value()
            success, prefix, number = decompose_variable(variable_name)
            if success:
                if prefix not in prefixes:
                    prefixes[prefix] = []
                prefixes[prefix].append(number)
            else: # doesn't end with number
                if variable_name not in prefixes:
                    prefixes[variable_name] = []
                prefixes[variable_name].append('-1')
        if term.kind() == TermKind.Sequence:
            for i in range(term.length()):
                childterm = term.get(i)
                if childterm.kind() in [TermKind.Variable, TermKind.Sequence]:
                    stack.append(childterm)
    return prefixes
