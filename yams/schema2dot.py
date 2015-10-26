# copyright 2004-2014 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of yams.
#
# yams is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option)
# any later version.
#
# yams is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with yams. If not, see <http://www.gnu.org/licenses/>.
"""Write a schema as a dot file.

"""
from __future__ import print_function
__docformat__ = "restructuredtext en"

import sys, os
import os.path as osp
from itertools import cycle

from logilab.common.graph import DotBackend, GraphGenerator

CARD_MAP = {'?': '0..1',
            '1': '1',
            '*': '0..n',
            '+': '1..n'}

class SchemaDotPropsHandler(object):
    def __init__(self, visitor):
        self.visitor = visitor
        # FIXME: colors are arbitrary
        self._colors = cycle( ('#aa0000', '#00aa00', '#0000aa',
                                 '#000000', '#888888') )
        self.nextcolor = lambda: next(self._colors)

    def node_properties(self, eschema):
        """return default DOT drawing options for an entity schema"""
        label = ['{',eschema.type,'|']
        label.append(r'\l'.join(rel.type for rel in eschema.ordered_relations()
                                if rel.final and self.visitor.should_display_attr(eschema, rel)))
        label.append(r'\l}') # trailing \l ensure alignement of the last one
        return {'label' : ''.join(label), 'shape' : "record",
                'fontname' : "Courier", 'style' : "filled"}

    def edge_properties(self, rschema, subjnode, objnode):
        """return default DOT drawing options for a relation schema"""
        # rschema can be none if the subject is a specialization of the object
        # we get there because we want to draw a specialization arrow anyway
        if rschema is None:
            kwargs = {'label': 'Parent class',
                      'color' : 'grey',  'style' : 'filled',
                      'arrowhead': 'empty'}
        elif rschema.symmetric:
            # symmetric rels are handled differently, let yams decide what's best
            kwargs = {'label': rschema.type,
                      'color': '#887788', 'style': 'dashed',
                      'dir': 'both', 'arrowhead': 'normal', 'arrowtail': 'normal'}
        else:
            kwargs = {'label': rschema.type,
                      'color' : 'black',  'style' : 'filled'}
            rdef = rschema.rdef(subjnode, objnode)
            composite = rdef.composite
            if rdef.composite == 'subject':
                kwargs['arrowhead'] = 'none'
                kwargs['arrowtail'] = 'diamond'
            elif rdef.composite == 'object':
                kwargs['arrowhead'] = 'diamond'
                kwargs['arrowtail'] = 'none'
            else:
                kwargs['arrowhead'] = 'normal'
                kwargs['arrowtail'] = 'none'
            # UML like cardinalities notation, omitting 1..1
            if rdef.cardinality[1] != '1':
                kwargs['taillabel'] = CARD_MAP[rdef.cardinality[1]]
            if rdef.cardinality[0] != '1':
                kwargs['headlabel'] = CARD_MAP[rdef.cardinality[0]]
            kwargs['color'] = self.nextcolor()
        kwargs['fontcolor'] = kwargs['color']
        # dot label decoration is just awful (1 line underlining the label
        # + 1 line going to the closest edge spline point)
        kwargs['decorate'] = 'false'
        #kwargs['labelfloat'] = 'true'
        return kwargs


class SchemaVisitor(object):
    def __init__(self, skiptypes=()):
        self._done = set()
        self.skiptypes = skiptypes
        self._nodes = None
        self._edges = None

    def should_display_schema(self, erschema):
        return not (erschema.final or erschema in self.skiptypes)

    def should_display_attr(self, eschema, rschema):
        return not rschema in self.skiptypes

    def display_rel(self, rschema, setype, tetype):
        if (rschema, setype, tetype) in self._done:
            return False
        self._done.add((rschema, setype, tetype))
        if rschema.symmetric:
            self._done.add((rschema, tetype, setype))
        return True

    def nodes(self):
        return self._nodes

    def edges(self):
        return self._edges


class FullSchemaVisitor(SchemaVisitor):
    def __init__(self, schema, skiptypes=()):
        super(FullSchemaVisitor, self).__init__(skiptypes)
        self.schema = schema
        self._eindex = None
        entities = [eschema for eschema in schema.entities()
                    if self.should_display_schema(eschema)]
        self._eindex = dict([(e.type, e) for e in entities])

    def nodes(self):
        for eschema in sorted(self._eindex.values(), key=lambda x: x.type):
            yield eschema.type, eschema

    def edges(self):
        # Entities with inheritance relations.
        for eschema in sorted(self._eindex.values(), key=lambda x: x.type):
            if eschema.specializes():
                yield str(eschema), str(eschema.specializes()), None
        # Subject/object relations.
        for rschema in sorted(self.schema.relations(), key=lambda x: x.type):
            if not self.should_display_schema(rschema):
                continue
            for setype, tetype in sorted(rschema.rdefs, key=lambda x: (x[0].type, x[1].type)):
                if not (setype in self._eindex and tetype in self._eindex):
                    continue
                if not self.display_rel(rschema, setype, tetype):
                    continue
                yield str(setype), str(tetype), rschema


class OneHopESchemaVisitor(SchemaVisitor):
    def __init__(self, eschema, skiptypes=()):
        super(OneHopESchemaVisitor, self).__init__(skiptypes)
        nodes = set()
        edges = set()
        nodes.add((eschema.type, eschema))
        for rschema in eschema.subject_relations():
            if not self.should_display_schema(rschema):
                continue
            for teschema in rschema.objects(eschema.type):
                nodes.add((teschema.type, teschema))
                if not self.display_rel(rschema, eschema.type, teschema.type):
                    continue
                edges.add((eschema.type, teschema.type, rschema))
        for rschema in eschema.object_relations():
            if not self.should_display_schema(rschema):
                continue
            for teschema in rschema.subjects(eschema.type):
                nodes.add((teschema.type, teschema))
                if not self.display_rel(rschema, teschema.type, eschema.type):
                    continue
                edges.add((teschema.type, eschema.type, rschema))
        # Inheritance relations.
        if eschema.specializes():
            nodes.add((eschema.specializes().type, eschema.specializes()))
            edges.add((eschema.type, eschema.specializes().type, None))
        if eschema.specialized_by():
            for pschema in eschema.specialized_by():
                nodes.add((pschema.type, pschema))
                edges.add((pschema.type, eschema.type, None))
        self._nodes = nodes
        self._edges = edges


class OneHopRSchemaVisitor(SchemaVisitor):
    def __init__(self, rschema, skiptypes=()):
        super(OneHopRSchemaVisitor, self).__init__(skiptypes)
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


def schema2dot(schema=None, outputfile=None, skiptypes=(),
               visitor=None, prophdlr=None, size=None):
    """write to the output stream a dot graph representing the given schema"""
    visitor = visitor or FullSchemaVisitor(schema, skiptypes)
    prophdlr = prophdlr or SchemaDotPropsHandler(visitor)
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
    loader = SchemaLoader()
    try:
        schema_dir = sys.argv[1]
    except IndexError:
        print("USAGE: schema2dot SCHEMA_DIR [OUTPUT FILE]")
        sys.exit(1)
    if len(sys.argv) > 2:
        outputfile = sys.argv[2]
    else:
        outputfile = None
    schema = loader.load([schema_dir], 'Test')
    schema2dot(schema, outputfile)


if __name__ == '__main__':
    run()
