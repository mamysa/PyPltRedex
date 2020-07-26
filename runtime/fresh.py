
# Traverse the term and find all variables matching ^(.*[^0-9])([0-9]+)$. 
# store group1 : [ int(group2) ] in the the dictionary (create key as necessary)
# If variable_prefix is not in dictionary, return variable_prefix
# Otherwise, retrieve array of numbers and sort them.
fresh_var_regex = re.compile('^(.*[^0-9])([0-9]+)$')
def variable_not_in(term, variable):
    if variable.kind() != TermKind.Variable:
        raise Exception('variable_not_in: contract violation - expected variable')
    variable_prefix = variable.value()
    prefixes = find_variables(term) 
    if variable_prefix not in prefixes:
        return Variable(variable_prefix)
    numbers = sorted(prefixes[variable_prefix])
    i, j = 1, 0
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
    assert isinstance(term, Ast)
    prefixes = {}
    stack = []
    stack.append(term)
    while len(stack) != 0:
        term = stack.pop()
        if term.kind() == TermKind.Variable:
            variable_name = term.value()
            match = fresh_var_regex.match(variable_name)
            if match:
                prefix, number =  match.group(1), match.group(2)
                if prefix not in prefixes:
                    prefixes[prefix] = []
                prefixes[prefix].append( int(number) )
            else: # doesn't end with number
                if variable_name not in prefixes:
                    prefixes[variable_name] = []
        if term.kind() == TermKind.Sequence:
            for i in range(term.length()):
                childterm = term.get(i)
                if childterm.kind() in [TermKind.Variable, TermKind.Sequence]:
                    stack.append(childterm)
    return prefixes
