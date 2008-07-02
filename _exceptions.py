"""Exceptions shared by different ER-Schema modules.

:organization: Logilab
:copyright: 2004-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__docformat__ = "restructuredtext en"

class SchemaError(Exception):
    """base class for schema exceptions"""
    
    def __str__(self):
        return unicode(self).encode('utf8')
    
class UnknownType(SchemaError):
    """using an unknown entity type"""
    msg = 'Unknown type %s'
    def __unicode__(self):
        return self.msg % self.args

class BadSchemaDefinition(SchemaError):
    """error in the schema definition"""
    msg = '%s line %s: %s'


    def __init__(self, *args):
        if len(args) > 1:
            self.filename = args[0]
            args = args[1:]
        else:
            self.filename = None
        if len(args) > 1:
            self.lineno = args[0]
            args = args[1:]
        else:
            self.lineno = None
        super(BadSchemaDefinition,self).__init__(*args)



    def __unicode__(self):
        msgs = []
        if self.filename is not None:
            msgs.append(self.filename)
            if self.lineno is not None:
                msgs.append(" line %s" % self.lineno)
            msgs.append(': ')
        msgs.append(' '.join(self.args))
        return ''.join(msgs)
class ESQLParseError(Exception):
    """raised when a line is unparsable (end up by a warning)"""
    msg = '%s: unable to parse %s'
    def __str__(self):
        return self.msg % self.args

class ValidationError(SchemaError):
    """validation error are used when some validation failed and precisily
    explain why using a dictionary describing each error
    """

    def __init__(self, entity, explanation):
        # set args so ValidationError are serializable through pyro
        SchemaError.__init__(self, entity, explanation)
        self.entity = entity
        self.errors = explanation
        
    def __unicode__(self):
        if len(self.errors) == 1:
            attr, error = self.errors.items()[0]
            return u'%s (%s): %s' % (self.entity, attr, error)
        errors = '\n'.join('* %s: %s' % (k, v) for k, v in self.errors.items())
        return u'%s:\n%s' % (self.entity, errors)
