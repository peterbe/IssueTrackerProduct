# -*- coding: iso-8859-1 -*
##
## <peter@fry-it.com>
##


import unittest
import random

import sys, os
import stat
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Globals import SOFTWARE_HOME    
from Testing import ZopeTestCase
from AccessControl import getSecurityManager
from AccessControl.SecurityManagement import newSecurityManager
from DateTime import DateTime

import Acquisition

ZopeTestCase.installProduct('MailHost')
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZCTextIndex')
ZopeTestCase.installProduct('SiteErrorLog')
ZopeTestCase.installProduct('PythonScripts')
ZopeTestCase.installProduct('IssueTrackerProduct')

#------------------------------------------------------------------------------
#
# Some constants
#

#------------------------------------------------------------------------------

# Open ZODB connection
app = ZopeTestCase.app()
        
# Set up sessioning objects
ZopeTestCase.utils.setupCoreSessions(app)

# Set up the error log
ZopeTestCase.utils.setupSiteErrorLog(app)

# Set up example applications
#if not hasattr(app, 'Examples'):
#    ZopeTestCase.utils.importObjectFromFile(app, examples_path)
        
# Close ZODB connection
ZopeTestCase.close(app)

    

#------------------------------------------------------------------------------

class TestBase(ZopeTestCase.ZopeTestCase):

    def dummy_redirect(self, *a, **kw):
        self.has_redirected = a[0]
        if kw:
            print "*** Redirecting to %r + (%s)" % (a[0], kw)
        else:
            print "*** Redirecting to %r" % a[0]
    
    def afterSetUp(self):
        # install an issue tracker
        dispatcher = self.folder.manage_addProduct['IssueTrackerProduct']
        dispatcher.manage_addIssueTracker('tracker', 'Issue Tracker')
        
        # install an error_log
        #dispatcher = self.folder.manage_addProduct['SiteErrorLog']
        #dispatcher.manage_addErrorLog()
        
        
        # if you set this override you won't be able to do a transaction.get().commit()
        # in the unit tests.
        #self.mexpenses.http_redirect = self.dummy_redirect 
        
        #request = self.app.REQUEST
        #sdm = self.app.session_data_manager
        #request.set('SESSION', sdm.getSessionData())
        
        #self.has_redirected = False

        
from Products.IssueTrackerProduct.Constants import UNICODE_ENCODING        

class CustomFieldTestCase(TestBase):
    """ 
    """
    
    def _createCustomField(self, id=None, title=None, **kw):
        if id is None:
            id = str(int(10000*random.random()))
        if title is None:
            title = unicode(int(10000*random.random()))
        
        tracker = self.folder.tracker
        adder = tracker.manage_addProduct['IssueTrackerProduct'].manage_addCustomField
            
        return adder(id, title, **kw)
    
    
    def test_creatingCustomField(self):
        """ test to create a custom field account """
        tracker = self.folder.tracker
        
        # if you create a custom field in a tracker with 'create_in_folder'
        # it will make sure it creates the custom field in a 
        # Custom Field Folder object.
        adder = tracker.manage_addProduct['IssueTrackerProduct'].manage_addCustomField
        obj = adder('xxx','title', create_in_folder=True)
        self.assertEqual(obj.getId(), 'xxx')
        self.assertEqual(obj.getTitle(), u'title')
        self.assertTrue(isinstance(obj.getTitle(), unicode))
        self.failUnless(obj.aq_parent.meta_type.endswith('Custom Field Folder'))

        # create another shouldn't create *another* folder
        new_obj = adder('yyy', 'title2', create_in_folder=True)
        self.failUnless(new_obj.aq_parent.absolute_url()== obj.aq_parent.absolute_url())
        
    def test_basic_rendering(self):
        """ basic rendering """
        
        obj = self._createCustomField(id='a', title='A', create_in_folder=True)
        
        rendered = obj.render()
        
        # the rendered HTML should be in unicode
        self.assertTrue(isinstance(rendered, unicode))
        # the __str__ should be ascii if possible
        self.assertTrue(isinstance(str(obj), str))
        
        # expect to find certain things in it
        self.assertTrue(rendered.find('name="a:%s:ustring"'% UNICODE_ENCODING) > -1)
        self.assertTrue(rendered.find('id="id_a"') > -1)
        
    def test_basic_rendering_extra_attributes(self):
        """ basic rendering """
        
        obj = self._createCustomField(id='a', title='A', create_in_folder=True)
        
        rendered = obj.render(id='customid', size=10)
        
        # expect to find certain things in it
        self.assertTrue(rendered.find('id="customid"') > -1)        
        self.assertTrue(rendered.find('size="10"') > -1)
        
        
    def test_basic_rendering_with_extra(self):
        """ basic rendering """
        
        css = 'body{}'
        js = 'alert(document)'
        obj = self._createCustomField(id='a', title='A', create_in_folder=True,
                                      extra_css=css, extra_js=js)
        
        rendered = obj.render()
        
        # in this we should find certain things
        found_css = rendered.find(u'<style type="text/css">\nbody{}\n</style>'); assert found_css > -1
        found_js = rendered.find(u'<script type="text/javascript">\nalert(document)\n</script>'); assert found_js > -1
        found_tag = rendered.find(u'<input id="id_a" name="a:%s:ustring" title="A" />' % UNICODE_ENCODING)
        assert found_tag > -1, rendered
        assert -1 < found_css < found_js < found_tag
        

    def test_render_css(self):
        """ test the <customfield>.render_extra_css() method """
        
        # a path
        obj = self._createCustomField(extra_css='/foo/bar.css')
        rendered = obj.render_extra_css()
        self.assertEqual(rendered, u'<link rel="stylesheet" type="text/css" href="/foo/bar.css" />')
        
        # a payload
        obj = self._createCustomField(extra_css='body { }')
        rendered = obj.render_extra_css()
        self.assertEqual(rendered, u'<style type="text/css">\nbody { }\n</style>')
        
        # nothing
        obj = self._createCustomField()
        rendered = obj.render_extra_css()
        self.assertEqual(rendered, u'')
        
    def test_render_js(self):
        """ test the <customfield>.render_extra_js() method """
        
        # a path
        obj = self._createCustomField(extra_js='foo/bar.js')
        rendered = obj.render_extra_js()
        self.assertEqual(rendered, u'<script type="text/javascript" src="foo/bar.js"></script>')
        
        # a payload
        obj = self._createCustomField(extra_js='function foo() {return;}')
        rendered = obj.render_extra_js()
        self.assertEqual(rendered, u'<script type="text/javascript">\nfunction foo() {return;}\n</script>')
        
        # nothing
        obj = self._createCustomField()
        rendered = obj.render_extra_js()
        self.assertEqual(rendered, u'')
        
    def test_rendering_select(self):
        """ basic rendering """
        
        obj = self._createCustomField(id='a', title='A', 
                                      input_type='select',
                                      options=[('x','X'), ('y','Y')],
                                      )
        
        rendered = obj.render()
        assert rendered.find('id="id_a"') > -1
        assert rendered.find('name="a:%s:ustring"' % UNICODE_ENCODING) > -1
        assert rendered.find('title="A"') > -1
        found_select = rendered.find(u'<select ')
        found_option1 = rendered.find(u'<option value="x">X</option>')
        found_option2 = rendered.find(u'<option value="y">Y</option>')
        found_close = rendered.find(u'</select>')
        assert -1 < found_select < found_option1 < found_option2 < found_close
        
        rendered = obj.render(multiple="multiple")
        found_select = rendered.find(u'<select ')
        found_attr = rendered.find(u'multiple="multiple"')
        found_option1 = rendered.find(u'<option value="x">X</option>')
        found_option2 = rendered.find(u'<option value="y">Y</option>')
        found_close = rendered.find(u'</select>')
        assert -1 < found_select < found_attr < found_option1 < found_option2 < found_close
        
        # what if you want to render it with a particular value
        rendered = obj.render('y')
        found_option1 = rendered.find(u'<option value="x">X</option>')
        found_option2 = rendered.find(u'<option value="y" selected="selected">Y</option>')
        assert -1 < found_option1 < found_option2
        
        # the passed in value can be a list or a tuple
        rendered = obj.render(['y','x'])
        found_option1 = rendered.find(u'<option value="x" selected="selected">X</option>')
        found_option2 = rendered.find(u'<option value="y" selected="selected">Y</option>')
        assert -1 < found_option1 < found_option2
        

    def test_options_expression(self):
        """ if a custom field has a TALES expression on the options_expression
        it needs to be valid for options.
        """
        obj = self._createCustomField(id='a', title='A', create_in_folder=True,
                                      input_type='select'
                                      )
        obj.options_expression = "python:[('a','A'), ('b','B') ]"
        self.assertTrue(obj._valid_options_expression())
        
        obj.options_expression = "python:(u'\xa3', u'\xe4')"
        self.assertTrue(obj._valid_options_expression())
        
        obj.options_expression = "python:['a', ('b','B') ]"
        self.assertTrue(obj._valid_options_expression())
        
        # can't let keys be non-unicode
        obj.options_expression = "python:[('a',nothing), ('b','B') ]"
        self.assertTrue(obj._valid_options_expression())
        
        obj.options_expression = "python:request"
        self.assertFalse(obj._valid_options_expression())
        
        # now, let's try to make it a bit more complicated
        obj.options_expression = "here/objectIds"
        self.assertTrue(obj._valid_options_expression())
        
        obj.options_expression = "here/aq_parent/objectIds"
        self.assertTrue(obj._valid_options_expression())
        
        obj.options_expression = "request/keys"
        self.assertTrue(obj._valid_options_expression())


        # and referring to self
        # this should work since we're logged in with the
        obj.options_expression = "python:[path('object/absolute_url')]"
        self.assertTrue(obj._valid_options_expression())
        
        obj.options = ('x','y','z')
        obj.options_expression = "python:('x','y','z')"
        assert obj._valid_options_expression()
        self.assertEqual(obj.getOptionsIterable(), ['x','y','z'])
        
        
    def test_with_requestform_variables_already_set(self): # crap name!
        """ if certain values are already set in REQUEST.form they
        should be picked up if you render the field.
        """
        obj = self._createCustomField(id='age', title='Age', create_in_folder=True,
                                      input_type='text', python_type='int'
                                      )
        html = obj.render()
        expect = '<input id="id_age" name="age:int" title="Age" />'
        self.assertEqual(html, expect)
        
        self.app.REQUEST.form['age'] = 123
        html = obj.render(self.app.REQUEST)
        expect = '<input id="id_age" name="age:int" title="Age" '\
                 'value="123" />'
        
        # But what if the field as a default value
        #obj = self._createCustomField(id='age', title='Age', create_in_folder=True,
        #                              input_type='text', python_type='int'
        #                              )
        obj.manage_saveFieldProperties(value='0')
        
        html = obj.render()
        expect = '<input id="id_age" name="age:int" title="Age" value="0" />'
        self.assertEqual(html, expect)

        
    def test_basic_input_validation(self):
        """ a custom field can have a default python type, for example 'int'
        which means that we can do a basic validation test. 
        """
        age = self._createCustomField(id='age', title='Age', create_in_folder=True,
                                      python_type='int'
                                      )
        date = self._createCustomField(id='date', title='Date', create_in_folder=True,
                                      python_type='date'
                                      )
        height = self._createCustomField(id='height', title='Height', create_in_folder=True,
                                      python_type='float'
                                      )
                                      
        # the fields have a method called testValidValue() which you 
        # can throw a value at and return a tuple (bool, msg)
        self.assertEqual(age.testValidValue(20), (True, None))
        self.assertEqual(age.testValidValue('20'), (True, None))
        self.assertEqual(age.testValidValue('XX'), (False, u'Not an integer number'))
        
        self.assertEqual(date.testValidValue('2007/01/01'), (True, None))
        self.assertEqual(date.testValidValue('13/12/1979'), (True, None))
        self.assertEqual(date.testValidValue(DateTime()), (True, None))
        self.assertEqual(date.testValidValue('2012/13/13'), (False, u'Not a valid date'))
        
        self.assertEqual(height.testValidValue(20), (True, None))
        self.assertEqual(height.testValidValue(1.3333333333), (True, None))
        self.assertEqual(height.testValidValue('20.3'), (True, None))
        self.assertEqual(height.testValidValue('XX'), (False, u'Not a floating point number'))
        
        
        
    def test_tales_input_validation(self):
        """ a custom field can have a 0 or more validation expressions that
        are rendered by SubmitIssue. If any of them fails you get 
        the validation is considered failed.
        """
        age = self._createCustomField(id='age', title='Age', create_in_folder=True,
                                      python_type='int'
                                      )
        self.assertEqual(age.testValidValue(4), (True, None))
        
        age.manage_addValidationExpression('python:value > 5', "Less or equal to 5")
        self.assertEqual(age.testValidValue(4), (False, u"Less or equal to 5"))
        self.assertEqual(age.testValidValue(6), (True, None))
        
    def test_getCustomFieldObjects(self):
        """ test asking the issuetracker for custom fields """
        def make(id, python_type='ustring', create_in_folder=True):
            return self._createCustomField(id=id, title=id.title(),
                                           create_in_folder=create_in_folder,
                                           python_type=python_type
                                           )
        age = make('age')
        date = make('date')
        height = make('height')
        
        # make one outside
        weight = make('weight', create_in_folder=False)
        
        tracker = self.folder.tracker
        fields = tracker.getCustomFieldObjects()
        
        self.assertEqual(len(fields), 4)
        
        # disable one of them 
        date.disabled = True
        fields = tracker.getCustomFieldObjects()
        self.assertEqual(len(fields), 3)
        
        # set a visibility expression on one of them
        date.disabled = False
        fields = tracker.getCustomFieldObjects()
        assert len(fields) == 4
        
        date.visibility_expression = 'python:0'
        fields = tracker.getCustomFieldObjects()
        self.assertEqual(len(fields), 3)
        # reset
        date.visibility_expression = ''
        
        # filter by ids
        fields = tracker.getCustomFieldObjects(['weight','age'])
        self.assertEqual(len(fields), 2)
        # the order should be as input
        self.assertEqual([x.getId() for x in fields], ['weight','age'])
        
        # filter by ids by a function
        filter_function = lambda x: x.getId() in ('height', 'date')
        fields = tracker.getCustomFieldObjects(filter_function)
        self.assertEqual(len(fields), 2)
        
        # filter by if they should be included in filter options
        filter_function = lambda x: x.includeInFilterOptions()
        fields = tracker.getCustomFieldObjects(filter_function)
        self.assertEqual(len(fields), 0)
        
        age.include_in_filter_options = True
        
        filter_function = lambda x: x.includeInFilterOptions()
        fields = tracker.getCustomFieldObjects(filter_function)
        self.assertEqual(len(fields), 1)
        
        
        
        
        
        

        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(CustomFieldTestCase))
    return suite
    
if __name__ == '__main__':
    framework()
        

