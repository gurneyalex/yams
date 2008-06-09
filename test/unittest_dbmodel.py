"""tests for db.Model => yams schema conversion
"""

from logilab.common.testlib import TestCase, unittest_main

import os.path as osp
import new
from mx.DateTime import today

try:
    from yams.gae import GaeSchemaLoader
except ImportError:
    GaeSchemaLoader = None

from yams.schema import Schema

class DbModelTC(TestCase):

    def setUp(self):
        if GaeSchemaLoader is None:
            self.skip('could not import appengine')
        self.loader = GaeSchemaLoader()
    
    def import_module(self, modname):
        mod = new.module(modname)
        fname = osp.join(self.datadir, 'dbmodel', '%s.py' % modname)
        execfile(fname, mod.__dict__)
        return mod

    def test_entity_types(self):
        blog = self.import_module('blog')
        schema = self.loader.load_module(blog, True)
        self.assert_(isinstance(schema, Schema))
        etypes = [eschema.type for eschema in schema.entities()
                  if not eschema.is_final()]
        self.assertSetEquals(etypes, ['Blog', 'Article'])
    
    def test_blog_conversion(self):
        blog = self.import_module('blog')
        schema = self.loader.load_module(blog, True)
        blog = schema.eschema('Blog')
        attrs = [rschema.type for (rschema, _) in
                 blog.attribute_definitions()]
        self.assertEquals(attrs, ['diem', 'content', 'itemtype'])
        # test diem properties
        diem = blog.destination('diem')
        self.assertEquals(diem.type, 'Date')
        self.assertEquals(blog.default('diem'), today())
        self.assertEquals(blog.rproperty('diem', 'cardinality')[0], '1')
        self.assertEquals(blog.rproperty('diem', 'constraints'), ())
        # test content properties
        content = blog.destination('content')
        self.assertEquals(content.type, 'String')
        self.assertEquals(blog.default('content'), None)
        self.assertEquals(blog.rproperty('content', 'cardinality')[0], '?')
        self.assertEquals(blog.rproperty('content', 'constraints'), ())
        # test itemtype properties
        itemtype = blog.destination('itemtype')
        self.assertEquals(itemtype.type, 'String')
        self.assertEquals(blog.default('itemtype'), None)
        self.assertEquals(blog.rproperty('itemtype', 'cardinality')[0], '1')
        constraints = [(cstr.type(), cstr.serialize())
                       for cstr in blog.rproperty('itemtype', 'constraints')]
        self.assertSetEquals(constraints,
                             [('SizeConstraint', 'max=8'),
                              ('StaticVocabularyConstraint', "u'personal', u'business'")])
        # test talks_about properties
        talks_about = blog.subject_relation('talks_about')
        self.failIf(talks_about.is_final())
        self.assertEquals(talks_about.objects(), ['Article'])
        # test cites properties
        talks_about = blog.subject_relation('cites')
        self.failIf(talks_about.is_final())
        self.assertEquals(talks_about.objects(), ['Blog'])
        
    def test_article_conversion(self):
        article = self.import_module('blog')
        schema = self.loader.load_module(article, True)
        article = schema.eschema('Article')
        attrs = [rschema.type for (rschema, _) in
                 article.attribute_definitions()]
        self.assertEquals(attrs, ['content', 'synopsis', 'image'])
        # test content properties
        content = article.destination('content')
        self.assertEquals(content.type, 'String')
        self.assertEquals(article.default('content'), None)
        self.assertEquals(article.rproperty('content', 'cardinality')[0], '?')
        self.assertEquals(article.rproperty('content', 'constraints'), ())
        # test synopsis properties
        synopsis = article.destination('synopsis')
        self.assertEquals(synopsis.type, 'String')
        self.assertEquals(article.default('synopsis'), 'hello')
        self.assertEquals(article.rproperty('synopsis', 'cardinality')[0], '?')
        constraints = [(cstr.type(), cstr.serialize())
                       for cstr in article.rproperty('synopsis', 'constraints')]
        self.assertSetEquals(constraints, [('SizeConstraint', 'max=500'),])
        # test image properties
        image = article.destination('image')
        self.assertEquals(image.type, 'Bytes')
        self.assertEquals(article.default('image'), None)
        self.assertEquals(article.rproperty('image', 'cardinality')[0], '1')
        self.assertEquals(article.rproperty('image', 'constraints'), ())
if __name__ == '__main__':
    unittest_main()
