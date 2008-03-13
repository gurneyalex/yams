class Company(EntityType):
    name = String()

class Division(EntityType):
    name = String()

class Employee(EntityType):
    works_for = SubjectRelation(('Company', 'Division'))

class require_permission(RelationType):
    """link a permission to the entity. This permission should be used in the
    security definition of the entity's type to be useful.
    """
    permissions = {
        'read':   ('managers', 'users', 'guests'),
        'add':    ('managers',),
        'delete': ('managers',),
        }


class missing_require_permission(RelationDefinition):
    name = 'require_permission'
    subject = ('Company', 'Division')
    object = 'EPermission'

class EPermission(MetaEntityType):
    """entity type that may be used to construct some advanced security configuration
    """
    name = String(required=True, indexed=True, internationalizable=True, maxsize=100,
                  description=_('name or identifier of the permission'))
