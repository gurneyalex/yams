# copyright 2004-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
        self.assertEqual(company.specializes(), None)
        # division
        division = schema.eschema('Division')
        self.assertEqual(division.specializes().type, 'Company')
        # subdivision
        subdivision = schema.eschema('SubDivision')
        self.assertEqual(subdivision.specializes().type, 'Division')
        # subsubdivision
        subsubdivision = schema.eschema('SubSubDivision')
        self.assertEqual(subsubdivision.specializes(), None)

    def test_ancestors(self):
        schema = self.schema
        # company
        company = schema.eschema('Company')
        self.assertEqual(company.ancestors(), [])
        # division
        division = schema.eschema('Division')
        self.assertEqual(division.ancestors(), ['Company'])
        # subdivision
        subdivision = schema.eschema('SubDivision')
        self.assertEqual(subdivision.ancestors(), ['Division', 'Company'])
        # subsubdivision
        subsubdivision = schema.eschema('SubSubDivision')
        self.assertEqual(subsubdivision.ancestors(), [])

    def test_specialized_by(self):
        schema = self.schema
        # company
        company = schema.eschema('Company')
        self.assertEqual(sorted(company.specialized_by(False)), ['Division', 'SubCompany'])
        self.assertEqual(sorted(company.specialized_by(True)), ['Division', 'SubCompany', 'SubDivision'])
        # division
        division = schema.eschema('Division')
        self.assertEqual(sorted(division.specialized_by(False)), ['SubDivision'])
        self.assertEqual(sorted(division.specialized_by(True)), ['SubDivision'])
        # subdivision
        subdivision = schema.eschema('SubDivision')
        self.assertEqual(sorted(subdivision.specialized_by(False)), [])
        # subsubdivision
        subsubdivision = schema.eschema('SubSubDivision')
        self.assertEqual(subsubdivision.specialized_by(False), [])

    def test_relations_infered(self):
        entities = [str(e) for e in self.schema.entities() if not e.final]
        relations = sorted([r for r in self.schema.relations() if not r.final])
        self.assertListEqual(sorted(entities), ['Company', 'Division', 'Person',
                                                 'Student', 'SubCompany', 'SubDivision', 'SubSubDivision'])
        self.assertListEqual(relations, ['division_of', 'knows', 'works_for'])
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
            self.assertTrue(subjobj in expected)
            self.assertEqual(krschema.rdef(subject, object).infered,
                              expected[subjobj])
        self.assertEqual(len(set(expected) - done), 0, 'missing %s' % (set(expected) - done))
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
            self.assertTrue(subjobj in expected)
            self.assertEqual(wrschema.rdef(subject, object).infered,
                              expected[subjobj])
        self.assertEqual(len(set(expected) - done), 0, 'missing %s' % (set(expected) - done))

    def test_remove_infered_relations(self):
        self.schema.remove_infered_definitions()
        relations = sorted([r for r in self.schema.relations() if not r.final])
        self.assertListEqual(relations, ['division_of', 'knows', 'works_for'])
        expected = {('Person', 'Person'): False,
                    # as Student extends Person, it already has the `knows` relation
                    ('Student', 'Person'): False,
                    }
        done = set()
        drschema, krschema, wrschema = relations
        for subjobj in krschema.rdefs:
            subject, object = subjobj
            done.add(subjobj)
            self.assertTrue(subjobj in expected)
            self.assertEqual(krschema.rdef(subject, object).infered,
                              expected[subjobj])
        self.assertEqual(len(set(expected) - done), 0, 'missing %s' % (set(expected) - done))
        expected = {('Person', 'Company'): False,
                    ('Student', 'Company'): False,
                   }
        done = set()
        for subjobj in wrschema.rdefs:
            subject, object = subjobj
            done.add(subjobj)
            self.assertTrue(subjobj in expected)
            self.assertEqual(wrschema.rdef(subject, object).infered,
                              expected[subjobj])
        self.assertEqual(len(set(expected) - done), 0, 'missing %s' % (set(expected) - done))


if __name__ == '__main__':
    unittest_main()
