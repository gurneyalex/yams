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

from datetime import datetime, date, time

# XXX set _ builtin to unicode by default, should be overriden if necessary
import __builtin__
__builtin__._ = unicode

from logilab.common.date import strptime, strptime_time
from logilab.common import nullobject

from yams.__pkginfo__ import version as __version__
from yams._exceptions import *

MARKER = nullobject()

BASE_TYPES = set(('String', 'Password', 'Bytes',
                  'Int', 'BigInt', 'Float', 'Boolean', 'Decimal',
                  'Date', 'Time', 'Datetime', 'TZTime', 'TZDatetime', 'Interval'
                  ))

# base groups used in permissions
BASE_GROUPS = set((_('managers'), _('users'), _('guests'), _('owners')))

KEYWORD_MAP = {'Datetime.NOW' : datetime.now,
               'Datetime.TODAY': datetime.today,
               'TZDatetime.NOW' : datetime.utcnow,
               'TZDatetime.TODAY': datetime.today,
               'Date.TODAY': date.today}
DATE_FACTORY_MAP = {
    'Datetime' : lambda x: ':' in x and strptime(x, '%Y/%m/%d %H:%M') or strptime(x, '%Y/%m/%d'),
    'Date' : lambda x : strptime(x, '%Y/%m/%d'),
    'Time' : strptime_time
    }

KNOWN_METAATTRIBUTES = set(('format', 'encoding', 'name'))

# work in progress ###

class _RelationRole(int):
    def __eq__(self, other):
        if isinstance(other, _RelationRole):
            return other is self
        if self:
            return other == 'object'
        return other == 'subject'
    def __nonzero__(self):
        if self is SUBJECT:
            return OBJECT
        return SUBJECT


SUBJECT = _RelationRole(0)
OBJECT  = _RelationRole(1)

from warnings import warn

def ensure_new_subjobj(val, cls=None, attr=None):
    if isinstance(val, int):
        return val
    if val == 'subject':
        msg = 'using string instead of cubicweb.SUBJECT'
        if cls:
            msg += ' for attribute %s of class %s' % (attr, cls.__name__)
        warn(DeprecationWarning, msg)
        return SUBJECT
    if val == 'object':
        msg = 'using string instead of cubicweb.OBJECT'
        if cls:
            msg += ' for attribute %s of class %s' % (attr, cls.__name__)
        warn(DeprecationWarning, msg)
        return SUBJECT

def register_base_type(name, parameters=(), check_function=None):
    """register a yams base (final) type. You'll have to call
    base_type_class to generate the class.
    """
    from yams.schema import RelationDefinitionSchema
    from yams.constraints import BASE_CHECKERS, yes
    # Add the datatype to yams base types
    assert name not in BASE_TYPES, '%s alreadt in BASE_TYPES %s' % (name, BASE_TYPES)
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
