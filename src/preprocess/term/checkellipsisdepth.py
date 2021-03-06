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

class Term_EllipsisDepthChecker(term.TermTransformer):
    def __init__(self, variables, idof, context):
        self.idof = idof
        self.path = []
        self.context = context
        self.variables = variables
        self.symgen = SymGen()

        # stores annotations that will be injected into term-template after
        # visiting all the children.
        self.annotations = {
            term.TermAttribute.MatchRead: {},
            term.TermAttribute.InArg    : {},
            term.TermAttribute.ForEach  : {},
        }    

    def add_annotation_to(self, node, attribute, value):
        attributedict = self.annotations[attribute]
        if node not in attributedict:
            attributedict[node] = []
        attributedict[node].append(value)

    def complete_annotation(self, oldnode, newnode):
        if isinstance(oldnode, term.Repeat):
            attributedict = self.annotations[term.TermAttribute.ForEach]
            contents = attributedict.get(oldnode, [])
            return newnode.addattribute(term.TermAttribute.ForEach, contents)

        attributedict = self.annotations[term.TermAttribute.MatchRead]
        contents = attributedict.get(oldnode, [])
        newnode.addattribute(term.TermAttribute.MatchRead, contents)
        attributedict = self.annotations[term.TermAttribute.InArg]
        contents = attributedict.get(oldnode, [])
        return newnode.addattribute(term.TermAttribute.InArg, contents)

    def contains_nonzero_foreach_annotations(self, node):
        assert isinstance(node, term.Repeat)
        attributedict = self.annotations[term.TermAttribute.ForEach]
        contents = attributedict.get(node, [])
        return len(contents) != 0

    def transform(self, element):
        assert isinstance(element, term.Term)
        method_name = 'transform' + element.__class__.__name__
        method_ref = getattr(self, method_name)
        self.path.append(element)
        result = method_ref(element)
        assert isinstance(result, term.Term)
        self.path.pop()
        return result 

    def transformTermLiteral(self, literal):
        assert isinstance(literal, term.TermLiteral)
        #self.context.add_lit_term(literal)
        return literal

    def transformPyCall(self, pycall):
        assert isinstance(pycall, term.PyCall)
        terms = []
        for t in pycall.termargs:
            transformer = Term_EllipsisDepthChecker(self.variables, '', self.context)
            terms.append( transformer.transform(t) )
        return self.complete_annotation(pycall, term.PyCall(pycall.mode, pycall.functionname, terms))

    def transformRepeat(self, repeat):
        assert isinstance(repeat, term.Repeat)
        nrepeat = term.Repeat(self.transform(repeat.term)).copyattributesfrom(repeat)
        if not self.contains_nonzero_foreach_annotations(repeat):
            raise Exception('too many ellipses in template {}'.format(repr(nrepeat)))
        return self.complete_annotation(repeat, nrepeat)

    def transformTermSequence(self, termsequence):
        ntermsequence = super().transformTermSequence(termsequence)
        return self.complete_annotation(termsequence, ntermsequence)

    def transformInHole(self, inhole):
        ninhole = super().transformInHole(inhole)
        return self.complete_annotation(inhole, ninhole)

    def transformUnresolvedSym(self, node):
        assert isinstance(node, term.UnresolvedSym)
        if node.sym not in self.variables:
            t = term.TermLiteral(term.TermLiteralKind.Variable, node.sym)
            #self.context.add_lit_term(t)
            return t
        expecteddepth = self.variables[node.sym] 
        actualdepth = 0

        param = self.symgen.get(node.sym)
        # definitely a pattern variable now, topmost entry on the stack is this node. 
        for t in reversed(self.path): 
            if isinstance(t, term.UnresolvedSym): 
                if expecteddepth == 0:
                    self.add_annotation_to(t, term.TermAttribute.MatchRead, (node.sym, param))
                    break
                self.add_annotation_to(t, term.TermAttribute.InArg, param)
            if isinstance(t, term.TermSequence) or isinstance(t, term.InHole):
                if expecteddepth == actualdepth:
                    self.add_annotation_to(t, term.TermAttribute.MatchRead, (node.sym, param))
                    break
                else:
                    self.add_annotation_to(t, term.TermAttribute.InArg, param)
            if isinstance(t, term.Repeat):
                actualdepth += 1
                self.add_annotation_to(t, term.TermAttribute.ForEach, (param, actualdepth))

        if actualdepth != expecteddepth:
            raise Exception('inconsistent ellipsis depth for pattern variable {}: expected {} actual {}'.format(node.sym, expecteddepth, actualdepth))

        return self.complete_annotation(node, term.PatternVariable(node.sym))

