"""Object model and utilities to define generic Entities/Relations schemas.

:copyright:
  2004-2010 `LOGILAB S.A. <http://www.logilab.fr>`_ (Paris, FRANCE),
  all rights reserved.

:contact:
  http://www.logilab.org/project/yams --
  mailto:python-projects@logilab.org

:license:
  `General Public License version 2
  <http://www.gnu.org/licenses/old-licenses/gpl-2.0.html>`_
"""
__docformat__ = "restructuredtext en"

from datetime import datetime, date, time

# set _ builtin to unicode by default, should be overriden if necessary
import __builtin__
__builtin__._ = unicode

from logilab.common.compat import set
from logilab.common.date import strptime, strptime_time
from logilab.common import nullobject

from yams.__pkginfo__ import version as __version__
from yams._exceptions import *

MARKER = nullobject()

BASE_TYPES = set(('String', 'Int', 'Float', 'Boolean', 'Date', 'Decimal',
                  'Time', 'Datetime', 'Interval', 'Password', 'Bytes'))

# base groups used in permissions
BASE_GROUPS = set((_('managers'), _('users'), _('guests'), _('owners')))

KEYWORD_MAP = {'Datetime.NOW' : datetime.now,
               'Datetime.TODAY': datetime.today,
               'Date.TODAY': date.today}
DATE_FACTORY_MAP = {
    'Datetime' : lambda x: ':' in x and strptime(x, '%Y/%m/%d %H:%M') or strptime(x, '%Y/%m/%d'),
    'Date' : lambda x : strptime(x, '%Y/%m/%d'),
    'Time' : strptime_time
    }

# work in progress ###

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
