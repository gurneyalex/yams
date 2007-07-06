from yams.constraints import *

from logilab.common.testlib import TestCase, unittest_main

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
        
    
if __name__ == '__main__':
    unittest_main()
    
    
