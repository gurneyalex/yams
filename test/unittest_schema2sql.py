"""
unit tests for module yams.schema2sql

Copyright Logilab 2002-2005, all rights reserved.
http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: unittest_schema2sql.py,v 1.9 2006-03-20 09:36:41 syt Exp $"

from cStringIO import StringIO

from logilab.common.testlib import TestCase, unittest_main

from yams import SchemaLoader
from yams.schema2sql import schema2sql

class DummyDefaultHandler:

    def default_modname(self):
        return 'yo'
    
    def vocabulary_license(self):
        return ['GPL', 'ZPL']
    
    def vocabulary_debian_handler(self):
        return ['machin', 'bidule']

schema = SchemaLoader().load('data', default_handler=DummyDefaultHandler())

EXPECTED_DATA_DROP = """
DROP TABLE Affaire;
CREATE TABLE Affaire(
  sujet varchar(128),
  ref varchar(12),
  inline_rel integer
);
CREATE INDEX affaire_inline_rel_idx ON Affaire (inline_rel);

DROP TABLE Eetype;
CREATE TABLE Eetype(
  name varchar(64) UNIQUE NOT NULL,
  description text,
  meta boolean,
  final boolean,
  initial_state integer
);
CREATE INDEX eetype_name_idx ON Eetype (name);
CREATE INDEX eetype_initial_state_idx ON Eetype (initial_state);

DROP TABLE Note;
CREATE TABLE Note(
  date varchar(10),
  type varchar(1),
  para varchar(512)
);

DROP TABLE Person;
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
  test boolean
);

DROP TABLE Societe;
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

DROP TABLE State;
CREATE TABLE State(
  eid integer PRIMARY KEY,
  name varchar(256) NOT NULL,
  description text
);
CREATE INDEX state_name_idx ON State (name);

DROP TABLE pkginfo;
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
"""

EXPECTED_DATA_NO_DROP = """
CREATE TABLE Affaire(
  sujet varchar(128),
  ref varchar(12),
  inline_rel integer
);
CREATE INDEX affaire_inline_rel_idx ON Affaire (inline_rel);

CREATE TABLE Eetype(
  name varchar(64) UNIQUE NOT NULL,
  description text,
  meta boolean,
  final boolean,
  initial_state integer
);
CREATE INDEX eetype_name_idx ON Eetype (name);
CREATE INDEX eetype_initial_state_idx ON Eetype (initial_state);

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
  test boolean
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
"""

class SQLSchemaTC(TestCase):
    
    def test_known_values(self):
        output = StringIO()
        schema2sql(output, schema)
        self.assertLinesEquals(output.getvalue().strip(), EXPECTED_DATA_NO_DROP.strip())

    def test_known_values_drop(self):
        output = StringIO()
        schema2sql(output, schema, drop=True)
        self.assertLinesEquals(output.getvalue().strip(), EXPECTED_DATA_DROP.strip())

    def test_known_values_no_drop(self):
        output = StringIO()
        schema2sql(output, schema, drop=False)
        self.assertLinesEquals(output.getvalue().strip(), EXPECTED_DATA_NO_DROP.strip())

        
if __name__ == '__main__':
    unittest_main()
