import unittest
from src.parser import RedexSpecParser
from src.preprocdefinelang import DefineLanguagePatternSimplifier, PatternComparator
from src.preprocdefinelang import NtResolver


def parse_pattern(pat, ntsyms):
    pat = RedexSpecParser(pat, is_filename=False).pattern()
    pat = NtResolver(ntsyms).transform(pat)
    return pat


class TestDefineLanguagePatternSimplifier(unittest.TestCase):

    def test_pattern_simplifier_1(self):
        input_ = parse_pattern('()', set(['n']))
        actual = DefineLanguagePatternSimplifier().transform(input_)
        expected = parse_pattern('()', set(['n']))
        self.assertTrue( PatternComparator().compare(actual, expected) )

    def test_pattern_simplifier_2(self):
        input_ = parse_pattern('(n n ... n n ... n)', set(['n']))
        actual = DefineLanguagePatternSimplifier().transform(input_)
        expected = parse_pattern('(n n n n ...)', set(['n']))
        self.assertTrue( PatternComparator().compare(actual, expected) )


    def test_pattern_simplifier_3(self):
        input_ = parse_pattern('(n n ... n n ... n x x ... n ... n n)', set(['n', 'x']))
        actual = DefineLanguagePatternSimplifier().transform(input_)
        expected = parse_pattern('(n n n n ... x x ... n n n ...)', set(['n', 'x']))
        self.assertTrue( PatternComparator().compare(actual, expected) )

    def test_pattern_simplifier_4(self):
        input_ = parse_pattern('((x n) ... (x n) n ... n (x n))', set(['n', 'x']))
        actual = DefineLanguagePatternSimplifier().transform(input_)
        expected = parse_pattern('((x n) (x n) ... n n ... (x n))', set(['n', 'x']))
        self.assertTrue( PatternComparator().compare(actual, expected) )

    def test_pattern_simplifier_5(self):
        input_ = parse_pattern('((x ... x ...) ... (x ...) n)', set(['n', 'x']))
        actual = DefineLanguagePatternSimplifier().transform(input_)
        expected = parse_pattern('((x ...) (x ...) ... n)', set(['n', 'x']))
        self.assertTrue( PatternComparator().compare(actual, expected) )

    def test_pattern_simplifier_6(self):
        input_ = parse_pattern('((6 x ... x ...) ... (6 x ...) n)', set(['n', 'x']))
        actual = DefineLanguagePatternSimplifier().transform(input_)
        expected = parse_pattern('((6 x ...) (6 x ...) ... n)', set(['n', 'x']))
        self.assertTrue( PatternComparator().compare(actual, expected) )

    def test_pattern_simplifier_7(self):
        input_ = parse_pattern('((7 x ... x ...) ... (6 x ...) n)', set(['n', 'x']))
        actual = DefineLanguagePatternSimplifier().transform(input_)
        expected = parse_pattern('((7 x ...) ... (6 x ...)  n)', set(['n', 'x']))
        self.assertTrue( PatternComparator().compare(actual, expected) )

    def test_pattern_simplifier_8(self):
        input_ = parse_pattern('(x ... n r ...)', set(['n', 'x', 'r']))
        actual = DefineLanguagePatternSimplifier().transform(input_)
        expected = parse_pattern('(x ... n r ...)', set(['n', 'x', 'r']))
        self.assertTrue( PatternComparator().compare(actual, expected) )
