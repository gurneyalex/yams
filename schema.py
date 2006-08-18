"""classes to define generic Entities/Relations schemas

:version: $Revision: 1.35 $  
:organization: Logilab
:copyright: 2003-2006 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

from __future__ import generators

__docformat__ = "restructuredtext en"

from mx.DateTime import today, now

from logilab.common import cached
from logilab.common.compat import sorted
from logilab.common.interface import implements

from yams import InvalidEntity, BadSchemaDefinition
from yams.interfaces import ISchema, IRelationSchema, IEntitySchema, \
     IVocabularyConstraint
from yams.constraints import BASE_CHECKERS
from yams.builder import BASE_TYPES, EntityType

KEYWORD_MAP = {'NOW' : now,
               'TODAY': today,
               }

class ERSchema(object):
    """common base class to entity and relation schema
    """

    def __init__(self, schema, erdef):
        self.schema = schema
        self.type = erdef.name
        self.meta = erdef.meta
        if erdef.__doc__:
            descr = ' '.join(erdef.__doc__.split())
        else:
            descr = ''
        self.description = descr
        # mapping from action to groups
        self._groups = getattr(erdef, 'permissions', None) or {}

    ACTIONS = ()
    
    def set_groups(self, action, groups):
        """set the groups allowed to perform <action> on entities of this type
        
        :type action: str
        :param action: the name of a permission

        :type groups: list
        :param groups: the groups with the given permission
        """
        assert type(groups) is tuple
        assert action in self.ACTIONS, action
        self._groups[action] = groups
    
    def get_groups(self, action):
        """return the groups authorized to perform <action> on entities of
        this type

        :type action: str
        :param action: the name of a permission

        :rtype: list
        :return: the groups with the given permission
        """
        assert action in self.ACTIONS, action
        #assert action in self._groups, '%s %s' % (self, action)
        try:
            return self._groups[action]
        except KeyError:
            return ()
        

    def has_group(self, action, group):
        """return true if the group is authorized for the given action
        
        :type action: str
        :param action: the name of a permission
        
        :rtype: bool
        :return: flag indicating whether the group has the permission
        """
        assert action in self.ACTIONS, action
        return group in self._groups[action]

    def has_access(self, user, action):
        """return true if the user has the given permission on entity of this
        type

        :type user: `ginco.common.utils.User`
        :param user: a Erudi user instance
        
        :type action: str
        :param action: the name of a permission
        
        :rtype: bool
        :return: flag indicating whether the user has the permission
        """
        return user.in_groups(self.get_groups(action))


# Schema objects definition ###################################################

class EntitySchema(ERSchema):
    """a entity has a type, a set of subject and or object relations
    the entity schema defines the possible relations for a given type and some
    constraints on those relations
    """
    __implements__ = IEntitySchema    
    
    ACTIONS = ('read', 'add', 'update', 'delete')

    def __init__(self, schema, edef):
        super(EntitySchema, self).__init__(schema, edef)
        # quick access to bounded relation schemas
        self._subj_relations = {}
        self._obj_relations = {}
        
    def __repr__(self):
        return '<%s %s %s - %s>' % (self.__class__.__name__, self.type,
                                    self.subject_relations(),
                                    self.object_relations())
        
    # schema building methods #################################################
                
    def add_subject_relation(self, rschema, rdef):
        """register the relation schema as possible subject relation"""
        self._subj_relations[rschema.type] = rschema
        
    def add_object_relation(self, rschema, rdef):
        """register the relation schema as possible object relation"""
        self._obj_relations[rschema.type] = rschema
        
    def del_subject_relation(self, rtype):
        del self._subj_relations[rtype]
        
    def del_object_relation(self, rtype):
        del self._obj_relations[rtype]

    def set_default_groups(self):
        """set default action -> groups mapping"""
        if self._groups:
            pass # already initialized
        elif self.is_final():
            # give access to everybody for final entities
            self._groups = {'read': ('managers', 'users', 'guests'),
                            'update': ('managers', 'users'),
                            'delete': ('managers', 'users'),
                            'add': ('managers', 'users')}
        elif self.meta:
            self._groups = {'read': ('managers', 'users', 'guests',),
                            'update': ('managers', 'owners',),
                            'delete': ('managers',),
                            'add': ('managers',)}
        else:
            self._groups = {'read': ('managers', 'users', 'guests',),
                            'update': ('managers', 'owners',),
                            'delete': ('managers', 'owners'),
                            'add': ('managers', 'users',)}

    # IEntitySchema interface #################################################

    def is_final(self):
        """return true if the entity is a final entity
        (and so cannot be used as subject of a relation)
        """
        return self.type in BASE_TYPES
    
    def ordered_relations(self):
        """ return subject relation in an ordered way"""
        result = []
        for rschema in self._subj_relations.values():
            otype = rschema.object_types(self.type)[0]
            result.append((rschema.rproperty(self.type, otype, 'order'), rschema))
        return [r[1] for r in sorted(result)]
    
    def subject_relations(self, schema=True):
        """return a list of relations that may have this type of entity as
        subject
        
        If schema, return a list of schemas instead of relation's types.
        """
        if schema:
            return self.ordered_relations()
        return [rschema.type for rschema in self.ordered_relations()]
    
    def object_relations(self, schema=True):
        """return a list of relations that may have this type of entity as
        object
        
        If schema, return a list of schemas instead of relation's types.
        """
        if schema:
            return self._obj_relations.values()
        else:
            return self._obj_relations.keys()

    def subject_relation(self, rtype):
        """return the relation schema for the rtype subject relation
        
        Raise `KeyError` if rtype is not a subject relation of this entity type
        """        
        return self._subj_relations[rtype]
    
    def object_relation(self, rtype):
        """return the relation schema for the rtype object relation
        
        Raise `KeyError` if rtype is not an object relation of this entity type
        """
        return self._obj_relations[rtype]

    def attribute_definitions(self):
        """return an iterator on attribute definitions
        
        attribute relations are a subset of subject relations where the
        object's type is a final entity
        
        an attribute definition is a 2-uple :
        * schema of the (final) relation
        * schema of the destination entity type
        """
        for rschema in self.ordered_relations():
            if not rschema.is_final():
                continue
            eschema = rschema.objects(etype=self.type)[0]
            yield rschema, eschema

    def destination_type(self, rtype):
        """return the type or schema of entities related by the given relation

        `rtype` must be a subject final relation
        """
        rschema = self.subject_relation(rtype)
        assert rschema.is_final(), (self.type, rtype)
        objtypes = rschema.object_types(self.type)
        assert len(objtypes) == 1
        return objtypes[0]
    
    def rproperty(self, rtype, prop):
        """convenience method to access a property of a subject relation"""
        rschema = self.subject_relation(rtype)
        return rschema.rproperty(self.type, self.destination_type(rtype), prop)

    def set_rproperty(self, rtype, prop, value):
        """convenience method to set the value of a property of a subject relation"""
        rschema = self.subject_relation(rtype)
        return rschema.set_rproperty(self.type, self.destination_type(rtype), prop, value)

    def rproperties(self, rtype):
        """convenience method to access properties of a subject relation"""
        rschema = self.schema.rschema(rtype)
        desttype = rschema.object_types(self.type)[0]
        return rschema.rproperties(self.type, desttype)

    def relation_definitions(self):
        """return an iterator on "real" relation definitions
        
        "real"  relations are a subset of subject relations where the
        object's type is not a final entity
        
        a relation definition is a 2-uple :
        * schema of the (non final) relation
        * schema of the destination entity type
        """
        for rschema in self.ordered_relations():
            if rschema.is_final():
                continue
            yield rschema, rschema.objects(etype=self.type), 'subject'
        for rschema in self.object_relations():
            yield rschema, rschema.subjects(etype=self.type), 'object'
            
    
    def main_attribute(self):
        """convenience method that returns the *main* (i.e. the first non meta)
        attribute defined in the entity schema
        """
        for rschema, _ in self.attribute_definitions():
            if rschema.meta:
                continue
            return rschema.type
    
    def indexable_attributes(self):
        """return the name of relations to index"""
        assert not self.is_final()
        for rschema in self.subject_relations():
            if not rschema.is_final():
                continue
            rtype = rschema.type
            if self.rproperty(rtype, 'fulltextindexed'):
                yield rtype                
    #indexable_attributes = cached(indexable_attributes)
    
    def defaults(self):
        """return the list of (attribute name, default value)
        """
        assert not self.is_final()
        for rschema in self.ordered_relations():
            if not rschema.is_final():
                continue
            value = self.default(rschema.type)
            if value is not None:
                yield rschema.type, value   
        
    def default(self, rtype):
        """return the default value of a subject relation"""
        default =  self.rproperty(rtype, 'default')
        if callable(default):
            default = default()
        if default is not None:
            attrtype = self.destination_type(rtype)
            if attrtype == 'Boolean':
                # XXX Int, Float...
                if not isinstance(default, bool):
                    default = default == 'True'
            elif attrtype in ('Date', 'Datetime'):
                default = KEYWORD_MAP[default.upper()]()
            else:
                default = unicode(default)
        return default
    
    def constraints(self, rtype):
        """return constraint of type <cstrtype> associated to the <rtype>
        subjet relation

        returns None if no constraint of type <cstrtype> is found
        """
        return self.rproperty(rtype, 'constraints')

    def vocabulary(self, rtype):
        """backward compat return the vocabulary of a subject relation
        """
        for constraint in self.constraints(rtype):
            if implements(constraint, IVocabularyConstraint):
                break
        else:
            raise AssertionError('field %s of entity %s has no vocabulary' %
                                 (rtype, self.type))
        return constraint.vocabulary()
    
    def check(self, entity, creation=False):
        """check the entity and raises an InvalidEntity exception if it
        contains some invalid fields (ie some constraints failed)
        """
        assert not self.is_final()
        errors = {}
        etype = self.type
        for rschema in self.ordered_relations():
            if not rschema.is_final():
                continue
            rtype = rschema.type
            aschema = self.schema[self.destination_type(rtype)]
            # don't care about rhs cardinality, always '*' (if it make senses)
            card = rschema.rproperty(etype, aschema.type, 'cardinality')[0]
            assert card in '?1'
            required = card == '1'
            # check value according to their type
            try:
                value = entity[rtype]
            except KeyError:
                if creation and required:
                    # missing required attribute with no default on creation
                    # is not autorized
                    errors[rtype] = 'missing attribute'
                # on edition, missing attribute is considered as no changes
                continue
            # skip other constraint if value is None and None is allowed
            if value is None and not required:
                break
            if not aschema.check_value(value):
                errors[rtype] = 'incorrect value %r for type %s' % (value,
                                                                    aschema.type)
                continue
            # check arbitrary constraints
            for constraint in rschema.rproperty(etype, aschema.type,
                                                'constraints'):
                if not constraint.check(entity, rtype, value):
                    errors[rtype] = '%s constraint failed' % constraint
        if errors:
            raise InvalidEntity(entity, errors)

    def check_value(self, value):
        """check the value of a final entity (ie a const value)"""
        assert self.is_final()
        return BASE_CHECKERS[self.type](self, value)
    
    # bw compat
    subject_relation_schema = subject_relation
    object_relation_schema = object_relation

    
class RelationSchema(ERSchema):
    """A relation is a named ordered link between two entities.
    A relation schema defines the possible types of both extremities.

    cardinality between the two given entity's type is defined
    as a 2 characters string where each character is one of:
        - 1 <-> 1..1
        - ? <-> 0..1
        - + <-> 1..n
        - * <-> 0..n
    """
    ACTIONS = ('read', 'add', 'delete')    
    _RPROPERTIES = {'cardinality': None,
                    'constraints': (),
                    'order': 0,
                    'description': ''}
    _FINAL_RPROPERTIES = {'default': None,
                          'uid': False,
                          'indexed': False}
    _STRING_RPROPERTIES = {'fulltextindexed': False,
                           'internationalizable': False}
    
    __implements__ = IRelationSchema    
    
    def __init__(self, schema, rdef):
        super(RelationSchema, self).__init__(schema, rdef)
        # if this relation is symetric
        self.symetric = rdef.symetric
        # if this relation is an attribute relation
        self.final = False
        # mapping to subject/object with schema as key
        self._subj_schemas = {}
        self._obj_schemas = {}
        # mapping to subject/object with type as key
        self._subj_types = {}
        self._obj_types = {}
        # relation properties
        self._rproperties = {}
        
    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self.type,
                               self.association_types())
        
    # schema building methods #################################################

    def update(self, subjschema, objschema, rdef):
        """Allow this relation between the two given types schema
        """
        subjtype = subjschema.type
        objtype = objschema.type
        if subjschema.is_final():
            msg = 'type %s can\'t be used as subject in a relation' % subjtype
            raise BadSchemaDefinition(msg)
        # check final consistency:
        # * a final relation only points to final entity types
        # * a non final relation only points to non final entity types
        final = objschema.is_final()
        for eschema in self.objects():
            if eschema is objschema:
                continue
            if final != eschema.is_final():
                if final:
                    frtype, nfrtype = objtype, eschema.type
                else:
                    frtype, nfrtype = eschema.type, objtype
                msg = "ambiguous relation %s: %s is final but not %s" % (
                    self.type, frtype, nfrtype)
                raise BadSchemaDefinition(msg)
        self.final = final
        # update our internal struct
        self._update(subjschema, objschema)
        if self.symetric:
            self._update(objschema, subjschema)
            try:
                self.init_rproperties(subjtype, objtype, rdef)
                if objtype != subjtype:
                    self.init_rproperties(objtype, subjtype, rdef)
            except BadSchemaDefinition:
                # this is authorized for consistency
                pass
        else:
            self.init_rproperties(subjtype, objtype, rdef)
        # update extremities schema
        subjschema.add_subject_relation(self, rdef)
        if self.symetric:
            objschema.add_subject_relation(self, rdef)
        else:
            objschema.add_object_relation(self, rdef)

    def _update(self, subjectschema, objectschema):
        objtypes = self._subj_schemas.setdefault(subjectschema, [])
        if not objectschema in objtypes:
            objtypes.append(objectschema)
            self._subj_types.setdefault(subjectschema.type, []).append(objectschema)
        subjtypes = self._obj_schemas.setdefault(objectschema, [])
        if not subjectschema in subjtypes:
            subjtypes.append(subjectschema)
            self._obj_types.setdefault(objectschema.type, []).append(subjectschema)
    
    def del_relation_def(self, subjschema, objschema):
        self._subj_schemas[subjschema].remove(objschema)
        self._subj_types[subjschema.type].remove(objschema)
        if len(self._subj_schemas[subjschema]) == 0:
            del self._subj_schemas[subjschema]
            del self._subj_types[subjschema.type]
        self._obj_schemas[objschema].remove(subjschema)
        self._obj_types[objschema.type].remove(subjschema)
        if len(self._obj_schemas[objschema]) == 0:
            del self._obj_schemas[objschema]
            del self._obj_types[objschema.type]
        del self._rproperties[(subjschema.type, objschema.type)]
        if not self._obj_schemas or not self._subj_schemas:
            assert not self._obj_schemas and not self._subj_schemas
            return True
        return False
            
    def set_default_groups(self):
        """set default action -> groups mapping"""
        if self._groups:
            pass # already initialized
        elif self.final:
            self._groups = {'read': ('managers', 'users', 'guests'),
                            'delete': ('managers', 'users', 'guests'),
                            'add': ('managers', 'users', 'guests')}
        elif self.meta:
            self._groups = {'read': ('managers', 'users', 'guests'),
                            'delete': ('managers',),
                            'add': ('managers',)}
        else:
            self._groups = {'read': ('managers', 'users', 'guests',),
                            'delete': ('managers', 'users'),
                            'add': ('managers', 'users',)}
    
    
    # relation definitions properties handling ################################
    
    def rproperty_defs(self, desttype):
        """return a list tuple (property name, default value)
        for each allowable properties when the relation has `desttype` as
        target entity's type
        """
        basekeys = self._RPROPERTIES.items()
        if not self.is_final():
            return basekeys
        basekeys += self._FINAL_RPROPERTIES.items()
        if desttype != 'String':
            return basekeys
        return basekeys + self._STRING_RPROPERTIES.items()

    def rproperty_keys(self):
        """return the list of keys which have associated rproperties"""
        return self._rproperties.keys()
    
    def rproperties(self, subjecttype, objecttype):
        """return the properties dictionary of a relation"""
        #assert rtype in self._subj_relations
        try:
            return self._rproperties[(subjecttype, objecttype)]
        except KeyError:
            raise KeyError('%s %s %s' % (subjecttype, self.type, objecttype))
    
    def rproperty(self, subjecttype, objecttype, property):
        """return the properties dictionary of a relation"""
        return self.rproperties(subjecttype, objecttype).get(property)

    def set_rproperty(self, subjecttype, objecttype, pname, value):
        """set value for a subject relation specific property"""
        #assert pname in self._rproperties
        self._rproperties[(subjecttype, objecttype)][pname] = value

    def init_rproperties(self, subjecttype, objecttype, rdef):
        key = subjecttype, objecttype
        if key in self._rproperties:
            msg = '%s already defined for %s' % (key, self.type)
            raise BadSchemaDefinition(msg)
        self._rproperties[key] = {}
        for prop, default in self.rproperty_defs(key[1]):
            self._rproperties[key][prop] = getattr(rdef, prop, default)

    # IRelationSchema interface ###############################################

    def is_final(self):
        """return true if this relation has final object entity's types
        
        (we enforce that a relation can't point to both final and non final
        entity's type)
        """
        return self.final

    def association_types(self):
        """return a list of (subjecttype, [objecttypes]) defining between
        which types this relation may exists
        """
        return [(subj.type, [obj.type for obj in objs])
                for subj, objs in self._subj_schemas.items()]
        
    def subjects(self, etype=None):
        """return a list of entity schemas which can be subject of this relation
        
        If etype is not None, return a list of schemas which can be subject of
        this relation with etype as object.
        
        :raise: `KeyError` if etype is not a subject entity type.
        """
        if etype is None:
            return self._subj_schemas.keys()
        return self._obj_types[etype]
    
    def subject_types(self, etype=None):
        """return a list of entity types which can be subject of this relation
        
        If etype is not None, return a list of types which can be subject of
        this relation with etype as object.
        
        :raise: `KeyError` if etype is not a subject entity type.
        """
        return [subj.type for subj in self.subjects(etype)]
    
    def objects(self, etype=None):
        """return a list of entity schema which can be object of this relation.
        
        If etype is not None, return a list of schemas which can be object of
        this relation with etype as subject.
        
        :raise: `KeyError` if etype is not an object entity type.
        """
        if etype is None:
            return self._obj_schemas.keys()
        return self._subj_types[etype]
    
    def object_types(self, etype=None):
        """return a list of types which can be object of this relation.
        
        If etype is not None, return a list of types which can be object of
        this relation with etype as subject.
        Raise `KeyError` if etype is not an object entity type.
        """
        return [obj.type for obj in self.objects(etype)]

    def physical_mode(self):
        """return an appropriate mode for physical storage of this relation type:
        * 'subjectinline' if every possible subject cardinalities are 1 or ?
        * 'objectinline' if 'subjectinline' mode is not possible but every
          possible object cardinalities are 1 or ?
        * None if neither 'subjectinline' and 'objectinline'
        """
        assert not self.final
        subjinline, objinline = True, True
        for key in self._rproperties:
            cards = self._rproperties[key]['cardinality']
            if cards[0] not in '1?':
                subjinline = False
            if cards[1] not in '1?':
                objinline = False
        if subjinline:
            return 'subjectinline'
        if objinline:
            return 'objectinline'
        return None
    physical_mode = cached(physical_mode)

        
class Schema(object):
    """set of entities and relations schema defining the possible data sets
    used in an application


    :type name: str
    :ivar name: name of the schema, usually the application identifier
    
    :type base: str
    :ivar base: path of the directory where the schema is defined
    """
    __implements__ = ISchema
    entity_class = EntitySchema
    relation_class = RelationSchema
    
    def __init__(self, name, directory=None, **kwargs):
        super(Schema, self).__init__(**kwargs)
        self.name = name
        self.base = directory
        self._entities = {}
        self._relations = {}
        for etype in BASE_TYPES:
            edef = EntityType(name=etype, meta=True)
            self.add_entity_type(edef).set_default_groups()

    def __getitem__(self, name):
        try:
            return self.eschema(name)
        except KeyError:
            return self.rschema(name)
            
    def __contains__(self, name):
        try:
            self[name]
        except KeyError:
            return False
        return True
        
    # schema building methods #################################################
    
    def add_entity_type(self, edef):
        """add a entity schema definition for an entity's type

        :type etype: str
        :param etype: the name of the entity type to define

        :raise `BadSchemaDefinition`: if the entity type is already defined
        :rtype: `EntitySchema`
        :return: the newly created entity schema instance
        """
        etype = edef.name
        if self._entities.has_key(etype):
            msg = "entity type %s is already defined" % etype
            raise BadSchemaDefinition(msg)
        eschema = self.entity_class(self, edef)
        self._entities[etype] = eschema
        return eschema
    
    def add_relation_type(self, rtypedef):
        rtype = rtypedef.name
        if self._relations.has_key(rtype):
            msg = "relation type %s is already defined" % rtype
            raise BadSchemaDefinition(msg)
        rschema = self.relation_class(self, rtypedef)
        self._relations[rtype] = rschema
        return rschema
        
    def add_relation_def(self, rdef):
        """build a part of a relation schema:
        add a relation between two specific entity's types

        :rtype: RelationSchema
        :return: the newly created or simply completed relation schema
        """
        rtype = rdef.name
        try:
            rschema = self.rschema(rtype)
        except KeyError, ex:
            msg = 'using unknown relation type %s' % rtype
            raise BadSchemaDefinition(msg)
        try:
            subjectschema = self.eschema(rdef.subject)
        except KeyError, ex:
            msg = 'using unknown type %s in relation %s' % (str(ex), rtype)
            raise BadSchemaDefinition(msg)
        try:
            objectschema = self.eschema(rdef.object)
        except KeyError, ex:
            msg = "using unknown type %s in relation %s" % (str(ex), rtype)
            raise BadSchemaDefinition(msg)
        rschema.update(subjectschema, objectschema, rdef)

    def del_relation_def(self, subjtype, rtype, objtype):
        subjschema = self.eschema(subjtype)
        objschema = self.eschema(objtype)
        rschema = self.rschema(rtype)
        subjschema.del_subject_relation(rtype)
        if not rschema.symetric:
            objschema.del_object_relation(rtype)
        if rschema.del_relation_def(subjschema, objschema):
            del self._relations[rtype]
            
    def del_relation_type(self, rtype):
        # XXX don't iter directly on the dictionary since it may be changed
        # by del_relation_def
        for subjtype, objtype in self.rschema(rtype)._rproperties.keys():
            self.del_relation_def(subjtype, rtype, objtype)
        if not self.rschema(rtype)._rproperties:
            del self._relations[rtype]
            
    def del_entity_type(self, etype):
        eschema = self._entities[etype]
        for rschema in eschema._subj_relations.values():
            for objtype in rschema.object_types(etype):
                self.del_relation_def(eschema.type, rschema.type, objtype)
        for rschema in eschema._obj_relations.values():
            for subjtype in rschema.subject_types(etype):
                self.del_relation_def(subjtype, rschema.type, eschema.type)
        del self._entities[etype]
        
            
    # ISchema interface #######################################################
    
    def entities(self, schema=False):
        """return a list of possible entity's type

        :type schema: bool
        :param schema: return a list of schemas instead of types if true

        :rtype: list
        :return: defined entity's types (str) or schemas (`EntitySchema`)
        """
        if not schema:
            return sorted(self._entities.keys())
        return [self._entities[etype] for etype in sorted(self._entities)]
        
    def has_entity(self, etype):
        """return true the type is defined in the schema

        :type etype: str
        :param etype: the entity's type

        :rtype: bool
        :return:
          a boolean indicating whether this type is defined in this schema
        """
        return self._entities.has_key(etype)
    
    def eschema(self, etype):
        """return the entity's schema for the given type

        :rtype: `EntitySchema`
        :raise `KeyError`: if the type is not defined as an entity
        """
        return self._entities[etype]
    
    def relations(self, schema=False):
        """return the list of possible relation'types
        
        :type schema: bool
        :param schema: return a list of schemas instead of types if true

        :rtype: list
        :return: defined relation's types (str) or schemas (`RelationSchema`)
        """
        if not schema:
            return sorted(self._relations)
        return [self._relations[rtype] for rtype in sorted(self._relations)]
    
    def has_relation(self, rtype):
        """return true the relation is defined in the schema

        :type rtype: str
        :param rtype: the relation's type

        :rtype: bool
        :return:
          a boolean indicating whether this type is defined in this schema
        """
        return self._relations.has_key(rtype)

    def rschema(self, rtype):
        """return the relation schema for the given type
        
        :rtype: `RelationSchema`
        """
        return self._relations[rtype]
        
    def final_relations(self, schema=False):
        """return the list of possible final relation'types
        
        :type schema: bool
        :param schema: return a list of schemas instead of types if true

        :rtype: list
        :return: defined relation's types (str) or schemas (`RelationSchema`)
        """
        for rschema in self.relations(schema=True):
            if rschema.is_final():
                if schema:
                    yield rschema
                else:
                    yield rschema.type

    def nonfinal_relations(self, schema=False):
        """return the list of possible final relation'types
        
        :type schema: bool
        :param schema: return a list of schemas instead of types if true

        :rtype: list
        :return: defined relation's types (str) or schemas (`RelationSchema`)
        """
        for rschema in self.relations(schema=True):
            if not rschema.is_final():
                if schema:
                    yield rschema
                else:
                    yield rschema.type
                    
    # bw compat
    relation_schema = rschema
    entity_schema = eschema

