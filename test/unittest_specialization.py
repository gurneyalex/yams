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

    def test_schema_specialization(self):
        schema = self.schema
        # company
        company = schema.eschema('Company')
        self.assertEquals(company.specializes(), None)
        # division
        division = schema.eschema('Division')
        self.assertEquals(division.specializes().type, 'Company')
        # subdivision
        subdivision = schema.eschema('SubDivision')
        self.assertEquals(subdivision.specializes().type, 'Division')
        # subsubdivision
        subsubdivision = schema.eschema('SubSubDivision')
        self.assertEquals(subsubdivision.specializes(), None)

    def test_ancestors(self):
        schema = self.schema
        # company
        company = schema.eschema('Company')
        self.assertEquals(company.ancestors(), [])
        # division
        division = schema.eschema('Division')
        self.assertEquals(division.ancestors(), ['Company'])
        # subdivision
        subdivision = schema.eschema('SubDivision')
        self.assertEquals(subdivision.ancestors(), ['Division', 'Company'])
        # subsubdivision
        subsubdivision = schema.eschema('SubSubDivision')
        self.assertEquals(subsubdivision.ancestors(), [])

    def test_specialized_by(self):
        schema = self.schema
        # company
        company = schema.eschema('Company')
        self.assertEquals(sorted(company.specialized_by(False)), ['Division', 'SubCompany'])
        self.assertEquals(sorted(company.specialized_by(True)), ['Division', 'SubCompany', 'SubDivision'])
        # division
        division = schema.eschema('Division')
        self.assertEquals(sorted(division.specialized_by(False)), ['SubDivision'])
        self.assertEquals(sorted(division.specialized_by(True)), ['SubDivision'])
        # subdivision
        subdivision = schema.eschema('SubDivision')
        self.assertEquals(sorted(subdivision.specialized_by(False)), [])
        # subsubdivision
        subsubdivision = schema.eschema('SubSubDivision')
        self.assertEquals(subsubdivision.specialized_by(False), [])

    def test_relations_infered(self):
        entities = [str(e) for e in self.schema.entities() if not e.final]
        relations = sorted([r for r in self.schema.relations() if not r.final])
        self.assertListEquals(sorted(entities), ['Company', 'Division', 'Person',
                                                 'Student', 'SubCompany', 'SubDivision', 'SubSubDivision'])
        self.assertListEquals(relations, ['division_of', 'knows', 'works_for'])
        expected = {('Person', 'Person'): False,
                    ('Person', 'Student'): True,
                    # as Student extends Person, it already has the `knows` relation
                    ('Student', 'Person'): False,
                    ('Student', 'Student'): True,
                    }
        done = set()
        drschema, krschema, wrschema = relations
        for subjobj in krschema.rdefs:
            subject, object = subjobj
            done.add(subjobj)
            self.failUnless(subjobj in expected)
            self.assertEquals(krschema.rdef(subject, object).infered,
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
        for subjobj in wrschema.rdefs:
            subject, object = subjobj
            done.add(subjobj)
            self.failUnless(subjobj in expected)
            self.assertEquals(wrschema.rdef(subject, object).infered,
                              expected[subjobj])
        self.assertEquals(len(set(expected) - done), 0, 'missing %s' % (set(expected) - done))

    def test_remove_infered_relations(self):
        self.schema.remove_infered_definitions()
        relations = sorted([r for r in self.schema.relations() if not r.final])
        self.assertListEquals(relations, ['division_of', 'knows', 'works_for'])
        expected = {('Person', 'Person'): False,
                    # as Student extends Person, it already has the `knows` relation
                    ('Student', 'Person'): False,
                    }
        done = set()
        drschema, krschema, wrschema = relations
        for subjobj in krschema.rdefs:
            subject, object = subjobj
            done.add(subjobj)
            self.failUnless(subjobj in expected)
            self.assertEquals(krschema.rdef(subject, object).infered,
                              expected[subjobj])
        self.assertEquals(len(set(expected) - done), 0, 'missing %s' % (set(expected) - done))
        expected = {('Person', 'Company'): False,
                    ('Student', 'Company'): False,
                   }
        done = set()
        for subjobj in wrschema.rdefs:
            subject, object = subjobj
            done.add(subjobj)
            self.failUnless(subjobj in expected)
            self.assertEquals(wrschema.rdef(subject, object).infered,
                              expected[subjobj])
        self.assertEquals(len(set(expected) - done), 0, 'missing %s' % (set(expected) - done))


if __name__ == '__main__':
    unittest_main()
