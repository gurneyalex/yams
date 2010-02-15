from yams.buildobjs import EntityType, RelationType, SubjectRelation

class Anentity(EntityType):
    rel = SubjectRelation('Anentity', inlined=True)

class Anotherentity(EntityType):
    rel = SubjectRelation('Anentity')


class rel(RelationType):
    composite = 'subject'
    cardinality = '1*'
    symmetric = True

class __rel(RelationType):
    name = 'rel'
    composite = 'subject'
