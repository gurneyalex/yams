# copyright 2004-2012 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of yams.
#
# yams is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option)
# any later version.
#
# yams is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with yams. If not, see <http://www.gnu.org/licenses/>.
"""unit tests for module yams.reader"""

from __future__ import with_statement

import sys
import os.path as osp
from datetime import datetime, date, time

from logilab.common.testlib import TestCase, unittest_main

from yams import BadSchemaDefinition, buildobjs
from yams.schema import Schema
from yams.reader import SchemaLoader, build_schema_from_namespace
from yams.constraints import StaticVocabularyConstraint, SizeConstraint

sys.path.insert(0, osp.join(osp.dirname(__file__)))

DATADIR = osp.abspath(osp.join(osp.dirname(__file__), 'data'))

schema = SchemaLoader().load([DATADIR])


class SchemaLoaderTC(TestCase):

    # test helper functions ###################################################

    def test_get_schema_files(self):
        files = [osp.basename(f) for f in SchemaLoader().get_schema_files(DATADIR)]
        self.assertEqual(files[0], '__init__.py')
        self.assertEqual(sorted(files),
                          ['Company.py', 'Dates.py', 'State.py', '__init__.py', 'schema.py'])

    # test load_schema read entity and relation types #######################

    def test_load_schema(self):
        self.assert_(isinstance(schema, Schema))
        self.assertEqual(schema.name, 'NoName')
        self.assertListEqual(sorted(schema.entities()),
                              ['Affaire', 'BigInt', 'Boolean', 'Bytes', 'Company',
                               'Date', 'Datetest', 'Datetime', 'Decimal',
                               'Division', 'EPermission', 'Eetype',  'Employee', 'Float', 'Int', 'Interval',
                               'Note', 'Password', 'Person', 'Societe', 'State', 'String',
                               'Subcompany', 'Subdivision', 'TZDatetime', 'TZTime', 'Time', 'pkginfo'])
        self.assertListEqual(sorted(schema.relations()),
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
        self.assertEqual(eschema.description, '')
        self.assertEqual(eschema.final, False)
        self.assertListEqual(sorted(eschema.subject_relations()),
                              ['ad1', 'ad2', 'ad3', 'cp', 'evaluee',
                               'fax', 'nom', 'rncs', 'subj_wildcard', 'tel', 'ville',
                               'web'])
        self.assertListEqual(sorted(eschema.object_relations()),
                          ['concerne', 'obj_wildcard', 'travaille'])

        eschema = schema.eschema('Eetype')
        self.assertEqual(eschema.description, 'define an entity type, used to build the application schema')
        self.assertEqual(eschema.final, False)
        self.assertListEqual(sorted(str(r) for r in eschema.subject_relations()),
                              ['description', 'final', 'initial_state', 'meta',
                               'name', 'subj_wildcard'])
        self.assertListEqual(sorted(str(r) for r in eschema.object_relations()),
                              ['obj_wildcard', 'state_of'])

        eschema = schema.eschema('Boolean')
        self.assertEqual(eschema.description, '')
        self.assertEqual(eschema.final, True)
        self.assertListEqual(sorted(eschema.subject_relations()),
                              [])
        self.assertListEqual(sorted(eschema.object_relations()),
                              ['final', 'meta', 'test'])

    # test base entity type's subject relation properties #####################

    def test_indexed(self):
        eschema = schema.eschema('Person')
        self.assert_(not eschema.rdef('nom').indexed)
        eschema = schema.eschema('State')
        self.assert_(eschema.rdef('name').indexed)

    def test_uid(self):
        eschema = schema.eschema('State')
        self.assert_(eschema.rdef('eid').uid)
        self.assert_(not eschema.rdef('name').uid)

    def test_fulltextindexed(self):
        eschema = schema.eschema('Person')
        self.assertRaises(AttributeError, getattr, eschema.rdef('tel'), 'fulltextindexed') # tel is an INT
        self.assert_(eschema.rdef('nom').fulltextindexed)
        self.assert_(eschema.rdef('prenom').fulltextindexed)
        self.assert_(not eschema.rdef('sexe').fulltextindexed)
        indexable = sorted(eschema.indexable_attributes())
        self.assertEqual(['nom', 'prenom', 'titre'], indexable)
        self.assertEqual(schema.rschema('works_for').fulltext_container, None)
        self.assertEqual(schema.rschema('require_permission').fulltext_container,
                          'subject')
        eschema = schema.eschema('Company')
        indexable = sorted(eschema.indexable_attributes())
        self.assertEqual([], indexable)
        indexable = sorted(eschema.fulltext_relations())
        self.assertEqual([('require_permission', 'subject')], indexable)
        containers = sorted(eschema.fulltext_containers())
        self.assertEqual([], containers)
        eschema = schema.eschema('EPermission')
        indexable = sorted(eschema.indexable_attributes())
        self.assertEqual(['name'], indexable)
        indexable = sorted(eschema.fulltext_relations())
        self.assertEqual([], indexable)
        containers = sorted(eschema.fulltext_containers())
        self.assertEqual([('require_permission', 'subject')], containers)

    def test_internationalizable(self):
        eschema = schema.eschema('Eetype')
        self.assert_(eschema.rdef('name').internationalizable)
        eschema = schema.eschema('State')
        self.assert_(eschema.rdef('name').internationalizable)
        eschema = schema.eschema('Societe')
        self.assert_(not eschema.rdef('ad1').internationalizable)

    # test advanced entity type's subject relation properties #################

    def test_vocabulary(self):
        eschema = schema.eschema('pkginfo')
        self.assertEqual(eschema.vocabulary('license'), ('GPL', 'ZPL'))
        self.assertEqual(eschema.vocabulary('debian_handler'), ('machin', 'bidule'))

    def test_default(self):
        eschema = schema.eschema('pkginfo')
        self.assertEqual(eschema.default('version'), '0.1')
        self.assertEqual(eschema.default('license'), None)

    # test relation type properties ###########################################

    def test_rschema(self):
        rschema = schema.rschema('evaluee')
        self.assertEqual(rschema.symmetric, False)
        self.assertEqual(rschema.description, '')
        self.assertEqual(rschema.final, False)
        self.assertListEqual(sorted(rschema.subjects()), ['Person', 'Societe'])
        self.assertListEqual(sorted(rschema.objects()), ['Note'])

        rschema = schema.rschema('sym_rel')
        self.assertEqual(rschema.symmetric, True)
        self.assertEqual(rschema.description, '')
        self.assertEqual(rschema.final, False)
        self.assertListEqual(sorted(rschema.subjects()), ['Affaire', 'Person'])
        self.assertListEqual(sorted(rschema.objects()), ['Affaire', 'Person'])

        rschema = schema.rschema('initial_state')
        self.assertEqual(rschema.symmetric, False)
        self.assertEqual(rschema.description, 'indicate which state should be used by default when an entity using states is created')
        self.assertEqual(rschema.final, False)
        self.assertListEqual(sorted(rschema.subjects()), ['Eetype'])
        self.assertListEqual(sorted(rschema.objects()), ['State'])

        rschema = schema.rschema('name')
        self.assertEqual(rschema.symmetric, False)
        self.assertEqual(rschema.description, '')
        self.assertEqual(rschema.final, True)
        self.assertListEqual(sorted(rschema.subjects()), ['Company', 'Division', 'EPermission', 'Eetype', 'State', 'Subcompany', 'Subdivision'])
        self.assertListEqual(sorted(rschema.objects()), ['String'])

    def test_cardinality(self):
        rschema = schema.rschema('evaluee')
        self.assertEqual(rschema.rdef('Person', 'Note').cardinality, '**')
        rschema = schema.rschema('inline_rel')
        self.assertEqual(rschema.rdef('Affaire', 'Person').cardinality, '?*')
        rschema = schema.rschema('initial_state')
        self.assertEqual(rschema.rdef('Eetype', 'State').cardinality, '?*')
        rschema = schema.rschema('state_of')
        self.assertEqual(rschema.rdef('State', 'Eetype').cardinality, '+*')
        rschema = schema.rschema('name')
        self.assertEqual(rschema.rdef('State', 'String').cardinality, '11')
        rschema = schema.rschema('description')
        self.assertEqual(rschema.rdef('State', 'String').cardinality, '?1')

    def test_constraints(self):
        eschema = schema.eschema('Person')
        self.assertEqual(len(eschema.rdef('nom').constraints), 1)
        self.assertEqual(len(eschema.rdef('promo').constraints), 2)
        self.assertEqual(len(eschema.rdef('tel').constraints), 0)
        eschema = schema.eschema('State')
        self.assertEqual(len(eschema.rdef('name').constraints), 1)
        self.assertEqual(len(eschema.rdef('description').constraints), 0)
        eschema = schema.eschema('Eetype')
        self.assertEqual(len(eschema.rdef('name').constraints), 2)

    def test_inlined(self):
        rschema = schema.rschema('evaluee')
        self.assertEqual(rschema.inlined, False)
        rschema = schema.rschema('state_of')
        self.assertEqual(rschema.inlined, False)
        rschema = schema.rschema('inline_rel')
        self.assertEqual(rschema.inlined, True)
        rschema = schema.rschema('initial_state')
        self.assertEqual(rschema.inlined, True)

    def test_relation_permissions(self):
        rschema = schema.rschema('evaluee')
        self.assertEqual(rschema.rdef('Person', 'Note').permissions,
                          {'read': ('managers',),
                           'delete': ('managers',),
                           'add': ('managers',)})
        self.assertEqual(rschema.rdef('Societe', 'Note').permissions,
                          {'read': ('managers',),
                           'delete': ('managers',),
                           'add': ('managers',)})
        rschema = schema.rschema('concerne')
        self.assertEqual(rschema.rdef('Person', 'Affaire').permissions,
                          {'read': ('managers',),
                           'delete': ('managers',),
                           'add': ('managers',)})
        self.assertEqual(rschema.rdef('Affaire', 'Societe').permissions,
                          buildobjs.DEFAULT_RELPERMS)
        rschema = schema.rschema('travaille')
        self.assertEqual(rschema.rdef('Person', 'Societe').permissions,
                          {'read': (), 'add': (), 'delete': ('managers',)})

    def test_attributes_permissions(self):
        rschema = schema.rschema('name')
        self.assertEqual(rschema.rdef('Company', 'String').permissions,
                          buildobjs.DEFAULT_ATTRPERMS)
        rschema = schema.rschema('tel')
        self.assertEqual(rschema.rdef('Person', 'Int').permissions,
                          {'read': (),
                           'update': ('managers',)})


    def test_entity_permissions(self):
        eschema = schema.eschema('State')
        self.assertEqual(eschema.permissions,
                          {'read':   ('managers', 'users', 'guests',),
                           'add':    ('managers', 'users',),
                           'delete': ('managers', 'owners',),
                           'update': ('managers', 'owners',)})

        eschema = schema.eschema('Eetype')
        self.assertEqual(eschema.permissions,
                          {'read':   ('managers', 'users', 'guests',),
                           'add':    ('managers',),
                           'delete': ('managers',),
                           'update': ('managers', 'owners',)})

        eschema = schema.eschema('Person')
        self.assertEqual(eschema.permissions,
                          {'read':   ('managers', 'users', 'guests',),
                           'add':    ('managers', 'users',),
                           'delete': ('managers', 'owners',),
                           'update': ('managers', 'owners',)})

##     def test_nonregr_using_tuple_as_relation_target(self):
##         rschema = schema.rschema('see_also')
##         self.assertEqual(rschema.symmetric, False)
##         self.assertEqual(rschema.description, '')
##         self.assertEqual(rschema.final, False)
##         self.assertListEqual(sorted(rschema.subjects()), ['Employee'])
##         self.assertListEqual(sorted(rschema.objects()), ['Company', 'Division'])
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
    i = B.Int(required=True, metadata={'name': B.String()})
    f = B.Float()
    d = B.Datetime()



class PySchemaTC(TestCase):

    def test_python_inheritance(self):
        bp = BasePerson()
        p = Person()
        e = Employee()
        self.assertEqual([r.name for r in bp.__relations__], ['firstname', 'lastname'])
        self.assertEqual([r.name for r in p.__relations__], ['firstname', 'lastname', 'email'])
        self.assertEqual([r.name for r in e.__relations__], ['firstname', 'lastname', 'email', 'company'])

    def test_schema_extension(self):
        s = Student()
        self.assertEqual([r.name for r in s.__relations__], ['firstname', 'lastname', 'email', 'college'])
        self.assertEqual(s.specialized_type, 'Person')
        x = X()
        self.assertEqual(x.specialized_type, None)

    def test_relationtype(self):
        foo = Foo()
        self.assertEqual(['Int', 'String', 'Float', 'Datetime'],
                         [r.etype for r in foo.__relations__])
        self.assertEqual(foo.__relations__[0].cardinality, '11')
        self.assertEqual(foo.__relations__[2].cardinality, '?1')

    def test_maxsize(self):
        bp = BasePerson()
        def maxsize(e):
            for e in e.constraints:
                if isinstance(e, SizeConstraint):
                    return e.max
        self.assertEqual(maxsize(bp.__relations__[0]), 7)
        # self.assertEqual(maxsize(bp.__relations__[1]), 7)
        emp = Employee()
        self.assertEqual(maxsize(emp.__relations__[3]), 7)

    def test_metadata(self):
        foo = Foo()
        self.assertEqual('i_name', foo.__relations__[1].name)


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
        self.assertTrue(abs(delta.seconds) < 5)
        self.assertEqual(date(dt2.year, dt2.month, dt2.day), _today)
        self.assertIsInstance(dt2, datetime)
        # dates
        self.assertEqual(d1, _today)
        self.assertIsInstance(d1, date)
        self.assertEqual(d2, datetime(2007, 12, 11, 0, 0))
        self.assertIsInstance(d2, datetime)
        # times
        self.assertEqual(t1, time(8, 40))
        self.assertIsInstance(t1, time)
        self.assertEqual(t2, time(9, 45))
        self.assertIsInstance(t2, time)


class SchemaLoaderTC2(TestCase):

    def tearDown(self):
        SchemaLoader.main_schema_directory = 'schema'

    def test_broken_schema1(self):
        SchemaLoader.main_schema_directory = 'brokenschema1'
        with self.assertRaises(BadSchemaDefinition) as cm:
            SchemaLoader().load([DATADIR], 'Test')
        try:
            self.assertEqual(str(cm.exception), "conflicting values False/True for property inlined of relation 'rel'")
        except AssertionError:
            self.assertEqual(str(cm.exception), "conflicting values True/False for property inlined of relation 'rel'")


    def test_broken_schema2(self):
        SchemaLoader.main_schema_directory = 'brokenschema2'
        with self.assertRaises(BadSchemaDefinition) as cm:
            SchemaLoader().load([DATADIR], 'Test')
        try:
            self.assertEqual(str(cm.exception), "conflicting values True/False for property inlined of relation 'rel'")
        except AssertionError:
            self.assertEqual(str(cm.exception), "conflicting values False/True for property inlined of relation 'rel'")

    def test_broken_schema3(self):
        SchemaLoader.main_schema_directory = 'brokenschema3'
        with self.assertRaises(BadSchemaDefinition) as cm:
            SchemaLoader().load([DATADIR], 'Test')
        try:
            self.assertEqual(str(cm.exception), "conflicting values True/False for property inlined of relation 'rel'")
        except AssertionError:
            self.assertEqual(str(cm.exception), "conflicting values False/True for property inlined of relation 'rel'")

    def test_broken_schema4(self):
        schema = Schema('toto')
        schema.add_entity_type(buildobjs.EntityType(name='Entity'))
        schema.add_entity_type(buildobjs.EntityType(name='Int'))
        schema.add_relation_type(buildobjs.RelationType(name='toto'))
        with self.assertRaises(BadSchemaDefinition) as cm:
            schema.add_relation_def(buildobjs.RelationDefinition(
                name='toto', subject='Entity', object='Int',
                constraints=[SizeConstraint(40)]))
        self.assertEqual(str(cm.exception), "size constraint doesn't apply to Int entity type")

    def test_broken_schema5(self):
        schema = Schema('toto')
        schema.add_entity_type(buildobjs.EntityType(name='Entity'))
        schema.add_entity_type(buildobjs.EntityType(name='String'))
        schema.add_relation_type(buildobjs.RelationType(name='toto'))
        with self.assertRaises(BadSchemaDefinition) as cm:
            schema.add_relation_def(buildobjs.RelationDefinition(
                name='toto', subject='Entity', object='String',
                constraints=[StaticVocabularyConstraint(['ab', 'abc']),
                             SizeConstraint(2)]))
        self.assertEqual(str(cm.exception), "size constraint set to 2 but vocabulary contains string of greater size")

    def test_broken_schema6(self):
        schema = Schema('foo')
        rtype = buildobjs.RelationType(name='foo', __permissions__={'read': ()})
        schema.add_entity_type(buildobjs.EntityType(name='Entity'))
        schema.add_entity_type(buildobjs.EntityType(name='String'))
        schema.add_relation_type(rtype)
        class rdef(buildobjs.RelationDefinition):
            name = 'foo'
            subject = 'Entity'
            object = 'String'
            __permissions__ = {'add':()}
        with self.assertRaises(BadSchemaDefinition) as cm:
            rdef.expand_relation_definitions({'foo': rtype}, schema)
        self.assertEqual(str(cm.exception), "conflicting values {'add': ()}/{'read': ()} for property __permissions__ of relation 'foo'")

    def test_schema(self):
        SchemaLoader.main_schema_directory = 'schema2'
        schema = SchemaLoader().load([DATADIR], 'Test')
        rel = schema['rel']
        self.assertEqual(rel.rdef('Anentity', 'Anentity').composite,
                          'subject')
        self.assertEqual(rel.rdef('Anotherentity', 'Anentity').composite,
                          'subject')
        self.assertEqual(rel.rdef('Anentity', 'Anentity').cardinality,
                          '1*')
        self.assertEqual(rel.rdef('Anotherentity', 'Anentity').cardinality,
                          '1*')
        self.assertEqual(rel.symmetric, True)
        self.assertEqual(rel.inlined, True)

    def test_imports(self):
        SchemaLoader.main_schema_directory = 'schema'
        schema = SchemaLoader().load([DATADIR, DATADIR+'2'], 'Test')
        self.assertEqual(schema['Affaire'].permissions, {'read': (),
                                                          'add': (),
                                                          'update': (),
                                                          'delete': ()})
        self.assertEqual([str(r) for r,at in schema['MyNote'].attribute_definitions()],
                          ['date', 'type', 'para', 'text'])

    def test_duplicated_rtype(self):
        loader = SchemaLoader()
        loader.defined = {}
        class RT1(RelationType):
            pass
        loader.add_definition(RT1)
        with self.assertRaises(BadSchemaDefinition) as cm:
            loader.add_definition(RT1)
        self.assertEqual(str(cm.exception), 'duplicated relation type for RT1')

    def test_rtype_priority(self):
        loader = SchemaLoader()
        loader.defined = {}
        class RT1Def(RelationDefinition):
            name = 'RT1'
            subject = 'Whatever'
            object = 'Whatever'
        class RT1(RelationType):
            pass
        loader.add_definition(RT1Def)
        loader.add_definition(RT1)
        self.assertEqual(loader.defined['RT1'], RT1)

    def test_unfinalized_manipulation(self):
        expected_attributes = ['base_arg_a', 'base_arg_b', 'new_arg_a',
                               'new_arg_b']
        expected_relations = ['base_o_obj', 'base_o_sub', 'base_obj',
                              'base_sub', 'new_o_obj', 'new_o_sub', 'new_obj',
                              'new_sub']

        SchemaLoader.main_schema_directory = 'schema_unfinalized_manipulation'
        schema = SchemaLoader().load([DATADIR], 'Test')
        self.assertIn('MyEntity', schema.entities())
        my_entity = schema['MyEntity']
        attributes_def = my_entity.attribute_definitions()
        attributes = sorted(attr[0].type for attr in attributes_def)
        self.assertEqual( attributes, expected_attributes)
        relations_def = my_entity.relation_definitions()
        relations = sorted( rel[0].type for rel in relations_def)
        self.assertEqual( relations, expected_relations)

    def test_post_build_callback(self):
        SchemaLoader.main_schema_directory = 'post_build_callback'
        schema = SchemaLoader().load([DATADIR], 'Test')
        self.assertIn('Toto', schema.entities())

class BuildSchemaTC(TestCase):

    def test_build_schema(self):
        from yams.buildobjs import EntityType, RelationDefinition, Int, String

        class Question(EntityType):
            number = Int()
            text = String()

        class Form(EntityType):
            title = String()

        class in_form(RelationDefinition):
            subject = 'Question'
            object = 'Form'
            cardinality = '*1'

        schema = build_schema_from_namespace(vars().items())
        entities = [x for x in schema.entities() if not x.final]
        self.assertItemsEqual(['Form', 'Question'], entities)
        relations = [x for x in schema.relations() if not x.final]
        self.assertItemsEqual(['in_form'], relations)

if __name__ == '__main__':
    unittest_main()


