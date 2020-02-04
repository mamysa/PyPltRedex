import enum

def is_lpar(c):
    return c == '('

def is_rpar(c):
    return c == ')'

def is_reserved(c): 
    return c in ['(', ')', '[', ']', '{', '}', '\"', '\'', '`', ';', '#', '|', '\\']

def is_parenthesis(c):
    return c in ['(', ')', '[', ']', '{', '}']

def is_whitespace(c):
    return c == ' ' or c == '\t' or c == '\n' or c == '\r'

def is_newline(c):
    return c == '\n'

def is_digit(c):
    return c >= '0' and c <= '9'

def is_ident(string):
    isnum = True
    for c in string: 
        if not is_digit(c):
            isnum = False
        if is_reserved(c):
            return False
    return not isnum

def is_string(string):
    return string[0] == '\"' and string[-1] == '\"'

#FIXME need to support floating point numbers and fractions later.
def is_number(string):
    for c in string:
        if not is_digit(c):
            return False
    return True

def is_boolean(string):
    return string in ['#t', '#f']



class LiteralKind(enum.Enum):
    Number = 0
    String = 1
    Boolean = 2

class Literal:
    def __init__(self, value, kind):
        self.value = value
        self.kind = kind

    def __repr__(self):
        return 'Literal({}, {})'.format(self.value, self.kind)

#print( repr(Literal("343", LiteralKind.Number)))

# Essentially is reimplementation of redex_spec.split()  but split is not adequate enough 
# for comments and literal strings.
# In case of comments, discard all tokens until the newline.
# In case of string literals, consume all characters until closing double quote is found.
class RedexSpecTokenizer:
    def __init__(self, filename):
        f = open(filename, 'r')
        self.buf = f.read()
        f.close()
        self.tokens = []
        # character offsets.
        self.start = 0
        self.end = 0

    def peek(self):
        if self.end >= len(self.buf):
            return '\0'
        return self.buf[self.end]

    def advance(self):
        self.end += 1

    def get(self):
        token = self.buf[self.start:self.end]
        self.start = self.end
        return token

    def tokenize_string(self):
        self.advance()
        while self.peek() != '\"':
            self.advance()

            if self.peek() == '\0':
                assert False, 'reached EOF while tokenizing a string'

        self.advance()
        self.tokens.append(self.get())

    def tokenize_identifier(self):
        while not is_whitespace(self.peek()) and not is_reserved(self.peek()):
            self.advance()
            if self.peek() == '\0':
                break
        self.tokens.append(self.get())

    def skip_comment(self):
        self.advance()
        while not is_newline(self.peek()):
            self.advance()
            if self.peek() == '\0':
                break
        self.advance()
        self.get()

    def tokenize(self):
        while self.peek() != '\0':

            char = self.peek()
            if is_parenthesis(char):
                self.advance()
                self.tokens.append(self.get())
                continue

            if char == '\"': 
                self.tokenize_string()
                continue

            if char == ';':
                self.skip_comment()
                continue

            if is_whitespace(char):
                self.advance()
                self.get()
                continue

            self.tokenize_identifier()

        return self.tokens


print( RedexSpecTokenizer('tok').tokenize())


















class RedexSpecParser:
    def __init__(self, filename):
        f = open(filename, 'r')
        self.buf = f.read()
        self.cursor = 0
        self.buf = self.buf.replace('(', ' ( ') \
                           .replace(')', ' ) ') \
                           .split()
        #print(self.buf)
        f.close()


    def peek(self):
        if self.cursor < len(self.buf):
            return self.buf[self.cursor]
        assert False, 'unexpected eof'

    def expect(self, tok):
        if self.cursor < len(self.buf) and self.buf[self.cursor] == tok:
            self.cursor += 1
            return
        assert False, 'unexpected ' + tok

    def consume_ident(self):
        isnum = True
        for c in self.buf[self.cursor]:
            if not is_digit(c):
                isnum = False
            if is_reserved(c):
                assert False, 'contains reserved char'
        if isnum:
            assert False, 'is number'

        tok = self.buf[self.cursor]
        self.cursor += 1
        return tok






    # (define-language lang-name non-terminal-def ...)
    def define_language(self):
        self.expect('define-language')
        lang_name = self.consume_ident()
        nts = []
        nts.append(self.non_terminal_def())

        while self.peek() != ')':
            nts.append(self.non_terminal_def())
        self.expect(')')
        return (lang_name, nts)

    # non-terminal-def = (non-terminal-name ::= pattern ...+)
    def non_terminal_def(self):
        self.expect('(')
        not_terminal_name = self.consume_ident()
        self.expect('::=')

        patterns = []
        patterns.append(self.pattern())
        while self.peek() != ')':
            patterns.append(self.pattern())

        self.expect(')')
        return (not_terminal_name, patterns)

    # pattern = number 
    def pattern(self):
        if self.peek() == 'number': 
            self.expect('number')
            return 'number' 

        if self.peek() == 'variable-not-otherwise-mentioned':
            self.expect('variable-not-otherwise-mentioned')
            return 'variable-not-otherwise-mentioned'


        if self.peek() == '(':
            return self.pattern_sequence()

        ident = self.peek()

        if is_number(ident): return Literal(ident, LiteralKind.Number)
        if is_string(ident): return Literal(ident, LiteralKind.String)

        print(ident, is_string(ident))
        if is_boolean(ident): return Literal(ident, LiteralKind.Boolean)
        else:
            return self.consume_ident()


    # pattern-sequence : ( pattern(_id)? (literal ...)?  )
    # FIXME perhaps (_id) should be applied outside pattern_sequence?
    def pattern_sequence(self):
        self.expect('(')

        sequence = []
        while self.peek() != ')':
            pat = self.pattern()
            underscore = pat.find('_')
            if underscore != -1:
                ident = pat[underscore:]
                print(ident)
                if not is_ident(ident):
                    assert False, 'invalid expression after underscore'
                sequence.append(pat[:underscore])
                sequence.append(pat[underscore:])
            else:
                sequence.append(pat)

            if self.peek() == '...':
                self.expect('...')
                sequence.append('...')
        self.expect(')')
        return sequence

    def parse(self):
        self.expect('(')
        if self.peek() == 'define-language':
            return self.define_language()






#print(RedexSpecParser("test2.rkt").parse())
    




