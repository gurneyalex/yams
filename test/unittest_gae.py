from logilab.common.testlib import TestCase, unittest_main

import os.path as osp
from datetime import datetime, date, time

from mx.DateTime import today

try:
    from google.appengine.ext import db
    from google.appengine.api import datastore_types as dtypes
    from yams.gae import eschema2dbmodel, schema2dbmodel
    IMPORT_APPENGINE = True
except ImportError:
    IMPORT_APPENGINE = False

from yams.reader import SchemaLoader

class DummyDefaultHandler:

    def default_modname(self):
        return 'yo'
    
    def vocabulary_license(self):
        return ['GPL', 'ZPL']
    
    def vocabulary_debian_handler(self):
        return ['machin', 'bidule']

DATADIR = osp.abspath(osp.join(osp.dirname(__file__),'data'))

class Yams2GaeModel(TestCase):
    schema = SchemaLoader().load([DATADIR], 'Test', DummyDefaultHandler())

    def setUp(self):
        if not IMPORT_APPENGINE:
            self.skip('could not import appengine')
        self.clean_kind_map = dict(db._kind_map)

    def tearDown(self):
        db._kind_map = self.clean_kind_map


    def test_simple_entity_type_conversion(self):
        eschema = self.schema.eschema('Company')
        self.failIf('Company' in db._kind_map)
        company = eschema2dbmodel(eschema, db)
        self.failUnless('Company' in db._kind_map)
        self.failUnless(db._kind_map['Company'] is company)
        self.assertEquals(company.properties().keys(), ['name'])
        nameprop = company.properties()['name']
        self.assertEquals(nameprop.data_type, dtypes.Text)
        self.assertEquals(nameprop.required, False)


    def test_entity_type_conversion_with_required(self):
        eschema = self.schema.eschema('EPermission')
        self.failIf('EPermission' in db._kind_map)
        eperm = eschema2dbmodel(eschema, db)
        self.failUnless('EPermission' in db._kind_map)
        self.failUnless(db._kind_map['EPermission'] is eperm)
        self.assertEquals(eperm.properties().keys(), ['name'])
        nameprop = eperm.properties()['name']
        self.assertEquals(nameprop.data_type, basestring)
        self.assertEquals(nameprop.required, True)


    def test_entity_type_conversion_with_dates(self):
        eschema = self.schema.eschema('Datetest')
        self.failIf('Datetest' in db._kind_map)
        datetest = eschema2dbmodel(eschema, db)
        mxtoday = today()
        # NOTE: datetime's today method is an alias for now !
        _dttoday = datetime(mxtoday.year, mxtoday.month, mxtoday.day)
        _dtoday = date(mxtoday.year, mxtoday.month, mxtoday.day)
        self.failUnless('Datetest' in db._kind_map)
        self.failUnless(db._kind_map['Datetest'] is datetest)
        properties = sorted(datetest.properties().values(), key=lambda x:x.creation_counter)
        expected = [('dt1', datetime, False, datetime.now()),
                    ('dt2', datetime, False, _dttoday),
                    ('d1', date, False, _dtoday),
                    ('d2', date, False, date(2007, 12, 11)),
                    ('t1', time, False, time(8, 40)),
                    ('t2', time, False, time(9, 45)),
                    ]
        self.assertEquals(len(properties), len(expected))
        for prop, (pname, ptype, prequired, pdefault) in zip(properties, expected):
            self.assertEquals(prop.name, pname)
            self.assertEquals(prop.data_type, ptype)
            self.assertEquals(prop.required, prequired)
            default = prop.default_value()
            if prop.name == 'dt1': # XXX special 'now' handling 
                # self.failUnless((pdefault - default).seconds > 10)
                pass
            else:
                self.assertEquals(default, pdefault)

    def test_full_schema_conversion(self):
        schema2dbmodel(self.schema, db)
        self.failUnless('Datetest' in db._kind_map)
        self.failUnless('Company' in db._kind_map)
        self.failUnless('EPermission' in db._kind_map)

##     def test_entity_types(self):
##         """make sure we have a kind_map entry for each entity type
##         """
##         self.schema.build_gae_model()
##         self.assertSetEquals(db._kind_map.keys(),
##                              (['Affaire', 'Boolean', 'Bytes', 'Company', 'Date', 'Datetest', 'Datetime',
##                                'Division', 'EPermission', 'Eetype',  'Employee', 'Float', 'Int', 'Interval',
##                                'Note', 'Password', 'Person', 'Societe', 'State', 'String', 'Time',
##                                'pkginfo']))
if __name__ == '__main__':
    unittest_main();
