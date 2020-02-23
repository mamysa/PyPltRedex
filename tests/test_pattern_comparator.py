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
