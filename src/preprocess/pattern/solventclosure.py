import src.model.tlform as tlform
import src.model.pattern as pattern
import copy

class DefineLanguage_NtClosureSolver:
    def __init__(self, definelanguage):
        assert isinstance(definelanguage, tlform.DefineLanguage)
        self.definelanguage = definelanguage

    def run(self):
        # compute initial sets.
        closureof = {}
        closureof['number'] = set([])
        closureof['hole'] = set([])
        closureof['variable-not-otherwise-mentioned'] = set([])
        for ntdef in self.definelanguage.nts.values():
            syms = []
            assert isinstance(ntdef, tlform.DefineLanguage.NtDefinition)
            for pat in ntdef.patterns:
                if isinstance(pat, pattern.Nt):
                    syms.append(pat.prefix)
                if isinstance(pat, pattern.BuiltInPat):
                    syms.append(pat.prefix)
            closureof[ntdef.get_nt_sym()] = set(syms)
        x = copy.deepcopy(closureof)

        # iteratively compute closure.
        changed = True
        while changed:
            changed = False
            for sym, closure in closureof.items():
                for elem in closure:
                    closureof_elem = closureof.get(elem, set([])) # might be built-in pattern.
                    closureof_sym = closure.union(closureof_elem)
                    if closureof_sym != closure:
                        changed = True
                    closure = closureof_sym 
                closureof[sym] = closure
        return x, closureof
