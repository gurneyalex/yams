"""defines classes used to build a schema
"""

__revision__ = "$Id: builder.py,v 1.6 2006-04-10 14:38:59 syt Exp $"
__docformat__ = "restructuredtext en"
__metaclass__ = type

from logilab.common.compat import set
from yams import BadSchemaDefinition

BASE_TYPES = set(('String', 'Int', 'Float', 'Boolean', 'Date',
                  'Time', 'Datetime', 'Password', 'Bytes'))


class Definition(object):
    """abstract class for entity / relation definition classes"""
    
    meta = False
    name = None
    subject, object = None, None
    
    def __init__(self, name=None, **kwargs):
        self.__dict__.update(kwargs)
        self.name = name or getattr(self, 'name', None) or self.__class__.__name__
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
            rtype = RelationType(name=self.name, symetric=self.symetric)
            rschema = schema.add_relation_type(rtype)
        for subj in self._actual_types(schema, self.subject):
            for obj in self._actual_types(schema, self.object):
                rdef = RelationDefinition(subj, self.name, obj)
                rdef.__dict__.update(self.__dict__)
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
        for eschema in schema.entities(True):
            if eschema.is_final() or eschema.meta:
                continue
            yield eschema.type
        
    def _pow_etypes(self, schema):
        for eschema in schema.entities(True):
            if eschema.is_final():
                continue
            yield eschema.type


class EntityType(Definition):
    
    def __init__(self, *args, **kwargs):
        super(EntityType, self).__init__(*args, **kwargs)
        if not hasattr(self, 'relations'):
            self.relations = []
    
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
                rdef = RelationDefinition(subject=relation.etype, name=relation.name,
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
    def __init__(self, subject, name, object, **kwargs):
        self.subject = subject
        self.object = object
        self.name = name
        super(RelationDefinition, self).__init__(**kwargs)
        
    def register_relations(self, schema):
        assert self.subject and self.object
        self.add_relations(schema)
        
    def __repr__(self):
        return '%(subject)s %(name)s %(object)s' % self.__dict__
    
class ObjectRelation(object):
    cardinality = None
    constraints = ()
    
    def __init__(self, relations, rname, etype, **kwargs):
        relations.append(self)
        self.name = rname
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
    

class MetaEntityType(EntityType):
    permissions = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers',),
        'delete': ('managers',),
        'update': ('managers', 'owners',),
        }
    meta = True

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

