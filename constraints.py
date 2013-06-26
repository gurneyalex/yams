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
"""Some common constraint classes."""

__docformat__ = "restructuredtext en"
_ = unicode

import re
import decimal
import operator
from StringIO import StringIO

from logilab.common.deprecation import class_renamed

import yams
from yams import BadSchemaDefinition
from yams.interfaces import IConstraint, IVocabularyConstraint


class BaseConstraint(object):
    """base class for constraints"""
    __implements__ = IConstraint

    def check_consistency(self, subjschema, objschema, rdef):
        pass

    def type(self):
        return self.__class__.__name__

    def serialize(self):
        """called to make persistent valuable data of a constraint"""
        return None

    @classmethod
    def deserialize(cls, value):
        """called to restore serialized data of a constraint. Should return
        a `cls` instance
        """
        return cls()

    def failed_message(self, key, value):
        return _('%(KEY-cstr)s constraint failed for value %(KEY-value)r'), {
            key+'-cstr': self,
            key+'-value': value}

# possible constraints ########################################################

class UniqueConstraint(BaseConstraint):
    """object of relation must be unique"""

    def __str__(self):
        return 'unique'

    def check_consistency(self, subjschema, objschema, rdef):
        if not objschema.final:
            raise BadSchemaDefinition("unique constraint doesn't apply to non "
                                      "final entity type")

    def check(self, entity, rtype, values):
        """return true if the value satisfy the constraint, else false"""
        return True


class SizeConstraint(BaseConstraint):
    """the string size constraint :

    if max is not None the string length must not be greater than max
    if min is not None the string length must not be shorter than min
    """

    def __init__(self, max=None, min=None):
        assert (max is not None or min is not None), "No max or min"
        self.max = max
        self.min = min

    def __str__(self):
        res = 'size'
        if self.max is not None:
            res = '%s <= %s' % (res, self.max)
        if self.min is not None:
            res = '%s <= %s' % (self.min, res)
        return res

    def check_consistency(self, subjschema, objschema, rdef):
        if not objschema.final:
            raise BadSchemaDefinition("size constraint doesn't apply to non "
                                      "final entity type")
        if not objschema in ('String', 'Bytes', 'Password'):
            raise BadSchemaDefinition("size constraint doesn't apply to %s "
                                      "entity type" % objschema)
        if self.max:
            for cstr in rdef.constraints:
                if cstr.__class__ is StaticVocabularyConstraint:
                    for value in cstr.values:
                        if len(value) > self.max:
                            raise BadSchemaDefinition(
                                'size constraint set to %s but vocabulary '
                                'contains string of greater size' % self.max)

    def check(self, entity, rtype, value):
        """return true if the value is in the interval specified by
        self.min and self.max
        """
        if self.max is not None:
            if len(value) > self.max:
                return False
        if self.min is not None:
            if len(value) < self.min:
                return False
        return True

    def failed_message(self, key, value):
        if self.max is not None and len(value) > self.max:
            return _('value should have maximum size of %(KEY-max)s but found %(KEY-size)s'), {
                key+'-max': self.max,
                key+'-size': len(value)}
        if self.min is not None and len(value) < self.min:
            return _('value should have minimum size of %(KEY-min)s but found %(KEY-size)s'), {
                key+'-min': self.min,
                key+'-size': len(value)}
        assert False, 'shouldnt be there'

    def serialize(self):
        """simple text serialization"""
        if self.max and self.min:
            return u'min=%s,max=%s' % (self.min, self.max)
        if self.max:
            return u'max=%s' % (self.max)
        return u'min=%s' % (self.min)

    @classmethod
    def deserialize(cls, value):
        """simple text deserialization"""
        kwargs = {}
        for adef in value.split(','):
            key, val = [w.strip() for w in adef.split('=')]
            assert key in ('min', 'max')
            kwargs[str(key)] = int(val)
        return cls(**kwargs)


class RegexpConstraint(BaseConstraint):
    """specifies a set of allowed patterns for a string value"""
    __implements__ = IConstraint

    def __init__(self, regexp, flags=0):
        """
        Construct a new RegexpConstraint.

        :Parameters:
         - `regexp`: (str) regular expression that strings must match
         - `flags`: (int) flags that are passed to re.compile()
        """
        self.regexp = regexp
        self.flags = flags
        self._rgx = re.compile(regexp, flags)

    def __str__(self):
        return 'regexp %s' % self.regexp

    def check_consistency(self, subjschema, objschema, rdef):
        if not objschema.final:
            raise BadSchemaDefinition("regexp constraint doesn't apply to non "
                                      "final entity type")
        if not objschema in ('String', 'Password'):
            raise BadSchemaDefinition("regexp constraint doesn't apply to %s "
                                      "entity type" % objschema)

    def check(self, entity, rtype, value):
        """return true if the value maches the regular expression"""
        return self._rgx.match(value, self.flags)

    def failed_message(self, key, value):
        return _("%(KEY-value)r doesn't match the %(KEY-regexp)r regular expression"), {
            key+'-value': value,
            key+'-regexp': self.regexp}

    def serialize(self):
        """simple text serialization"""
        return u'%s,%s' % (self.regexp, self.flags)

    @classmethod
    def deserialize(cls, value):
        """simple text deserialization"""
        regexp, flags = value.rsplit(',', 1)
        return cls(regexp, int(flags))

    def __deepcopy__(self, memo):
        return RegexpConstraint(self.regexp, self.flags)


OPERATORS = {
    '<=': operator.le,
    '<': operator.lt,
    '>': operator.gt,
    '>=': operator.ge,
    }

class BoundaryConstraint(BaseConstraint):
    """the int/float bound constraint :

    set a minimal or maximal value to a numerical value
    """
    __implements__ = IConstraint

    def __init__(self, op, boundary=None):
        assert op in OPERATORS, op
        self.operator = op
        self.boundary = boundary

    def __str__(self):
        return 'value %s' % self.serialize()

    def check_consistency(self, subjschema, objschema, rdef):
        if not objschema.final:
            raise BadSchemaDefinition("bound constraint doesn't apply to non "
                                      "final entity type")

    def check(self, entity, rtype, value):
        """return true if the value satisfy the constraint, else false"""
        boundary = actual_value(self.boundary, entity)
        return OPERATORS[self.operator](value, boundary)

    def failed_message(self, key, value):
        return _("value %(KEY-value)s must be %(KEY-op)s %(KEY-boundary)s"), {
            key+'-value': value,
            key+'-op': self.operator,
            key+'-boundary': self.boundary}

    def serialize(self):
        """simple text serialization"""
        return u'%s %s' % (self.operator, self.boundary)

    @classmethod
    def deserialize(cls, value):
        """simple text deserialization"""
        op, boundary = value.split(' ', 1)
        return cls(op, eval(boundary))

BoundConstraint = class_renamed('BoundConstraint', BoundaryConstraint)
BoundConstraint.type = lambda x: 'BoundaryConstraint'


class IntervalBoundConstraint(BaseConstraint):
    """an int/float bound constraint :

    sets a minimal and / or a maximal value to a numerical value
    This class replaces the BoundConstraint class
    """
    __implements__ = IConstraint

    def __init__(self, minvalue=None, maxvalue=None):
        """
        :param minvalue: the minimal value that can be used
        :param maxvalue: the maxvalue value that can be used
        """
        assert not (minvalue is None and maxvalue is None)
        self.minvalue = minvalue
        self.maxvalue = maxvalue

    def __str__(self):
        return 'value [%s]' % self.serialize()

    def check_consistency(self, subjschema, objschema, rdef):
        if not objschema.final:
            raise BadSchemaDefinition("interval bound constraint doesn't apply "
                                      "to non final entity type")

    def check(self, entity, rtype, value):
        minvalue = actual_value(self.minvalue, entity)
        if minvalue is not None and value < minvalue:
            return False
        maxvalue = actual_value(self.maxvalue, entity)
        if maxvalue is not None and value > maxvalue:
            return False
        return True

    def failed_message(self, key, value):
        if self.minvalue is not None and value < self.minvalue:
            return _("value %(KEY-value)s must be >= %(KEY-boundary)s"), {
                key+'-value': value,
                key+'-boundary': self.minvalue}
        if self.maxvalue is not None and value > self.maxvalue:
            return _("value %(KEY-value)s must be <= %(KEY-boundary)s"), {
                key+'-value': value,
                key+'-boundary': self.maxvalue}
        assert False, 'shouldnt be there'

    def serialize(self):
        """simple text serialization"""
        return u'%s;%s' % (self.minvalue, self.maxvalue)

    @classmethod
    def deserialize(cls, value):
        """simple text deserialization"""
        minvalue, maxvalue = value.split(';')
        return cls(eval(minvalue), eval(maxvalue))


class StaticVocabularyConstraint(BaseConstraint):
    """Enforces a predefined vocabulary set for the value."""
    __implements__ = IVocabularyConstraint

    def __init__(self, values):
        self.values = tuple(values)

    def __str__(self):
        return 'value in (%s)' % self.serialize()

    def check(self, entity, rtype, value):
        """return true if the value is in the specific vocabulary"""
        return value in self.vocabulary(entity=entity)

    def failed_message(self, key, value):
        if isinstance(value, basestring):
            value = '"%s"' % unicode(value)
            choices = ', '.join('"%s"' % val for val in self.values)
        else:
            choices = ', '.join(unicode(val) for val in self.values)
        return _('invalid value %(KEY-value)s, it must be one of %(KEY-choices)s'), {
            key+'-value': value,
            key+'-choices': choices}

    def vocabulary(self, **kwargs):
        """return a list of possible values for the attribute"""
        return self.values

    def serialize(self):
        """serialize possible values as a csv list of evaluable strings"""
        try:
            sample = iter(self.vocabulary()).next()
        except:
            sample = unicode()
        if not isinstance(sample, basestring):
            return u', '.join(repr(word) for word in self.vocabulary())
        return u', '.join(repr(unicode(word).replace(',', ',,'))
                          for word in self.vocabulary())

    @classmethod
    def deserialize(cls, value):
        """deserialize possible values from a csv list of evaluable strings"""
        values = [eval(w) for w in re.split('(?<!,), ', value)]
        if values and isinstance(values[0], basestring):
            values = [v.replace(',,', ',') for v in values]
        return cls(values)


class FormatConstraint(StaticVocabularyConstraint):

    regular_formats = (_('text/rest'),
                       _('text/html'),
                       _('text/plain'),
                       )
    def __init__(self):
        pass

    def check_consistency(self, subjschema, objschema, rdef):
        if not objschema.final:
            raise BadSchemaDefinition("unique constraint doesn't apply to non "
                                      "final entity type")
        if not objschema == 'String':
            raise BadSchemaDefinition("format constraint only apply to String")

    def serialize(self):
        """called to make persistent valuable data of a constraint"""
        return None

    @classmethod
    def deserialize(cls, value):
        """called to restore serialized data of a constraint. Should return
        a `cls` instance
        """
        return cls()

    def vocabulary(self, **kwargs):
        return self.regular_formats

    def __str__(self):
        return 'value in (%s)' % u', '.join(repr(unicode(word)) for word in self.vocabulary())

FORMAT_CONSTRAINT = FormatConstraint()


class MultipleStaticVocabularyConstraint(StaticVocabularyConstraint):
    """Enforce a list of values to be in a predefined set vocabulary."""
    # XXX never used
    def check(self, entity, rtype, values):
        """return true if the values satisfy the constraint, else false"""
        vocab = self.vocabulary(entity=entity)
        for value in values:
            if not value in vocab:
                return False
        return True

# special classes to be used w/ constraints accepting values as argument(s):
# IntervalBoundConstraint

import datetime # needed for timedelta evaluation

def actual_value(value, entity):
    if hasattr(value, 'value'):
        return value.value(entity)
    return value


class Attribute(object):
    def __init__(self, attr):
        self.attr = attr

    def __str__(self):
        return '%s(%r)' % (self.__class__.__name__, self.attr)

    def value(self, entity):
        return getattr(entity, self.attr)


class NOW(object):
    def __init__(self, offset=None):
        self.offset = offset

    def __str__(self):
        return '%s(%r)' % (self.__class__.__name__, self.offset)

    def value(self, entity):
        now = yams.KEYWORD_MAP['Datetime.NOW']()
        if self.offset:
            now += self.offset
        return now


class TODAY(object):
    def __init__(self, offset=None, type='Date'):
        self.offset = offset
        self.type = type

    def __str__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.offset, self.type)

    def value(self, entity):
        now = yams.KEYWORD_MAP['%s.TODAY' % self.type]()
        if self.offset:
            now += self.offset
        return now


# base types checking functions ################################################

def check_string(eschema, value):
    """check value is an unicode string"""
    return isinstance(value, unicode)

def check_password(eschema, value):
    """check value is an encoded string"""
    return isinstance(value, (str, StringIO))

def check_int(eschema, value):
    """check value is an integer"""
    try:
        int(value)
    except ValueError:
        return False
    return True

def check_float(eschema, value):
    """check value is a float"""
    try:
        float(value)
    except ValueError:
        return False
    return True

def check_decimal(eschema, value):
    """check value is a Decimal"""
    try:
        decimal.Decimal(value)
    except (TypeError, decimal.InvalidOperation):
        return False
    return True

def check_boolean(eschema, value):
    """check value is a boolean"""
    return isinstance(value, int)

def check_file(eschema, value):
    """check value has a getvalue() method (e.g. StringIO or cStringIO)"""
    return hasattr(value, 'getvalue')

def yes(*args, **kwargs):
    """dunno how to check"""
    return True


BASE_CHECKERS = {
    'Date' :     yes,
    'Time' :     yes,
    'Datetime' : yes,
    'TZTime' :   yes,
    'TZDatetime':yes,
    'Interval' : yes,
    'String' :   check_string,
    'Int' :      check_int,
    'BigInt' :   check_int,
    'Float' :    check_float,
    'Decimal' :  check_decimal,
    'Boolean' :  check_boolean,
    'Password' : check_password,
    'Bytes' :    check_file,
    }

BASE_CONVERTERS = {
    'String' :  unicode,
    'Password':  str,
    'Int' :      int,
    'BigInt' :   int,
    'Float' :    float,
    'Boolean' :  bool,
    'Decimal' :  decimal.Decimal,
    }

def patch_sqlite_decimal():
    """patch Decimal checker and converter to bypass SQLITE Bug
    (SUM of Decimal return float in SQLITE)"""
    def convert_decimal(value):
        # XXX issue a warning
        if isinstance(value, float):
            value = str(value)
        return decimal.Decimal(value)
    def check_decimal(eschema, value):
        """check value is a Decimal"""
        try:
            if isinstance(value, float):
                return True
            decimal.Decimal(value)
        except (TypeError, decimal.InvalidOperation):
            return False
        return True

    global BASE_CONVERTERS
    BASE_CONVERTERS['Decimal'] = convert_decimal
    global BASE_CHECKERS
    BASE_CHECKERS["Decimal"] = check_decimal
