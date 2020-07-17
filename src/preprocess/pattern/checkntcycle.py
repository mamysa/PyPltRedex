import src.model.pattern as pattern
from src.util import CompilationError
import enum

class DFSState(enum.IntEnum):
    Undiscovered = 0
    Discovered = 1
    Completed = 2

class DefineLanguage_NtCycleChecker:
    def __init__(self, definelanguage, successors):
        self.definelanguage = definelanguage
        self.successors = successors
        self.nts = self.definelanguage.ntsyms()
        self.color = dict((g, DFSState.Undiscovered) for g in successors.keys())

        self.completednts = set([])

    def reportcycle(self, path, v):
        idx = path.index(v)
        assert v in self.nts 
        for p in path[idx:]:
            assert p in self.nts
        cyclepath = path[idx:] + [v]
        raise CompilationError('nt cycle {}'.format(cyclepath))

    def visit(self, v, path):
        if self.color[v] == DFSState.Undiscovered:
            path.append(v)
            self.color[v] = DFSState.Discovered
            for adjv in self.successors.get(v, set([])):
                self.visit(adjv, path)
            self.color[v] = DFSState.Completed
            self.completednts.add(v)
            path.pop()
        if self.color[v] == DFSState.Discovered:
            self.reportcycle(path, v)

    def run(self):
        nts2visit = set(self.nts)
        while len(nts2visit) != 0:
            self.visit(nts2visit.pop(), [])
            nts2visit.difference_update(self.completednts)
