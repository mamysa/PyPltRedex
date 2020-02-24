from src.parser import RedexSpecParser
from src.preprocdefinelang import definelanguage_preprocess

tree = RedexSpecParser("test2.rkt", is_filename=True).parse()
print(tree)
tree = definelanguage_preprocess(tree)
print(tree)




