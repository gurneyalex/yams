# copyright 2004-2012 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
"""YAMS exception classes"""

__docformat__ = "restructuredtext en"

import sys

from six import PY2, text_type


class SchemaError(Exception):
    """base class for schema exceptions"""

    if PY2:
        def __str__(self):
            return unicode(self).encode('utf8')
    else:
        def __str__(self):
            return self.__unicode__()


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
    """Validation error details the reason(s) why the validation failed.

    Arguments are:

    * `entity`: the entity that could not be validated; actual type depends on
      the client library

    * `errors`: errors dictionary, None key used for global error, other keys
      should be attribute/relation of the entity, qualified as subject/object
      using :func:`yams.role_name`.  Values are the message associated to the
      keys, and may include interpolation string starting with '%(KEY-' where
      'KEY' will be replaced by the associated key once the message has been
      translated. This allows predictable/translatable message and avoid args
      conflict if used for several keys.

    * `msgargs`: dictionary of substitutions to be inserted in error
      messages once translated (only if msgargs is given)

    * `i18nvalues`: list of keys in msgargs whose value should be translated

    Translation will be done **in-place** by calling :meth:`translate`.
    """

    def __init__(self, entity, errors, msgargs=None, i18nvalues=None):
        # set args so ValidationError are serializable through pyro
        SchemaError.__init__(self, entity, errors)
        self.entity = entity
        assert isinstance(errors, dict), 'validation errors must be a dict'
        self.errors = errors
        self.msgargs = msgargs
        self.i18nvalues = i18nvalues
        self._translated = False

    def __unicode__(self):
        if self._translated:
            errors = self.errors
        else:
            errors = dict(self._translated_errors(text_type))
        if len(errors) == 1:
            attr, error = next(iter(errors.items()))
            return u'%s (%s): %s' % (self.entity, attr, error)
        errors = '\n'.join('* %s: %s' % (k, v) for k, v in errors.items())
        return u'%s:\n%s' % (self.entity, errors)

    def translate(self, _):
        """Translate and interpolate messsages in the errors dictionary, using
        the given translation function.

        If no substitution has been given, suppose msg is already translated for
        bw compat, so no translation occurs.

        This method may only be called once.
        """
        assert not self._translated
        self._translated = True
        if self.msgargs is not None:
            if self.i18nvalues:
                for key in self.i18nvalues:
                    self.msgargs[key] = _(self.msgargs[key])
        self.errors = dict(self._translated_errors(_))

    def _translated_errors(self, _):
        for key, msg in self.errors.items():
            msg = _(msg)
            if key is not None:
                msg = msg.replace('%(KEY-', '%('+key+'-')
            if self.msgargs:
                msg = msg % self.msgargs
            yield key, msg

