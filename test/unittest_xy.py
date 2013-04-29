# copyright 2004-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
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
from logilab.common.testlib import TestCase, unittest_main
from yams.xy import XYRegistry

class XYTC(TestCase):
    def test(self):
        xy = XYRegistry()
        xy.register_prefix('dc', 'http://purl.org/dc/elements/1.1/')
        xy.register_prefix('foaf', 'http://xmlns.com/foaf/0.1/')
        xy.register_prefix('doap', 'http://usefulinc.com/ns/doap#')

        xy.add_equivalence('creation_date', 'dc:date')
        xy.add_equivalence('created_by', 'dc:creator')
        xy.add_equivalence('description', 'dc:description')
        xy.add_equivalence('CWUser', 'foaf:Person')
        xy.add_equivalence('CWUser login', 'dc:title')
        xy.add_equivalence('CWUser surname', 'foaf:Person foaf:name')
        xy.add_equivalence('Project', 'doap:Project')
        xy.add_equivalence('Project name', 'dc:title')
        xy.add_equivalence('Project name', 'doap:Project doap:name')
        xy.add_equivalence('Project creation_date', 'doap:Project doap:created')
        xy.add_equivalence('Project created_by CWUser', 'doap:Project doap:maintainer foaf:Person')
        xy.add_equivalence('Version', 'doap:Version')
        xy.add_equivalence('Version name', 'doap:Version doap:name')
        xy.add_equivalence('Version creation_date', 'doap:Version doap:created')
        xy.add_equivalence('Version num', 'doap:Version doap:revision')

        self.assertEqual(xy.yeq('doap:Project', isentity=True), ['Project'])
        self.assertEqual(xy.yeq('dc:title'), [('CWUser', 'login', '*'),
                                               ('Project', 'name', '*')])
        self.assertEqual(xy.yeq('doap:Project doap:maintainer'),
                          [('Project', 'created_by', 'CWUser')])

if __name__ == '__main__':
    unittest_main()
