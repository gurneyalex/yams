"""extends yams to be able to load google appengine's schemas

MISING FEATURES:
 - ListProperty, StringList, EmailProperty, etc. (XXX)
 - ReferenceProperty.verbose_name, collection_name, etc. (XXX)
"""

from datetime import datetime, date, time

from google.appengine.ext import db
from google.appengine.api import datastore_types

from yams.schema2sql import eschema_attrs
from yams.constraints import SizeConstraint
from yams.reader import SchemaLoader
from yams.buildobjs import (String, Int, Float, Boolean, Date, Time, Datetime,
                            Interval, Password, Bytes, SubjectRelation)
from yams.buildobjs import metadefinition, EntityType

# db.Model -> yams ############################################################

DBM2Y_TYPESMAP = {
    basestring: String,
    datastore_types.Text: String,
    int: Int,
    float: Float,
    bool: Boolean,
    time: Time,
    date: Date,
    datetime: Datetime,
    datastore_types.Blob: Bytes,
    }


def dbm2y_default_factory(prop, **kwargs):
    """just wraps the default types map to set
    basic constraints like `required`, `default`, etc.
    """
    yamstype = DBM2Y_TYPESMAP[prop.data_type]
    if 'default' not in kwargs:
        default = prop.default_value()
        if default is not None:
            kwargs['default'] = default
    if prop.required:
        kwargs['required'] = True
    return yamstype(**kwargs)

def dbm2y_string_factory(prop):
    """like dbm2y_default_factory but also deals with `maxsize` and `vocabulary`"""
    kwargs = {}
    if prop.data_type is basestring:
        kwargs['maxsize'] = 500
    if prop.choices is not None:
        kwargs['vocabulary'] = prop.choices
    return dbm2y_default_factory(prop, **kwargs)


def dbm2y_date_factory(prop):
    """like dbm2y_default_factory but also deals with today / now definition"""
    kwargs = {}
    if prop.auto_now_add:
        if prop.data_type is datetime:
            kwargs['default'] = 'now'
        else:
            kwargs['default'] = 'today'
    # XXX no equivalent to Django's `auto_now`
    return dbm2y_default_factory(prop, **kwargs)


def dbm2y_relation_factory(prop, multiple=False):
    """called if `prop` is a `db.ReferenceProperty`"""
    # XXX deal with potential kwargs of ReferenceProperty.__init__()
    if multiple:
        cardinality = '**'
    elif prop.required:
        cardinality = '1*'
    else:
        cardinality = '?*'
    return SubjectRelation(prop.data_type.kind(), cardinality=cardinality)
    
    
DBM2Y_FACTORY = {
    basestring: dbm2y_string_factory,
    datastore_types.Text: dbm2y_string_factory,
    int: dbm2y_default_factory,
    float: dbm2y_default_factory,
    bool: dbm2y_default_factory,
    time: dbm2y_date_factory,
    date: dbm2y_date_factory,
    datetime: dbm2y_date_factory,
    datastore_types.Blob: dbm2y_default_factory,
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
                rdef = dbm2y_relation_factory(prop, multiple=True)
            else:
                try:
                    if isinstance(prop, db.ReferenceProperty):
                        rdef = dbm2y_relation_factory(prop)
                    else:
                        rdef = DBM2Y_FACTORY[prop.data_type](prop)
                except KeyError, exc:
                    self.error('ignoring property %s (keyerror on %s)'
                               % (prop.name, exc))
                    continue
            clsdict[prop.name] = rdef
        edef = metadefinition(dbmodel.kind(), (EntityType,), clsdict)
        self.add_definition(self, edef())


    def error(self, msg):
        print 'ERROR:', msg


# yams -> db.Model ############################################################

Y2DBM_TYPESMAP = {
    'Int'      : 'IntegerProperty',
    'Float'    : 'FloatProperty',
    'Boolean'  : 'BooleanProperty',
    'Datetime' : 'DateTimeProperty',
    'Date'     : 'DateProperty',
    'Time'     : 'TimeProperty',
    }

def mx2datetime(mxobj, yamstype):
    """converts a mx date object (DateTime, Date or Time) into a
    regular python datetime object
    """
    if yamstype == 'Datetime':
        return datetime(mxobj.year, mxobj.month, mxobj.day,
                        mxobj.hour, mxobj.minute, int(mxobj.second))
    elif yamstype == 'Date':
        return date(mxobj.year, mxobj.month, mxobj.day)
    return time(mxobj.hour, mxobj.minute, int(mxobj.second))


Y2DBM_FACTORY = {
    'Datetime' : mx2datetime,
    'Date'     : mx2datetime,
    'Time'     : mx2datetime,
    }



def schema2dbmodel(schema, db, skip_relations=()):
    for eschema in schema.entities():
        eschema2dbmodel(eschema, db, skip_relations)

def eschema2dbmodel(eschema, db, skip_relations=()):
    classdict = {}
    for rschema, attrschema in eschema_attrs(eschema, skip_relations):
        if attrschema is not None:
            prop = aschema2dbproperty(eschema, rschema, attrschema, db)
            classdict[rschema.type] = prop
    # db.PropertiedClass is the db.Model's metaclass
    return db.PropertiedClass(eschema.type, (db.Model,), classdict)

def aschema2dbproperty(eschema, rschema, attrschema, db):
    attr = rschema.type
    attrtype = attrschema.type
    constraints = rschema.rproperty(eschema.type, attrschema.type, 'constraints')
    if attrtype == 'String':
        propcls = _dbproperty_from_constraints(db, attrschema.type, constraints)
    else:
        propcls = getattr(db, Y2DBM_TYPESMAP[attrschema.type])
    kwargs = {}
    default = eschema.default(attr)
    if default is not None:
        # special cases for keyword values
        defaultdef = eschema.rproperty(attr, 'default')
        if default in ('today', 'now'): # XXX both should be handled differently
            kwargs['autonow_add'] = True
        else:
            if attrtype in Y2DBM_FACTORY:
                default = Y2DBM_FACTORY[attrtype](default, attrtype)
            kwargs['default'] = default
    if rschema.rproperty(eschema.type, attrtype, 'cardinality')[0] == '1':
        kwargs['required'] = True
    return propcls(**kwargs)

def _dbproperty_from_constraints(db, etype, constraints):
    """return a dbproperty class corresponding to the constraints"""
    if etype == 'String':
        for constraint in constraints:
            if (isinstance(constraint, SizeConstraint)
                and constraint.max is not None
                and constraint.max < 500):
                        return db.StringProperty
    return db.TextProperty
