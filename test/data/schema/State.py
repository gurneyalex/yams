from yams.buildobjs import EntityType, RelationType, SubjectRelation, \
     Int, String,  Boolean

class State(MetaUserEntityType):
    """used to associate simple states to an entity
    type and/or to define workflows
    """
    permissions = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers', 'users',),
        'delete': ('managers', 'owners',),
        'update': ('managers', 'owners',),
        }

    # attributes
    eid = Int(required=True, uid=True)
    name = String(required=True,
                  indexed=True, internationalizable=True,
                  constraints=[SizeConstraint(256)])
    description = String(fulltextindexed=True)
    # relations
    state_of = SubjectRelation('Eetype', cardinality='+*')
    next_state = SubjectRelation('State', cardinality='**')
    initial_state = ObjectRelation('Eetype', cardinality='?*')


class state_of(RelationType):
    """link a state to one or more entity type"""
    permissions = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers',),
        'delete': ('managers',),
        }

class next_state(RelationType):
    """define a workflow by associating a state to possible following states
    """
    permissions = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers',),
        'delete': ('managers',),
        }

class initial_state(MetaUserRelationType):
    """indicate which state should be used by default when an entity using states
    is created
    """
    permissions = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers', 'users',),
        'delete': ('managers', 'users',),
        }
    inlined = True

class Eetype(EntityType):
    """define an entity type, used to build the application schema"""
    permissions = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers',),
        'delete': ('managers',),
        'update': ('managers', 'owners',),
        }
    name = String(required=True, indexed=True, internationalizable=True,
                  constraints=[UniqueConstraint(), SizeConstraint(64)])
    description = String(fulltextindexed=True)
    meta = Boolean()
    final = Boolean()
