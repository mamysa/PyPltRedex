class SymGen:
    def __init__(self):
        self.syms = {}

    def get(self, var='tmp'):
        if var not in self.syms:
            self.syms[var] = 0
        val = self.syms[var]
        self.syms[var] += 1
        return '{}{}'.format(var, val)
