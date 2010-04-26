"""Classes used to build a schema.

:organization: Logilab
:copyright: 2003-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: Lesser General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

from warnings import warn

from logilab.common import attrdict
from logilab.common.compat import sorted
from logilab.common.decorators import iclassmethod

from yams import BASE_TYPES, MARKER, BadSchemaDefinition
from yams.constraints import (SizeConstraint, UniqueConstraint,
                              StaticVocabularyConstraint, format_constraint)

__all__ = ('EntityType', 'RelationType', 'RelationDefinition',
           'SubjectRelation', 'ObjectRelation', 'BothWayRelation',
           'RichString', ) + tuple(BASE_TYPES)

ETYPE_PROPERTIES = ('description', '__permissions__',
                    'meta') # XXX meta is deprecated
# don't put description inside, handled "manualy"
RTYPE_PROPERTIES = ('symmetric', 'inlined', 'fulltext_container',
                    'meta') # XXX meta is deprecated
RDEF_PROPERTIES = ('cardinality', 'constraints', 'composite',
                   'order',  'default', 'uid', 'indexed', 'uid',
                   'fulltextindexed', 'internationalizable',
                   '__permissions__',)

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
    if isinstance(rdef, RichString):
        format_attrdef = String(internationalizable=True,
                                default=rdef.default_format, maxsize=50,
                                constraints=rdef.format_constraints)
        _add_relation(relations, format_attrdef,
                      (name or rdef.name) + '_format', insertidx)
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
            raise BadSchemaDefinition('no such property %r in %r'
                                      % (key, attributes))

def _copy_attributes(fromobj, toobj, attributes):
    for attr in attributes:
        value = getattr(fromobj, attr, MARKER)
        if value is MARKER:
            continue
        ovalue = getattr(toobj, attr, MARKER)
        if not ovalue is MARKER and value != ovalue:
            rname = getattr(toobj, 'name', None) or toobj.__name__
            raise BadSchemaDefinition(
                'conflicting values %r/%r for property %s of relation %r'
                % (ovalue, value, attr, rname))
        setattr(toobj, attr, value)

def register_base_types(schema):
    for etype in BASE_TYPES:
        edef = EntityType(
            name=etype,
            # unused actually
            # XXX add a group in read perms to satisfy schema constraints in cw
            __permissions__={'read': ('users',), 'add': (), 'delete': (),
                             'update': ()})
        schema.add_entity_type(edef)

# XXX use a "frozendict"
DEFAULT_RELPERMS = {'read': ('managers', 'users', 'guests',),
                     'delete': ('managers', 'users'),
                     'add': ('managers', 'users',)}

DEFAULT_ATTRPERMS = {'read': ('managers', 'users', 'guests',),
                      'update': ('managers', 'owners'),
                      }

class Relation(object):
    """Abstract class which have to be defined before the metadefinition
    meta-class.
    """
    __permissions__ = MARKER

# first class schema definition objects #######################################

class Definition(object):
    """Abstract class for entity / relation definition classes."""

    meta = MARKER
    description = MARKER
    __permissions__ = MARKER

    def __init__(self, name=None):
        self.name = (name or getattr(self, 'name', None)
                     or self.__class__.__name__)
        if self.__doc__:
            self.description = ' '.join(self.__doc__.split())

    def __repr__(self):
        return '<%s %r @%x>' % (self.__class__.__name__, self.name, id(self))

    @classmethod
    def expand_type_definitions(cls, defined):
        """Schema building step 1: register definition objects by adding them
        to the `defined` dictionnary.
        """
        raise NotImplementedError()

    @classmethod
    def expand_relation_definitions(cls, defined, schema):
        """Schema building step 2: register all relations definition,
        expanding wildcard if necessary.
        """
        raise NotImplementedError()

    @iclassmethod
    def get_permissions(cls, final=False):
        if cls.__permissions__ is MARKER:
            if final:
                return DEFAULT_ATTRPERMS
            return DEFAULT_RELPERMS
        return cls.__permissions__

    @classmethod
    def set_permissions(cls, perms):
        cls.__permissions__ = perms

    @classmethod
    def set_action_permissions(cls, action, actionperms):
        permissions = cls.get_permissions().copy()
        permissions[action] = actionperms
        cls.__permissions__ = permissions


class XXX_backward_permissions_compat(type):
    stacklevel = 2
    def __new__(mcs, name, bases, classdict):
        if 'permissions' in classdict:
            classdict['__permissions__'] = classdict.pop('permissions')
            warn('[yams 0.27.0] permissions is deprecated, use __permissions__ instead (class %s)' % name,
                 DeprecationWarning, stacklevel=mcs.stacklevel)
        if 'symetric' in classdict:
            classdict['symmetric'] = classdict.pop('symetric')
            warn('[yams 0.27.0] symetric has been respelled symmetric (class %s)' % name,
                 DeprecationWarning, stacklevel=mcs.stacklevel)
        return super(XXX_backward_permissions_compat, mcs).__new__(mcs, name, bases, classdict)

    # XXX backward compatiblity
    def get_permissions(cls):
        warn('[yams 0.27.0] %s.permissions is deprecated, use .__permissions__ instead'
             % cls.__name__, DeprecationWarning, stacklevel=2)
        return cls.__permissions__

    def set_permissions(cls, newperms):
        warn('[yams 0.27.0] %s.permissions is deprecated, use .__permissions__ instead'
             % cls.__name__, DeprecationWarning, stacklevel=2)
        cls.__permissions__ = newperms

    permissions = property(get_permissions, set_permissions)


class metadefinition(XXX_backward_permissions_compat):
    """Metaclass that builds the __relations__ attribute of
    EntityType's subclasses.
    """
    stacklevel = 3
    def __new__(mcs, name, bases, classdict):

        rels = classdict.setdefault('__relations__', [])
        relations = dict((rdef.name, rdef) for rdef in rels)
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
            for rdef in getattr(base, '__relations__', ()):
                if not rdef.name in relations or not relations[rdef.name].override:
                    rels.append(rdef)
                else:
                    relations[rdef.name].creation_rank = rdef.creation_rank
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
    # XXX use a "frozendict"
    __permissions__ = {
        'read': ('managers', 'users', 'guests',),
        'update': ('managers', 'owners',),
        'delete': ('managers', 'owners'),
        'add': ('managers', 'users',)
        }

    def __init__(self, name=None, **kwargs):
        super(EntityType, self).__init__(name)
        _check_kwargs(kwargs, ETYPE_PROPERTIES)
        self.__dict__.update(kwargs)
        self.specialized_type = self.__class__.__dict__.get('__specializes__')

    def __str__(self):
        return 'entity type %r' % self.name

    @property
    def specialized_by(self):
        return self.__class__.__dict__.get('__specialized_by__', [])

    @classmethod
    def expand_type_definitions(cls, defined):
        """Schema building step 1: register definition objects by adding
        them to the `defined` dictionnary.
        """
        name = getattr(cls, 'name', cls.__name__)
        assert cls is not defined.get(name), 'duplicate registration: %s' % name
        assert name not in defined, \
            "type '%s' was already defined here %s, new definition here %s" % \
            (name, defined[name].__module__, cls)
        cls._defined = defined # XXX may be used later (eg .add_relation())
        defined[name] = cls
        for relation in cls.__relations__:
            cls._ensure_relation_type(relation)

    @classmethod
    def _ensure_relation_type(cls, relation):
        """Check the type the relation

        return False if the class is not yet finalized
        (XXX raise excep instead ?)"""
        rtype = RelationType(relation.name)
        _copy_attributes(relation, rtype, RTYPE_PROPERTIES)
        #assert hasattr(cls, '_defined'), "Type definition for %s not yet expanded. you can't register new type through it" % cls
        if hasattr(cls, '_defined'):
            defined = cls._defined
            if relation.name in defined:
                _copy_attributes(rtype, defined[relation.name], RTYPE_PROPERTIES)
            else:
                defined[relation.name] = rtype
            return True
        else:
            return False

    @classmethod
    def expand_relation_definitions(cls, defined, schema):
        """schema building step 2:

        register all relations definition, expanding wildcards if necessary
        """
        order = 1
        name = getattr(cls, 'name', cls.__name__)
        for relation in cls.__relations__:
            if isinstance(relation, SubjectRelation):
                rdef = RelationDefinition(subject=name, name=relation.name,
                                          object=relation.etype, order=order)
                _copy_attributes(relation, rdef, RDEF_PROPERTIES + ('description',))
            elif isinstance(relation, ObjectRelation):
                rdef = RelationDefinition(subject=relation.etype,
                                          name=relation.name,
                                          object=name, order=order)
                _copy_attributes(relation, rdef, RDEF_PROPERTIES + ('description',))
            elif isinstance(relation, RelationDefinition):
                rdef = relation
            else:
                raise BadSchemaDefinition('dunno how to handle %s' % relation)
            order += 1
            rdef._add_relations(defined, schema)

    # methods that can be used to extend an existant schema definition ########

    @classmethod
    def extend(cls, othermetadefcls):
        for rdef in othermetadefcls.__relations__:
            cls.add_relation(rdef)

    @classmethod
    def add_relation(cls, rdef, name=None):
        if name:
            rdef.name = name
        if cls._ensure_relation_type(rdef):
            _add_relation(cls.__relations__, rdef, name)
            if isinstance(rdef, RichString) and not rdef in cls._defined:
                format_attr_name = (name or rdef.name) + '_format'
                rdef = cls.get_relations(format_attr_name).next()
                cls._ensure_relation_type(rdef)
        else:
           _add_relation(cls.__relations__, rdef, name=name)

    @classmethod
    def insert_relation_after(cls, afterrelname, name, rdef):
        # FIXME change order of arguments to rdef, name, afterrelname ?
        rdef.name = name
        cls._ensure_relation_type(rdef)
        for i, rel in enumerate(cls.__relations__):
            if rel.name == afterrelname:
                break
        else:
            raise BadSchemaDefinition("can't find %s relation on %s" % (
                    afterrelname, cls))
        _add_relation(cls.__relations__, rdef, name, i+1)

    @classmethod
    def remove_relation(cls, name):
        for rdef in cls.get_relations(name):
            cls.__relations__.remove(rdef)

    @classmethod
    def get_relations(cls, name):
        """get relation definitions by name (may have multiple definitions with
        the same name if the relation is both a subject and object relation)
        """
        for rdef in cls.__relations__[:]:
            if rdef.name == name:
                yield rdef

    @classmethod
    def get_relation(cls, name):
        """get relation definitions by name (may have multiple definitions with
        the same name if the relation is both a subject and object relation)
        """
        relations = tuple(cls.get_relations(name))
        assert len(relations) == 1, "can't use get_relation for relation with multiple definitions"
        return relations[0]


class RelationType(Definition):
    __metaclass__ = XXX_backward_permissions_compat

    symmetric = MARKER
    inlined = MARKER
    fulltext_container = MARKER

    def __init__(self, name=None, **kwargs):
        """kwargs must have values in RTYPE_PROPERTIES"""
        super(RelationType, self).__init__(name)
        if kwargs.pop('meta', None):
            warn('[yams 0.25] meta is deprecated', DeprecationWarning, stacklevel=2)
        _check_kwargs(kwargs, RTYPE_PROPERTIES + ('description', '__permissions__'))
        self.__dict__.update(kwargs)

    def __str__(self):
        return 'relation type %r' % self.name

    @classmethod
    def expand_type_definitions(cls, defined):
        """schema building step 1:

        register definition objects by adding them to the `defined` dictionnary
        """
        name = getattr(cls, 'name', cls.__name__)
        if cls.__doc__ and not cls.description:
            cls.description = ' '.join(cls.__doc__.split())
        if name in defined:
            if defined[name].__class__ is not RelationType:
                raise BadSchemaDefinition('duplicated relation type for %s'
                                          % name)
            # relation type created from a relation definition, override it
            _copy_attributes(defined[name], cls,
                             REL_PROPERTIES + ('subject', 'object'))
        defined[name] = cls

    @classmethod
    def expand_relation_definitions(cls, defined, schema):
        """schema building step 2:

        register all relations definition, expanding wildcard if necessary
        """
        name = getattr(cls, 'name', cls.__name__)
        if getattr(cls, 'subject', None) and getattr(cls, 'object', None):
            rdef = RelationDefinition(subject=cls.subject, name=name,
                                      object=cls.object)
            _copy_attributes(cls, rdef, RDEF_PROPERTIES)
            rdef._add_relations(defined, schema)


class RelationDefinition(Definition):
    # FIXME reader magic forbids to define a docstring...
    #"""a relation is defined by a name, the entity types that can be
    #subject or object the relation, the cardinality, the constraints
    #and the symmetric property.
    #"""

    subject = MARKER
    object = MARKER
    cardinality = MARKER
    constraints = MARKER
    symmetric = MARKER
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
        if kwargs.pop('meta', None):
            warn('[yams 0.25] meta is deprecated', DeprecationWarning)
        if 'symetric' in kwargs:
            warn('[yams 0.27.0] symetric has been respelled symmetric',
                 DeprecationWarning, stacklevel=2)
            kwargs['symmetric'] = kwargs.pop('symetric')
        _check_kwargs(kwargs, RDEF_PROPERTIES + ('description',))
        _copy_attributes(attrdict(**kwargs), self, RDEF_PROPERTIES + ('description',))
        if self.constraints:
            self.constraints = list(self.constraints)

    def __str__(self):
        return 'relation definition (%(subject)s %(name)s %(object)s)' % self.__dict__

    @classmethod
    def expand_type_definitions(cls, defined):
        """schema building step 1:

        register definition objects by adding them to the `defined` dictionnary
        """
        name = getattr(cls, 'name', cls.__name__)
        rtype = RelationType(name)
        if hasattr(cls, 'symetric'):
            cls.symmetric = cls.symetric
            del cls.symetric
            warn('[yams 0.27.0] symetric has been respelled symmetric (class %s)' % name,
                 DeprecationWarning)
        _copy_attributes(cls, rtype, RTYPE_PROPERTIES)
        if name in defined:
            _copy_attributes(rtype, defined[name], RTYPE_PROPERTIES)
        else:
            defined[name] = rtype
        key = (cls.subject, name, cls.object)
        if key in defined:
            raise BadSchemaDefinition('duplicated %s' % cls)
        defined[key] = cls

    @classmethod
    def expand_relation_definitions(cls, defined, schema):
        """schema building step 2:

        register all relations definition, expanding wildcard if necessary
        """
        assert cls.subject and cls.object, '%s; check the schema' % cls
        cls()._add_relations(defined, schema)

    def _add_relations(self, defined, schema):
        name = getattr(self, 'name', self.__class__.__name__)
        rtype = defined[name]
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
        rschema = schema.rschema(name)
        if self.subject == '**' or self.object == '**':
            warn('[yams 0.25] ** is deprecated, use * (%s)' % rtype, DeprecationWarning)
        if self.__permissions__ is MARKER:
            final = iter(_actual_types(schema, self.object)).next() in BASE_TYPES
            permissions = rtype.get_permissions(final)
        else:
            permissions = self.__permissions__
        for subj in _actual_types(schema, self.subject):
            for obj in _actual_types(schema, self.object):
                rdef = RelationDefinition(subj, name, obj, __permissions__=permissions)
                _copy_attributes(self, rdef, RDEF_PROPERTIES + ('description',))
                schema.add_relation_def(rdef)

def _actual_types(schema, etype):
    if etype in ('**', '*'): # XXX ** is deprecated
        return _pow_etypes(schema)
    if isinstance(etype, (list, tuple)):
        return etype
    if not isinstance(etype, basestring):
        raise RuntimeError('Entity types must not be instances but strings '
                           'or list/tuples thereof. Ex. (bad, good) : '
                           'SubjectRelation(Foo), SubjectRelation("Foo"). '
                           'Hence, %r is not acceptable.' % etype)
    return (etype,)

def _pow_etypes(schema):
    for eschema in schema.entities():
        if eschema.final:
            continue
        yield eschema.type


# classes used to define relationships within entity type classes ##################


# \(Object\|Subject\)Relation(relations, '\([a-z_A-Z]+\)',
# -->
# \2 = \1Relation(

class ObjectRelation(Relation):
    cardinality = MARKER
    constraints = MARKER
    created = 0

    def __init__(self, etype, **kwargs):
        if self.__class__.__name__ == 'ObjectRelation':
            warn('[yams 0.29] ObjectRelation is deprecated, '
                 'use RelationDefinition subclass', DeprecationWarning,
                 stacklevel=2)
        ObjectRelation.created += 1
        self.creation_rank = ObjectRelation.created
        self.name = '<undefined>'
        self.etype = etype
        if self.constraints:
            self.constraints = list(self.constraints)
        self.override = kwargs.pop('override', False)
        if 'symetric' in kwargs:
            kwargs['symmetric'] = kwargs.pop('symetric')
            warn('[yams 0.27.0] symetric has been respelled symmetric',
                 DeprecationWarning, stacklevel=2)
        try:
            _check_kwargs(kwargs, REL_PROPERTIES)
        except BadSchemaDefinition, bad:
            # XXX (auc) bad field name + required attribute can lead there instead of schema.py ~ 920
            bsd_ex = BadSchemaDefinition(('%s in relation to entity %r (also is %r defined ? (check two '
                                          'lines above in the backtrace))') % (bad.args, etype, etype))
            bsd_ex.tb_offset = 2
            raise bsd_ex
        self.__dict__.update(kwargs)

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
        warn('[yams 0.29] BothWayRelation is deprecated, '
             'use RelationDefinition subclass', DeprecationWarning,
             stacklevel=2)
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

# provides a RichString class for convenience


class RichString(String):
    """Convenience RichString attribute type
    The following declaration::

      class Card(EntityType):
          content = RichString(fulltextindexed=True, default_format='text/rest')

    is equivalent to::

      class Card(EntityType):
          content_format = String(internationalizable=True,
                                  default='text/rest', constraints=[format_constraint])
          content  = String(fulltextindexed=True)
    """
    def __init__(self, default_format='text/plain', format_constraints=None, **kwargs):
        self.default_format = default_format
        self.format_constraints = format_constraints or [format_constraint]
        super(RichString, self).__init__(**kwargs)


# various derivated classes with some predefined values XXX deprecated

class MetaEntityType(EntityType):
    __permissions__ = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers',),
        'update': ('managers', 'owners',),
        'delete': ('managers',),
        }

class MetaUserEntityType(EntityType):
    pass

class MetaRelationType(RelationType):
    __permissions__ = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers',),
        'delete': ('managers',),
        }

class MetaUserRelationType(RelationType):
    pass

class MetaAttributeRelationType(RelationType):
    # just set permissions to None so default permissions are set
    __permissions__ = MARKER


__all__ += ('MetaEntityType', 'MetaUserEntityType',
            'MetaRelationType', 'MetaUserRelationType',
            'MetaAttributeRelationType')

