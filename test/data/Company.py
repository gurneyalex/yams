class Company(EntityType):
    name = String()

class Division(EntityType):
    name = String()

class Employee(EntityType):
    works_for = SubjectRelation(('Company', 'Division'))

