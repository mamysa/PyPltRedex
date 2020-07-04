import src.model.tlform as tlform 
import src.model.pattern as pattern
# This pass attempts to make consecutive ellipses match deterministically.
# Here's the example:
# Given language (m ::= (* m m) e) (e ::= (+ e e) n) (n ::= number), ellipses in pattern 
# (m_1 ... e_1 ... n_1 ... e_2) cannot match deterministically - because m_1, e_1 and e_2 can also be numbers.
# We have {e} ⊆ m, {n} ⊆ e, and {number} ⊆ n. If we compute transitive "closure" for each non-terminal we get the following:
# {number, n, e} ⊆ m; {number, n} ⊆ e; {number} ⊆ n. Two patterns p1,p2 cannot be made deterministic 
# if closure(p1) ∩ closure(p2) is not empty.
#FIXME this is not true for duplicate definitions that are not used anywhere, add extra (z ::= number) rule and 
# while computing closure z is not in e. We need to introduce a graph, perform dfs and see if common nodes can be reached.

# This should handle primitive cases of Nt and BuiltInPat. 
 
# Otherwise, we should check if patterns being compared are structurally identical and leafs of patterns
# pass closure membership test from above.
# In ((m_1 e_1) ... (e_2 n_1) ...) subpatterns  (m_1 e_1) and (e_2 n_1)
# are structurally identical and for pair (m_1, e_2) e ∈ closure(m), for (e_1, n_1) n ∈ closure(e)

# Now we consider pattern ((x_1 ...) ... (n_1 ...) ...). (x_1 ...) ... pattern cannot be matched deterministically since even though
# patterns x and n match competely different terms  both subpatterns may match (). 
#For example, for term (a b) () (1 2 3) there are two matches match1: x_1=((a b) ()) n_1=((1 2 3)) match2: x_1=((a b))  n_1=(() (1 2 3)).
# This should be initial term check.

# What about ((x_1 ... n_1) ... (s_1 ... n_2) ...)? Both subterms under ellipsis have the same structure. Term ((x y z 1) (1 2 3 4)) matches 
# the pattern but since (x y z) and (1 2 3) are optional, the term without these becomes ((1) (4)) which has to be matched non-deterministically.
# Similarly, by adding (y ::= string) rule to the language the pattern ((x_1 ... y_1) ... (x_1 ... n_1) ...) CAN BE matched deterministically, 
# for example ((x y z "helloworld") (x 1)). 
# TLDR we ignore ellipsis and make decision based on elements of the sequence that have to matched. If closure test fails then pattern matching can
# be made deterministic.

# TODO in-hole treatment?  
class EllipsisMatchModeRewriter(pattern.PatternTransformer):
    # Given two patterns pat1 and pat2, both under ellipsis, return True if pat1
    # can be matched deterministically.
    class PatternStructuralChecker:
        def __init__(self, closures):
            self.closures = closures

        def aredifferent(self, pat1, pat2):
            assert isinstance(pat1, pattern.Pat)
            assert isinstance(pat2, pattern.Pat)
            method_name = 'aredifferent' + pat1.__class__.__name__
            method_ref = getattr(self, method_name)
            return method_ref(pat1, pat2)

        def aredifferentPatSequence(self, pat1, pat2):
            assert isinstance(pat1, pattern.PatSequence)
            if isinstance(pat2, pattern.PatSequence):
                p1 = pat1.get_nonoptional_matches()
                p2 = pat2.get_nonoptional_matches()
                if len(p1) != len(p2):
                    return True
                for i in range(len(p1)):
                    if self.aredifferent(p1[i], p2[i]):
                        return True
                return False 
            return True

        def aredifferentNt(self, pat1, pat2):
            assert isinstance(pat1, pattern.Nt)
            if isinstance(pat2, pattern.Nt):
                pat1cl = self.closures[pat1.prefix]
                pat2cl = self.closures[pat2.prefix]
                return len(pat1cl.intersection(pat2cl)) == 0
            if isinstance(pat2, pattern.BuiltInPat):
                pat1cl = self.closures[pat1.prefix]
                return not pat2.prefix in pat1cl
            return True

        # TODO figure out how to handle adjacent in-hole patterns properly.
        def aredifferentInHole(self, pat1, pat2):
            assert isinstance(pat1, pattern.InHole)
            return False

        def aredifferentBuiltInPat(self, pat1, pat2):
            assert isinstance(pat1, pattern.BuiltInPat)
            if isinstance(pat2, pattern.BuiltInPat):
                return pat1.kind != pat2.kind
            if isinstance(pat2, pattern.Nt):
                pat2cl = self.closures[pat2.prefix]
                return not pat1.prefix in pat2cl
            return True

        def aredifferentLit(self, pat1, pat2):
            assert isinstance(pat1, pattern.Lit)
            if isinstance(pat2, pattern.Lit):
                if pat1.kind == pat2.kind:
                    return pat1.lit != pat2.lit
                return True
            return True

    def __init__(self, definelanguage, closures):
        assert isinstance(definelanguage, tlform.DefineLanguage)
        self.definelanguage = definelanguage 
        self.closures = closures

    # Partitions sequence of terms 
    def _partitionseq(self, seq):
        matching_ellipsis = False
        partitions = [] 
        partition = []
        for i, pat in enumerate(seq):
            if isinstance(pat, pattern.Repeat):
                if matching_ellipsis:
                    partition.append(pat)
                else:
                    # flush previous partition
                    matching_ellipsis = True
                    if len(partition) > 0:
                        partitions.append((False, partition))
                    partition = [ pat ]
            else:
                partition.append(pat)
                if matching_ellipsis:
                    assert len(partition) > 1
                    matching_ellipsis = False
                    partitions.append((True, partition))
                    partition = []

        if len(partition) > 0:
            if matching_ellipsis:
                partitions.append((True, partition))
            else:
                partitions.append((False, partition))

        return partitions

    def transformPatSequence(self, sequence):
        assert isinstance(sequence, pattern.PatSequence)
        closures = self.closures

        # recursively transform patterns first.
        tseq = []
        for pat in sequence.seq:
            tseq.append( self.transform(pat) )
            
        nseq = []
        partitions = self._partitionseq(tseq)
        for contains_ellipsis, partition in partitions:
            if contains_ellipsis:
                for i in range(len(partition) - 1):
                    pat1, pat2 = partition[i], partition[i+1]
                    if isinstance(pat1, pattern.Repeat):
                        psc = self.PatternStructuralChecker(closures)
                        if isinstance(pat2, pattern.Repeat):
                            p1, p2 = pat1.pat, pat2.pat
                        else:
                            p1, p2 = pat1.pat, pat2
                        if psc.aredifferent(p1, p2):
                            nrep = pattern.Repeat(p1, pattern.RepeatMatchMode.Deterministic).copymetadatafrom(pat1)
                            nseq.append(nrep)
                        else:
                            nseq.append(pat1)
                # append the last unprocessed element
                last = partition[-1]
                if isinstance(last, pattern.Repeat):
                    if not isinstance(last.pat, pattern.InHole):
                        last = pattern.Repeat(last.pat, pattern.RepeatMatchMode.Deterministic).copymetadatafrom(last)
                nseq.append(last)
            else: 
                nseq += partition
        return pattern.PatSequence(nseq).copymetadatafrom(sequence)

class Pattern_EllipsisMatchModeRewriter(EllipsisMatchModeRewriter):
    def __init__(self, definelanguage, pattern, closures):
        super().__init__(definelanguage, closures)
        self.pattern = pattern

    def run(self):
        return self.transform(self.pattern)

class DefineLanguage_EllipsisMatchModeRewriter(EllipsisMatchModeRewriter):
    def __init__(self, definelanguage, closures):
        super().__init__(definelanguage, closures)

    def run(self):
        ntdefs = []
        for nt, ntdef in self.definelanguage.nts.items():
            npats = []
            for pat in ntdef.patterns:
                npat = self.transform(pat)
                npat.copymetadatafrom(pat)
                npats.append(npat)
            ntdefs.append(tlform.DefineLanguage.NtDefinition(ntdef.nt, npats))
        return tlform.DefineLanguage(self.definelanguage.name, ntdefs)
