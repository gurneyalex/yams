"""defines classes used to build a schema

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""
__docformat__ = "restructuredtext en"

from logilab.common import attrdict
from logilab.common.compat import sorted

from yams import BASE_TYPES, MARKER, BadSchemaDefinition
from yams.constraints import SizeConstraint, UniqueConstraint, \
     StaticVocabularyConstraint

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
RTYPE_PROPERTIES = ('meta', 'symetric', 'inlined', 'permissions')
RDEF_PROPERTIES = ('cardinality', 'constraints', 'composite',
                   'order',  'default', 'uid', 'indexed', 'uid', 
                   'fulltextindexed', 'internationalizable')

REL_PROPERTIES = RTYPE_PROPERTIES+RDEF_PROPERTIES + ('description',)


def add_constraint(kwargs, constraint):
    constraints = kwargs.setdefault('constraints', [])
    for i, existingconstraint in enumerate(constraints):
        if existingconstraint.__class__ is constraint.__class__:
            constraints[i] = constraint
            return
    constraints.append(constraint)
        
def add_relation(relations, rdef, name=None):
    if isinstance(rdef, BothWayRelation):
        add_relation(relations, rdef.subjectrel, name)
        add_relation(relations, rdef.objectrel, name)
    else:
        if name is not None:
            rdef.name = name
        relations.append(rdef)

def check_kwargs(kwargs, attributes):
    for key in kwargs:
        if not key in attributes: 
            raise BadSchemaDefinition('no such property %r' % key)
    
def copy_attributes(fromobj, toobj, attributes):
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
    """abstract class which have to be defined before the metadefinition
    meta-class
    """

# first class schema definition objects #######################################

class Definition(object):
    """abstract class for entity / relation definition classes"""

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
        """schema building step 1:

        register definition objects by adding them to the `defined` dictionnary
        """
        raise NotImplementedError()
    
    def expand_relation_definitions(self, defined, schema):
        """schema building step 2:

        register all relations definition, expanding wildcard if necessary
        """
        raise NotImplementedError()


class metadefinition(type):
    """this metaclass builds the __relations__ attribute
    of EntityType's subclasses
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
        defclass = super(metadefinition, mcs).__new__(mcs, name, bases, classdict)
        for rname, rdef in relations.items():
            add_relation(defclass.__relations__, rdef, rname)
        # take base classes'relations into account
        for base in bases:
            rels.extend(getattr(base, '__relations__', []))
        # sort relations by creation rank
        defclass.__relations__ = sorted(rels, key=lambda r: r.creation_rank)
        return defclass
    
        
class EntityType(Definition):

    __metaclass__ = metadefinition
        
    def __init__(self, name=None, **kwargs):
        super(EntityType, self).__init__(name)
        check_kwargs(kwargs, ETYPE_PROPERTIES)
        copy_attributes(attrdict(kwargs), self, ETYPE_PROPERTIES)
        # if not hasattr(self, 'relations'):
        self.relations = list(self.__relations__)

    def __str__(self):
        return 'entity type %r' % self.name
    
    def expand_type_definitions(self, defined):
        """schema building step 1:

        register definition objects by adding them to the `defined` dictionnary
        """
        assert not self.name in defined
        defined[self.name] = self
        for relation in self.relations:
            rtype = RelationType(relation.name)
            copy_attributes(relation, rtype, RTYPE_PROPERTIES)
            if relation.name in defined:
                copy_attributes(rtype, defined[relation.name], RTYPE_PROPERTIES)
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
                copy_attributes(relation, rdef, RDEF_PROPERTIES + ('description',))
            elif isinstance(relation, ObjectRelation):
                rdef = RelationDefinition(subject=relation.etype,
                                          name=relation.name,
                                          object=self.name, order=order)
                copy_attributes(relation, rdef, RDEF_PROPERTIES + ('description',))
            else:
                raise BadSchemaDefinition('dunno how to handle %s' % relation)
            order += 1
            rdef._add_relations(defined, schema)

    # methods that can be used to extend an existant schema definition ########
    
    def extend(self, othermetadefcls):
        for rdef in othermetadefcls.__relations__:
            self.add_relation(rdef)
            
    def add_relation(self, rdef, name=None):
        add_relation(self.relations, rdef, name)
            
    def remove_relation(self, name):
        for rdef in self._get_relations(name):
            self.relations.remove(rdef)
            
    def _get_relations(self, name):
        """get relation definitions by name (may have multiple definitions with
        the same name if the relation is both a subject and object relation)
        """
        for rdef in self.relations[:]:
            if rdef.name == name:
                yield rdef

    
class RelationType(Definition):
    symetric = MARKER
    inlined = MARKER
    
    def __init__(self, name=None, **kwargs):
        super(RelationType, self).__init__(name)
        check_kwargs(kwargs, RTYPE_PROPERTIES + ('description',))
        copy_attributes(attrdict(kwargs), self, RTYPE_PROPERTIES + ('description',))

    def __str__(self):
        return 'relation type %r' % self.name
    
    def expand_type_definitions(self, defined):
        """schema building step 1:

        register definition objects by adding them to the `defined` dictionnary
        """
        if self.name in defined:
            copy_attributes(self, defined[self.name],
                            REL_PROPERTIES + ('subject', 'object'))
        else:
            defined[self.name] = self
            
    def expand_relation_definitions(self, defined, schema):
        """schema building step 2:

        register all relations definition, expanding wildcard if necessary
        """
        if getattr(self, 'subject', None) or getattr(self, 'object', None):
            assert self.subject and self.object
            rdef = RelationDefinition(subject=self.subject, name=self.name,
                                      object=self.object)
            copy_attributes(self, rdef, RDEF_PROPERTIES)
            rdef._add_relations(defined, schema)


class RelationDefinition(Definition):
    subject = MARKER
    object = MARKER
    cardinality = MARKER
    constraints = MARKER
    symetric = MARKER
    inlined = MARKER
    
    def __init__(self, subject=None, name=None, object=None,**kwargs):
        if subject:
            self.subject = subject
        else:
            self.subject = self.__class__.subject
        if object:
            self.object = object
        else:
            self.object = self.__class__.object
        super(RelationDefinition, self).__init__(name)
        check_kwargs(kwargs, RDEF_PROPERTIES + ('description',))
        copy_attributes(attrdict(kwargs), self, RDEF_PROPERTIES + ('description',))
        if self.constraints:
            self.constraints = list(self.constraints)
        
    def __str__(self):
        return 'relation definition (%(subject)s %(name)s %(object)s)' % self.__dict__

    def expand_type_definitions(self, defined):
        """schema building step 1:

        register definition objects by adding them to the `defined` dictionnary
        """
        rtype = RelationType(self.name)
        copy_attributes(self, rtype, RTYPE_PROPERTIES)
        if self.name in defined:
            copy_attributes(rtype, defined[self.name], RTYPE_PROPERTIES)
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
        assert self.subject and self.object
        self._add_relations(defined, schema)
    
    def _add_relations(self, defined, schema):
        rtype = defined[self.name]
        copy_attributes(rtype, self, RDEF_PROPERTIES)
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
                copy_attributes(self, rdef, RDEF_PROPERTIES + ('description',))
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

    
# classes used to define relation within entity type classes ##################


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
        check_kwargs(kwargs, REL_PROPERTIES)
        copy_attributes(attrdict(kwargs), self, REL_PROPERTIES)
    
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
            add_constraint(kwargs, SizeConstraint(max=maxsize))
        vocabulary = kwargs.pop('vocabulary', None)
        if vocabulary is not None:
            self.set_vocabulary(vocabulary, kwargs)
        unique = kwargs.pop('unique', None)
        if unique:
            add_constraint(kwargs, UniqueConstraint())
        # use the etype attribute provided by subclasses
        super(AbstractTypedAttribute, self).__init__(self.etype, **kwargs)

    def set_vocabulary(self, vocabulary, kwargs=None):
        if kwargs is None:
            kwargs = self.__dict__
        #constraints = kwargs.setdefault('constraints', [])
        add_constraint(kwargs, StaticVocabularyConstraint(vocabulary))
        if self.__class__.__name__ == 'String': # XXX
            maxsize = max(len(x) for x in vocabulary)
            add_constraint(kwargs, SizeConstraint(max=maxsize))
            
    def __repr__(self):
        return '<%(name)s(%(etype)s)>' % self.__dict__
        
# build a specific class for each base type
for basetype in BASE_TYPES:
    globals()[basetype] = type(basetype, (AbstractTypedAttribute,),
                               {'etype' : basetype})

