import ply.lex as lex
import ply.yacc as yacc
import astdefs as ast

import term #as term

reserved = {
    'define-language': 'DEFINELANGUAGE',
    'redex-match'    : 'REDEXMATCH',
    'match-equal?'   : 'MATCHEQUAL',
    'hole'           : 'HOLE',
    '...'            : 'ELLIPSIS',
    '::='            : 'NTDEFINITION'
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


# Patterns. Unlike Redex, multiple ellipses appearing in a row are dissallowed on grammar level.
# pattern ::= number 
#           | variable-not-otherwise-mentioned 
#           | (pattern-sequence)
#           | literal-number
# pattern-under-ellipsis ::= pattern ... | pattern 
# pattern-sequence ::= pattern-under-ellipsis *

# this could be either a built-in pattern or unresolved symbol (which will either become non-terminal 
# or literal variable)
def p_pattern_ident(t):
    'pattern : IDENT'
    prefix = extract_prefix(t[1])
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


# Parsing 'literal' terms. These will be inserted into output directly using runtime classes.
# E.g. (1 2) -> Sequence([Integer(1), Integer(2)])
# term ::= (term ...) | atom
# atom ::= INTEGER | IDENTIFIER
def p_term_literal(t):
    """
    term_literal : LPAREN term_literal_list RPAREN 
                 | term_literal_atom
    """
    if len(t) == 2:
        t[0] = t[1]
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
result = parser.parse('(define-language Lc (e ::= n) (e ::= number))')
print(result)

