import ply.lex as lex
import ply.yacc as yacc

import src.model.tlform as tlform
import src.model.pattern as pat
import src.model.term as term

import os

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
    'assert-term-eq' : 'ASSERTTERMEQ',
    ','              : 'COMMA',
    ',@'             : 'COMMAATSIGN',
    '->'             : 'LEFTARROW',
    '-->'            : 'ARROW',
    ':'              : 'COLON',
    'define-reduction-relation' : 'DEFINEREDUCTIONRELATION',
    'define-metafunction' : 'DEFINEMETAFUNCTION',
    'require-python-source' : 'REQUIREPYTHONSOURCE',
    'apply-reduction-relation' : 'APPLYREDUCTIONRELATION',
    'assert-term-lists-equal' : 'ASSERTTERMLISTSEQUAL',
}

tokens = [
    'IDENT',
    'INTEGER',
    'BOOLEAN',
    'LPAREN',
    'RPAREN',
    'STRING',
    'REDDOMAIN',
]


tokens = tokens + list(reserved.values())

# FIXME double quotes " in comments raise parse error? why?
def t_comment(t):
    r';[^\n]*'

t_ignore = ' \t'
t_LPAREN = r'\(|\{|\['
t_RPAREN = r'\)|\}|\]'
t_BOOLEAN = r'\#t|\#f'
t_REDDOMAIN = '\#:domain' 

def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# From http://www.dabeaz.com/ply/ply.html#ply_nn6
# All tokens defined by functions are added in the same order as they appear in the lexer file. 
# Need to match idents first.
# Also come up with better regex than this - [A-Z][a-z] matching does not include unicode characters.
# TODO (match any symbol except reserved)* (match any symbol except reserved AND digit)+ 

def t_STRING(t):
    r'\"([^\"]|\\")*\"'
    return t

def t_IDENT(t):
    r'([^ \(\)\[\]\{\}\"\'`;\#\n])*([^ \(\)\[\]\{\}\"\'`;\#0123456789\n])+([^ \(\)\[\]\{\}\"\'`;\#\n])*'
    t.type = reserved.get(t.value, 'IDENT')
    return t

def t_INTEGER(t):
    r'[0-9]+'
    return t

def t_error(t):
    raise Exception('illegal character {}'.format(t.value[0]))

def trimstringlit(lit):
    #print(lit, lit[-1])
    assert lit[0] == '"' and lit[-1] == '"' 
    return lit[1:-1]#.encode('unicode-escape')

# --------------------- TOP-LEVEL -----------------------
# module ::= define-language (redex-match match-equals)...

start = 'module'

def p_module(t):
    'module : top-level-form-list'
    t[0] = tlform.Module(t[1]) 

def p_top_level_form_list(t):
    """
    top-level-form-list : top-level-form-list top-level-form
                        | top-level-form
    """
    if len(t) == 2:
        t[0] = [t[1]]
    else:
        t[0] = t[1]
        t[0].append(t[2])

def p_top_level_form(t):
    """
    top-level-form : define-language
                   | redex-match
                   | match-equal
                   | assert-term-eq
                   | require-python-source
                   | define-reduction-relation
                   | apply-reduction-relation
                   | assert-term-lists-equal
                   | define-metafunction
    """
    t[0] = t[1]

# ---------------------REQUIRE-PYTHON-SOURCE FORM-----------------------

def p_require_python_source(t):
    'require-python-source : LPAREN REQUIREPYTHONSOURCE STRING RPAREN'
    filename = trimstringlit(t[3]) 
    assert os.path.isfile(filename)
    t[0] = tlform.RequirePythonSource(filename)

# ---------------------DEFINE-LANGUAGE FORM -----------------------
# define-language  ::= (define-language lang-name non-terminal-def ...+)
# non-terminal-def ::= (non-terminal-name ::= pattern ...+)
def p_define_language(t):
    'define-language : LPAREN DEFINELANGUAGE IDENT non-terminal-def-list RPAREN'
    t[0] = tlform.DefineLanguage(t[3], t[4])

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
    t[0] = tlform.DefineLanguage.NtDefinition(pat.Nt(t[2], t[2]),  t[4])

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

# --------------------- DEFINE-METAFUNCTION-----------------
# define-metafunction ::=  ( define-metafunction IDENT metafunction-contract metafunction-case ... )
# metafunction-contract ::= IDENT : pattern-sequence ...  -> pattern
# metafunction-case ::= [ (IDENT pattern ...) term-template ]
def p_define_metafunction(p):
    """
    define-metafunction : LPAREN DEFINEMETAFUNCTION IDENT metafunction-contract metafunction-case-list RPAREN
    """
    p[0] = tlform.DefineMetafunction(p[3], p[4], p[5])


def p_define_metafunction_contract(p):
    """
    metafunction-contract : IDENT COLON LEFTARROW pattern
                         | IDENT COLON pattern-sequence LEFTARROW pattern
    """
    if len(p) == 5:
        p[0] = tlform.DefineMetafunction.MetafunctionContract(p[1], [], p[4])
    else:
        p[0] = tlform.DefineMetafunction.MetafunctionContract(p[1], p[3], p[5])

def p_metafunction_case_list(t):
    """
    metafunction-case-list : metafunction-case-list metafunction-case 
                           | metafunction-case 
    """
    if len(t) == 2:
        t[0] = [t[1]]
    else:
        t[0] = t[1] 
        t[0].append(t[2])

def p_metafunction_case(p):
    """
    metafunction-case : LPAREN LPAREN IDENT RPAREN term-template RPAREN
                      | LPAREN LPAREN IDENT pattern-sequence RPAREN term-template RPAREN
    """
    if len(p) == 7:
        p[0] = tlform.DefineMetafunction.MetafunctionCase(p[3], [], p[5])
    else:
        p[0] = tlform.DefineMetafunction.MetafunctionCase(p[3], p[4], p[6])

# --------------------- DEFINE-REDUCTION-RELATION FORM ---------
# define-reduction-relation ::= ( define-reduction-relation IDENT IDENT domain reduction-case ... )
# reduction-case ::= (--> pattern term-template STRING)
# domain ::= #:domain pattern
def p_define_reduction_relation(t):
    """
    define-reduction-relation : LPAREN DEFINEREDUCTIONRELATION IDENT IDENT domain reduction-case-list RPAREN
    define-reduction-relation : LPAREN DEFINEREDUCTIONRELATION IDENT IDENT reduction-case-list RPAREN
    """
    if len(t) == 8:
        t[0] = tlform.DefineReductionRelation(t[3], t[4], t[5], t[6])
    else:
        t[0] = tlform.DefineReductionRelation(t[3], t[4], None, t[5])

def p_define_reduction_relation_domain(t):
    'domain : REDDOMAIN pattern'
    t[0] = t[2]

def p_reduction_case_list(t):
    """
    reduction-case-list : reduction-case-list reduction-case
                        | reduction-case 
    """
    if len(t) == 2:
        t[0] = [t[1]]
    else:
        t[0] = t[1] 
        t[0].append(t[2])

def p_reduction_case(t):
    """
    reduction-case : LPAREN ARROW pattern term-template STRING RPAREN
    """
    t[0] = tlform.DefineReductionRelation.ReductionCase(t[3], t[4], trimstringlit(t[5]))


# --------------------- APPLY-REDUCTION-RELATION FORM -----------------------
# apply-reduction-relation : (apply-reduction-relation IDENT term-template-top)
def p_apply_reduction_relation(p):
    'apply-reduction-relation : LPAREN APPLYREDUCTIONRELATION IDENT term-template-top RPAREN'
    p[0] = tlform.ApplyReductionRelation(p[3], p[4])


# --------------------- REDEX-MATCH FORM -----------------------
# redex-match ::= (redex-match lang-name pattern term)
# A bit inflexible at the moment - terms must be 'literal'
def p_redex_match(t):
    'redex-match : LPAREN REDEXMATCH IDENT pattern term-template-top RPAREN'
    t[0] = tlform.RedexMatch(t[3], t[4], t[5])

# --------------------- TERM-LET FORM -----------------------
# term-let ::= (term-let ([tl-pat literal-term] ...) term-template)
# tl-pat ::= identifier ( tl_pat_ele )
# tl-pat-ele : tl_pat | tl_pat ELLPISIS 

def p_assert_term_eq(t):
    """
    assert-term-eq : LPAREN ASSERTTERMEQ LPAREN variable-assignment-list RPAREN term-template-top term-template-top RPAREN
                   | LPAREN ASSERTTERMEQ LPAREN RPAREN term-template-top term-template-top RPAREN
    """
    variabledepths = {} 
    variableassignments = {}
    if len(t) == 8:
        t[0] = tlform.AssertTermsEqual(variabledepths, variableassignments, t[5], t[6])
    else:
        for sym, (depth, term) in t[4].items():
            variabledepths[sym] = depth
            variableassignments[sym] = term
        t[0] = tlform.AssertTermsEqual(variabledepths, variableassignments, t[6], t[7])

def p_variable_assignment_list(t):
    """
    variable-assignment-list : variable-assignment-list variable-assignment 
                             | variable-assignment 
    """
    if len(t) == 3:
        ident, depth, term = t[2]
        if ident in t[1].keys():
            raise Exception('{} mentioned twice'.format(ident))
        t[0] = t[1]
        t[0][ident] = (depth, term) 
    else:
        t[0] = {}
        ident, depth, term = t[1]
        t[0][ident] = (depth, term) 

# Seeing that variables under ellipsis are flat (i.e. no arbitrary list nesting) 
# provide ellipsis depth instead of tl-pat. Ellipsis depth is known at compile time. 
# FIXME rename the form to something else?
def p_variable_assignment(t):
    'variable-assignment : LPAREN IDENT INTEGER term-template-top RPAREN'
    t[0] = (t[2], int(t[3]), t[4])

def p_tl_pat(t):
    """
    tl-pat : IDENT
           | LPAREN tl-pat-ele RPAREN
    """
    if len(t) == 2:
        t[0] = pat.Nt(t[1], t[1])
    else:
        t[0] = pat.PatSequence(t[2])

def p_tl_pat_ele(t):
    """
    tl-pat-ele : tl-pat
               | tl-pat ELLIPSIS
    """
    if len(t) == 2:
        t[0] = t[1]
    else:
        t[0] = pat.Repeat(t[1])


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
        t[0] = tlform.MatchEqual(t[3], t[4])
    else:
        t[0] = tlform.MatchEqual(t[3], [])


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

# --------------------- ASSERT-TERM-LISTS-EQUAL FORM -----------------------
# assert-term-lists-equal ::= ( apply-reduction-relation literal-term-list )
# literal'
def p_assert_term_lists_equal(p):
    'assert-term-lists-equal : LPAREN ASSERTTERMLISTSEQUAL apply-reduction-relation listof-terms RPAREN'
    p[0] = tlform.AssertTermListsEqual(p[3], p[4])

def p_listof_literal_terms(t):
    """
    listof-terms : LPAREN literal-term-list RPAREN
                          | LPAREN RPAREN
    """
    if len(t) == 4:
        t[0] = t[2]
    else:
        t[0] = []

def p_literalterm_list(t):
    """
    literal-term-list : literal-term-list term-template-top 
                      | term-template-top
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
        t[0] = tlform.MatchEqual.Match([])
    else:
        t[0] = tlform.MatchEqual.Match(t[3])

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
    'match-bind : LPAREN BIND IDENT term-template RPAREN'
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
        case = pat.BuiltInPatKind(prefix).name
        t[0] = pat.BuiltInPat(pat.BuiltInPatKind[case], prefix, t[1])
    except ValueError:
        t[0] = pat.UnresolvedSym(prefix, t[1])

def p_pattern_sequence(t):
    """
    pattern : LPAREN pattern-sequence RPAREN
            | LPAREN RPAREN 
    """
    if len(t) == 3:
        t[0] = pat.PatSequence([])
    else:
        t[0] = pat.PatSequence(t[2])

def p_pattern_hole(t):
    'pattern : HOLE'
    t[0] = pat.BuiltInPat(pat.BuiltInPatKind.Hole, 'hole', 'hole')
      
def p_pattern_inhole(t):
    'pattern : LPAREN INHOLE pattern pattern RPAREN'
    t[0] = pat.InHole(t[3], t[4])

def p_pattern_literal_int(t):
    'pattern : INTEGER'
    t[0] = pat.Lit(t[1], pat.LitKind.Integer)


def p_pattern_sequence_contents(t):
    """
    pattern-sequence : pattern-sequence pattern-under-ellipsis 
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
        t[0] = pat.Repeat(t[1])

# ---------------------TERM TEMPLATES -----------------------
# Things that look like terms but instead are compiled into code.
# To be used with term-let and similar.
# term-tempate-top ::= (TERM term-tempate)
# term-template    ::= ( term-sequence ) 
#                    | number
#                    | ident
# term-under-ellipsis ::= term-template ... | term-template 
# term-sequence ::= term-under-ellipsis *

def p_term_template_top(t):
    'term-template-top : LPAREN TERM term-template RPAREN'
    t[0] = t[3]

def p_term_template(t):
    """
    term-template : LPAREN term-template-list RPAREN 
                  | LPAREN RPAREN
    """
    if len(t) == 3:
        t[0] = term.TermSequence([])
    else: 
        t[0] = term.TermSequence(t[2])

def p_term_template_inhole(t):
    'term-template : LPAREN INHOLE term-template term-template RPAREN'
    t[0] = term.InHole(t[3], t[4])

def p_term_template_integer(t):
    'term-template : INTEGER'
    t[0] = term.TermLiteral(term.TermLiteralKind.Integer, t[1])

def p_term_template_hole(t):
    'term-template : HOLE'
    t[0] = term.TermLiteral(term.TermLiteralKind.Hole, t[1])

def p_term_pycall_append_list(t):
    'term-template : COMMA LPAREN IDENT list-of-term-template-top RPAREN'
    t[0] = term.PyCall(term.PyCallInsertionMode.Append, t[3], t[4])

def p_term_template_unresolved(t):
    'term-template : IDENT'
    t[0] = term.UnresolvedSym(t[1])

def p_list_of_template_list_top(t):
    """
    list-of-term-template-top : list-of-term-template-top term-template-top
                              | term-template-top
    """
    if len(t) == 3:
        t[0] = t[1]
        t[0].append(t[2])
    else:
        t[0] = [t[1]]

def p_term_template_list(t):
    """
    term-template-list : term-template-list term-template-under-ellipsis
                       | term-template-under-ellipsis
    """
    if len(t) == 3:
        t[0] = t[1]
        t[0].append(t[2])
    else:
        t[0] = [t[1]]

def p_term_under_ellipsis(t):
    """
    term-template-under-ellipsis : term-template ELLIPSIS
                                 | term-template
                                 | term-template-pycall-extend
    """
    if len(t) == 2:
        t[0] = t[1]
    else:
        t[0] = term.Repeat(t[1])


def p_term_template_pycall_extend(t):
    'term-template-pycall-extend : COMMAATSIGN LPAREN IDENT list-of-term-template-top RPAREN'
    t[0] = term.PyCall(term.PyCallInsertionMode.Extend, t[3], t[4])

# This is how we can handle errors!
#def p_term_literal_top_error_1(t):
#    'term-literal-top : LPAREN error term_literal RPAREN'
#    raise Exception('blah', t[2], t[2].lineno)

def p_error(t):
    raise Exception('unexpected token {} on line {}'.format(t.value, t.lineno))

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

def parse(filename):
    f = open(filename, 'r')
    buf = f.read()
    f.close()
    lexer = lex.lex()
    parser = yacc.yacc(debug=1)
    return parser.parse(buf)

def parse_string(string):
    lexer = lex.lex()
    parser = yacc.yacc(debug=1)
    return parser.parse(string)


