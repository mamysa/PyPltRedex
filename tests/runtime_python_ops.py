def b_length_equal(sequence, desiredlength):
    assert isinstance(sequence, Sequence)
    assert isinstance(desiredlength, Integer)
    return sequence.length() == desiredlength.value()

def b_int_is_even(integer):
    assert isinstance(integer, Integer)
    return integer.value() % 2 == 0

def sequence_int_sum(sequence):
    assert isinstance(sequence, Sequence)
    intsum = 0
    for i in range(sequence.length()):
        term = sequence.get(i)
        assert isinstance(term, Integer)
        intsum = intsum + term.value()
    return Integer(intsum)
