from yams.buildobjs import (EntityType, SubjectRelation, ObjectRelation,
                            String, Int, Float, Date, Boolean)


class MyEntity(EntityType):
    base_arg_b = String()
    base_arg_a = Boolean()
    base_sub = SubjectRelation('MyOtherEntity')
    base_obj = ObjectRelation('MyOtherEntity')

class MyOtherEntity(EntityType):
    base_o_obj = SubjectRelation('MyEntity')
    base_o_sub = ObjectRelation('MyEntity')

MyEntity.add_relation(Date(), name='new_arg_a')
MyEntity.add_relation(Int(), name='new_arg_b')

MyEntity.add_relation(SubjectRelation('MyOtherEntity'), name="new_sub")
MyEntity.add_relation(ObjectRelation('MyOtherEntity'), name="new_obj")
MyOtherEntity.add_relation(SubjectRelation('MyEntity'), name="new_o_obj")
MyOtherEntity.add_relation(ObjectRelation('MyEntity'), name="new_o_sub")
