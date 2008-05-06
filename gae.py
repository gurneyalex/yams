"""extends yams to be able to load google appengine's schemas

MISING FEATURES:
 - ListProperty, StringList, EmailProperty, etc. (XXX)
 - ReferenceProperty.verbose_name, collection_name, etc. (XXX)
"""

import datetime 

from google.appengine.ext import db
from google.appengine.api import datastore_types

from yams.reader import SchemaLoader
from yams.buildobjs import (String, Int, Float, Boolean, Date, Time, Datetime,
                            Interval, Password, Bytes, SubjectRelation)
from yams.buildobjs import metadefinition, EntityType


TYPESMAP = {
    basestring: String,
    datastore_types.Text: String,
    int: Int,
    float: Float,
    bool: Boolean,
    datetime.time: Time,
    datetime.date: Date,
    datetime.datetime: Datetime,
    datastore_types.Blob: Bytes,
    }


def default_factory(prop, **kwargs):
    """just wraps the default types map to set
    basic constraints like `required`, `default`, etc.
    """
    yamstype = TYPESMAP[prop.data_type]
    if 'default' not in kwargs:
        default = prop.default_value()
        if default is not None:
            kwargs['default'] = default
    if prop.required:
        kwargs['required'] = True
    return yamstype(**kwargs)

def string_factory(prop):
    """like default_factory but also deals with `maxsize` and `vocabulary`"""
    kwargs = {}
    if prop.data_type is basestring:
        kwargs['maxsize'] = 500
    if prop.choices is not None:
        kwargs['vocabulary'] = prop.choices
    return default_factory(prop, **kwargs)


def date_factory(prop):
    """like default_factory but also deals with today / now definition"""
    kwargs = {}
    if prop.auto_now_add:
        if prop.data_type is datetime.datetime:
            kwargs['default'] = 'now'
        else:
            kwargs['default'] = 'today'
    # XXX no equivalent to Django's `auto_now`
    return default_factory(prop, **kwargs)


def relation_factory(prop, multiple=False):
    """called if `prop` is a `db.ReferenceProperty`"""
    # XXX deal with potential kwargs of ReferenceProperty.__init__()
    if multiple:
        cardinality = '**'
    elif prop.required:
        cardinality = '1*'
    else:
        cardinality = '?*'
    return SubjectRelation(prop.data_type.kind(), cardinality=cardinality)
    
    
FACTORIES = {
    basestring: string_factory,
    datastore_types.Text: string_factory,
    int: default_factory,
    float: default_factory,
    bool: default_factory,
    datetime.time: date_factory,
    datetime.date: date_factory,
    datetime.datetime: date_factory,
    datastore_types.Blob: default_factory,
    }

class GaeSchemaLoader(SchemaLoader):
    """Google appengine schema loader class"""

    def load_module(self, pymod, register_base_types=False):
        """return a `yams.schema.Schema` from the gae schema definition
        stored in `pymod`.
        """
        self.load_classes(vars(pymod).values(), register_base_types)
                
    def load_classes(self, objs, register_base_types=False):
        self.defined = {}
        for obj in objs:
            if isinstance(obj, type) and issubclass(obj, db.Model):
                self.load_dbmodel(obj)
        return self._build_schema('google-appengine', register_base_types)

    def load_dbmodel(self, dbmodel):
        clsdict = {}
        ordered_props = sorted(dbmodel.properties().values(),
                               key=lambda x: x.creation_counter)
        for prop in ordered_props:
            if isinstance(prop, db.ListProperty):
                if not issubclass(prop.item_type, db.Model):
                    self.error('ignoring list property with %s item type'
                               % prop.item_type)
                    continue
                rdef = relation_factory(prop, multiple=True)
            else:
                try:
                    if isinstance(prop, db.ReferenceProperty):
                        rdef = relation_factory(prop)
                    else:
                        rdef = FACTORIES[prop.data_type](prop)
                except KeyError, exc:
                    self.error('ignoring property %s (keyerror on %s)'
                               % (prop.name, exc))
                    continue
            clsdict[prop.name] = rdef
        edef = metadefinition(dbmodel.kind(), (EntityType,), clsdict)
        self.add_definition(self, edef())


    def error(self, msg):
        print 'ERROR:', msg
