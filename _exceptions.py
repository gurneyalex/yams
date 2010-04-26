"""Exceptions shared by different ER-Schema modules.

:organization: Logilab
:copyright: 2004-2009 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: Lesser General Public License version 2 - http://www.gnu.org/licenses/
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
    """error in the schema definition

    instance attributes:
    * filename is the source file where the exception was raised
    * lineno is the line number where the exception was raised
    * line is the actual line in text form
    """

    msg = '%s line %s: %s'

    def __get_filename(self):
        if len(self.args) > 1:
            return self.args[0]
        else:
            return None
    filename = property(__get_filename)

    def __unicode__(self):
        msgs = []
        args_offset = 0
        if self.filename is not None:
            msgs.append(self.filename)
            args_offset += 1
            msgs.append(': ')
        msgs.append(' '.join(self.args[args_offset:]))
        return ''.join(msgs)


class ValidationError(SchemaError):
    """validation error details the reason(s) why the validation failed

    :type entity: EntityType
    :param entity: the entity that could not be validated

    :type explanation: dict
    :param explanation: pairs of (attribute, error)
    """

    def __init__(self, entity, explanation):
        # set args so ValidationError are serializable through pyro
        SchemaError.__init__(self, entity, explanation)
        self.entity = entity
        assert isinstance(explanation, dict), \
            'validation error explanation must be a dict'
        self.errors = explanation

    def __unicode__(self):
        if len(self.errors) == 1:
            attr, error = self.errors.items()[0]
            return u'%s (%s): %s' % (self.entity, attr, error)
        errors = '\n'.join('* %s: %s' % (k, v) for k, v in self.errors.items())
        return u'%s:\n%s' % (self.entity, errors)
