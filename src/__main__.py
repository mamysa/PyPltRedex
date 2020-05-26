from src.parser import parse 
from src.preprocdefinelang import DefineLanguageProcessor, TopLevelProcessor 

from src.gentlform import TopLevelFormCodegen

import sys
import os
import shutil
import argparse
import src.rpython as rpy

from src.context import CompilationContext


BASEDIR = 'rpyout'

def create_output(module):
    writer = rpy.RPythonWriter()
    text = writer.write(module)
    lang = open('{}/out.py'.format(BASEDIR), 'w')
    lang.write(text)
    lang.close()


parser = argparse.ArgumentParser()
parser.add_argument('src', help='.rkt containing Redex spec')
parser.add_argument('-dump-ast', action='store_true', help='Write spec to stdout')
parser.add_argument('-dump-term-attribs', action='store_true', help='Blah')
parser.add_argument('--include-py', nargs=1)
args = parser.parse_args()

tree = parse(args.src) 
context = CompilationContext()
tree, context = DefineLanguageProcessor(tree, context).run()
tree, context = TopLevelProcessor(tree, context, tree.definelanguage.ntsyms()).run()
if args.dump_ast:
    print(tree)
    sys.exit(0)
rpymodule = TopLevelFormCodegen(tree, context, args.include_py).run()
create_output(rpymodule)
