"""Classes used to build a schema.

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

from logilab.common import attrdict
from logilab.common.compat import sorted

from yams import BASE_TYPES, MARKER, BadSchemaDefinition
from yams.constraints import (SizeConstraint, UniqueConstraint,
                              StaticVocabularyConstraint)

__all__ = ('ObjectRelation', 'SubjectRelation', 'BothWayRelation',
           'RelationDefinition', 'EntityType', 'MetaEntityType',
           'RestrictedEntityType', 'UserEntityType', 'MetaUserEntityType',
           'RelationType', 'MetaRelationType', 'UserRelationType',
           'MetaUserRelationType', 'AttributeRelationType',
           'MetaAttributeRelationType',
           'SubjectRelation', 'ObjectRelation', 'BothWayRelation',
           ) + tuple(BASE_TYPES)

ETYPE_PROPERTIES = ('meta', 'description', 'permissions')
# don't put description inside, handled "manually"
RTYPE_PROPERTIES = ('meta', 'symetric', 'inlined', 'fulltext_container', 'permissions')
RDEF_PROPERTIES = ('cardinality', 'constraints', 'composite',
                   'order',  'default', 'uid', 'indexed', 'uid',
                   'fulltextindexed', 'internationalizable')

REL_PROPERTIES = RTYPE_PROPERTIES+RDEF_PROPERTIES + ('description',)


def _add_constraint(kwargs, constraint):
    """Add constraint to param kwargs."""
    constraints = kwargs.setdefault('constraints', [])
    for i, existingconstraint in enumerate(constraints):
        if existingconstraint.__class__ is constraint.__class__:
            constraints[i] = constraint
            return
    constraints.append(constraint)

def _add_relation(relations, rdef, name=None, insertidx=None):
    """Add relation (param rdef) to list of relations (param relations)."""
    if isinstance(rdef, BothWayRelation):
        _add_relation(relations, rdef.subjectrel, name, insertidx)
        _add_relation(relations, rdef.objectrel, name, insertidx)
    else:
        if name is not None:
            rdef.name = name
        if insertidx is None:
            relations.append(rdef)
        else:
            relations.insert(insertidx, rdef)

def _check_kwargs(kwargs, attributes):
    """Check that all keys of kwargs are actual attributes."""
    for key in kwargs:
        if not key in attributes:
            raise BadSchemaDefinition('no such property %r in %r' % (key, attributes))

def _copy_attributes(fromobj, toobj, attributes):
    for attr in attributes:
        value = getattr(fromobj, attr, MARKER)
        if value is MARKER:
            continue
        ovalue = getattr(toobj, attr, MARKER)
        if not ovalue is MARKER and value != ovalue:
            raise BadSchemaDefinition('conflicting values %r/%r for property %s of %s'
                                      % (ovalue, value, attr, toobj))
        setattr(toobj, attr, value)

def register_base_types(schema):
    for etype in BASE_TYPES:
        edef = EntityType(name=etype, meta=True)
        schema.add_entity_type(edef).set_default_groups()


class Relation(object):
    """Abstract class which have to be defined before the metadefinition
    meta-class.
    """

# first class schema definition objects #######################################

class Definition(object):
    """Abstract class for entity / relation definition classes."""

    meta = MARKER
    description = MARKER

    def __init__(self, name=None):
        self.name = (name or getattr(self, 'name', None)
                     or self.__class__.__name__)
        if self.__doc__:
            self.description = ' '.join(self.__doc__.split())

    def __repr__(self):
        return '<%s %r @%x>' % (self.__class__.__name__, self.name, id(self))

    def expand_type_definitions(self, defined):
        """Schema building step 1: register definition objects by adding them
        to the `defined` dictionnary.
        """
        raise NotImplementedError()

    def expand_relation_definitions(self, defined, schema):
        """Schema building step 2: register all relations definition,
        expanding wildcard if necessary.
        """
        raise NotImplementedError()


class metadefinition(type):
    """Metaclass that builds the __relations__ attribute of
    EntityType's subclasses.
    """
    def __new__(mcs, name, bases, classdict):
        classdict['__relations__'] = rels = []
        relations = {}
        for rname, rdef in classdict.items():
            if isinstance(rdef, Relation):
                # relation's name **must** be removed from class namespace
                # to avoid conflicts with instance's potential attributes
                del classdict[rname]
                relations[rname] = rdef
        if '__specializes_schema__' in classdict:
            specialized = bases[0]
            classdict['__specializes__'] = specialized.__name__
            if '__specialized_by__' not in specialized.__dict__:
                specialized.__specialized_by__ = []
            specialized.__specialized_by__.append(name)
        defclass = super(metadefinition, mcs).__new__(mcs, name, bases, classdict)
        for rname, rdef in relations.items():
            _add_relation(defclass.__relations__, rdef, rname)
        # take base classes'relations into account
        for base in bases:
            rels.extend(getattr(base, '__relations__', []))
        # sort relations by creation rank
        defclass.__relations__ = sorted(rels, key=lambda r: r.creation_rank)
        return defclass


class EntityType(Definition):
    # FIXME reader magic forbids to define a docstring...
    #"""an entity has attributes and can be linked to other entities by
    #relations. Both entity attributes and relationships are defined by
    #class attributes.
    #
    #kwargs keys must have values in ETYPE_PROPERTIES
    #
    #Example:
    #
    #>>> class Project(EntityType):
    #...     name = String()
    #>>>
    #"""

    __metaclass__ = metadefinition

    def __init__(self, name=None, **kwargs):
        super(EntityType, self).__init__(name)
        _check_kwargs(kwargs, ETYPE_PROPERTIES)
        _copy_attributes(attrdict(kwargs), self, ETYPE_PROPERTIES)
        # if not hasattr(self, 'relations'):
        self.relations = list(self.__relations__)
        self.specialized_type = self.__class__.__dict__.get('__specializes__')

    @property
    def specialized_by(self):
        return self.__class__.__dict__.get('__specialized_by__', [])

    def __str__(self):
        return 'entity type %r' % self.name

    def expand_type_definitions(self, defined):
        """Schema building step 1: register definition objects by adding
        them to the `defined` dictionnary.
        """
        assert self.name not in defined, "type '%s' was already defined" % self.name
        self._defined = defined # XXX may be used later (eg .add_relation())
        defined[self.name] = self
        for relation in self.relations:
            self._ensure_relation_type(relation)

    def _ensure_relation_type(self, relation):
        rtype = RelationType(relation.name)
        _copy_attributes(relation, rtype, RTYPE_PROPERTIES)
        defined = self._defined
        if relation.name in defined:
            _copy_attributes(rtype, defined[relation.name], RTYPE_PROPERTIES)
        else:
            defined[relation.name] = rtype

    def expand_relation_definitions(self, defined, schema):
        """schema building step 2:

        register all relations definition, expanding wildcards if necessary
        """
        order = 1
        for relation in self.relations:
            if isinstance(relation, SubjectRelation):
                rdef = RelationDefinition(subject=self.name, name=relation.name,
                                          object=relation.etype, order=order)
                _copy_attributes(relation, rdef, RDEF_PROPERTIES + ('description',))
            elif isinstance(relation, ObjectRelation):
                rdef = RelationDefinition(subject=relation.etype,
                                          name=relation.name,
                                          object=self.name, order=order)
                _copy_attributes(relation, rdef, RDEF_PROPERTIES + ('description',))
            else:
                raise BadSchemaDefinition('dunno how to handle %s' % relation)
            order += 1
            rdef._add_relations(defined, schema)

    # methods that can be used to extend an existant schema definition ########

    def extend(self, othermetadefcls):
        for rdef in othermetadefcls.__relations__:
            self.add_relation(rdef)

    def add_relation(self, rdef, name=None):
        if name:
            rdef.name = name
        self._ensure_relation_type(rdef)
        _add_relation(self.relations, rdef, name)

    def insert_relation_after(self, afterrelname, name, rdef):
        # FIXME change order of arguments to rdef, name, afterrelname ?
        rdef.name = name
        self._ensure_relation_type(rdef)
        for i, rel in enumerate(self.relations):
            if rel.name == afterrelname:
                break
        else:
            raise BadSchemaDefinition("can't find %s relation on %s" % (
                    afterrelname, self))
        _add_relation(self.relations, rdef, name, i+1)

    def remove_relation(self, name):
        for rdef in self.get_relations(name):
            self.relations.remove(rdef)
            self.__relations__.remove(rdef)

    def get_relations(self, name):
        """get relation definitions by name (may have multiple definitions with
        the same name if the relation is both a subject and object relation)
        """
        for rdef in self.relations[:]:
            if rdef.name == name:
                yield rdef

class RelationType(Definition):
    symetric = MARKER
    inlined = MARKER
    fulltext_container = MARKER

    def __init__(self, name=None, **kwargs):
        """kwargs must have values in RTYPE_PROPERTIES"""
        super(RelationType, self).__init__(name)
        _check_kwargs(kwargs, RTYPE_PROPERTIES + ('description',))
        _copy_attributes(attrdict(kwargs), self, RTYPE_PROPERTIES + ('description',))

    def __str__(self):
        return 'relation type %r' % self.name

    def expand_type_definitions(self, defined):
        """schema building step 1:

        register definition objects by adding them to the `defined` dictionnary
        """
        if self.name in defined:
            _copy_attributes(self, defined[self.name],
                             REL_PROPERTIES + ('subject', 'object'))
        else:
            defined[self.name] = self

    def expand_relation_definitions(self, defined, schema):
        """schema building step 2:

        register all relations definition, expanding wildcard if necessary
        """
        if getattr(self, 'subject', None) and getattr(self, 'object', None):
            rdef = RelationDefinition(subject=self.subject, name=self.name,
                                      object=self.object)
            _copy_attributes(self, rdef, RDEF_PROPERTIES)
            rdef._add_relations(defined, schema)


class RelationDefinition(Definition):
    # FIXME reader magic forbids to define a docstring...
    #"""a relation is defined by a name, the entity types that can be
    #subject or object the relation, the cardinality, the constraints
    #and the symetric property.
    #"""

    subject = MARKER
    object = MARKER
    cardinality = MARKER
    constraints = MARKER
    symetric = MARKER
    inlined = MARKER

    def __init__(self, subject=None, name=None, object=None, **kwargs):
        """kwargs keys must have values in RDEF_PROPERTIES"""
        if subject:
            self.subject = subject
        else:
            self.subject = self.__class__.subject
        if object:
            self.object = object
        else:
            self.object = self.__class__.object
        super(RelationDefinition, self).__init__(name)
        _check_kwargs(kwargs, RDEF_PROPERTIES + ('description',))
        _copy_attributes(attrdict(kwargs), self, RDEF_PROPERTIES + ('description',))
        if self.constraints:
            self.constraints = list(self.constraints)

    def __str__(self):
        return 'relation definition (%(subject)s %(name)s %(object)s)' % self.__dict__

    def expand_type_definitions(self, defined):
        """schema building step 1:

        register definition objects by adding them to the `defined` dictionnary
        """
        rtype = RelationType(self.name)
        _copy_attributes(self, rtype, RTYPE_PROPERTIES)
        if self.name in defined:
            _copy_attributes(rtype, defined[self.name], RTYPE_PROPERTIES)
        else:
            defined[self.name] = rtype
        key = (self.subject, self.name, self.object)
        if key in defined:
            raise BadSchemaDefinition('duplicated %s' % self)
        defined[key] = self

    def expand_relation_definitions(self, defined, schema):
        """schema building step 2:

        register all relations definition, expanding wildcard if necessary
        """
        assert self.subject and self.object, '%s; check the schema' % self
        self._add_relations(defined, schema)

    def _add_relations(self, defined, schema):
        rtype = defined[self.name]
        _copy_attributes(rtype, self, RDEF_PROPERTIES)
        # process default cardinality and constraints if not set yet
        cardinality = self.cardinality
        if cardinality is MARKER:
            if self.object in BASE_TYPES:
                self.cardinality = '?1'
            else:
                self.cardinality = '**'
        else:
            assert len(cardinality) == 2
            assert cardinality[0] in '1?+*'
            assert cardinality[1] in '1?+*'
        if not self.constraints:
            self.constraints = ()
        rschema = schema.rschema(self.name)
        for subj in self._actual_types(schema, self.subject):
            for obj in self._actual_types(schema, self.object):
                rdef = RelationDefinition(subj, self.name, obj)
                _copy_attributes(self, rdef, RDEF_PROPERTIES + ('description',))
                schema.add_relation_def(rdef)

    def _actual_types(self, schema, etype):
        if etype == '*':
            return self._wildcard_etypes(schema)
        elif etype == '**':
            return self._pow_etypes(schema)
        elif isinstance(etype, (tuple, list)):
            return etype
        return (etype,)

    def _wildcard_etypes(self, schema):
        for eschema in schema.entities():
            if eschema.is_final() or eschema.meta:
                continue
            yield eschema.type

    def _pow_etypes(self, schema):
        for eschema in schema.entities():
            if eschema.is_final():
                continue
            yield eschema.type


# various derivated classes with some predefined values #######################

class MetaEntityType(EntityType):
    permissions = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers',),
        'delete': ('managers',),
        'update': ('managers', 'owners',),
        }
    meta = True

class RestrictedEntityType(MetaEntityType):
    permissions = {
        'read':   ('managers', 'users',),
        'add':    ('managers',),
        'delete': ('managers',),
        'update': ('managers', 'owners',),
        }

class UserEntityType(EntityType):
    permissions = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers', 'users',),
        'delete': ('managers', 'owners',),
        'update': ('managers', 'owners',),
        }

class MetaUserEntityType(UserEntityType):
    meta = True


class MetaRelationType(RelationType):
    permissions = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers',),
        'delete': ('managers',),
        }
    meta = True

class UserRelationType(RelationType):
    permissions = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers', 'users',),
        'delete': ('managers', 'users',),
        }

class MetaUserRelationType(UserRelationType):
    meta = True


class AttributeRelationType(RelationType):
    # just set permissions to None so default permissions are set
    permissions = MARKER

class MetaAttributeRelationType(AttributeRelationType):
    meta = True

# classes used to define relationships within entity type classes ##################


# \(Object\|Subject\)Relation(relations, '\([a-z_A-Z]+\)',
# -->
# \2 = \1Relation(

class ObjectRelation(Relation):
    cardinality = MARKER
    constraints = MARKER
    created = 0

    def __init__(self, etype, **kwargs):
        ObjectRelation.created += 1
        self.creation_rank = ObjectRelation.created
        self.name = '<undefined>'
        self.etype = etype
        if self.constraints:
            self.constraints = list(self.constraints)
        try:
            _check_kwargs(kwargs, REL_PROPERTIES)
        except BadSchemaDefinition, bad:
            # XXX (auc) bad field name + required attribute can lead there instead of schema.py ~ 920
             bsd_ex = BadSchemaDefinition(('%s in relation to entity %r (also is %r defined ? (check two '
                                           'lines above in the backtrace))') % (bad.args, etype, etype))
             setattr(bsd_ex,'tb_offset',2)
             raise bsd_ex
        _copy_attributes(attrdict(kwargs), self, REL_PROPERTIES)

    def __repr__(self):
        return '%(name)s %(etype)s' % self.__dict__


class SubjectRelation(ObjectRelation):
    uid = MARKER
    indexed = MARKER
    fulltextindexed = MARKER
    internationalizable = MARKER
    default = MARKER

    def __repr__(self):
        return '%(etype)s %(name)s' % self.__dict__


class BothWayRelation(Relation):

    def __init__(self, subjectrel, objectrel):
        assert isinstance(subjectrel, SubjectRelation)
        assert isinstance(objectrel, ObjectRelation)
        self.subjectrel = subjectrel
        self.objectrel = objectrel
        self.creation_rank = subjectrel.creation_rank


class AbstractTypedAttribute(SubjectRelation):
    """AbstractTypedAttribute is not directly instantiable

    subclasses must provide a <etype> attribute to be instantiable
    """
    def __init__(self, **kwargs):
        required = kwargs.pop('required', False)
        if required:
            cardinality = '11'
        else:
            cardinality = '?1'
        kwargs['cardinality'] = cardinality
        maxsize = kwargs.pop('maxsize', None)
        if maxsize is not None:
            _add_constraint(kwargs, SizeConstraint(max=maxsize))
        vocabulary = kwargs.pop('vocabulary', None)
        if vocabulary is not None:
            self.set_vocabulary(vocabulary, kwargs)
        unique = kwargs.pop('unique', None)
        if unique:
            _add_constraint(kwargs, UniqueConstraint())
        # use the etype attribute provided by subclasses
        super(AbstractTypedAttribute, self).__init__(self.etype, **kwargs)

    def set_vocabulary(self, vocabulary, kwargs=None):
        if kwargs is None:
            kwargs = self.__dict__
        #constraints = kwargs.setdefault('constraints', [])
        _add_constraint(kwargs, StaticVocabularyConstraint(vocabulary))
        if self.__class__.__name__ == 'String': # XXX
            maxsize = max(len(x) for x in vocabulary)
            _add_constraint(kwargs, SizeConstraint(max=maxsize))

    def __repr__(self):
        return '<%(name)s(%(etype)s)>' % self.__dict__

# build a specific class for each base type
for basetype in BASE_TYPES:
    globals()[basetype] = type(basetype, (AbstractTypedAttribute,),
                               {'etype' : basetype})

