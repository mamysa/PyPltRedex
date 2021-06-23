from src.parser import parse 
from src.preprocess import TopLevelProcessor 
from src.codegen.tlform import TopLevelFormCodegen

import sys
import shutil
import argparse
import pathlib
import src.model.rpython as rpy

from src.context import CompilationContext


DEFAULTPATH = 'rpyout'

def create_output(module, path):
    writer = rpy.RPythonWriter()
    text = writer.write(module)
    path.mkdir(parents=True, exist_ok=True)
    with pathlib.Path(path, 'out.py').open(mode='w') as f:
        f.write(text)

def entrypoint(args):
    tree = parse(args.src) 
    context = CompilationContext()
    tree, context = TopLevelProcessor(tree, context, debug_dump_ntgraph=args.debug_dump_ntgraph).run()
    if args.dump_ast:
        print(tree)
        sys.exit(0)
    rpymodule = TopLevelFormCodegen(tree, context).run()
    path = pathlib.Path(pathlib.Path.cwd(), args.output_directory)
    create_output(rpymodule, path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('src', help='.rkt containing Redex spec')
    parser.add_argument('-o', '--output-directory', help='Write RPython source to output directory, default rpyout', default= 'rpyout/')
    parser.add_argument('-dump-ast', action='store_true', help='Write spec to stdout')
    parser.add_argument('-debug-dump-ntgraph', action='store_true', help='Write Nt graph')
    args = parser.parse_args()
    entrypoint(args)

