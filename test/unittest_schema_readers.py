"""unit tests for module yams.reader

Copyright Logilab 2003-2006, all rights reserved.
"""

from logilab.common.testlib import TestCase, unittest_main
from logilab.common.compat import sorted

from yams.schema import Schema, EntitySchema
from yams.reader import SchemaLoader, RelationFileReader

import os.path as osp

DATADIR = osp.abspath(osp.join(osp.dirname(__file__),'data'))

class DummyDefaultHandler:

    def default_modname(self):
        return 'yo'
    
    def vocabulary_license(self):
        return ['GPL', 'ZPL']
    
    def vocabulary_debian_handler(self):
        return ['machin', 'bidule']

schema = SchemaLoader().load(DATADIR, 'Test', DummyDefaultHandler())


class SchemaLoaderTC(TestCase):

    # test helper functions ###################################################
    
    def test_get_schema_files(self):
        files = sorted([osp.basename(f) for f in SchemaLoader().get_schema_files(DATADIR)])
        self.assertEquals(files,
                          ['Affaire.sql', 'Note.sql', 'Person.sql', 'Societe.sql',
                           'State.py', 'pkginfo.esql', 'relations.rel'])
    
    def test_include(self):
        files = SchemaLoader().include_schema_files('Person', DATADIR)
        self.assertEquals(files, [osp.join(DATADIR,'Person.sql')])
        files = SchemaLoader().include_schema_files('pkginfo', DATADIR)
        self.assertEquals(files, [osp.join(DATADIR, 'pkginfo.esql')])

    # test load_schema readen entity and relation types #######################
    
    def test_load_schema(self):
        self.assert_(isinstance(schema, Schema))
        self.assertEquals(schema.name, 'Test')
        self.assertListEquals(sorted(schema.entities()),
                              ['Affaire', 'Boolean', 'Bytes', 'Date', 'Datetime',
                               'Eetype',  'Float', 'Int', 'Note', 'Password',
                               'Person', 'Societe', 'State', 'String', 'Time',
                               'pkginfo'])
        self.assertListEquals(sorted(schema.relations()),
                              ['ad1', 'ad2', 'ad3', 'adel', 'ass', 'author', 'author_email',
                               'concerne', 'copyright', 'cp',
                               'date', 'datenaiss', 'debian_handler', 'description',
                               'eid', 'evaluee', 'fax', 'final',
                               'initial_state', 'inline_rel',
                               'license', 'long_desc',
                               'mailinglist', 'meta', 'modname',
                               'name', 'next_state', 'nom', 'obj_wildcard',
                               'para', 'prenom', 'promo', 'pyversions',
                               'ref', 'rncs',
                               'sexe', 'short_desc', 'state_of', 'subj_wildcard', 'sujet', 'sym_rel',
                               'tel', 'test', 'titre', 'travaille', 'type',
                               'version', 
                               'ville', 'web'])

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
        self.assertListEquals(sorted(rschema.subjects()), ['Eetype', 'State'])
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
        
    def test_physical_mode(self):
        rschema = schema.rschema('evaluee')
        self.assertEquals(rschema.physical_mode(), None)
        rschema = schema.rschema('inline_rel')        
        self.assertEquals(rschema.physical_mode(), 'subjectinline')
        rschema = schema.rschema('initial_state')        
        self.assertEquals(rschema.physical_mode(), 'subjectinline')
        rschema = schema.rschema('state_of')
        self.assertEquals(rschema.physical_mode(), None)



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
        


from yams import builder as B

class BasePerson(B.EntityType):
    firstname = B.String()
    lastname = B.String()

class Person(BasePerson):
    email = B.String()

class Employee(Person):
    company = B.String()

class Foo(B.EntityType):
    i = B.Int(required=True)
    f = B.Float()
    d = B.Datetime()
    

class PySchemaTC(TestCase):

    def test_inheritance(self):        
        bp = BasePerson()
        p = Person()
        e = Employee()
        self.assertEquals([r.name for r in bp.relations], ['firstname', 'lastname'])
        self.assertEquals([r.name for r in p.relations], ['firstname', 'lastname', 'email'])
        self.assertEquals([r.name for r in e.relations], ['firstname', 'lastname', 'email', 'company'])
        

    def test_relationtype(self):
        foo = Foo()
        self.assertEquals([r.etype for r in foo.relations],
                          ['Int', 'Float', 'Datetime'])
        self.assertEquals(foo.relations[0].cardinality, '11')
        self.assertEquals(foo.relations[1].cardinality, '?1')
        

if __name__ == '__main__':
    unittest_main()
