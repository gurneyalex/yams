from yams.buildobjs import EntityType, RelationType, SubjectRelation, \
     ObjectRelation, Int, String,  Boolean
from yams.constraints import SizeConstraint, UniqueConstraint

from data.schema import RESTRICTED_RTYPE_PERMS

class State(EntityType):
    """used to associate simple states to an entity
    type and/or to define workflows
    """
    __permissions__ = {
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
    description = String(fulltextindexed=True, meta=True) # XXX meta to test bw compat
    # relations
    state_of = SubjectRelation('Eetype', cardinality='+*')
    next_state = SubjectRelation('State', cardinality='**')
    initial_state = ObjectRelation('Eetype', cardinality='?*')


class state_of(RelationType):
    """link a state to one or more entity type"""
    __permissions__ = RESTRICTED_RTYPE_PERMS

class next_state(RelationType):
    """define a workflow by associating a state to possible following states
    """
    __permissions__ = RESTRICTED_RTYPE_PERMS

class initial_state(RelationType):
    """indicate which state should be used by default when an entity using states
    is created
    """
    __permissions__ = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers', 'users',),
        'delete': ('managers', 'users',),
        }
    inlined = True

class Eetype(EntityType):
    """define an entity type, used to build the application schema"""
    __permissions__ = {
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
