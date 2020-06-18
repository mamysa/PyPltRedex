import unittest
from src.preprocdefinelang import MakeEllipsisDeterministic
from src.pat import PatSequence, BuiltInPat, Nt, Repeat, Lit, LitKind, BuiltInPatKind, RepeatMatchMode
from src.tlform import DefineLanguage
from src.digraph import DiGraph

class TestMakeEllipsisDeterministic(unittest.TestCase):
    def test_computeclosure(self):
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
            ]),
            DefineLanguage.NtDefinition(Nt('z', 'z'), [
                Nt('n', 'n'),
            ]),
            DefineLanguage.NtDefinition(Nt('y', 'y'), [
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        med = MakeEllipsisDeterministic(lang, Nt('e', 'e'))
        closure = med._compute_closure()

        self.assertSetEqual(closure['m'], {'e', 'n', 'number'})
        self.assertSetEqual(closure['e'], {     'n', 'number'})
        self.assertSetEqual(closure['z'], {     'n', 'number'})
        self.assertSetEqual(closure['n'], {          'number'})
        self.assertSetEqual(closure['y'], {          'hole'  })


    def test_partitioning(self):
        seq1 = [ Nt('y', 'y'), Repeat(Nt('e', 'e')), Repeat(Nt('x', 'x')), Nt('y', 'y'), Nt('z', 'z')]
        #seq1 = [ Nt('y', 'y'), Repeat(Nt('e', 'e')), Repeat(Nt('x', 'x')), Nt('y', 'y') ]

        partitions = MakeEllipsisDeterministic._partitionseq(None, seq1)
        self.assertEqual(len(partitions), 3)

        contains_ellipsis, partition = partitions[0]
        self.assertEqual(len(partition), 1)
        self.assertEqual(contains_ellipsis, False)
        self.assertEqual(partition[0], Nt('y', 'y'))

        contains_ellipsis, partition = partitions[1]
        self.assertEqual(len(partition), 3)
        self.assertEqual(contains_ellipsis, True)
        self.assertEqual(partition[0], Repeat(Nt('e', 'e')))
        self.assertEqual(partition[1], Repeat(Nt('x', 'x')))
        self.assertEqual(partition[2], Nt('y', 'y'))

        contains_ellipsis, partition = partitions[2]
        self.assertEqual(len(partition), 1)
        self.assertEqual(contains_ellipsis, False)
        self.assertEqual(partition[0], Nt('z', 'z'))


    def test_det_1(self):
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
            ]),

            DefineLanguage.NtDefinition(Nt('z', 'z'), [
                BuiltInPat(BuiltInPatKind.Number, 'number', 'number'),
            ]),
            DefineLanguage.NtDefinition(Nt('h', 'h'), [
                BuiltInPat(BuiltInPatKind.Hole, 'hole', 'hole'),
            ]),
        ])

        # (e e ... m ... n)  no deterministm possible
        pat = PatSequence([
                Nt('e', 'e'), 
                Repeat(Nt('e', 'e')), 
                Repeat(Nt('m', 'm')), 
                Nt('n', 'n') 
            ])
        actual = MakeEllipsisDeterministic(lang, pat).run()
        self.assertEqual(actual, pat)
        # (e ... number ... m ...) # s can be matched deterministically
        pat = PatSequence([
                Repeat(Nt('e', 'e')), 
                Repeat(BuiltInPat(BuiltInPatKind.Number, 'number', 'number')), 
                Repeat(Nt('m', 'm')), 
            ])

        expected = PatSequence([
                Repeat(Nt('e', 'e')), 
                Repeat(BuiltInPat(BuiltInPatKind.Number, 'number', 'number')), 
                Repeat(Nt('m', 'm'), RepeatMatchMode.Deterministic), 
            ])


        actual = MakeEllipsisDeterministic(lang, pat).run()
        self.assertEqual(actual, expected)

        # (e e ... m ... h)  m should be deterministic
        pat = PatSequence([
                Nt('e', 'e'), 
                Repeat(Nt('e', 'e')), 
                Repeat(Nt('m', 'm')), 
                Nt('h', 'h') 
            ])

        expected = PatSequence([
                Nt('e', 'e'), 
                Repeat(Nt('e', 'e')), 
                Repeat(Nt('m', 'm'), RepeatMatchMode.Deterministic), 
                Nt('h', 'h') 
            ])

        actual = MakeEllipsisDeterministic(lang, pat).run()
        self.assertEqual(actual, expected)

        # (e e ... m ... h ...)  m and h should be deterministic.
        pat = PatSequence([
                Nt('e', 'e'), 
                Repeat(Nt('e', 'e')), 
                Repeat(Nt('m', 'm')), 
                Repeat(Nt('h', 'h')) 
            ])

        expected = PatSequence([
                Nt('e', 'e'), 
                Repeat(Nt('e', 'e')), 
                Repeat(Nt('m', 'm'), RepeatMatchMode.Deterministic), 
                Repeat(Nt('h', 'h'), RepeatMatchMode.Deterministic)
            ])

        actual = MakeEllipsisDeterministic(lang, pat).run()
        self.assertEqual(actual, expected)


        # ((e) ... (m) ... (h) ...) m and h should be deterministic.
        pat = PatSequence([
                Repeat(PatSequence([Nt('e', 'e')])),
                Repeat(PatSequence([Nt('m', 'm')])),
                Repeat(PatSequence([Nt('h', 'h')])),
            ])

        expected = PatSequence([
                Repeat(PatSequence([Nt('e', 'e')])),
                Repeat(PatSequence([Nt('m', 'm')]), RepeatMatchMode.Deterministic),
                Repeat(PatSequence([Nt('h', 'h')]), RepeatMatchMode.Deterministic),
            ])

        actual = MakeEllipsisDeterministic(lang, pat).run()
        self.assertEqual(actual, expected)


        #((e ...) ... (m ...) ... (m ... h ...) ...) -> (m ... h ...) term can be matched deterministically
        pat = PatSequence([
                Repeat(PatSequence([
                        Repeat(Nt('e', 'e')),
                    ])),
                Repeat(PatSequence([
                        Repeat(Nt('m', 'm')),
                    ])),
                Repeat(PatSequence([
                        Repeat(Nt('m', 'm')),
                        Repeat(Nt('h', 'h')),
                    ])),
            ])

        expected = PatSequence([
                Repeat(PatSequence([
                        Repeat(Nt('e', 'e'), RepeatMatchMode.Deterministic),
                    ])),
                Repeat(PatSequence([
                        Repeat(Nt('m', 'm'), RepeatMatchMode.Deterministic),
                    ])),
                Repeat(PatSequence([
                        Repeat(Nt('m', 'm'), RepeatMatchMode.Deterministic),
                        Repeat(Nt('h', 'h'), RepeatMatchMode.Deterministic),
                    ]), RepeatMatchMode.Deterministic),
            ])

        actual = MakeEllipsisDeterministic(lang, pat).run()
        self.assertEqual(actual, expected)

        #((e ...) ... (m ... h ...) ... (m ... h ...)) ->  nondeterministc
        pat = PatSequence([
                Repeat(PatSequence([
                        Repeat(Nt('e', 'e')),
                    ])),
                Repeat(PatSequence([
                        Repeat(Nt('m', 'm')),
                        Repeat(Nt('h', 'h')),
                    ])),
                PatSequence([
                        Repeat(Nt('m', 'm')),
                        Repeat(Nt('h', 'h')),
                    ]),
            ])

        expected = PatSequence([
                Repeat(PatSequence([
                        Repeat(Nt('e', 'e'), RepeatMatchMode.Deterministic),
                    ])),
                Repeat(PatSequence([
                        Repeat(Nt('m', 'm'), RepeatMatchMode.Deterministic),
                        Repeat(Nt('h', 'h'), RepeatMatchMode.Deterministic),
                    ])),
                PatSequence([
                        Repeat(Nt('m', 'm'), RepeatMatchMode.Deterministic),
                        Repeat(Nt('h', 'h'), RepeatMatchMode.Deterministic),
                    ]),
            ])

        actual = MakeEllipsisDeterministic(lang, pat).run()
        self.assertEqual(actual, expected)
