from src.parser import RedexSpecParser
from src.preprocdefinelang import module_preprocess 
from src.patcodegen2 import DefineLanguagePatternCodegen3, SourceWriter

import sys
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

def codegen(tree, context):
# imports should be tucked away somewhere
    writer = SourceWriter()
    writer += 'from match import Match'
    writer.newline()
    writer += 'from parser import Parser'
    writer.newline()
    codegen = DefineLanguagePatternCodegen3(writer, context)
    codegen.transform(tree.definelanguage)
    for rm in tree.redexmatches:
        codegen.transform(rm)
    create_output(writer)


tree = RedexSpecParser("test2.rkt", is_filename=True).parse()
tree, context = module_preprocess(tree)

codegen(tree, context)
