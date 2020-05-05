from src.parser2 import parse 
from src.preprocdefinelang import module_preprocess 
from src.patcodegen2 import DefineLanguagePatternCodegen3, SourceWriter

import sys
import os
import shutil

import src.astdefs as ast 
import src.genterm as genterm


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
    writer += 'from match import Match, assert_compare_match_lists, combine_matches'
    writer.newline()
    writer += 'from parser import Parser'
    writer.newline()
    writer += 'from term import Hole, copy_path_and_replace_last, Sequence, plughole, TermKind'
    writer.newline()
    writer += 'hole = Hole()'
    writer.newline()
    writer += 'import term'
    writer.newline()

    # append to output file. We will be doing this for all files eventually.
    writer.newline()
    f = open('runtime/termops.py')
    buf = f.read()
    writer += buf
    f.close()
    writer.newline()

    codegen = DefineLanguagePatternCodegen3(writer, context)
    codegen.transform(tree.definelanguage)
    for rm in tree.redexmatches:
        codegen.transform(rm)

    for me in tree.matchequals:
        codegen.transform(me)

    for me in tree.termlet:
        codegen.transform(me)


    create_output(writer)



parser = argparse.ArgumentParser()
parser.add_argument('src', help='.rkt containing Redex spec')
parser.add_argument('-dump-ast', action='store_true', help='Write spec to stdout')
parser.add_argument('-dump-term-attribs', action='store_true', help='Blah')
args = parser.parse_args()

tree = parse(args.src)
tree, context = module_preprocess(tree)

if args.dump_term_attribs:
    for tl in tree.termlet:
        assert isinstance(tl, ast.AssertTermsEqual)
        t = genterm.TermAnnotate(tl.variable_assignments, 'blah', context).transform(tl.template)
        print(t)
    sys.exit(0)




if args.dump_ast:
    print(tree)
    sys.exit(0)

codegen(tree, context)
