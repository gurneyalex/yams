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
"""Classes used to build a schema."""

__docformat__ = "restructuredtext en"

from warnings import warn
from copy import copy

from six import add_metaclass, string_types

from logilab.common import attrdict

from yams import (BASE_TYPES, MARKER, BadSchemaDefinition, KNOWN_METAATTRIBUTES,
                  DEFAULT_ETYPEPERMS, DEFAULT_RELPERMS, DEFAULT_ATTRPERMS,
                  DEFAULT_COMPUTED_ATTRPERMS)
from yams.constraints import (SizeConstraint, UniqueConstraint,
                              StaticVocabularyConstraint, FORMAT_CONSTRAINT)
from yams.schema import RelationDefinitionSchema

PACKAGE = '<builtin>' # will be modified by the yams'reader when schema is
                      # beeing read

__all__ = ('EntityType', 'RelationType', 'RelationDefinition',
           'SubjectRelation', 'ObjectRelation',
           'RichString', ) + tuple(BASE_TYPES)

# EntityType properties
ETYPE_PROPERTIES = ('description', '__permissions__', '__unique_together__')
# RelationType properties. Don't put description inside, handled specifically
RTYPE_PROPERTIES = ('symmetric', 'inlined', 'fulltext_container')
# RelationDefinition properties have to be computed dynamically since new ones
# may be added at runtime
def _RDEF_PROPERTIES():
    base = RelationDefinitionSchema.ALL_PROPERTIES()
    # infered is an internal property and should not be specified explicitly
    base.remove('infered')
    # replace permissions by __permissions__ as it's spelled that way in schema
    # definition files
    base.remove('permissions')
    base.add('__permissions__')
    return tuple(base)
# regroup all rtype/rdef properties as they may be defined one on each other in
# some cases
def _REL_PROPERTIES():
    return RTYPE_PROPERTIES + _RDEF_PROPERTIES()

# pre 0.37 backward compat
RDEF_PROPERTIES = () # stuff added here is also added to underlying dict, nevermind


CREATION_RANK = 0

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
    if name is not None:
        rdef.name = name
    if insertidx is None:
        insertidx = len(relations)
    relations.insert(insertidx, rdef)
    if getattr(rdef, 'metadata', {}):
        for meta_name, value in rdef.metadata.items():
            assert meta_name in KNOWN_METAATTRIBUTES
            insertidx += 1 # insert meta after main
            meta_rel_name = '_'.join(((name or rdef.name), meta_name))
            _add_relation(relations, value, meta_rel_name, insertidx)

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
    """add base (final) entity types to the given schema"""
    for etype in BASE_TYPES:
        edef = EntityType(name=etype)
        schema.add_entity_type(edef)


# first class schema definition objects #######################################

class autopackage(type):
    def __new__(mcs, name, bases, classdict):
        classdict['package'] = PACKAGE
        return super(autopackage, mcs).__new__(mcs, name, bases, classdict)


@add_metaclass(autopackage)
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

    def get_permissions(self, final=False):
        if self.__permissions__ is MARKER:
            if final:
                return DEFAULT_ATTRPERMS
            return DEFAULT_RELPERMS
        return self.__permissions__

    @classmethod
    def set_permissions(cls, perms):
        cls.__permissions__ = perms


# classes used to define relationships within entity type classes ##################

# has to be defined before the metadefinition metaclass which "isinstance" this
# class
class ObjectRelation(object):
    __permissions__ = MARKER
    cardinality = MARKER
    constraints = MARKER

    def __init__(self, etype, **kwargs):
        if self.__class__.__name__ == 'ObjectRelation':
            warn('[yams 0.29] ObjectRelation is deprecated, '
                 'use RelationDefinition subclass', DeprecationWarning,
                 stacklevel=2)
        global CREATION_RANK
        CREATION_RANK += 1
        self.creation_rank = CREATION_RANK
        self.package = PACKAGE
        self.name = '<undefined>'
        self.etype = etype
        if self.constraints:
            self.constraints = list(self.constraints)
        self.override = kwargs.pop('override', False)
        if kwargs.pop('meta', None):
            warn('[yams 0.37.0] meta is deprecated',
                 DeprecationWarning, stacklevel=3)
        try:
            _check_kwargs(kwargs, _REL_PROPERTIES())
        except BadSchemaDefinition as bad:
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


class AbstractTypedAttribute(SubjectRelation):
    """AbstractTypedAttribute is not directly instantiable

    subclasses must provide a <etype> attribute to be instantiable
    """
    def __init__(self, metadata=None, **kwargs):
        # Store metadata
        if metadata is None:
            metadata = {}
        self.metadata = metadata
        # transform "required" into "cardinality"
        required = kwargs.pop('required', False)
        if required:
            cardinality = '11'
        else:
            cardinality = '?1'
        kwargs['cardinality'] = cardinality
        # transform maxsize into SizeConstraint
        maxsize = kwargs.pop('maxsize', None)
        if maxsize is not None:
            _add_constraint(kwargs, SizeConstraint(max=maxsize))
        # formula
        self.formula = kwargs.pop('formula', MARKER)
        # transform vocabulary into StaticVocabularyConstraint
        vocabulary = kwargs.pop('vocabulary', None)
        if vocabulary is not None:
            self.set_vocabulary(vocabulary, kwargs)
        # transform unique into UniqueConstraint
        unique = kwargs.pop('unique', None)
        if unique:
            _add_constraint(kwargs, UniqueConstraint())
        # use the etype attribute provided by subclasses
        super(AbstractTypedAttribute, self).__init__(self.etype, **kwargs)
        # reassign creation rank
        #
        # Main attribute are marked as created before it's metadata.
        # order in meta data is preserved.
        if self.metadata:
            meta = sorted(metadata.values(), key= lambda x: x.creation_rank)
            if meta[0].creation_rank < self.creation_rank:
                m_iter = iter(meta)
                previous = self
                for next in meta:
                    if previous.creation_rank < next.creation_rank:
                        break
                    previous.creation_rank, next.creation_rank = next.creation_rank, previous.creation_rank
                    next = previous

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


def make_type(etype):
    """create a python class for a Yams base type.

    Notice it is now possible to create a specific type with user-defined
    behaviour, e.g.:

        Geometry = make_type('Geometry') # (c.f. postgis)

    will allow the use of:

        Geometry(geom_type='POINT')

    in a Yams schema, provided in this example that `geom_type` is specified to
    the :func:`yams.register_base_type` function which should be called prior to
    make_type.
    """
    assert etype in BASE_TYPES
    return type(etype, (AbstractTypedAttribute,), {'etype' : etype})


# build a specific class for each base type
String = make_type('String')
Password = make_type('Password')
Bytes = make_type('Bytes')
Int = make_type('Int')
BigInt = make_type('BigInt')
Float = make_type('Float')
Boolean = make_type('Boolean')
Decimal = make_type('Decimal')
Time = make_type('Time')
Date = make_type('Date')
Datetime = make_type('Datetime')
TZTime = make_type('TZTime')
TZDatetime = make_type('TZDatetime')
Interval = make_type('Interval')


# provides a RichString factory for convenience
def RichString(default_format='text/plain', format_constraints=None, **kwargs):
    """RichString is a convenience attribute type for attribute containing text
    in a format that should be specified in another attribute.

    The following declaration::

      class Card(EntityType):
          content = RichString(fulltextindexed=True, default_format='text/rest')

    is equivalent to::

      class Card(EntityType):
          content_format = String(internationalizable=True,
                                  default='text/rest', constraints=[FORMAT_CONSTRAINT])
          content  = String(fulltextindexed=True)
    """
    format_args = {'default': default_format,
                   'maxsize': 50}
    if format_constraints is None:
        format_args['constraints'] = [FORMAT_CONSTRAINT]
    else:
        format_args['constraints'] = format_constraints
    meta = {'format':String(internationalizable=True, **format_args)}
    return String(metadata=meta, **kwargs)


# other schema definition classes ##############################################

class metadefinition(autopackage):
    """Metaclass that builds the __relations__ attribute of EntityType's
    subclasses.
    """
    stacklevel = 3
    def __new__(mcs, name, bases, classdict):
        ### Move (any) relation from the class dict to __relations__ attribute
        rels = classdict.setdefault('__relations__', [])
        relations = dict((rdef.name, rdef) for rdef in rels)
        for rname, rdef in list(classdict.items()):
            if isinstance(rdef, ObjectRelation):
                # relation's name **must** be removed from class namespace
                # to avoid conflicts with instance's potential attributes
                del classdict[rname]
                relations[rname] = rdef
        ### handle logical inheritance
        if '__specializes_schema__' in classdict:
            specialized = bases[0]
            classdict['__specializes__'] = specialized.__name__
            if '__specialized_by__' not in specialized.__dict__:
                specialized.__specialized_by__ = []
            specialized.__specialized_by__.append(name)
        ### Initialize processed class
        defclass = super(metadefinition, mcs).__new__(mcs, name, bases, classdict)
        for rname, rdef in relations.items():
            _add_relation(defclass.__relations__, rdef, rname)
        ### take base classes'relations into account
        for base in bases:
            for rdef in getattr(base, '__relations__', ()):
                if not rdef.name in relations or not relations[rdef.name].override:
                    if isinstance(rdef, RelationDefinition):
                        rdef = copy(rdef)
                        if rdef.subject == base.__name__:
                            rdef.subject = name
                        if rdef.object == base.__name__:
                            rdef.object = name
                    rels.append(rdef)
                else:
                    relations[rdef.name].creation_rank = rdef.creation_rank
        ### sort relations by creation rank
        defclass.__relations__ = sorted(rels, key=lambda r: r.creation_rank)
        return defclass


@add_metaclass(metadefinition)
class EntityType(Definition):
    #::FIXME reader magic forbids to define a docstring...
    #: an entity has attributes and can be linked to other entities by
    #: relations. Both entity attributes and relationships are defined by
    #: class attributes.
    #:
    #: kwargs keys must have values in ETYPE_PROPERTIES
    #:
    #: Example:
    #:
    #: >>> class Project(EntityType):
    #: ...     name = String()
    #: >>>
    #:
    #: After instanciation, EntityType can we altered with dedicated class methods:
    #:
    #: .. currentmodule:: yams.buildobjs
    #:
    #:  .. automethod:: EntityType.extend
    #:  .. automethod:: EntityType.add_relation
    #:  .. automethod:: EntityType.insert_relation_after
    #:  .. automethod:: EntityType.remove_relation
    #:  .. automethod:: EntityType.get_relation
    #:  .. automethod:: EntityType.get_relations

    __permissions__ = DEFAULT_ETYPEPERMS

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
        rdefprops = _RDEF_PROPERTIES()
        for relation in cls.__relations__:
            if isinstance(relation, SubjectRelation):
                rdef = RelationDefinition(subject=name, name=relation.name,
                                          object=relation.etype, order=order,
                                          package=relation.package)
                _copy_attributes(relation, rdef, rdefprops)
            elif isinstance(relation, ObjectRelation):
                rdef = RelationDefinition(subject=relation.etype,
                                          name=relation.name,
                                          object=name, order=order,
                                          package=relation.package)
                _copy_attributes(relation, rdef, rdefprops)
            elif isinstance(relation, RelationDefinition):
                rdef = relation
            else:
                raise BadSchemaDefinition('dunno how to handle %s' % relation)
            order += 1
            rdef._add_relations(defined, schema)

    # methods that can be used to extend an existant schema definition ########

    @classmethod
    def extend(cls, othermetadefcls):
        """add all relations of ``othermetadefcls`` to the current class"""
        for rdef in othermetadefcls.__relations__:
            cls.add_relation(rdef)

    @classmethod
    def add_relation(cls, rdef, name=None):
        """Add ``rdef`` relation to the class"""
        if name:
            rdef.name = name
        if cls._ensure_relation_type(rdef):
            _add_relation(cls.__relations__, rdef, name)
            if getattr(rdef, 'metadata', {}) and not rdef in cls._defined:
                for meta_name in rdef.metadata:
                    format_attr_name = '_'.join(((name or rdef.name), meta_name))
                    rdef = next(cls.get_relations(format_attr_name))
                    cls._ensure_relation_type(rdef)
        else:
           _add_relation(cls.__relations__, rdef, name=name)

    @classmethod
    def insert_relation_after(cls, afterrelname, name, rdef):
        """Add ``rdef`` relation to the class right after another"""
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
        """Remove relation from the class"""
        for rdef in cls.get_relations(name):
            cls.__relations__.remove(rdef)

    @classmethod
    def get_relations(cls, name):
        """Iterate over relations definitions that match the ``name`` parameters

        It may iterate multiple definitions when the class is both object and
        sujet of a relation:
        """
        for rdef in cls.__relations__[:]:
            if rdef.name == name:
                yield rdef

    @classmethod
    def get_relation(cls, name):
        """Return relation definitions by name. Fails if there is multiple one.
        """
        relations = tuple(cls.get_relations(name))
        assert len(relations) == 1, "can't use get_relation for relation with multiple definitions"
        return relations[0]


class RelationType(Definition):
    symmetric = MARKER
    inlined = MARKER
    fulltext_container = MARKER
    rule = MARKER

    def __init__(self, name=None, **kwargs):
        """kwargs must have values in RTYPE_PROPERTIES"""
        super(RelationType, self).__init__(name)
        if kwargs.pop('meta', None):
            warn('[yams 0.37] meta is deprecated', DeprecationWarning, stacklevel=2)
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
            allprops = _REL_PROPERTIES() + ('subject', 'object')
            _copy_attributes(defined[name], cls, allprops)
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
            _copy_attributes(cls, rdef, _RDEF_PROPERTIES())
            rdef._add_relations(defined, schema)


class ComputedRelation(RelationType):
    __permissions__ = MARKER

    def __init__(self, name=None, rule=None, **kwargs):
        if rule is not None:
            self.rule = rule
        super(ComputedRelation, self).__init__(name, **kwargs)


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
    formula = MARKER

    def __init__(self, subject=None, name=None, object=None, package=None,
                 **kwargs):
        """kwargs keys must have values in _RDEF_PROPERTIES()"""
        if subject:
            self.subject = subject
        else:
            self.subject = self.__class__.subject
        if object:
            self.object = object
        else:
            self.object = self.__class__.object
        super(RelationDefinition, self).__init__(name)
        global CREATION_RANK
        CREATION_RANK += 1
        self.creation_rank = CREATION_RANK
        if package is not None:
            self.package = package
        elif self.package == '<builtin>':
            self.package = PACKAGE
        if kwargs.pop('meta', None):
            warn('[yams 0.37] meta is deprecated', DeprecationWarning)
        rdefprops = _RDEF_PROPERTIES()
        _check_kwargs(kwargs, rdefprops)
        _copy_attributes(attrdict(**kwargs), self, rdefprops)
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
        _copy_attributes(cls, rtype, RTYPE_PROPERTIES)
        if name in defined:
            _copy_attributes(rtype, defined[name], RTYPE_PROPERTIES)
        else:
            defined[name] = rtype

        # subject and object in defined's keys are only strings not tuples
        if isinstance(cls.subject, tuple):
            subjects = cls.subject
        else:
            subjects = (cls.subject, )
        if isinstance(cls.object, tuple):
            objects = cls.object
        else:
            objects = (cls.object, )
        for sub in subjects:
            for obj in objects:
                key = (sub, name, obj)
                if key in defined:
                    raise BadSchemaDefinition(
                        'duplicated relation definition (%s) %s (%s.%s)'
                        % (defined[key], key, cls.__module__, cls.__name__))
                defined[key] = cls

        # XXX keep this for bw compat
        defined[(cls.subject, name, cls.object)] = cls

    @classmethod
    def expand_relation_definitions(cls, defined, schema):
        """schema building step 2:

        register all relations definition, expanding wildcard if necessary
        """
        assert cls.subject and cls.object, '%s; check the schema (%s, %s)' % (cls, cls.subject, cls.object)
        cls()._add_relations(defined, schema)

    def _add_relations(self, defined, schema):
        name = getattr(self, 'name', self.__class__.__name__)
        rtype = defined[name]
        rdefprops = _RDEF_PROPERTIES()
        # copy relation definition attributes set on the relation type, beside
        # description
        _copy_attributes(rtype, self, set(rdefprops) - set(('description',)))
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
        if rschema.rule:
            raise BadSchemaDefinition(
                'Cannot add relation definition "{0}" because an '
                'homonymous computed relation already exists '
                'with rule "{1}"'.format(rschema.type, rschema.rule))
        if self.__permissions__ is MARKER:
            final = next(iter(_actual_types(schema, self.object))) in BASE_TYPES
            if final:
                if self.formula is not MARKER:
                    permissions = DEFAULT_COMPUTED_ATTRPERMS
                else:
                    permissions = DEFAULT_ATTRPERMS
            else:
                permissions = DEFAULT_RELPERMS
        else:
            permissions = self.__permissions__
        for subj in _actual_types(schema, self.subject):
            for obj in _actual_types(schema, self.object):
                rdef = RelationDefinition(subj, name, obj,
                                          __permissions__=permissions,
                                          package=self.package)
                _copy_attributes(self, rdef, rdefprops)
                schema.add_relation_def(rdef)

def _actual_types(schema, etype):
    if etype == '*':
        return _pow_etypes(schema)
    if isinstance(etype, (list, tuple)):
        return etype
    if not isinstance(etype, string_types):
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
