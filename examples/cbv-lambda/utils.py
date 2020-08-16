def subs_check_is_false_1(term1, term2):
    assert isinstance(term1, Term)
    assert isinstance(term2, Boolean)
    print('here')
    if term2.value() == '#f':
        return term1 
    return None
