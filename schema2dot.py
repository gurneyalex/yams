"""Write a schema as a dot file.

:organization: Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: General Public License version 2 - http://www.gnu.org/licenses
"""

__docformat__ = "restructuredtext en"
__metaclass__ = type

import sys, os
import os.path as osp

from logilab.common.graph import DotBackend, GraphGenerator

CARD_MAP = {'?': '0..1',
            '1': '1',
            '*': '0..n',
            '+': '1..n'}

class SchemaDotPropsHandler(object):
    def display_attr(self, rschema):
        return not rschema.meta
    
    def node_properties(self, eschema):
        """return default DOT drawing options for an entity schema"""
        label = ['{',eschema.type,'|']
        label.append(r'\l'.join(rel.type for rel in eschema.ordered_relations()
                                if rel.final and self.display_attr(rel)))
        label.append(r'\l}') # trailing \l ensure alignement of the last one
        return {'label' : ''.join(label), 'shape' : "record",
                'fontname' : "Courier", 'style' : "filled"}
    
    def edge_properties(self, rschema, subjnode, objnode):
        """return default DOT drawing options for a relation schema"""
        if rschema.symetric:
            kwargs = {'label': rschema.type,
                      'color': '#887788', 'style': 'dashed',
                      'dir': 'both', 'arrowhead': 'normal', 'arrowtail': 'normal'}
        else:
            kwargs = {'label': rschema.type,
                      'color' : 'black',  'style' : 'filled'}
            composite = rschema.rproperty(subjnode, objnode, 'composite')
            if composite == 'subject':
                kwargs['arrowhead'] = 'none'
                kwargs['arrowtail'] = 'diamond'
            elif composite == 'object':
                kwargs['arrowhead'] = 'diamond'
                kwargs['arrowtail'] = 'none'
            else:
                kwargs['arrowhead'] = 'normal'
                kwargs['arrowtail'] = 'none'
            cards = rschema.rproperty(subjnode, objnode, 'cardinality')
            # UML like cardinalities notation, omitting 1..1
            if cards[1] != '1':
                kwargs['taillabel'] = CARD_MAP[cards[1]]
            if cards[0] != '1':
                kwargs['headlabel'] = CARD_MAP[cards[0]]
        
        kwargs['decorate'] = 'true'
        kwargs['color'] = 'grey'
        #kwargs['labelfloat'] = 'true'
        return kwargs


class SchemaVisitor(object):
    def __init__(self, skipmeta=True):
        self._done = set()
        self.skipmeta = skipmeta
        self._nodes = None
        self._edges = None
        
    def display_schema(self, erschema):
        return not (erschema.is_final() or (self.skipmeta and erschema.meta))

    def display_rel(self, rschema, setype, tetype):
        if (rschema, setype, tetype) in self._done:
            return False
        self._done.add((rschema, setype, tetype))
        if rschema.symetric:
            self._done.add((rschema, tetype, setype))
        return True

    def nodes(self):
        # yield non meta first then meta to group them on the graph
        for nodeid, node in self._nodes:
            if not node.meta:
                yield nodeid, node
        for nodeid, node in self._nodes:
            if node.meta:
                yield nodeid, node
            
    def edges(self):
        return self._edges

    
class FullSchemaVisitor(SchemaVisitor):
    def __init__(self, schema, skipetypes=(), skiprels=(), skipmeta=True):
        super(FullSchemaVisitor, self).__init__(skipmeta)
        self.schema = schema
        self.skiprels = skiprels
        self._eindex = None
        entities = [eschema for eschema in schema.entities()
                    if self.display_schema(eschema) and not eschema.type in skipetypes]
        self._eindex = dict([(e.type, e) for e in entities])

    def nodes(self):
        for eschema in self._eindex.values():
            yield eschema.type, eschema
            
    def edges(self):
        for rschema in self.schema.relations():
            if rschema.is_final() or rschema.type in self.skiprels:
                continue
            for setype, tetype in rschema._rproperties:
                if not (setype in self._eindex and tetype in self._eindex):
                    continue
                if not self.display_rel(rschema, setype, tetype):
                    continue
                yield str(setype), str(tetype), rschema

    
class OneHopESchemaVisitor(SchemaVisitor):
    def __init__(self, eschema, skiprels=()):
        super(OneHopESchemaVisitor, self).__init__(skipmeta=False)
        nodes = set()
        edges = set()
        nodes.add((eschema.type, eschema))
        for rschema in eschema.subject_relations():
            if rschema.is_final() or rschema.type in skiprels:
                continue
            for teschema in rschema.objects(eschema.type):
                nodes.add((teschema.type, teschema))
                if not self.display_rel(rschema, eschema.type, teschema.type):
                    continue                
                edges.add((eschema.type, teschema.type, rschema))
        for rschema in eschema.object_relations():
            if rschema.type in skiprels:
                continue
            for teschema in rschema.subjects(eschema.type):
                nodes.add((teschema.type, teschema))
                if not self.display_rel(rschema, teschema.type, eschema.type):
                    continue                
                edges.add((teschema.type, eschema.type, rschema))
        self._nodes = nodes
        self._edges = edges


class OneHopRSchemaVisitor(SchemaVisitor):
    def __init__(self, rschema, skiprels=()):
        super(OneHopRSchemaVisitor, self).__init__(skipmeta=False)
        nodes = set()
        edges = set()
        done = set()
        for seschema in rschema.subjects():
            nodes.add((seschema.type, seschema))
            for oeschema in rschema.objects(seschema.type):
                nodes.add((oeschema.type, oeschema))
                if not self.display_rel(rschema, seschema.type, oeschema.type):
                    continue                                
                edges.add((seschema.type, oeschema.type, rschema))
        self._nodes = nodes
        self._edges = edges


def schema2dot(schema=None, outputfile=None, skipentities=(),
               skiprels=(), skipmeta=True, visitor=None,
               prophdlr=None, size=None):
    """write to the output stream a dot graph representing the given schema"""
    visitor = visitor or FullSchemaVisitor(schema, skipentities,
                                           skiprels, skipmeta)
    prophdlr = prophdlr or SchemaDotPropsHandler()
    if outputfile:
        schemaname = osp.splitext(osp.basename(outputfile))[0]
    else:
        schemaname = 'Schema'
    generator = GraphGenerator(DotBackend(schemaname, 'BT',
                                          ratio='compress', size=size,
                                          renderer='dot',
                                          additionnal_param={
                                              'overlap':'false',
                                              'splines':'true',
                                              #'polylines':'true',
                                              'sep':'0.2'
                                          }))
    return generator.generate(visitor, prophdlr, outputfile)


def run():
    """main routine when schema2dot is used as a script"""
    from yams.reader import SchemaLoader
    class DefaultHandler:
        """we need to handle constraints while loading schema"""
        def __getattr__(self, dummy):
            return lambda *args: 'abcdef'
    loader = SchemaLoader()
    try:
        schema_dir = sys.argv[1]
    except IndexError:
        print "USAGE: schema2dot SCHEMA_DIR [OUTPUT FILE]"
        sys.exit(1)
    if len(sys.argv) > 2:
        outputfile = sys.argv[2]
    else:
        outputfile = None
    schema = loader.load(schema_dir, 'Test', DefaultHandler())
    schema2dot(schema, outputfile)


if __name__ == '__main__':
    run()
    
