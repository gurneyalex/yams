"""specialization tests
"""
from logilab.common.testlib import TestCase, unittest_main

from yams.reader import SchemaLoader



class SpecializationTC(TestCase):
    def setUp(self):
        SchemaLoader.main_schema_directory = 'spschema'
        self.schema = SchemaLoader().load([self.datadir], 'Test')

    def tearDown(self):
        SchemaLoader.main_schema_directory = 'schema'

    def test_specialized_by(self):
        eschema = self.schema.eschema('Company')
        self.assertEquals(sorted(eschema.specialized_by(False)),
                          ['Division', 'SubCompany'])
        self.assertEquals(sorted(eschema.specialized_by(True)),
                          ['Division', 'SubCompany', 'SubDivision'])
        
    def test_relations_infered(self):
        entities = [str(e) for e in self.schema.entities() if not e.is_final()]
        relations = sorted([r for r in self.schema.relations() if not r.final])
        self.assertListEquals(sorted(entities), ['Company', 'Division', 'Person',
                                                 'Student', 'SubCompany', 'SubDivision', 'SubSubCompany'])
        self.assertListEquals(relations, ['division_of', 'knows', 'works_for'])
        expected = {('Person', 'Person'): False,
                    ('Person', 'Student'): True,
                    # as Student extends Person, it already has the `knows` relation
                    ('Student', 'Person'): False,
                    ('Student', 'Student'): True,
                    }
        done = set()
        drschema, krschema, wrschema = relations
        for subjobj in krschema.rdefs():
            subject, object = subjobj
            done.add(subjobj)
            self.failUnless(subjobj in expected)
            self.assertEquals(krschema.rproperty(subject, object, 'infered'),
                              expected[subjobj])
        self.assertEquals(len(set(expected) - done), 0, 'missing %s' % (set(expected) - done))
        expected = {('Person', 'Company'): False,
                    ('Person', 'Division'): True,
                    ('Person', 'SubDivision'): True,
                    ('Person', 'SubCompany'): True,
                    ('Student', 'Company'): False,
                    ('Student', 'Division'): True,
                    ('Student', 'SubDivision'): True,
                    ('Student', 'SubCompany'): True,
                    }
        done = set()
        for subjobj in wrschema.rdefs():
            subject, object = subjobj
            done.add(subjobj)
            self.failUnless(subjobj in expected)
            self.assertEquals(wrschema.rproperty(subject, object, 'infered'),
                              expected[subjobj])
        self.assertEquals(len(set(expected) - done), 0, 'missing %s' % (set(expected) - done))


if __name__ == '__main__':
    unittest_main()
    
