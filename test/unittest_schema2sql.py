"""
unit tests for module yams.schema2sql

Copyright Logilab 2002-2005, all rights reserved.
http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

from cStringIO import StringIO

from logilab.common.testlib import TestCase, unittest_main

from yams import SchemaLoader
from yams.schema2sql import schema2sql

import os.path as osp

DATADIR = osp.abspath(osp.join(osp.dirname(__file__),'data'))

class DummyDefaultHandler:

    def default_modname(self):
        return 'yo'
    
    def vocabulary_license(self):
        return ['GPL', 'ZPL']
    
    def vocabulary_debian_handler(self):
        return ['machin', 'bidule']

schema = SchemaLoader().load(DATADIR, default_handler=DummyDefaultHandler())


EXPECTED_DATA_NO_DROP = """
CREATE TABLE Affaire(
 sujet varchar(128),
 ref varchar(12),
 inline_rel integer
);
CREATE INDEX affaire_inline_rel_idx ON Affaire (inline_rel);

CREATE TABLE Company(
 name text
);

CREATE TABLE Division(
 name text
);

CREATE TABLE Eetype(
 name varchar(64) UNIQUE NOT NULL,
 description text,
 meta boolean,
 final boolean,
 initial_state integer
);
CREATE INDEX eetype_name_idx ON Eetype (name);
CREATE INDEX eetype_initial_state_idx ON Eetype (initial_state);

CREATE TABLE Employee(
);

CREATE TABLE Note(
 date varchar(10),
 type varchar(1),
 para varchar(512)
);

CREATE TABLE Person(
 nom varchar(64) NOT NULL,
 prenom varchar(64),
 sexe varchar(1) DEFAULT 'M',
 promo text,
 titre varchar(128),
 adel varchar(128),
 ass varchar(128),
 web varchar(128),
 tel integer,
 fax integer,
 datenaiss date,
 test boolean,
 salary float
);

CREATE TABLE Societe(
 nom varchar(64),
 web varchar(128),
 tel integer,
 fax integer,
 rncs varchar(32),
 ad1 varchar(128),
 ad2 varchar(128),
 ad3 varchar(128),
 cp varchar(12),
 ville varchar(32)
);

CREATE TABLE State(
 eid integer PRIMARY KEY,
 name varchar(256) NOT NULL,
 description text
);
CREATE INDEX state_name_idx ON State (name);

CREATE TABLE pkginfo(
 modname varchar(30) DEFAULT 'yo' NOT NULL,
 version varchar(10) NOT NULL,
 copyright text NOT NULL,
 license text,
 pyversions text,
 short_desc varchar(80) NOT NULL,
 long_desc text NOT NULL,
 author varchar(100) NOT NULL,
 author_email varchar(100) NOT NULL,
 mailinglist varchar(100),
 debian_handler text
);


CREATE TABLE concerne_relation (
  eid_from INTEGER NOT NULL,
  eid_to INTEGER NOT NULL,
  CONSTRAINT concerne_relation_p_key PRIMARY KEY(eid_from, eid_to),
  CONSTRAINT concerne_relation_fkey1 FOREIGN KEY (eid_from) REFERENCES entities (eid) ON DELETE CASCADE,
  CONSTRAINT concerne_relation_fkey2 FOREIGN KEY (eid_to) REFERENCES entities (eid) ON DELETE CASCADE
);

CREATE INDEX concerne_relation_from_idx ON concerne_relation (eid_from);
CREATE INDEX concerne_relation_to_idx ON concerne_relation (eid_to);

CREATE TABLE evaluee_relation (
  eid_from INTEGER NOT NULL,
  eid_to INTEGER NOT NULL,
  CONSTRAINT evaluee_relation_p_key PRIMARY KEY(eid_from, eid_to),
  CONSTRAINT evaluee_relation_fkey1 FOREIGN KEY (eid_from) REFERENCES entities (eid) ON DELETE CASCADE,
  CONSTRAINT evaluee_relation_fkey2 FOREIGN KEY (eid_to) REFERENCES entities (eid) ON DELETE CASCADE
);

CREATE INDEX evaluee_relation_from_idx ON evaluee_relation (eid_from);
CREATE INDEX evaluee_relation_to_idx ON evaluee_relation (eid_to);

CREATE TABLE next_state_relation (
  eid_from INTEGER NOT NULL,
  eid_to INTEGER NOT NULL,
  CONSTRAINT next_state_relation_p_key PRIMARY KEY(eid_from, eid_to),
  CONSTRAINT next_state_relation_fkey1 FOREIGN KEY (eid_from) REFERENCES entities (eid) ON DELETE CASCADE,
  CONSTRAINT next_state_relation_fkey2 FOREIGN KEY (eid_to) REFERENCES entities (eid) ON DELETE CASCADE
);

CREATE INDEX next_state_relation_from_idx ON next_state_relation (eid_from);
CREATE INDEX next_state_relation_to_idx ON next_state_relation (eid_to);

CREATE TABLE obj_wildcard_relation (
  eid_from INTEGER NOT NULL,
  eid_to INTEGER NOT NULL,
  CONSTRAINT obj_wildcard_relation_p_key PRIMARY KEY(eid_from, eid_to),
  CONSTRAINT obj_wildcard_relation_fkey1 FOREIGN KEY (eid_from) REFERENCES entities (eid) ON DELETE CASCADE,
  CONSTRAINT obj_wildcard_relation_fkey2 FOREIGN KEY (eid_to) REFERENCES entities (eid) ON DELETE CASCADE
);

CREATE INDEX obj_wildcard_relation_from_idx ON obj_wildcard_relation (eid_from);
CREATE INDEX obj_wildcard_relation_to_idx ON obj_wildcard_relation (eid_to);

CREATE TABLE state_of_relation (
  eid_from INTEGER NOT NULL,
  eid_to INTEGER NOT NULL,
  CONSTRAINT state_of_relation_p_key PRIMARY KEY(eid_from, eid_to),
  CONSTRAINT state_of_relation_fkey1 FOREIGN KEY (eid_from) REFERENCES entities (eid) ON DELETE CASCADE,
  CONSTRAINT state_of_relation_fkey2 FOREIGN KEY (eid_to) REFERENCES entities (eid) ON DELETE CASCADE
);

CREATE INDEX state_of_relation_from_idx ON state_of_relation (eid_from);
CREATE INDEX state_of_relation_to_idx ON state_of_relation (eid_to);

CREATE TABLE subj_wildcard_relation (
  eid_from INTEGER NOT NULL,
  eid_to INTEGER NOT NULL,
  CONSTRAINT subj_wildcard_relation_p_key PRIMARY KEY(eid_from, eid_to),
  CONSTRAINT subj_wildcard_relation_fkey1 FOREIGN KEY (eid_from) REFERENCES entities (eid) ON DELETE CASCADE,
  CONSTRAINT subj_wildcard_relation_fkey2 FOREIGN KEY (eid_to) REFERENCES entities (eid) ON DELETE CASCADE
);

CREATE INDEX subj_wildcard_relation_from_idx ON subj_wildcard_relation (eid_from);
CREATE INDEX subj_wildcard_relation_to_idx ON subj_wildcard_relation (eid_to);

CREATE TABLE sym_rel_relation (
  eid_from INTEGER NOT NULL,
  eid_to INTEGER NOT NULL,
  CONSTRAINT sym_rel_relation_p_key PRIMARY KEY(eid_from, eid_to),
  CONSTRAINT sym_rel_relation_fkey1 FOREIGN KEY (eid_from) REFERENCES entities (eid) ON DELETE CASCADE,
  CONSTRAINT sym_rel_relation_fkey2 FOREIGN KEY (eid_to) REFERENCES entities (eid) ON DELETE CASCADE
);

CREATE INDEX sym_rel_relation_from_idx ON sym_rel_relation (eid_from);
CREATE INDEX sym_rel_relation_to_idx ON sym_rel_relation (eid_to);

CREATE TABLE travaille_relation (
  eid_from INTEGER NOT NULL,
  eid_to INTEGER NOT NULL,
  CONSTRAINT travaille_relation_p_key PRIMARY KEY(eid_from, eid_to),
  CONSTRAINT travaille_relation_fkey1 FOREIGN KEY (eid_from) REFERENCES entities (eid) ON DELETE CASCADE,
  CONSTRAINT travaille_relation_fkey2 FOREIGN KEY (eid_to) REFERENCES entities (eid) ON DELETE CASCADE
);

CREATE INDEX travaille_relation_from_idx ON travaille_relation (eid_from);
CREATE INDEX travaille_relation_to_idx ON travaille_relation (eid_to);

CREATE TABLE works_for_relation (
  eid_from INTEGER NOT NULL,
  eid_to INTEGER NOT NULL,
  CONSTRAINT works_for_relation_p_key PRIMARY KEY(eid_from, eid_to),
  CONSTRAINT works_for_relation_fkey1 FOREIGN KEY (eid_from) REFERENCES entities (eid) ON DELETE CASCADE,
  CONSTRAINT works_for_relation_fkey2 FOREIGN KEY (eid_to) REFERENCES entities (eid) ON DELETE CASCADE
);

CREATE INDEX works_for_relation_from_idx ON works_for_relation (eid_from);
CREATE INDEX works_for_relation_to_idx ON works_for_relation (eid_to);
"""

class SQLSchemaTC(TestCase):
    
    def test_known_values(self):
        output = schema2sql(schema)
        self.assertTextEquals(output.strip(), EXPECTED_DATA_NO_DROP.strip())

        
if __name__ == '__main__':
    unittest_main()
