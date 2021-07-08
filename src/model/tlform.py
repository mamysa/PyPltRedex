import src.model.pattern as pattern
from src.model.term import PyCall, PyCallInsertionMode
from src.util import CompilationError

# object containing other top-level forms...
class Module:
    def __init__(self, tlforms):
        self.tlforms = tlforms

    def __repr__(self):
        out = []
        for form in self.tlforms:
            out.append(repr(form))
        return "\n".join(out)

class TopLevelForm:
    pass

class RequirePythonSource(TopLevelForm):
    def __init__(self, filename):
        self.filename = filename

    def __repr__(self):
        return 'RequirePythonSource({})'.format(self.filename)

class DefineLanguage(TopLevelForm):
    # only used by define-language
    class NtDefinition:
        def __init__(self, nt, patterns):
            assert isinstance(nt, pattern.Nt)
            self.nt = nt
            self.patterns = patterns

        def get_nt_sym(self):
            return self.nt.sym

        def __repr__(self):
            return 'NtDefinition({}, {})'.format(repr(self.nt), repr(self.patterns))

    def __init__(self, name, ntdefs):
        self.name = name 
        self.nts = {} 

        # non-terminal-definitions must not contain underscores and each symbol can only appear once.
        for ntdef in ntdefs:
            ntsym = ntdef.get_nt_sym()
            if ntsym.find('_') != -1:
                raise ValueError('define-language: cannot use _ in a non-terminal name {}'.format(ntsym))

            if ntsym in self.nts.keys():
                raise ValueError('define-language: same non-terminal defined twice: {}'.format(ntsym))
            self.nts[ntsym] = ntdef
            self.closure = None

    def ntsyms(self):
        return set(self.nts.keys())

    def __repr__(self):
        return 'DefineLanguage({}, {})'.format(self.name, self.nts)

class DefineMetafunction(TopLevelForm):
    class MetafunctionCase:
        class SideCondition:
            def __init__(self, pythoncall):
                assert isinstance(pythoncall, PyCall)
                assert pythoncall.mode == PyCallInsertionMode.SideConditionAssertBoolean
                self.pythoncall = pythoncall

            def __repr__(self):
                return 'SideCondition({})'.format(self.pythoncall)

        def __init__(self, patternsequence, termtemplate, sideconditions=None):
            assert isinstance(patternsequence, pattern.PatSequence)
            self.patternsequence = patternsequence
            self.termtemplate = termtemplate
            self.sideconditions = sideconditions
            if self.sideconditions == None:
                self.sideconditions = []

        def __repr__(self):
            return 'MetaFunctionCase({}, {}, side-conditions: {})'.format(self.patternsequence, self.termtemplate, self.sideconditions)

    class MetafunctionContract:
        def __init__(self, name, domain, codomain):
            self.name = name 
            self.domain = pattern.PatSequence([pattern.Lit(name, pattern.LitKind.Variable)] + domain) # we will turn contract into pattern.
            self.codomain = codomain

        def __repr__(self):
            return 'MetafunctionContract({}, {})'.format(self.name, self.domain, self.codomain)

    def __init__(self, languagename, contract, cases):
        self.languagename = languagename
        self.contract = contract
        self.cases = cases
        for case in self.cases:
            name = case.patternsequence[0]
            if not (isinstance(name, pattern.Lit) and name.kind == pattern.LitKind.Variable and name.lit == contract.name):
                raise CompilationError('each metafunction case must begin with {}'.format(contract.name))

    def __repr__(self):
        return 'DefineMetafunction({}, {}, {})'.format(self.languagename, self.contract, self.cases)

class DefineReductionRelation(TopLevelForm):
    class ReductionCase:
        def __init__(self, pattern, termtemplate, name):
            self.pattern = pattern
            self.termtemplate = termtemplate
            self.name = name

        def __repr__(self):
            return 'ReductionCase({}, {}, {})'.format(self.pattern, self.termtemplate, self.name)

    def __init__(self, name, languagename, domain, reductioncases):
        self.name = name
        self.languagename = languagename
        self.reductioncases = reductioncases
        self.domain = domain

    def __repr__(self):
        return 'DefineReductionRelation({},{},{},{})'.format(self.name, self.languagename, self.domain, repr(self.reductioncases))

class RedexMatch(TopLevelForm):
    def __init__(self, languagename, pat, termstr):
        self.languagename = languagename
        self.pat = pat
        self.termstr = termstr 

    def __repr__(self):
        return 'RedexMatch({}, {}, {})'.format(self.languagename, repr(self.pat), self.termstr)

class RedexMatchAssertEqual(TopLevelForm):
    # Creates Match object with specified string-term bindings.
    class Match:
        def __init__(self, bindings):
            self.bindings = bindings

        def __repr__(self):
            return 'Match({})'.format(repr(self.bindings))

    def __init__(self, languagename, pat, termtemplate, expectedmatches):
        self.languagename = languagename
        self.pat = pat
        self.termtemplate = termtemplate
        self.expectedmatches = expectedmatches

    def __repr__(self):
        return 'RedexMatchAssertEqual({}, {}, {}, {})'.format(self.languagename, repr(self.pat), self.termtemplate, self.expectedmatches)

class TermLetAssertEqual(TopLevelForm):
    def __init__(self, variabledepths, variableassignments, template, expected):
        self.variabledepths = variabledepths # ellipsis depth
        self.variableassignments = variableassignments
        self.template = template
        self.expected = expected 

    def __repr__(self):
        return 'TermLetAssertEqual({}, {}, {}, {})'.format(repr(self.variabledepths), repr(self.variableassignments), repr(self.template), repr(self.expected))

class ApplyReductionRelationAssertEqual(TopLevelForm):
    def __init__(self, reductionrelationname, term, expected_termtemplates):
        self.reductionrelationname = reductionrelationname
        self.term = term
        self.expected_termtemplates = expected_termtemplates

    def __repr__(self):
        return 'ApplyReductionRelationAssertEqual({}, {}, {})'.format(self.reductionrelationname, self.term, self.expected_termtemplates)

class ParseAssertEqual(TopLevelForm):
    def __init__(self, string2parse, expected_termtemplate):
        self.string2parse = string2parse
        self.expected_termtemplate = expected_termtemplate

    def __repr__(self):
        return 'ParseAssertEqual({}, {})'.format(self.string2parse, self.expected_termtemplate)

class ReadFromStdinAndApplyReductionRelation(TopLevelForm):
    def __init__(self, reductionrelationname, metafunctionname=None):
        self.reductionrelationname = reductionrelationname
        self.metafunctionname = metafunctionname

    def __repr__(self):
        return 'ReadFromStdinAndApplyReductionRelation({}, {})'.format(self.reductionrelationname, self.metafunctionname)

class TopLevelFormVisitor:
    def _visit(self, element):
        assert isinstance(element, TopLevelForm)
        method_name = '_visit' + element.__class__.__name__
        method_ref = getattr(self, method_name)
        return method_ref(element)

    def run(self):
        assert False, 'override this'

    def _visitRequirePythonSource(self, form):
        return form

    def _visitDefineLanguage(self, form):
        return form 

    def _visitRedexMatch(self, form):
        return form 

    def _visitRedexMatchAssertEqual(self, form):
        return form

    def _visitTermLetAssertEqual(self, form):
        return form 

    def _visitDefineReductionRelation(self, form):
        return form

    def _visitApplyReductionRelationAssertEqual(self, form):
        return form

    def _visitParseAssertEqual(self, form):
        return form

    def _visitReadFromStdinAndApplyReductionRelation(self, form):
        return form
