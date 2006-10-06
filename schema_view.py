"""an helper class to display a schema using ureports

:version: $Revision: 1.8 $  
:organization: Logilab
:copyright: 2003-2006 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__docformat__ = "restructuredtext en"
__metaclass__ = type

from logilab.common.ureports import Section, Title, Table, Link, Text, List

_ = getattr(__builtins__, '_', str)

class SchemaViewer:
    """return an ureport layout for some part of a schema"""

    def __init__(self, encoding='UTF-8'):
        self.encoding = encoding
        
    def visit_schema(self, schema, display_relations=0,
                     skiprels=(), skipmeta=True):
        """get a layout for a whole schema"""
        title = Title(_('Schema %s') % schema.name,
                      klass='titleUnderline')
        layout = Section(children=(title,))
        esection = Section(children=(Title(_('Entities'),
                                           klass='titleUnderline'),))
        layout.append(esection)
        entities = [eschema for eschema in schema.entities(schema=1)
                    if not eschema.is_final()]
        if skipmeta:
            entities = [eschema for eschema in entities
                        if not eschema.meta]
        keys = [(eschema.type, eschema) for eschema in entities]
        for key, eschema in sorted(keys):
            esection.append(self.visit_entityschema(eschema, skiprels))
        if display_relations:
            title = Title(_('Relations'), klass='titleUnderline')
            rsection = Section(children=(title,)) 
            layout.append(rsection)
            relations = [rschema for rschema in schema.relations(schema=1)
                         if not (rschema.is_final() or rschema.type in skiprels)]
            if skipmeta:
                relations = [rschema for rschema in relations
                             if not rschema.meta]
            keys = [(rschema.type, rschema) for rschema in relations]
            for key, rschema in sorted(keys):
                relstr = self.visit_relationschema(rschema)
                rsection.append(relstr)
        return layout

    def _entity_attributes_data(self, eschema):
        data = [_('attribute'), _('type'), _('default'), _('constraints')]
        for rschema, aschema in eschema.attribute_definitions():
            aname = rschema.type
            data.append(aname)
            data.append(aschema.type)
            data.append(self.to_string(eschema.default(aname)))
            constraints = rschema.rproperty(eschema.type, aschema.type,
                                            'constraints')
            data.append(', '.join([str(constr) for constr in constraints]))
        return data

    def eschema_link_url(self, eschema):
        return '#'+eschema.type
    def rschema_link_url(self, rschema):
        return '#'+rschema.type
    
    def visit_entityschema(self, eschema, skiprels=()):
        """get a layout for an entity schema"""
        layout = Section(title=_('Entity %s') % eschema.type, id=eschema.type,
                         klass='schema')
        data = self._entity_attributes_data(eschema)
        table = Table(cols=4, cheaders=1, children=data)
        layout.append(Section(children=(table,), klass='entityAttributes'))
        data = [_('relation'), _('type'), _('targets')]#, _('constraints')]
        for rschema, targetschemas, x in eschema.relation_definitions():
            if rschema.type in skiprels:
                continue
            rname = rschema.type
            data.append(Link(self.rschema_link_url(rschema), rname))
            data.append(Text(x))
            targets = List()
            for oeschema in targetschemas:
                targets.append(Link(self.eschema_link_url(oeschema),
                                    oeschema.type))
            data.append(targets)
            data.append(Text(constraints))
        table = Table(cols=3, cheaders=1, children=data)
        layout.append(Section(children=(table,), klass='entityAttributes'))
        return layout
    
    def visit_relationschema(self, rschema):
        """get a layout for a relation schema"""
        title = Link(self.rschema_link_url(rschema), rschema.type)
        stereotypes = []
        if rschema.meta:
            stereotypes.append('meta')
        if rschema.symetric:
            stereotypes.append('symetric')
        if rschema.inlined:
            stereotypes.append('inlined')
        if stereotypes:
            stereotypes = [self.stereotype(','.join(stereotypes))]
        
        layout = Section(title=title, children=stereotypes,
                         id=rschema.type, klass='schema')
        data = [_('from'), _('to')]
        schema = rschema.schema
        for from_type, to_types in rschema.association_types():
            for to_type in to_types:
                data.append(Link(self.eschema_link_url(schema[from_type]), from_type))
                data.append(Link(self.eschema_link_url(schema[to_type]), to_type))
        table = Table(cols=2, cheaders=1, children=data)
        layout.append(Section(children=(table,), klass='relationDefinition'))
        return layout

    def to_string(self, value):
        """used to converte arbitrary values to encoded string"""
        if isinstance(value, unicode):
            return value.encode(self.encoding, 'replace')
        return str(value)
