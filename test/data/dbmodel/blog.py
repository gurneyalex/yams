# copyright 2004-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of yams.
#
# yams is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 2.1 of the License, or (at your option)
# any later version.
#
# yams is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with yams. If not, see <http://www.gnu.org/licenses/>.
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
