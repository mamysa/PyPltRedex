import unittest
from src.preprocess import TopLevelProcessor
from src.preprocess.pattern import DefineLanguage_NtCycleChecker, DefineLanguage_NtClosureSolver
from src.model.pattern import PatSequence, BuiltInPat, Nt, Repeat, Lit, LitKind, BuiltInPatKind, RepeatMatchMode
from src.model.tlform import DefineLanguage, Module
from src.context import CompilationContext
from src.util import CompilationError

def genmsg(path):
    return 'nt cycle {}'.format(path)

# This one is a bit hard to test due to python's randomized hashing every time
# program is run. Going to list all possible cases for now.
class TestCycleCheck(unittest.TestCase):
    def test_cyclecheck1(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('m', 'm'), [
                Nt('e', 'e'), 
                PatSequence([Lit('-', LitKind.Variable), Nt('m', 'm_1'), Nt('m', 'm_2')]),
            ]),
            DefineLanguage.NtDefinition(Nt('e', 'e'), [
                PatSequence([Lit('+', LitKind.Variable), Nt('e', 'e_1'), Nt('e', 'e_2')]),
                Nt('n', 'n'), 
            ]),
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'), 
                Nt('e', 'e'), 
            ]),
        ])

        successors, _ = DefineLanguage_NtClosureSolver(lang).run()
        try:
            DefineLanguage_NtCycleChecker(lang, successors).run()
            self.fail('should throw')
        except CompilationError as ex:
            self.assertIn(str(ex), [genmsg(['e', 'n', 'e']), genmsg(['n', 'e', 'n'])])

    def test_cyclecheck2(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('m', 'm'), [
                Nt('e', 'e'),
                Nt('m', 'm'),
            ]),
            DefineLanguage.NtDefinition(Nt('e', 'e'), [
                PatSequence([Lit('+', LitKind.Variable), Nt('e', 'e_1'), Nt('e', 'e_2')]),
                Nt('n', 'n'), 
            ]),
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'), 
            ]),
        ])

        successors, _ = DefineLanguage_NtClosureSolver(lang).run()
        try:
            DefineLanguage_NtCycleChecker(lang, successors).run()
            self.fail('should throw')
        except CompilationError as ex:
            self.assertIn(str(ex), [genmsg(['m', 'm'])])



