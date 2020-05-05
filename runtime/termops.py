def number_add(n1, n2):
    assert n1.kind() == term.TermKind.Integer 
    assert n2.kind() == term.TermKind.Integer
    return term.Integer(n1.value() + n2.value())

def zzip(nxseq):
    assert nxseq.kind() == term.TermKind.Sequence
    seq = []
    for elem in nxseq.seq:
        n = elem.get(0)
        x = elem.get(1)
        seq.append(term.Variable('{}_{}'.format(x, n)))
    return term.Sequence(seq)
