import logging
from io import StringIO
from logilab.common.graph import ordered_nodes

def serialize_to_python(s):
    out = StringIO()
    w = out.write
    w(u'from yams.buildobjs import *\n\n')
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
            w(u'class %s(%s):\n' % (e.type, base))
            attr_defs = list(e.attribute_definitions())
            if attr_defs:
                for attr,obj in attr_defs:
                    w(u'    %s = %s()\n' % (attr.type, obj.type))
            else:
                w(u'    pass\n')
            w(u'\n')
    for r in s.relations():
        if not r.final:
            if r.subjects() and r.objects():
                w(u'class %s(RelationDefinition):\n' % r.type)
                w(u'    subject = (%s,)\n' % ', '.join("'%s'" % x for x in r.subjects()))
                w(u'    object = (%s,)\n' % ', '.join("'%s'" % x for x in r.objects()))
                w(u'\n')
            else:
                logging.warning('relation definition %s missing subject/object' % r.type)
    return out.getvalue()
