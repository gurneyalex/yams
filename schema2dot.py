"""write a schema as a dot file

(adapted from pypy/translator/tool/make_dot.py)
:version: $Revision: 1.6 $  
:organization: Logilab
:copyright: 2003-2005 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: schema2dot.py,v 1.6 2006-03-28 23:26:44 syt Exp $"
__docformat__ = "restructuredtext en"
__metaclass__ = type

import sys, os
import os.path as osp

from logilab.common.compat import set

from yams.reader import SchemaLoader

_ = getattr(__builtins__, '_', str)

class DotGenerator:
    """Dot File generator"""
    def __init__(self, graphname, rankdir=None, size=None, ratio=None):
        self.graphname = graphname
        self.lines = []
        self._source = None
        self.emit("digraph %s {" % graphname)
        if rankdir:
            self.emit('rankdir=%s' % rankdir)
        if ratio:
            self.emit('ratio=%s' % ratio)
        if size:
            self.emit('size="%s"' % size)

    def get_source(self):
        """returns self._source"""
        if self._source is None:
            self.emit("}")
            self._source = '\n'.join(self.lines)
            del self.lines
        return self._source

    source = property(get_source)
    
    def generate(self, outputfile=None, dotfile=None):
        """generates a graph file
        :param target: output format ('png', 'ps', etc.). If None,
                       the raw dot source will be returned
        :return: a path to the generated file
        """
        if outputfile is not None:
            storedir, basename, target = target_info_from_filename(outputfile)
        else:
            storedir = '/tmp'
            basename = '%s.png' % (self.graphname)
            target = 'png'
            outputfile = osp.join(storedir, basename)
        dotfile = dotfile or ('%s.dot' % self.graphname)
        dot_sourcepath = osp.join(storedir, dotfile)
        pdot = file(dot_sourcepath, 'w')
        pdot.write(self.source)
        pdot.close()
        os.system('dot -T%s %s -o%s' % (target, dot_sourcepath, outputfile))
        return outputfile

    def emit(self, line):
        """adds <line> to final output"""
        self.lines.append(line)

    def emit_edge(self, name1, name2, **props):
        """emits edge from <name1> to <name2>
        
        authorized props: label, style, color, dir, weight
        """
        attrs = ['%s="%s"' % (prop, value) for prop, value in props.items()]
        self.emit('edge [%s];' % ", ".join(attrs))
        self.emit('%s -> %s' % (name1, name2))

    def emit_node(self, name, **props):
        """authorized props: shape, label, color, fillcolor, style"""
        attrs = ['%s="%s"' % (prop, value) for prop, value in props.items()]
        self.emit('%s [%s];' % (name, ", ".join(attrs)))


class SchemaVisitor:
    """used to dump a dot graph from a Schema instance
    
    NOTE: this is not a Visitor DP
    Would be nice to provide control on node/edges properties
    """
    def __init__(self, generator=None):
        self.generator = generator or DotGenerator('Schema',  'BT',
                                                   ratio='compress', size='12,30')
        self.processed_entities = set()
        self.processed_relations = set()

    def get_props_for_eschema(self, eschema):
        """return default drawing options for <eschema>

        override this method if you want to customize node properties
        """
        return {'label' : eschema.type,
                'fontname' : "Courier",
                'shape' : "box",
                'style' : "filled"
                }

    def get_props_for_rschema(self, rschema):
        """return default drawing options for <rschema>

        override this method if you want to customize node properties
        """
        if rschema.symetric:
            return {'label' :  rschema.type, 'dir' : "both"}
        else:
            return {'label' :  rschema.type, 'dir' : "forward"}

    def visit(self, schema, skipped_entities=(), skipped_relations=()):
        """browse schema nodes and generate dot instructions"""
        for eschema in schema.entities(schema=True):
            self.visit_entity_schema(eschema, skipped_entities,
                                     skipped_relations)
        for rschema in schema.relations(schema=True):
            self.visit_relation_schema(rschema, skipped_entities,
                                       skipped_relations)


    def visit_entity_schema(self, eschema, skipped_entities=(),
                            skipped_relations=()):
        """dumps a entity node in the graph

        :param eschema: the entity's schema
        :type eschema: EntitySchema
        
        :param skipped_entities: a list of entities that shouldn't be displayed
        :param skipped_relations: a list of relations that shouldn't be
                                  displayed
        """
        etype = eschema.type
        if etype in self.processed_entities or etype in skipped_entities or \
               eschema.is_final():
            return
        self.processed_entities.add(etype)
        nodeprops = self.get_props_for_eschema(eschema)
        self.generator.emit_node(etype, **nodeprops)
        # XXX try to have related entities near ?
        for rschema, targetschemas, x in eschema.relation_definitions():
            if rschema.type in skipped_relations:
                continue
            if x == 'object':
                # display object related entities latter
                continue
            for destschema in targetschemas:
                if destschema.type in skipped_entities:
                    continue
                self.visit_entity_schema(destschema, skipped_entities,
                                         skipped_relations)

    def visit_relation_schema(self, rschema, skipped_entities=(),
                              skipped_relations=()):
        """visit relations separately to handle easily symetric relations"""
        rtype = rschema.type
        if rschema.is_final() or rtype in skipped_relations:
            return
        for subjtype, objtypes in rschema.association_types():
            if subjtype in skipped_entities:
                continue
            for objtype in objtypes:
                triplet = (subjtype, rtype, objtype)
                if objtype in skipped_entities or \
                       triplet in self.processed_relations:
                    continue
                edgeprops = self.get_props_for_rschema(rschema)
                self.generator.emit_edge(subjtype, objtype, **edgeprops)
                self.processed_relations.add(triplet)
                if rschema.symetric:
                    self.processed_relations.add((objtype, rtype, subjtype))


def schema2dot(schema, outputfile=None, skipped_entities=(),
               skipped_relations=()):
    """write to the output stream a dot graph"""
    visitor = SchemaVisitor()
    visitor.visit(schema, skipped_entities, skipped_relations)
    generator = visitor.generator
    return generator.generate(outputfile)


## Utilities #####################################

def escape(value):
    """make <value> usable in a dot file"""
    lines = [line.replace('"', '\\"') for line in value.split('\n')]
    data = '\\l'.join(lines)
    return '\\n' + data

def target_info_from_filename(filename):
    """transforms /some/path/foo.png into ('/some/path', 'foo.png', 'png')"""
    abspath = osp.abspath(filename)
    basename = osp.basename(filename)
    storedir = osp.dirname(abspath)
    target = filename.split('.')[-1]
    return storedir, basename, target
   

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
    
