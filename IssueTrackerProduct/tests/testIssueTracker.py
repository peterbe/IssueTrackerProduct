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


import Acquisition

ZopeTestCase.installProduct('MailHost')
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZCTextIndex')
ZopeTestCase.installProduct('SiteErrorLog')
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
    
class IssueTrackerTestCase(TestBase):
    
    def test_addingIssue(self):
        """ test something """
        #self.tracker = self.folder['mexpenses']
        tracker = self.folder.tracker
        
        request = self.app.REQUEST
        request.set('title', u'TITLE')
        request.set('fromname', u'From name')
        request.set('email', u'email@address.com')
        request.set('description', u'DESCRIPTION')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        
        tracker.SubmitIssue(request)
        
        self.assertEqual(len(tracker.getIssueObjects()), 1)
        
        
    def test_modifyingIssue(self):
        """ test something """
        #self.tracker = self.folder['mexpenses']
        tracker = self.folder.tracker
        
        request = self.app.REQUEST
        request.set('title', u'TITLE')
        request.set('fromname', u'From name')
        request.set('email', u'email@address.com')
        request.set('description', u'DESCRIPTION')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        tracker.SubmitIssue(request)
        
        issue = tracker.getIssueObjects()[0]
        
        request.set('comment', u'COMMENT')
        issue.ModifyIssue(request)
        
        self.assertEqual(len(issue.getThreadObjects()), 1)
        
        
    def test_debatingIssue(self):
        """ test posting a followup under a different email address than the original """
        tracker = self.folder.tracker
        
        request = self.app.REQUEST
        request.set('title', u'TITLE')
        request.set('fromname', u'From name')
        request.set('email', u'email@address.com')
        request.set('description', u'DESCRIPTION')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        tracker.SubmitIssue(request)
        
        issue = tracker.getIssueObjects()[0]
        
        request.set('comment', u'COMMENT')
        request.set('fromname', u'Someone Else')
        request.set('email', u'else@address.com')
        request.set('notify', 1)
        issue.ModifyIssue(request)
        
        # there should now be a notifiation object
        self.assertEqual(len(issue.getCreatedNotifications()), 1)
        
        # have a look at that notification object
        notification = issue.getCreatedNotifications()[0]
        self.assertEqual(notification.getTitle(), u'TITLE')
        self.assertTrue(isinstance(notification.getTitle(), unicode))
        self.assertEqual(notification.getIssueID(), issue.getId())
        self.assertEqual(notification.getEmails(), [u'email@address.com'])
        if tracker.doDispatchOnSubmit():
            self.assertTrue(notification.isDispatched())
            
            
    def test_debatingIssue_withSmartAvoidanceOfNotifications(self):
        """ If A posts an issue, B follows up and shortly there after A 
        follows up too, then if the automatic dispatcher is switched off,
        the notification to A can be ignored since A has already seen the 
        followup.
        """
        tracker = self.folder.tracker
        
        # Important
        tracker.dispatch_on_submit = False
        
        A = u'email@address.com'
        Af = u'From name'
        
        request = self.app.REQUEST
        request.set('title', u'TITLE')
        request.set('fromname', Af)
        request.set('email', A)
        request.set('description', u'DESCRIPTION')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        tracker.SubmitIssue(request)

        
        B = u'else@address.com'
        Bf = u'Someone Else'
        
        issue = tracker.getIssueObjects()[0]
        request.set('comment', u'COMMENT')
        request.set('fromname', Bf)
        request.set('email', B)
        request.set('notify', 1)
        issue.ModifyIssue(request)
        
        # have a look at that notification object
        notification = issue.getCreatedNotifications()[0]
        self.assertFalse(notification.isDispatched())            

        # A returns and posts a followup
        request.set('comment', u'REPLY')
        request.set('fromname', Af)
        request.set('email', A)
        request.set('notify', 1)
        issue.ModifyIssue(request)

        # Since the second followup done by A must mean that A
        # doesn't need to be notified about the first notification
        # since A has already made a newer followup.
        # However, B's notification should still be there.
        
        self.assertEqual(len(issue.getCreatedNotifications()), 1)
        notification = issue.getCreatedNotifications()[0]
        # this should be designated to B
        self.assertEqual(notification.getEmails(), [B])
        
        # Ok, let's do it again.
        # Now, C joins in so that each notification is designated
        # to two people. By adding a followup by A or B, there is 
        # no need to send out the notification to A or B.
        
        C = u'C@email.com'
        Cf = u'Mr. C'
        
        request.set('comment', u'COMMENT BY C')
        request.set('fromname', Cf)
        request.set('email', C)
        request.set('notify', 1)
        issue.ModifyIssue(request)
        
        # there should now be one new notification designated
        # to A AND B.
        
        self.assertEqual(len(issue.getCreatedNotifications()), 2)
        # let's look at the latest notification
        notification = issue.getCreatedNotifications(sort=True)[1]
        self.assertEqual(notification.getEmails(), [A, B])
        
        request.set('comment', u'COMMENT BY B again')
        request.set('fromname', Bf)
        request.set('email', B)
        request.set('notify', 1)
        issue.ModifyIssue(request)        
        
        self.assertEqual(len(issue.getCreatedNotifications()), 2)
        # let's look at the latest notification
        notification = issue.getCreatedNotifications(sort=True)[1]
        self.assertEqual(notification.getEmails(), [A, C])

    
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(IssueTrackerTestCase))
    return suite
    
if __name__ == '__main__':
    framework()
        

