import unittest
from src.preprocdefinelang import NumberOfHoles, DefineLanguageCalculateNumberOfHoles 
from src.model.pattern import PatSequence, BuiltInPat, Nt, Repeat, Lit, LitKind, BuiltInPatKind, RepeatMatchMode, PatNumHoles , InHole
from src.model.tlform import DefineLanguage, Module
from src.context import CompilationContext
from src.parser import parse_string
from src.util import CompilationError

def result(lang, nt):
    return lang.nts[nt].nt.getmetadata(PatNumHoles)

class TestDefineLanguageHoleReachabilitySolver(unittest.TestCase):
            
    # (n ::= number)
    # (P ::= (E))
    # (E ::= (E n) hole)
    # n = (zero, zero) P = (one one) E = (one one)
    def test_holereachability0(self):
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

        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.One ))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.One ))

    # (P ::= (E))
    # (E ::= P)
    # P = (zero, zero) E = (zero zero)
    def test_holereachability1(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
            ]),
        ])



        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))

    # (n ::= number)          (zero zero)
    # (P ::= (E))             (one one)
    # (E ::= P (E n) hole)    (one one)
    def test_holereachability2(self):
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


        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.One ))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.One ))

    # (n ::= number)                (zero zero)
    # (P ::= (E))                   (one many)
    # (E ::= P (E n) (E E) hole)    (one many)
    def test_holereachability3(self):
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

        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.Many))

    # (n ::= number)                  (zero zero)
    # (P ::= (E))                     (zero many) 
    # (E ::= P n (E n) (E E) hole)    (zero many) zero because n
    def test_holereachability4(self):
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

        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))

    # (n ::= number)                  (zero zero)
    # (P ::= (E))                     (zero many) 
    # (E ::= P (E n) (hole ...))      (zero many) hole under ellipsis
    def test_holereachability5(self):
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

        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))

    # (n ::= number)                  (zero zero)
    # (P ::= (E))                     (many many) 
    # (E ::= P (E hole))              (many many) (((...) hole) hole)
    def test_holereachability6(self):
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

        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Many, NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Many, NumberOfHoles.Many))

    # (n ::= number)                    (zero zero)
    # (P ::= (E))                       (zero many) 
    # (E ::= P n (E hole))              (zero many) because n
    def test_holereachability7(self):
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

        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))


    # (n ::= number)                    (zero zero)
    # (P ::= (E E))                     (many many) 
    # (E ::= P (E n) hole)              (one many) 
    def test_holereachability8(self):
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

        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Many, NumberOfHoles.Many))

    # (n ::= number)                    (zero zero)
    # (P ::= (E E) hole)                (one many) 
    # (E ::= P (E n))                   (one many) 
    def test_holereachability9(self):
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

        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.One , NumberOfHoles.Many))

    # (n ::= number)                    (zero zero)
    # (Z ::= P)                         (zero many) 
    # (P ::= (E))                       (zero many)
    # (E ::= P ((Z) ... n) hole         (zero many)  because Z under ellipsis
    def test_holereachability10(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('Z', 'Z'), [
                Nt('P', 'P')
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                PatSequence([
                    Repeat(PatSequence([Nt('Z', 'Z'), ])),
                    Nt('n', 'n_2'),
                ]),
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))
        self.assertEqual(result(lang, 'Z'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))

    # (n ::= number)                    (zero zero)
    # (P ::= (E))                       (zero many)
    # (E ::= P ((P) ... ()) hole        (zero many)  
    def test_holereachability11(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                PatSequence([
                    Repeat(PatSequence([Nt('P', 'P'), ])),
                    PatSequence([]),
                ]),
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        DefineLanguageCalculateNumberOfHoles(lang).run()
        self.assertEqual(result(lang, 'n'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Zero))
        self.assertEqual(result(lang, 'E'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))
        self.assertEqual(result(lang, 'P'), PatNumHoles(NumberOfHoles.Zero, NumberOfHoles.Many))

    # (n ::= number)                    (zero zero)
    # (P ::= (E))                       (zero many)
    # (E ::= P (in-hole P n) hole        (zero many)  
    # Think we should disallow in-hole patterns in language grammar definition.
    def test_holereachability12(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                InHole(Nt('P', 'P'), Nt('n', 'n')),
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        try:
            DefineLanguageCalculateNumberOfHoles(lang).run()
            self.fail()
        except CompilationError as ex:
            self.assertEqual(str(ex), 'in-hole pattern in define-language')

    # (n ::= number)                    (zero zero)
    # (P ::= (E))                       (zero many)
    # (E ::= P ((in-hole P n) ...) hole        (zero many)  
    # Think we should disallow in-hole patterns in language grammar definition.
    def test_holereachability13(self):
        lang = DefineLanguage('Lang', [
            DefineLanguage.NtDefinition(Nt('n', 'n'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('P', 'P'), [
                PatSequence([Nt('E', 'E_0')]),
            ]),
            DefineLanguage.NtDefinition(Nt('E', 'E'), [
                Nt('P', 'P_1'),
                PatSequence([Repeat(InHole(Nt('P', 'P'), Nt('n', 'n'))) ]),
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        try:
            DefineLanguageCalculateNumberOfHoles(lang).run()
            self.fail()
        except CompilationError as ex:
            self.assertEqual(str(ex), 'in-hole pattern in define-language')
