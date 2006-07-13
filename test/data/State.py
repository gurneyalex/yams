
class State(MetaUserEntityType):
    """used to associate simple states to an entity
    type and/or to define workflows
    """
    eid = SubjectRelation('Int', cardinality='11', uid=True)
    name = SubjectRelation('String', cardinality='11',
                           indexed=True, internationalizable=True,
                           constraints=[SizeConstraint(256)])
    description = SubjectRelation('String',  fulltextindexed=True)
    state_of = SubjectRelation('Eetype', cardinality='+*')
    next_state = SubjectRelation('State', cardinality='**')
    initial_state = ObjectRelation('Eetype', cardinality='?*')


class state_of(RelationType):
    """link a state to one or more entity type"""
    meta = True

class next_state(MetaRelationType):
    """define a workflow by associating a state to possible following states
    """
    meta = True

class initial_state(MetaUserRelationType):
    """indicate which state should be used by default when an entity using states
    is created
    """
    meta = True

    
class Eetype(MetaEntityType):
    """define an entity type, used to build the application schema"""
    name = SubjectRelation('String', cardinality='11',
                           indexed=True, internationalizable=True,
                           constraints=[UniqueConstraint(), SizeConstraint(64)])
    description = SubjectRelation('String',  fulltextindexed=True)
    meta = SubjectRelation('Boolean')
    final = SubjectRelation('Boolean')
