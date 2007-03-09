"""model object and utilities to define generic Entities/Relations schemas

:organization: Logilab
:copyright: 2004-2007 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

from yams._exceptions import *
from yams.schema import Schema, EntitySchema, RelationSchema
from yams.reader import SchemaLoader

# set _ builtin to unicode by default, should be overriden if necessary
import __builtin__
__builtin__._ = unicode
