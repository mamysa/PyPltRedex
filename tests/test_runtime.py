import shutil 
import subprocess
import unittest
import os

from src.__main__ import entrypoint 

RPYTHON_SOURCE_DIR = 'rpyout_temp'

testcases = [
    'tests/patmatchtest.rkt',
    'tests/inholetest.rkt',
    'tests/plugtest.rkt',
    'tests/applyreductionrelationtest.rkt',
    'tests/metafunction_test1.rkt',
    'tests/freshtest.rkt',
    'tests/parsetest.rkt',
]

def runpython(filename):
    py = subprocess.Popen(['python2.7', filename])
    return py.wait() 


def make_arg_obj(src):
    return type('Args', (object,),
            {'src': src, 'dump_ast': False, 'debug_dump_ntgraph': False, 
                'output_directory': RPYTHON_SOURCE_DIR, })

def gentestcase(filename):
    def testcase(self):
        print('\n')
        print('------------------------------- Run {} ---------------'.format(filename))
        entrypoint(make_arg_obj(filename))
        exitcode = runpython('{}/out.py'.format(RPYTHON_SOURCE_DIR))
        self.assertEqual(exitcode, 0)
    return testcase

class TestRuntimeCode(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        os.remove('{}/out.py'.format(RPYTHON_SOURCE_DIR))
        os.rmdir(RPYTHON_SOURCE_DIR)

for i, testcase in enumerate(testcases):
    setattr(TestRuntimeCode, 'test_{}'.format(i), gentestcase(testcase))

