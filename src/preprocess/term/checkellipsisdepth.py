import src.model.term as term
from src.util import SymGen
from src.context import CompilationContext

# Need to annotate term template to ease code generation. Given a pattern variable n
# and associated ellipsis depth, we keep track of the path to the pattern variable in the term 
# and annotate terms on the path as follows:
# (1) Set depth to zero after discovering pattern variable.
# (2) if path(term) == Repeat:        annotate term with ForEach(n, depth + 1)
# (3) if path(term) == TermSequence:  annotate term with InArg(n, symgen(n), from-match)
#     from-match indicates where term to be plugged to come from - either is a function argument or 
#     should be taken directly from match object that is passed around.
# Ensure the number of elllipses equal to ellipsis depth of n has been consumed on the path.
# Once all pattern variables all been resolved, ensure that there are no-unannotated ellipses. Along the way
# collect all literal terms and assign a variable to them - this way there will be only a single instance of the term.

class TermAnnotate(term.TermTransformer):
    def __init__(self, variables, idof, context):
        self.idof = idof
        self.path = []
        self.context = context
        self.variables = variables
        self.symgen = SymGen()

    def transform(self, element):
        assert isinstance(element, term.Term)
        method_name = 'transform' + element.__class__.__name__
        method_ref = getattr(self, method_name)
        self.path.append(element)
        result = method_ref(element)
        self.path.pop()
        return result 

    def transformTermLiteral(self, literal):
        assert isinstance(literal, term.TermLiteral)
        self.context.add_lit_term(literal)
        sym = self.symgen.get('{}_lit'.format(self.idof))
        literal.addattribute(term.TermAttribute.FunctionName, sym)
        return literal

    def transformPyCall(self, pycall):
        assert isinstance(pycall, term.PyCall)
        sym = self.symgen.get('{}_gen_term'.format(self.idof))
        terms = []
        for t in pycall.termargs:
            idof = self.symgen.get('{}_pycall_gen_term_'.format(self.idof))
            transformer = TermAnnotate(self.variables, idof, self.context)
            terms.append( transformer.transform(t) )

        return term.PyCall(pycall.mode, pycall.functionname, terms) \
                   .addattribute(term.TermAttribute.FunctionName, sym)

    def transformRepeat(self, repeat):
        assert isinstance(repeat, term.Repeat)
        nrepeat = term.Repeat(self.transform(repeat.term)).copyattributesfrom(repeat)
        try:
            if len(nrepeat.getattribute(term.TermAttribute.ForEach)) == 0:
                raise Exception('too many ellipses in template {}'.format(repr(nrepeat)))
        except:
            raise Exception('too many ellipses in template {}'.format(repr(nrepeat)))
        return nrepeat

    def transformTermSequence(self, termsequence):
        ntermsequence = super().transformTermSequence(termsequence)
        sym = self.symgen.get('{}_gen_term'.format(self.idof))
        return ntermsequence.addattribute(term.TermAttribute.FunctionName, sym)

    def transformInHole(self, inhole):
        ninhole = super().transformInHole(inhole)
        sym = self.symgen.get('{}_gen_term'.format(self.idof))
        return ninhole.addattribute(term.TermAttribute.FunctionName, sym)

    def transformUnresolvedSym(self, node):
        assert isinstance(node, term.UnresolvedSym)
        if node.sym not in self.variables:
            sym = self.symgen.get('{}_lit'.format(self.idof))
            t = term.TermLiteral(term.TermLiteralKind.Variable, node.sym)
            t.addattribute(term.TermAttribute.FunctionName, sym)
            self.context.add_lit_term(t)
            return t
        expecteddepth = self.variables[node.sym] 
        actualdepth = 0

        param = self.symgen.get(node.sym)
        # definitely a pattern variable now, topmost entry on the stack is this node. 
        for t in reversed(self.path): 
            if isinstance(t, term.UnresolvedSym): 
                if expecteddepth == 0:
                    t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, True))
                    break
                t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, False))
            if isinstance(t, term.TermSequence) or isinstance(t, term.InHole):
                if expecteddepth == actualdepth:
                    t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, True))
                    break
                else:
                    t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, False))
            if isinstance(t, term.Repeat):
                actualdepth += 1
                t.addattribute(term.TermAttribute.ForEach, (param, actualdepth))

        if actualdepth != expecteddepth:
            raise Exception('inconsistent ellipsis depth for pattern variable {}: expected {} actual {}'.format(node.sym, expecteddepth, actualdepth))

        sym = self.symgen.get('{}_gen_term'.format(self.idof))
        return term.PatternVariable(node.sym).copyattributesfrom(node).addattribute(term.TermAttribute.FunctionName, sym)

