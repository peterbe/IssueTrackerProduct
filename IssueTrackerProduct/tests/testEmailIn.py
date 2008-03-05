# -*- coding: iso-8859-1 -*
##
## <peter@fry-it.com>
##

import unittest

import sys, os
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Globals import SOFTWARE_HOME    
from Testing import ZopeTestCase
from AccessControl import getSecurityManager
from AccessControl.SecurityManagement import newSecurityManager

import Acquisition

ZopeTestCase.installProduct('MailHost')
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZCTextIndex')
ZopeTestCase.installProduct('SiteErrorLog')
ZopeTestCase.installProduct('PythonScripts')
ZopeTestCase.installProduct('IssueTrackerProduct')

#from Products.IssueTrackerProduct.Permissions import IssueTrackerManagerRole, IssueTrackerUserRole
#from Products.IssueTrackerProduct.Constants import ISSUEUSERFOLDER_METATYPE


#------------------------------------------------------------------------------
#
# Some constants
#

#------------------------------------------------------------------------------

# Open ZODB connection
app = ZopeTestCase.app()
        
# Set up sessioning objects
ZopeTestCase.utils.setupCoreSessions(app)
        
# Set up example applications
#if not hasattr(app, 'Examples'):
#    ZopeTestCase.utils.importObjectFromFile(app, examples_path)
        
# Close ZODB connection
ZopeTestCase.close(app)

#------------------------------------------------------------------------------
pre_submitissue_script_src = """
## Script (Python) "pre_SubmitIssue"
##parameters=
##title=
##
request = context.REQUEST
title = request.get('title',u'')
if title.lower().startswith(u'a'):
    return {'title':u'Subject line must NOT start with an A'}
"""


post_submitissue_script_src = """
## Script (Python) "post_SubmitIssue"
##parameters=issue
##title=
##

if 'Security' in issue.getSections():
   # increase the urgency by one notch

   urgency = issue.getUrgency()

   options = issue.getUrgencyOptions() # acquired 

   try:
       urgency = options[options.index(urgency)+1]
   except IndexError:
       # was already at the topmost
       return
   issue.editIssueDetails(urgency=urgency)
   
"""
    

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
        dispatcher = self.folder.manage_addProduct['SiteErrorLog']
        dispatcher.manage_addErrorLog()
        
        
        # if you set this override you won't be able to do a transaction.get().commit()
        # in the unit tests.
        #self.mexpenses.http_redirect = self.dummy_redirect 
        
        request = self.app.REQUEST
        sdm = self.app.session_data_manager
        request.set('SESSION', sdm.getSessionData())
        
        #self.has_redirected = False
        
    def tearDown(self):
        pass


class POP3TestCase(TestBase):
    """ 
    Test to create a POP3 account object and several accepting email accounts
    inside it.
    """ 
    
    def test_creatingAccount(self):
        """ test to create a POP3 account """
        tracker = self.folder.tracker
        
        self.assertEqual(tracker.getPOP3Accounts(), [])
        
        tracker.createPOP3Account('mail.example.com', 'peter', 'secret')
        self.assertEqual(len(tracker.getPOP3Accounts()), 1)
        
        account = tracker.getPOP3Accounts()[0]
        self.assertEqual(account.getTitle(), 'mail.example.com')
        self.assertEqual(account.getHostname(), 'mail.example.com')
        self.assertEqual(account.getPort(), 110)
        self.assertEqual(account.getUsername(), 'peter')
        self.assertFalse(account.doDeleteAfter())
        self.assertFalse(account.doSSL())
        
        self.assertEqual(len(account.getAcceptingEmails()), 0)
        
        # try editing it
        account.manage_editAccount(hostname='m.example.com', username='peterbe', 
                            portnr=210, delete_after=1)
                            
        self.assertEqual(account.getHostname(), 'm.example.com')
        self.assertEqual(account.getPort(), 210)
        self.assertEqual(account.getUsername(), 'peterbe')
        self.assertTrue(account.doDeleteAfter())
    

    def test_creatingAcceptingEmail(self):
        """ test to create a POP3 account accepting email object """
        tracker = self.folder.tracker
        account = tracker.createPOP3Account('mail.example.com', 'peter', 'secret')
        
        # there are unfortunately two different ways to create accepting email
        # objects. Either directly on the account or via the issuetracker 
        # itself. With the latter option, you have to pass the ID of the 
        # account.
        # The latter one is more user friendly and easier to "access" because
        # that's what the DTML files do.
        ae = tracker.createAcceptingEmail(account.getId(), 'mail@example.com')
        self.assertEqual(ae.aq_parent.absolute_url(), account.absolute_url())
        
        
                 
        

class EmailInTestCase(TestBase):
    
    def test_acceptingEmail(self):
        """ test something """
        tracker = self.folder.tracker
        
        
        
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(POP3TestCase))
    suite.addTest(makeSuite(EmailInTestCase))
    return suite
    
if __name__ == '__main__':
    framework()
        

