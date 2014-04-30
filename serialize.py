import logging
from cStringIO import StringIO
from logilab.common.graph import ordered_nodes

def serialize_to_python(s):
    out = StringIO()
    w = out.write
    w('from yams.buildobjs import *\n\n')
    graph = {}
    for entity in s.entities():
        l = graph.setdefault(entity, [])
        if entity._specialized_type is not None:
            l.append(entity._specialized_type)
    for e in reversed(ordered_nodes(graph)):
        if not e.final:
            if e._specialized_type:
                base = e._specialized_type
            else:
                base = 'EntityType'
            w('class %s(%s):\n' % (e.type, base))
            attr_defs = list(e.attribute_definitions())
            if attr_defs:
                for attr,obj in attr_defs:
                    w('    %s = %s()\n' % (attr.type, obj.type))
            else:
                w('    pass\n')
            w('\n')
    for r in s.relations():
        if not r.final:
            if r.subjects() and r.objects():
                w('class %s(RelationDefinition):\n' % r.type)
                w('    subject = (%s,)\n' % ', '.join("'%s'" % x for x in r.subjects()))
                w('    object = (%s,)\n' % ', '.join("'%s'" % x for x in r.objects()))
                w('\n')
            else:
                logging.warning('relation definition %s missing subject/object' % r.type)
    return out.getvalue()
