"""Object model and utilities to define generic Entities/Relations schemas.

:copyright:
  2004-2008 `LOGILAB S.A. <http://www.logilab.fr>`_ (Paris, FRANCE),
  all rights reserved.

:contact:
  http://www.logilab.org/project/yams --
  mailto:python-projects@logilab.org

:license:
  `General Public License version 2
  <http://www.gnu.org/licenses/old-licenses/gpl-2.0.html>`_
"""
__docformat__ = "restructuredtext en"
from yams.__pkginfo__ import version as __version__

# set _ builtin to unicode by default, should be overriden if necessary
import __builtin__
__builtin__._ = unicode

from logilab.common.compat import set

BASE_TYPES = set(('String', 'Int', 'Float', 'Boolean', 'Date', 'Decimal',
                  'Time', 'Datetime', 'Interval', 'Password', 'Bytes'))

# base groups used in permissions
BASE_GROUPS = set((_('managers'), _('users'), _('guests'), _('owners')))


from logilab.common import nullobject
MARKER = nullobject()


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

# work in progress
from yams._exceptions import *
from yams.schema import Schema, EntitySchema, RelationSchema

class _RelationRole(int):
    def __eq__(self, other):
        if isinstance(other, _RelationRole):
            return other is self
        if self:
            return other == 'object'
        return other == 'subject'
    def __nonzero__(self):
        print 'oyop'
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
