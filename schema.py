"""Classes to define generic Entities/Relations schemas.

:organization: Logilab
:copyright: 2003-2009 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

import warnings
from copy import deepcopy
from decimal import Decimal

from logilab.common.decorators import cached
from logilab.common.compat import sorted
from logilab.common.interface import implements
from logilab.common.deprecation import deprecated_function

from yams import BASE_TYPES, MARKER, ValidationError, BadSchemaDefinition
from yams.interfaces import (ISchema, IRelationSchema, IEntitySchema,
                             IVocabularyConstraint)
from yams.constraints import BASE_CHECKERS, BASE_CONVERTERS, UniqueConstraint


from mx.DateTime import today, now, DateTimeFrom, DateFrom, TimeFrom

def use_py_datetime():
    global DATE_FACTORY_MAP, KEYWORD_MAP

    from datetime import datetime, date, time
    from time import strptime as time_strptime

    try:
        strptime = datetime.strptime
    except AttributeError: # py < 2.5
        def strptime(value, format):
            return datetime(*time_strptime(value, format)[:6])

    def strptime_time(value, format='%H:%M'):
        return time(*time_strptime(value, format)[3:6])

    KEYWORD_MAP = {'Datetime.NOW' : datetime.now,
                   'Datetime.TODAY': datetime.today,
                   'Date.TODAY': date.today}
    DATE_FACTORY_MAP = {
        'Datetime' : lambda x: ':' in x and strptime(x, '%Y/%m/%d %H:%M') or strptime(x, '%Y/%m/%d'),
        'Date' : lambda x : strptime(x, '%Y/%m/%d'),
        'Time' : strptime_time
        }

try:
    from mx.DateTime import today, now, DateTimeFrom, DateFrom, TimeFrom
    KEYWORD_MAP = {'Datetime.NOW' : now,
                   'Datetime.TODAY' : today,
                   'Date.TODAY': today}
    DATE_FACTORY_MAP = {'Datetime' : DateTimeFrom,
                        'Date' : DateFrom,
                        'Time' : TimeFrom}
except ImportError:
    use_py_datetime()

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

    ACTIONS = ()

    def __init__(self, schema=None, erdef=None):
        """
        Construct an ERSchema instance.

        :Parameters:
         - `schema`: (??)
         - `erdef`: (??)
        """
        if erdef is None:
            return
        assert schema
        assert erdef
        self.schema = schema
        self.type = erdef.name
        self.meta = erdef.meta or False
        self.description = erdef.description or ''
        # mapping from action to groups
        try:
            self._groups = erdef.permissions.copy()
        except AttributeError:
            self._groups = {}

    def __cmp__(self, other):
        return cmp(self.type, getattr(other, 'type', other))

    def __hash__(self):
        try:
            if self.schema.__hashmode__ is None:
                return hash(self.type)
        except AttributeError:
            pass
        return hash(id(self))

    def __deepcopy__(self, memo):
        clone = self.__class__()
        memo[id(self)] = clone
        clone.type = deepcopy(self.type, memo)
        clone.schema = deepcopy(self.schema, memo)
        clone.schema.__hashmode__ = None
        clone.__dict__ = deepcopy(self.__dict__, memo)
        return clone

    def __str__(self):
        return self.type

    def set_groups(self, action, groups):
        """set the groups allowed to perform <action> on entities of this type

        :Parameters:
         - `action`: (str) the name of a permission
         - `groups`: (tuple) the groups with the given permission
        """
        assert type(groups) is tuple, ('groups is expected to be a tuple not %s' % type(groups))
        assert action in self.ACTIONS, ('%s not in %s' % (action, self.ACTIONS))
        self._groups[action] = groups

    def get_groups(self, action):
        """return the groups authorized to perform <action> on entities of
        this type

        :type action: str
        :param action: the name of a permission

        :rtype: tuple
        :return: the groups with the given permission
        """
        assert action in self.ACTIONS, ('%s not in %s' % (action, self.ACTIONS))
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
        assert action in self.ACTIONS, ('%s not in %s' % (action, self.ACTIONS))
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
        return user.matching_groups(self.get_groups(action))

    def set_default_groups(self):
        """set default action -> groups mapping"""
        if self._groups:
            # already initialized
            pass
            #assert not self.is_final(), \
            #       'permission for final entities are not considered'
        else:
            self._groups = self.get_default_groups()

    def get_default_groups(self):
        """provide default action -> groups mapping"""
        raise NotImplementedError()

# Schema objects definition ###################################################

KNOWN_METAATTRIBUTES = set(('format', 'encoding'))

class EntitySchema(ERSchema):
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
            self._subj_relations = {}
            self._obj_relations = {}
            self._specialized_type = rdef.specialized_type
            self._specialized_by = rdef.specialized_by
        else:
            self._specialized_type = None
            self._specialized_by = []

    def __repr__(self):
        return '<%s %s - %s>' % (self.type,
                                 [rs.type for rs in self.subject_relations()],
                                 [rs.type for rs in self.object_relations()])

    def _rehash(self):
        self._subj_relations = rehash(self._subj_relations)
        self._obj_relations = rehash(self._obj_relations)

    # schema building methods #################################################

    def add_subject_relation(self, rschema):
        """register the relation schema as possible subject relation"""
        self._subj_relations[rschema] = rschema

    def add_object_relation(self, rschema):
        """register the relation schema as possible object relation"""
        self._obj_relations[rschema] = rschema

    def del_subject_relation(self, rtype):
        try:
            del self._subj_relations[rtype]
        except KeyError:
            pass

    def del_object_relation(self, rtype):
        try:
            del self._obj_relations[rtype]
        except KeyError:
            pass

    def get_default_groups(self):
        """   get default action -> groups mapping  """
        if self.is_final():
            # no permissions needed for final entities, access to them
            # is defined through relations
            return {'read': ('managers', 'users', 'guests',)}
        elif self.meta:
            return {'read': ('managers', 'users', 'guests',),
                            'update': ('managers', 'owners',),
                            'delete': ('managers',),
                            'add': ('managers',)}
        else:
            return {'read': ('managers', 'users', 'guests',),
                            'update': ('managers', 'owners',),
                            'delete': ('managers', 'owners'),
                            'add': ('managers', 'users',)}

    # IEntitySchema interface #################################################

    def is_final(self):
        """return true if the entity is a final entity
        (and so cannot be used as subject of a relation)
        """
        return self.type in BASE_TYPES

    def subjrproperty(self, rschema, prop):
        return rschema.rproperty(self.type, rschema.objects(self.type)[0], prop)
    def objrproperty(self, rschema, prop):
        return rschema.rproperty(rschema.subjects(self.type)[0], self.type, prop)

    def is_subobject(self, strict=False):
        """return True if this entity type is contained by another. If strict,
        return True if this entity type *must* be contained by another.
        """
        for rschema in self.object_relations():
            if self.objrproperty(rschema, 'composite') == 'subject':
                if not strict:
                    return True
                if self.objrproperty(rschema, 'cardinality')[1] in '1+':
                    return True
        for rschema in self.subject_relations():
            if self.subjrproperty(rschema, 'composite') == 'object':
                if not strict:
                    return True
                if self.subjrproperty(rschema, 'cardinality')[0] in '1+':
                    return True
                return True
        return False

    def ordered_relations(self):
        """ return subject relation in an ordered way"""
        result = []
        for rschema in self._subj_relations.values():
            otype = rschema.objects(self)[0]
            result.append((rschema.rproperty(self, otype, 'order'), rschema))
        return [r[1] for r in sorted(result)]

    def subject_relations(self):
        """return a list of relations that may have this type of entity as
        subject
        """
        return self._subj_relations.values()

    def has_subject_relation(self, rtype):
        """if this entity type as a `rtype` subject relation, return its schema
        else return None
        """
        return self._subj_relations.get(rtype)

    def object_relations(self):
        """return a list of relations that may have this type of entity as
        object
        """
        return self._obj_relations.values()

    def has_object_relation(self, rtype):
        """if this entity type as a `rtype` object relation, return its schema
        else return None
        """
        return self._obj_relations.get(rtype)

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
            eschema = rschema.objects(self)[0]
            yield rschema, eschema

    def destination(self, rtype):
        """return the type or schema of entities related by the given relation

        `rtype` must be a subject final relation
        """
        rschema = self.subject_relation(rtype)
        assert rschema.is_final(), (self.type, rtype)
        objtypes = rschema.objects(self.type)
        assert len(objtypes) == 1
        return objtypes[0]

    def rproperty(self, rtype, prop):
        """convenience method to access a property of a subject relation"""
        rschema = self.subject_relation(rtype)
        return rschema.rproperty(self, self.destination(rtype), prop)

    def set_rproperty(self, rtype, prop, value):
        """convenience method to set the value of a property of a subject relation"""
        rschema = self.subject_relation(rtype)
        return rschema.set_rproperty(self, self.destination(rtype), prop, value)

    def rproperties(self, rtype):
        """convenience method to access properties of a subject relation"""
        rschema = self.subject_relation(rtype)
        desttype = rschema.objects(self)[0]
        return rschema.rproperties(self, desttype)

    def relation_definitions(self, includefinal=False):
        """return an iterator on relation definitions

        if includefinal is false, only non attribute relation are returned

        a relation definition is a 3-uple :
        * schema of the (non final) relation
        * schemas of the possible destination entity types
        * a string telling if this is a 'subject' or 'object' relation
        """
        for rschema in self.ordered_relations():
            if includefinal or not rschema.is_final():
                yield rschema, rschema.objects(self), 'subject'
        for rschema in self.object_relations():
            yield rschema, rschema.subjects(self), 'object'

    def has_metadata(self, attr, metadata):
        """return true if this entity's schema has an encoding field for the given
        attribute
        """
        return self.has_subject_relation('%s_%s' % (attr, metadata))

    def is_metadata(self, attr):
        """return a metadata for an attribute (None if unspecified)"""
        try:
            attr, metadata = str(attr).rsplit('_', 1)
        except ValueError:
            return None
        if metadata in KNOWN_METAATTRIBUTES and self.has_subject_relation(attr):
            return (attr, metadata)
        return None

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
            if meta in KNOWN_METAATTRIBUTES and self.has_subject_relation(attr):
                metaattrs[rschema] = (meta, attr)
        return metaattrs

    def main_attribute(self):
        """convenience method that returns the *main* (i.e. the first non meta)
        attribute defined in the entity schema
        """
        for rschema, _ in self.attribute_definitions():
            if not rschema.meta:
                return rschema

    def indexable_attributes(self):
        """return the relation schema of attribtues to index"""
        assert not self.is_final()
        for rschema in self.subject_relations():
            if rschema.is_final():
                if self.rproperty(rschema, 'fulltextindexed'):
                    yield rschema

    def fulltext_relations(self):
        """return the (name, role) of relations to index"""
        assert not self.is_final()
        for rschema in self.subject_relations():
            if not rschema.is_final() and  rschema.fulltext_container == 'subject':
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

    def defaults(self):
        """return an iterator on (attribute name, default value)"""
        assert not self.is_final()
        for rschema in self.subject_relations():
            if rschema.is_final():
                value = self.default(rschema)
                if value is not None:
                    yield rschema, value

    def default(self, rtype):
        """return the default value of a subject relation"""
        default =  self.rproperty(rtype, 'default')
        if callable(default):
            default = default()
        if default is MARKER:
            default = None
        if default is not None:
            attrtype = self.destination(rtype)
            if attrtype == 'Boolean':
                if not isinstance(default, bool):
                    default = default == 'True'
            elif attrtype == 'Int':
                if not isinstance(default, int):
                    default = int(default)
            elif attrtype == 'Float':
                if not isinstance(default, float):
                    default = float(default)
            elif attrtype == 'Decimal':
                if not isinstance(default, Decimal):
                    default = Decimal(default)
            elif attrtype in ('Date', 'Datetime', 'Time'):
                try:
                    default = KEYWORD_MAP['%s.%s' % (attrtype, default.upper())]()
                except KeyError:
                    default = DATE_FACTORY_MAP[attrtype](default)
            else:
                default = unicode(default)
        return default

    def has_unique_values(self, rtype):
        """convenience method to check presence of the UniqueConstraint on a
        relation
        """
        rschema = self.subject_relation(rtype)
        for constraint in self.constraints(rtype):
            if isinstance(constraint, UniqueConstraint):
                return True
        return False

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
                                 (rtype, self))
        return constraint.vocabulary()

    def check(self, entity, creation=False, _=unicode):
        """check the entity and raises an ValidationError exception if it
        contains some invalid fields (ie some constraints failed)
        """
        assert not self.is_final()
        errors = {}
        for rschema in self.subject_relations():
            if not rschema.is_final():
                continue
            aschema = self.destination(rschema)
            # don't care about rhs cardinality, always '*' (if it make senses)
            card = rschema.rproperty(self, aschema, 'cardinality')[0]
            assert card in '?1'
            required = card == '1'
            # check value according to their type
            try:
                value = entity[rschema]
            except KeyError:
                if creation and required:
                    # missing required attribute with no default on creation
                    # is not autorized
                    errors[rschema.type] = _('required attribute')
                # on edition, missing attribute is considered as no changes
                continue
            # skip other constraint if value is None and None is allowed
            if value is None:
                if required:
                    errors[rschema.type] = _('required attribute')
                continue
            if not aschema.check_value(value):
                errors[rschema.type] = _('incorrect value (%(value)s) for type "%(type)s"') % {
                    'value':value, 'type': _(aschema.type)}
                if isinstance(value, str):
                    errors[rschema.type] = '%s; you might want to try unicode'  % errors[rschema.type]
                continue
            # ensure value has the correct python type
            entity[rschema] = value = aschema.convert_value(value)
            # check arbitrary constraints
            for constraint in rschema.rproperty(self, aschema, 'constraints'):
                if not constraint.check(entity, rschema, value):
                    errors[rschema.type] = _('%(cstr)s constraint failed for value %(value)r') % {
                        'cstr': constraint, 'value': value}
        if errors:
            raise ValidationError(entity, errors)

    def check_value(self, value):
        """check the value of a final entity (ie a const value)"""
        assert self.is_final()
        return self.field_checkers[self](self, value)

    def convert_value(self, value):
        """check the value of a final entity (ie a const value)"""
        assert self.is_final()
        try:
            return self.field_converters[self](value)
        except KeyError:
            return value

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

    # bw compat
    subject_relation_schema = subject_relation
    object_relation_schema = object_relation


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
    ACTIONS = ('read', 'add', 'delete')
    _RPROPERTIES = {'cardinality': None,
                    'constraints': (),
                    'order': 9999,
                    'description': '',
                    'infered': False,}
    _NONFINAL_RPROPERTIES = {'composite': None}
    _FINAL_RPROPERTIES = {'default': None,
                          'uid': False,
                          'indexed': False}
    _STRING_RPROPERTIES = {'fulltextindexed': False,
                           'internationalizable': False}
    _BYTES_RPROPERTIES = {'fulltextindexed': False}

    __implements__ = IRelationSchema

    def __init__(self, schema=None, rdef=None, **kwargs):
        if rdef is not None:
            # if this relation is symetric/inlined
            self.symetric = rdef.symetric or False
            self.inlined = rdef.inlined or False
            # if full text content of subject/object entity should be added
            # to other side entity (the container)
            self.fulltext_container = rdef.fulltext_container or None
            # if this relation is an attribute relation
            self.final = False
            # mapping to subject/object with schema as key
            self._subj_schemas = {}
            self._obj_schemas = {}
            # relation properties
            self._rproperties = {}
        super(RelationSchema, self).__init__(schema, rdef, **kwargs)

    def __repr__(self):
        return '<%s [%s]>' % (self.type,
                              '; '.join('%s,%s:%s'%(s.type, o.type, _format_properties(props))
                                        for (s, o), props in self._rproperties.items()))

    def _rehash(self):
        self._subj_schemas = rehash(self._subj_schemas)
        self._obj_schemas = rehash(self._obj_schemas)
        self._rproperties = rehash(self._rproperties)

    # schema building methods #################################################

    def update(self, subjschema, objschema, rdef):
        """Allow this relation between the two given types schema"""
        if subjschema.is_final():
            msg = 'type %s can\'t be used as subject in a relation' % subjschema
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
                    frschema, nfrschema = objschema, eschema
                else:
                    frschema, nfrschema = eschema, objschema
                msg = "ambiguous relation %s: %s is final but not %s" % (
                    self.type, frschema, nfrschema)
                raise BadSchemaDefinition(msg)
        self.final = final
        # update our internal struct
        self._update(subjschema, objschema)
        if self.symetric:
            self._update(objschema, subjschema)
            try:
                self.init_rproperties(subjschema, objschema, rdef)
                if objschema != subjschema:
                    self.init_rproperties(objschema, subjschema, rdef)
            except BadSchemaDefinition:
                # this is authorized for consistency
                pass
        else:
            self.init_rproperties(subjschema, objschema, rdef)
        # update extremities schema
        subjschema.add_subject_relation(self)
        if self.symetric:
            objschema.add_subject_relation(self)
        else:
            objschema.add_object_relation(self)

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
            del self._rproperties[(subjschema, objschema)]
        except KeyError:
            pass
        try:
            if self.symetric and subjschema != objschema and not _recursing:
                self.del_relation_def(objschema, subjschema, True)
        except KeyError:
            pass
        if not self._obj_schemas or not self._subj_schemas:
            assert not self._obj_schemas and not self._subj_schemas
            return True
        return False

    def get_default_groups(self):
        if self.final:
            return {'read': ('managers', 'users', 'guests'),
                    'delete': ('managers', 'users', 'guests'),
                    'add': ('managers', 'users', 'guests')}
        elif self.meta:
            return {'read': ('managers', 'users', 'guests'),
                            'delete': ('managers',),
                            'add': ('managers',)}
        else:
            return {'read': ('managers', 'users', 'guests',),
                            'delete': ('managers', 'users'),
                            'add': ('managers', 'users',)}

    # relation definitions properties handling ################################

    def rproperty_defs(self, desttype):
        """return a dictionary mapping property name to its definition
        for each allowable properties when the relation has `desttype` as
        target entity's type
        """
        propdefs = self._RPROPERTIES.copy()
        if not self.is_final():
            propdefs.update(self._NONFINAL_RPROPERTIES)
        else:
            propdefs.update(self._FINAL_RPROPERTIES)
            if desttype == 'String':
                propdefs.update(self._STRING_RPROPERTIES)
            elif desttype == 'Bytes':
                propdefs.update(self._BYTES_RPROPERTIES)
        return propdefs

    def iter_rdefs(self):
        """return an iterator on (subject, object) of this relation"""
        return self._rproperties.iterkeys()

    rproperty_keys = deprecated_function(iter_rdefs) # XXX bw compat

    def rdefs(self):
        """return a list of (subject, object) of this relation"""
        return self._rproperties.keys()

    def has_rdef(self, subj, obj):
        return (subj, obj) in self._rproperties

    def rproperties(self, subject, object):
        """return the properties dictionary of a relation"""
        try:
            return self._rproperties[(subject, object)]
        except KeyError:
            raise KeyError('%s %s %s' % (subject, self, object))

    def rproperty(self, subject, object, property):
        """return the property for a relation definition"""
        return self.rproperties(subject, object).get(property)

    def set_rproperty(self, subject, object, pname, value):
        """set value for a subject relation specific property"""
        assert pname in self.rproperty_defs(object)
        self._rproperties[(subject, object)][pname] = value

    def init_rproperties(self, subject, object, rdef):
        key = subject, object
        if key in self._rproperties:
            msg = '(%s, %s) already defined for %s' % (subject, object, self)
            raise BadSchemaDefinition(msg)
        self._rproperties[key] = {}
        for prop, default in self.rproperty_defs(key[1]).iteritems():
            rdefval = getattr(rdef, prop, MARKER)
            if rdefval is MARKER:
                if prop == 'cardinality':
                    default = (object in BASE_TYPES) and '?1' or '**'
            else:
                default = rdefval
            self._rproperties[key][prop] = default

    # IRelationSchema interface ###############################################

    def is_final(self):
        """return true if this relation has final object entity's types

        (we enforce that a relation can't point to both final and non final
        entity's type)
        """
        return self.final

    def associations(self):
        """return a list of (subject, [objects]) defining between
        which types this relation may exists
        """
        # XXX deprecates in favor of iter_rdefs() ?
        return self._subj_schemas.items()

    def subjects(self, etype=None):
        """Return a list of entity schemas which can be subject of this relation.

        If etype is not None, return a list of schemas which can be subject of
        this relation with etype as object.

        :raise `KeyError`: if etype is not a subject entity type.
        """
        if etype is None:
            return tuple(self._subj_schemas.keys())
        try:
            return tuple(self._obj_schemas[etype])
        except KeyError:
            raise KeyError("%s don't have %s as object" % (self, etype))

    def objects(self, etype=None):
        """Return a list of entity schema which can be object of this relation.

        If etype is not None, return a list of schemas which can be object of
        this relation with etype as subject.

        :raise `KeyError`: if etype is not an object entity type.
        """
        if etype is None:
            return tuple(self._obj_schemas.keys())
        try:
            return tuple(self._subj_schemas[etype])
        except KeyError:
            raise KeyError("%s don't have %s as subject" % (self, etype))

    def targets(self, etype, role='subject'):
        """return possible target types with <etype> as <x>"""
        assert role in ('subject', 'object')
        if role == 'subject':
            return self.objects(etype)
        return self.subjects(etype)

    def constraint_by_type(self, subjtype, objtype, cstrtype):
        for cstr in self.rproperty(subjtype, objtype, 'constraints'):
            if cstr.type() == cstrtype:
                return cstr
        return None


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
    # __hashmode__ is a evil hack to support schema pickling
    # it should be set to 'pickle' before pickling is done and reset to None
    # once it's done
    __hashmode__ = 'pickle' # None | 'pickle'

    def __init__(self, name, construction_mode='strict'):
        super(Schema, self).__init__()
        self.__hashmode__ = None
        self.name = name
        # with construction_mode != 'strict', no error when trying to add a
        # relation using an undefined entity type, simply log the error
        self.construction_mode = construction_mode
        self._entities = {}
        self._relations = {}

    def __setstate__(self, state):
        self.__dict__.update(state)
        # restore __hashmode__
        self.__hashmode__ = None
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
        assert oldname in self._entities
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
        rschema.update(subjectschema, objectschema, rdef)
        return True

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
        for subjtype, objtype in self.rschema(rtype)._rproperties.keys():
            self.del_relation_def(subjtype, rtype, objtype)
        if not self.rschema(rtype)._rproperties:
            del self._relations[rtype]

    def del_entity_type(self, etype):
        eschema = self._entities[etype]
        for rschema in eschema._subj_relations.values():
            for objtype in rschema.objects(etype):
                self.del_relation_def(eschema, rschema, objtype)
        for rschema in eschema._obj_relations.values():
            for subjtype in rschema.subjects(etype):
                self.del_relation_def(subjtype, rschema, eschema)
        del self._entities[etype]

    def infer_specialization_rules(self):
        # XXX
        class XXXRelationDef:
            infered = True
        for rschema in self.relations():
            if rschema.is_final():
                continue
            for subject, object in rschema.rdefs():
                subjeschemas = [subject] + subject.specialized_by(recursive=True)
                objeschemas = [object] + object.specialized_by(recursive=True)
                for subjschema in subjeschemas:
                    for objschema in objeschemas:
                        subjobj = (subjschema, objschema)
                        # don't try to add an already defined relation
                        if subjobj in rschema.rdefs():
                            continue
                        rschema.update(subjschema, objschema, XXXRelationDef)

    def remove_infered_definitions(self):
        """remove any infered definitions added by
        `infer_specialization_rules`
        """
        for rschema in self.relations():
            if rschema.is_final():
                continue
            for subject, object in rschema.rdefs():
                if rschema.rproperty(subject, object, 'infered'):
                    self.del_relation_def(subject, rschema, object)

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
        return self._entities.values()

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
            raise KeyError('No entity named %s in schema' % etype)

    def relations(self):
        """return the list of possible relation'types

        :rtype: list
        :return: defined relation's types (str) or schemas (`RelationSchema`)
        """
        return self._relations.values()

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

    def final_relations(self):
        """return the list of possible final relation'types

        :rtype: list
        :return: defined relation's types (str) or schemas (`RelationSchema`)
        """
        for rschema in self.relations():
            if rschema.is_final():
                if schema:
                    yield rschema
                else:
                    yield rschema.type

    def nonfinal_relations(self):
        """return the list of possible final relation'types

        :rtype: list
        :return: defined relation's types (str) or schemas (`RelationSchema`)
        """
        for rschema in self.relations():
            if not rschema.is_final():
                if schema:
                    yield rschema
                else:
                    yield rschema.type

    # bw compat
    relation_schema = rschema
    entity_schema = eschema


import logging
from logilab.common.logging_ext import set_log_methods
LOGGER = logging.getLogger('yams')
set_log_methods(Schema, LOGGER)
