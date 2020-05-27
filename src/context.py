import src.rpython as rpy
from src.symgen import SymGen

class CompilationContext:
    def __init__(self):
        self.__variables_mentioned = None
        self.__isa_functions = {}
        self.__pattern_code = {}
        self.__term_template_funcs = {}

        self._litterms = {}

        self.__toplevel_patterns = {}

        self.symgen = SymGen()

    def add_variables_mentioned(self, variables):
        self.__variables_mentioned = ('variables_mentioned', variables)

    def get_variables_mentioned(self):
        return self.__variables_mentioned

    def add_isa_function_name(self, prefix, function):
        assert prefix not in self.__isa_functions
        self.__isa_functions[prefix] = function
    
    def get_isa_function_name(self, prefix):
        if prefix in self.__isa_functions:
            return self.__isa_functions[prefix]
        return None

    def add_lit_term(self, term):
        self._litterms[term] = self.symgen.get('literal_term_') 

    def get_sym_for_lit_term(self, term):
        return self._litterms[term]

    # FIXME this should be in module-level context?
    def add_function_for_pattern(self, prefix, function):
        assert prefix not in self.__pattern_code, 'function for {} is present'.format(prefix)
        self.__pattern_code[prefix] = function
    
    def get_function_for_pattern(self, prefix):
        if prefix in self.__pattern_code:
            return self.__pattern_code[prefix]
        return None

    def add_toplevel_function_for_pattern(self, patrepr, functionname):
        assert patrepr not in self.__toplevel_patterns, 'function for {} is present'.format(patrepr)
        self.__toplevel_patterns[patrepr] = functionname

    def get_toplevel_function_for_pattern(self, patrepr):
        if patrepr in self.__toplevel_patterns:
            return self.__toplevel_patterns[patrepr]
        return None

    def add_function_for_term_template(self, prefix, function):
        assert prefix not in self.__term_template_funcs, 'function for {} is present'.format(prefix)
        self.__term_template_funcs[prefix] = function

    def get_function_for_term_template(self, prefix):
        if prefix in self.__term_template_funcs:
            return self.__term_template_funcs[prefix]
        return None


