"""unit tests for module yams.reader"""

from logilab.common.testlib import TestCase, unittest_main
from logilab.common.compat import sorted

from datetime import datetime, date, time

from yams import BadSchemaDefinition
from yams.schema import Schema, EntitySchema
from yams.reader import SchemaLoader, RelationFileReader
from yams.constraints import StaticVocabularyConstraint, SizeConstraint

from yams import schema
schema.use_py_datetime()

import os.path as osp

DATADIR = osp.abspath(osp.join(osp.dirname(__file__), 'data'))

class DummyDefaultHandler:

    def default_modname(self):
        return 'yo'
    
    def vocabulary_license(self):
        return ['GPL', 'ZPL']
    
    def vocabulary_debian_handler(self):
        return ['machin', 'bidule']

schema = SchemaLoader().load([DATADIR], 'Test', DummyDefaultHandler())


class SchemaLoaderTC(TestCase):

    # test helper functions ###################################################
    
    def test_get_schema_files(self):
        files = sorted([osp.basename(f) for f in SchemaLoader().get_schema_files(DATADIR)])
        self.assertEquals(files,
                          ['Affaire.sql', 'Company.py', 'Dates.py', 'Note.sql', 'Person.sql',
                           'Societe.sql', 'State.py', 'pkginfo.esql', 'relations.rel'])
    
    def test_include(self):
        files = SchemaLoader().include_schema_files('Person', osp.join(DATADIR, 'schema'))
        self.assertEquals(files, [osp.join(DATADIR, 'schema', 'Person.sql')])
        files = SchemaLoader().include_schema_files('pkginfo', osp.join(DATADIR, 'schema'))
        self.assertEquals(files, [osp.join(DATADIR, 'schema', 'pkginfo.esql')])

    # test load_schema read entity and relation types #######################
    
    def test_load_schema(self):
        self.assert_(isinstance(schema, Schema))
        self.assertEquals(schema.name, 'Test')
        self.assertListEquals(sorted(schema.entities()),
                              ['Affaire', 'Boolean', 'Bytes', 'Company', 'Date', 'Datetest', 'Datetime', 'Decimal',
                               'Division', 'EPermission', 'Eetype',  'Employee', 'Float', 'Int', 'Interval',
                               'Note', 'Password', 'Person', 'Societe', 'State', 'String',
                               'Subcompany', 'Subdivision', 'Time', 'pkginfo'])
        self.assertListEquals(sorted(schema.relations()),
                              ['ad1', 'ad2', 'ad3', 'adel', 'ass', 'author', 'author_email',
                               'concerne', 'copyright', 'cp',
                               'd1', 'd2', 'date', 'datenaiss', 'debian_handler', 'description', 'division_of', 'dt1', 'dt2',
                               'eid', 'evaluee', 'fax', 'final',
                               'initial_state', 'inline_rel',
                               'license', 'long_desc',
                               'mailinglist', 'meta', 'modname',
                               'name', 'next_state', 'nom', 'obj_wildcard',
                               'para', 'prenom', 'promo', 'pyversions',
                               'ref', 'require_permission', 'rncs',
                               'salary', 'sexe', 'short_desc', 'state_of', 'subcompany_of',
                               'subdivision_of', 'subj_wildcard', 'sujet', 'sym_rel',
                               't1', 't2', 'tel', 'test', 'titre', 'travaille', 'type',
                               'version', 
                               'ville', 'web', 'works_for'])

    def test_eschema(self):
        eschema = schema.eschema('Societe')
        self.assertEquals(eschema.description, '')
        self.assertEquals(eschema.meta, False)
        self.assertEquals(eschema.is_final(), False)
        self.assertListEquals(sorted(eschema.subject_relations()),
                              ['ad1', 'ad2', 'ad3', 'cp', 'evaluee',
                               'fax', 'nom', 'rncs', 'subj_wildcard', 'tel', 'ville',
                               'web'])
        self.assertListEquals(sorted(eschema.object_relations()),
                          ['concerne', 'obj_wildcard', 'travaille'])
        
        eschema = schema.eschema('Eetype')
        self.assertEquals(eschema.description, 'define an entity type, used to build the application schema')
        self.assertEquals(eschema.meta, True)
        self.assertEquals(eschema.is_final(), False)
        self.assertListEquals(sorted(eschema.subject_relations()),
                              ['description', 'final', 'initial_state', 'meta',
                               'name'])
        self.assertListEquals(sorted(eschema.object_relations()),
                              ['state_of'])

        eschema = schema.eschema('Boolean')
        self.assertEquals(eschema.description, '')
        self.assertEquals(eschema.meta, True)
        self.assertEquals(eschema.is_final(), True)
        self.assertListEquals(sorted(eschema.subject_relations()),
                              [])
        self.assertListEquals(sorted(eschema.object_relations()),
                              ['final', 'meta', 'test'])

    # test base entity type's subject relation properties #####################

    def test_indexed(self):
        eschema = schema.eschema('Person')
        self.assert_(not eschema.rproperty('nom', 'indexed'))
        eschema = schema.eschema('State')
        self.assert_(eschema.rproperty('name', 'indexed'))

    def test_uid(self):
        eschema = schema.eschema('State')
        self.assert_(eschema.rproperty('eid', 'uid'))
        self.assert_(not eschema.rproperty('name', 'uid'))
    
    def test_fulltextindexed(self):
        eschema = schema.eschema('Person')
        self.assert_(not eschema.rproperty('tel', 'fulltextindexed'))
        self.assert_(eschema.rproperty('nom', 'fulltextindexed'))
        self.assert_(eschema.rproperty('prenom', 'fulltextindexed'))
        self.assert_(not eschema.rproperty('sexe', 'fulltextindexed'))
        indexable = sorted(eschema.indexable_attributes())
        self.assertEquals(['nom', 'prenom', 'titre'], indexable)
        self.assertEquals(schema.rschema('works_for').fulltext_container, None)
        self.assertEquals(schema.rschema('require_permission').fulltext_container,
                          'subject')
        eschema = schema.eschema('Company')
        indexable = sorted(eschema.indexable_attributes())
        self.assertEquals([], indexable)
        indexable = sorted(eschema.fulltext_relations())
        self.assertEquals([('require_permission', 'subject')], indexable)
        containers = sorted(eschema.fulltext_containers())
        self.assertEquals([], containers)
        eschema = schema.eschema('EPermission')
        indexable = sorted(eschema.indexable_attributes())
        self.assertEquals(['name'], indexable)
        indexable = sorted(eschema.fulltext_relations())
        self.assertEquals([], indexable)
        containers = sorted(eschema.fulltext_containers())
        self.assertEquals([('require_permission', 'subject')], containers)
        
    def test_internationalizable(self):
        eschema = schema.eschema('Eetype')
        self.assert_(eschema.rproperty('name', 'internationalizable'))
        eschema = schema.eschema('State')
        self.assert_(eschema.rproperty('name', 'internationalizable'))
        eschema = schema.eschema('Societe')
        self.assert_(not eschema.rproperty('ad1', 'internationalizable'))

    # test advanced entity type's subject relation properties #################

    def test_vocabulary(self):
        eschema = schema.eschema('pkginfo')
        self.assertEquals(eschema.vocabulary('license'), ('GPL', 'ZPL'))
        self.assertEquals(eschema.vocabulary('debian_handler'), ('machin', 'bidule'))
        
    def test_default(self):
        eschema = schema.eschema('pkginfo')
        self.assertEquals(eschema.default('modname'), 'yo')
        self.assertEquals(eschema.default('license'), None)

    # test relation type properties ###########################################
        
    def test_rschema(self):
        rschema = schema.rschema('evaluee')
        self.assertEquals(rschema.symetric, False)
        self.assertEquals(rschema.description, '')
        self.assertEquals(rschema.meta, False)
        self.assertEquals(rschema.is_final(), False)
        self.assertListEquals(sorted(rschema.subjects()), ['Person', 'Societe'])
        self.assertListEquals(sorted(rschema.objects()), ['Note'])

        rschema = schema.rschema('sym_rel')
        self.assertEquals(rschema.symetric, True)
        self.assertEquals(rschema.description, '')
        self.assertEquals(rschema.meta, False)
        self.assertEquals(rschema.is_final(), False)
        self.assertListEquals(sorted(rschema.subjects()), ['Affaire', 'Person'])
        self.assertListEquals(sorted(rschema.objects()), ['Affaire', 'Person'])

        rschema = schema.rschema('initial_state')
        self.assertEquals(rschema.symetric, False)
        self.assertEquals(rschema.description, 'indicate which state should be used by default when an entity using states is created')
        self.assertEquals(rschema.meta, True)
        self.assertEquals(rschema.is_final(), False)
        self.assertListEquals(sorted(rschema.subjects()), ['Eetype'])
        self.assertListEquals(sorted(rschema.objects()), ['State'])

        rschema = schema.rschema('name')
        self.assertEquals(rschema.symetric, False)
        self.assertEquals(rschema.description, '')
        self.assertEquals(rschema.meta, False)
        self.assertEquals(rschema.is_final(), True)
        self.assertListEquals(sorted(rschema.subjects()), ['Company', 'Division', 'EPermission', 'Eetype', 'State', 'Subcompany', 'Subdivision'])
        self.assertListEquals(sorted(rschema.objects()), ['String'])

    def test_cardinality(self):
        rschema = schema.rschema('evaluee')
        self.assertEquals(rschema.rproperty('Person', 'Note', 'cardinality'), '**')
        rschema = schema.rschema('inline_rel')        
        self.assertEquals(rschema.rproperty('Affaire', 'Person', 'cardinality'), '?*')
        rschema = schema.rschema('initial_state')        
        self.assertEquals(rschema.rproperty('Eetype', 'State', 'cardinality'), '?*')
        rschema = schema.rschema('state_of')
        self.assertEquals(rschema.rproperty('State', 'Eetype', 'cardinality'), '+*')
        rschema = schema.rschema('name')
        self.assertEquals(rschema.rproperty('State', 'String', 'cardinality'), '11')
        rschema = schema.rschema('description')
        self.assertEquals(rschema.rproperty('State', 'String', 'cardinality'), '?1')
    
    def test_constraints(self):
        eschema = schema.eschema('Person')
        self.assertEquals(len(eschema.constraints('nom')), 1)
        self.assertEquals(len(eschema.constraints('promo')), 1)
        self.assertEquals(len(eschema.constraints('tel')), 0)
        self.assertRaises(AssertionError, eschema.constraints, 'travaille')
        self.assertRaises(KeyError, eschema.constraints, 'inline_rel')
        eschema = schema.eschema('State')
        self.assertEquals(len(eschema.constraints('name')), 1)
        self.assertEquals(len(eschema.constraints('description')), 0)
        self.assertRaises(AssertionError, eschema.constraints, 'next_state')
        self.assertRaises(KeyError, eschema.constraints, 'initial_state')
        eschema = schema.eschema('Eetype')
        self.assertEquals(len(eschema.constraints('name')), 2)
        
    def test_inlined(self):
        rschema = schema.rschema('evaluee')
        self.assertEquals(rschema.inlined, False)
        rschema = schema.rschema('state_of')
        self.assertEquals(rschema.inlined, False)
        rschema = schema.rschema('inline_rel')        
        self.assertEquals(rschema.inlined, True)
        rschema = schema.rschema('initial_state')        
        self.assertEquals(rschema.inlined, True)

    def test_relation_permissions(self):
        rschema = schema.rschema('state_of')
        self.assertEquals(rschema._groups,
                          {'read': ('managers', 'users', 'guests'),
                           'delete': ('managers',),
                           'add': ('managers',)})
        
        rschema = schema.rschema('next_state')
        self.assertEquals(rschema._groups,
                          {'read':   ('managers', 'users', 'guests',),
                           'add':    ('managers',),
                           'delete': ('managers',)})
        
        rschema = schema.rschema('initial_state')
        self.assertEquals(rschema._groups,
                          {'read':   ('managers', 'users', 'guests',),
                           'add':    ('managers', 'users',),
                           'delete': ('managers', 'users',)})
        
        rschema = schema.rschema('evaluee')
        self.assertEquals(rschema._groups,
                          {'read':   ('managers', 'users', 'guests',),
                           'add':    ('managers', 'users',),
                           'delete': ('managers', 'users',)})
        
        rschema = schema.rschema('nom')
        self.assertEquals(rschema._groups, {'read': ('managers', 'users', 'guests'),
                                            'add': ('managers', 'users', 'guests'),
                                            'delete': ('managers', 'users', 'guests')})
        
        rschema = schema.rschema('require_permission')
        self.assertEquals(rschema._groups, {'read': ('managers', 'users', 'guests'),
                                            'add': ('managers', ),
                                            'delete': ('managers',)})
        
    def test_entity_permissions(self):
        eschema = schema.eschema('State')
        self.assertEquals(eschema._groups,
                          {'read':   ('managers', 'users', 'guests',),
                           'add':    ('managers', 'users',),
                           'delete': ('managers', 'owners',),
                           'update': ('managers', 'owners',)})
        
        eschema = schema.eschema('Eetype')
        self.assertEquals(eschema._groups,
                          {'read':   ('managers', 'users', 'guests',),
                           'add':    ('managers',),
                           'delete': ('managers',),
                           'update': ('managers', 'owners',)})
        
        eschema = schema.eschema('Person')
        self.assertEquals(eschema._groups, 
                          {'read':   ('managers', 'users', 'guests',),
                           'add':    ('managers', 'users',),
                           'delete': ('managers', 'owners',),
                           'update': ('managers', 'owners',)})
        
##     def test_nonregr_using_tuple_as_relation_target(self):
##         rschema = schema.rschema('see_also')
##         self.assertEquals(rschema.symetric, False)
##         self.assertEquals(rschema.description, '')
##         self.assertEquals(rschema.meta, False)
##         self.assertEquals(rschema.is_final(), False)
##         self.assertListEquals(sorted(rschema.subjects()), ['Employee'])
##         self.assertListEquals(sorted(rschema.objects()), ['Company', 'Division'])
## 


from yams import buildobjs as B

class BasePerson(B.EntityType):
    firstname = B.String(vocabulary=('logilab', 'caesium'), maxsize=10)
    lastname = B.String(constraints=[StaticVocabularyConstraint(['logilab', 'caesium'])])

class Person(BasePerson):
    email = B.String()

class Employee(Person):
    company = B.String(vocabulary=('logilab', 'caesium'))


class Student(Person):
    __specializes_schema__ = True
    college = B.String()

class X(Student):
    pass

class Foo(B.EntityType):
    i = B.Int(required=True)
    f = B.Float()
    d = B.Datetime()

    
class PySchemaTC(TestCase):

    def test_python_inheritance(self):        
        bp = BasePerson()
        p = Person()
        e = Employee()
        self.assertEquals([r.name for r in bp.relations], ['firstname', 'lastname'])
        self.assertEquals([r.name for r in p.relations], ['firstname', 'lastname', 'email'])
        self.assertEquals([r.name for r in e.relations], ['firstname', 'lastname', 'email', 'company'])

    def test_schema_extension(self):
        s = Student()
        self.assertEquals([r.name for r in s.relations], ['firstname', 'lastname', 'email', 'college'])
        self.assertEquals(s.specialized_type, 'Person')
        x = X()
        self.assertEquals(x.specialized_type, None)

    def test_relationtype(self):
        foo = Foo()
        self.assertEquals([r.etype for r in foo.relations],
                          ['Int', 'Float', 'Datetime'])
        self.assertEquals(foo.relations[0].cardinality, '11')
        self.assertEquals(foo.relations[1].cardinality, '?1')

    def test_maxsize(self):
        bp = BasePerson()
        def maxsize(e):
            for e in e.constraints:
                if isinstance(e, SizeConstraint):
                    return e.max
        self.assertEquals(maxsize(bp.relations[0]), 7)
        # self.assertEquals(maxsize(bp.relations[1]), 7)
        emp = Employee()
        self.assertEquals(maxsize(emp.relations[3]), 7)

    def test_date_defaults(self):
        _today = date.today()
        _now = datetime.now()
        datetest = schema.eschema('Datetest')
        dt1 = datetest.default('dt1')
        dt2 = datetest.default('dt2')
        d1 = datetest.default('d1')
        d2 = datetest.default('d2')
        t1 = datetest.default('t1')
        t2 = datetest.default('t2')
        # datetimes
        self.assertIsInstance(dt1, datetime)
        # there's no easy way to test NOW (except monkey patching now() itself)
        delta = dt1 - _now
        self.failUnless(abs(delta.seconds) < 5)
        self.assertEquals(date(dt2.year, dt2.month, dt2.day), _today)
        self.assertIsInstance(dt2, datetime)
        # dates
        self.assertEquals(d1, _today)
        self.assertIsInstance(d1, date)
        self.assertEquals(d2, datetime(2007, 12, 11, 0, 0))
        self.assertIsInstance(d2, datetime)
        # times
        self.assertEquals(t1, time(8, 40))
        self.assertIsInstance(t1, time)
        self.assertEquals(t2, time(9, 45))
        self.assertIsInstance(t2, time)


class SchemaLoaderTC2(TestCase):
    def test_broken_schema1(self):
        SchemaLoader.main_schema_directory = 'brokenschema1' 
        ex = self.assertRaises(BadSchemaDefinition,
                               SchemaLoader().load, [DATADIR], 'Test', DummyDefaultHandler())
        self.assertEquals(str(ex), "conflicting values True/False for property inlined of relation type 'rel'")
        
    def test_broken_schema2(self):
        SchemaLoader.main_schema_directory = 'brokenschema2' 
        ex = self.assertRaises(BadSchemaDefinition,
                               SchemaLoader().load, [DATADIR], 'Test', DummyDefaultHandler())
        self.assertEquals(str(ex), "conflicting values False/True for property inlined of relation type 'rel'")
        
    def test_broken_schema3(self):
        SchemaLoader.main_schema_directory = 'brokenschema3' 
        ex = self.assertRaises(BadSchemaDefinition,
                               SchemaLoader().load, [DATADIR], 'Test', DummyDefaultHandler())
        self.assertEquals(str(ex), "conflicting values False/True for property inlined of relation type 'rel'")
        
    def test_schema(self):
        SchemaLoader.main_schema_directory = 'schema2' 
        schema = SchemaLoader().load([DATADIR], 'Test', DummyDefaultHandler())
        rel = schema['rel']
        self.assertEquals(rel.rproperty('Anentity', 'Anentity', 'composite'),
                          'subject')
        self.assertEquals(rel.rproperty('Anotherentity', 'Anentity', 'composite'),
                          'subject')
        self.assertEquals(rel.rproperty('Anentity', 'Anentity', 'cardinality'),
                          '1*')
        self.assertEquals(rel.rproperty('Anotherentity', 'Anentity', 'cardinality'),
                          '1*')
        self.assertEquals(rel.symetric, True)
        self.assertEquals(rel.inlined, True)
        self.assertEquals(rel.meta, False)
        

if __name__ == '__main__':
    unittest_main()
