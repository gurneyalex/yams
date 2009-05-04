"""ER schema loader.

Use either a sql derivated language for entities and relation definitions
files or a direct python definition file.

:organization: Logilab
:copyright: 2004-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

import sys
from os.path import exists, join, splitext
from os import listdir

from logilab.common import attrdict
from logilab.common.textutils import get_csv

from yams import UnknownType, BadSchemaDefinition, FileReader
from yams import constraints, schema as schemamod
from yams import buildobjs


def _lines(path, comments=None):
    result = []
    for line in open(path, 'U'):
        line = line.strip()
        if line and (comments is None or not line.startswith(comments)):
            result.append(line)
    return result

# .rel and .py formats file readers ###########################################

class RelationFileReader(FileReader): # XXX deprecate this ?
    """read simple relation definitions files"""
    rdefcls = buildobjs.RelationDefinition

    def read_line(self, line):
        """read a relation definition:

        a 3-uple, as in 'User in_groups Group', optionally followed by the
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
        self.process_properties(rdef, relation_def)
        self.loader.add_definition(self, rdef)

    def process_properties(self, rdef, relation_def):
        if 'symetric' in relation_def:
            rdef.symetric = True
            relation_def.remove('symetric')
        if 'inline' in relation_def:
            rdef.cardinality = '?*'
            rdef.inlined = True
            relation_def.remove('inline')
        # is there some arbitrary constraint ?
        if relation_def:
            if relation_def[0].lower() == 'constraint':
                self.handle_constraint(rdef, ' '.join(relation_def[1:]))
            else:
                self.error()

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


def _builder_context():
    """builds the context in which the schema files
    will be executed
    """
    return dict([(attr, getattr(buildobjs, attr))
                 for attr in buildobjs.__all__])

class PyFileReader(FileReader):
    """read schema definition objects from a python file"""
    context = {'_' : unicode}
    context.update(_builder_context())
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
                isdef = issubclass(obj, buildobjs.Definition)
            except TypeError:
                continue
            if isdef:
                self.loader.add_definition(self, obj())

    def import_schema_file(self, schemamod):
        filepath = self.loader.include_schema_files(schemamod)[0]
        try:
            return self._loaded[filepath]
        except KeyError:
            try:
                return self.exec_file(filepath)
            except Exception, ex:
                setattr(ex,'schema_files',filepath)
                raise

    def import_erschema(self, ertype, schemamod=None, instantiate=True):
        try:
            erdef = self.loader.defined[ertype]
            if erdef.name == ertype:
                assert instantiate, 'can\'t get class of an already registered type'
                return erdef
        except KeyError:
            pass
        erdefcls = getattr(self.import_schema_file(schemamod or ertype), ertype)
        if instantiate:
            erdef = erdefcls()
            self.loader.add_definition(self, erdef)
            return erdef
        return erdefcls

    def exec_file(self, filepath):
        flocals = self.context.copy()
        flocals['import_schema'] = self.import_schema_file # XXX deprecate local name
        flocals['import_erschema'] = self.import_erschema
        flocals['defined_types'] = self.loader.defined
        execfile(filepath, flocals)
        for key in self.context:
            if key in flocals:
                del flocals[key]
        del flocals['import_schema']
        self._loaded[filepath] = attrdict(flocals)
        return self._loaded[filepath]

# the main schema loader ######################################################

from yams.sqlreader import EsqlFileReader

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

    def load(self, directories, name=None, default_handler=None,
             register_base_types=True, construction_mode='strict',
             remove_unused_rtypes=True):
        """return a schema from the schema definition read from <directory>
        """
        self.defined = {}
        self.loaded_files = []
        self._instantiate_handlers(default_handler)
        files = self._load_definition_files(directories)
        try:
            schema = self._build_schema(name, register_base_types,
                                        construction_mode=construction_mode,
                                        remove_unused_rtypes=remove_unused_rtypes)
        except Exception, ex:
            if not hasattr(ex, 'schema_files'):
                ex.schema_files = self.loaded_files
            raise ex, None, sys.exc_info()[-1]
        schema.loaded_files = self.loaded_files
        return schema

    def _instantiate_handlers(self, default_handler=None):
        self._live_handlers = {}
        for ext, hdlrcls in self.file_handlers.items():
            self._live_handlers[ext] = hdlrcls(self, default_handler,
                                               self.read_deprecated_relations)

    def _load_definition_files(self, directories):
        for directory in directories:
            for filepath in self.get_schema_files(directory):
                self.handle_file(filepath)

    def _build_schema(self, name, register_base_types=True,
                      construction_mode='strict', remove_unused_rtypes=False):
        """build actual schema from definition objects, and return it"""
        schema = self.schemacls(name or 'NoName', construction_mode=construction_mode)
        if register_base_types:
            buildobjs.register_base_types(schema)
        # register relation types and non final entity types
        for definition in self.defined.itervalues():
            if isinstance(definition, buildobjs.RelationType):
                schema.add_relation_type(definition)
            elif isinstance(definition, buildobjs.EntityType):
                schema.add_entity_type(definition)
        # register relation definitions
        for definition in self.defined.itervalues():
            definition.expand_relation_definitions(self.defined, schema)
        if remove_unused_rtypes:
            # remove relation types without definitions
            for rschema in schema.relations():
                if not rschema.rdefs():
                    schema.del_relation_type(rschema)
        # set permissions on entities and relations
        for erschema in schema.entities() + schema.relations():
            erschema.set_default_groups()
        schema.infer_specialization_rules()
        return schema

    # has to be overideable sometimes (usually for test purpose)
    main_schema_directory = 'schema'
    def get_schema_files(self, directory):
        """return an ordered list of files defining a schema

        look for a schema.py file and or a schema sub-directory in the given
        directory
        """
        result = []
        if exists(join(directory, 'schema.py')):
            result = [join(directory, 'schema.py')]
        if exists(join(directory, self.main_schema_directory)):
            directory = join(directory, self.main_schema_directory)
            for filename in listdir(directory):
                if filename[0] == '_':
                    continue
                if filename.lower() == 'include':
                    for etype in _lines(join(directory, filename)):
                        if etype.startswith('#'):
                            continue
                        for filepath in self.include_schema_files(etype):
                            result.append(filepath)
                    continue
                ext = splitext(filename)[1]
                if self.file_handlers.has_key(ext):
                    result.append(join(directory, filename))
                else:
                    self.unhandled_file(join(directory, filename))
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
        self.loaded_files.append(filepath)

    def unhandled_file(self, filepath):
        """called when a file without handler associated has been found,
        does nothing by default.
        """
        pass

    def add_definition(self, hdlr, defobject):
        """file handler callback to add a definition object

        wildcard capability force to load schema in two steps : first register
        all definition objects (here), then create actual schema objects (done in
        `_build_schema`)
        """
        if not isinstance(defobject, buildobjs.Definition):
            hdlr.error('invalid definition object')
        defobject.expand_type_definitions(self.defined)

