"""unit tests for module yams.reader"""

import sys
import os.path as osp
from datetime import datetime, date, time

from logilab.common.testlib import TestCase, unittest_main
from logilab.common.compat import sorted

from yams import BadSchemaDefinition, buildobjs
from yams.schema import Schema
from yams.reader import SchemaLoader
from yams.constraints import StaticVocabularyConstraint, SizeConstraint

from yams import schema
schema.use_py_datetime()

sys.path.insert(0, osp.join(osp.dirname(__file__)))

DATADIR = osp.abspath(osp.join(osp.dirname(__file__), 'data'))

schema = SchemaLoader().load([DATADIR])


class SchemaLoaderTC(TestCase):

    # test helper functions ###################################################

    def test_get_schema_files(self):
        files = [osp.basename(f) for f in SchemaLoader().get_schema_files(DATADIR)]
        self.assertEquals(files[0], '__init__.py')
        self.assertEquals(sorted(files),
                          ['Company.py', 'Dates.py', 'State.py', '__init__.py', 'schema.py'])

    # test load_schema read entity and relation types #######################

    def test_load_schema(self):
        self.assert_(isinstance(schema, Schema))
        self.assertEquals(schema.name, 'NoName')
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
                               'para', 'prenom', 'promo',
                               'ref', 'require_permission', 'rncs',
                               'salary', 'sexe', 'short_desc', 'state_of', 'subcompany_of',
                               'subdivision_of', 'subj_wildcard', 'sujet', 'sym_rel',
                               't1', 't2', 'tel', 'test', 'titre', 'travaille', 'type',
                               'version',
                               'ville', 'web', 'works_for'])

    def test_eschema(self):
        eschema = schema.eschema('Societe')
        self.assertEquals(eschema.description, '')
        self.assertEquals(eschema.is_final(), False)
        self.assertListEquals(sorted(eschema.subject_relations()),
                              ['ad1', 'ad2', 'ad3', 'cp', 'evaluee',
                               'fax', 'nom', 'rncs', 'subj_wildcard', 'tel', 'ville',
                               'web'])
        self.assertListEquals(sorted(eschema.object_relations()),
                          ['concerne', 'obj_wildcard', 'travaille'])

        eschema = schema.eschema('Eetype')
        self.assertEquals(eschema.description, 'define an entity type, used to build the application schema')
        self.assertEquals(eschema.is_final(), False)
        self.assertListEquals(sorted(str(r) for r in eschema.subject_relations()),
                              ['description', 'final', 'initial_state', 'meta',
                               'name', 'subj_wildcard'])
        self.assertListEquals(sorted(str(r) for r in eschema.object_relations()),
                              ['obj_wildcard', 'state_of'])

        eschema = schema.eschema('Boolean')
        self.assertEquals(eschema.description, '')
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
        self.assertEquals(eschema.default('version'), '0.1')
        self.assertEquals(eschema.default('license'), None)

    # test relation type properties ###########################################

    def test_rschema(self):
        rschema = schema.rschema('evaluee')
        self.assertEquals(rschema.symetric, False)
        self.assertEquals(rschema.description, '')
        self.assertEquals(rschema.is_final(), False)
        self.assertListEquals(sorted(rschema.subjects()), ['Person', 'Societe'])
        self.assertListEquals(sorted(rschema.objects()), ['Note'])

        rschema = schema.rschema('sym_rel')
        self.assertEquals(rschema.symetric, True)
        self.assertEquals(rschema.description, '')
        self.assertEquals(rschema.is_final(), False)
        self.assertListEquals(sorted(rschema.subjects()), ['Affaire', 'Person'])
        self.assertListEquals(sorted(rschema.objects()), ['Affaire', 'Person'])

        rschema = schema.rschema('initial_state')
        self.assertEquals(rschema.symetric, False)
        self.assertEquals(rschema.description, 'indicate which state should be used by default when an entity using states is created')
        self.assertEquals(rschema.is_final(), False)
        self.assertListEquals(sorted(rschema.subjects()), ['Eetype'])
        self.assertListEquals(sorted(rschema.objects()), ['State'])

        rschema = schema.rschema('name')
        self.assertEquals(rschema.symetric, False)
        self.assertEquals(rschema.description, '')
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
        self.assertEquals(len(eschema.constraints('promo')), 2)
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
                                            'add': ('managers', 'users'),
                                            'delete': ('managers', 'users')})

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
        self.assertEquals([r.name for r in bp.__relations__], ['firstname', 'lastname'])
        self.assertEquals([r.name for r in p.__relations__], ['firstname', 'lastname', 'email'])
        self.assertEquals([r.name for r in e.__relations__], ['firstname', 'lastname', 'email', 'company'])

    def test_schema_extension(self):
        s = Student()
        self.assertEquals([r.name for r in s.__relations__], ['firstname', 'lastname', 'email', 'college'])
        self.assertEquals(s.specialized_type, 'Person')
        x = X()
        self.assertEquals(x.specialized_type, None)

    def test_relationtype(self):
        foo = Foo()
        self.assertEquals([r.etype for r in foo.__relations__],
                          ['Int', 'Float', 'Datetime'])
        self.assertEquals(foo.__relations__[0].cardinality, '11')
        self.assertEquals(foo.__relations__[1].cardinality, '?1')

    def test_maxsize(self):
        bp = BasePerson()
        def maxsize(e):
            for e in e.constraints:
                if isinstance(e, SizeConstraint):
                    return e.max
        self.assertEquals(maxsize(bp.__relations__[0]), 7)
        # self.assertEquals(maxsize(bp.__relations__[1]), 7)
        emp = Employee()
        self.assertEquals(maxsize(emp.__relations__[3]), 7)

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
                               SchemaLoader().load, [DATADIR], 'Test')
        try:
            self.assertEquals(str(ex), "conflicting values False/True for property inlined of relation 'rel'")
        except AssertionError:
            self.assertEquals(str(ex), "conflicting values True/False for property inlined of relation 'rel'")


    def test_broken_schema2(self):
        SchemaLoader.main_schema_directory = 'brokenschema2'
        ex = self.assertRaises(BadSchemaDefinition,
                               SchemaLoader().load, [DATADIR], 'Test')
        try:
            self.assertEquals(str(ex), "conflicting values True/False for property inlined of relation 'rel'")
        except AssertionError:
            self.assertEquals(str(ex), "conflicting values False/True for property inlined of relation 'rel'")

    def test_broken_schema3(self):
        SchemaLoader.main_schema_directory = 'brokenschema3'
        ex = self.assertRaises(BadSchemaDefinition,
                               SchemaLoader().load, [DATADIR], 'Test')
        try:
            self.assertEquals(str(ex), "conflicting values True/False for property inlined of relation 'rel'")
        except AssertionError:
            self.assertEquals(str(ex), "conflicting values False/True for property inlined of relation 'rel'")

    def test_broken_schema4(self):
        schema = Schema('toto')
        schema.add_entity_type(buildobjs.EntityType(name='Entity'))
        schema.add_entity_type(buildobjs.EntityType(name='Int'))
        schema.add_relation_type(buildobjs.RelationType(name='toto'))
        ex = self.assertRaises(BadSchemaDefinition,
                               schema.add_relation_def,
                               buildobjs.RelationDefinition(name='toto', subject='Entity', object='Int',
                                                     constraints=[SizeConstraint(40)]))
        self.assertEquals(str(ex), "size constraint doesn't apply to Int entity type")

    def test_broken_schema5(self):
        schema = Schema('toto')
        schema.add_entity_type(buildobjs.EntityType(name='Entity'))
        schema.add_entity_type(buildobjs.EntityType(name='String'))
        schema.add_relation_type(buildobjs.RelationType(name='toto'))
        ex = self.assertRaises(BadSchemaDefinition,
                               schema.add_relation_def,
                               buildobjs.RelationDefinition(name='toto', subject='Entity', object='String',
                                                            constraints=[StaticVocabularyConstraint(['ab', 'abc']),
                                                                         SizeConstraint(2)]))
        self.assertEquals(str(ex), "size constraint set to 2 but vocabulary contains string of greater size")

    def test_schema(self):
        SchemaLoader.main_schema_directory = 'schema2'
        schema = SchemaLoader().load([DATADIR], 'Test')
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

    def test_imports(self):
        SchemaLoader.main_schema_directory = 'schema'
        schema = SchemaLoader().load([DATADIR, DATADIR+'2'], 'Test')
        self.assertEquals(schema['Affaire']._groups, {'read': (),
                                                      'add': (),
                                                      'update': (),
                                                      'delete': ()})
        self.assertEquals([str(r) for r,at in schema['MyNote'].attribute_definitions()],
                          ['date', 'type', 'para', 'text'])

    def test_duplicated_rtype(self):
        loader = SchemaLoader()
        loader.defined = {}
        class RT1(RelationType):
            pass
        loader.add_definition(None, RT1)
        ex = self.assertRaises(BadSchemaDefinition,
                          loader.add_definition, None, RT1)
        self.assertEquals(str(ex), 'duplicated relation type for RT1')

    def test_rtype_priority(self):
        loader = SchemaLoader()
        loader.defined = {}
        class RT1Def(RelationDefinition):
            name = 'RT1'
            subject = 'Whatever'
            object = 'Whatever'
        class RT1(RelationType):
            pass
        loader.add_definition(None, RT1Def)
        loader.add_definition(None, RT1)
        self.assertEquals(loader.defined['RT1'], RT1)

if __name__ == '__main__':
    unittest_main()


