# conflicting RelationType properties

class Anentity(EntityType):
    rel = SubjectRelation('Anentity', inlined=True)

class rel(RelationType):
    inlined = False
