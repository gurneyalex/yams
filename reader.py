"""ER schema loader (use either a sql derivated language for entities and
relation definitions files or a direct python definition file)


:version: $Revision: 1.16 $  
:organization: Logilab
:copyright: 2003-2006 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: reader.py,v 1.16 2006-04-10 14:38:59 syt Exp $"
__docformat__ = "restructuredtext en"
__metaclass__ = type

import sys
from os.path import exists, join, splitext
from os import listdir

from logilab.common.fileutils import lines
from logilab.common.textutils import get_csv

from yams import UnknownType, BadSchemaDefinition
from yams import constraints, schema as schemamod
from yams.builder import *

                
def read_perms_def(schema, filepath):
    """read action / groups mapping for an entity / relation schema

    each no empty/comment line should be of the form :
    <action>: <group1> [,<group2]*
    """
    log(LOG_INFO, 'reading permission for %s from %s', (schema.type, filepath))
    for line in lines(filepath, '#'):
        try:
            action, groups = line.split(':')
        except TypeError:
            raise BadSchemaDefinition(line, filepath)
        else:
            action = action.strip().lower()
            groups = get_csv(groups)
            schema.set_groups(action, tuple(groups))            

# .rel and .py formats file readers ###########################################
        
class RelationFileReader(FileReader):
    """read simple relation definitions files"""
    rdefcls = RelationDefinition
    
    def read_line(self, line):
        """read a relation definition:
        
        a 3-uple, as in 'User in_groups Group', optionaly followed by the
        "symetric" keyword and/or by the "constraint" keyword followed by an arbitrary
        expression (should be handled in a derivated class
        
        the special case of '* rel_name Entity' means that the relation is created
        for each entity's types in the schema
        """
        relation_def = line.split()
        try:
            _from, rtype, _to = relation_def[:3]
            relation_def = relation_def[3:]
        except TypeError:
            self.error('bad syntax')
        rdef = self.rdefcls(_from, rtype, _to)
        if 'symetric' in relation_def:
            rdef.symetric = True
            relation_def.remove('symetric')
        if 'inline' in relation_def:
            #print 'XXX inline is deprecated'
            rdef.cardinality = '?*'
            relation_def.remove('inline')
        # is there some arbitrary constraint ?
        if relation_def:
            if relation_def[0].lower() == 'constraint':
                self.handle_constraint(rdef, ' '.join(relation_def[1:]))
            else:
                self.error()
        self.loader.add_definition(self, rdef)

    def handle_constraint(self, rdef, constraint_text):
        """handle an arbitrary constraint on a relation, should be overridden for
        application specific stuff
        """
        self.error("this reader doesn't handle constraint")


CONSTRAINTS = {}
# add constraint classes to the context
for objname in dir(constraints):
    if objname[0] == '_':
        continue
    obj = getattr(constraints, objname)
    try:
        if issubclass(obj, constraints.BaseConstraint) and (
            not obj is constraints.BaseConstraint):
            CONSTRAINTS[objname] = obj
    except TypeError:
        continue

class PyFileReader(FileReader):
    """read schema definition objects from a python file"""
    context = {'EntityType':           EntityType,
               'MetaEntityType':       MetaEntityType,
               'UserEntityType':       UserEntityType,
               'MetaUserEntityType':   MetaUserEntityType,
               
               'RelationType':              RelationType,
               'MetaRelationType':          MetaRelationType,
               'UserRelationType':          UserRelationType,
               'MetaUserRelationType':      MetaUserRelationType,
               'AttributeRelationType':     AttributeRelationType,
               'MetaAttributeRelationType': MetaAttributeRelationType,
               
               'SubjectRelation':      SubjectRelation,
               'ObjectRelation':       ObjectRelation,
               'RelationDefinition':   RelationDefinition,
               '_': str,
               }
    context.update(CONSTRAINTS)

    def __init__(self, *args, **kwargs):
        super(PyFileReader, self).__init__(*args, **kwargs)
        self._loaded = {}

    def read_file(self, filepath):
        try:
            fdata = self._loaded[filepath]
        except KeyError:
            fdata = self.exec_file(filepath)
        for name, obj in fdata.items():
            if name.startswith('_'):
                continue
            try:
                if issubclass(obj, Definition):
                    self.loader.add_definition(self, obj())
            except TypeError:
                continue
        
    def import_schema(self, schemamod):
        filepath = self.loader.include_schema_files(schemamod)[0]            
        try:
            return self._loaded[filepath]
        except KeyError:
            return self.exec_file(filepath)
    
    def exec_file(self, filepath):
        #partname = self._partname(filepath)
        flocals = self.context.copy()
        flocals['import_schema'] = self.import_schema
        execfile(filepath, flocals)
        for key in self.context:
            del flocals[key]
        del flocals['import_schema']
        self._loaded[filepath] = attrdict(flocals)
        return self._loaded[filepath]

class attrdict(dict):
    """a dictionary whose keys are also accessible as attributes"""
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)
    
# the main schema loader ######################################################

from yams.sqlschema import EsqlFileReader

class SchemaLoader(object):
    """the schema loader is responsible to build a schema object from a
    set of files
    """
    schemacls = schemamod.Schema
    lib_directory = None
    read_deprecated_relations = False
    
    file_handlers = {
        '.py' : PyFileReader,
        '.rel' : RelationFileReader,
        '.esql' : EsqlFileReader,
        '.sql' : EsqlFileReader,
        }
    
    def load(self, directory, name=None, default_handler=None):
        """return a schema from the schema definition readen from <directory>
        """
        self._instantiate_handlers(default_handler)
        self._defobjects = []
        if self.lib_directory is not None: 
            sys.path.insert(0, self.lib_directory)
        sys.path.insert(0, directory)
        try:
            self._load_definition_files(directory)
        finally:
            sys.path.pop(0)
            if self.lib_directory is not None: 
                sys.path.pop(0)
        return self._build_schema(name, directory)
    
    def _instantiate_handlers(self, default_handler=None):
        self._live_handlers = {}
        for ext, hdlrcls in self.file_handlers.items():
            self._live_handlers[ext] = hdlrcls(self, default_handler,
                                               self.read_deprecated_relations)

    def _load_definition_files(self, directory):
        for filepath in self.get_schema_files(directory):
            self.handle_file(filepath)
        
    def _build_schema(self, name, directory):
        """build actual schema from definition objects, and return it"""
        schema = self.schemacls(name or 'NoName', directory)
        # register relation types and non final entity types
        for definition in self._defobjects:
            if isinstance(definition, RelationType):
                definition.rschema = schema.add_relation_type(definition)
            elif isinstance(definition, EntityType):
                definition.eschema = schema.add_entity_type(definition)
        # register relation definitions
        for definition in self._defobjects:
            if isinstance(definition, EntityType):
                definition.register_relations(schema)
        for definition in self._defobjects:
            if not isinstance(definition, EntityType):
                definition.register_relations(schema)
        # set permissions on entities and relations
        for erschema in schema.entities(schema=True)+schema.relations(schema=True):
            self._set_perms(directory, erschema)
        return schema

    def get_schema_files(self, base_directory):
        """return an ordered list of files defining a schema"""
        result = []
        for filename in listdir(base_directory):
            if filename[0] == '_':
                continue
            if filename.lower() == 'include':
                for etype in lines(join(base_directory, filename)):
                    for filepath in self.include_schema_files(etype):
                        result.append(filepath)
                continue
            ext = splitext(filename)[1]
            if self.file_handlers.has_key(ext):
                result.append(join(base_directory, filename))
            elif ext != '.perms':
                self.unhandled_file(join(base_directory, filename))
        return result

    def include_schema_files(self, etype, directory=None):
        """return schema files for a type defined in a schemas library"""
        directory = directory or self.lib_directory
        if directory is None:
            raise BadSchemaDefinition('No schemas library defined')
        base = join(directory, etype)
        result = []
        for ext in self.file_handlers.keys():
            if exists(base + ext):
                result.append(base + ext)
        if not result:
            raise UnknownType('No type %s in %s' % (etype, directory))
        return result

    def handle_file(self, filepath):
        """handle a partial schema definition file according to its extension
        """
        self._current_file = filepath
        self._live_handlers[splitext(filepath)[1]](filepath)

    def unhandled_file(self, filepath):
        """called when a file without handler associated has been found,
        does nothing by default.
        """
        pass

    def add_definition(self, hdlr, defobject):
        """file handler callback to add a definition object"""
        if not isinstance(defobject, Definition):
            hdlr.error('invalid definition object')
        self._defobjects.append(defobject)

    def _set_perms(self, directory, erschema):
        erschema.set_default_groups()
        filepath = join(directory, erschema.type + '.perms')
        if not exists(filepath) and self.lib_directory is not None:
            filepath = join(self.lib_directory, erschema.type + '.perms')
        if exists(filepath):
            read_perms_def(erschema, filepath)
            
