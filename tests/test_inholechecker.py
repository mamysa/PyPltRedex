import unittest
from src.preprocdefinelang import DefineLanguageCalculateNumberOfHoles2, NumberOfHoles 
from src.pat import PatSequence, BuiltInPat, Nt, Repeat, Lit, LitKind, BuiltInPatKind, RepeatMatchMode, PatNumHoles 
from src.tlform import DefineLanguage, Module
from src.context import CompilationContext
from src.parser import parse_string
from src.util import CompilationError

def result(lang, nt):
    return lang.nts[nt].nt.getmetadata(PatNumHoles)

class TestInHoleCheck(unittest.TestCase):
            
    # (n ::= number)
    # (P ::= (E))
    # (E ::= (E n) hole)
    # n = (zero, zero) P = (one one) E = (one one)
    def test_inholecheck0(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                PatSequence([Nt('E', 'E_2'), Nt('n', 'n_3')]),
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles2(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.One ))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.One ))

    # (P ::= (E))
    # (E ::= P)
    # P = (zero, zero) E = (zero zero)
    def test_inholecheck1(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles2(lang).run()
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))

    # (n ::= number)          (zero zero)
    # (P ::= (E))             (one one)
    # (E ::= P (E n) hole)    (one one)
    def test_inholecheck2(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                PatSequence([Nt('E', 'E_2'), Nt('n', 'n_3')]),
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles2(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.One ))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.One ))

    # (n ::= number)                (zero zero)
    # (P ::= (E))                   (one many)
    # (E ::= P (E n) (E E) hole)    (one many)
    def test_inholecheck3(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                PatSequence([Nt('E', 'E_3'), Nt('E', 'E_4')]),
                PatSequence([Nt('E', 'E_5'), Nt('n', 'n_6')]),
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles2(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.Many))

    # (n ::= number)                  (zero zero)
    # (P ::= (E))                     (zero many) 
    # (E ::= P n (E n) (E E) hole)    (zero many) zero because n
    def test_inholecheck4(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                Nt('n', 'n_2'),
                PatSequence([Nt('E', 'E_3'), Nt('E', 'E_4')]),
                PatSequence([Nt('E', 'E_5'), Nt('n', 'n_6')]),
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles2(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))

    # (n ::= number)                  (zero zero)
    # (P ::= (E))                     (zero many) 
    # (E ::= P (E n) (hole ...))      (zero many) hole under ellipsis
    def test_inholecheck5(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                PatSequence([Nt('E', 'E_5'), Nt('n', 'n_6')]),
                PatSequence([Repeat(BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'))]), 
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles2(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))

    # (n ::= number)                  (zero zero)
    # (P ::= (E))                     (many many) 
    # (E ::= P (E hole))              (many many) (((...) hole) hole)
    def test_inholecheck6(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                PatSequence([Nt('E', 'E_5'), BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole')]),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles2(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Many, NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Many, NumberOfHoles.Many))

    # (n ::= number)                    (zero zero)
    # (P ::= (E))                       (zero many) 
    # (E ::= P n (E hole))              (zero many) because n
    def test_inholecheck7(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                Nt('n', 'n_2'),
                PatSequence([Nt('E', 'E_5'), BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole')]),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles2(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))


    # (n ::= number)                    (zero zero)
    # (P ::= (E E))                     (many many) 
    # (E ::= P (E n) hole)              (one many) 
    def test_inholecheck8(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0'), Nt('E', 'E_1')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                PatSequence([Nt('E', 'E_5'), Nt('n', 'n_2')]),
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles2(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Many, NumberOfHoles.Many))

    # (n ::= number)                    (zero zero)
    # (P ::= (E E) hole)                (one many) 
    # (E ::= P (E n))                   (one many) 
    def test_inholecheck9(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0'), Nt('E', 'E_1')]),
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                PatSequence([Nt('E', 'E_5'), Nt('n', 'n_2')]),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles2(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.Many))
