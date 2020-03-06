from src.parser import RedexSpecParser
from src.preprocdefinelang import definelanguage_preprocess
from src.patcodegen import DefineLanguagePatternCodegen, AstDump

import os
import shutil

BASEDIR = 'rpyout'

def create_output(module):
    if os.path.isdir(BASEDIR):
        shutil.rmtree(BASEDIR)
    os.mkdir(BASEDIR)
    shutil.copy('runtime/parser.py', BASEDIR)
    shutil.copy('runtime/term.py', BASEDIR)


    lang = open('{}/lang.py'.format(BASEDIR), 'w')
    dumper = AstDump()
    dumper.write(module)
    out = ''.join(dumper.buf)
    lang.write(out)
    lang.close()







tree = RedexSpecParser("test2.rkt", is_filename=True).parse()
tree = definelanguage_preprocess(tree)

codegen = DefineLanguagePatternCodegen()
codegen.transform(tree)

create_output(codegen.modulebuilder.build())












