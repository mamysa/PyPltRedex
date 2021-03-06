import src.model.rpython as rpy
import src.model.term as term
from src.util import SymGen


class CompilationContext:
    def __init__(self):
        self.__variables_mentioned = {} 
        self.__isa_functions = {}
        self.__pattern_code = {}
        self.__term_template_funcs = {}

        self._litterms = {}

        self.__toplevel_patterns = {}

        self.__reductionrelations = {}
        self.__metafuctions = {}

        self.__redexmatches = {}

        self.symgen = SymGen()

    def add_variables_mentioned(self, languagename,  variables):
        assert languagename not in self.__variables_mentioned
        self.__variables_mentioned[languagename] = ('{}_variables_mentioned'.format(languagename), variables)

    def get_variables_mentioned(self, languagename):
        assert languagename in self.__variables_mentioned
        return self.__variables_mentioned[languagename]

    def get_variables_mentioned_all(self):
        return self.__variables_mentioned.values()

    def add_lit_term(self, term):
        self._litterms[term] = self.symgen.get('literal_term_') 

    def add_isa_function_name(self, languagename, patrepr, functionname):
        k = (languagename, patrepr)
        assert k not in self.__isa_functions
        self.__isa_functions[k] = functionname
    
    def get_isa_function_name(self, languagename, patrepr):
        k = (languagename, patrepr)
        if k in self.__isa_functions:
            return self.__isa_functions[k]
        return None

    def get_sym_for_lit_term(self, term):
        return self._litterms[term]

    def add_function_for_pattern(self, languagename, patrepr, functionname):
        k = (languagename, patrepr)
        assert k not in self.__pattern_code, 'function for {}-{}  is present'.format(languagename, patrepr)
        self.__pattern_code[k] = functionname
    
    def get_function_for_pattern(self, languagename, patrepr):
        k = (languagename, patrepr)
        if k in self.__pattern_code:
            return self.__pattern_code[k]
        return None
    
    # generated and returns procedurename, boolean for given pattern. If boolean is True - the code for 
    # pattern has already been generated.
    def get_function_for_pattern_2(self, languagename, patrepr):
        k = (languagename, patrepr)
        if k in self.__pattern_code:
            return self.__pattern_code[k], True 
        self.__pattern_code[k] = self.symgen.get('pattern_match')
        return self.__pattern_code[k], False 

    def add_toplevel_function_for_pattern(self, languagename, patrepr, functionname):
        k = (languagename, patrepr)
        assert k not in self.__toplevel_patterns, 'function for {}-{} is present'.format(languagename, patrepr)
        self.__toplevel_patterns[k] = functionname

    def get_toplevel_function_for_pattern(self, languagename, patrepr):
        k = (languagename, patrepr)
        if k in self.__toplevel_patterns:
            return self.__toplevel_patterns[k]
        return None

    def get_function_for_term_template(self, term_template):
        assert isinstance(term_template, term.Term)
        if term_template not in self.__term_template_funcs:
            name = self.symgen.get('gen_term')
            self.__term_template_funcs[term_template] = name
        return self.__term_template_funcs[term_template]

    def add_reduction_relation(self, reductionrelationname, function):
        k = reductionrelationname
        assert k not in self.__reductionrelations
        self.__reductionrelations[k] = function 

    def get_reduction_relation(self, reductionrelationname):
        k = reductionrelationname
        if k in self.__reductionrelations:
            return self.__reductionrelations[k]
        return None

    def add_metafunction(self, mfname, function):
        k = mfname 
        assert k not in self.__metafuctions
        self.__metafuctions[k] = function 

    def get_metafunction(self, mfname):
        k = mfname 
        if k in self.__metafuctions:
            return self.__metafuctions[k]
        return None

    def get_redexmatch_for(self, form):
        return self.__redexmatches[form]

    def add_redexmatch_for(self, form, name):
        self.__redexmatches[form] = name
