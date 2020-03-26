import enum
import re

import src.astdefs as ast

import src.preprocdefinelang

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
    
class RedexSpecParser:
    # Essentially is reimplementation of redex_spec.split()  but split is not adequate enough 
    # for comments and literal strings.
    # In case of comments, discard all tokens until the newline.
    # In case of string literals, consume all characters until closing double quote is found.
    # FIXME perhaps shouldn't use \0 to indicate eof?
    class RedexSpecTokenizer:
        def __init__(self, filename, is_filename):
            if is_filename:
                f = open(filename, 'r')
                self.buf = f.read()
                f.close()
            else:
                self.buf = filename
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

        def extract_chars_until_matching_rparen(self):
            depth = 0
            ch = self.peek()
            while ch:
                if ch == '\0':
                    assert False, 'unbalanced lparen'
                if ch == ')':
                    if depth == 0:
                        break
                    depth -= 1
                if ch == '(':
                    depth += 1
                self.advance()
                ch = self.peek()
            return self.extract()

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
    
    def __init__(self, filename, is_filename=True):
        self.tokenizer = self.RedexSpecTokenizer(filename, is_filename)
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
                    assert False, 'unexpected ' + str(kind)
            else:
                ret = self.nexttoken
                self.nexttoken = self.tokenizer.next()
                return ret[1]
        assert False, 'unexpected {}, actual {}'.format(str(kind), str(self.nexttoken[0]))

    # (define-language lang-name non-terminal-def ...)
    def define_language(self):
        self.expect(TokenKind.Ident, 'define-language')
        lang_name = self.expect(TokenKind.Ident)

        nts = {} # TODO decide on a single representation, either use dict or a list of Nt
        nt, ntdef = self.non_terminal_def()
        nts[nt] = ntdef

        while self.peek() != TokenKind.RParen:
            nt, ntdef = self.non_terminal_def()
            if nt in nts.keys():
                raise Exception('define-language: same non-terminal defined twice {}'.format(nt))
            nts[nt] = ntdef 
        self.expect(TokenKind.RParen)
        return ast.DefineLanguage(lang_name, nts)

    def redex_match(self):
        self.expect(TokenKind.Ident, 'redex-match')
        langname = self.expect(TokenKind.Ident)
        pattern  = self.pattern()

        #( term ...)
        self.expect(TokenKind.LParen)
        tok, val = self.peekv() 
        if val != 'term':
            assert False, 'term expected'
        termstr = self.tokenizer.extract_chars_until_matching_rparen().strip()
        self.nexttoken = self.tokenizer.next() # very hacky but oh well :)
        self.expect(TokenKind.RParen)

        self.expect(TokenKind.RParen)
        return ast.RedexMatch(langname, pattern, termstr)

    # non-terminal-def = (non-terminal-name ::= pattern ...+)
    def non_terminal_def(self):
        self.expect(TokenKind.LParen)
        not_terminal_name = self.expect(TokenKind.Ident) 
        if not_terminal_name.find('_') != -1:
            raise Exception('define-language: cannot use _ in a non-terminal name {}'.format(not_terminal_name))

        self.expect(TokenKind.Ident, '::=')

        patterns = []
        patterns.append(self.pattern())
        while self.peek() != TokenKind.RParen:
            patterns.append(self.pattern())
        self.expect(TokenKind.RParen)
        return not_terminal_name, ast.NtDefinition(ast.Nt(not_terminal_name, not_terminal_name), patterns)

    # pattern = number 
    def pattern(self):
        tokenkind, tokenvalue = self.peekv()
        
        if tokenkind == TokenKind.LParen:
            return self.pattern_sequence()
        if tokenkind == TokenKind.Integer: 
            ident = self.expect(tokenkind)
            return ast.Lit(ident, ast.LitKind.Integer)
        if tokenkind == TokenKind.Decimal: 
            ident = self.expect(tokenkind)
            return ast.Lit(ident, ast.LitKind.Decimal)
        if tokenkind == TokenKind.String : 
            ident = self.expect(tokenkind)
            return ast.Lit(ident, ast.LitKind.String)
        if tokenkind == TokenKind.Boolean: 
            ident = self.expect(tokenkind)
            return ast.Lit(ident, ast.LitKind.Boolean)
        else:
            # not an obvious case, could be either non-terminal or literal,
            # need a set of non-terminals to decide.
            self.expect(TokenKind.Ident)
            prefix = self.extract_prefix(tokenvalue)
            # disregard prefixes in patterns defined in define-language.
            try:
                case = ast.BuiltInPatKind(prefix).name
                # FIXME investigate redex-match Lc hole_1 (term hole), seems like hole doesnt allow suffixes although it is 
                # a built-in pat? 
                # Need to move such logic into a separate pass.
                if prefix == 'hole' and prefix != tokenvalue: 
                    raise Exception('before underscore must be either a non-terminal or build-in pattern {}'.format(prefix))
                return ast.BuiltInPat(ast.BuiltInPatKind[case], prefix, tokenvalue)
            except ValueError:
                if tokenvalue.startswith('...'):
                    raise Exception('found ellipsis outside of a sequence')
                return ast.UnresolvedSym(prefix, tokenvalue)
            
    def extract_prefix(self, token):
        # extract prefix i.e. given symbol n_1 retrieve n.
        # in case of no underscore return token itself
        # So far we are not supporting patterns such as _!_ so this method may work.
        idx = token.find('_')
        if idx == 0:
            raise Exception('define-language: before underscore must be either a non-terminal or build-in pattern {}'.format(tokenvalue))
        if idx == -1:
            return token
        return token[:idx]

    # pattern-sequence : ( pattern(_id)? (literal ...)?  )
    # FIXME perhaps (_id) should be applied outside pattern_sequence?
    def pattern_sequence(self):
        self.expect(TokenKind.LParen)
        sequence = []
        while self.peek() != TokenKind.RParen:
            pat = self.pattern()
            tokenkind, tokenvalue = self.peekv()
            if tokenvalue == '...':
                self.expect(TokenKind.Ident)
                pat = ast.Repeat(pat)
            sequence.append(pat)
        self.expect(TokenKind.RParen)
        return ast.PatSequence(sequence) 

    def parse(self):
        redexmatches = []
        definelanguage = None
        while self.nexttoken != None:
            self.expect(TokenKind.LParen)
            #print(self.nexttoken)
            tokenkind, tokenvalue = self.peekv()
            if tokenvalue == 'define-language':
                definelanguage = self.define_language()
            if tokenvalue == 'redex-match':
                redexmatches.append(self.redex_match())

        for redexmatch in redexmatches:
            if definelanguage == None or redexmatch.languagename != definelanguage.name:
                assert False, 'undefined language ' + redexmatch.languagename
        return ast.Module(definelanguage, redexmatches)
