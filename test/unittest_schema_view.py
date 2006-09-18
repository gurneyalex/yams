"""
unit tests for module yams.sqlschema

Copyright Logilab 2003-2005, all rights reserved.
"""

__revision__ = "$Id: unittest_schema_view.py,v 1.3 2005-07-01 21:39:36 nico Exp $"

from logilab.common.testlib import TestCase, unittest_main

from yams import SchemaLoader
from yams.schema_view import SchemaViewer

from unittest_schema_readers import DummyDefaultHandler

import os.path as osp

DATADIR = osp.abspath(osp.join(osp.dirname(__file__),'data'))

class SchemaViewTC(TestCase):

    def test_noerror(self):
        schema = SchemaLoader().load(DATADIR, 'Test', DummyDefaultHandler())
        SchemaViewer().visit_schema(schema, True)
        
if __name__ == '__main__':
    unittest_main()
