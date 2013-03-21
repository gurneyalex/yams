"""Compare two yams schemas

Textual representation of schema are created and standard diff algorithm are
applied.
"""

import subprocess
import tempfile
import os

from yams import MARKER
from yams.buildobjs import REL_PROPERTIES
from yams.constraints import (SizeConstraint,
                              UniqueConstraint,
                              StaticVocabularyConstraint)
from yams.reader import SchemaLoader


ATTR_CARD_CONVERTER = {'11': True, '?1': False}

def properties_from(attr, is_relation=False):
    """return a dictionnaries containing properties of an attributes
    or a relation (if specified with is_relation option)"""
    ret = {}
    for prop in REL_PROPERTIES:
        try:
            val = getattr(attr, prop)
        except AttributeError:
            continue
        if prop == 'cardinality' and not is_relation: #for attibutes only
            prop = 'required'
            val = ATTR_CARD_CONVERTER[val]

        if prop == 'constraints' and val is not MARKER:
            for constraint in val:
                if isinstance(constraint, SizeConstraint):
                    ret['maxsize'] = constraint.max
                elif isinstance(constraint, UniqueConstraint):
                    ret['unique'] = True
                elif isinstance(constraint, StaticVocabularyConstraint):
                    ret['vocabulary'] = constraint.vocabulary()
            continue

        if val is not MARKER:
            ret[prop] = val

    return ret

def schema2descr(schema):
    """convert a yams schema into a text description"""
    txt = ""
    for entity in sorted(schema.entities(), key=lambda e: e.type):
        txt += "%s\n" % str(entity.type)

        attributes = [(attr[0].type,
                       attr[1].type,
                       properties_from(entity.rdef(attr[0].type)))
                      for attr in entity.attribute_definitions()]
        for attr_name, attr_type, attr_props in attributes:
            txt += "\t%s: %s\n" % (attr_name, attr_type)
            for k, v in attr_props.iteritems():
                txt +="\t\t%s=%s\n" % (k, v)

        relations = [(rel[0].type,
                      rel[1][0].type,
                      properties_from(entity.rdef(rel[0].type), True))
                     for rel in entity.relation_definitions() if rel[2] == 'subject']
        for rel_name, rel_type, rel_props in relations:
            txt += "\t%s: %s\n" % (rel_name, rel_type)
            for k, v in rel_props.iteritems():
                txt += "\t\t%s=%s\n" % (k, v)
    return txt

def schema2file(schema, output):
    """Save schema description of schema find
    in directory schema_dir into output file"""
    description_file = open(output, "w")
    description_file.write(schema2descr(schema))
    description_file.close()

def schema_diff(schema1, schema2, diff_tool=None):
    """schema 1 and 2 are CubicwebSchema
    diff_tool is the name of tool use for file comparison
    """
    tmpdir = tempfile.mkdtemp()
    output1 = os.path.join(tmpdir, "schema1.txt")
    output2 = os.path.join(tmpdir, "schema2.txt")
    schema2file(schema1, output1)
    schema2file(schema2, output2)
    if diff_tool:
        cmd = "%s %s %s" %(diff_tool,
                           output1, output2)
        process = subprocess.Popen(cmd, shell=True)
    else:
        print "description files save in %s and %s" % (output1, output2)
    return output1, output2

if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-f", "--first-schema", dest="schema1",
                      help= "Specify the directory of the first schema")
    parser.add_option("-s", "--second-schema", dest="schema2",
                      help= "Specify the directory of the second schema")
    parser.add_option("-d", "--diff-tool", dest="diff_tool",
                      help= "Specify the name of the diff tool")
    (options, args) = parser.parse_args()
    if options.schema1 and options.schema2:
        schema1 = SchemaLoader().load([options.schema1])
        schema2 = SchemaLoader().load([options.schema2])
        output1, output2 = schema_diff(schema1, schema2)
        if options.diff_tool:
            cmd = "%s %s %s" %(options.diff_tool,
                               output1, output2)
            process = subprocess.Popen(cmd, shell=True)
        else:
            print "description files save in %s and %s" % (output1, output2)
    else:
        parser.error("An input file name must be specified")
