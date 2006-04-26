"""Exceptions shared by different ER-Schema modules.

:organization: Logilab
:copyright: 2004 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:version: $Revision: 1.4 $  
"""

__revision__ = "$Id: _exceptions.py,v 1.4 2006-03-17 18:17:51 syt Exp $"
__docformat__ = "restructuredtext en"

#class MyException(
class SchemaError(Exception):
    """base class for schema exceptions"""

class InvalidEntity(SchemaError):
    """the entity is not valid according to its schema"""
    msg = 'Invalid entity %s: \n%s'
    
## class InvalidAttributeValue(SchemaError):
##     """an entity's attribute value is not valid according to its schema"""
    
class UnknownType(SchemaError):
    """using an unknown entity type"""
    msg = 'Unknown type %s'

class BadSchemaDefinition(SchemaError):
    """error in the schema definition"""
    msg = '%s line %s: %s'
    args = ()
    def __str__(self):
        if len(self.args) == 3:
            return self.msg % self.args
        return ' '.join(self.args)

class ESQLParseError(Exception):
    """raised when a line is unparsable (end up by a warning)"""
    msg = '%s: unable to parse %s'
    args = ()
    def __str__(self):
        return self.msg % self.args
