import src.pat as pat

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
            assert isinstance(nt, pat.Nt)
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

    def ntsyms(self):
        return set(self.nts.keys())

    def __repr__(self):
        return 'DefineLanguage({}, {})'.format(self.name, self.nts)

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
        self.domain = domain
        self.reductioncases = reductioncases

    def __repr__(self):
        return 'DefineReductionRelation({},{},{},{})'.format(self.name, self.languagename, self.domain, repr(self.reductioncases))

class RedexMatch(TopLevelForm):
    def __init__(self, languagename, pat, termstr):
        self.languagename = languagename
        self.pat = pat
        self.termstr = termstr 

    def __repr__(self):
        return 'RedexMatch({}, {}, {})'.format(self.languagename, repr(self.pat), self.termstr)

# asserts that matches produced by redex-matches are equal to predefined list
# only used for testing.
class MatchEqual(TopLevelForm):
    # Creates Match object with specified string-term bindings.
    class Match:
        def __init__(self, bindings):
            self.bindings = bindings

        def __repr__(self):
            return 'Match({})'.format(repr(self.bindings))

    def __init__(self, redexmatch, list_of_matches, equality=True):
        self.redexmatch = redexmatch
        self.list_of_matches = list_of_matches

    def __repr__(self):
        return 'MatchEqual({} {})'.format(self.redexmatch, self.list_of_matches)

class AssertTermsEqual(TopLevelForm):
    def __init__(self, variabledepths, variableassignments, template, literal):
        self.variabledepths = variabledepths # ellipsis depth
        self.variableassignments = variableassignments
        self.template = template
        self.literal = literal

    def __repr__(self):
        return 'AssertTermsEqual({}, {}, {}, {})'.format(repr(self.variabledepths), repr(self.variableassignments), repr(self.template), repr(self.literal))

class ApplyReductionRelation(TopLevelForm):
    def __init__(self, reductionrelationname, term):
        self.reductionrelationname = reductionrelationname
        self.term = term

    def __repr__(self):
        return 'ApplyReductionRelation({}, {})'.format(self.reductionrelationname, self.term)

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

    def _visitMatchEqual(self, form):
        return MatchEqual(self._visit(form.redexmatch), form.list_of_matches)

    def _visitAssertTermsEqual(self, form):
        return form 

    def _visitDefineReductionRelation(self, form):
        return form
