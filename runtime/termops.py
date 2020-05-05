def number_add(n1, n2):
    assert n1.kind() == term.TermKind.Integer 
    assert n2.kind() == term.TermKind.Integer
    return term.Integer(n1.value() + n2.value())
