"""Exceptions shared by different ER-Schema modules.

:organization: Logilab
:copyright: 2004-2006 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__docformat__ = "restructuredtext en"

class SchemaError(Exception):
    """base class for schema exceptions"""
    
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

class ValidationError(SchemaError):
    """validation error are used when some validation failed and precisily
    explain why using a dictionary describing each error
    """

    def __init__(self, entity, explanation):
        # pylint: disable-msg=W0231
        self.entity = entity
        self.errors = explanation
        
    def __str__(self):
        return '\n'.join('%s: %s' % (k, v) for k, v in self.errors.items())
