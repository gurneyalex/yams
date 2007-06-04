"""unittests for schema2dot"""

from logilab.common.testlib import TestCase, unittest_main
from logilab.common.compat import set

from yams import SchemaLoader
from yams import schema2dot

import os.path as osp

DATADIR = osp.abspath(osp.join(osp.dirname(__file__),'data'))

class DummyDefaultHandler:

    def default_modname(self):
        return 'yo'
    
    def vocabulary_license(self):
        return ['GPL', 'ZPL']
    
    def vocabulary_debian_handler(self):
        return ['machin', 'bidule']

schema = SchemaLoader().load(DATADIR, default_handler=DummyDefaultHandler())

DOT_SOURCE = """digraph "Schema" {
rankdir=BT
ratio=compress
size="12,30"
"Person" [label="Person"];
"Societe" [label="Societe"];
edge [label="travaille"];
"Person" -> "Societe"
}"""


class MyVisitor(schema2dot.SchemaVisitor):
    """customize drawing options for better control"""
    def get_props_for_eschema(self, eschema):
        return {'label' : eschema.type}

    def get_props_for_rschema(self, rschema):
        return {'label' : rschema.type}

class DotTC(TestCase):
    
    def test_schema2dot(self):
        """tests dot conversion without attributes information"""
        wanted_entities = set(('Person', 'Societe'))
        skipped_entities = set(schema.entities()) - wanted_entities
        visitor = MyVisitor()
        visitor.visit(schema, skipped_entities=skipped_entities)
        self.assertEquals(DOT_SOURCE, visitor.generator.source)
        
if __name__ == '__main__':
    unittest_main()
