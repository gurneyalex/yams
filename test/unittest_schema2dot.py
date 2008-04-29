"""unittests for schema2dot"""

import os

from logilab.common.testlib import TestCase, unittest_main
from logilab.common.compat import set

from yams.reader import SchemaLoader
from yams import schema2dot

import os.path as osp

DATADIR = osp.abspath(osp.join(osp.dirname(__file__), 'data'))

class DummyDefaultHandler:

    def default_modname(self):
        return 'yo'
    
    def vocabulary_license(self):
        return ['GPL', 'ZPL']
    
    def vocabulary_debian_handler(self):
        return ['machin', 'bidule']

schema = SchemaLoader().load([DATADIR], default_handler=DummyDefaultHandler())

DOT_SOURCE = """digraph "toto" {
rankdir=BT
ratio=compress
charset="utf-8"
"Person" [shape="box", fontname="Courier", style="filled", label="Person"];
"Societe" [shape="box", fontname="Courier", style="filled", label="Societe"];
edge [taillabel="0..n", style="filled", arrowhead="open", color="black", label="travaille", headlabel="0..n", arrowtail="none"];
"Person" -> "Societe"
}"""


class DotTC(TestCase):
    
    def test_schema2dot(self):
        """tests dot conversion without attributes information"""
        wanted_entities = set(('Person', 'Societe'))
        skipped_entities = set(schema.entities()) - wanted_entities
        schema2dot.schema2dot(schema, '/tmp/toto.dot', skipentities=skipped_entities)
        generated = open('/tmp/toto.dot').read()
        os.remove('/tmp/toto.dot')
        self.assertTextEquals(DOT_SOURCE, generated)
        
if __name__ == '__main__':
    unittest_main()
