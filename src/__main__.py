from src.parser import RedexSpecParser
from src.preprocdefinelang import definelanguage_preprocess
from src.patcodegen import DefineLanguagePatternCodegen, AstDump

tree = RedexSpecParser("test2.rkt", is_filename=True).parse()
tree = definelanguage_preprocess(tree)

codegen = DefineLanguagePatternCodegen()
codegen.transform(tree)



fns = codegen.functions


#dumper = AstDump()
#print(fns)
#dumper.write(fns[3])
#print(''.join(dumper.buf))

for i, f in enumerate(fns):
    dumper = AstDump()
    dumper.write(f)
    print(''.join(dumper.buf))





