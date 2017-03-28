# copyright 2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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

"""unit tests for module yams.diff"""

from logilab.common.testlib import TestCase, unittest_main

from yams.reader import build_schema_from_namespace
from yams.buildobjs import String, Int, Float, EntityType, SubjectRelation
from yams.diff import properties_from, schema_diff


class PersonBase(EntityType):
    nom = String()
    prenom = String()


class PersonAttrMod(EntityType):
    nom = String()
    prenom = Float()


class PersonAttrAdd(EntityType):
    nom = String()
    prenom = String()
    age = Int()
    is_friend_of = SubjectRelation('PersonAttrMod')


class PersonAttrAdd2(EntityType):
    nom = String()
    prenom = String()
    salaire = Float()
    is_friend_of = SubjectRelation('PersonAttrAdd')


class PersonAttrAdd3(EntityType):
    nom = String()
    prenom = String()
    age = Int()
    salaire = Float()
    is_spouse_of = SubjectRelation('PersonAttrAdd')


def create_schema_1():
    class Affaire(EntityType):
        nom = String()
        associate_affaire = SubjectRelation('Affaire')
    return build_schema_from_namespace([('PersonBase', PersonBase),
                                        ('Affaire',    Affaire),
                                        ('PersonAttrMod', PersonAttrMod)])


def create_schema_2():
    class Affaire(EntityType):
        nom = String(maxsize=150)
        numero = Int()
        associate_affaire = SubjectRelation('Affaire', cardinality='**')
        associate_person = SubjectRelation('PersonBase')
    return build_schema_from_namespace([('PersonBase', PersonBase),
                                        ('Affaire',    Affaire)])


class PropertiesFromTC(TestCase):

    expected_default_attr_perms = (
        " {\n\t\t\t'read': ('guests','managers','users'),"
        "\n\t\t\t'add': ('managers','users'),"
        "\n\t\t\t'update': ('managers','owners')\n\t\t}")

    def build_rdef(self, props_ref):
        class AType(EntityType):
            attr = String(**props_ref)
        schema = build_schema_from_namespace(locals().items())
        return schema['AType'].rdef('attr')

    def build_props_dict(self, props_ref):
        result = {'default': None,
                  'description': '',
                  'fulltextindexed': False,
                  'indexed': False,
                  'internationalizable': False,
                  'order': 1,
                  'required': False,
                  'uid': False}
        result.update(props_ref)
        return result

    def test_properties_from_final_attributes_1(self):
        props_ref = {'required': True, 'default': 'toto',
                     'description': 'something'}
        self.assertEqual({'default': 'toto',
                          'required': True,
                          '__permissions__': self.expected_default_attr_perms,
                          'description': "'something'",
                          'order': 1},
                         properties_from(self.build_rdef(props_ref)),
                         )

    def test_properties_from_final_attributes_2(self):
        props_ref = {}
        self.assertEqual({'__permissions__': self.expected_default_attr_perms,
                          'order': 1},
                         properties_from(self.build_rdef(props_ref)))

    def test_properties_from_final_attributes_3(self):
        props_ref = {'default': None, 'required': False}
        self.assertEqual({'__permissions__': self.expected_default_attr_perms,
                          'order': 1},
                         properties_from(self.build_rdef(props_ref)))

    def test_constraint_properties_1(self):
        props_ref = {'maxsize': 150, 'required': False}
        self.assertEqual({'maxsize': 150,
                          '__permissions__': self.expected_default_attr_perms,
                          'order': 1},
                         properties_from(self.build_rdef(props_ref)))

    def test_constraint_properties_2(self):
        props_ref = {'unique': True, 'required': False}
        self.assertEqual({'__permissions__': self.expected_default_attr_perms,
                          'unique': True,
                          'order': 1},
                         properties_from(self.build_rdef(props_ref)))

    def test_constraint_properties_3(self):
        props_ref = {'vocabulary': ('aaa', 'bbbb', 'ccccc'), 'required': False,
                     'maxsize': 20}
        rdef = self.build_rdef(props_ref)
        props_ref['maxsize'] = 5
        self.assertEqual({'maxsize': 5,
                          '__permissions__': self.expected_default_attr_perms,
                          'order': 1,
                          'vocabulary': [u'aaa', u'bbbb', u'ccccc']},
                         properties_from(rdef))

    def test_permissions(self):
        props_ref = {'__permissions__': {
            'add': ('managers', 'users'),
            'update': ('owners', 'managers'),
            'read': ('users', 'managers', 'guests'),
            },
        }
        rdef = self.build_rdef(props_ref)
        self.assertEqual({'__permissions__': self.expected_default_attr_perms,
                          'order': 1,
                          }, properties_from(rdef))


class SchemaDiff(TestCase):

    def test_schema_diff(self):
        schema1 = create_schema_1()
        schema2 = create_schema_2()
        output1, output2 = schema_diff(schema1, schema2)
        self.assertMultiLineEqual(open(output1).read(),
                                  open(self.datapath('schema1.txt')).read())
        self.assertMultiLineEqual(open(output2).read(),
                                  open(self.datapath('schema2.txt')).read())


if __name__ == '__main__':
    unittest_main()
