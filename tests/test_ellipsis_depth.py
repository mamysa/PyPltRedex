import unittest
from src.parser import RedexSpecParser
from src.preprocdefinelang import EllipsisDepthChecker
from src.preprocdefinelang import NtResolver


class TestEllipsisDepth(unittest.TestCase):


    def test_ellpsis_depth_1(self):
        pat = RedexSpecParser('((n_1 ...) ... n_1 ...)', is_filename=False).pattern()
        pat = NtResolver(set(['n'])).transform(pat)
        with self.assertRaises(Exception):
            EllipsisDepthChecker().transform(pat)

    def test_ellpsis_depth_2(self):
        pat = RedexSpecParser('((n_1 ...) ... (n_1 ...) ...)', is_filename=False).pattern()
        pat = NtResolver(set(['n'])).transform(pat)
        EllipsisDepthChecker().transform(pat)

    def test_ellpsis_depth_3(self):
        pat = RedexSpecParser('((n_1 ...) ... n_2 ... (n_1 ...))', is_filename=False).pattern()
        pat = NtResolver(set(['n'])).transform(pat)
        with self.assertRaises(Exception):
            EllipsisDepthChecker().transform(pat)

    def test_ellpsis_depth_4(self):
        pat = RedexSpecParser('((n_1 ...) ... n_2 ... (n_2 ...))', is_filename=False).pattern()
        pat = NtResolver(set(['n'])).transform(pat)
        EllipsisDepthChecker().transform(pat)

    def test_ellpsis_depth_5(self):
        pat = RedexSpecParser('((n_1 ...) ... n_2 ...)', is_filename=False).pattern()
        pat = NtResolver(set(['n'])).transform(pat)
        EllipsisDepthChecker().transform(pat)


















