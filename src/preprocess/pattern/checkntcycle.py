import src.model.pattern as pattern
from src.util import CompilationError

class DefineLanguageNtCycleChecker:
    def __init__(self, definelanguage, successors):
        self.definelanguage = definelanguage
        self.successors = successors
        self.nts = self.definelanguage.ntsyms()

        self.time = 0
        self.d = dict((g, -1) for g in successors.keys()) # discovery time
        self.f = dict((g, -1) for g in successors.keys()) # finish time

    def gettime(self):
        t = self.time 
        self.time += 1
        return t

    def reportcycle(self, path, v):
        idx = path.index(v)
        assert v in self.nts 
        for p in path[idx:]:
            assert p in self.nts
        cyclepath = path[idx:] + [v]
        raise CompilationError('nt cycle {}'.format(cyclepath))

    def visit(self, v, path):
        if self.d[v] == -1: 
            path.append(v)
            self.d[v] = self.gettime()
            for adjv in self.successors.get(v, set([])):
                self.visit(adjv, path)
                if self.f[adjv] == -1:
                    self.reportcycle(path, adjv)
            self.f[v] = self.gettime()
            path.pop()

    def run(self):
        for nt in self.nts:
            self.visit(nt, [])
