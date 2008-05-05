# -*- coding: iso-8859-1 -*
##
## <peter@fry-it.com>
##

import unittest
from pprint import pprint

import sys, os
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Globals import SOFTWARE_HOME    
from Testing import ZopeTestCase
from AccessControl import getSecurityManager
from AccessControl.SecurityManagement import newSecurityManager, noSecurityManager

import Acquisition

ZopeTestCase.installProduct('MailHost')
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZCTextIndex')
ZopeTestCase.installProduct('SiteErrorLog')
ZopeTestCase.installProduct('PythonScripts')
ZopeTestCase.installProduct('IssueTrackerProduct')

from Products.IssueTrackerProduct.Permissions import IssueTrackerManagerRole, IssueTrackerUserRole
from Products.IssueTrackerProduct.Constants import ISSUEUSERFOLDER_METATYPE, \
 DEBUG, ISSUE_DRAFT_METATYPE, TEMPFOLDER_REQUEST_KEY

#------------------------------------------------------------------------------
#
# Some constants
#

#------------------------------------------------------------------------------

# Open ZODB connection
app = ZopeTestCase.app()
        
# Set up sessioning objects
ZopeTestCase.utils.setupCoreSessions(app)

ZopeTestCase.utils.setupSiteErrorLog(app)
        
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

class NewFileUpload:
    def __init__(self, file_path):
        self.file = open(file_path)
        self.filename = os.path.basename(file_path)
        self.file_path = file_path
        
    def read(self, bytes=None):
        if bytes:
            return self.file.read(bytes)
        else:
            return self.file.read()
    
    def seek(self, bytes, mode=0):
        self.file.seek(bytes, mode)
        
    def tell(self):
        return self.file.tell()
        
class DodgyNewFileUpload:
    """ a file upload that returns a blank string no when you read it """
    
    def __init__(self, file_path):
        self.file = open(file_path)
        self.filename = os.path.basename(file_path)
        self.file_path = file_path    
    
    def read(self, bytes=None, mode=0):
        return ""

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

        # install a MailHost
        if not DEBUG:
            dispatcher = self.folder.manage_addProduct['MailHost']
            dispatcher.manage_addMailHost('MailHost')
        
        # if you set this override you won't be able to do a transaction.get().commit()
        # in the unit tests.
        #self.mexpenses.http_redirect = self.dummy_redirect 
        
        request = self.app.REQUEST
        sdm = self.app.session_data_manager
        request.set('SESSION', sdm.getSessionData())
        
        #self.has_redirected = False
        
    def set_cookie(self, key, value, expires=365, path='/',
                   across_domain_cookie_=False,
                   **kw):
        
        self.app.REQUEST.cookies[key] = value
        
    #def beforeTearDown(self):
    def afterClear(self):
        global __trapped_emails__
        __trapped_emails__ = []
        
class TestFunctionalBase(ZopeTestCase.FunctionalTestCase):

    def afterSetUp(self):
        # install an issue tracker
        dispatcher = self.folder.manage_addProduct['IssueTrackerProduct']
        dispatcher.manage_addIssueTracker('tracker', 'Issue Tracker')

        # install a MailHost
        if not DEBUG:
            dispatcher = self.folder.manage_addProduct['MailHost']
            dispatcher.manage_addMailHost('MailHost')

        request = self.app.REQUEST
        sdm = self.app.session_data_manager
        request.set('SESSION', sdm.getSessionData())
            
    
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
        tracker.sitemaster_email = 'something@valid.com'

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

        # we should now expect an email to have been sent to email@address.com
        assert __trapped_emails__, "not trapped emails"
        latest_email = __trapped_emails__[0]
        self.assertTrue(latest_email['mto'].find('email@address.com') > -1)
        self.assertTrue(latest_email['mfrom'].find('something@valid.com') > -1)
        
            
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
        
        #print getSecurityManager().getUser().getRoles()
        #tracker.SubmitIssue(request)
        #self.assertEqual(len(tracker.getIssueObjects()), 1)
        #issue = tracker.getIssueObjects()[0]


    def test_getModifyTimestamp(self):
        """ test issuetracker.getModifyTimestamp() """
        tracker = self.folder.tracker
        
        # with no issues, the getModifyTimestamp() should be the 
        # same as the issuetrackers' bobobase_modification_time()
        self.assertEqual(int(tracker.bobobase_modification_time()), 
                         tracker.getModifyTimestamp())
                         
        # if we add an issue, the issuetrackers' getModifyTimestamp()
        # should be that of the last added issue.
        request = self.app.REQUEST
        request.set('title', u'TITLE')
        request.set('fromname', u'From name')
        request.set('email', u'email@address.com')
        request.set('description', u'DESCRIPTION')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        
        tracker.SubmitIssue(request)
        
        issue = tracker.getIssueObjects()[0]
        self.assertEqual(issue.getModifyTimestamp(), tracker.getModifyTimestamp())

    def test_okFileAttachment(self):
        """ try to add an issue with a crap file attachment """
        tracker = self.folder.tracker
        request = self.app.REQUEST
        request.set('title', u'TITLE')
        request.set('fromname', u'From name')
        request.set('email', u'email@address.com')
        request.set('description', u'DESCRIPTION')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        request.set('fileattachment', NewFileUpload(os.path.abspath(__file__)))
        
        tracker.SubmitIssue(request)
        issue = tracker.getIssueObjects()[0]
        self.assertEqual(issue.countFileattachments(), 1)
        
    def test_crapFileAttachment(self):
        """ try to add an issue with a crap file attachment """
        
        tracker = self.folder.tracker
        request = self.app.REQUEST
        request.set('title', u'TITLE')
        request.set('fromname', u'From name')
        request.set('email', u'email@address.com')
        request.set('description', u'DESCRIPTION')
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        request.set('fileattachment', DodgyNewFileUpload(os.path.abspath(__file__)))
        
        # this should fail to add an issue
        tracker.SubmitIssue(request)
        self.assertEqual(len(tracker.getIssueObjects()), 0)
        
        # this time, try to upload it with a file that is empty
        empty_file = os.path.join(os.path.dirname(__file__), 'size0_file.jpg')
        request.set('fileattachment', NewFileUpload(os.path.abspath(empty_file)))
        
        tracker.SubmitIssue(request)
        self.assertEqual(len(tracker.getIssueObjects()), 0)
        
        
    def test_saveIssueDraft(self):
        """ try to add an issue with a crap file attachment """
        tracker = self.folder.tracker
        request = self.app.REQUEST
        title = u'TITLE'; request.set('title', title)
        fromname = u'From name'; request.set('fromname', fromname)
        email = u'email@address.com'; request.set('email', email)
        description = u'DESCRIPTION'; request.set('description', description)
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        request.set('fileattachment', NewFileUpload(os.path.abspath(__file__)))
        
        tracker.SaveDraftIssue(request)

        # Because getMyIssueDrafts() depends on cookies and cookies don't
        # work in ZopeTestCase :( we have to fake this a bit
        drafts = tracker.getDraftsContainer().objectValues(ISSUE_DRAFT_METATYPE)
        assert len(drafts) == 1

        # Now check that draft
        draft = drafts[0]
        self.assertEqual(draft.getTitle(), title)
        self.assertEqual(draft.getDescription(), description)
        self.assertEqual(draft.getFromname(), fromname)
        self.assertEqual(draft.getEmail(), email)
        self.assertEqual(draft.getType(), tracker.getDefaultType())
        self.assertEqual(draft.getUrgency(), tracker.getDefaultUrgency())
        
        # from this it will be possible to get the files back via the
        # tempfolder
        assert request.get(TEMPFOLDER_REQUEST_KEY), "no tempfolder set in request"
        tempfolder = tracker._getTempFolder()
        files = tempfolder[request.get(TEMPFOLDER_REQUEST_KEY)].objectValues('File')
        assert files, "no temp files"
        temp_file = files[0]
        self.assertEqual(temp_file.getId(), os.path.basename(__file__))

    def test_searchIssues(self):
        """ basic search tests """
        tracker = self.folder.tracker
        request = self.app.REQUEST
        title = u'titles are working'; request.set('title', title)
        fromname = u'From name'; request.set('fromname', fromname)
        email = u'email@address.com'; request.set('email', email)
        description = u'DESCRIPTION is a in the this test'
        request.set('description', description)
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        request.set('fileattachment', NewFileUpload(os.path.abspath(__file__)))
        
        tracker.SubmitIssue(request)
        assert tracker.getIssueObjects()
        
        issue = tracker.getIssueObjects()[0]

        # search and find it
        q = 'working'
        self.assertEqual(issue, tracker._searchCatalog(q, search_only_on=None)[0])
        self.assertEqual(issue, tracker._searchCatalog(q, search_only_on='title')[0])
        
        # don't expect to find it
        q = 'notmentioned'
        self.assertEqual(tracker._searchCatalog(q, search_only_on='description'), [])
        self.assertEqual(tracker._searchCatalog(q), [])
        
        # search fuzzy and find it
        q = 'title'
        self.assertEqual(issue, tracker._searchCatalog(q)[0])
        # it should be case insensitive
        q = 'DeScriPtion'
        self.assertEqual(issue, tracker._searchCatalog(q)[0])
        
        # low level test of searching by filename
        self.assertEqual(issue, tracker._searchByFilename(os.path.basename(__file__))[0])
        # and do it fuzzy
        self.assertEqual(issue, tracker._searchByFilename(os.path.basename(__file__).upper())[0])
        # or without the extension
        name = os.path.splitext(os.path.basename(__file__))[0]
        self.assertEqual(issue, tracker._searchByFilename(name)[0])

        
        
    def test_filterIssues(self):
        """ test to call filter issues and note how the filter should be saved and 
        should be reusable later. """
        
        tracker = self.folder.tracker
        request = self.app.REQUEST
        
        # first, the user who performs this test is a normal zope acl 
        # user. Let's add a name and email so that we can make sure 
        # this is information is saved in the saved filter
        self.set_cookie(tracker.getCookiekey('name'), u'Bob')
        self.set_cookie(tracker.getCookiekey('email'), u'bob@test.com')
            
        # initially there shouldn't be a folder called 'saved-filters'
        self.assertFalse(hasattr(tracker, 'saved-filters'))
        # and there shouldn't be a zcatalog called 'saved-filters-catalog'
        self.assertFalse(hasattr(tracker, 'saved-filters-catalog'))
        
        # On the homepage, the links to see only say issues "On hold" is
        # /ListIssues?Filterlogic=show&f-statuses=on%20hold
        # Let's mimick that:
        request.set('Filterlogic','show')
        request.set('f-statuses','on hold')
        tracker.ListIssuesFiltered()
        
        # this should now have create the saved-filters folder 
        # and the saved-filters-catalog
        self.assertTrue(hasattr(tracker, 'saved-filters'))
        self.assertTrue(hasattr(tracker, 'saved-filters-catalog'))
        
        # let's look at what was created in the saved-filters folder
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 1)
        
        # since I'm here logged into Zope as a normal Zope user
        # we can expect to find that the saved filter should be to me
        zopeuser = tracker.getZopeUser()
        path = '/'.join(zopeuser.getPhysicalPath())
        name = zopeuser.getUserName()
        acl_adder = ','.join([path, name])
        saved_filter = saved_filters[0]
        
        self.assertEqual(saved_filter.acl_adder, acl_adder)
        self.assertEqual(saved_filter.getTitle(), u"Only on hold issues")
        # this is who created the filter (quite unimportant)
        self.assertEqual(saved_filter.adder_fromname, u'Bob')
        self.assertEqual(saved_filter.adder_email, 'bob@test.com')
        # and we didn't need to associate with a cookie key
        self.assertEqual(saved_filter.key, '')
        
        # the logic was to show
        self.assertEqual(saved_filter.filterlogic, 'show')
        
        # some attributes are automatically set for the issue metadata
        self.assertEqual(saved_filter.sections, None)
        self.assertEqual(saved_filter.urgencies, None)
        self.assertEqual(saved_filter.types, None)
        self.assertEqual(saved_filter.statuses, [u'on hold'])
        
        # We should have a saved-filters-catalog created
        catalog = tracker.getFilterValuerCatalog()
        self.assertTrue(catalog is not None)
        # and there should only be one brain it right now
        self.assertTrue(len(catalog.searchResults()) == 1)
        
        saved_filter_from_brain = catalog.searchResults()[0].getObject()
        self.assertTrue(saved_filter_from_brain == saved_filter)
        
        # the high level function getMySavedFilters() uses the catalog
        # to extract the saved filters with the most recent one
        # first.
        saved_filter_from_mysavedfilters = tracker.getMySavedFilters()[0]
        self.assertTrue(saved_filter_from_mysavedfilters == saved_filter)
        

        # If you run ListIssuesFiltered() again, it should have to create 
        # one more new saved filter
        tracker.ListIssuesFiltered()
        
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 1)
        
        # But if we change the parameters a little bit it should have 
        # created a new saved filter
        request.set('f-statuses','taken')
        tracker.ListIssuesFiltered()
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 2)
        
        # getMySavedFilters() is smart in that it returns the filters ordered.
        # Test that the more recent one comes first
        saved_filters_from_mysavedfilters = tracker.getMySavedFilters()
        self.assertEqual(saved_filters_from_mysavedfilters[0].statuses, [u'taken'])
        
        # Test the function getCurrentlyUsedSavedFilter(request_only=True)
        assert tracker.getCurrentlyUsedSavedFilter() is None
        
        saved_filter_id = tracker.getCurrentlyUsedSavedFilter(request_only=False)
        # now check that this is the correct one
        self.assertEqual(saved_filter_id, saved_filters_from_mysavedfilters[0].getId())
        # another (more long winded) way of checking this is by that since the 
        # last filter was to filter by "taken". Check that this is what the 
        # filter does that comes from getCurrentlyUsedSavedFilter(request_only=False)
        current_saved_filter = getattr(getattr(tracker, 'saved-filters'), saved_filter_id)
        self.assertEqual(current_saved_filter.statuses, [u'taken'])
        
        
        # Some options that can be passed directly to _ListIssuesFiltered
        # are: 
        #   skip_filter
        #   skip_sort
        #
        # To set these for ListIssuesFiltered() you have to put them in the
        # REQUEST. These are useful if you for example want to ignore possibly
        # filters in session such as for the homepage where it uses 
        # ListIssuesFiltered() but without any filtering.
        # The skip_sort is useful to set when you don't want any sorting since
        # sorting will only cost time.
        # XXX: Only able to test this WITH issues

        
    def test_filterIssues_anonymous_user(self):
        """ test filtering issues when the user is not logged in """
        # when *not* logged in there are two ways to remember a saved filter:
        #   by name and email
        #   by a cookie key
        # Let's first try to filter issues as a complete nobody
        
        noSecurityManager()
        tracker = self.folder.tracker
        request = self.app.REQUEST
        
        tracker.set_cookie = self.set_cookie
        
        # On the homepage, the links to see only say issues "On hold" is
        # /ListIssues?Filterlogic=show&f-statuses=on%20hold
        # Let's mimick that:
        request.set('Filterlogic','show')
        request.set('f-statuses','on hold')
        tracker.ListIssuesFiltered()
        
        # let's look at what was created in the saved-filters folder
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 1)
        saved_filter = saved_filters[0]
        self.assertTrue(saved_filter.getKey() in request.cookies.values())
        
        # run it again and it shouldn't create another saved filter
        tracker.ListIssuesFiltered()
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 1)
        
    def test_filterIssues_anonymous_named_user(self):
        """ test filtering when the user is no logged in but has a name
        and email in the cookie. """
        
        noSecurityManager()
        tracker = self.folder.tracker
        request = self.app.REQUEST
        
        tracker.set_cookie = self.set_cookie
        
        self.set_cookie(tracker.getCookiekey('name'), u'Bob')
        self.set_cookie(tracker.getCookiekey('email'), u'bob@test.com')
        
        # On the homepage, the links to see only say issues "On hold" is
        # /ListIssues?Filterlogic=show&f-statuses=on%20hold
        # Let's mimick that:
        request.set('Filterlogic','show')
        request.set('f-statuses','on hold')
        tracker.ListIssuesFiltered()
        
        # let's look at what was created in the saved-filters folder
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 1)
        saved_filter = saved_filters[0]
        self.assertEqual(saved_filter.adder_email, 'bob@test.com')
        self.assertEqual(saved_filter.adder_fromname, u'Bob')
        
        # run it again and it shouldn't create another saved filter
        tracker.ListIssuesFiltered()
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 1)
        
        
    def test_filterIssues_anonymous_named_user_no_email(self):
        """ test filtering when the user is no logged in but has a name
        and email in the cookie. """
        
        noSecurityManager()
        tracker = self.folder.tracker
        request = self.app.REQUEST
        
        tracker.set_cookie = self.set_cookie
        
        self.set_cookie(tracker.getCookiekey('name'), u'Bob')
        
        # On the homepage, the links to see only say issues "On hold" is
        # /ListIssues?Filterlogic=show&f-statuses=on%20hold
        # Let's mimick that:
        request.set('Filterlogic','show')
        request.set('f-statuses','on hold')
        tracker.ListIssuesFiltered()
        
        # let's look at what was created in the saved-filters folder
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 1)
        saved_filter = saved_filters[0]
        self.assertEqual(saved_filter.adder_fromname, u'Bob')
        
        # run it again and it shouldn't create another saved filter
        tracker.ListIssuesFiltered()
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 1)        
    

    def test_filterIssues_recycleable(self):
        """ test to call filter issues and note how the filter should be saved and 
        should be reusable later. 
        When you *go back* to run a filter you've already done before it should be
        able to reuse an existing object instead of having to create a new one."""

        tracker = self.folder.tracker
        request = self.app.REQUEST
        
        # 1
        request.set('Filterlogic','show')
        request.set('f-statuses','on hold')
        tracker.ListIssuesFiltered()
        
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 1)

        # 2
        request.set('f-statuses','taken')
        tracker.ListIssuesFiltered()
        
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 2)
        
        # 3
        request.set('f-statuses','on hold')
        tracker.ListIssuesFiltered()
        
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 2)
        
    def test_filterIssues_from_cookie_after_purge(self):
        """ If all the saved-filters are deleted and someone has a cookie
        of an old savedfilter, if the saved filter is deleted, getting it
        from the cookie shouldn't raise an AttributeError.
        """
        
        tracker = self.folder.tracker
        request = self.app.REQUEST
        
        tracker.set_cookie = self.set_cookie
        
        ckey = tracker.getCookiekey('remember_savedfilter_persistently')
        tracker.set_cookie(ckey, 1)
        
        # 1
        request.set('Filterlogic','show')
        request.set('f-statuses','on hold')
        tracker.ListIssuesFiltered()
        
        self.assertTrue('__issuetracker_savedfilter_id-tracker' in request.cookies)
        
        saved_filters = getattr(tracker, 'saved-filters').objectValues()
        self.assertEqual(len(saved_filters), 1)
        
        # now, mess with it
        tracker.manage_delObjects(['saved-filters','saved-filters-catalog'])

        # if the cookie causes an AttributeError, then ListIssuesFiltered()
        # here wouldn't work. Just running this is the final test.
        tracker.ListIssuesFiltered()
        
        
        
    def test_unicode_in_statuses(self):
        """ test that it's possible to set a verb:action pair to the 
        statuses that is unicode. """
        
        tracker = self.folder.tracker
        request = self.app.REQUEST
        
        for status, verb in tracker.getStatusesMerged(aslist=True):
            self.assertTrue(isinstance(status, unicode))
            self.assertTrue(isinstance(verb, unicode))
            
        # All the default ones are easy, lets spice it up a bit
        statuses_and_verbs = [u'open, open', 
                              u'taken, take', 
                              u'on hold, put on hold', 
                              u'a pr\xe9c\xe9dente, faire pr\xe9c\xe9dente', 
                              u'rejected, reject', 
                              u'completed, complete']
        request.set('statuses-and-verbs', statuses_and_verbs)
        
        tracker.manage_editIssueTrackerProperties(carefulbooleans=True, REQUEST=request)
        
        for status, verb in tracker.getStatusesMerged(aslist=True):
            self.assertTrue(isinstance(status, unicode))
            self.assertTrue(isinstance(verb, unicode))
    
        
        
#class IssueTrackerFunctionalTestCase(TestFunctionalBase):
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(IssueTrackerTestCase))
#    suite.addTest(makeSuite(IssueTrackerFunctionalTestCase))
    return suite


from Products.MailHost.MailHost import MailBase
def _monkeypatch_send(self, mfrom, mto, messageText):
    if 0:
        import inspect
        print "_send(%r, %r, %r)" % (mfrom, mto, messageText[:40]+'...')
        for i in range(2,6):
            try:
                #caller_module = inspect.stack()[i][1]
                caller_method = inspect.stack()[i][3]
                caller_method_line = inspect.stack()[i][2]
            except IndexError:
                break
            print "\t%s:%s"%(caller_method, caller_method_line)
        print ""
    
    __trapped_emails__.append(dict(mfrom=mfrom, mto=mto, messageText=messageText))
    
    #print >>sys.stderr, "from:%s To:%s" % (mfrom, mto)
MailBase._send = _monkeypatch_send
__trapped_emails__ = []
    
if __name__ == '__main__':
    framework()
    
    
        

