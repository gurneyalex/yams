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
from logilab.common.testlib import TestCase, unittest_main, mock_object

from yams.constraints import *
# after import *
from datetime import datetime, date, timedelta

class ConstraintTC(TestCase):

    def test_membership(self):
        s = set()
        cstrs = [UniqueConstraint(),
                 SizeConstraint(min=0, max=42),
                 RegexpConstraint('babar', 0),
                 BoundaryConstraint('>', 1),
                 IntervalBoundConstraint(minvalue=0, maxvalue=42),
                 StaticVocabularyConstraint((1, 2, 3)),
                 FormatConstraint()]
        for cstr in cstrs:
            s.add(cstr)
            s.add(type(cstr).deserialize(cstr.serialize()))
        self.assertEqual(7, len(s))

    def test_interval_serialization_integers(self):
        cstr = IntervalBoundConstraint(12, 13)
        self.assertEqual(IntervalBoundConstraint.deserialize('12;13'), cstr)
        self.assertEqual(cstr.serialize(), u'{"maxvalue": 13, "minvalue": 12}')
        self.assertEqual(cstr.__class__.deserialize(cstr.serialize()), cstr)
        cstr = IntervalBoundConstraint(maxvalue=13)
        self.assertEqual(IntervalBoundConstraint.deserialize('None;13'), cstr)
        self.assertEqual(cstr.serialize(), u'{"maxvalue": 13, "minvalue": null}')
        self.assertEqual(cstr.__class__.deserialize(cstr.serialize()), cstr)
        cstr = IntervalBoundConstraint(minvalue=13)
        self.assertEqual(IntervalBoundConstraint.deserialize('13;None'), cstr)
        self.assertEqual(cstr.serialize(), u'{"maxvalue": null, "minvalue": 13}')
        self.assertEqual(cstr.__class__.deserialize(cstr.serialize()), cstr)
        self.assertRaises(AssertionError, IntervalBoundConstraint)

    def test_interval_serialization_floats(self):
        cstr = IntervalBoundConstraint(12.13, 13.14)
        self.assertEqual(IntervalBoundConstraint.deserialize('12.13;13.14'), cstr)
        self.assertEqual(cstr.serialize(), u'{"maxvalue": 13.14, "minvalue": 12.13}')
        self.assertEqual(cstr.__class__.deserialize(cstr.serialize()), cstr)

    def test_interval_deserialization_integers(self):
        cstr = IntervalBoundConstraint.deserialize('12;13')
        self.assertEqual(cstr.minvalue, 12)
        self.assertEqual(cstr.maxvalue, 13)
        cstr = IntervalBoundConstraint.deserialize('None;13')
        self.assertEqual(cstr.minvalue, None)
        self.assertEqual(cstr.maxvalue, 13)
        cstr = IntervalBoundConstraint.deserialize('12;None')
        self.assertEqual(cstr.minvalue, 12)
        self.assertEqual(cstr.maxvalue, None)

    def test_interval_deserialization_floats(self):
        cstr = IntervalBoundConstraint.deserialize('12.13;13.14')
        self.assertEqual(cstr.minvalue, 12.13)
        self.assertEqual(cstr.maxvalue, 13.14)

    def test_regexp_serialization(self):
        cstr = RegexpConstraint('[a-z]+,[A-Z]+', 12)
        self.assertEqual(cstr.serialize(), '{"flags": 12, "regexp": "[a-z]+,[A-Z]+"}')
        self.assertEqual(cstr.__class__.deserialize(cstr.serialize()), cstr)

    def test_regexp_deserialization(self):
        cstr = RegexpConstraint.deserialize('[a-z]+,[A-Z]+,12')
        self.assertEqual(cstr.regexp, '[a-z]+,[A-Z]+')
        self.assertEqual(cstr.flags, 12)

    def test_interval_with_attribute(self):
        cstr = IntervalBoundConstraint(NOW(), Attribute('hop'))
        cstr2 = IntervalBoundConstraint.deserialize(cstr.serialize())
        self.assertEqual(cstr2.minvalue.offset, None)
        self.assertEqual(cstr2.maxvalue.attr, 'hop')
        self.assertTrue(cstr2.check(mock_object(hop=datetime.now()+timedelta(hours=1)),
                                    'hip', datetime.now() + timedelta(seconds=2)))
        # fail, value < minvalue
        self.assertFalse(cstr2.check(mock_object(hop=datetime.now()+timedelta(hours=1)),
                                'hip', datetime.now() - timedelta(hours=2)))
        # fail, value > maxvalue
        self.assertFalse(cstr2.check(mock_object(hop=datetime.now()+timedelta(hours=1)),
                                'hip', datetime.now() + timedelta(hours=2)))

    def test_interval_with_date(self):
        cstr = IntervalBoundConstraint(TODAY(timedelta(1)),
                                       TODAY(timedelta(3)))
        cstr2 = IntervalBoundConstraint.deserialize(cstr.serialize())
        self.assertEqual(cstr2.minvalue.offset, timedelta(1))
        self.assertEqual(cstr2.maxvalue.offset, timedelta(3))
        self.assertTrue(cstr2.check(None, 'hip', date.today() + timedelta(2)))
        # fail, value < minvalue
        self.assertFalse(cstr2.check(None, 'hip', date.today()))
        # fail, value > maxvalue
        self.assertFalse(cstr2.check(None, 'hip', date.today() + timedelta(4)))

    def test_bound_constant(self):
        cstr = BoundaryConstraint('<=', 0)
        cstr2 = BoundaryConstraint.deserialize(cstr.serialize())
        self.assertFalse(cstr2.check(None, 'hip', 25))
        self.assertTrue(cstr2.check(None, 'hip', -1))

    def test_bound_with_attribute(self):
        cstr = BoundaryConstraint('<=', Attribute('hop'))
        cstr2 = BoundaryConstraint.deserialize(cstr.serialize())
        self.assertEqual(cstr, cstr2)
        self.assertEqual(cstr2.boundary.attr, 'hop')
        self.assertEqual(cstr2.operator, '<=')
        self.assertTrue(cstr2.check(mock_object(hop=date.today()), 'hip', date.today()))
        # fail, value > maxvalue
        self.assertFalse(cstr2.check(mock_object(hop=date.today()),
                                     'hip', date.today() + timedelta(days=1)))

    def test_bound_with_date(self):
        cstr = BoundaryConstraint('<=', TODAY())
        cstr2 = BoundaryConstraint.deserialize(cstr.serialize())
        self.assertEqual(cstr, cstr2)
        self.assertEqual(cstr2.boundary.offset, None)
        self.assertEqual(cstr2.operator, '<=')
        self.assertTrue(cstr2.check(None, 'hip', date.today()))
        # fail, value > maxvalue
        self.assertFalse(cstr2.check(None, 'hip', date.today() + timedelta(days=1)))

    def test_bound_with_unset_attribute(self):
        cstr = BoundaryConstraint('<=', None)
        self.assertTrue(cstr.check(None, 'hip', date.today()))
        cstr = BoundaryConstraint('<=', Attribute('unset_attr'))
        self.assertTrue(cstr.check(mock_object(unset_attr=None), 'hip', date.today()))

    def test_boundary_constraint_message(self):
        cstr = BoundaryConstraint('<=', 0)
        self.assertEqual(cstr.failed_message('attr', 1),
                         ('value %(KEY-value)s must be <= %(KEY-boundary)s',
                          {'attr-value': 1, 'attr-boundary': 0}))

    def test_vocab_constraint_serialization(self):
        cstr = StaticVocabularyConstraint(['a, b', 'c'])
        self.assertEqual(StaticVocabularyConstraint.deserialize(cstr.serialize()).values,
                         ('a, b', 'c'))


if __name__ == '__main__':
    unittest_main()
