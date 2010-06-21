# copyright 2004-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of yams.
#
# yams is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option)
# any later version.
#
# yams is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with yams. If not, see <http://www.gnu.org/licenses/>.
from yams.buildobjs import (EntityType, RelationDefinition, SubjectRelation,
                            String, Int, Float, Date, Boolean)


class MyEntity(EntityType):
    base_arg_b = String()
    base_arg_a = Boolean()
    base_sub = SubjectRelation('MyOtherEntity')

class base_obj(RelationDefinition):
    subject = 'MyOtherEntity'
    object = 'MyEntity'

class MyOtherEntity(EntityType):
    base_o_obj = SubjectRelation('MyEntity')

class base_o_sub(RelationDefinition):
    subject = 'MyEntity'
    object = 'MyOtherEntity'

MyEntity.add_relation(Date(), name='new_arg_a')
MyEntity.add_relation(Int(), name='new_arg_b')

MyEntity.add_relation(SubjectRelation('MyOtherEntity'), name="new_sub")
MyOtherEntity.add_relation(SubjectRelation('MyEntity'), name="new_o_obj")


class new_obj(RelationDefinition):
    subject = 'MyOtherEntity'
    object = 'MyEntity'


class new_o_sub(RelationDefinition):
    subject = 'MyEntity'
    object = 'MyOtherEntity'
