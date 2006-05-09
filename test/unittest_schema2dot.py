"""unittests for schema2dot"""

__revision__ = '$Id: unittest_schema2dot.py,v 1.5 2006-03-17 18:17:54 syt Exp $'

from logilab.common.testlib import TestCase, unittest_main
from logilab.common.compat import set

from yams import SchemaLoader
from yams import schema2dot


class DummyDefaultHandler:

    def default_modname(self):
        return 'yo'
    
    def vocabulary_license(self):
        return ['GPL', 'ZPL']
    
    def vocabulary_debian_handler(self):
        return ['machin', 'bidule']

schema = SchemaLoader().load('data', default_handler=DummyDefaultHandler())

DOT_SOURCE = """digraph Schema {
rankdir=BT
ratio=compress
size="12,30"
Societe [label="Societe"];
Person [label="Person"];
edge [label="travaille"];
Person -> Societe
}"""


class MyVisitor(schema2dot.SchemaVisitor):
    """customize drawing options for better control"""
    def get_props_for_eschema(self, e_schema):
        return {'label' : e_schema.type}

    def get_props_for_rschema(self, r_schema):
        return {'label' : r_schema.type}

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
