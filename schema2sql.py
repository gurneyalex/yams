"""write a schema as sql

:organization: Logilab
:copyright: 2004-2009 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: Lesser General Public License version 2 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"
__metaclass__ = type

from logilab.common.compat import sorted

from yams.constraints import SizeConstraint, UniqueConstraint

# default are usually not handled at the sql level. If you want them, set
# SET_DEFAULT to True
SET_DEFAULT = False


def schema2sql(dbhelper, schema, skip_entities=(), skip_relations=(), prefix=''):
    """write to the output stream a SQL schema to store the objects
    corresponding to the given schema
    """
    output = []
    w = output.append
    for etype in sorted(schema.entities()):
        eschema = schema.eschema(etype)
        if eschema.final or eschema.type in skip_entities:
            continue
        w(eschema2sql(dbhelper, eschema, skip_relations, prefix=prefix))
    for rtype in sorted(schema.relations()):
        rschema = schema.rschema(rtype)
        if rschema.final or rschema.inlined:
            continue
        w(rschema2sql(rschema))
    return '\n'.join(output)


def dropschema2sql(schema, skip_entities=(), skip_relations=(), prefix=''):
    """write to the output stream a SQL schema to store the objects
    corresponding to the given schema
    """
    output = []
    w = output.append
    for etype in sorted(schema.entities()):
        eschema = schema.eschema(etype)
        if eschema.final or eschema.type in skip_entities:
            continue
        w(dropeschema2sql(eschema, skip_relations, prefix=prefix))
    for rtype in sorted(schema.relations()):
        rschema = schema.rschema(rtype)
        if rschema.final or rschema.inlined:
            continue
        w(droprschema2sql(rschema))
    return '\n'.join(output)


def eschema_attrs(eschema, skip_relations):
    attrs = [attrdef for attrdef in eschema.attribute_definitions()
             if not attrdef[0].type in skip_relations]
    attrs += [(rschema, None)
              for rschema in eschema.subject_relations()
              if not rschema.final and rschema.inlined]
    return attrs


def dropeschema2sql(eschema, skip_relations=(), prefix=''):
    """return sql to drop an entity type's table"""
    # not necessary to drop indexes, that's implictly done when dropping
    # the table
    return 'DROP TABLE %s;' % (prefix + eschema.type)


def eschema2sql(dbhelper, eschema, skip_relations=(), prefix=''):
    """write an entity schema as SQL statements to stdout"""
    output = []
    w = output.append
    table = prefix + eschema.type
    w('CREATE TABLE %s(' % (table))
    attrs = eschema_attrs(eschema, skip_relations)
    # XXX handle objectinline physical mode
    for i in xrange(len(attrs)):
        rschema, attrschema = attrs[i]
        if attrschema is not None:
            sqltype = aschema2sql(dbhelper, eschema, rschema, attrschema,
                                  indent=' ')
        else: # inline relation
            # XXX integer is ginco specific
            sqltype = 'integer'
        if i == len(attrs) - 1:
            w(' %s%s %s' % (prefix, rschema.type, sqltype))
        else:
            w(' %s%s %s,' % (prefix, rschema.type, sqltype))
    w(');')
    # create index
    for i in xrange(len(attrs)):
        rschema, attrschema = attrs[i]
        if attrschema is None or eschema.rdef(rschema).indexed:
            w(dbhelper.sql_create_index(table, prefix + rschema.type))
    w('')
    return '\n'.join(output)


def aschema2sql(dbhelper, eschema, rschema, aschema, creating=True, indent=''):
    """write an attribute schema as SQL statements to stdout"""
    attr = rschema.type
    rdef = rschema.rdef(eschema.type, aschema.type)
    sqltype = type_from_constraints(dbhelper, aschema.type, rdef.constraints,
                                    creating)
    if SET_DEFAULT:
        default = eschema.default(attr)
        if default is not None:
            if aschema.type == 'Boolean':
                sqltype += ' DEFAULT %s' % dbhelper.boolean_value(default)
            elif aschema.type == 'String':
                sqltype += ' DEFAULT %r' % str(default)
            elif aschema.type in ('Int', 'Float'):
                sqltype += ' DEFAULT %s' % default
            # XXX ignore default for other type
            # this is expected for NOW / TODAY
    if creating:
        if rdef.uid:
            sqltype += ' PRIMARY KEY'
        elif rdef.cardinality[0] == '1':
            # don't set NOT NULL if backend isn't able to change it later
            if dbhelper.alter_column_support:
                sqltype += ' NOT NULL'
    # else we're getting sql type to alter a column, we don't want key / indexes
    # / null modifiers
    return sqltype


def type_from_constraints(dbhelper, etype, constraints, creating=True):
    """return a sql type string corresponding to the constraints"""
    constraints = list(constraints)
    unique, sqltype = False, None
    if etype == 'String':
        for constraint in constraints:
            if isinstance(constraint, SizeConstraint):
                if constraint.max is not None:
                    sqltype = 'varchar(%s)' % constraint.max
            elif isinstance(constraint, UniqueConstraint):
                unique = True
    if sqltype is None:
        sqltype = dbhelper.TYPE_MAPPING[etype]
    if creating and unique:
        sqltype += ' UNIQUE'
    return sqltype

# backward compat
_type_from_constraints = type_from_constraints


_SQL_SCHEMA = """
CREATE TABLE %(table)s (
  eid_from INTEGER NOT NULL,
  eid_to INTEGER NOT NULL,
  CONSTRAINT %(table)s_p_key PRIMARY KEY(eid_from, eid_to)
);

CREATE INDEX %(table)s_from_idx ON %(table)s(eid_from);
CREATE INDEX %(table)s_to_idx ON %(table)s(eid_to);"""


def rschema2sql(rschema):
    return _SQL_SCHEMA % {'table': '%s_relation' % rschema.type}


def droprschema2sql(rschema):
    """return sql to drop a relation type's table"""
    # not necessary to drop indexes, that's implictly done when dropping
    # the table
    return 'DROP TABLE %s_relation;' % rschema.type


def grant_schema(schema, user, set_owner=True, skip_entities=(), prefix=''):
    """write to the output stream a SQL schema to store the objects
    corresponding to the given schema
    """
    output = []
    w = output.append
    for etype in sorted(schema.entities()):
        eschema = schema.eschema(etype)
        if eschema.final or etype in skip_entities:
            continue
        w(grant_eschema(eschema, user, set_owner, prefix=prefix))
    for rtype in sorted(schema.relations()):
        rschema = schema.rschema(rtype)
        if rschema.final or rschema.inlined:
            continue
        w(grant_rschema(rschema, user, set_owner))
    return '\n'.join(output)


def grant_eschema(eschema, user, set_owner=True, prefix=''):
    output = []
    w = output.append
    etype = eschema.type
    if set_owner:
        w('ALTER TABLE %s%s OWNER TO %s;' % (prefix, etype, user))
    w('GRANT ALL ON %s%s TO %s;' % (prefix, etype, user))
    return '\n'.join(output)


def grant_rschema(rschema, user, set_owner=True):
    output = []
    if set_owner:
        output.append('ALTER TABLE %s_relation OWNER TO %s;' % (rschema.type, user))
    output.append('GRANT ALL ON %s_relation TO %s;' % (rschema.type, user))
    return '\n'.join(output)
