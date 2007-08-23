"""
unit tests for module yams.sqlschema

Copyright Logilab 2003-2006, all rights reserved.
"""

from __future__ import generators

from logilab.common.testlib import TestCase, unittest_main

from yams.constraints import SizeConstraint
from yams.builder import EntityType
from yams import BadSchemaDefinition
from yams.sqlschema import EsqlFileReader

import os.path as osp

DATADIR = osp.abspath(osp.join(osp.dirname(__file__), 'data', 'schema'))

def __getattr__(self, attr):
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
                               ("yo dynamicchoice('')",
                                osp.join(DATADIR, '_missing_dynamicchoice_handler.sql'),
                                "unknown type 'Dynamicchoice'"))
        
    def test_bad_esql(self):
        """test schema_readers on a bad entity definition"""
        testfile = osp.join(DATADIR,'_bad_entity.sql')
        self.assertRaises(BadSchemaDefinition,
                          self.reader, testfile)
        try:
            self.reader(testfile)
        except Exception, ex:
            self.assertEquals(ex.args, ('bla bla bla', osp.join(DATADIR,'_bad_entity.sql'),
                                        "unknown type 'Bla'"))
        
##     def test_bad_schema_stream(self):
##         """tests stream schema_readers on a bad schema"""
##         schema = Schema('Test')
##         teststream = file('data/_missing_dynamicchoice_handler.sql')
##         self.assertRaises(BadSchemaDefinition,
##                           self.reader_from_stream, schema, 'etype', teststream)
##         teststream = file('data/_missing_dynamicchoice_handler.sql')
##         try:
##             self.reader_from_stream('etype', teststream)
##         except Exception, ex:
##             msg = str(ex)
##         self.assertEquals(msg, '(stream) etype: missing callback for dynamic choice relation yo')
        
##     def test_bad_esql_stream(self):
##         """test stream schema_readers on a bad entity definition"""
##         schema = Schema('Test')
##         teststream = file('data/_bad_entity.sql')
##         self.assertRaises(ESQLParseError,
##                           self.reader_from_stream, schema, 'etype', teststream)
##         teststream = file('data/_bad_entity.sql')
##         try:
##             self.reader_from_stream('etype', teststream)
##         except Exception, ex:
##             msg = str(ex)
##         self.assertEquals(msg, '(stream) etype: unable to parse bla bla bla')
        
##     def test_read_base(self):
##         """checks basic reading"""
##         for schema, e_schema in try_every_way_to_read('data/Person.sql', 'Person'):
##             self.assert_(isinstance(e_schema, EntitySchema))
##             self.assertEqual(e_schema.type, 'Person')
##             self.assertEqual(e_schema, schema.entity_schema('Person'))
                         
##     def test_read_relations(self):
##         """checks how relations are read and stored"""
##         for schema, e_schema in try_every_way_to_read('data/Person.sql', 'Person'):            
##             nom_rel = e_schema.subject_relation_schema(r_type='nom')
##             self.assert_(nom_rel)
##             self.assert_(isinstance(nom_rel, RelationSchema))
##             self.assertEqual(nom_rel.type, 'nom')

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
        self.assertEqual(edef.nom.default, None)
        self.assertEqual(edef.tel.default, None)
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
