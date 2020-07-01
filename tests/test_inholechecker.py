import unittest
from src.preprocdefinelang import NumberOfHoles, DefineLanguageCalculateNumberOfHoles, PatternNumHolesChecker 
from src.pat import PatSequence, BuiltInPat, Nt, Repeat, Lit, LitKind, BuiltInPatKind, RepeatMatchMode, PatNumHoles , InHole
from src.tlform import DefineLanguage, Module
from src.context import CompilationContext
from src.parser import parse_string
from src.util import CompilationError


class TestPatternNumHolesChecker(unittest.TestCase):
    # (n ::= number)
    # (P ::= (E))
    # (E ::= (E n) hole)
    # n = (zero, zero) P = (one one) E = (one one)
    def test_patternnumholes0(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                PatSequence([Nt('E', 'E'), Nt('n', 'n')]),
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles(lang).run()
        pat = PatSequence([Repeat(Nt('E', 'E'))])
        nmin, nmax = PatternNumHolesChecker(lang, pat).run()
        self.assertEqual(nmin, NumberOfHoles.Zero)
        self.assertEqual(nmax, NumberOfHoles.Many)

        pat = PatSequence([Nt('P', 'P'), Repeat(Nt('E', 'E'))])
        nmin, nmax = PatternNumHolesChecker(lang, pat).run()
        self.assertEqual(nmin, NumberOfHoles.One)
        self.assertEqual(nmax, NumberOfHoles.Many)

        pat = PatSequence([Repeat( InHole(Nt('E', 'E'), Nt('n', 'n')))])
        nmin, nmax = PatternNumHolesChecker(lang, pat).run()
        self.assertEqual(nmin, NumberOfHoles.Zero)
        self.assertEqual(nmax, NumberOfHoles.Zero)
        
        pat = PatSequence([Nt('P', 'P'), Nt('n', 'n'), Nt('E', 'E')])
        nmin, nmax = PatternNumHolesChecker(lang, pat).run()
        self.assertEqual(nmin, NumberOfHoles.Many)
        self.assertEqual(nmax, NumberOfHoles.Many)

        pat = PatSequence([Nt('n', 'n'), BuiltInPat(BuiltInPatKind.Number, 'number', 'number'), BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole')])
        nmin, nmax = PatternNumHolesChecker(lang, pat).run()
        self.assertEqual(nmin, NumberOfHoles.One)
        self.assertEqual(nmax, NumberOfHoles.One)
