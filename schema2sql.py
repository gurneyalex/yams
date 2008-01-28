"""write a schema as sql

:organization: Logilab
:copyright: 2004-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__docformat__ = "restructuredtext en"
__metaclass__ = type

from logilab.common.compat import sorted

from yams.constraints import SizeConstraint, UniqueConstraint


def schema2sql(dbhelper, schema, skip_entities=(), skip_relations=()):
    """write to the output stream a SQL schema to store the objects
    corresponding to the given schema
    """
    output = []
    w = output.append
    for etype in sorted(schema.entities()):
        eschema = schema.eschema(etype)
        if eschema.is_final() or eschema.type in skip_entities:
            continue
        w(eschema2sql(dbhelper, eschema, skip_relations))
    for rtype in sorted(schema.relations()):
        rschema = schema.rschema(rtype)
        if rschema.is_final() or rschema.inlined:
            continue
        w(rschema2sql(rschema))
    return '\n'.join(output)


def dropschema2sql(schema, skip_entities=(), skip_relations=()):
    """write to the output stream a SQL schema to store the objects
    corresponding to the given schema
    """
    output = []
    w = output.append
    for etype in sorted(schema.entities()):
        eschema = schema.eschema(etype)
        if eschema.is_final() or eschema.type in skip_entities:
            continue
        w(dropeschema2sql(eschema, skip_relations))
    for rtype in sorted(schema.relations()):
        rschema = schema.rschema(rtype)
        if rschema.is_final() or rschema.inlined:
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

def dropeschema2sql(eschema, skip_relations=()):
    """return sql to drop an entity type's table"""
    # not necessary to drop indexes, that's implictly done when dropping
    # the table
    return 'DROP TABLE %s;' % eschema.type

def eschema2sql(dbhelper, eschema, skip_relations=()):
    """write an entity schema as SQL statements to stdout"""
    output = []
    w = output.append
    etype = eschema.type
    w('CREATE TABLE %s(' % etype)
    attrs = eschema_attrs(eschema, skip_relations)
    # XXX handle objectinline physical mode
    for i in xrange(len(attrs)):
        rschema, attrschema = attrs[i]
        if attrschema is not None:
            sqltype = aschema2sql(dbhelper, eschema, rschema, attrschema, ' ')
        else: # inline relation
            # XXX integer is ginco specific
            sqltype = 'integer'
        if i == len(attrs) - 1:
            w(' %s %s' % (rschema.type, sqltype))
        else:
            w(' %s %s,' % (rschema.type, sqltype))
    w(');')
    # create index
    for i in xrange(len(attrs)):
        rschema, attrschema = attrs[i]
        if attrschema is None or eschema.rproperty(rschema.type, 'indexed'):
            w(dbhelper.sql_create_index(etype, rschema.type))
    w('')
    return '\n'.join(output)

    
def aschema2sql(dbhelper, eschema, rschema, aschema, indent=''):
    """write an attribute schema as SQL statements to stdout"""
    attr = rschema.type
    constraints = rschema.rproperty(eschema.type, aschema.type, 'constraints')
    sqltype = _type_from_constraints(dbhelper, aschema.type, constraints)
    default = eschema.default(attr)
    if default is not None:
        if aschema.type == 'Boolean':
            sqltype += ' DEFAULT %s' % (default and 'true' or 'false')
        elif aschema.type == 'String':
            sqltype += ' DEFAULT %r' % str(default)
        elif aschema.type == 'Int':
            sqltype += ' DEFAULT %s' % default
    if eschema.rproperty(attr, 'uid'):
        sqltype += ' PRIMARY KEY'
    elif rschema.rproperty(eschema.type, aschema.type, 'cardinality')[0] == '1':
        sqltype += ' NOT NULL'
    return sqltype

    
def _type_from_constraints(dbhelper, etype, constraints):
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
    if unique:
        sqltype += ' UNIQUE'
    return sqltype
    

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


def grant_schema(schema, user, set_owner=True, skip_entities=()):
    """write to the output stream a SQL schema to store the objects
    corresponding to the given schema
    """
    output = []
    w = output.append
    for etype in sorted(schema.entities()):
        eschema = schema.eschema(etype)
        if eschema.is_final() or etype in skip_entities:
            continue
        w(grant_eschema(eschema, user, set_owner))
    for rtype in sorted(schema.relations()):
        rschema = schema.rschema(rtype)
        if rschema.is_final() or rschema.inlined:
            continue
        w(grant_rschema(rschema, user, set_owner))
    return '\n'.join(output)

def grant_eschema(eschema, user, set_owner=True):
    output = []
    w = output.append
    etype = eschema.type
    if set_owner:
        w('ALTER TABLE %s OWNER TO %s;' % (etype, user))
    w('GRANT ALL ON %s TO %s;' % (etype, user))
    return '\n'.join(output)

def grant_rschema(rschema, user, set_owner=True):
    output = []
    if set_owner:
        output.append('ALTER TABLE %s_relation OWNER TO %s;' % (rschema.type, user))
    output.append('GRANT ALL ON %s_relation TO %s;' % (rschema.type, user))
    return '\n'.join(output)
