"""unit tests for module yams.sqlschema"""

from __future__ import generators

from logilab.common.testlib import TestCase, unittest_main

from yams import MARKER, BadSchemaDefinition
from yams.constraints import SizeConstraint
from yams.buildobjs import EntityType
from yams.sqlreader import EsqlFileReader

import os.path as osp

DATADIR = osp.abspath(osp.join(osp.dirname(__file__), 'data', 'schema'))

def __getattr__(self, attr):
    if 'relations' in self.__dict__:
        for e in self.relations:
            if e.name == attr:
                return e
    raise AttributeError(attr)
EntityType.__getattr__ = __getattr__

class DummyLoader:
    def __init__(self):
        self._defs = []
    def add_definition(self, hdlr, defobject):
        self._defs.append(defobject)

        
class SQLSchemaReaderClassTest(TestCase):
    """test suite for sql schema readers"""
    
    def setUp(self):
        loader = DummyLoader()
        self.reader = EsqlFileReader(loader)
        self.result = loader._defs
        
    def test_bad_schema(self):
        """tests schema_readers on a bad schema"""
        testfile = osp.join(DATADIR, '_missing_dynamicchoice_handler.sql')
        self.assertRaises(BadSchemaDefinition,
                          self.reader, testfile)
        try:
            self.reader(testfile)
        except Exception, ex:
            self.assertEquals(ex.args,
                               (testfile, 2, "yo dynamicchoice('')",
                                "unknown type 'Dynamicchoice'"))
            self.assertEquals(ex.filename,testfile)
            self.assertEquals(ex.lineno, 2)
            self.assertEquals(ex.line, "yo dynamicchoice('')")
        
    def test_bad_esql(self):
        """test schema_readers on a bad entity definition"""
        testfile = osp.join(DATADIR,'_bad_entity.sql')
        self.assertRaises(BadSchemaDefinition,
                          self.reader, testfile)
        try:
            self.reader(testfile)
        except Exception, ex:
            self.assertEquals(ex.args, (testfile, 11, 'bla bla bla',
                                        "unknown type 'Bla'"))
            self.assertEquals(ex.filename,testfile)
            self.assertEquals(ex.lineno,11)
            self.assertEquals(ex.line,"bla bla bla")
        
    def _get_result(self):
        self.assertEqual(len(self.result), 1)
        return self.result[0]
    
    def test_read_constraints(self):
        """checks how constraints are read and stored"""
        self.reader(osp.join(DATADIR,'Person.sql'))
        edef = self._get_result()
        nom_constraints = edef.nom.constraints
        self.assert_(isinstance(nom_constraints[0], SizeConstraint))
        self.assertEqual(nom_constraints[0].max, 64)
        self.assertEqual(nom_constraints[0].min, None)
        tel_constraints = edef.tel.constraints
        self.assert_(not tel_constraints)

    def test_read_defaults(self):
        """checks how default values are read and stored"""
        self.reader(osp.join(DATADIR,'Person.sql'))
        edef = self._get_result()
        self.assertEqual(edef.nom.default, MARKER)
        self.assertEqual(edef.tel.default, MARKER)
        self.assertEqual(edef.sexe.default, 'M')

    def test_read_types(self):
        """checks how base types are read"""
        self.reader(osp.join(DATADIR,'Person.sql'))
        edef = self._get_result()
        for attr, etype in ( ('nom', 'String'), ('tel', 'Int'), ('fax', 'Int'),
                             ('test', 'Boolean'), ('promo', 'String'),
                             ('datenaiss', 'Date'), ('sexe', 'String'),
                             ('salary', 'Float')):
            self.assertEqual(getattr(edef, attr).etype, etype)
        
        
if __name__ == '__main__':
    unittest_main()
