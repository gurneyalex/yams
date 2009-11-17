from yams.buildobjs import EntityType, RelationType, RelationDefinition, \
     SubjectRelation, String

class Company(EntityType):
    name = String()

class Subcompany(Company):
    __specializes_schema__ = True
    subcompany_of = SubjectRelation('Company')

class Division(Company):
    __specializes_schema__ = True
    division_of = SubjectRelation('Company')

class Subdivision(Division):
    __specializes_schema__ = True
    subdivision_of = SubjectRelation('Company')

class Employee(EntityType):
    works_for = SubjectRelation('Company')

class require_permission(RelationType):
    """link a permission to the entity. This permission should be used in the
    security definition of the entity's type to be useful.
    """
    fulltext_container = 'subject'
    __permissions__ = {
        'read':   ('managers', 'users', 'guests'),
        'add':    ('managers',),
        'delete': ('managers',),
        }


class missing_require_permission(RelationDefinition):
    name = 'require_permission'
    subject = 'Company'
    object = 'EPermission'

class EPermission(EntityType):
    """entity type that may be used to construct some advanced security configuration
    """
    __permissions__ = {
        'read':   ('managers', 'users', 'guests',),
        'add':    ('managers',),
        'delete': ('managers',),
        'update': ('managers', 'owners',),
        }
    name = String(required=True, indexed=True, internationalizable=True,
                  fulltextindexed=True, maxsize=100,
                  description=_('name or identifier of the permission'))
