"""ER schema loader.

Use either a sql derivated language for entities and relation definitions
files or a direct python definition file.

:organization: Logilab
:copyright: 2004-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

import sys
import types
from os import listdir
from os.path import exists, join, splitext, basename, abspath
from warnings import warn

from logilab.common.testlib import mock_object
from logilab.common.textutils import get_csv
from logilab.common.modutils import modpath_from_file, cleanup_sys_modules

from yams import UnknownType, BadSchemaDefinition, BASE_TYPES
from yams import constraints, schema as schemamod
from yams import buildobjs


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


class DeprecatedDict(dict):
    def __init__(self, context, message):
        dict.__init__(self, context)
        self.message = message

    def __getitem__(self, key):
        warn(self.message, DeprecationWarning, stacklevel=2)
        return super(DeprecatedDict, self).__getitem__(key)
    def __contains__(self, key):
        warn(self.message, DeprecationWarning, stacklevel=2)
        return super(DeprecatedDict, self).__contains__(key)


def _builder_context():
    """builds the context in which the schema files
    will be executed
    """
    return dict([(attr, getattr(buildobjs, attr))
                 for attr in buildobjs.__all__])



class PyFileReader(object):
    """read schema definition objects from a python file"""
    context = _builder_context()
    context.update(CONSTRAINTS)

    def __init__(self, loader):
        self.loader = loader
        self._current_file = None
        self._loaded = {}

    def error(self, msg=None):
        """raise a contextual exception"""
        raise BadSchemaDefinition(self._current_file, msg)

    def read_file(self, filepath):
        self._current_file = filepath
        try:
            modname, module = self._loaded[filepath]
        except KeyError:
            modname, module = self.exec_file(filepath)
        processed_object = set()
        for name, obj in vars(module).items():
            if name.startswith('_'):
                continue
            try:
                isdef = issubclass(obj, buildobjs.Definition)
            except TypeError:
                continue
            if (not isdef) or obj.__module__ != modname or \
                obj in processed_object:
                continue
            self.loader.add_definition(self, obj)
            processed_object.add(obj)

    def import_erschema(self, ertype, schemamod=None, instantiate=True):
        warn('import_erschema is deprecated, use explicit import once schema '
             'is turned into a proper python module (eg not expecting '
             'predefined context in globals)', DeprecationWarning, stacklevel=3)
        try:
            erdef = self.loader.defined[ertype]
            name = hasattr(erdef, 'name') and erdef.name or erdef.__name__
            if name == ertype:
                assert instantiate, 'can\'t get class of an already registered type'
                return erdef
        except KeyError:
            pass
        assert False, 'ooups'

    def exec_file(self, filepath):
        try:
            modname = '.'.join(modpath_from_file(filepath, self.loader.extrapath))
            doimport = True
        except ImportError:
            warn('module for %s can\'t be found, add necessary __init__.py '
                 'files to make it importable' % filepath, DeprecationWarning)
            modname = splitext(basename(filepath))[0]
            doimport = False
        # XXX can't rely on __import__ until bw compat (eg implicit import) needed
        #if doimport:
        #    module = __import__(modname, fglobals)
        #    for part in modname.split('.')[1:]:
        #        module = getattr(module, part)
        #else:
        if modname in sys.modules:
            module = sys.modules[modname]
            # NOTE: don't test raw equality to avoid .pyc / .py comparisons
            assert abspath(module.__file__).startswith(abspath(filepath)), (filepath, module.__file__)
        else:
            # XXX until bw compat is gone, put context into builtins to allow proper
            # control of deprecation warning
            import __builtin__
            fglobals = {} # self.context.copy()
            # wrap callable that should be imported
            for key, val in self.context.items():
                if key in BASE_TYPES or key == 'RichString' or key in CONSTRAINTS or \
                       key in ('SubjectRelation', 'ObjectRelation', 'BothWayRelation'):
                    val = obsolete(val)
                setattr(__builtin__, key, val)
            __builtin__.import_erschema = self.import_erschema
            __builtin__.defined_types = DeprecatedDict(self.loader.defined,
                                                        'defined_types is deprecated, '
                                                        'use yams.reader.context')
            fglobals['__file__'] = filepath
            fglobals['__name__'] = modname
            package = '.'.join(modname.split('.')[:-1])
            if package and not package in sys.modules:
                __import__(package)
            execfile(filepath, fglobals)
            # check for use of classes that should be imported, without
            # importing them
            for name, obj in fglobals.items():
                if isinstance(obj, type) and \
                       issubclass(obj, buildobjs.Definition) and \
                       obj.__module__ == modname:
                    for parent in obj.__bases__:
                        pname = parent.__name__
                        if pname in ('MetaEntityType', 'MetaUserEntityType',
                                     'MetaRelationType', 'MetaUserRelationType',
                                     'MetaAttributeRelationType'):
                            warn('%s: %s is deprecated, use EntityType/RelationType'
                                 ' with explicit permission (%s)' % (filepath, pname, name),
                                 DeprecationWarning)
                        if pname in fglobals or not pname in self.context:
                            # imported
                            continue
                        warn('%s: please explicitly import %s (%s)'
                             % (filepath, pname, name), DeprecationWarning)
            for key in self.context:
                fglobals.pop(key, None)
            fglobals['__file__'] = filepath
            module = types.ModuleType(str(modname))
            module.__dict__.update(fglobals)
            sys.modules[modname] = module
            if package:
                setattr(sys.modules[package], modname.split('.')[-1], module)
        if hasattr(module, 'post_build_callback'):
            self.loader.post_build_callbacks.append(module.post_build_callback)
        self._loaded[filepath] = (modname, module)
        return self._loaded[filepath]

def obsolete(cls):
    def wrapped(*args, **kwargs):
        reason = '%s should be explictly imported from %s' % (
            cls.__name__, cls.__module__)
        warn(reason, DeprecationWarning, stacklevel=2)
        return cls(*args, **kwargs)
    return wrapped

# the main schema loader ######################################################

class SchemaLoader(object):
    """the schema loader is responsible to build a schema object from a
    set of files
    """
    schemacls = schemamod.Schema
    extrapath = None

    def load(self, directories, name=None,
             register_base_types=True, construction_mode='strict',
             remove_unused_rtypes=True):
        """return a schema from the schema definition read from <directory>
        """
        self.defined = {}
        self.loaded_files = []
        self._pyreader = PyFileReader(self)
        self.post_build_callbacks = []
        sys.modules[__name__].context = self
        # ensure we don't have an iterator
        directories = tuple(directories)
        try:
            self._load_definition_files(directories)
            try:
                schema = self._build_schema(name, register_base_types,
                                            construction_mode=construction_mode,
                                            remove_unused_rtypes=remove_unused_rtypes)
            except Exception, ex:
                if not hasattr(ex, 'schema_files'):
                    ex.schema_files = self.loaded_files
                raise ex, None, sys.exc_info()[-1]
        finally:
            # cleanup sys.modules from schema modules
            # ensure we're only cleaning schema [sub]modules
            directories = [(not directory.endswith(self.main_schema_directory)
                            and join(directory, self.main_schema_directory)
                            or directory)
                           for directory in directories]
            cleanup_sys_modules(directories)
        schema.loaded_files = self.loaded_files
        return schema

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
            if isinstance(definition, type):
                definition = definition()
            if isinstance(definition, buildobjs.RelationType):
                schema.add_relation_type(definition)
            elif isinstance(definition, buildobjs.EntityType):
                schema.add_entity_type(definition)
        # register relation definitions
        for definition in self.defined.itervalues():
            if isinstance(definition, type):
                definition = definition()
            definition.expand_relation_definitions(self.defined, schema)
        # call 'post_build_callback' functions found in schema modules
        for cb in self.post_build_callbacks:
            cb(schema)
        # optionaly remove relation types without definitions
        if remove_unused_rtypes:
            for rschema in schema.relations():
                if not rschema.rdefs:
                    schema.del_relation_type(rschema)
        # set permissions on entities and relations
        for erschema in schema.entities() + schema.relations():
            erschema.check_permission_definitions()
        schema.infer_specialization_rules()
        return schema

    # has to be overridable sometimes (usually for test purpose)
    main_schema_directory = 'schema'
    def get_schema_files(self, directory):
        """return an ordered list of files defining a schema

        look for a schema.py file and or a schema sub-directory in the given
        directory
        """
        result = []
        if exists(join(directory, self.main_schema_directory + '.py')):
            result = [join(directory, self.main_schema_directory + '.py')]
        if exists(join(directory, self.main_schema_directory)):
            directory = join(directory, self.main_schema_directory)
            for filename in listdir(directory):
                if filename[0] == '_':
                    if filename == '__init__.py':
                        result.insert(0, join(directory, filename))
                    continue
                ext = splitext(filename)[1]
                if ext == '.py':
                    result.append(join(directory, filename))
                else:
                    self.unhandled_file(join(directory, filename))
        return result

    def handle_file(self, filepath):
        """handle a partial schema definition file according to its extension
        """
        ext = splitext(filepath)[1]
        assert ext == '.py'
        self._pyreader.read_file(filepath)
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
        if not issubclass(defobject, buildobjs.Definition):
            hdlr.error('invalid definition object')
        defobject.expand_type_definitions(self.defined)


context = mock_object(defined={})
