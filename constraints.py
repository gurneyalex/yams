"""Some common constraint classes.

:organization: Logilab
:copyright: 2004-2009 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""

__docformat__ = "restructuredtext en"

import re
import decimal
import operator
from StringIO import StringIO

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
            res = '%s < %s' % (res, self.max)
        if self.min is not None:
            res = '%s < %s' % (self.min, res)
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
        return 'regexp %s' % self.serialize()

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

class BoundConstraint(BaseConstraint):
    """the int/float bound constraint :

    set a minimal or maximal value to a numerical value
    This class is DEPRECATED, use IntervalBoundConstraint instead
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

    def serialize(self):
        """simple text serialization"""
        return u'%s %s' % (self.operator, self.boundary)

    @classmethod
    def deserialize(cls, value):
        """simple text deserialization"""
        op, boundary = value.split(' ', 1)
        return cls(op, eval(boundary))


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
        return u', '.join(repr(unicode(word)) for word in self.vocabulary())

    @classmethod
    def deserialize(cls, value):
        """deserialize possible values from a csv list of evaluable strings"""
        return cls([eval(w) for w in value.split(', ')])


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

format_constraint = FormatConstraint()


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
    'Interval' : yes,
    'String' :   check_string,
    'Int' :      check_int,
    'Float' :    check_float,
    'Decimal' :  check_decimal,
    'Boolean' :  check_boolean,
    'Password' : check_password,
    'Bytes' :    check_file,
    }

BASE_CONVERTERS = {
    'Int' :      int,
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
