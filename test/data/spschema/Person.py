from yams.buildobjs import EntityType, SubjectRelation, String

class Person(EntityType):
    firstname = String()
    knows = SubjectRelation('Person')
    works_for = SubjectRelation('Company')

class Student(Person):
    __specializes_schema__ = True

class Company(EntityType):
    name = String()

class SubCompany(Company):
    __specializes_schema__ = True

class Division(Company):
    __specializes_schema__ = True
    division_of = SubjectRelation('Company')

class SubDivision(Division):
    __specializes_schema__ = True

# This class doesn't extend the schema
class SubSubDivision(SubDivision):
    pass
