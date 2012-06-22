'''
Created on Jun 20, 2012

@author: Yangming
'''
import sys
from os import path
_rootpath = path.dirname(path.realpath(__file__))
sys.path.append(path.join(_rootpath, ".."))

import unittest
from test_plugin import TestPlugin
from check_passenger import PassengerChecker

class TestPassengerChecker(TestPlugin):
    def setUp(self):
        self.checker = PassengerChecker()
        print 'check_passenger'

    def test_get_max_procs(self):
        self.assert_status("-t MAX_PROCESSES")

    def test_get_procs(self):
        self.assert_status("-t RUNNING_PROCESSES")

    def test_get_active_procs(self):
        self.assert_status("-t ACTIVE_PROCESSES")

if __name__ == "__main__":
    unittest.main()