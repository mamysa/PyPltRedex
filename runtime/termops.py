def number_add(n1, n2):
    assert n1.kind() == TermKind.Integer 
    assert n2.kind() == TermKind.Integer
    return Integer(n1.value() + n2.value())

def zzip(nxseq):
    assert nxseq.kind() == TermKind.Sequence
    seq = []
    for elem in nxseq.seq:
        n = elem.get(0)
        x = elem.get(1)
        seq.append(Variable('{}_{}'.format(x, n)))
    return Sequence(seq)

def mmap3mul2(n_1, n_2, n_3):
    seq = []
    seq.append( Integer(2 * n_1.value()) )
    seq.append( Integer(2 * n_2.value()) )
    seq.append( Integer(2 * n_3.value()) )
    return Sequence(seq)

