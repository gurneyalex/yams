
class State(MetaUserEntityType):
    """used to associate simple states to an entity
    type and/or to define workflows
    """
    relations = []

    SubjectRelation(relations, 'eid', 'Int', cardinality='11', uid=True)
    SubjectRelation(relations, 'name', 'String', cardinality='11',
                    indexed=True, internationalizable=True,
                    constraints=[SizeConstraint(256)])
    SubjectRelation(relations, 'description', 'String', 
                    fulltextindexed=True)
    
    SubjectRelation(relations, 'state_of', 'Eetype', cardinality='+*')
    SubjectRelation(relations, 'next_state', 'State', cardinality='**')
    ObjectRelation(relations, 'initial_state', 'Eetype', cardinality='?*')


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
    relations = []
    
    SubjectRelation(relations, 'name', 'String', cardinality='11',
                    indexed=True, internationalizable=True,
                    constraints=[UniqueConstraint(), SizeConstraint(64)])
    SubjectRelation(relations, 'description', 'String', 
                    fulltextindexed=True)
    SubjectRelation(relations, 'meta', 'Boolean')
    SubjectRelation(relations, 'final', 'Boolean')
