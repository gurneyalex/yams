"""some default constraint classes

:version: $Revision: 1.1 $  
:organization: Logilab
:copyright: 2003-2006 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: constraints.py,v 1.1 2006-03-30 19:50:56 syt Exp $"
__docformat__ = "restructuredtext en"

from yams.interfaces import IConstraint, IVocabularyConstraint
        
class BaseConstraint(object):
    """base class for constraints"""
    __implements__ = IConstraint
    
    def serialize(self):
        """called to make persistent valuable data of a constraint"""
        return None
    
    def deserialize(cls, value):
        """called to restore serialized data of a constraint. Should return
        a `cls` instance
        """
        return cls()
    deserialize = classmethod(deserialize)


# possible constraints ########################################################

class UniqueConstraint(BaseConstraint):
    
    def check(self, entity, rtype, values):
        """return true if the value satisfy the constraint, else false"""
        return True
    
class SizeConstraint(BaseConstraint):
    """the string size constraint :
    
    if max is not None the string length must not be greater than max
    if in is not None the string length must not be shorter than min
    """
    
    def __init__(self, max=None, min=None):
        self.max = max
        self.min = min
        
    def check(self, entity, rtype, value):
        """return true if the value is in the interval specified by
        self.min and self.max
        """
        if self.max is not None:
            if len(value) > self.max:
                return 0
        if self.min is not None:
            if len(value) < self.min:
                return 0
        return 1
    
    def __str__(self):
        res = 'size'
        if self.max is not None:
            res = '%s < %s' % (res, self.max)
        if self.min is not None:
            res = '%s < %s' % (self.min, res)
        return res
    
    def serialize(self):
        """simple text serialization"""
        if self.max and self.min:
            return 'min=%s,max=%s' % (self.min, self.max)
        if self.max:
            return 'max=%s' % (self.max)
        return 'min=%s' % (self.min)
            
    def deserialize(cls, value):
        """simple text deserialization"""
        kwargs = {}
        for adef in value.split(','):
            key, val = [w.strip() for w in adef.split('=')]
            assert key in ('min', 'max')
            kwargs[str(key)] = int(val)
        return cls(**kwargs)
    deserialize = classmethod(deserialize)
            
    
class BoundConstraint(BaseConstraint):
    """the int/float bound constraint :

    set a minimal or maximal value to a numerical value
    """
    __implements__ = IConstraint
    
    def __init__(self, operator, bound=None):
        assert operator in ('<=', '<', '>', '>=')
        self.type = operator
        self.bound = bound
        
    def check(self, entity, rtype, value):
        """return true if the value satisfy the constraint, else false"""
        return eval('%s %s %s' % (value, self.type, self.bound))

    def __str__(self):
        return 'value %s' % self.serialize()

    def serialize(self):
        """simple text serialization"""
        return '%s %s' % (self.type, self.bound)
    
    def deserialize(cls, value):
        """simple text deserialization"""
        operator = value.split()[0]
        bound = ' '.join(value.split()[1:])
        return cls(operator, bound)
    deserialize = classmethod(deserialize)


class StaticVocabularyConstraint(BaseConstraint):
    """the static vocabulary constraint :

    enforce the value to be in a predefined set vocabulary
    """
    __implements__ = IVocabularyConstraint
    
    def __init__(self, values):
        self.values = tuple(values)
        
    def check(self, entity, rtype, value):
        """return true if the value is in the specific vocabulary"""
        return value in self.vocabulary()

    def vocabulary(self):
        """return a list of possible values for the attribute
        """
        return self.values
    
    def __str__(self):
        return 'value in (%s)' % self.serialize()
    
    def serialize(self):
        """serialize possible values as a csv list of evaluable strings"""
        return u', '.join([repr(unicode(word)) for word in self.vocabulary()])
    
    def deserialize(cls, value):
        """deserialize possible values from a csv list of evaluable strings"""
        return cls([eval(w) for w in value.split(', ')])
    deserialize = classmethod(deserialize)


class MultipleStaticVocabularyConstraint(StaticVocabularyConstraint):
    """the multiple static vocabulary constraint :

    enforce a list of values to be in a predefined set vocabulary

    XXX never used
    """    
    def check(self, entity, rtype, values):
        """return true if the values satisfy the constraint, else false"""
        vocab = self.vocabulary()
        for value in values:
            if not value in vocab:
                return False
        return True


# base types checking functions ###############################################

def check_string(eschema, value):
    """check value is an unicode string"""
    return isinstance(value, unicode)
    
def check_password(eschema, value):
    """check value is an encoded string"""
    return isinstance(value, str)
    
def check_int(eschema, value):
    """check value is an integer"""
    try:
        int(value)
    except ValueError:
        return 0
    return 1
    
def check_float(eschema, value):
    """check value is a float"""
    try:
        float(value)
    except ValueError:
        return 0
    return 1
    
def check_boolean(eschema, value):
    """check value is a boolean"""
    return isinstance(value, int)
    
def check_file(eschema, value):
    """check value has a getvalue() method (e.g. StringIO or cStringIO)"""
    return hasattr(value, 'getvalue')
    
def yes(*args, **kwargs):
    """dunno how to check"""
    return 1

BASE_CHECKERS = {
    'Date' :     yes,
    'Time' :     yes,
    'Datetime' : yes,
    'String' :   check_string,
    'Int' :      check_int,
    'Float' :    check_float,
    'Boolean' :  check_boolean,
    'Password' : check_password,
    'Bytes' :    check_file,
    }
