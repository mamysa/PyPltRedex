class TermLiteralKind:
    Integer = 0
    Variable = 1
    Hole = 2
    List = 3

class TermLiteral:
    def __init__(self, kind, value):
        self.kind = kind
        self.value = value

    def __repr__(self):
        if self.kind in [TermLiteralKind.Integer, TermLiteralKind.Variable, TermLiteralKind.Hole]: 
            return str(self.value)
        # is a list, 
        return '({})'.format(' '.join(map(repr, self.value)))
