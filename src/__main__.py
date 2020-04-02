from src.parser import RedexSpecParser
from src.preprocdefinelang import module_preprocess 
from src.patcodegen2 import DefineLanguagePatternCodegen3, SourceWriter

import sys
import os
import shutil

import argparse

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
    writer += 'from match import Match, assert_compare_match_lists'
    writer.newline()
    writer += 'from parser import Parser'
    writer.newline()
    writer += 'from term import Hole, copy_path_and_replace_last'
    writer.newline()
    writer += 'hole = Hole()'
    writer.newline()
    codegen = DefineLanguagePatternCodegen3(writer, context)
    codegen.transform(tree.definelanguage)
    for rm in tree.redexmatches:
        codegen.transform(rm)

    for me in tree.matchequals:
        codegen.transform(me)

    create_output(writer)



parser = argparse.ArgumentParser()
parser.add_argument('src', help='.rkt containing Redex spec')
parser.add_argument('-dump-ast', action='store_true', help='Write spec to stdout')
args = parser.parse_args()

tree = RedexSpecParser(args.src, is_filename=True).parse()
tree, context = module_preprocess(tree)

if args.dump_ast:
    print(tree)
    sys.exit(0)

codegen(tree, context)
