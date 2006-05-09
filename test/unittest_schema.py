# -*- coding: iso-8859-1 -*-
"""unit tests for module yams.schema classes

Copyright Logilab 2002-2004, all rights reserved.
"""

__revision__ = "$Id: unittest_schema.py,v 1.15 2006-04-10 14:39:03 syt Exp $"

from logilab.common.testlib import TestCase, unittest_main

from yams.builder import EntityType, RelationType, RelationDefinition

from yams.schema import *


# build a dummy schema ########################################################


class BaseSchemaTC(TestCase):
    def setUp(self):
        global schema, enote, eaffaire, eperson, esociete, estring, eint
        global rconcerne, rnom
        schema = Schema('Test Schema')
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
            # real relations
            ('Person  travaille Societe'),
            ('Person  evaluee   Note'),
            ('Societe evaluee   Note'),
            ('Person  concerne  Affaire'),
            ('Person  concerne  Societe'),
            ('Affaire Concerne  Societe'),
            ('Affaire concerne  Societe'),
            )
        for rel in RELS:
            _from, _type, _to = rel.split()
            schema.add_relation_def(RelationDefinition(_from, _type, _to))
        schema.rschema('nom')._card[('Person', 'String')] = '11' # not null

        enote.set_rproperty('type', 'constraints',
                             [MultipleStaticVocabularyConstraint(('bon', 'pasbon',
                                                                  'bof', 'peux mieux faire'))])
        eaffaire.set_rproperty('sujet', 'constraints', [SizeConstraint(128)])
        eaffaire.set_rproperty('ref', 'constraints', [SizeConstraint(12)])
        eperson.set_rproperty('nom', 'constraints', [SizeConstraint(20, 10)])
        eperson.set_rproperty('prenom', 'constraints', [SizeConstraint(64)])
        eperson.set_rproperty('tel', 'constraints', [BoundConstraint('<=', 999999)])
        eperson.set_rproperty('promo', 'constraints', [StaticVocabularyConstraint( ('bon', 'pasbon'))])

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
    ('Person', [('nom', 1), ('sexe', u'MorF'), ('sexe', 'F'),
                ('promo', 'uyou'),
                ('datenaiss', 'XXX'), 
                ('tel', 'notastring'), 
                ('test', 'notaboolean'), ('test', 0), ('test', 1)]),
    ('Person', [('nom', u'tropcour'), ('sexe', u'F'),
                ('promo', u'bon'),
                ('datenaiss', '1977-06-07'),
                ('tel', 1999999), ('fax', None), 
                ('test', 'true'), ('test', 'false')]),
    ('Person', [('nom', u' >10 mais < 20 '),
                ('datenaiss', '979-06-12')]),
    ('Person', [('nom', u'>10 mais  supérieur à < 20 , c\'est long'),
                ('datenaiss', '1970-09-12')]),
    ('Note', [('date', '2229-01-31 minuit')]),
##     ('Note', [('type', ['bof', 'mais y arrivera sans doute !'])]),
    ('Affaire', [('starton', 'midi')]),
    )
ATTRIBUTE_GOOD_VALUES = (
    ('Person', [('nom', u'>10 mais < 20 '), ('sexe', 0.5),
                ('promo', u'bon'),
                ('datenaiss', '1977-06-07'),
                ('tel', 83433), ('fax', None), 
                ('test', 'true'), ('test', 'false')]),
    ('Note', [('date', '2229-01-31 00:00')]),
##     ('Note', [('type', ['bof', 'peux mieux faire'])]),
    ('Affaire', [('starton', '00:00')]),
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
        self.assertEquals(repr(enote), "<EntitySchema Note ['date', 'type'] - ['evaluee']>")
        
#    def test_is_uid(self):
#        eperson.set_uid('nom')
#        self.assertEquals(eperson.is_uid('nom'), True)
        
    def test_is_final(self):        
        self.assertEquals(eperson.is_final(), False)
        self.assertEquals(enote.is_final(), False)
        self.assertEquals(estring.is_final(), True)
        self.assertEquals(eint.is_final(), True)
        self.assertEquals(eperson.is_final('nom'), True)
        self.assertEquals(eperson.is_final('concerne'), False)
        
    def test_defaults(self):        
        self.assertEquals(list(eperson.defaults()), [])
        self.assertRaises(AssertionError,
                          estring.defaults().next)

    def test_vocabulary(self):
        self.assertEquals(eperson.vocabulary('promo'), ('bon', 'pasbon'))
        self.assertRaises(AssertionError,
                          eperson.vocabulary, 'what?')
        self.assertRaises(AssertionError,
                          eperson.vocabulary, 'nom')
        
    def test_indexable_attributes(self):
        eperson.set_rproperty('nom', 'indexable', True)
        eperson.set_rproperty('prenom', 'indexable', True)
        self.assertEquals(eperson.indexable_attributes(), ['nom', 'prenom'])

    
    def test_goodValues_relation_default(self):
        """check good values of entity does not raise an exception"""
        eperson.set_rproperty('nom', 'default', 'No name')
        self.assertEquals(eperson.default('nom'), 'No name')
        
    def test_subject_relations(self):
        """check subject relations a returned in the same order as in the
        schema definition"""
        rels = eperson.subject_relations()
        expected = ['nom', 'prenom', 'sexe', 'tel', 'fax', 'datenaiss',
                    'TEST', 'promo', 'travaille', 'evaluee', 'concerne']
        self.assertEquals(rels, expected)
        rels = [schem.type for schem in eperson.subject_relations()]
        self.assertEquals(rels, ['nom', 'prenom', 'sexe', 'tel', 'fax', 'datenaiss',
                                'TEST', 'promo', 'travaille', 'evaluee', 'concerne'])

    def test_object_relations(self):
        """check object relations a returned in the same order as in the
        schema definition"""
        rels = eaffaire.object_relations(False)
        expected = ['concerne']
        self.assertEquals(rels, expected)
        rels = [schem.type for schem in eaffaire.object_relations()]
        self.assertEquals(rels, expected)
        self.assertEquals(eaffaire.object_relation('concerne').type,
                         'concerne')

#     def test_destination_types(self):
#         """check subject relations a returned in the same order as in the
#         schema definition"""
#         expected = ['Societe']
#         self.assertEquals(eperson.destination_types('travaille'), expected)
#         expected = ['String']
#         self.assertEquals(eperson.destination_types('nom'), expected)
        
    def test_destination_type(self):
        """check subject relations a returned in the same order as in the
        schema definition"""
        expected = 'String'
        self.assertEquals(eperson.destination_type('nom'), expected)
        self.assertRaises(AssertionError,
                          eperson.destination_type, 'travaille')
        
class RelationSchemaTC(BaseSchemaTC):

    def test_base(self):
        self.assertEquals(repr(rnom), "<RelationSchema nom [('Person', ['String'])]>")

    def test_star_types(self):
        types = rconcerne.subject_types()
        types.sort()
        self.assertEquals(types, ['Affaire', 'Person'])
        types = rconcerne.object_types()
        types.sort()
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
        assoc_types = rconcerne.association_types()
        assoc_types.sort()
        self.assertEquals(assoc_types, expected)
        assoc_types = []
        for _from, _to in rconcerne.association_types(True):
            assoc_types.append( (_from.type, [s.type for s in _to]) ) 
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
        all_types = ['Affaire', 'Boolean', 'Date', 'Datetime',
                     'Float', 'Int', 'Note',
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
        self.assertRaisesMsg(BadSchemaDefinition, 'the "symetric" property should appear on every definition of relation evaluee' ,
                             schema.add_relation_def, RelationDefinition('Affaire', 'evaluee', 'Note', {'symetric':1}))
        
    def test_schema_relations(self):
        all_relations = ['Concerne', 'TEST', 'concerne', 'travaille', 'evaluee',
                         'date', 'type', 'sujet', 'ref', 'nom', 'prenom',
                         'starton',
                         'sexe', 'promo', 'tel', 'fax', 'datenaiss']
        all_relations.sort()
        relations = schema.relations()
        relations.sort()
        self.assertEquals(relations, all_relations)
        
        self.assertEquals(len(eperson.rproperty('nom', 'constraints')), 1) 
        self.assertEquals(len(eperson.rproperty('prenom', 'constraints')), 1)
       
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
        """check bad values of entity raises InvalidEntity exception"""
        for etype, val_list in ATTRIBUTE_BAD_VALUES:
            eschema = schema.eschema(etype)
            self.assertRaises(InvalidEntity, eschema.check, dict(val_list))
        

##     def test_relations_goodValues_check(self):
##         """ check good values of relation return true """
##         for r, list in RELATIONS_GOOD_VALUES.items():
##             rschema = schema.rschema(r)
##             for efrom, eto in list:
##                 es_from = schema.eschema(efrom)
##                 es_to = schema.eschema(eto)
##                 e1 = EntityInstance(es_from, None)
##                 e2 = EntityInstance(es_to, None)
##                 r = RelationInstance(rschema, e1, e2)
##                 r.check()
                
##     def test_relations_badValues_check(self):
##         """ check bad values of relation raise InvalidRelation exception """
##         for r, list in RELATIONS_BAD_VALUES.items():
##             rschema = schema.rschema(r)
##             for efrom, eto in list:
##                 es_from = schema.eschema(efrom)
##                 es_to = schema.eschema(eto)
##                 e1 = EntityInstance(es_from, None)
##                 e2 = EntityInstance(es_to, None)
##                 r = RelationInstance(rschema, e1, e2)
##                 self.assertRaises(InvalidRelation, r.check)

class SymetricTC(TestCase):
    def setUp(self):
        global schema
        schema = Schema('Test Schema')
        ebug = schema.add_entity_type(EntityType('Bug'))
        estory = schema.add_entity_type(EntityType('Story'))
        eproject = schema.add_entity_type(EntityType('Project'))
        schema.add_relation_type(RelationType('see_also', symetric=True))

    def test_association_types(self):
        schema.add_relation_def(RelationDefinition('Bug', 'see_also', 'Bug'))
        schema.add_relation_def(RelationDefinition('Bug', 'see_also', 'Story'))
        schema.add_relation_def(RelationDefinition('Bug', 'see_also', 'Project'))
        schema.add_relation_def(RelationDefinition('Story', 'see_also', 'Story'))
        schema.add_relation_def(RelationDefinition('Story', 'see_also', 'Project'))
        schema.add_relation_def(RelationDefinition('Project', 'see_also', 'Project'))
        
        rsee_also = schema.rschema('see_also')
        subj_types = rsee_also.association_types()
        subj_types.sort()
        self.assertEquals(subj_types,
                          [('Bug', ['Bug', 'Story', 'Project']),
                           ('Project', ['Bug', 'Story', 'Project']),
                           ('Story', ['Bug', 'Story', 'Project'])])

    def test_wildcard_association_types(self):
        rdef = RelationDefinition('*', 'see_also', '*')
        rdef.register_relations(schema)

        rsee_also = schema.rschema('see_also')
        subj_types = rsee_also.association_types()
        subj_types.sort()
        for key, vals in subj_types:
            vals.sort()
        self.assertEquals(subj_types,
                          [('Bug', ['Bug', 'Project', 'Story']),
                           ('Project', ['Bug', 'Project', 'Story']),
                           ('Story', ['Bug', 'Project', 'Story'])])
        
if __name__ == '__main__':
    unittest_main()
