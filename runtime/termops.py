def number_add(n1, n2):
    assert isinstance(n1, Integer)
    assert isinstance(n2, Integer)
    return Integer(n1.value() + n2.value())

def zzip(nxseq):
    assert nxseq.kind() == TermKind.Sequence
    seq = []
    for elem in nxseq.seq:
        n = elem.get(0)
        x = elem.get(1)
        assert isinstance(n, Integer)
        assert isinstance(x, Variable)
        seq.append(Variable('%s_%d' % (x.value(), n.value())))
    return Sequence(seq)

def mmap3mul2(n_1, n_2, n_3):
    assert isinstance(n_1, Integer)
    assert isinstance(n_2, Integer)
    assert isinstance(n_3, Integer)
    seq = []
    seq.append( Integer(2 * n_1.value()) )
    seq.append( Integer(2 * n_2.value()) )
    seq.append( Integer(2 * n_3.value()) )
    return Sequence(seq)

def map_multiply(ns, n):
    seq = []
    for i in range(ns.length()):
        v = ns.get(i).value() * n.value()
        seq.append(Integer(v))
    return Sequence(seq)



