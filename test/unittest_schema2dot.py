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
"""unittests for schema2dot"""

import os
import os.path as osp

from logilab.common.testlib import TestCase, unittest_main

from yams.reader import SchemaLoader
from yams import schema2dot

DATADIR = osp.abspath(osp.join(osp.dirname(__file__), 'data'))

schema = SchemaLoader().load([DATADIR])

DOT_SOURCE = r'''digraph "toto" {
rankdir=BT
ratio=compress
charset="utf-8"
overlap=false
sep=0.2
splines=true
"Person" [fontname="Courier", label="{Person|nom\lprenom\lsexe\lpromo\ltitre\ladel\lass\lweb\ltel\lfax\ldatenaiss\ltest\lsalary\l}", shape="record", style="filled"];
"Salaried" [fontname="Courier", label="{Salaried|nom\lprenom\lsexe\lpromo\ltitre\ladel\lass\lweb\ltel\lfax\ldatenaiss\ltest\lsalary\l}", shape="record", style="filled"];
"Societe" [fontname="Courier", label="{Societe|nom\lweb\ltel\lfax\lrncs\lad1\lad2\lad3\lcp\lville\l}", shape="record", style="filled"];
"Salaried" -> "Person" [arrowhead="empty", color="grey", decorate="false", fontcolor="grey", label="Parent class", style="filled"];
"Person" -> "Societe" [arrowhead="normal", arrowtail="none", color="#aa0000", decorate="false", fontcolor="#aa0000", headlabel="0..n", label="travaille", style="filled", taillabel="0..n"];
"Salaried" -> "Societe" [arrowhead="normal", arrowtail="none", color="#00aa00", decorate="false", fontcolor="#00aa00", headlabel="0..n", label="travaille", style="filled", taillabel="0..n"];
}
'''

class DotTC(TestCase):

    def test_schema2dot(self):
        """tests dot conversion without attributes information"""
        wanted_entities = set(('Person', 'Salaried', 'Societe'))
        skipped_entities = set(ent for ent in schema.entities()
                               if ent.type not in wanted_entities)
        schema2dot.schema2dot(schema, 'toto.dot', skiptypes=skipped_entities)
        generated = open('toto.dot').read()
        os.remove('toto.dot')
        self.assertMultiLineEqual(DOT_SOURCE, generated)

if __name__ == '__main__':
    unittest_main()
