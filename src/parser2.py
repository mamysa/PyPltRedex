import ply.lex as lex
import ply.yacc as yacc
import astdefs as ast

import term #as term

reserved = {
    'define-language': 'DEFINELANGUAGE',
    'redex-match'    : 'REDEXMATCH',
    'match-equal?'   : 'MATCHEQUAL',
    'hole'           : 'HOLE',
    'in-hole'        : 'INHOLE',
    '...'            : 'ELLIPSIS',
    '::='            : 'NTDEFINITION',
    'term'           : 'TERM',
    'match'          : 'MATCH',
    'bind'           : 'BIND',
}

tokens = [
    'IDENT',
    'INTEGER',
    'BOOLEAN',
    'LPAREN',
    'RPAREN',
]

tokens = tokens + list(reserved.values())

t_ignore = ' \t'

t_LPAREN = r'\(|\{|\['
t_RPAREN = r'\)|\}|\]'
t_BOOLEAN = r'\#t|\#f'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# From http://www.dabeaz.com/ply/ply.html#ply_nn6
# All tokens defined by functions are added in the same order as they appear in the lexer file. 
# Need to match idents first.
# Also come up with better regex than this - [A-Z][a-z] matching does not include unicode characters.
# TODO (match any symbol except reserved)* (match any symbol except reserved AND digit)+ 
def t_IDENT(t):
    r'([^ \(\)\[\]\{\}\"\'`;\#])*([^ \(\)\[\]\{\}\"\'`;\#0123456789])+([^ \(\)\[\]\{\}\"\'`;\#])*'
    t.type = reserved.get(t.value, 'IDENT')
    return t

def t_INTEGER(t):
    r'[0-9]+'
    return t

def t_error(t):
    raise Exception('illegal character {}'.format(t.value[0]))

def t_comment(t):
    r';[^\n]*'
    pass

# ---------------------DEFINE-LANGUAGE FORM -----------------------
# define-language  ::= (define-language lang-name non-terminal-def ...+)
# non-terminal-def ::= (non-terminal-name ::= pattern ...+)
def p_define_language(t):
    'define-language : LPAREN DEFINELANGUAGE IDENT non-terminal-def-list RPAREN'
    t[0] = ast.DefineLanguage(t[3], t[4])

def p_non_terminal_def_list(t):
    """
    non-terminal-def-list : non-terminal-def-list non-terminal-def
                          | non-terminal-def
    """
    if len(t) == 2:
        t[0] = [t[1]]
    else:
        t[0] = t[1] 
        t[0].append(t[2])

def p_non_terminal_def(t):
    """
    non-terminal-def : LPAREN IDENT NTDEFINITION pattern-list RPAREN
    """
    t[0] = ast.NtDefinition(ast.Nt(t[2], t[2]),  t[4])

def p_pattern_list(t):
    """
    pattern-list : pattern-list pattern
                 | pattern
    """
    if len(t) == 2:
        t[0] = [t[1]]
    else:
        t[0] = t[1] 
        t[0].append(t[2])


#start = 'match-equal'

# --------------------- REDEX-MATCH FORM -----------------------
# redex-match ::= (redex-match lang-name pattern term)
# A bit inflexible at the moment - terms must be 'literal'
def p_redex_match(t):
    'redex-match : LPAREN REDEXMATCH IDENT pattern term-literal-top RPAREN'
    t[0] = ast.RedexMatch(t[3], t[4], t[5])

# --------------------- MATCH-EQUAL? FORM -----------------------
# This form compares output of redex-match with a list of match objects. Not part of PltRedex and 
# used exclusively for testing pattern matching functionality.
# match-equal ::= (match-equal? redex-match match ...) | (match-equal? redex-match () )
def p_match_equal(t):
    """
    match-equal : LPAREN MATCHEQUAL redex-match match-list RPAREN
                | LPAREN MATCHEQUAL redex-match LPAREN RPAREN RPAREN
    """
    if len(t) == 6:
        t[0] = ast.MatchEqual(t[3], t[4])
    else:
        t[0] = ast.MatchEqual(t[3], [])


def p_match_list(t):
    """
    match-list : match-list match
               | match
    """
    if len(t) == 3:
        t[0] = t[1]
        t[0].append(t[2])
    else:
        t[0] = [t[1]]

# --------------------- MATCH -----------------------
# This form creates match objects and used for testing pattern matching. Not part of PltRedex.
# Literal terms are not specified using (term ...) thing, maybe should fix it eventually to be consisitent.
# match ::= (match (bind var literal-term) ...)

def p_match(t):
    """
    match : LPAREN MATCH RPAREN
          | LPAREN MATCH match-bind-list RPAREN
    """
    if len(t) == 4:
        t[0] = ast.Match([])
    else:
        t[0] = ast.Match(t[3])

def p_match_bind_list(t):
    """
    match-bind-list : match-bind-list match-bind
                    | match-bind  
    """
    if len(t) == 3:
        t[0] = t[1]
        t[0].append(t[2])
    else:
        t[0] = [t[1]]

def p_match_bind(t):
    'match-bind : LPAREN BIND IDENT term_literal RPAREN'
    t[0] = (t[3], t[4])

# --------------------- PATTERN -----------------------
# Patterns. Unlike Redex, multiple ellipses appearing in a row are dissallowed on grammar level.
# pattern ::= number 
#           | variable-not-otherwise-mentioned 
#           | (pattern-sequence)
#           | (in-hole pattern pattern)
#           | hole
#           | literal-number
# pattern-under-ellipsis ::= pattern ... | pattern 
# pattern-sequence ::= pattern-under-ellipsis *

# this could be either a built-in pattern or unresolved symbol (which will either become non-terminal 
# or literal variable)
def p_pattern_ident(t):
    'pattern : IDENT'
    prefix = extract_prefix(t[1])
    # do not allow underscores for holes.
    if prefix == 'hole': 
        raise Exception('before underscore must be either a non-terminal or build-in pattern {}'.format(prefix))
    try: 
        case = ast.BuiltInPatKind(prefix).name
        t[0] = ast.BuiltInPat(ast.BuiltInPatKind[case], prefix, t[1])
    except ValueError:
        t[0] = ast.UnresolvedSym(prefix, t[1])

def p_pattern_sequence(t):
    """
    pattern : LPAREN patternsequence RPAREN
            | LPAREN RPAREN 
    """
    if len(t) == 3:
        t[0] = ast.PatSequence([])
    else:
        t[0] = ast.PatSequence(t[2])

def p_pattern_hole(t):
    'pattern : HOLE'
    t[0] = ast.BuiltInPat('hole', ast.BuiltInPatKind.Hole)
      
def p_pattern_inhole(t):
    'in-hole : LPAREN INHOLE pattern pattern RPAREN'
    t[0] = ast.BuiltInPat(ast.BuiltInPatKind.InHole, 'in-hole', 'in-hole', (t[3], t[4]))

def p_pattern_literal_int(t):
    'pattern : INTEGER'
    t[0] = ast.Lit(t[1], ast.LitKind.Integer)


def p_pattern_sequence_contents(t):
    """
    patternsequence : patternsequence pattern-under-ellipsis 
                    | pattern-under-ellipsis 
    """
    if len(t) == 3:
        t[0] = t[1]
        t[0].append(t[2])
    else:
        t[0] = [t[1]]


def p_pattern_under_ellipsis(t):
    """
    pattern-under-ellipsis : pattern ELLIPSIS
                           | pattern
    """
    if len(t) == 2:
        t[0] = t[1]
    else:
        t[0] = ast.Repeat(t[1])


# ---------------------LITERAL TERMS -----------------------
# Parsing 'literal' terms. These will be inserted into output directly using runtime classes.
# E.g. (1 2) -> Sequence([Integer(1), Integer(2)])
# term ::= (term ...) | atom
# atom ::= INTEGER | IDENTIFIER

def p_term_literal_top(t):
    'term-literal-top : LPAREN TERM term_literal RPAREN'
    t[0] = t[3]

def p_term_literal(t):
    """
    term_literal : LPAREN term_literal_list RPAREN 
                 | LPAREN RPAREN
                 | term_literal_atom
    """
    if len(t) == 2:
        t[0] = t[1]
    elif len(t) == 3:
        t[0] = term.TermLiteral(term.TermLiteralKind.List, [])
    else:
        t[0] = term.TermLiteral(term.TermLiteralKind.List, t[2])

def p_term_literal_list(t):
    """
    term_literal_list : term_literal_list term_literal
                      | term_literal
    """
    if len(t) == 3:
        t[0] = t[1]
        t[0].append(t[2])
    else:
        t[0] = [t[1]]

def p_term_literal_atom_integer(t):
    'term_literal_atom : INTEGER'
    t[0] = term.TermLiteral(term.TermLiteralKind.Integer, t[1])

def p_term_literal_atom_identifier(t):
    'term_literal_atom : IDENT'
    t[0] = term.TermLiteral(term.TermLiteralKind.Variable, t[1])

def extract_prefix(token):
        # extract prefix i.e. given symbol n_1 retrieve n.
        # in case of no underscore return token itself
        # So far we are not supporting patterns such as _!_ so this method may work.
        idx = token.find('_')
        if idx == 0:
            raise Exception('define-language: before underscore must be either a non-terminal or build-in pattern {}'.format(tokenvalue))
        if idx == -1:
            return token
        return token[:idx]

lexer = lex.lex()
#lexer.input('hole')
#print(lexer.token())
parser = yacc.yacc(debug=1)
result = parser.parse('(match-equal? (redex-match Lc x (term 1)) ())')
print(result)
