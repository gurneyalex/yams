"""Entity Schema reader, read EntitySchema from Pseudo SQL.

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

import re
from os.path import split, splitext

from yams import MARKER, FileReader
from yams.constraints import StaticVocabularyConstraint, SizeConstraint, \
     MultipleStaticVocabularyConstraint
from yams.buildobjs import EntityType, SubjectRelation

FTI = 1 # Full text indexing

NAME_PAT = "(?P<name>\S+)"
SQL_TYPE_PAT = "(?P<sql_type>[^\(\s]+)"
TYPE_ATTRS = "(\((?P<type_attrs>.*?)\))"
TYPE_PAT = "(?P<type>%s%s?)" % (SQL_TYPE_PAT, TYPE_ATTRS)

DEFAULT_VALUE_CST_PAT = "(DEFAULT\s+(?P<default>\S+(\s+[^\s,]+)*)\s*(?=,|$))"
NOTNULL_VALUE_CST_PAT = '(?P<notnull>NOT NULL)'
VALUE_CST_PAT = "(?P<value_constraint>%s|%s)" % (DEFAULT_VALUE_CST_PAT,
                                                 NOTNULL_VALUE_CST_PAT)
CST_PAT = "(?P<constraints>.*$)"

DEFAULT_VALUE_CST_RE = re.compile(DEFAULT_VALUE_CST_PAT, re.I)
NOTNULL_VALUE_CST_RE = re.compile(NOTNULL_VALUE_CST_PAT, re.I)

SQL_RE = re.compile('%s\s+%s\s*%s' % (NAME_PAT, TYPE_PAT, CST_PAT), re.I)


CHOICE_CLASSES = {
    'Choice': StaticVocabularyConstraint,
    'Multiplechoice': MultipleStaticVocabularyConstraint,
    }


class EsqlFileReader(FileReader):

    def read_file(self, filepath):
        self._edef = EntityType(name=split(splitext(filepath)[0])[1])
        super(EsqlFileReader, self).read_file(filepath)
        self.loader.add_definition(self, self._edef)
        
    def read_line(self, line):
        """reads a line of entity definition"""
        match = SQL_RE.match(line)
        if match is None:
            self.error('invalid sql definition')
        name = match.group('name')
        assert name != 'eid' # XXX ginco specific
        sqltype = match.group('sql_type')
        typeattrs = match.group('type_attrs')
        ftype, baseconstraints, options = self.sql_to_constraints(name, sqltype,
                                                                  typeattrs)
        rdef = SubjectRelation(ftype)
        rdef.name = name
        self._edef.relations.append(rdef)
        rdef.constraints = baseconstraints
        if options & FTI:
            rdef.fulltextindexed = True
        self.parse_suite(rdef, match.group('constraints'), ftype)

    def sql_to_constraints(self, field, sqltype, typeattrs):
        """take an sql type and return a list of internal constraints to apply to
        the attribute. The first element of the list is the type of data (string,
        int...)
        """
        sqltype = sqltype.capitalize()
        if sqltype in ('Integer',):
            return 'Int', [], 0
        if sqltype == 'Float':
            return 'Float', [], 0
        if sqltype == ('Numeric', 'Decimal'):
            return 'Decimal', [], 0
        elif sqltype in ('Date', 'Time', 'Datetime', 'Boolean'):
            return sqltype, [], 0
        elif sqltype == 'Password':
            return 'Password', [SizeConstraint(max=24)], 0
        elif sqltype == 'Bytes':
            return 'Bytes', [], 0
        elif sqltype == 'Ibytes':
            return 'Bytes', [], FTI
        elif sqltype == 'Text':
            return 'String', [], 0
        elif sqltype == 'Itext':
            return 'String', [], FTI
        elif sqltype in ('Char', 'Varchar'):
            length = int(typeattrs)
            return 'String', [SizeConstraint(max=length)], 0
        elif sqltype in ('Ichar', 'Ivarchar'):
            length = int(typeattrs)
            return 'String', [SizeConstraint(max=length)], FTI
        elif sqltype in ('Choice', 'Multiplechoice'):
            # XXX: plante si  virgule dans valeur
            arg = [eval(val.strip()) for val in typeattrs.split(',')]
            rqltype = check_choice_values(arg)
            return rqltype, [CHOICE_CLASSES[sqltype](arg)], 0
        self.error('unknown type %r' % sqltype)


    def parse_suite(self, rdef, suite, etype):
        """Parses the default value and not null constraint retrieved from an
        attribute definition, modifying the relation definition as necessary
        """
        default = MARKER
        # First, make a list for each constraint part
        for cst in [cst.strip() for cst in suite.split(',') if cst.strip()]:
            default_m = DEFAULT_VALUE_CST_RE.match(cst)
            if default_m:
                # Do some stuff to handle default value
                default_str = default_m.group('default')
                default = parse_default_constraint(default_str, etype)
            elif NOTNULL_VALUE_CST_RE.match(cst):
                # Do some stuff to handle "not null" constraints
                rdef.cardinality = '11'
            else:
                self.error(cst)
        if default is MARKER:
            default = getattr(self.default_hdlr, 'default_%s' % rdef.name, MARKER)
        if default is not MARKER:
            rdef.default = default
            

def parse_default_constraint(value, etype):
    """Parses a default value string and return its actual value"""
    if etype == 'Date':
        # XXX: check value is in a valid date format or TODAY or NOW
        value = value.upper()
    elif etype == 'String':
        value = eval(value)
    elif etype == 'Boolean':
        value = eval(value.capitalize())
    return value


def check_choice_values(values):
    """check that all values in a choice are of the same type,
    and return the corresponding Erudi type
    """
    rqltype = None
    for value in values:
        if type(value) == type(''):
            if rqltype is None:
                rqltype = 'String'
            else:
                assert rqltype == 'String', 'different type used in choice'
        elif type(value) == type(0):
            if rqltype is None:
                rqltype = 'Int'
            else:
                assert rqltype == 'Int', 'different type used in choice'
        elif type(value) == type(0.):
            if rqltype is None:
                rqltype = 'Float'
            else:
                assert rqltype == 'Float', 'different type used in choice'
    return rqltype

