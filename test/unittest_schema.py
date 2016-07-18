# -*- coding: iso-8859-1 -*-
# copyright 2004-2014 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
"""unit tests for module yams.schema classes"""

from logilab.common.testlib import TestCase, unittest_main

from copy import copy, deepcopy
from tempfile import mktemp

from six import text_type

from yams import (BASE_TYPES, ValidationError, BadSchemaDefinition,
                  register_base_type, unregister_base_type)
from yams.buildobjs import (register_base_types, make_type, _add_relation,
                            EntityType, RelationType, RelationDefinition,
                            RichString)
from yams.schema import Schema, RelationDefinitionSchema
from yams.interfaces import IVocabularyConstraint
from yams.constraints import (BASE_CHECKERS, SizeConstraint, RegexpConstraint,
                              StaticVocabularyConstraint, IntervalBoundConstraint,
                              FormatConstraint)
from yams.reader import SchemaLoader
from yams.buildobjs import register_base_types


# build a dummy schema ########################################################


class BaseSchemaTC(TestCase):
    def setUp(self):
        global schema, enote, eaffaire, eperson, esociete, estring, eint
        global rconcerne, rnom
        schema = Schema('Test Schema')
        register_base_types(schema)
        enote = schema.add_entity_type(EntityType('Note'))
        eaffaire = schema.add_entity_type(EntityType('Affaire'))
        eperson = schema.add_entity_type(EntityType('Person'))
        esociete = schema.add_entity_type(EntityType('Societe'))


        RELS = (
            # attribute relations
            ('Note date Datetime'),
            ('Note type String'),
            ('Affaire sujet String'),
            ('Affaire ref String'),
            ('Affaire starton Time'),
            ('Person nom String'),
            ('Person prenom String'),
            ('Person sexe Float'),
            ('Person tel Int'),
            ('Person fax Int'),
            ('Person datenaiss Date'),
            ('Person TEST Boolean'),
            ('Person promo String'),
            ('Person promo_enlarged String'),
            ('Person promo_encoding String'),
            ('Person promo_format String'),
            # real relations
            ('Person  travaille Societe'),
            ('Person  evaluee   Note'),
            ('Societe evaluee   Note'),
            ('Person  concerne  Affaire'),
            ('Person  concerne  Societe'),
            ('Affaire concerne  Societe'),
            )
        for i, rel in enumerate(RELS):
            _from, _type, _to = rel.split()
            try:
                schema.rschema(_type)
            except KeyError:
                schema.add_relation_type(RelationType(_type))
            schema.add_relation_def(RelationDefinition(_from, _type, _to, order=i))
        schema.rschema('nom').rdef('Person', 'String').cardinality = '11' # not null

        enote.rdef('type').constraints = [StaticVocabularyConstraint((u'bon', u'pasbon',
                                                                      u'bof', u'peux mieux faire'))]
        enote.rdef('date').cardinality = '11'

        eaffaire.rdef('sujet').constraints = [SizeConstraint(128)]
        eaffaire.rdef('ref').constraints = [SizeConstraint(12), RegexpConstraint(r'[A-Z]+\d+')]
        eperson.rdef('nom').constraints = [SizeConstraint(20, 10)]
        eperson.rdef('prenom').constraints = [SizeConstraint(64)]
        eperson.rdef('tel').constraints = [IntervalBoundConstraint(maxvalue=999999)]
        eperson.rdef('fax').constraints = [IntervalBoundConstraint(minvalue=12, maxvalue=999999)]
        eperson.rdef('promo').constraints = [StaticVocabularyConstraint( (u'bon', u'pasbon'))]
        eperson.rdef('promo_format').constraints = [FormatConstraint()]

        estring = schema.eschema('String')
        eint = schema.eschema('Int')
        rconcerne = schema.rschema('concerne')
        rnom = schema.rschema('nom')

    def assertRaisesMsg(self, ex_class, msg, func, *args, **kwargs):
        self.assertRaises(ex_class, func, *args, **kwargs)
        try:
            func(*args, **kwargs)
        except Exception as ex:
            self.assertEqual(str(ex), msg)

# test data ###################################################################

BAD_RELS = ( ('Truc badrelation1 Affaire'),
             ('Affaire badrelation2 Machin'),
             )

ATTRIBUTE_BAD_VALUES = (
    ('Person', [('nom', 1), ('nom', u'tropcour'),
                ('nom', u'>10 mais  supérieur à < 20 , c\'est long'),
                ('sexe', u'F'), ('sexe', u'MorF'), ('sexe', 'F'),
                ('promo', b'bon'), ('promo', 'uyou'),
                ('promo', u' pas bon du tout'),
                ('promo_format', u'text/something'),
                ('tel', 'notastring'),
                ('tel', 1000000),
                ('fax', 11),
                ('TEST', 'notaboolean'), #('TEST', 0), ('TEST', 1)]), #should we accept this ?
                ('TEST', 'true'), ('TEST', 'false')]),
## the date and time are not checked for now
##    ('Person', [('nom', u' >10 mais < 20 '),
##               ('datenaiss', '979-06-12')]),
##    ('Note', [('date', '2229-01-31 minuit')]),
##    ('Affaire', [('starton', 'midi')]),

    ('Note', [('type', ['bof', 'peux mieux faire']),
              ('type', 'bof, je suis pas unicode, alors...'),
              ('date', None),
              ]),
    ('Affaire', [('ref', 'ginco01'), ('ref', 'GINCO'),],
    ),
    )

ATTRIBUTE_GOOD_VALUES = (
    ('Person', [('nom', u'>10 mais < 20 '), ('sexe', 0.5),
                ('promo', u'bon'),
                ('datenaiss', '1977-06-07'),
                ('tel', 83433), ('fax', None), ('fax', 12),
                ('TEST', True), ('TEST', False)]),
    ('Note', [('date', '2229-01-31 00:00')]),
    ('Affaire', [('starton', '00:00'),
                 ('ref', u'GINCO01')]),
    )

RELATIONS_BAD_VALUES = {
    'travaille': [('Person', 'Affaire'), ('Affaire', 'Societe'),
                  ('Affaire', 'Societe'), ('Societe', 'Person')]
    }
RELATIONS_GOOD_VALUES = {
    'travaille': [('Person', 'Societe')],
    'concerne': [('Person', 'Affaire'), ('Affaire', 'Societe')]
    }


# test suite ##################################################################

class EntitySchemaTC(BaseSchemaTC):

    def test_base(self):
        self.assertTrue(repr(eperson))

    def test_cmp(self):
        self.assertTrue(eperson == 'Person')
        self.assertFalse(eperson != 'Person')
        self.assertTrue('Person' == eperson)
        self.assertTrue(eperson != 'Note')
        self.assertTrue('Note' != eperson)
        self.assertFalse(enote == eperson)
        self.assertFalse(eperson == enote)
        self.assertTrue(enote != eperson)
        self.assertTrue(eperson != enote)
        l = [eperson, enote, eaffaire, esociete]
        l.sort()
        self.assertListEqual(l, [eaffaire, enote, eperson, esociete])
        self.assertListEqual(l, ['Affaire', 'Note', 'Person', 'Societe'])

    def test_hash(self):
        d = {}
        d[eperson] = 'p'
        d[enote] = 'n'
        self.assertEqual(d[copy(eperson)], 'p')
        self.assertEqual(d[copy(enote)], 'n')
        self.assertEqual(d['Person'], 'p')
        self.assertEqual(d['Note'], 'n')
        d = {}
        d['Person'] = eperson
        d['Note'] = enote
        self.assertEqual(copy(eperson), 'Person')
        self.assertEqual(d[copy(eperson)], 'Person')
        self.assertEqual(d[copy(enote)], 'Note')

    def test_deepcopy_with_regexp_constraints(self):
        eaffaire.rdef('ref').constraints = [RegexpConstraint(r'[A-Z]+\d+')]
        rgx_cstr, = eaffaire.rdef('ref').constraints
        eaffaire2 = deepcopy(schema).eschema('Affaire')
        rgx_cstr2, = eaffaire2.rdef('ref').constraints
        self.assertEqual(rgx_cstr2.regexp, rgx_cstr.regexp)
        self.assertEqual(rgx_cstr2.flags, rgx_cstr.flags)
        self.assertEqual(rgx_cstr2._rgx, rgx_cstr._rgx)

    def test_deepcopy(self):
        global schema
        schema = deepcopy(schema)
        self.assertFalse(eperson is schema['Person'])
        self.assertEqual(eperson, schema['Person'])
        self.assertEqual('Person', schema['Person'])
        self.assertCountEqual(eperson.subject_relations(), schema['Person'].subject_relations())
        self.assertCountEqual(eperson.object_relations(), schema['Person'].object_relations())
        self.assertEqual(schema.eschema('Person').final, False)
        self.assertEqual(schema.eschema('String').final, True)
        self.assertEqual(schema.rschema('ref').final, True)
        self.assertEqual(schema.rschema('concerne').final, False)

    def test_attribute_description(self):
        schema = SchemaLoader().load([self.datadir], 'Test')
        self.assertEqual(schema['EPermission'].rdef('name').description,
                         'name or identifier of the permission')

    def test_deepcopy_specialization(self):
        schema2 = deepcopy(SchemaLoader().load([self.datadir], 'Test'))
        edivision = schema2.eschema('Division')
        self.assertEqual(edivision.specializes(), 'Company')
        self.assertEqual(edivision.specialized_by(), ['Subdivision'])
        schema2.del_entity_type('Subdivision')
        self.assertEqual(edivision.specialized_by(), [])

    def test_is_final(self):
        self.assertEqual(eperson.final, False)
        self.assertEqual(enote.final, False)
        self.assertEqual(estring.final, True)
        self.assertEqual(eint.final, True)
        self.assertEqual(eperson.subjrels['nom'].final, True)
        #self.assertEqual(eperson.is_final('concerne'), False)
        self.assertEqual(eperson.subjrels['concerne'].final, False)

    def test_is_metadata(self):
        self.assertEqual(eperson.is_metadata('promo'), None)
        self.assertEqual(eperson.is_metadata('promo_enlarged'), None)
        self.assertEqual(eperson.is_metadata('promo_encoding'), ('promo', 'encoding'))
        self.assertCountEqual([(k.type, v)  for k, v in eperson.meta_attributes().items()],
                          [('promo_encoding', ('encoding', 'promo')),
                           ('promo_format', ('format', 'promo'))])

    def test_defaults(self):
        self.assertEqual(list(eperson.defaults()), [])
        self.assertRaises(StopIteration, next, estring.defaults())

    def test_vocabulary(self):
        #self.assertEqual(eperson.vocabulary('promo')
        self.assertEqual(eperson.rdef('promo').constraint_by_interface(IVocabularyConstraint).vocabulary(),
                          ('bon', 'pasbon'))
        # self.assertRaises(AssertionError,
        #                   eperson.vocabulary, 'nom')

    def test_indexable_attributes(self):
        eperson.rdef('nom').fulltextindexed = True
        eperson.rdef('prenom').fulltextindexed = True
        self.assertCountEqual(list(eperson.indexable_attributes()), ['nom', 'prenom'])


    def test_goodValues_relation_default(self):
        """check good values of entity does not raise an exception"""
        eperson.rdef('nom').default = 'No name'
        self.assertEqual(eperson.default('nom'), 'No name')

    def test_subject_relations(self):
        """check subject relations a returned in the same order as in the
        schema definition"""
        rels = eperson.ordered_relations()
        expected = ['nom', 'prenom', 'sexe', 'tel', 'fax', 'datenaiss', 'TEST',
                    'promo', 'promo_enlarged', 'promo_encoding', 'promo_format',
                    'travaille', 'evaluee', 'concerne']
        self.assertEqual([r.type for r in rels], expected)

    def test_object_relations(self):
        """check object relations a returned in the same order as in the
        schema definition"""
        rels = eaffaire.object_relations()
        expected = ['concerne']
        self.assertEqual(rels, expected)
        rels = [schem.type for schem in eaffaire.object_relations()]
        self.assertEqual(rels, expected)
        self.assertEqual(eaffaire.objrels['concerne'].type,
                         'concerne')

    def test_destination_type(self):
        """check subject relations a returned in the same order as in the
        schema definition"""
        self.assertEqual(eperson.destination('nom'), 'String')
        self.assertEqual(eperson.destination('travaille'), 'Societe')

    def test_check_unique_together1(self):
        eperson._unique_together = [('prenom', 'nom')]
        eperson.check_unique_together()

    def test_check_unique_together2(self):
        eperson._unique_together = [('prenom', 'noms')]
        with self.assertRaises(BadSchemaDefinition) as cm:
            eperson.check_unique_together()
        self.assertTrue('no such attribute or relation noms'
                        in cm.exception.args[0])

    def test_check_unique_together3(self):
        eperson._unique_together = [('nom', 'travaille')]
        with self.assertRaises(BadSchemaDefinition) as cm:
            eperson.check_unique_together()
        self.assertTrue('travaille is not an attribute or an inlined relation'
                        in cm.exception.args[0])


class RelationSchemaTC(BaseSchemaTC):

    def test_cmp(self):
        self.assertTrue(rconcerne == 'concerne')
        self.assertFalse(rconcerne != 'concerne')
        self.assertTrue('concerne' == rconcerne)
        self.assertTrue(rconcerne != 'nom')
        self.assertTrue('nom' != rconcerne)
        self.assertFalse(rnom == rconcerne)
        self.assertFalse(rconcerne == rnom)
        self.assertTrue(rnom != rconcerne)
        self.assertTrue(rconcerne != rnom)

    def test_hash(self):
        d = {}
        d[rconcerne] = 'p'
        d[rnom] = 'n'
        self.assertEqual(d[copy(rconcerne)], 'p')
        self.assertEqual(d[copy(rnom)], 'n')
        self.assertEqual(d['concerne'], 'p')
        self.assertEqual(d['nom'], 'n')


    def test_base(self):
        self.assertTrue(repr(rnom))

    def test_star_types(self):
        types = sorted(rconcerne.subjects())
        self.assertEqual(types, ['Affaire', 'Person'])
        types = sorted(rconcerne.objects())
        self.assertEqual(types, ['Affaire', 'Societe'])

    def test_raise_update(self):
        self.assertRaisesMsg(BadSchemaDefinition,
                             'type String can\'t be used as subject in a relation',
                             rconcerne.update, estring, enote, {})
##         self.assertRaisesMsg(BadSchemaDefinition,
##                              "can't have a final relation pointing to multiple entity types (nom: ['String', 'Int'])" ,
##                              rnom.update, enote, eint)
        msgref = ("ambiguous relation: 'Person.nom' is final (String) "
                  "but not 'Note.nom' (Affaire)")
        self.assertRaisesMsg(BadSchemaDefinition, msgref,
                             rnom.update, enote, eaffaire, {})
        self.assertRaises(BadSchemaDefinition,
                          rconcerne.update, enote, estring, {})

    def test_association_types(self):
        expected = [ ('Affaire', ['Societe']),
                     ('Person', ['Affaire', 'Societe']) ]
        assoc_types = rconcerne.associations()
        assoc_types.sort()
        self.assertEqual(assoc_types, expected)
        assoc_types = []
        for _from, _to in rconcerne.associations():
            assoc_types.append( (_from, _to))
            #assoc_types.append( (_from.type, [s.type for s in _to]) )
        assoc_types.sort()
        self.assertEqual(assoc_types, expected)

#     def test_reverse_association_types(self):
#         expected = [ ('Affaire', ['Person']),
#                      ('Societe', ['Person', 'Affaire'])]
#         assoc_types = rconcerne.reverse_association_types()
#         assoc_types.sort()
#         self.assertEqual(assoc_types, expected)
#         assoc_types = []
#         for _from, _to in rconcerne.reverse_association_types(True):
#             assoc_types.append( (_from.type, [s.type for s in _to]) )
#         assoc_types.sort()
#         self.assertEqual(assoc_types, expected)


class SchemaTC(BaseSchemaTC):

    def test_schema_base(self):
        """test base schema methods
        """
        all_types = ['Affaire', 'BigInt', 'Boolean', 'Bytes', 'Date', 'Datetime',
                     'Decimal',
                     'Float', 'Int', 'Interval', 'Note', 'Password',
                     'Person', 'Societe', 'String', 'TZDatetime', 'TZTime', 'Time']
        self.assertEqual(sorted(schema.entities()), all_types)
        self.assertEqual(schema.has_entity('Affaire'), True)
        self.assertEqual(schema.has_entity('Aaire'), False)

    def test_raise_add_entity_type(self):
        self.assertRaisesMsg(BadSchemaDefinition, "entity type Person is already defined" ,
                             schema.add_entity_type, EntityType('Person'))

    def test_raise_relation_def(self):
        self.assertRaisesMsg(BadSchemaDefinition, "using unknown type 'Afire' in relation evaluee"  ,
                             schema.add_relation_def, RelationDefinition('Afire', 'evaluee', 'Note'))
## XXX what is this ?
##        self.assertRaisesMsg(BadSchemaDefinition, 'the "symmetric" property should appear on every definition of relation evaluee' ,
##                             schema.add_relation_def, RelationDefinition('Affaire', 'evaluee', 'Note', symmetric=True))

    def test_schema_relations(self):
        all_relations = ['TEST', 'concerne', 'travaille', 'evaluee',
                         'date', 'type', 'sujet', 'ref', 'nom', 'prenom',
                         'starton', 'sexe', 'promo', 'promo_enlarged',
                         'promo_encoding', 'promo_format', 'tel', 'fax',
                         'datenaiss']
        all_relations.sort()
        relations = schema.relations()
        relations.sort()
        self.assertEqual(relations, all_relations)

        self.assertEqual(len(eperson.rdef('nom').constraints), 1)
        self.assertEqual(len(eperson.rdef('prenom').constraints), 1)

    def test_schema_check_relations(self):
        """test behaviour with some incorrect relations"""
        for rel in BAD_RELS:
            _from, _type, _to = rel.split()
            self.assertRaises(BadSchemaDefinition,
                              schema.add_relation_def, RelationDefinition(_from, _type, _to))
        # check we can't extend a final relation
        self.assertRaises(BadSchemaDefinition,
                          schema.add_relation_def, RelationDefinition('Person', 'nom', 'affaire'))

    def test_entities_goodValues_check(self):
        """check good values of entity does not raise an exception"""
        for etype, val_list in ATTRIBUTE_GOOD_VALUES:
            eschema = schema.eschema(etype)
            eschema.check(dict(val_list))

    def test_entities_badValues_check(self):
        """check bad values of entity raises ValidationError exception"""
        for etype, val_list in ATTRIBUTE_BAD_VALUES:
            eschema = schema.eschema(etype)
            # check attribute values one each time...
            for item in val_list:
                with self.assertRaises(ValidationError) as cm:
                    eschema.check(dict([item]))
                # check automatic call to translation works properly
                text_type(cm.exception)

    def test_validation_error_translation_1(self):
        eschema = schema.eschema('Person')
        with self.assertRaises(ValidationError) as cm:
            eschema.check({'nom': 1, 'promo': 2})
        cm.exception.translate(text_type)
        self.assertEqual(cm.exception.errors,
                         {'nom-subject': u'incorrect value (1) for type "String"',
                          'promo-subject': u'incorrect value (2) for type "String"'})

    def test_validation_error_translation_2(self):
        eschema = schema.eschema('Person')
        with self.assertRaises(ValidationError) as cm:
            eschema.check({'nom': u'x'*21, 'prenom': u'x'*65})
        cm.exception.translate(text_type)
        self.assertEqual(cm.exception.errors,
                         {'nom-subject': u'value should have maximum size of 20 but found 21',
                          'prenom-subject': u'value should have maximum size of 64 but found 65'})

    def test_validation_error_translation_3(self):
        eschema = schema.eschema('Person')
        with self.assertRaises(ValidationError) as cm:
            eschema.check({'tel': 1000000, 'fax': 1000001})
        cm.exception.translate(text_type)
        self.assertEqual(cm.exception.errors,
                         {'fax-subject': u'value 1000001 must be <= 999999',
                          'tel-subject': u'value 1000000 must be <= 999999'})

    def test_validation_error_translation_4(self):
        verr = ValidationError(1, {None: 'global message about eid %(eid)s'}, {'eid': 1})
        verr.translate(text_type)
        self.assertEqual(verr.errors,
                         {None: 'global message about eid 1'})

    def test_validation_error_unicode_then_translation(self):
        verr = ValidationError(1, {None: 'global message about eid %(eid)s'}, {'eid': 1})
        self.assertEqual(str(verr), '1 (None): global message about eid 1')
        self.assertEqual(text_type(verr), '1 (None): global message about eid 1')
        verr.translate(text_type)
        self.assertEqual(verr.errors,
                         {None: 'global message about eid 1'})

    def test_validation_error_translate_without_msgargs(self):
        """Check that ValidationError.errors get translated even without msgargs"""
        verr = ValidationError(1, {None: 'hello'})
        verr.translate(list)
        self.assertEqual(verr.errors, {None: list('hello')})

    def test_pickle(self):
        """schema should be pickeable"""
        import pickle
        picklefile = mktemp()
        picklestream = open(picklefile, 'wb')
        pickle.dump(schema, picklestream)
        picklestream.close()
        pschema = pickle.load(open(picklefile, 'rb'))
        self.assertFalse(eperson is pschema['Person'])
        self.assertEqual(eperson, pschema['Person'])
        self.assertEqual('Person', pschema['Person'])
        self.assertEqual(eperson.ordered_relations(), pschema['Person'].ordered_relations())
        self.assertEqual(eperson.object_relations(), pschema['Person'].object_relations())


    def test_rename_entity_type(self):
        affaire = schema.eschema('Affaire')
        orig_rprops = affaire.rdef('concerne')
        schema.rename_entity_type('Affaire', 'Workcase')
        self.assertCountEqual(schema._entities.keys(),
                             ['BigInt', 'Boolean', 'Bytes', 'Date', 'Datetime', 'Float',
                              'Decimal',
                              'Int', 'Interval', 'Note', 'Password', 'Person',
                              'Societe', 'String', 'Time', 'TZDatetime', 'TZTime',
                              'Workcase'])
        rconcerne = schema.rschema('concerne')
        self.assertCountEqual(rconcerne.subjects(), ['Workcase', 'Person'])
        self.assertCountEqual(rconcerne.objects(), ['Workcase', 'Societe'])
        self.assertRaises(KeyError, schema.eschema, 'Affaire')
        workcase = schema.eschema('Workcase')
        schema.__test__ = True
        self.assertEqual(workcase.rdef('concerne'), orig_rprops)

    def test_inheritance_rdefs(self):
        class Plan(EntityType):
            pass
        rdef = RelationDefinition('Plan', 'custom_workflow', 'Workflow')
        _add_relation(Plan.__relations__, rdef)
        class TE(Plan):
            pass
        self.assertListEqual(['custom_workflow'],
                             [rel.name for rel in TE.__relations__])

    def test_add_rdef_after_registration(self):
        class Label(EntityType):
            pass
        Label.expand_type_definitions({})
        Label.add_relation(RichString(), name='label')


class SymetricTC(TestCase):
    def setUp(self):
        global schema
        schema = Schema('Test Schema')
        schema.add_entity_type(EntityType('Bug'))
        schema.add_entity_type(EntityType('Story'))
        schema.add_entity_type(EntityType('Project'))
        schema.add_relation_type(RelationType('see_also', symmetric=True))

    def test_association_types(self):
        schema.add_relation_def(RelationDefinition('Bug', 'see_also', 'Bug'))
        schema.add_relation_def(RelationDefinition('Bug', 'see_also', 'Story'))
        schema.add_relation_def(RelationDefinition('Bug', 'see_also', 'Project'))
        schema.add_relation_def(RelationDefinition('Story', 'see_also', 'Story'))
        schema.add_relation_def(RelationDefinition('Story', 'see_also', 'Project'))
        schema.add_relation_def(RelationDefinition('Project', 'see_also', 'Project'))

        rsee_also = schema.rschema('see_also')
        subj_types = rsee_also.associations()
        subj_types.sort()
        self.assertEqual(subj_types,
                          [('Bug', ['Bug', 'Story', 'Project']),
                           ('Project', ['Bug', 'Story', 'Project']),
                           ('Story', ['Bug', 'Story', 'Project'])])

    def test_wildcard_association_types(self):
        class see_also(RelationDefinition):
            subject = '*'
            object ='*'
        see_also.expand_relation_definitions({'see_also': see_also}, schema)
        rsee_also = schema.rschema('see_also')
        subj_types = rsee_also.associations()
        subj_types.sort()
        for key, vals in subj_types:
            vals.sort()
        self.assertEqual(subj_types,
                          [('Bug', ['Bug', 'Project', 'Story']),
                           ('Project', ['Bug', 'Project', 'Story']),
                           ('Story', ['Bug', 'Project', 'Story'])])


class CustomTypeTC(TestCase):

    def tearDown(self):
        try:
            unregister_base_type('Test')
        except AssertionError:
            pass

    def test_register_base_type(self):
        register_base_type('Test', ('test1', 'test2'))
        self.assertIn('Test', BASE_TYPES)
        self.assertIn('Test', RelationDefinitionSchema.BASE_TYPE_PROPERTIES)
        self.assertEqual(RelationDefinitionSchema.BASE_TYPE_PROPERTIES['Test'],
                         {'test1': None, 'test2': None})
        self.assertIn('Test', BASE_CHECKERS)
        schema = Schema('test')
        register_base_types(schema)
        self.assertIn('Test', schema)
        schema.del_entity_type('Test')
        self.assertNotIn('Test', BASE_TYPES)
        self.assertNotIn('Test', RelationDefinitionSchema.BASE_TYPE_PROPERTIES)
        self.assertNotIn('Test', BASE_CHECKERS)

    def test_make_base_type_class(self):
        register_base_type('Test', ('test1', 'test2'))
        Test = make_type('Test')
        self.assertIsInstance(Test, type)
        self.assertEqual(Test.etype, 'Test')
        t = Test(test1=1)
        self.assertEqual(t.test1, 1)
        self.assertFalse(hasattr(t, 'test2'))

if __name__ == '__main__':
    unittest_main()
