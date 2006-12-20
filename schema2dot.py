"""write a schema as a dot file


:organization: Logilab
:copyright: 2003-2006 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__docformat__ = "restructuredtext en"
__metaclass__ = type

import sys, os
import os.path as osp

from logilab.common.graph import DotBackend, GraphGenerator

from yams.reader import SchemaLoader

_ = getattr(__builtins__, '_', str)


class SchemaDotPropsHandler:
    def node_properties(self, eschema):
        """return default DOT drawing options for an entity schema"""
        return {'label' : eschema.type, 'shape' : "box",
                'fontname' : "Courier", 'style' : "filled"}
    def edge_properties(self, rschema):
        """return default DOT drawing options for a relation schema"""
        if rschema.symetric:
            return {'label': rschema.type, 'dir': 'both',
                    'color': '#887788', 'style': 'dashed'}
        return {'label': rschema.type, 'dir': 'forward',
                'color' : 'black', 'style' : 'filled'}

class SchemaVisitor:
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
        entities = [eschema for eschema in schema.entities(True)
                    if self.display_schema(eschema) and not eschema.type in skipetypes]
        self._eindex = dict([(e.type, e) for e in entities])

    def nodes(self):
        for eschema in self._eindex.values():
            yield eschema.type, eschema
            
    def edges(self):
        for rschema in self.schema.relations(schema=True):
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
               prophdlr=None):
    """write to the output stream a dot graph representing the given schema"""
    visitor = visitor or FullSchemaVisitor(schema, skipentities,
                                           skiprels, skipmeta)
    prophdlr = prophdlr or SchemaDotPropsHandler()
    if outputfile:
        schemaname = osp.splitext(osp.basename(outputfile))[0]
    else:
        schemaname = 'Schema'
    generator = GraphGenerator(DotBackend(schemaname,  'BT',
                                          ratio='compress', size='12,30'))
    return generator.generate(visitor, prophdlr, outputfile)


# XXX deprecated ##############################################################

class SchemaVisitor(SchemaDotPropsHandler):
    """used to dump a dot graph from a Schema instance
    
    NOTE: this is not a Visitor DP
    Would be nice to provide control on node/edges properties
    """
    def __init__(self, generator=None):
        self.generator = generator or DotBackend('Schema',  'BT',
                                                 ratio='compress', size='12,30')
        self._processed = set()
        self._eindex = None
        
    get_props_for_eschema = SchemaDotPropsHandler.node_properties
    get_props_for_rschema = SchemaDotPropsHandler.edge_properties

    def visit(self, schema, skipped_entities=(), skipped_relations=()):
        """browse schema nodes and generate dot instructions"""
        entities = [eschema for eschema in schema.entities()
                    if not (eschema.is_final() or eschema.type in skipped_entities)]
        self._eindex = dict([(e.type, e) for e in entities])
        for eschema in entities:
            self.visit_entity_schema(eschema)
        for rschema in schema.relations():
            if rschema.is_final() or rschema.type in skipped_relations:
                continue
            self.visit_relation_schema(rschema)

    def visit_entity_schema(self, eschema, hop=0):
        """dumps a entity node in the graph

        :param eschema: the entity's schema
        :type eschema: EntitySchema
        
        :param skipped_entities: a list of entities that shouldn't be displayed
        :param skipped_relations: a list of relations that shouldn't be
                                  displayed
        """
        etype = eschema.type
        if etype in self._processed:
            return
        self._processed.add(etype)
        nodeprops = self.get_props_for_eschema(eschema)
        self.generator.emit_node(str(etype), **nodeprops)

    def visit_relation_schema(self, rschema, comingfrom=None):
        """visit relations separately to handle easily symetric relations"""
        rtype = rschema.type
        if rtype in self._processed:
            return
        self._processed.add(rtype)
        if comingfrom:
            etype, target = comingfrom
        for subjtype, objtypes in rschema.associations():
            if self._eindex and not subjtype in self._eindex:
                continue
            for objtype in objtypes:
                if self._eindex and not objtype in self._eindex:
                    continue
                edgeprops = self.get_props_for_rschema(rschema)
                self.generator.emit_edge(str(subjtype), str(objtype), **edgeprops)




def run():
    """main routine when schema2dot is used as a script"""
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
    
