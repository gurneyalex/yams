from logilab.common.testlib import TestCase, unittest_main, mock_object

from yams.constraints import *
# after import *
from datetime import datetime, date, timedelta

class ConstraintTC(TestCase):

    def test_interval_serialization_integers(self):
        cstr = IntervalBoundConstraint(12, 13)
        self.assertEquals(cstr.serialize(), '12;13')
        cstr = IntervalBoundConstraint(maxvalue=13)
        self.assertEquals(cstr.serialize(), 'None;13')
        cstr = IntervalBoundConstraint(minvalue=13)
        self.assertEquals(cstr.serialize(), '13;None')
        self.assertRaises(AssertionError, IntervalBoundConstraint)

    def test_interval_serialization_floats(self):
        cstr = IntervalBoundConstraint(12.13, 13.14)
        self.assertEquals(cstr.serialize(), '12.13;13.14')


    def test_interval_deserialization_integers(self):
        cstr = IntervalBoundConstraint.deserialize('12;13')
        self.assertEquals(cstr.minvalue, 12)
        self.assertEquals(cstr.maxvalue, 13)
        cstr = IntervalBoundConstraint.deserialize('None;13')
        self.assertEquals(cstr.minvalue, None)
        self.assertEquals(cstr.maxvalue, 13)
        cstr = IntervalBoundConstraint.deserialize('12;None')
        self.assertEquals(cstr.minvalue, 12)
        self.assertEquals(cstr.maxvalue, None)

    def test_interval_deserialization_floats(self):
        cstr = IntervalBoundConstraint.deserialize('12.13;13.14')
        self.assertEquals(cstr.minvalue, 12.13)
        self.assertEquals(cstr.maxvalue, 13.14)


    def test_regexp_serialization(self):
        cstr = RegexpConstraint('[a-z]+,[A-Z]+', 12)
        self.assertEquals(cstr.serialize(), '[a-z]+,[A-Z]+,12')

    def test_regexp_deserialization(self):
        cstr = RegexpConstraint.deserialize('[a-z]+,[A-Z]+,12')
        self.assertEquals(cstr.regexp, '[a-z]+,[A-Z]+')
        self.assertEquals(cstr.flags, 12)

    def test_interval_with_attribute(self):
        cstr = IntervalBoundConstraint(NOW(), Attribute('hop'))
        cstr2 = IntervalBoundConstraint.deserialize(cstr.serialize())
        self.assertEquals(cstr2.minvalue.offset, None)
        self.assertEquals(cstr2.maxvalue.attr, 'hop')
        self.failUnless(cstr2.check(mock_object(hop=datetime.now()+timedelta(hours=1)),
                                    'hip', datetime.now() + timedelta(seconds=2)))
        # fail, value < minvalue
        self.failIf(cstr2.check(mock_object(hop=datetime.now()+timedelta(hours=1)),
                                'hip', datetime.now() - timedelta(hours=2)))
        # fail, value > maxvalue
        self.failIf(cstr2.check(mock_object(hop=datetime.now()+timedelta(hours=1)),
                                'hip', datetime.now() + timedelta(hours=2)))


    def test_interval_with_date(self):
        cstr = IntervalBoundConstraint(TODAY(timedelta(1)),
                                       TODAY(timedelta(3)))
        cstr2 = IntervalBoundConstraint.deserialize(cstr.serialize())
        self.assertEquals(cstr2.minvalue.offset, timedelta(1))
        self.assertEquals(cstr2.maxvalue.offset, timedelta(3))
        self.failUnless(cstr2.check(None, 'hip', date.today() + timedelta(2)))
        # fail, value < minvalue
        self.failIf(cstr2.check(None, 'hip', date.today()))
        # fail, value > maxvalue
        self.failIf(cstr2.check(None, 'hip', date.today() + timedelta(4)))

    def test_bound_with_attribute(self):
        cstr = BoundaryConstraint('<=', Attribute('hop'))
        cstr2 = BoundaryConstraint.deserialize(cstr.serialize())
        self.assertEquals(cstr2.boundary.attr, 'hop')
        self.assertEquals(cstr2.operator, '<=')
        self.failUnless(cstr2.check(mock_object(hop=date.today()), 'hip', date.today()))
        # fail, value > maxvalue
        self.failIf(cstr2.check(mock_object(hop=date.today()),
                                'hip', date.today() + timedelta(days=1)))


    def test_bound_with_date(self):
        cstr = BoundaryConstraint('<=', TODAY())
        cstr2 = BoundaryConstraint.deserialize(cstr.serialize())
        self.assertEquals(cstr2.boundary.offset, None)
        self.assertEquals(cstr2.operator, '<=')
        self.failUnless(cstr2.check(None, 'hip', date.today()))
        # fail, value > maxvalue
        self.failIf(cstr2.check(None, 'hip', date.today() + timedelta(days=1)))

if __name__ == '__main__':
    unittest_main()


