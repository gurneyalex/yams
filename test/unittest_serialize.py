from logilab.common import testlib

from yams.buildobjs import register_base_types, String, EntityType, RelationType, RelationDefinition
from yams import schema, serialize

class MyTests(testlib.TestCase):

    def test_yams_serialize(self):
        s = schema.Schema('Unknown')
        register_base_types(s)
        e2 = EntityType('Ent2')
        s.add_entity_type(e2)
        e1 = EntityType('Ent1')
        e1.specialized_type = 'Ent2'
        s.add_entity_type(e1)
        s.add_relation_type(RelationType('attr1'))
        s.add_relation_def(RelationDefinition('Ent1', 'attr1', 'String'))
        out = serialize.serialize_to_python(s)
        self.assertMultiLineEqual(out, '\n'.join([
                'from yams.buildobjs import *',
                '',
                'class Ent2(EntityType):',
                '    pass',
                '',
                'class Ent1(Ent2):',
                '    attr1 = String()',
                '\n']))

if __name__ == '__main__':
    testlib.unittest_main()
