from src.parser2 import parse 
from src.preprocdefinelang import module_preprocess 
from src.patcodegen3 import DefineLanguagePatternCodegen3, SourceWriter

import sys
import os
import shutil

import src.astdefs as ast 
#import src.genterm as genterm
import src.rpython as rpy

import argparse

BASEDIR = 'rpyout'

def create_output(module):
    writer = rpy.RPythonWriter()
    text = writer.write(module)
    lang = open('{}/out.py'.format(BASEDIR), 'w')
    lang.write(text)
    lang.close()

def codegen(tree, context, includepy):
    codegen = DefineLanguagePatternCodegen3(context)
    codegen.init_module(includepy)
    codegen.transform(tree.definelanguage)
    for rm in tree.redexmatches:
        codegen.transform(rm)
    for me in tree.matchequals:
        codegen.transform(me)
    for me in tree.termlet:
        codegen.transform(me)
    module = codegen.build_module()
    create_output(module)

parser = argparse.ArgumentParser()
parser.add_argument('src', help='.rkt containing Redex spec')
parser.add_argument('-dump-ast', action='store_true', help='Write spec to stdout')
parser.add_argument('-dump-term-attribs', action='store_true', help='Blah')
parser.add_argument('--include-py', nargs=1)
args = parser.parse_args()

tree = parse(args.src)
tree, context = module_preprocess(tree)

"""
if args.dump_term_attribs:
    for tl in tree.termlet:
        assert isinstance(tl, ast.AssertTermsEqual)
        t = genterm.TermAnnotate(tl.variable_assignments, 'blah', context).transform(tl.template)
        print(t)
    sys.exit(0)
"""

if args.dump_ast:
    print(tree)
    sys.exit(0)

codegen(tree, context, args.include_py)
