"""Object model and utilities to define generic Entities/Relations schemas.

:organization: Logilab
:copyright: 2004-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

# set _ builtin to unicode by default, should be overriden if necessary
import __builtin__
__builtin__._ = unicode

from logilab.common.compat import set
    
BASE_TYPES = set(('String', 'Int', 'Float', 'Boolean', 'Date',
                  'Time', 'Datetime', 'Interval', 'Password', 'Bytes'))

from logilab.common import nullobject
MARKER = nullobject()


class FileReader(object):
    """Abstract class for file readers."""
    
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
        raise BadSchemaDefinition(self._current_file, self._current_lineno,
            self._current_line, msg)
    
    def read_file(self, filepath):
        """default implementation, calling read_line() method for each
        non-blank lines, and ignoring lines starting by '#' which are
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

from yams._exceptions import *
from yams.schema import Schema, EntitySchema, RelationSchema
from yams.__pkginfo__ import version as __version__
