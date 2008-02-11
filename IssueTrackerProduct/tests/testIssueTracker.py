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

from Products.IssueTrackerProduct.Permissions import IssueTrackerManagerRole, IssueTrackerUserRole
from Products.IssueTrackerProduct.Constants import ISSUEUSERFOLDER_METATYPE

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
        
        
    def test_debatingIssue_withSmartAvoidanceOfNotifications_part2(self):
        """ same test_debatingIssue_withSmartAvoidanceOfNotifications() but this time
        test what happens if an issue is created with always notify on or
        an issue is assigned to someone. """
        
        
        tracker = self.folder.tracker
        
        # Important
        tracker.dispatch_on_submit = False
        
        # add an issue user folder
        # Since manage_addIssueUserFolder() needs to add the two extra roles
        # we have to do that first because manage_addIssueUserFolder() isn't
        # allowed to it because it's not a POST request.
        tracker._addRole(IssueTrackerUserRole)
        tracker._addRole(IssueTrackerManagerRole)
        tracker.manage_addProduct['IssueTrackerProduct']\
          .manage_addIssueUserFolder(keep_usernames=True)
        tracker.acl_users.userFolderAddUser("user", "secret", [IssueTrackerUserRole], [],
                                            email="user@test.com",
                                            fullname="User Name")

        # make the always notify of issuetracker be 'user' and A
        A = 'a@a.com'
        Af = 'Aaa'
        
        checked = []
        for each in (A, 'user'):
            valid, better_spelling = tracker._checkAlwaysNotify(each)
            if valid:
                checked.append(better_spelling)
        tracker.always_notify = checked

        # If someone else now adds an issue, a notification should
        # be made going out to user@test.com adn a@a.com
        
        B = u'email@address.com'
        Bf = u'From name'
        
        request = self.app.REQUEST
        request.set('title', u'TITLE')
        request.set('fromname', Bf)
        request.set('email', B)
        request.set('description', u'DESCRIPTION')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        tracker.SubmitIssue(request)
        
        issue = tracker.getIssueObjects()[0]
        
        # have a look at that notification object
        self.assertEqual(len(issue.getCreatedNotifications()), 1)
        notification = issue.getCreatedNotifications()[0]
        self.assertFalse(notification.isDispatched())
        self.assertEqual(notification.getEmails(), ['a@a.com','user@test.com'])
        
        # now, if a@a.com follows up on B's new issue, there'll be
        # you can cross off a@a.com from the notification
        # object.
        request.set('comment', u'COMMENT')
        request.set('fromname', Af)
        request.set('email', A)
        request.set('notify', 1)
        issue.ModifyIssue(request)
        
        # there should now be a new notification object where
        # the latest one goes out to the submitter of the issue
        self.assertEqual(len(issue.getCreatedNotifications()), 2)
        latest_notification = issue.getCreatedNotifications(sort=True)[-1]
        self.assertEqual(latest_notification.getEmails(), [B])
        
        
        
    def test_debatingIssue_withSmartAvoidanceOfNotifications_part3(self):
        """ same as test_debatingIssue_withSmartAvoidanceOfNotifications() 
        but create an assignment and then later as that assignee, 
        participate in the issue and that should cancel the notification
        going out to the assignee. 
        """
        
        
        tracker = self.folder.tracker
        
        # Important
        tracker.dispatch_on_submit = False
        
        # add an issue user folder
        # Since manage_addIssueUserFolder() needs to add the two extra roles
        # we have to do that first because manage_addIssueUserFolder() isn't
        # allowed to it because it's not a POST request.
        tracker._addRole(IssueTrackerUserRole)
        tracker._addRole(IssueTrackerManagerRole)
        tracker.manage_addProduct['IssueTrackerProduct']\
          .manage_addIssueUserFolder(keep_usernames=True)
        tracker.acl_users.userFolderAddUser("user", "secret", [IssueTrackerUserRole], [],
                                            email="user@test.com",
                                            fullname="User Name")

        # switch on issue assignment
        tracker.manage_UseIssueAssignmentToggle()
        self.assertEqual(len(tracker.getAllIssueUsers()), 1)
        assignee_option = tracker.getAllIssueUsers()[0]
        self.assertEqual(assignee_option['user'].getUserName(), 'user')
        
        # If someone else now adds an issue, a notification should
        # be made going out to user@test.com adn a@a.com
        
        B = u'email@address.com'
        Bf = u'From name'
        
        request = self.app.REQUEST
        request.set('title', u'TITLE')
        request.set('fromname', Bf)
        request.set('email', B)
        request.set('description', u'DESCRIPTION')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        request.set('assignee', tracker.getAllIssueUsers()[0]['identifier'])
        request.form['notify-assignee'] = '1'
        tracker.SubmitIssue(request)
        
        issue = tracker.getIssueObjects()[0]
        
        # have a look at that notification object
        self.assertEqual(len(issue.getCreatedNotifications()), 1)
        notification = issue.getCreatedNotifications()[0]
        self.assertFalse(notification.isDispatched())
        self.assertEqual(notification.getEmails(), ['user@test.com'])
        self.assertTrue(notification.getAssignmentObject() is not None)
        assignment = notification.getAssignmentObject()
        self.assertEqual(assignment.getEmail(), B) # who added it
        self.assertEqual(assignment.getAssigneeEmail(), "user@test.com") # assigned to

        # log in as this assignee
        uf = tracker.acl_users
        assert uf.meta_type == ISSUEUSERFOLDER_METATYPE
        user = uf.getUserById('user')
        user = user.__of__(uf)
        newSecurityManager(None, user)

        assert getSecurityManager().getUser().getUserName() == 'user'

        # now reply a comment as this logged in user which should
        # evetually nullify the notification going to this assignee
        
        request.set('comment', u'COMMENT')
        #request.set('fromname', Af)
        #request.set('email', A)
        request.set('notify', 1)
        issue.ModifyIssue(request)
        
        # there should now be a new notification object where
        # the latest one goes out to the submitter of the issue
        self.assertEqual(len(issue.getCreatedNotifications()), 1)
        latest_notification = issue.getCreatedNotifications()[0]
        self.assertEqual(latest_notification.getEmails(), [B])
        
        
        
    def test_Real0695_bug(self): # in lack of a better name 
        """ test that RSS and RDF feeds have the same security protection
        like viewing the issuetracker, the list of issues or an issue. """
        tracker = self.folder.tracker
        request = self.app.REQUEST

        # Adding an issue
        add_issue_html = tracker.AddIssue(request)
        self.assertTrue(add_issue_html.find('Description:') > -1)
        
        # add an issue so there's something in the ListIssues, and the XML feeds
        A = u'email@address.com'
        Af = u'From name'
        request.set('title', u'TITLE')
        request.set('fromname', Af)
        request.set('email', A)
        request.set('description', u'DESCRIPTION')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        tracker.SubmitIssue(request)
        

        # first of all, viewing these with the current user should be fine.
        #template_list_html = tracker.ListIssues(request)
        template_list_html = tracker.restrictedTraverse('ListIssues')(request)
        # expect it to say "# Issues: 0" since there are no issues added
        self.assertTrue(template_list_html.find('# Issues: 1') > -1)

        # rss.xml
        rss_xml = getattr(tracker, 'rss.xml')()
        self.assertTrue(rss_xml.find('<title><![CDATA[TITLE (Open)]]></title>') > -1)
        
        # rdf.xml
        rdf_xml = getattr(tracker, 'rdf.xml')()
        self.assertTrue(rdf_xml.find('<title>TITLE (Open)</title>') > -1)
        
        # Now, let's disallow anonymous access
        msg = tracker.manage_ViewPermissionToggle()
        self.assertEqual(msg, 'View permission disabled for Anonymous')
        
        # before we log out, let's create a user with the IssueTracker 
        # IssueTrackerManagerRole
        self.folder.acl_users.userFolderAddUser("manager", "secret", [IssueTrackerManagerRole], [])
        self.folder.acl_users.userFolderAddUser("user", "secret", [IssueTrackerUserRole], [])

        # Now, if I log out, none of the viewings above should work
        self.logout()
        assert getSecurityManager().getUser().getUserName() == 'Anonymous User'
        
        from zExceptions import Unauthorized

        self.assertRaises(Unauthorized, tracker.restrictedTraverse, 'ListIssues')
        self.assertRaises(Unauthorized, tracker.restrictedTraverse, 'rss.xml')
        self.assertRaises(Unauthorized, tracker.restrictedTraverse, 'rdf.xml')
        

        
    def test_preSubmitIssue_hook(self):
        """ test adding an issue with a script hook called 'pre_SubmitIssue()' """
        tracker = self.folder.tracker
        tracker.dispatch_on_submit = False # no annoying emails on stdout
        
        adder = tracker.manage_addProduct['PythonScripts'].manage_addPythonScript
        adder('pre_SubmitIssue')
        script = getattr(tracker, 'pre_SubmitIssue')
        script.write(pre_submitissue_script_src)
        
        # With this hook it won't be possible to add a issue where
        # the subject line starts with the letter a. (silly, yes)
        
        request = self.app.REQUEST
        request.set('title', u'A TITLE')
        request.set('fromname', u'From name')
        request.set('email', u'email@address.com')
        request.set('description', u'DESCRIPTION')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        
        tracker.SubmitIssue(request)
        
        self.assertEqual(len(tracker.getIssueObjects()), 0)

        request.set('title', u'Some TITLE')

        tracker.SubmitIssue(request)
        
        self.assertEqual(len(tracker.getIssueObjects()), 1)

        
        
    def test_postSubmitIssue_hook(self):
        """ test adding an issue with a script hook called 'post_SubmitIssue()' """
        tracker = self.folder.tracker
        tracker.dispatch_on_submit = False # no annoying emails on stdout
        tracker.can_add_new_sections = True
        
        # add an issue user folder
        # Since manage_addIssueUserFolder() needs to add the two extra roles
        # we have to do that first because manage_addIssueUserFolder() isn't
        # allowed to it because it's not a POST request.
        tracker._addRole(IssueTrackerUserRole)
        tracker._addRole(IssueTrackerManagerRole)
        tracker.manage_addProduct['IssueTrackerProduct']\
          .manage_addIssueUserFolder(keep_usernames=True)
        tracker.acl_users.userFolderAddUser("user", "secret", [IssueTrackerManagerRole,'Manager'], [],
                                            email="user@test.com",
                                            fullname="User Name")
        
        
        adder = tracker.manage_addProduct['PythonScripts'].manage_addPythonScript
        adder('post_SubmitIssue')
        script = getattr(tracker, 'post_SubmitIssue')
        script.write(post_submitissue_script_src)
        
        # With this hook it won't be possible to add a issue where
        # the subject line starts with the letter a. (silly, yes)
        
        request = self.app.REQUEST
        request.set('title', u'A TITLE')
        request.set('fromname', u'From name')
        request.set('email', u'email@address.com')
        request.set('description', u'DESCRIPTION')
        request.set('newsection', 'Security')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())

        uf = tracker.acl_users
        assert uf.meta_type == ISSUEUSERFOLDER_METATYPE
        user = uf.getUserById('user')
        user = user.__of__(uf)
        newSecurityManager(None, user)

        assert getSecurityManager().getUser().getUserName() == 'user'
        
        print getSecurityManager().getUser().getRoles()
        
        tracker.SubmitIssue(request)
        self.assertEqual(len(tracker.getIssueObjects()), 1)
        
        issue = tracker.getIssueObjects()[0]
        print issue.getSections()

        
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(IssueTrackerTestCase))
    return suite
    
if __name__ == '__main__':
    framework()
        

