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

DOT_SOURCE = r'''digraph "toto" {
rankdir=BT
ratio=compress
charset="utf-8"
splines=true
overlap=false
sep=0.2
"Person" [shape="record", fontname="Courier", style="filled", label="{Person|nom\lprenom\lsexe\lpromo\ltitre\ladel\lass\lweb\ltel\lfax\ldatenaiss\ltest\lsalary\l}"];
"Societe" [shape="record", fontname="Courier", style="filled", label="{Societe|nom\lweb\ltel\lfax\lrncs\lad1\lad2\lad3\lcp\lville\l}"];
"Person" -> "Societe" [taillabel="0..n", style="filled", arrowhead="normal", color="grey", label="travaille", headlabel="0..n", arrowtail="none", decorate="true"];
}
'''


class DotTC(TestCase):
    
    def test_schema2dot(self):
        """tests dot conversion without attributes information"""
        wanted_entities = set(('Person', 'Societe'))
        skipped_entities = set(schema.entities()) - wanted_entities
        schema2dot.schema2dot(schema, 'toto.dot', skipentities=skipped_entities)
        generated = open('toto.dot').read()
        os.remove('toto.dot')
        self.assertTextEquals(DOT_SOURCE, generated)
        
if __name__ == '__main__':
    unittest_main()
