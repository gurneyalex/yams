# copyright 2004-2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
"""Object model and utilities to define generic Entities/Relations schemas.
"""
__docformat__ = "restructuredtext en"

import warnings
from datetime import datetime, date

from six import string_types, text_type

import pkg_resources

from logilab.common.date import strptime, strptime_time
from logilab.common import nullobject

from yams._exceptions import *


__version__ = pkg_resources.get_distribution('yams').version

_ = text_type

MARKER = nullobject()

BASE_TYPES = set(('String', 'Password', 'Bytes',
                  'Int', 'BigInt', 'Float', 'Boolean', 'Decimal',
                  'Date', 'Time', 'Datetime', 'TZTime', 'TZDatetime', 'Interval'
                  ))

# base groups used in permissions
BASE_GROUPS = set((_('managers'), _('users'), _('guests'), _('owners')))

# default permissions for entity types, relations and attributes
DEFAULT_ETYPEPERMS = {'read': ('managers', 'users', 'guests',),
                      'update': ('managers', 'owners',),
                      'delete': ('managers', 'owners'),
                      'add': ('managers', 'users',)}
DEFAULT_RELPERMS = {'read': ('managers', 'users', 'guests',),
                    'delete': ('managers', 'users'),
                    'add': ('managers', 'users',)}
DEFAULT_ATTRPERMS = {'read': ('managers', 'users', 'guests',),
                     'add': ('managers', 'users'),
                     'update': ('managers', 'owners')}
DEFAULT_COMPUTED_RELPERMS = {'read': ('managers', 'users', 'guests',),
                             'delete': (),
                             'add': ()}
DEFAULT_COMPUTED_ATTRPERMS = {'read': ('managers', 'users', 'guests',),
                              'add': (),
                              'update': ()}


# This provides a way to specify callable objects as default values
# First level is the final type, second is the keyword to callable map
KEYWORD_MAP = {
    'Datetime': {'NOW': datetime.now,
                 'TODAY': datetime.today},
    'TZDatetime': {'NOW': datetime.utcnow,
                   'TODAY': datetime.today},
    'Date': {'TODAY': date.today}
}


# bw compat for literal date/time values stored as strings in schemas
DATE_FACTORY_MAP = {
    'Datetime': lambda x: ':' in x and strptime(x, '%Y/%m/%d %H:%M') or strptime(x, '%Y/%m/%d'),
    'Date': lambda x: strptime(x, '%Y/%m/%d'),
    'Time': strptime_time
}

KNOWN_METAATTRIBUTES = set(('format', 'encoding', 'name'))


def convert_default_value(rdef, default):
    # rdef can be either a .schema.RelationDefinitionSchema or a .buildobjs.RelationDefinition
    rtype = getattr(rdef, 'name', None) or rdef.rtype.type
    if isinstance(default, string_types) and rdef.object != 'String':
        # real Strings can be anything, including things that look like keywords
        # for other base types
        if rdef.object in KEYWORD_MAP:
            try:
                return KEYWORD_MAP[rdef.object][default.upper()]()
            except KeyError:
                # the default was likely not a special constant like TODAY but some literal
                pass
        # bw compat for old schemas
        if rdef.object in DATE_FACTORY_MAP:
            warnings.warn('using strings as default values for attribute %s of type %s '
                          'is deprecated; you should use the plain python objects instead'
                          % (rtype, rdef.object),
                          DeprecationWarning)
            try:
                return DATE_FACTORY_MAP[rdef.object](default)
            except ValueError as verr:
                raise ValueError('creating a default value for attribute %s of type %s '
                                 'from the string %r is not supported (cause %s)'
                                 % (rtype, rdef.object, default, verr))
    if rdef.object == 'String':
        default = text_type(default)
    return default  # general case: untouched default


def register_base_type(name, parameters=(), check_function=None):
    """register a yams base (final) type. You'll have to call
    base_type_class to generate the class.
    """
    from yams.schema import RelationDefinitionSchema
    from yams.constraints import BASE_CHECKERS, yes
    # Add the datatype to yams base types
    assert name not in BASE_TYPES, '%s already in BASE_TYPES %s' % (name, BASE_TYPES)
    BASE_TYPES.add(name)
    # Add the new datatype to the authorized types of RelationDefinitionSchema
    if not isinstance(parameters, dict):
        # turn tuple/list into dict with None values
        parameters = dict((p, None) for p in parameters)
    RelationDefinitionSchema.BASE_TYPE_PROPERTIES[name] = parameters
    # Add a yams checker or yes is not specified
    BASE_CHECKERS[name] = check_function or yes


def unregister_base_type(name):
    """Unregister a yams base (final) type"""
    from yams.schema import RelationDefinitionSchema
    from yams.constraints import BASE_CHECKERS
    assert name in BASE_TYPES, '%s not in BASE_TYPES %s' % (name, BASE_TYPES)
    BASE_TYPES.remove(name)
    RelationDefinitionSchema.BASE_TYPE_PROPERTIES.pop(name)
    BASE_CHECKERS.pop(name)
