from src.parser import parse 
from src.preprocdefinelang import  TopLevelProcessor 

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

def entrypoint(args):
    tree = parse(args.src) 
    context = CompilationContext()
    tree, context = TopLevelProcessor(tree, context, debug_dump_ntgraph=args.debug_dump_ntgraph).run()
    if args.dump_ast:
        print(tree)
        sys.exit(0)
    rpymodule = TopLevelFormCodegen(tree, context).run()
    create_output(rpymodule)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('src', help='.rkt containing Redex spec')
    parser.add_argument('-dump-ast', action='store_true', help='Write spec to stdout')
    parser.add_argument('-debug-dump-ntgraph', action='store_true', help='Write Nt graph')
    parser.add_argument('--include-py', nargs=1)
    args = parser.parse_args()
    entrypoint(args)

