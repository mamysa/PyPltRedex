import src.term as term
import src.astdefs as ast
from src.symgen import SymGen

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

    def __init__(self, variables):
        self.path = []
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

    def transformRepeat(self, repeat):
        assert isinstance(repeat, term.Repeat)
        nrepeat = term.Repeat(self.transform(repeat.term)).copyattributesfrom(repeat)
        #if nrepeat.attributelength() == 0:
        #    raise Exception('too many ellipses in template {}'.format(repr(repeat)))
        return nrepeat

    def transformUnresolvedSym(self, node):
        assert isinstance(node, term.UnresolvedSym)
        if node.sym not in self.variables:
            return term.TermLiteral(term.TermLiteralKind.Variable, node.sym)
        expecteddepth, _ = self.variables[node.sym] 
        actualdepth = 0

        param = self.symgen.get(node.sym)
        # definitely a pattern variable now, topmost entry on the stack is this node. 
        # TODO NEED TO KEEP TRACK OF 
        prevrepeat, inserted = None, False
        for t in reversed(self.path): 
            if isinstance(t, term.UnresolvedSym): 
                if expecteddepth == 0:
                    t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, True))
                    break
                t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, False))
            if isinstance(t, term.TermSequence):
                if prevrepeat != None:
                    if expecteddepth == actualdepth:
                        t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, True))
                        prevrepeat.addattribute(term.TermAttribute.ForEach, (param, actualdepth))
                        break
                    else:
                        t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, False))
                        if not inserted:
                            prevrepeat.addattribute(term.TermAttribute.ForEach, (param, actualdepth))
                    inserted = True
                else:
                    t.addattribute(term.TermAttribute.InArg, (node.sym, param, actualdepth, False))

            if isinstance(t, term.Repeat):
                actualdepth += 1
                prevrepeat = t

        if actualdepth != expecteddepth:
            raise Exception('inconsistent ellipsis depth for pattern variable {}: expected {} actual {}'.format(node.sym, expecteddepth, actualdepth))
        return term.PatternVariable(node.sym).copyattributesfrom(node)

