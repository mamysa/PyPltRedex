from src.parser import RedexSpecParser
from src.preprocdefinelang import definelanguage_preprocess
from src.patcodegen2 import DefineLanguagePatternCodegen3, SourceWriter

import os
import shutil

BASEDIR = 'rpyout'

def create_output(writer):
    if os.path.isdir(BASEDIR):
        shutil.rmtree(BASEDIR)
    os.mkdir(BASEDIR)
    shutil.copy('runtime/parser.py', BASEDIR)
    shutil.copy('runtime/term.py', BASEDIR)
    shutil.copy('runtime/match.py', BASEDIR)

    lang = open('{}/lang.py'.format(BASEDIR), 'w')
    lang.write(writer.build())
    lang.close()







tree = RedexSpecParser("test2.rkt", is_filename=True).parse()
tree = definelanguage_preprocess(tree)

print(tree)


# imports should be tucked away somewhere
writer = SourceWriter()
writer += 'from match import Match'
codegen = DefineLanguagePatternCodegen3(writer)
codegen.transform(tree)
create_output(writer)












