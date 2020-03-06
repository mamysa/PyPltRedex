import enum
import re
import ast
import term

class TokenKind(enum.Enum):
    Integer = 0
    Decimal = 1
    String  = 2
    Boolean = 3
    Ident   = 4
    LParen  = 5
    RParen  = 6


def is_whitespace(c):
    return c == ' ' or c == '\t' or c == '\n' or c == '\r'

def is_newline(c):
    return c == '\n'

def is_reserved(c): 
    return c in ['(', ')', '[', ']', '{', '}', '\"', '\'', '`', ';', '#', '|', '\\']

class Tokenizer:
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
            #TokenKind.Boolean : re.compile('^(#t|#f)$'),
            TokenKind.Ident   : re.compile('^([^\(\)\[\]{}\"\'`;#|\\\])+$'),
        }

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

            # handle boolean as a separate thing for now
            if self.extract_if_contains('#t'): return (TokenKind.Boolean, '#t')
            if self.extract_if_contains('#f'): return (TokenKind.Boolean, '#f')

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

class Parser:
    def __init__(self, filename):
        self.tokenizer = Tokenizer(filename)
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
            return term.Integer(self.expect(TokenKind.Integer))
        if self.peek() == TokenKind.Ident:
            return term.Variable(self.expect(TokenKind.Ident))
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
        return term.Sequence(seq)

    def parse(self):
        if self.peek() == TokenKind.LParen:
            term = self.parse_sequence()
        else: 
            term = self.parse_atom()
        assert self.iseof()
        return term 


import sys

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('no file provided')
        sys.exit(1)

    parser = Parser(sys.argv[1])
    t = parser.parse()
    print(t)
