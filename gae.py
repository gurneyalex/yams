"""extends yams to be able to load google appengine's schemas

MISING FEATURES:
 - ListProperty, StringList, EmailProperty, etc. (XXX)
 - ReferenceProperty.verbose_name, collection_name, etc. (XXX)
"""

from datetime import datetime, date, time

from google.appengine.ext import db
from google.appengine.api import datastore_types, users

from yams.schema2sql import eschema_attrs
from yams.constraints import SizeConstraint
from yams.reader import SchemaLoader, PyFileReader
from yams.buildobjs import (String, Int, Float, Boolean, Date, Time, Datetime,
                            Interval, Password, Bytes, SubjectRelation,
                            RestrictedEntityType)
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
    def __init__(self, *args, **kwargs):
        self.use_gauthservice = kwargs.pop('use_gauthservice', False)
        self._db = kwargs.pop('db', db)
        super(GaeSchemaLoader, self).__init__(*args, **kwargs)
        self.defined = {}
        self.created = []
        if self.use_gauthservice:
            self.defined['EUser'] = RestrictedEntityType(name='EUser')
            

    def dbclass_for_kind(self, kind):
        if kind == 'EUser' and self.use_gauthservice:
            return users.User
        return db.class_for_kind(kind)
    
    def load_module(self, pymod, register_base_types=False):
        """return a `yams.schema.Schema` from the gae schema definition
        stored in `pymod`.
        """
        return self.load_classes(vars(pymod).values(), register_base_types)
                
    def load_classes(self, objs, register_base_types=False):
        for obj in objs:
            if isinstance(obj, type) and issubclass(obj, db.Model):
                self.load_dbmodel(obj)
        schema = self._build_schema('google-appengine', register_base_types)
        for eschema in schema.entities():
            if eschema.is_final():
                continue
            try:
                dbcls = self.dbclass_for_kind(str(eschema))
            except db.KindError:
                # not defined as a db model (eg yams import), define it
                dbcls = eschema2dbmodel(eschema, self._db, dbclass_for_kind=self.dbclass_for_kind)
                self.created.append(dbcls)
#             else:
#                 dbprops = dbcls.properties()
#                 for rschema in eschema.subject_relations():
#                     if not str(rschema) in dbprops:
#                         if rschema.is_final():
#                             attrschema = eschema.destination(rschema)
#                             aschema2dbproperty(eschema, rschema, attrschema, db)
#                         else:
                            
        return schema
    
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

    def import_yams_schema(self, ertype, schemamod):
        reader = PyFileReader(self, None, False)
        erdef = reader.import_erschema(ertype, schemamod)
        #self.add_definition(reader, erdef)
        
        
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

def eschema2dbmodel(eschema, db, skip_relations=(), dbclass_for_kind=None):
    if dbclass_for_kind is None:
        dbclass_for_kind = db.class_for_kind
    classdict = {}
    for rschema, attrschema in eschema_attrs(eschema, skip_relations):
        if attrschema is not None:
            prop = aschema2dbproperty(eschema, rschema, attrschema, db)
            classdict[rschema.type] = prop
    for rschema in eschema.subject_relations():
        if rschema.is_final() or rschema == 'identity':
            continue
        targets = rschema.objects(eschema)
        if len(targets) > 1:
            raise NotImplementedError('relation with different target types '
                                      'are not currently supported')
        tschema = targets[0]
        card = rschema.rproperty(eschema, tschema, 'cardinality')[0]
        tdbcls = dbclass_for_kind(str(tschema))
        if tdbcls is users.User:
            assert card in '1?'
            classdict[rschema.type] = db.UserProperty()
            continue
        if card in '1?':
            classdict[rschema.type] = db.ReferenceProperty(tdbcls)
        else:
            classdict[rschema.type] = db.ListProperty(tdbcls)
    # db.PropertiedClass is the db.Model's metaclass
    cls = db.Model
    return cls.__metaclass__(eschema.type, (cls,), classdict)

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
