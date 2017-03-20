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
"""ER schema loader.

Use either a sql derivated language for entities and relation definitions
files or a direct python definition file.
"""
from __future__ import print_function

__docformat__ = "restructuredtext en"

import sys
import os
import types
import pkgutil
from os import listdir
from os.path import (dirname, exists, join, splitext, basename, abspath,
                     realpath)
from warnings import warn

from logilab.common import tempattr
from logilab.common.modutils import modpath_from_file, cleanup_sys_modules, clean_sys_modules

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


def fill_schema(schema, erdefs, register_base_types=True,
                remove_unused_rtypes=False, post_build_callbacks=[]):
    if register_base_types:
        buildobjs.register_base_types(schema)
    # relation definitions may appear multiple times
    erdefs_vals = set(erdefs.values())
    # register relation types and non final entity types
    for definition in erdefs_vals:
        if isinstance(definition, type):
            definition = definition()
        if isinstance(definition, buildobjs.RelationType):
            schema.add_relation_type(definition)
        elif isinstance(definition, buildobjs.EntityType):
            schema.add_entity_type(definition)
    # register relation definitions
    for definition in erdefs_vals:
        if isinstance(definition, type):
            definition = definition()
        definition.expand_relation_definitions(erdefs, schema)
    # call 'post_build_callback' functions found in schema modules
    for cb in post_build_callbacks:
        cb(schema)
    # finalize schema
    schema.finalize()
    # check permissions are valid on entities and relations
    for erschema in schema.entities() + schema.relations():
        erschema.check_permission_definitions()
    # check unique together consistency
    for eschema in schema.entities():
        eschema.check_unique_together()
    # optionaly remove relation types without definitions
    if remove_unused_rtypes:
        for rschema in schema.relations():
            if not rschema.rdefs:
                schema.del_relation_type(rschema)
    return schema


class SchemaLoader(object):
    """the schema loader is responsible to build a schema object from a
    set of files
    """
    schemacls = schemamod.Schema
    extrapath = None
    context = dict([(attr, getattr(buildobjs, attr))
                    for attr in buildobjs.__all__])
    context.update(CONSTRAINTS)

    def load(self, modnames, name=None,
             register_base_types=True, construction_mode='strict',
             remove_unused_rtypes=True):
        """return a schema from the schema definition read from <modnames> (a
        list of (PACKAGE, modname))
        """
        self.defined = {}
        self.loaded_files = []
        self.post_build_callbacks = []
        sys.modules[__name__].context = self
        # ensure we don't have an iterator
        modnames = tuple(modnames)
        # legacy usage using a directory list
        is_directories = modnames and not isinstance(modnames[0],
                                                     (list, tuple))
        try:
            if is_directories:
                warn('provide a list of modules names instead of directories',
                     DeprecationWarning)
                self._load_definition_files(modnames)
            else:
                self._load_modnames(modnames)
            schema = self.schemacls(name or 'NoName', construction_mode=construction_mode)
            try:
                fill_schema(schema, self.defined, register_base_types,
                            remove_unused_rtypes=remove_unused_rtypes,
                            post_build_callbacks=self.post_build_callbacks)
            except Exception as ex:
                if not hasattr(ex, 'schema_files'):
                    ex.schema_files = self.loaded_files
                raise
        finally:
            # cleanup sys.modules from schema modules
            # ensure we're only cleaning schema [sub]modules
            if is_directories:
                directories = [(not directory.endswith(os.sep + self.main_schema_directory)
                                and join(directory, self.main_schema_directory)
                                or directory)
                               for directory in modnames]
                cleanup_sys_modules(directories)
            else:
                clean_sys_modules([mname for _, mname in modnames])
        schema.loaded_files = self.loaded_files
        return schema

    def _load_definition_files(self, directories):
        for directory in directories:
            package = basename(directory)
            for filepath in self.get_schema_files(directory):
                with tempattr(buildobjs, 'PACKAGE', package):
                    self.handle_file(filepath, None)

    def _load_modnames(self, modnames):
        for package, modname in modnames:
            loader = pkgutil.find_loader(modname)
            filepath = loader.get_filename()
            if filepath.endswith('.pyc'):
                # check that related source file exists and ensure passing a
                # .py file to exec_file()
                filepath = filepath[:-1]
                if not exists(filepath):
                    continue
            with tempattr(buildobjs, 'PACKAGE', package):
                self.handle_file(filepath, modname=modname)

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

    def handle_file(self, filepath, modname=None):
        """handle a partial schema definition file according to its extension
        """
        assert filepath.endswith('.py'), 'not a python file'
        if filepath not in self.loaded_files:
            modname, module = self.exec_file(filepath, modname)
            objects_to_add = set()
            for name, obj in vars(module).items():
                if (isinstance(obj, type)
                    and issubclass(obj, buildobjs.Definition)
                    and obj.__module__ == modname
                    and not name.startswith('_')):
                    objects_to_add.add(obj)
            for obj in objects_to_add:
                self.add_definition(obj, filepath)
            if hasattr(module, 'post_build_callback'):
                self.post_build_callbacks.append(module.post_build_callback)
            self.loaded_files.append(filepath)

    def unhandled_file(self, filepath):
        """called when a file without handler associated has been found,
        does nothing by default.
        """
        pass

    def add_definition(self, defobject, filepath=None):
        """file handler callback to add a definition object

        wildcard capability force to load schema in two steps : first register
        all definition objects (here), then create actual schema objects (done in
        `_build_schema`)
        """
        if not issubclass(defobject, buildobjs.Definition):
            raise BadSchemaDefinition(filepath, 'invalid definition object')
        defobject.expand_type_definitions(self.defined)

    def exec_file(self, filepath, modname):
        if modname is None:
            try:
                modname = '.'.join(modpath_from_file(filepath, self.extrapath))
            except ImportError:
                warn('module for %s can\'t be found, add necessary __init__.py '
                     'files to make it importable' % filepath, DeprecationWarning)
                modname = splitext(basename(filepath))[0]
        if modname in sys.modules:
            module = sys.modules[modname]
            # NOTE: don't test raw equality to avoid .pyc / .py comparisons
            mpath = realpath(abspath(module.__file__))
            fpath = realpath(abspath(filepath))
            assert mpath.startswith(fpath), (
                modname, filepath, module.__file__)
        else:
            fglobals = {} # self.context.copy()
            fglobals['__file__'] = filepath
            fglobals['__name__'] = modname
            package = '.'.join(modname.split('.')[:-1])
            if package and not package in sys.modules:
                __import__(package)
            with open(filepath) as f:
                try:
                    code = compile(f.read(), filepath, 'exec')
                    exec(code, fglobals)
                except:
                    print('exception while reading %s' % filepath, file=sys.stderr)
                    raise
            fglobals['__file__'] = filepath
            module = types.ModuleType(str(modname))
            module.__dict__.update(fglobals)
            sys.modules[modname] = module
            if package:
                setattr(sys.modules[package], modname.split('.')[-1], module)
            if basename(filepath) == '__init__.py':
                # add __path__ to make dynamic loading work as defined in PEP 302
                # https://www.python.org/dev/peps/pep-0302/#packages-and-the-role-of-path
                module.__path__ = [dirname(filepath)]
        return (modname, module)

# XXX backward compatibility to prevent changing cw.schema and cw.test.unittest_schema (3.12.+)
PyFileReader = SchemaLoader
PyFileReader.__init__ = lambda *x: None

def fill_schema_from_namespace(schema, items, **kwargs):
    erdefs = {}
    for name, obj in items:
        if (isinstance(obj, type) and issubclass(obj, buildobjs.Definition)
            and obj not in (buildobjs.Definition, buildobjs.RelationDefinition, buildobjs.EntityType)):
            obj.expand_type_definitions(erdefs)
    fill_schema(schema, erdefs, **kwargs)

def build_schema_from_namespace(items):
    schema = schemamod.Schema('noname')
    fill_schema_from_namespace(schema, items)
    return schema

class _Context(object):
    def __init__(self):
        self.defined = {}

context = _Context()
