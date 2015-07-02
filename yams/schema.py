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
"""Classes to define generic Entities/Relations schemas."""

__docformat__ = "restructuredtext en"

import warnings
from copy import deepcopy
from decimal import Decimal
from itertools import chain

from six import text_type, binary_type

from logilab.common import attrdict
from logilab.common.decorators import cached, clear_cache
from logilab.common.interface import implements

import yams
from yams import (BASE_TYPES, MARKER, ValidationError, BadSchemaDefinition,
                  KNOWN_METAATTRIBUTES, convert_default_value, DEFAULT_ATTRPERMS,
                  DEFAULT_COMPUTED_RELPERMS)
from yams.interfaces import (ISchema, IRelationSchema, IEntitySchema,
                             IVocabularyConstraint)
from yams.constraints import BASE_CHECKERS, BASE_CONVERTERS, UniqueConstraint

_ = text_type

def role_name(rtype, role):
    """function to use for qualifying attribute / relation in ValidationError
    errors'dictionnary
    """
    return '%s-%s' % (rtype, role)

def rehash(dictionary):
    """this function manually builds a copy of `dictionary` but forces
    hash values to be recomputed. Note that dict(d) or d.copy() don't
    do that.

    It is used to :
      - circumvent Pyro / (un)pickle problems (hash mode is changed
        during reconstruction)
      - force to recompute keys' hash values. This is needed when a
        schema's type is changed because the schema's hash method is based
        on the type attribute. This problem is illusrated by the pseudo-code
        below :

        >>> topic = EntitySchema(type='Topic')
        >>> d = {topic : 'foo'}
        >>> d[topic]
        'foo'
        >>> d['Topic']
        'foo'
        >>> topic.type = 'folder'
        >>> topic in d
        False
        >>> 'Folder' in d
        False
        >>> 'Folder' in d.keys() # but it can be found "manually"
        True
        >>> d = rehash(d) # explicit rehash()
        >>> 'Folder' in d
        True
    """
    return dict(item for item in dictionary.items())

def _format_properties(props):
    res = [('%s=%s' % item) for item in props.items() if item[1]]
    return ','.join(res)

class ERSchema(object):
    """Base class shared by entity and relation schema."""


    def __init__(self, schema=None, erdef=None):
        """
        Construct an ERSchema instance.

        :Parameters:
         - `schema`: (??)
         - `erdef`: (??)
        """
        if erdef is None:
            return
        self.schema = schema
        self.type = erdef.name
        self.description = erdef.description or ''
        self.package = erdef.package

    def __eq__(self, other):
        return self.type == getattr(other, 'type', other)

    def __ne__(self, other):
        return not (self == other)

    def __lt__(self, other):
        return self.type < getattr(other, 'type', other)

    def __hash__(self):
        try:
            return hash(self.type)
        except AttributeError:
            pass
        return hash(id(self))

    def __deepcopy__(self, memo):
        clone = self.__class__()
        memo[id(self)] = clone
        clone.type = deepcopy(self.type, memo)
        clone.schema = deepcopy(self.schema, memo)
        clone.__dict__ = deepcopy(self.__dict__, memo)
        return clone

    def __str__(self):
        return self.type


class PermissionMixIn(object):
    """mixin class for permissions handling"""
    def action_permissions(self, action):
        return self.permissions[action]

    def set_action_permissions(self, action, permissions):
        assert type(permissions) is tuple, (
            'permissions is expected to be a tuple not %s' % type(permissions))
        assert action in self.ACTIONS, ('%s not in %s' % (action, self.ACTIONS))
        self.permissions[action] = permissions

    def check_permission_definitions(self):
        """check permissions are correctly defined"""
        # already initialized, check everything is fine
        for action, groups in self.permissions.items():
            assert action in self.ACTIONS, \
                'unknown action %s for %s' % (action, self)
            assert isinstance(groups, tuple), \
                   ('permission for action %s of %s isn\'t a tuple as '
                    'expected' % (action, self))
        if self.final:
            self.advertise_new_add_permission()
        for action in self.ACTIONS:
            assert action in self.permissions, \
                   'missing expected permissions for action %s for %s' % (action, self)


# Schema objects definition ###################################################


class EntitySchema(PermissionMixIn, ERSchema):
    """An entity has a type, a set of subject and or object relations
    the entity schema defines the possible relations for a given type and some
    constraints on those relations.
    """
    __implements__ = IEntitySchema

    ACTIONS = ('read', 'add', 'update', 'delete')
    field_checkers = BASE_CHECKERS
    field_converters = BASE_CONVERTERS

    # XXX set default values for those attributes on the class level since
    # they may be missing from schemas obtained by pyro
    _specialized_type = None
    _specialized_by = []

    def __init__(self, schema=None, rdef=None, *args, **kwargs):
        super(EntitySchema, self).__init__(schema, rdef, *args, **kwargs)
        if rdef is not None:
            # quick access to bounded relation schemas
            self.subjrels = {}
            self.objrels = {}
            self._specialized_type = rdef.specialized_type
            self._specialized_by = rdef.specialized_by
            self.final = self.type in BASE_TYPES
            self.permissions = rdef.__permissions__.copy()
            self._unique_together = getattr(rdef, '__unique_together__', [])
        else: # this happens during deep copy (cf. ERSchema.__deepcopy__)
            self._specialized_type = None
            self._specialized_by = []

    def check_unique_together(self):
        errors = []
        for unique_together in self._unique_together:
            for name in unique_together:
                try:
                    rschema = self.rdef(name, takefirst=True)
                except KeyError:
                    errors.append('no such attribute or relation %s' % name)
                else:
                    if not (rschema.final or rschema.rtype.inlined):
                        errors.append('%s is not an attribute or an inlined '
                                      'relation' % name)
        if errors:
            msg = 'invalid __unique_together__ specification for %s: %s' % (self, ', '.join(errors))
            raise BadSchemaDefinition(msg)

    def __repr__(self):
        return '<%s %s - %s>' % (self.type,
                                 [rs.type for rs in self.subject_relations()],
                                 [rs.type for rs in self.object_relations()])

    def _rehash(self):
        self.subjrels = rehash(self.subjrels)
        self.objrels = rehash(self.objrels)

    def advertise_new_add_permission(self):
        pass


    # schema building methods #################################################

    def add_subject_relation(self, rschema):
        """register the relation schema as possible subject relation"""
        self.subjrels[rschema] = rschema
        clear_cache(self, 'ordered_relations')
        clear_cache(self, 'meta_attributes')

    def add_object_relation(self, rschema):
        """register the relation schema as possible object relation"""
        self.objrels[rschema] = rschema

    def del_subject_relation(self, rtype):
        try:
            del self.subjrels[rtype]
            clear_cache(self, 'ordered_relations')
            clear_cache(self, 'meta_attributes')
        except KeyError:
            pass

    def del_object_relation(self, rtype):
        try:
            del self.objrels[rtype]
        except KeyError:
            pass

    # IEntitySchema interface #################################################

    ## navigation ######################

    def specializes(self):
        if self._specialized_type:
            return self.schema.eschema(self._specialized_type)
        return None

    def ancestors(self):
        specializes = self.specializes()
        ancestors = []
        while specializes:
            ancestors.append(specializes)
            specializes = specializes.specializes()
        return ancestors

    def specialized_by(self, recursive=True):
        eschema = self.schema.eschema
        subschemas = [eschema(etype) for etype in self._specialized_by]
        if recursive:
            for subschema in subschemas[:]:
                subschemas.extend(subschema.specialized_by(recursive=True))
        return subschemas

    def has_relation(self, rtype, role):
        if role == 'subject':
            return rtype in self.subjrels
        return rtype in self.objrels

    def subject_relations(self):
        """return a list of relations that may have this type of entity as
        subject
        """
        return list(self.subjrels.values())

    def object_relations(self):
        """return a list of relations that may have this type of entity as
        object
        """
        return list(self.objrels.values())

    def rdef(self, rtype, role='subject', targettype=None, takefirst=False):
        """return a relation definition schema for a relation of this entity type

        Notice that when targettype is not specified and the relation may lead
        to different entity types (ambiguous relation), one of them is picked
        randomly. If also takefirst is False, a warning will be emitted.
        """
        rschema = self.schema.rschema(rtype)
        if targettype is None:
            if role == 'subject':
                types = rschema.objects(self)
            else:
                types = rschema.subjects(self)
            if len(types) != 1 and not takefirst:
                warnings.warn('[yams 0.38] no targettype specified and there are several '
                              'relation definitions for rtype %s: %s. Yet you get the first '
                              'rdef.' % (rtype, [eschema.type for eschema in types]),
                              Warning, stacklevel=2)
            targettype = types[0]
        return rschema.role_rdef(self, targettype, role)

    @cached
    def ordered_relations(self):
        """return subject relations in an ordered way"""
        return sorted(self.subjrels.values(),
                      key=lambda x: x.rdef(self, x.objects(self)[0]).order)

    def relation_definitions(self, includefinal=False):
        """return an iterator on relation definitions

        if includefinal is false, only non attribute relation are returned

        a relation definition is a 3-uple :
        * schema of the (non final) relation
        * schemas of the possible destination entity types
        * a string telling if this is a 'subject' or 'object' relation
        """
        for rschema in self.ordered_relations():
            if includefinal or not rschema.final:
                yield rschema, rschema.objects(self), 'subject'
        for rschema in self.object_relations():
            yield rschema, rschema.subjects(self), 'object'

    def destination(self, rtype):
        """return the type or schema of entities related by the given subject relation

        `rtype` is expected to be a non ambiguous relation
        """
        rschema = self.subjrels[rtype]
        objtypes = rschema.objects(self.type)
        assert len(objtypes) == 1, (self.type, str(rtype),
                                    [str(ot) for ot in objtypes])
        # XXX return a RelationDefinitionSchema
        return objtypes[0]

    # attributes description ###########

    def attribute_definitions(self):
        """return an iterator on attribute definitions

        attribute relations are a subset of subject relations where the
        object's type is a final entity

        an attribute definition is a 2-uple :
        * schema of the (final) relation
        * schema of the destination entity type
        """
        for rschema in self.ordered_relations():
            if not rschema.final:
                continue
            # XXX return a RelationDefinitionSchema
            yield rschema, rschema.objects(self)[0]

    def main_attribute(self):
        """convenience method that returns the *main* (i.e. the first non meta)
        attribute defined in the entity schema
        """
        for rschema, _ in self.attribute_definitions():
            if not self.is_metadata(rschema):
                # XXX return a RelationDefinitionSchema
                return rschema

    def defaults(self):
        """return an iterator on (attribute name, default value)"""
        for rschema in self.subject_relations():
            if rschema.final:
                value = self.default(rschema)
                if value is not None:
                    # XXX return a RelationDefinitionSchema
                    yield rschema, value

    def default(self, rtype):
        """return the default value of a subject relation"""
        rdef = self.rdef(rtype, takefirst=True)
        default =  rdef.default
        if callable(default):
            default = default()
        if default is MARKER:
            default = None
        elif default is not None:
            return convert_default_value(rdef, default)
        return default

    def has_unique_values(self, rtype):
        """convenience method to check presence of the UniqueConstraint on a
        relation
        """
        return bool(self.rdef(rtype).constraint_by_class(UniqueConstraint))

    ## metadata attributes #############

    @cached
    def meta_attributes(self):
        """return a dictionnary defining meta-attributes:
        * key is an attribute schema
        * value is a 2-uple (metadata name, described attribute name)

        a metadata attribute is expected to be named using the following scheme:

          <described attribute name>_<metadata name>

        for instance content_format is the format metadata of the content
        attribute (if it exists).
        """
        metaattrs = {}
        for rschema, _ in self.attribute_definitions():
            try:
                attr, meta = rschema.type.rsplit('_', -1)
            except ValueError:
                continue
            if meta in KNOWN_METAATTRIBUTES and attr in self.subjrels:
                metaattrs[rschema] = (meta, attr)
        return metaattrs

    def has_metadata(self, attr, metadata):
        """return metadata's relation schema if this entity has the given
        `metadata` field for the given `attr` attribute
        """
        return self.subjrels.get('%s_%s' % (attr, metadata))

    def is_metadata(self, attr):
        """return a metadata for an attribute (None if unspecified)"""
        try:
            attr, metadata = str(attr).rsplit('_', 1)
        except ValueError:
            return None
        if metadata in KNOWN_METAATTRIBUTES and attr in self.subjrels:
            return (attr, metadata)
        return None

    # full text indexation control #####

    def indexable_attributes(self):
        """return the relation schema of attribtues to index"""
        for rschema in self.subject_relations():
            if rschema.final:
                try:
                    if self.rdef(rschema).fulltextindexed:
                        yield rschema
                except AttributeError:
                    # fulltextindexed is only available on String / Bytes
                    continue

    def fulltext_relations(self):
        """return the (name, role) of relations to index"""
        for rschema in self.subject_relations():
            if not rschema.final and rschema.fulltext_container == 'subject':
                yield rschema, 'subject'
        for rschema in self.object_relations():
            if rschema.fulltext_container == 'object':
                yield rschema, 'object'

    def fulltext_containers(self):
        """return relations whose extremity points to an entity that should
        contains the full text index content of entities of this type
        """
        for rschema in self.subject_relations():
            if rschema.fulltext_container == 'object':
                yield rschema, 'object'
        for rschema in self.object_relations():
            if rschema.fulltext_container == 'subject':
                yield rschema, 'subject'

    ## resource accessors ##############

    def is_subobject(self, strict=False, skiprels=()):
        """return True if this entity type is contained by another. If strict,
        return True if this entity type *must* be contained by another.
        """
        for rschema in self.object_relations():
            if (rschema, 'object') in skiprels:
                continue
            rdef = self.rdef(rschema, 'object', takefirst=True)
            if rdef.composite == 'subject':
                if not strict or rdef.cardinality[1] in '1+':
                    return True
        for rschema in self.subject_relations():
            if (rschema, 'subject') in skiprels:
                continue
            if rschema.final:
                continue
            rdef = self.rdef(rschema, 'subject', takefirst=True)
            if rdef.composite == 'object':
                if not strict or rdef.cardinality[0] in '1+':
                    return True
        return False

    ## validation ######################

    def check(self, entity, creation=False, _=None, relations=None):
        """check the entity and raises an ValidationError exception if it
        contains some invalid fields (ie some constraints failed)
        """
        if _ is not None:
            warnings.warn('[yams 0.36] _ argument is deprecated, remove it',
                          DeprecationWarning, stacklevel=2)
        _ = text_type
        errors = {}
        msgargs = {}
        i18nvalues = []
        relations = relations or self.subject_relations()
        for rschema in relations:
            if not rschema.final:
                continue
            aschema = self.destination(rschema)
            qname = role_name(rschema, 'subject')
            rdef = rschema.rdef(self, aschema)
            # don't care about rhs cardinality, always '*' (if it make senses)
            card = rdef.cardinality[0]
            assert card in '?1'
            required = card == '1'
            # check value according to their type
            try:
                value = entity[rschema]
            except KeyError:
                if creation and required:
                    # missing required attribute with no default on creation
                    # is not autorized
                    errors[qname] = _('required attribute')
                # on edition, missing attribute is considered as no changes
                continue
            # skip other constraint if value is None and None is allowed
            if value is None:
                if required:
                    errors[qname] = _('required attribute')
                continue
            rtype = rschema.type
            if not aschema.check_value(value):
                errors[qname] = _('incorrect value (%(KEY-value)r) for type "%(KEY-type)s"')
                msgargs[qname+'-value'] = value
                msgargs[qname+'-type'] = aschema.type
                i18nvalues.append(qname+'-type')
                if isinstance(value, binary_type) and aschema == 'String':
                    errors[qname] += '; you might want to try unicode'
                continue
            # ensure value has the correct python type
            nvalue = aschema.convert_value(value)
            if nvalue != value:
                # don't change what's has not changed, who knows what's behind
                # this <entity> thing
                entity[rschema] = value = nvalue
            # check arbitrary constraints
            for constraint in rdef.constraints:
                if not constraint.check(entity, rschema, value):
                    msg, args = constraint.failed_message(qname, value, entity)
                    errors[qname] = msg
                    msgargs.update(args)
                    break
        if errors:
            raise ValidationError(entity, errors, msgargs, i18nvalues)

    def check_value(self, value):
        """check the value of a final entity (ie a const value)"""
        return self.field_checkers[self](self, value)

    def convert_value(self, value):
        """check the value of a final entity (ie a const value)"""
        try:
            return self.field_converters[self](value)
        except KeyError:
            return value

    def vocabulary(self, rtype):
        """backward compat return the vocabulary of a subject relation
        """
        cstr = self.rdef(rtype).constraint_by_interface(IVocabularyConstraint)
        if cstr is None:
            raise AssertionError('field %s of entity %s has no vocabulary' %
                                 (rtype, self))
        return cstr.vocabulary()


class RelationDefinitionSchema(PermissionMixIn):
    """a relation definition is fully caracterized relation, eg

         <subject type> <relation type> <object type>
    """

    _RPROPERTIES = {'cardinality': None,
                    'constraints': (),
                    'order': 9999,
                    'description': '',
                    'infered': False,
                    'permissions': None}
    _NONFINAL_RPROPERTIES = {'composite': None}
    _FINAL_RPROPERTIES = {'default': None,
                          'uid': False,
                          'indexed': False,
                          'formula': None,
                          }
    # Use a TYPE_PROPERTIES dictionnary to store type-dependant parameters.
    BASE_TYPE_PROPERTIES = {'String': {'fulltextindexed': False,
                                       'internationalizable': False},
                            'Bytes': {'fulltextindexed': False}}

    @classmethod
    def ALL_PROPERTIES(cls):
        return set(chain(cls._RPROPERTIES,
                         cls._NONFINAL_RPROPERTIES,
                         cls._FINAL_RPROPERTIES,
                         *cls.BASE_TYPE_PROPERTIES.values()))

    def __init__(self, subject, rtype, object, package, values=None):
        if values is not None:
            self.update(values)
        self.subject = subject
        self.rtype = rtype
        self.object = object
        self.package = package

    @property
    def ACTIONS(self):
        if self.rtype.final:
            return ('read', 'add', 'update')
        else:
            return ('read', 'add', 'delete')

    def update(self, values):
        # XXX check we're copying existent properties
        self.__dict__.update(values)

    def __str__(self):
        if self.object.final:
            return 'attribute %s.%s[%s]' % (
            self.subject, self.rtype, self.object)
        return 'relation %s %s %s' % (
            self.subject, self.rtype, self.object)

    def __repr__(self):
        return '<%s at @%#x>' % (self, id(self))

    def as_triple(self):
        return (self.subject, self.rtype, self.object)

    def advertise_new_add_permission(self):
        """handle backward compatibility with pre-add permissions

        * if the update permission was () [empty tuple], use the
          default attribute permissions for `add`

        * else copy the `update` rule for `add`
        """
        if 'add' not in self.permissions:
            if self.permissions['update'] == ():
                defaultaddperms = DEFAULT_ATTRPERMS['add']
            else:
                defaultaddperms = self.permissions['update']
            self.permissions['add'] = defaultaddperms
            warnings.warn('[yams 0.39] %s: new "add" permissions on attribute '
                          'set to %s by default, but you must make it explicit' %
                          (self, defaultaddperms), DeprecationWarning)


    @classmethod
    def rproperty_defs(cls, desttype):
        """return a dictionary mapping property name to its definition for each
        allowable properties when the relation has `desttype` as target entity's
        type
        """
        propdefs = cls._RPROPERTIES.copy()
        if desttype not in BASE_TYPES:
            propdefs.update(cls._NONFINAL_RPROPERTIES)
        else:
            propdefs.update(cls._FINAL_RPROPERTIES)
            propdefs.update(cls.BASE_TYPE_PROPERTIES.get(desttype, {}))
        return propdefs

    def rproperties(self):
        """same as .rproperty_defs class method, but for instances (hence
        destination is known to be self.object).
        """
        return self.rproperty_defs(self.object)

    def get(self, key, default=None):
        return getattr(self, key, default)

    @property
    def final(self):
        return self.rtype.final

    def dump(self, subject, object):
        return self.__class__(subject, self.rtype, object,
                                        self.package,
                                        self.__dict__)

    def role_cardinality(self, role):
        return self.cardinality[role == 'object']

    def constraint_by_type(self, cstrtype):
        for cstr in self.constraints:
            if cstr.type() == cstrtype:
                return cstr
        return None

    def constraint_by_class(self, cls):
        for cstr in self.constraints:
            if isinstance(cstr, cls):
                return cstr
        return None

    def constraint_by_interface(self, iface):
        for cstr in self.constraints:
            if implements(cstr, iface):
                return cstr
        return None

    def check_permission_definitions(self):
        """check permissions are correctly defined"""
        super(RelationDefinitionSchema, self).check_permission_definitions()
        if (self.final and self.formula and
                (self.permissions['add'] or self.permissions['update'])):
            raise BadSchemaDefinition(
                'Cannot set add/update permissions on computed %s' % self)



class RelationSchema(ERSchema):
    """A relation is a named and oriented link between two entities.
    A relation schema defines the possible types of both extremities.

    Cardinality between the two given entity's type is defined
    as a 2 characters string where each character is one of:
     - 1 <-> 1..1 <-> one and only one
     - ? <-> 0..1 <-> zero or one
     - + <-> 1..n <-> one or more
     - * <-> 0..n <-> zero or more
    """

    __implements__ = IRelationSchema
    symmetric = False
    inlined = False
    fulltext_container = None
    rule = None
    # if this relation is an attribute relation
    final = False
    permissions = None # only when rule is not None, for later propagation to
                       # computed relation definitions
    rdef_class = RelationDefinitionSchema

    def __init__(self, schema=None, rdef=None, **kwargs):
        if rdef is not None:
            if rdef.rule:
                self.init_computed_relation(rdef)
            else:
                self.init_relation(rdef)
            # mapping to subject/object with schema as key
            self._subj_schemas = {}
            self._obj_schemas = {}
            # relation properties
            self.rdefs = {}
        super(RelationSchema, self).__init__(schema, rdef, **kwargs)

    def init_relation(self, rdef):
        if rdef.rule is not MARKER:
            raise BadSchemaDefinition("Relation has no rule attribute")
        # if this relation is symmetric/inlined
        self.symmetric = bool(rdef.symmetric)
        self.inlined = bool(rdef.inlined)
        # if full text content of subject/object entity should be added
        # to other side entity (the container)
        self.fulltext_container = rdef.fulltext_container or None

    def init_computed_relation(self, rdef):
        """computed relation are specific relation with only a rule attribute.

        Reponsibility to infer associated relation definitions is left to client
        code defining what's in rule (eg rql snippet in cubicweb).
        """
        for attr in ('inlined', 'symmetric', 'fulltext_container'):
            if getattr(rdef, attr, MARKER) is not MARKER:
                raise BadSchemaDefinition("Computed relation has no %s attribute" % attr)
        if rdef.__permissions__ is MARKER:
            permissions = DEFAULT_COMPUTED_RELPERMS
        else:
            permissions = rdef.__permissions__
        self.rule = rdef.rule
        self.permissions = permissions

    def __repr__(self):
        return '<%s [%s]>' % (self.type,
                              '; '.join('%s,%s' % (s.type, o.type)
                                        for (s, o), props in self.rdefs.items()))

    def _rehash(self):
        self._subj_schemas = rehash(self._subj_schemas)
        self._obj_schemas = rehash(self._obj_schemas)
        self.rdefs = rehash(self.rdefs)

    # schema building methods #################################################

    def update(self, subjschema, objschema, rdef):
        """Allow this relation between the two given types schema"""
        if subjschema.final:
            msg = 'type %s can\'t be used as subject in a relation' % subjschema
            raise BadSchemaDefinition(msg)
        # check final consistency:
        # * a final relation only points to final entity types
        # * a non final relation only points to non final entity types
        final = objschema.final
        for eschema in self.objects():
            if eschema is objschema:
                continue
            if final != eschema.final:
                if final:
                    feschema, nfeschema = subjschema, self.subjects()[0]
                    frschema, nfrschema = objschema, eschema
                else:
                    feschema, nfeschema = self.subjects()[0], subjschema
                    frschema, nfrschema = eschema, objschema
                msg = ("ambiguous relation: '%(feschema)s.%(rtype)s' is final (%(frschema)s) "
                       "but not '%(nfeschema)s.%(rtype)s' (%(nfrschema)s)")
                msg %= {'rtype': self.type,
                        'feschema': feschema, 'frschema': frschema,
                        'nfeschema': subjschema, 'nfrschema': nfrschema}
                raise BadSchemaDefinition(msg)
        constraints = getattr(rdef, 'constraints', None)
        if constraints:
            for cstr in constraints:
                cstr.check_consistency(subjschema, objschema, rdef)
        if (subjschema, objschema) in self.rdefs and self.symmetric:
            return
        # update our internal struct
        if final:
            assert not self.symmetric, 'no sense on final relation'
            assert not self.inlined, 'no sense on final relation'
            assert not self.fulltext_container, 'no sense on final relation'
        self.final = final
        rdefs = self.init_rproperties(subjschema, objschema, rdef)
        self._add_rdef(rdefs)
        return rdefs

    def _add_rdef(self, rdef):
        # update our internal struct
        self.rdefs[(rdef.subject, rdef.object)] = rdef
        self._update(rdef.subject, rdef.object)
        if self.symmetric:
            self._update(rdef.object, rdef.subject)
            if rdef.object != rdef.subject:
                self.rdefs[(rdef.object, rdef.subject)] = rdef
        if self.inlined and rdef.cardinality[0] in '*+':
            raise BadSchemaDefinition(
                'inlined relation %s can\'t have multiple cardinality for its '
                'subject' % rdef)
        # update entity types schema
        rdef.subject.add_subject_relation(self)
        if self.symmetric:
            rdef.object.add_subject_relation(self)
        else:
            rdef.object.add_object_relation(self)

    def _update(self, subjectschema, objectschema):
        objtypes = self._subj_schemas.setdefault(subjectschema, [])
        if not objectschema in objtypes:
            objtypes.append(objectschema)
        subjtypes = self._obj_schemas.setdefault(objectschema, [])
        if not subjectschema in subjtypes:
            subjtypes.append(subjectschema)

    def del_relation_def(self, subjschema, objschema, _recursing=False):
        try:
            self._subj_schemas[subjschema].remove(objschema)
            if len(self._subj_schemas[subjschema]) == 0:
                del self._subj_schemas[subjschema]
                subjschema.del_subject_relation(self)
        except (ValueError, KeyError):
            pass
        try:
            self._obj_schemas[objschema].remove(subjschema)
            if len(self._obj_schemas[objschema]) == 0:
                del self._obj_schemas[objschema]
                objschema.del_object_relation(self)
        except (ValueError, KeyError):
            pass
        try:
            del self.rdefs[(subjschema, objschema)]
        except KeyError:
            pass
        try:
            if self.symmetric and subjschema != objschema and not _recursing:
                self.del_relation_def(objschema, subjschema, True)
        except KeyError:
            pass
        if not self._obj_schemas or not self._subj_schemas:
            assert not self._obj_schemas and not self._subj_schemas
            return True
        return False

    # relation definitions properties handling ################################

    # XXX move to RelationDefinitionSchema

    def init_rproperties(self, subject, object, buildrdef):
        key = subject, object
        # raise an error if already defined unless the defined relalation has
        # been infered, in which case we may want to replace it
        if key in self.rdefs and not self.rdefs[key].infered:
            msg = '(%s, %s) already defined for %s' % (subject, object, self)
            raise BadSchemaDefinition(msg)
        self.rdefs[key] = rdef = self.rdef_class(subject, self, object,
                                                 buildrdef.package)
        for prop, default in rdef.rproperties().items():
            rdefval = getattr(buildrdef, prop, MARKER)
            if rdefval is MARKER:
                if prop == 'permissions':
                    rdefval = default = buildrdef.get_permissions(self.final).copy()
                if prop == 'cardinality':
                    default = (object in BASE_TYPES) and '?1' or '**'
            else:
                default = rdefval
            setattr(rdef, prop, default)
        return rdef

    # IRelationSchema interface ###############################################

    def associations(self):
        """return a list of (subject, [objects]) defining between which types
        this relation may exists
        """
        # XXX deprecates in favor of iter_rdefs() ?
        return list(self._subj_schemas.items())

    def subjects(self, etype=None):
        """Return a list of entity schemas which can be subject of this relation.

        If etype is not None, return a list of schemas which can be subject of
        this relation with etype as object.

        :raise `KeyError`: if etype is not a subject entity type.
        """
        if etype is None:
            return tuple(self._subj_schemas)
        try:
            return tuple(self._obj_schemas[etype])
        except KeyError:
            raise KeyError("%s does not have %s as object" % (self, etype))

    def objects(self, etype=None):
        """Return a list of entity schema which can be object of this relation.

        If etype is not None, return a list of schemas which can be object of
        this relation with etype as subject.

        :raise `KeyError`: if etype is not an object entity type.
        """
        if etype is None:
            return tuple(self._obj_schemas)
        try:
            return tuple(self._subj_schemas[etype])
        except KeyError:
            raise KeyError("%s does not have %s as subject" % (self, etype))

    def targets(self, etype=None, role='subject'):
        """return possible target types with <etype> as <x>"""
        if role == 'subject':
            return self.objects(etype)
        return self.subjects(etype)

    def rdef(self, subject, object):
        """return the properties dictionary of a relation"""
        try:
            return self.rdefs[(subject, object)]
        except KeyError:
            raise KeyError('%s %s %s' % (subject, self, object))

    def role_rdef(self, etype, ttype, role):
        if role == 'subject':
            return self.rdefs[(etype, ttype)]
        return self.rdefs[(ttype, etype)]

    def check_permission_definitions(self):
        """check permissions are correctly defined"""
        for rdef in self.rdefs.values():
            rdef.check_permission_definitions()
        if self.rule and (self.permissions.get('add')
                          or self.permissions.get('delete')):
            raise BadSchemaDefinition(
                'Cannot set add/delete permissions on computed relation %s'
                % self.type)


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
    # relation that should not be infered according to entity type inheritance
    no_specialization_inference = ()

    def __init__(self, name, construction_mode='strict'):
        super(Schema, self).__init__()
        self.name = name
        # with construction_mode != 'strict', no error when trying to add a
        # relation using an undefined entity type, simply log the error
        self.construction_mode = construction_mode
        self._entities = {}
        self._relations = {}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._rehash()

    def _rehash(self):
        """rehash schema's internal structures"""
        for eschema in self._entities.values():
            eschema._rehash()
        for rschema in self._relations.values():
            rschema._rehash()

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

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
        """Add an entity schema definition for an entity's type.

        :type edef: str
        :param edef: the name of the entity type to define

        :raise `BadSchemaDefinition`: if the entity type is already defined
        :rtype: `EntitySchema`
        :return: the newly created entity schema instance
        """
        etype = edef.name
        if etype in self._entities:
            msg = "entity type %s is already defined" % etype
            raise BadSchemaDefinition(msg)
        eschema = self.entity_class(self, edef)
        self._entities[etype] = eschema
        return eschema

    def rename_entity_type(self, oldname, newname):
        """renames an entity type and update internal structures accordingly
        """
        eschema = self._entities.pop(oldname)
        eschema.type = newname
        self._entities[newname] = eschema
        # rebuild internal structures since eschema's hash value has changed
        self._rehash()

    def add_relation_type(self, rtypedef):
        rtype = rtypedef.name
        if rtype in self._relations:
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
        except KeyError:
            return self._building_error('using unknown relation type in %s',
                                        rdef)
        try:
            subjectschema = self.eschema(rdef.subject)
        except KeyError:
            return self._building_error('using unknown type %r in relation %s',
                                        rdef.subject, rtype)
        try:
            objectschema = self.eschema(rdef.object)
        except KeyError:
            return self._building_error("using unknown type %r in relation %s",
                                        rdef.object, rtype)
        return rschema.update(subjectschema, objectschema, rdef)

    def _building_error(self, msg, *args):
        if self.construction_mode == 'strict':
            raise BadSchemaDefinition(msg % args)
        self.critical(msg, *args)

    def del_relation_def(self, subjtype, rtype, objtype):
        subjschema = self.eschema(subjtype)
        objschema = self.eschema(objtype)
        rschema = self.rschema(rtype)
        if rschema.del_relation_def(subjschema, objschema):
            del self._relations[rtype]

    def del_relation_type(self, rtype):
        # XXX don't iter directly on the dictionary since it may be changed
        # by del_relation_def
        for subjtype, objtype in list(self.rschema(rtype).rdefs):
            self.del_relation_def(subjtype, rtype, objtype)
        if not self.rschema(rtype).rdefs:
            del self._relations[rtype]

    def del_entity_type(self, etype):
        eschema = self._entities[etype]
        for rschema in list(eschema.subjrels.values()):
            for objtype in rschema.objects(etype):
                self.del_relation_def(eschema, rschema, objtype)
        for rschema in list(eschema.objrels.values()):
            for subjtype in rschema.subjects(etype):
                self.del_relation_def(subjtype, rschema, eschema)
        if eschema.specializes():
            eschema.specializes()._specialized_by.remove(eschema)
        if eschema.specialized_by():
            raise Exception("can't remove entity type %s used as parent class by %s" %
                            (eschema, ','.join(str(et) for et in eschema.specialized_by())))
        del self._entities[etype]
        if eschema.final:
            yams.unregister_base_type(etype)

    def infer_specialization_rules(self):
        for rschema in self.relations():
            if rschema in self.no_specialization_inference:
                continue
            for (subject, object), rdef in list(rschema.rdefs.items()):
                subjeschemas = [subject] + subject.specialized_by(recursive=True)
                objeschemas = [object] + object.specialized_by(recursive=True)
                for subjschema in subjeschemas:
                    for objschema in objeschemas:
                        # don't try to add an already defined relation
                        if (subjschema, objschema) in rschema.rdefs:
                            continue
                        thisrdef = rdef.dump(subjschema, objschema)
                        thisrdef.infered = True
                        rschema._add_rdef(thisrdef)

    def remove_infered_definitions(self):
        """remove any infered definitions added by
        `infer_specialization_rules`
        """
        for rschema in self.relations():
            if rschema.final:
                continue
            for (subject, object), rdef in list(rschema.rdefs.items()):
                if rdef.infered:
                    rschema.del_relation_def(subject, object)

    def rebuild_infered_relations(self):
        """remove any infered definitions and rebuild them"""
        self.remove_infered_definitions()
        self.infer_specialization_rules()

    # ISchema interface #######################################################

    def entities(self):
        """return a list of possible entity's type

        :rtype: list
        :return: defined entity's types (str) or schemas (`EntitySchema`)
        """
        return list(self._entities.values())

    def has_entity(self, etype):
        """return true the type is defined in the schema

        :type etype: str
        :param etype: the entity's type

        :rtype: bool
        :return:
          a boolean indicating whether this type is defined in this schema
        """
        return etype in self._entities

    def eschema(self, etype):
        """return the entity's schema for the given type

        :rtype: `EntitySchema`
        :raise `KeyError`: if the type is not defined as an entity
        """
        try:
            return self._entities[etype]
        except KeyError:
            if isinstance(etype, tuple):
                etype = list(etype)
            raise KeyError('No entity named %s in schema' % etype)

    def relations(self):
        """return the list of possible relation'types

        :rtype: list
        :return: defined relation's types (str) or schemas (`RelationSchema`)
        """
        return list(self._relations.values())

    def has_relation(self, rtype):
        """return true the relation is defined in the schema

        :type rtype: str
        :param rtype: the relation's type

        :rtype: bool
        :return:
          a boolean indicating whether this type is defined in this schema
        """
        return rtype in self._relations

    def rschema(self, rtype):
        """return the relation schema for the given type

        :rtype: `RelationSchema`
        """
        try:
            return self._relations[rtype]
        except KeyError:
            raise KeyError('No relation named %s in schema'%rtype)

    def finalize(self):
        """Finalize schema

        Can be used to, e.g., infer relations from inheritance, computed
        relations, etc.
        """
        self.infer_specialization_rules()


import logging
from logilab.common.logging_ext import set_log_methods
LOGGER = logging.getLogger('yams')
set_log_methods(Schema, LOGGER)
