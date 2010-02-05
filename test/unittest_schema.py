# -*- coding: iso-8859-1 -*-
"""unit tests for module yams.schema classes"""

from logilab.common.testlib import TestCase, unittest_main

from copy import copy, deepcopy
from tempfile import mktemp

from yams.buildobjs import register_base_types, EntityType, RelationType, RelationDefinition
from yams.schema import *
from yams.constraints import *
from yams.reader import SchemaLoader


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

        estring = schema.eschema('String')
        eint = schema.eschema('Int')
        rconcerne = schema.rschema('concerne')
        rnom = schema.rschema('nom')

    def assertRaisesMsg(self, ex_class, msg, func, *args, **kwargs):
        self.assertRaises(ex_class, func, *args, **kwargs)
        try:
            func(*args, **kwargs)
        except Exception, ex:
            self.assertEquals(str(ex), msg)

# test data ###################################################################

BAD_RELS = ( ('Truc badrelation1 Affaire'),
             ('Affaire badrelation2 Machin'),
             )

ATTRIBUTE_BAD_VALUES = (
    ('Person', [('nom', 1), ('nom', u'tropcour'),
                ('nom', u'>10 mais  supérieur à < 20 , c\'est long'),
                ('sexe', u'F'), ('sexe', u'MorF'), ('sexe', 'F'),
                ('promo', 'bon'), ('promo', 'uyou'),
                ('promo', u' pas bon du tout'),
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
        self.assert_(repr(eperson))

    def test_cmp(self):
        self.failUnless(eperson == 'Person')
        self.failUnless('Person' == eperson)
        self.failUnless(eperson != 'Note')
        self.failUnless('Note' != eperson)
        self.failIf(enote == eperson)
        self.failIf(eperson == enote)
        self.failUnless(enote != eperson)
        self.failUnless(eperson != enote)
        l = [eperson, enote, eaffaire, esociete]
        l.sort()
        self.assertListEquals(l, [eaffaire, enote, eperson, esociete])
        self.assertListEquals(l, ['Affaire', 'Note', 'Person', 'Societe'])

    def test_hash(self):
        d = {}
        d[eperson] = 'p'
        d[enote] = 'n'
        self.failUnlessEqual(d[copy(eperson)], 'p')
        self.failUnlessEqual(d[copy(enote)], 'n')
        self.failUnlessEqual(d['Person'], 'p')
        self.failUnlessEqual(d['Note'], 'n')
        d = {}
        d['Person'] = eperson
        d['Note'] = enote
        self.failUnlessEqual(copy(eperson), 'Person')
        self.failUnlessEqual(d[copy(eperson)], 'Person')
        self.failUnlessEqual(d[copy(enote)], 'Note')

    def test_deepcopy_with_regexp_constraints(self):
        eaffaire.rdef('ref').constraints = [RegexpConstraint(r'[A-Z]+\d+')]
        rgx_cstr, = eaffaire.rdef('ref').constraints
        eaffaire2 = deepcopy(schema).eschema('Affaire')
        rgx_cstr2, = eaffaire2.rdef('ref').constraints
        self.assertEquals(rgx_cstr2.regexp, rgx_cstr.regexp)
        self.assertEquals(rgx_cstr2.flags, rgx_cstr.flags)
        self.assertEquals(rgx_cstr2._rgx, rgx_cstr._rgx)

    def test_deepcopy(self):
        global schema
        schema = deepcopy(schema)
        self.failIf(eperson is schema['Person'])
        self.failUnlessEqual(eperson, schema['Person'])
        self.failUnlessEqual('Person', schema['Person'])
        self.failUnlessEqual(eperson.subject_relations(), schema['Person'].subject_relations())
        self.failUnlessEqual(eperson.object_relations(), schema['Person'].object_relations())
        self.assertEquals(schema.eschema('Person').final, False)
        self.assertEquals(schema.eschema('String').final, True)
        self.assertEquals(schema.rschema('ref').final, True)
        self.assertEquals(schema.rschema('concerne').final, False)

    def test_deepcopy_specialization(self):
        schema2 = deepcopy(SchemaLoader().load([self.datadir], 'Test'))
        edivision = schema2.eschema('Division')
        self.assertEquals(edivision.specializes(), 'Company')
        self.assertEquals(edivision.specialized_by(), ['Subdivision'])
        schema2.del_entity_type('Subdivision')
        self.assertEquals(edivision.specialized_by(), [])

    def test_is_final(self):
        self.assertEquals(eperson.final, False)
        self.assertEquals(enote.final, False)
        self.assertEquals(estring.final, True)
        self.assertEquals(eint.final, True)
        self.assertEquals(eperson.subjrels['nom'].final, True)
        #self.assertEquals(eperson.is_final('concerne'), False)
        self.assertEquals(eperson.subjrels['concerne'].final, False)

    def test_is_metadata(self):
        self.assertEquals(eperson.is_metadata('promo'), None)
        self.assertEquals(eperson.is_metadata('promo_enlarged'), None)
        self.assertEquals(eperson.is_metadata('promo_encoding'), ('promo', 'encoding'))
        self.assertEquals([(k.type, v)  for k, v in eperson.meta_attributes().items()],
                          [('promo_encoding', ('encoding', 'promo'))])

    def test_defaults(self):
        self.assertEquals(list(eperson.defaults()), [])
        self.assertRaises(StopIteration, estring.defaults().next)

    def test_vocabulary(self):
        #self.assertEquals(eperson.vocabulary('promo')
        self.assertEquals(eperson.rdef('promo').constraint_by_interface(IVocabularyConstraint).vocabulary(),
                          ('bon', 'pasbon'))
        # self.assertRaises(AssertionError,
        #                   eperson.vocabulary, 'nom')

    def test_indexable_attributes(self):
        eperson.rdef('nom').fulltextindexed = True
        eperson.rdef('prenom').fulltextindexed = True
        self.assertEquals(list(eperson.indexable_attributes()), ['nom', 'prenom'])


    def test_goodValues_relation_default(self):
        """check good values of entity does not raise an exception"""
        eperson.rdef('nom').default = 'No name'
        self.assertEquals(eperson.default('nom'), 'No name')

    def test_subject_relations(self):
        """check subject relations a returned in the same order as in the
        schema definition"""
        rels = eperson.ordered_relations()
        expected = ['nom', 'prenom', 'sexe', 'tel', 'fax', 'datenaiss',
                    'TEST', 'promo', 'promo_enlarged', 'promo_encoding', 'travaille',
                    'evaluee', 'concerne']
        self.assertEquals([r.type for r in rels], expected)

    def test_object_relations(self):
        """check object relations a returned in the same order as in the
        schema definition"""
        rels = eaffaire.object_relations()
        expected = ['concerne']
        self.assertEquals(rels, expected)
        rels = [schem.type for schem in eaffaire.object_relations()]
        self.assertEquals(rels, expected)
        self.assertEquals(eaffaire.objrels['concerne'].type,
                         'concerne')

    def test_destination_type(self):
        """check subject relations a returned in the same order as in the
        schema definition"""
        self.assertEquals(eperson.destination('nom'), 'String')
        #self.assertRaises(AssertionError, eperson.destination, 'concerne')
        self.assertEquals(eperson.destination('travaille'), 'Societe')


class RelationSchemaTC(BaseSchemaTC):

    def test_cmp(self):
        self.failUnless(rconcerne == 'concerne')
        self.failUnless('concerne' == rconcerne)
        self.failUnless(rconcerne != 'nom')
        self.failUnless('nom' != rconcerne)
        self.failIf(rnom == rconcerne)
        self.failIf(rconcerne == rnom)
        self.failUnless(rnom != rconcerne)
        self.failUnless(rconcerne != rnom)

    def test_hash(self):
        d = {}
        d[rconcerne] = 'p'
        d[rnom] = 'n'
        self.failUnlessEqual(d[copy(rconcerne)], 'p')
        self.failUnlessEqual(d[copy(rnom)], 'n')
        self.failUnlessEqual(d['concerne'], 'p')
        self.failUnlessEqual(d['nom'], 'n')


    def test_base(self):
        self.assert_(repr(rnom))

    def test_star_types(self):
        types = sorted(rconcerne.subjects())
        self.assertEquals(types, ['Affaire', 'Person'])
        types = sorted(rconcerne.objects())
        self.assertEquals(types, ['Affaire', 'Societe'])

    def test_raise_update(self):
        self.assertRaisesMsg(BadSchemaDefinition,
                             'type String can\'t be used as subject in a relation',
                             rconcerne.update, estring, enote, {})
##         self.assertRaisesMsg(BadSchemaDefinition,
##                              "can't have a final relation pointing to multiple entity types (nom: ['String', 'Int'])" ,
##                              rnom.update, enote, eint)
        self.assertRaisesMsg(BadSchemaDefinition, 'ambiguous relation nom: String is final but not Affaire',
                             rnom.update, enote, eaffaire, {})
        self.assertRaises(BadSchemaDefinition,
                          rconcerne.update, enote, estring, {})

    def test_association_types(self):
        expected = [ ('Affaire', ['Societe']),
                     ('Person', ['Affaire', 'Societe']) ]
        assoc_types = rconcerne.associations()
        assoc_types.sort()
        self.assertEquals(assoc_types, expected)
        assoc_types = []
        for _from, _to in rconcerne.associations():
            assoc_types.append( (_from, _to))
            #assoc_types.append( (_from.type, [s.type for s in _to]) )
        assoc_types.sort()
        self.assertEquals(assoc_types, expected)

#     def test_reverse_association_types(self):
#         expected = [ ('Affaire', ['Person']),
#                      ('Societe', ['Person', 'Affaire'])]
#         assoc_types = rconcerne.reverse_association_types()
#         assoc_types.sort()
#         self.assertEquals(assoc_types, expected)
#         assoc_types = []
#         for _from, _to in rconcerne.reverse_association_types(True):
#             assoc_types.append( (_from.type, [s.type for s in _to]) )
#         assoc_types.sort()
#         self.assertEquals(assoc_types, expected)


class SchemaTC(BaseSchemaTC):

    def test_schema_base(self):
        """test base schema methods
        """
        all_types = ['Affaire', 'Boolean', 'Bytes', 'Date', 'Datetime',
                     'Decimal',
                     'Float', 'Int', 'Interval', 'Note', 'Password',
                     'Person', 'Societe', 'String', 'Time']
        types = schema.entities()
        types.sort()
        self.assertEquals(types, all_types)
        self.assertEquals(schema.has_entity('Affaire'), True)
        self.assertEquals(schema.has_entity('Aaire'), False)

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
                         'promo_encoding', 'tel', 'fax', 'datenaiss']
        all_relations.sort()
        relations = schema.relations()
        relations.sort()
        self.assertEquals(relations, all_relations)

        self.assertEquals(len(eperson.rdef('nom').constraints), 1)
        self.assertEquals(len(eperson.rdef('prenom').constraints), 1)

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
                self.assertRaises(ValidationError, eschema.check, dict([item]))

    def test_pickle(self):
        """schema should be pickeable"""
        import pickle
        picklefile = mktemp()
        picklestream = open(picklefile, 'w')
        schema.__hashmode__ = 'pickle'
        pickle.dump(schema, picklestream)
        picklestream.close()
        pschema = pickle.load(open(picklefile))
        schema.__hashmode__ = None
        self.assertEquals(pschema.__hashmode__, None)
        self.failIf(eperson is pschema['Person'])
        self.failUnlessEqual(eperson, pschema['Person'])
        self.failUnlessEqual('Person', pschema['Person'])
        self.failUnlessEqual(eperson.ordered_relations(), pschema['Person'].ordered_relations())
        self.failUnlessEqual(eperson.object_relations(), pschema['Person'].object_relations())


    def test_rename_entity_type(self):
        affaire = schema.eschema('Affaire')
        orig_rprops = affaire.rdef('concerne')
        schema.rename_entity_type('Affaire', 'Workcase')
        self.assertUnorderedIterableEquals(schema._entities.keys(),
                             ['Boolean', 'Bytes', 'Date', 'Datetime', 'Float',
                              'Decimal',
                              'Int', 'Interval', 'Note', 'Password', 'Person',
                              'Societe', 'String', 'Time', 'Workcase'])
        rconcerne = schema.rschema('concerne')
        self.assertUnorderedIterableEquals(rconcerne.subjects(), ['Workcase', 'Person'])
        self.assertUnorderedIterableEquals(rconcerne.objects(), ['Workcase', 'Societe'])
        self.assertRaises(KeyError, schema.eschema, 'Affaire')
        workcase = schema.eschema('Workcase')
        schema.__test__ = True
        self.assertEquals(workcase.rdef('concerne'), orig_rprops)


class SymetricTC(TestCase):
    def setUp(self):
        global schema
        schema = Schema('Test Schema')
        ebug = schema.add_entity_type(EntityType('Bug'))
        estory = schema.add_entity_type(EntityType('Story'))
        eproject = schema.add_entity_type(EntityType('Project'))
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
        self.assertEquals(subj_types,
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
        self.assertEquals(subj_types,
                          [('Bug', ['Bug', 'Project', 'Story']),
                           ('Project', ['Bug', 'Project', 'Story']),
                           ('Story', ['Bug', 'Project', 'Story'])])

if __name__ == '__main__':
    unittest_main()
