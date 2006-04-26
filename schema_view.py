"""an helper class to display a schema using ureports

:version: $Revision: 1.8 $  
:organization: Logilab
:copyright: 2003-2005 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = '$Id: schema_view.py,v 1.8 2006-03-30 19:50:56 syt Exp $'
__docformat__ = "restructuredtext en"
__metaclass__ = type

from logilab.common.ureports import Section, Title, Table, Link, Text, List

_ = getattr(__builtins__, '_', str)

class SchemaViewer:
    """return an ureport layout for some part of a schema"""

    def __init__(self, encoding='UTF-8'):
        self.encoding = encoding
        
    def visit_schema(self, schema, display_relations=0):
        """get a layout for a whole schema"""
        title = Title(_('Schema %s') % schema.name,
                      klass='titleUnderline')
        layout = Section(children=(title,))
        entities = Section(children=(Title(_('Entities'),
                                           klass='titleUnderline'),))
        layout.append(entities)
        keys = [eschema.type for eschema in schema.entities(schema=1)
                if not eschema.is_final()]
        keys.sort()
        for key in keys:
            entities.append(self.visit_entityschema(schema.eschema(key)))
        if display_relations:
            title = Title(_('Relations'), klass='titleUnderline')
            relations = Section(children=(title,)) 
            layout.append(relations)
            keys = [rschema.type for rschema in schema.relations(schema=1)
                    if not rschema.is_final()]
            keys.sort()
            for key in keys:
                relstr = self.visit_relationschema(schema.rschema(key))
                relations.append(relstr)
        return layout
    
    def visit_entityschema(self, eschema):
        """get a layout for an entity schema"""
        layout = Section(title=_('Entity %s') % eschema.type, id=eschema.type,
                         klass='schema')
        data = [_('ATTRIBUTE'), _('TYPE'), _('DEFAULT'), _('CONSTRAINTS')]
        for rschema, aschema in eschema.attribute_definitions():
            aname = rschema.type
            data.append(aname)
            data.append(aschema.type)
            data.append(self.to_string(eschema.default(aname)))
            constraints = rschema.rproperty(eschema.type, aschema.type, 'constraints')
            data.append(', '.join([str(constr) for constr in constraints]))
            rschema = eschema.subject_relation(aname)
        table = Table(cols=4, cheaders=1, children=data)
        layout.append(Section(children=(table,), klass='entityAttributes'))
        data = [_('RELATION'), _('TYPE'), _('TARGETS')]#, _('CONSTRAINTS')]
        for rschema, targetschemas, x in eschema.relation_definitions():
            rname = rschema.type
            data.append(Link('#'+rname, rname))
            data.append(Text(x))
            targets = List()
            for oeschema in targetschemas:
                targets = List()
                targets.append(Link('#'+oeschema.type, oeschema.type))
            data.append(targets)
            data.append(Text(constraints))
        table = Table(cols=3, cheaders=1, children=data)
        layout.append(Section(children=(table,), klass='entityAttributes'))
        return layout
    
    def visit_relationschema(self, rschema):
        """get a layout for a relation schema"""
        title = _('Relation %s') % rschema.type
        physicalmode = rschema.physical_mode()
        if physicalmode:
            title += ' (%s)' % _(physicalmode)
        layout = Section(title=title, id=rschema.type, klass='schema')
        data = [_('FROM'), _('TO')]
        for from_type, to_types in rschema.association_types():
            for to_type in to_types:
                data.append(Link('#'+from_type, from_type))
                data.append(Link('#'+to_type, to_type))
        table = Table(cols=2, cheaders=1, children=data)
        layout.append(Section(children=(table,), klass='relationDefinition'))
        return layout

    def to_string(self, value):
        """used to converte arbitrary values to encoded string"""
        if isinstance(value, unicode):
            return value.encode(self.encoding, 'replace')
        return str(value)
