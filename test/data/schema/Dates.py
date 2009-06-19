from yams.buildobjs import EntityType, Datetime, Date, Time

class Datetest(EntityType):
    dt1 = Datetime(default=u'now')
    dt2 = Datetime(default=u'today')
    d1  = Date(default=u'today')
    d2  = Date(default=u'2007/12/11')
    t1  = Time(default=u'08:40')
    t2  = Time(default=u'09:45')

