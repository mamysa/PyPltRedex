import unittest
from src.parser import RedexSpecParser
from src.preprocdefinelang import PatternComparator 
from src.preprocdefinelang import NtResolver


def parse_pattern(pat, ntsyms):
    pat = RedexSpecParser(pat, is_filename=False).pattern()
    pat = NtResolver(ntsyms).transform(pat)
    return pat

class TestPatternComparator(unittest.TestCase):

    def test_pattern_comparator_1(self):
        pat1 = parse_pattern('n_1', set(['n']))
        pat2 = parse_pattern('n_2', set(['n']))
        self.assertTrue( PatternComparator().compare(pat1, pat2) )

    def test_pattern_comparator_2(self):
        pat1 = parse_pattern('#t', set([]))
        pat2 = parse_pattern('#t', set([]))
        self.assertTrue( PatternComparator().compare(pat1, pat2) )

    def test_pattern_comparator_3(self):
        pat1 = parse_pattern('#t', set([]))
        pat2 = parse_pattern('#f', set([]))
        self.assertFalse( PatternComparator().compare(pat1, pat2) )

    def test_pattern_comparator_4(self):
        pat1 = parse_pattern('(n_1 ...)', set(['n']))
        pat2 = parse_pattern('(n_2 ...)', set(['n']))
        self.assertTrue( PatternComparator().compare(pat1, pat2) )

    def test_pattern_comparator_5(self):
        pat1 = parse_pattern('((x_0) n_1 (n_2))', set(['n', 'x']))
        pat2 = parse_pattern('((x_1) n_2 (n_3))', set(['n', 'x']))
        self.assertTrue( PatternComparator().compare(pat1, pat2) )

    def test_pattern_comparator_6(self):
        pat1 = parse_pattern('((x_0) n_1 n_2)', set(['n', 'x']))
        pat2 = parse_pattern('((x_1) n_2 (n_3))', set(['n', 'x']))
        self.assertFalse( PatternComparator().compare(pat1, pat2) )

    def test_pattern_comparator_7(self):
        pat1 = parse_pattern('(x_0 n_1 (n_2))', set(['n', 'x']))
        pat2 = parse_pattern('((x_1) n_2 (n_3))', set(['n', 'x']))
        self.assertFalse( PatternComparator().compare(pat1, pat2) )

    def test_pattern_comparator_8(self):
        pat1 = parse_pattern('((x_0) variable-not-otherwise-mentioned_1)', set(['x']))
        pat2 = parse_pattern('((x_4) variable-not-otherwise-mentioned_1)', set(['x']))
        self.assertTrue( PatternComparator().compare(pat1, pat2) )

    def test_pattern_comparator_9(self):
        pat1 = parse_pattern('(x n)', set(['x']))
        pat2 = parse_pattern('(n x)', set(['x']))
        self.assertFalse( PatternComparator().compare(pat1, pat2) )

    def test_pattern_comparator_10(self):
        pat1 = parse_pattern('(3)', set([]))
        pat2 = parse_pattern('(4)', set([]))
        self.assertFalse( PatternComparator().compare(pat1, pat2) )


