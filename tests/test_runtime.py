import shutil 
import subprocess
import unittest

from src.__main__ import entrypoint , BASEDIR

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
            {'src': src, 'dump_ast': False, 'debug_dump_ntgraph': False})

def gentestcase(filename):
    def testcase(self):
        print('\n')
        print('------------------------------- Run {} ---------------'.format(filename))
        entrypoint(make_arg_obj(filename))
        exitcode = runpython('{}/out.py'.format(BASEDIR))
        self.assertEqual(exitcode, 0)
    return testcase

class TestRuntimeCode(unittest.TestCase):
    pass

for i, testcase in enumerate(testcases):
    setattr(TestRuntimeCode, 'test_{}'.format(i), gentestcase(testcase))
