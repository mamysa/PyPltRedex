class SourceWriter:
    def __init__(self):
        self.indents = 0
        self.buf = []
        self.should_insert_tabs = True 

    def indent(self):
        self.indents += 1
        return self

    def dedent(self):
        self.indents -= 1
        assert self.indents >= 0
        return self

    def newline(self):
        self.buf.append('\n')
        self.should_insert_tabs = True
        return self
    
    def __iadd__(self, string):
        if self.should_insert_tabs:
            self.buf.append(' '*self.indents*4)
            self.should_insert_tabs = False
        self.buf.append(string)
        return self

    def build(self):
        return ''.join(self.buf)

class Var:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

