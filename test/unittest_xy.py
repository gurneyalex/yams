from logilab.common.testlib import TestCase, unittest_main
from yams.xy import XYRegistry

class XYTC(TestCase):
    def test(self):
        xy = XYRegistry()
        xy.register_prefix('http://purl.org/dc/elements/1.1/', 'dc')
        xy.register_prefix('http://xmlns.com/foaf/0.1/', 'foaf')
        xy.register_prefix('http://usefulinc.com/ns/doap#', 'doap')

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

        self.assertEquals(xy.yeq('doap:Project', isentity=True), ['Project'])
        self.assertEquals(xy.yeq('dc:title'), [('CWUser', 'login', '*'),
                                               ('Project', 'name', '*')])
        self.assertEquals(xy.yeq('doap:Project doap:maintainer'),
                          [('Project', 'created_by', 'CWUser')])

if __name__ == '__main__':
    unittest_main()
