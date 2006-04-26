"""write a schema as sql

:version: $Revision: 1.15 $  
:organization: Logilab
:copyright: 2003-2005 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: schema2sql.py,v 1.15 2006-03-30 19:50:56 syt Exp $"
__docformat__ = "restructuredtext en"
__metaclass__ = type

from logilab.common.compat import sorted

from yams.constraints import SizeConstraint, UniqueConstraint


TYPE_MAPPING = {
    'String' : 'text',
    'Int' : 'integer',
    'Float' : 'float',
    'Boolean' : 'boolean',
    'Date' : 'date', 
    'Time' : 'time', 
    'Datetime' : 'timestamp',
    'Password' : 'varchar(24)',
    'Bytes' : 'bytea',         # FIXME: pgsql specific
    }


def schema2sql(schema, skip_entities=(), skip_relations=(), drop=False):
    """write to the output stream a SQL schema to store the objects
    corresponding to the given schema
    """
    output = []
    w = output.append
    for etype in sorted(schema.entities()):
        eschema = schema.eschema(etype)
        if eschema.is_final() or eschema.type in skip_entities:
            continue
        w(eschema2sql(eschema, skip_relations, drop))
    for rtype in sorted(schema.relations()):
        rschema = schema.rschema(rtype)
        if rschema.is_final() or rschema.physical_mode() == 'subjectinline':
            continue
        w(rschema2sql(rschema, drop))
    return '\n'.join(output)


def eschema2sql(eschema, skip_relations=(), drop=False):
    """write an entity schema as SQL statements to stdout"""
    output = []
    w = output.append
    etype = eschema.type
    if drop:
        w('DROP TABLE %s;' % etype)
    w('CREATE TABLE %s(' % etype)
    attrs = [attrdef for attrdef in eschema.attribute_definitions()
             if not attrdef[0].type in skip_relations]
    attrs += [(rschema, None)
              for rschema in eschema.subject_relations()
              if not rschema.final and rschema.physical_mode() == 'subjectinline']
    # XXX handle objectinline physical mode
    for i in xrange(len(attrs)):
        rschema, attrschema = attrs[i]
        if attrschema is not None:
            sqltype = aschema2sql(eschema, rschema, attrschema, ' ')
        else: # inline relation
            # XXX integer is ginco specific
            sqltype = 'integer'
            # XXX disabled since we may want to overrides this constraint
            #for oschema in eschema.destination_types(rschema.type, schema=True):
            #    card = rschema.rproperty(eschema.type, oschema.type, 'cardinality')
            #    if card[0] != '1':
            #        break
            #else:
            #    sqltype += ' NOT NULL'
        if i == len(attrs) - 1:
            w(' %s %s' % (rschema.type, sqltype))
        else:
            w(' %s %s,' % (rschema.type, sqltype))
    w(');')
    # create index
    for i in xrange(len(attrs)):
        rschema, attrschema = attrs[i]
        if attrschema is None or eschema.rproperty(rschema.type, 'indexed'):
            w('CREATE INDEX %s_%s_idx ON %s (%s);' % (
                etype.lower(), rschema.type.lower(), etype, rschema.type))
    w('')
    return '\n'.join(output)

    
def aschema2sql(eschema, rschema, aschema, indent=''):
    """write an attribute schema as SQL statements to stdout"""
    attr = rschema.type
    constraints = rschema.rproperty(eschema.type, aschema.type, 'constraints')
    sqltype = _type_from_constraints(aschema.type, constraints)
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

    
def _type_from_constraints(etype, constraints):
    """return a sql type string corresponding to the constraints"""
    constraints = list(constraints)
    sqltype = TYPE_MAPPING[etype]
    unique = False
    if sqltype == 'text':
        for constraint in constraints:
            if isinstance(constraint, SizeConstraint):
                if constraint.max is not None:
                    sqltype = 'varchar(%s)' % constraint.max
            elif isinstance(constraint, UniqueConstraint):
                unique = True
    if unique:
        sqltype += ' UNIQUE'
    return sqltype
    

_SQL_SCHEMA = """%%s
CREATE TABLE %(table)s (
  eid_from INTEGER NOT NULL,
  eid_to INTEGER NOT NULL,
  CONSTRAINT %(table)s_p_key PRIMARY KEY(eid_from, eid_to),
  CONSTRAINT %(table)s_fkey1 FOREIGN KEY (eid_from) REFERENCES entities (eid) ON DELETE CASCADE,
  CONSTRAINT %(table)s_fkey2 FOREIGN KEY (eid_to) REFERENCES entities (eid) ON DELETE CASCADE
);

%%s
CREATE INDEX %(table)s_from_idx ON %(table)s (eid_from);
%%s
CREATE INDEX %(table)s_to_idx ON %(table)s (eid_to);"""

def rschema2sql(rschema, drop=False):
    kwargs = {'table': '%s_relation' % rschema.type}
    result = _SQL_SCHEMA % kwargs
    if drop:
        result %= ('DROP TABLE %(table)s;',
                   'DROP INDEX %(table)s_from_idx;',
                   'DROP INDEX %(table)s_to_idx;')
        result %= kwargs
    else:
        result %= ('', '', '')
    return result


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
        if rschema.is_final() or rschema.physical_mode() == 'subjectinline':
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
