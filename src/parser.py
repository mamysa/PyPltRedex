import enum
import re

def is_whitespace(c):
    return c == ' ' or c == '\t' or c == '\n' or c == '\r'

def is_newline(c):
    return c == '\n'

def is_reserved(c): 
    return c in ['(', ')', '[', ']', '{', '}', '\"', '\'', '`', ';', '#', '|', '\\']

class TokenKind(enum.Enum):
    Integer = 0
    Decimal = 1
    String  = 2
    Boolean = 3
    Ident   = 4
    LParen  = 5
    RParen  = 6

class Literal:
    def __init__(self, value, kind):
        self.value = value
        self.kind = kind

    def __repr__(self):
        return 'Literal({}, {})'.format(self.value, self.kind)

#print( repr(Literal("343", LiteralKind.Number)))

class RedexSpecParser:

    # Essentially is reimplementation of redex_spec.split()  but split is not adequate enough 
    # for comments and literal strings.
    # In case of comments, discard all tokens until the newline.
    # In case of string literals, consume all characters until closing double quote is found.
    # FIXME perhaps shouldn't use \0 to indicate eof?
    class RedexSpecTokenizer:
        def __init__(self, filename):
            f = open(filename, 'r')
            self.buf = f.read()
            f.close()
            # character offsets.
            self.start = 0
            self.end = 0

            # Order sensitive, Ident may also match integers and decimals.
            # ^ and $ anchor to the beginning and end. 
            # Identifiers must not contain the following reserved characters:
            # ( ) [ ] { } " , ' ` ; # | \
            self.matchers = {
                TokenKind.Integer : re.compile('^-?[0-9]+$'),
                TokenKind.Decimal : re.compile('^-?[0-9]*\.[0-9]+$'),
                TokenKind.Boolean : re.compile('^(#t|#f)$'),
                TokenKind.Ident   : re.compile('^([^\(\)\[\]{}\"\'`;#|\\\])+$'),
            }

        def advance(self):
            self.end += 1

        def peek(self):
            if self.end >= len(self.buf):
                return '\0'
            return self.buf[self.end]

        def extract(self):
            token = self.buf[self.start:self.end]
            self.start = self.end
            return token

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
                        self.advance()
                        if self.peek() == '\\':
                            self.advance()
                            self.advance()
                        if self.peek() == '\0':
                            assert False, 'reached EOF while tokenizing a string'
                    self.advance()
                    return (TokenKind.String, self.extract())

                # otherwise, read until the next whitespace and identify the token 
                # can be a number, identifier, etc.
                # TODO confused as to what #lang is. 
                while not (is_whitespace(self.peek()) or is_reserved(self.peek())) :
                    self.advance()
                    if self.peek() == '\0':
                        break
                tok = self.extract()

                for kind, matcher in self.matchers.items():
                    if matcher.match(tok): 
                        return (kind, tok)
                assert False, 'unknown token ' + tok
            return None
    
    def __init__(self, filename):
        self.tokenizer = self.RedexSpecTokenizer(filename)
        self.nexttoken = self.tokenizer.next()

    def peek(self):
        if self.nexttoken == None:
            assert False, 'reached EOF'
        return self.nexttoken[0]
        assert False, 'unexpected eof'

    def peekv(self):
        if self.nexttoken == None:
            assert False, 'reached EOF'
        return self.nexttoken
        assert False, 'unexpected eof'

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

    # (define-language lang-name non-terminal-def ...)
    def define_language(self):
        self.expect(TokenKind.Ident, 'define-language')
        lang_name = self.expect(TokenKind.Ident)

        nts = []
        nts.append(self.non_terminal_def())

        while self.peek() != TokenKind.RParen:
            nts.append(self.non_terminal_def())
        self.expect(TokenKind.RParen)
        return (lang_name, nts)

    # non-terminal-def = (non-terminal-name ::= pattern ...+)
    def non_terminal_def(self):
        self.expect(TokenKind.LParen)
        not_terminal_name = self.expect(TokenKind.Ident) 
        self.expect(TokenKind.Ident, '::=')

        patterns = []
        patterns.append(self.pattern())
        while self.peek() != TokenKind.RParen:
            patterns.append(self.pattern())
        self.expect(TokenKind.RParen)
        return (not_terminal_name, patterns)

    # pattern = number 
    def pattern(self):
        tokenkind, tokenvalue = self.peekv()
        
        if tokenkind == TokenKind.Ident:
            if tokenvalue == 'number': 
                self.expect(TokenKind.Ident)
                return 'number'
            if tokenvalue == 'variable-not-otherwise-mentioned':
                self.expect(TokenKind.Ident)
                return 'variable-not-otherwise-mentioned'

        if tokenkind == TokenKind.LParen:
            return self.pattern_sequence()

        if tokenkind == TokenKind.Integer: 
            ident = self.expect(tokenkind)
            return Literal(ident, TokenKind.Integer)
        if tokenkind == TokenKind.Decimal: 
            ident = self.expect(tokenkind)
            return Literal(ident, TokenKind.Decimal)
        if tokenkind == TokenKind.String : 
            ident = self.expect(tokenkind)
            return Literal(ident, TokenKind.String)
        if tokenkind == TokenKind.Boolean: 
            ident = self.expect(tokenkind)
            return Literal(ident, TokenKind.Boolean)
        else:
            # not an obvious case, could be either non-terminal or literal,
            # need a set of non-terminals to decide.
            self.expect(TokenKind.Ident)
            return tokenvalue 


    # pattern-sequence : ( pattern(_id)? (literal ...)?  )
    # FIXME perhaps (_id) should be applied outside pattern_sequence?
    def pattern_sequence(self):
        self.expect(TokenKind.LParen)
        sequence = []
        while self.peek() != TokenKind.RParen:
            pat = self.pattern()
            
            """
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
            """
            sequence.append(pat)
            tokenkind, tokenvalue = self.peekv()
            if tokenvalue == '...':
                self.expect(TokenKind.Ident)
                sequence.append(tokenvalue)
        self.expect(TokenKind.RParen)
        return sequence

    def parse(self):
        self.expect(TokenKind.LParen)

        tokenkind, tokenvalue = self.peekv()
        
        if tokenvalue == 'define-language':
            return self.define_language()






print(RedexSpecParser("test2.rkt").parse())
    




