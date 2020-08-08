from rpython.rlib.parsing.regexparse import make_runner as compile_regex

class TokenKind:
    Integer = 0
    Float   = 1
    String  = 2
    Boolean = 3
    Ident   = 4
    LParen  = 5
    RParen  = 6
    Hole    = 7
    EOF     = 8

def is_whitespace(c):
    return c == ' ' or c == '\t' or c == '\n' or c == '\r'

def is_newline(c):
    return c == '\n'

def is_reserved(c): 
    return c in ['(', ')', '[', ']', '{', '}', '\"', '\'', '`', ';', '#', '|', '\\']

def is_digit(c):
    return c in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

def is_plusminus(c):
    return c in ['-', '+']

def is_delimeteter(c):
    return is_reserved(c) or c == '\0' or is_whitespace(c)


reserved_variables = ['in-hole']

class Tokenizer:
    def __init__(self, string):
        self.buf = string
        # character offsets.
        self.start = 0
        self.end = 0

    def advance(self):
        self.end += 1

    def peek(self):
        if self.end >= len(self.buf):
            return '\0'
        return self.buf[self.end]

    def extract_if_contains(self, substr):
        endidx = self.start + len(substr) 
        if endidx > len(self.buf):
            return False
        if substr == self.buf[self.start:endidx]:
            self.start = endidx
            self.end   = endidx
            return True 
        return False 

    def extract(self):
        token = self.buf[self.start:self.end]
        self.start = self.end
        return token

# -------BEGIN state machine for Integer/Float/Identifier
    def state1(self):
        c = self.peek()
        if is_plusminus(c):
            return self.state2()
        if c == '.':
            raise Exception()
        if is_digit(c):
            return self.state3()
        return self.state6()

    def state2(self):
        self.advance() # consume + or -
        c = self.peek()
        if is_digit(c):
            return self.state3()
        if is_delimeteter(c):
            return self.accept_ident()
        return self.state6()
        
    def state3(self):
        self.advance() # consume digit
        while is_digit(self.peek()):
            self.advance()
        c = self.peek()
        if is_delimeteter(c):
            return self.accept_int()
        if c == '.':
            return self.state4()
        return self.state6()

    def state4(self):
        self.advance() # consume .
        c = self.peek()
        if is_digit(c):
            return self.state5()
        if is_delimeteter(c):
            raise Exception()
        return self.state6()

    def state5(self):
        self.advance() # consume digit
        while is_digit(self.peek()):
            self.advance()
        c = self.peek()
        if is_delimeteter(c):
            return self.accept_float()
        return self.state6()

    def state6(self):
        self.advance() # consume non-reserved symbol
        while not is_delimeteter(self.peek()):
            self.advance()
        return self.accept_ident()

    def accept_ident(self):
        return (TokenKind.Ident, self.extract())

    def accept_int(self):
        return (TokenKind.Integer, self.extract())

    def accept_float(self):
        return (TokenKind.Float, self.extract())

# ------- END state machine for Integer/Float/Identifier
    def next(self):
        while self.peek() != '\0':

            # skip whitespace
            char = self.peek()
            if is_whitespace(char):
                self.advance()
                self.extract()
                continue
            
            # comments
            if char == ';':
                self.advance()
                while not is_newline(self.peek()):
                    self.advance()
                    if self.peek() == '\0':
                        break
                self.advance()
                self.extract()
                continue

            # various parentheses / braces / etc
            if char in ['(', '[', '{']:
                self.advance()
                return (TokenKind.LParen, self.extract())

            if char in [')', ']', '}']:
                self.advance()
                return (TokenKind.RParen, self.extract())

            # string literal
            if char == '\"': 
                self.advance()
                while self.peek() != '\"':
                    if self.peek() == '\\':
                        self.advance()
                        self.advance()
                    else:
                        self.advance()
                    if self.peek() == '\0':
                        assert False, 'reached EOF while tokenizing a string'
                self.advance()
                return (TokenKind.String, self.extract())

            if char == '#':
                if self.extract_if_contains('#true') : return (TokenKind.Boolean, '#t')
                if self.extract_if_contains('#t')    : return (TokenKind.Boolean, '#t')
                if self.extract_if_contains('#false'): return (TokenKind.Boolean, '#f')
                if self.extract_if_contains('#f')    : return (TokenKind.Boolean, '#f')
                assert False, 'using reserved symbol #'

            # otherwise, read until the next whitespace and identify the token 
            # can be a number, identifier, etc.
            if not is_delimeteter(self.peek()):
                return self.state1()

            assert False, 'unknown token kind'

        return None #(TokenKind.EOF, '')

class Parser:
    def __init__(self, string):
        self.tokenizer = Tokenizer(string)
        self.nexttoken = self.tokenizer.next()

    def peek(self):
        if self.nexttoken == None:
            assert False, 'reached EOF'
        return self.nexttoken[0]

    def iseof(self):
        return self.nexttoken == None

    def peekv(self):
        if self.nexttoken == None:
            assert False, 'reached EOF'
        return self.nexttoken

    def expect(self, kind, tok=None):
        if self.nexttoken == None:
            assert False, 'reached EOF'

        if self.nexttoken[0] == kind:
            if tok != None:
                if self.nexttoken[1] == tok: 
                    ret = self.nexttoken
                    self.nexttoken = self.tokenizer.next()
                    return ret[1]
                else:
                    assert False, 'unexpected ' + tok
            else:
                ret = self.nexttoken
                self.nexttoken = self.tokenizer.next()
                return ret[1]
        assert False, 'unexpected ' + tok

    def parse_atom(self):
        if self.peek() == TokenKind.Integer:
            return Integer(int(self.expect(TokenKind.Integer)))
        if self.peek() == TokenKind.Float:
            return Float(float(self.expect(TokenKind.Float)))
        if self.peek() == TokenKind.String:
            string = self.expect(TokenKind.String)
            return String(string)
        if self.peek() == TokenKind.Boolean:
            boolean = self.expect(TokenKind.Boolean)[0:2]
            return Boolean(boolean)
        if self.peek() == TokenKind.Ident:
            tokkind, tokval = self.peekv() 
            if tokval == 'hole':
                self.expect(TokenKind.Ident)
                return Hole()
            if tokval in reserved_variables:
                raise Exception('usage of reserved variable ' + tokval)
            return Variable(self.expect(TokenKind.Ident))
        assert False, 'unreachable'

    def parse_sequence(self):
        self.expect(TokenKind.LParen)
        seq = []
        while self.peek() != TokenKind.RParen:
            if self.peek() == TokenKind.LParen:
                seq.append(self.parse_sequence())
            else:  
                seq.append(self.parse_atom())
        self.expect(TokenKind.RParen)
        sequence = Sequence(seq)
        return sequence

    def parse(self):
        if self.peek() == TokenKind.LParen:
            term = self.parse_sequence()
        else: 
            term = self.parse_atom()
        assert self.iseof()
        return term
