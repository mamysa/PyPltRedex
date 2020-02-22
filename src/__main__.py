from src.parser import RedexSpecParser
tree = RedexSpecParser("test2.rkt", is_filename=True).parse()
print(tree)
