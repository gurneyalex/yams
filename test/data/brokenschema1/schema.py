# conflicting RelationType properties

class Anentity(EntityType):
    rel = SubjectRelation('Anentity', inlined=True)

class Anotherentity(EntityType):
    rel = SubjectRelation('Anentity', inlined=False)    
