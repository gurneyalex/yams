"""defines classes used to build a schema
"""

__docformat__ = "restructuredtext en"
__metaclass__ = type

from logilab.common.compat import set, sorted

from yams import BadSchemaDefinition
from yams.constraints import SizeConstraint, UniqueConstraint, \
     StaticVocabularyConstraint

BASE_TYPES = set(('String', 'Int', 'Float', 'Boolean', 'Date',
                  'Time', 'Datetime', 'Interval', 'Password', 'Bytes'))

__all__ = ('ObjectRelation', 'SubjectRelation', 'BothWayRelation',
           'RelationDefinition', 'EntityType', 'MetaEntityType',
           'RestrictedEntityType', 'UserEntityType', 'MetaUserEntityType',
           'RelationType', 'MetaRelationType', 'UserRelationType',
           'MetaUserRelationType', 'AttributeRelationType',
           'MetaAttributeRelationType',
           'SubjectRelation', 'ObjectRelation', 'BothWayRelation',
           ) + tuple(BASE_TYPES)


# \(Object\|Subject\)Relation(relations, '\([a-z_A-Z]+\)',
# -->
# \2 = \1Relation(
class Relation(object): pass

class ObjectRelation(Relation):
    cardinality = None
    constraints = ()
    created = 0

    def __init__(self, etype, **kwargs):
        ObjectRelation.created += 1
        self.creation_rank = ObjectRelation.created
        self.name = '<undefined>'
        self.etype = etype
        self.constraints = list(self.constraints)
        self.__dict__.update(kwargs)
    
    def __repr__(self):
        return '%(name)s %(etype)s' % self.__dict__


        
class SubjectRelation(ObjectRelation):
    uid = False
    indexed = False
    fulltextindexed = False
    internationalizable = False
    default = None
    
    def __repr__(self):
        return '%(etype)s %(name)s' % self.__dict__


class BothWayRelation(Relation):

    def __init__(self, subjectrel, objectrel):
        assert isinstance(subjectrel, SubjectRelation)
        assert isinstance(objectrel, ObjectRelation)
        self.subjectrel = subjectrel
        self.objectrel = objectrel

def add_constraint(kwargs, constraint):
    constraints = kwargs.setdefault('constraints', [])
    for i, existingconstraint in enumerate(constraints):
        if existingconstraint.__class__ is constraint.__class__:
            constraints[i] = constraint
            return
    constraints.append(constraint)
    
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


RDEF_PROPERTIES = ('meta', 'symetric', 'inlined', 
                   'cardinality', 'constraints', 'composite',
                   'order', 'description',
                   'default', 'uid', 'indexed', 'uid', 
                   'fulltextindexed', 'internationalizable')

def copy_attributes(fromobj, toobj):
    for attr in RDEF_PROPERTIES:
        try:
            setattr(toobj, attr, getattr(fromobj, attr))
        except AttributeError:
            continue
        
class Definition(object):
    """abstract class for entity / relation definition classes"""

    meta = False
    subject, object = None, None
    
    def __init__(self, name=None, **kwargs):
        self.__dict__.update(kwargs)
        self.name = (name or getattr(self, 'name', None)
                     or self.__class__.__name__)
        # XXX check properties
        #for key, val in kwargs.items():
        #    if not hasattr(self, key):
        #        self.error('no such property %r' % key)

    def register_relations(self, schema):
        raise NotImplementedError()

    def add_relations(self, schema):
        try:
            rschema = schema.rschema(self.name)
        except KeyError:
            # .rel file compat: the relation type may have not been added
            rtype = RelationType(**self.__dict__)
            rschema = schema.add_relation_type(rtype)
        for subj in self._actual_types(schema, self.subject):
            for obj in self._actual_types(schema, self.object):
                if isinstance(self, RelationDefinition):
                    rdef = self
                else:
                    rdef = RelationDefinition(subj, self.name, obj)
                    copy_attributes(self, rdef)
                assert isinstance(subj, basestring), subj
                assert isinstance(obj, basestring), obj
                rdef.subject = subj
                rdef.object = obj
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
            defclass.add_relation(rdef, rname)
        # take baseclases' relation into account
        for base in bases:
            rels.extend(getattr(base, '__relations__', []))
        # sort relations by creation rank
        defclass.__relations__ = sorted(rels, key=lambda r: r.creation_rank)
        return defclass
    
        
        
class EntityType(Definition):

    __metaclass__ = metadefinition

    @classmethod
    def extend(cls, othermetadefcls):
        for rdef in othermetadefcls.__relations__:
            cls.add_relation(rdef)
        
    @classmethod
    def add_relation(cls, rdef, name=None):
        if isinstance(rdef, BothWayRelation):
            cls.add_relation(rdef.subjectrel, name)
            cls.add_relation(rdef.objectrel, name)
        else:
            if name is not None:
                rdef.name = name
            cls.__relations__.append(rdef)
            
    @classmethod
    def remove_relation(cls, name):
        for rdef in cls.get_relations(name):
            cls.__relations__.remove(rdef)
            
    @classmethod
    def get_relations(cls, name):
        """get a relation definitions by name
        XXX take care, if the relation is both and subject/object, the
        first one encountered will be returned
        """
        for rdef in cls.__relations__[:]:
            if rdef.name == name:
                yield rdef
            
        
    def __init__(self, *args, **kwargs):
        super(EntityType, self).__init__(*args, **kwargs)
        # if not hasattr(self, 'relations'):
        self.relations = list(self.__relations__)

    def register_relations(self, schema):
        order = 1
        for relation in self.relations:
            if isinstance(relation, SubjectRelation):
                kwargs = relation.__dict__.copy()
                del kwargs['name']
                rdef = RelationDefinition(subject=self.name, name=relation.name,
                                          object=relation.etype, order=order,
                                          **kwargs)
                order += 1                
            elif isinstance(relation, ObjectRelation):
                kwargs = relation.__dict__.copy()
                del kwargs['name']
                rdef = RelationDefinition(subject=relation.etype,
                                          name=relation.name,
                                          object=self.name, order=order,
                                          **kwargs)
                order += 1
            else:
                raise BadSchemaDefinition('duh?')
            rdef.add_relations(schema)

    
class RelationBase(Definition):
    cardinality = None
    constraints = ()
    symetric = False
    
    def __init__(self, *args, **kwargs):
        super(RelationBase, self).__init__(*args, **kwargs)
        self.constraints = list(self.constraints)
        if self.object is None:
            return
        cardinality = self.cardinality
        if cardinality is None:
            if self.object in BASE_TYPES:
                self.cardinality = '?1'
            else:
                self.cardinality = '**'
        else:
            assert len(cardinality) == 2
            assert cardinality[0] in '1?+*'
            assert cardinality[1] in '1?+*'
    
class RelationType(RelationBase):
    object = None
        
    def register_relations(self, schema):
        if getattr(self, 'subject', None) or getattr(self, 'object', None):
            assert self.subject and self.object
            self.add_relations(schema)


class RelationDefinition(RelationBase):
    subject = None
    object = None
    def __init__(self, subject=None, name=None, object=None, **kwargs):
        if subject:
            self.subject = subject
        else:
            self.subject = self.__class__.subject
        if object:
            self.object = object
        else:
            self.object = self.__class__.object
        if name:
            self.name = name
        elif not getattr(self, 'name', None):
            self.name = self.__class__.__name__
        super(RelationDefinition, self).__init__(**kwargs)
        
    def register_relations(self, schema):
        assert self.subject and self.object
        self.add_relations(schema)
        
    def __repr__(self):
        return '%(subject)s %(name)s %(object)s' % self.__dict__
    

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
    permissions = None
    
class MetaAttributeRelationType(AttributeRelationType):
    meta = True
    

class FileReader(object):
    """abstract class for file readers"""
    
    def __init__(self, loader, defaulthandler=None, readdeprecated=False):
        self.loader = loader
        self.default_hdlr = defaulthandler
        self.read_deprecated = readdeprecated
        self._current_file = None
        self._current_line = None
        self._current_lineno = None

    def __call__(self, filepath):
        self._current_file = filepath
        self.read_file(filepath)
        
    def error(self, msg=None):
        """raise a contextual exception"""
        raise BadSchemaDefinition(self._current_line, self._current_file, msg)
    
    def read_file(self, filepath):
        """default implementation, calling .read_line method for each
        non blank lines, and ignoring lines starting by '#' which are
        considered as comment lines
        """
        for i, line in enumerate(file(filepath)):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            self._current_line = line
            self._current_lineno = i
            if line.startswith('//'):
                if self.read_deprecated:
                    self.read_line(line[2:])
            else:
                self.read_line(line)

    def read_line(self, line):
        """need overriding !"""
        raise NotImplementedError()

