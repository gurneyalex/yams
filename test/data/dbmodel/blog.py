from google.appengine.ext import db

class Article(db.Model):
    content = db.TextProperty()
    synopsis = db.StringProperty(default='hello')
    image = db.BlobProperty(required=True)


class Blog(db.Model):
    diem = db.DateProperty(required=True, auto_now_add=True)
    content = db.TextProperty()
    itemtype = db.StringProperty(required=True, choices=('personal', 'business'))
    talks_about = db.ReferenceProperty(Article)
    cites = db.SelfReferenceProperty()
