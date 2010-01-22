from yams.buildobjs import EntityType

def post_build_callback(schema):
    schema.add_entity_type(EntityType(name='Toto'))
