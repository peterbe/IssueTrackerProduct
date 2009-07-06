# IssueTrackerProduct
#
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

# python


# Zope
from Globals import InitializeClass
from OFS import SimpleItem
from AccessControl import ClassSecurityInfo
from zLOG import LOG, ERROR, INFO, PROBLEM, WARNING
from DateTime import DateTime
from Acquisition import aq_inner, aq_parent


# Product
from IssueTracker import IssueTracker, base_hasattr
from Constants import *
import Utils

#----------------------------------------------------------------------------

class IssueTrackerNotification(SimpleItem.SimpleItem,
                               IssueTracker
                               ):
    """ Issue Tracker Notification """

    meta_type = NOTIFICATION_META_TYPE
    icon = '%s/notification.gif'%ICON_LOCATION

    security = ClassSecurityInfo()
    
    _properties=({'id':'title',       'type': 'ustring',  'mode':'w'},
                 {'id':'change',      'type': 'ustring',  'mode':'w'},
                 {'id':'issueID',     'type': 'string',  'mode':'w'},
                 {'id':'comment',     'type': 'utext',    'mode':'w'},
                 {'id':'emails',      'type': 'lines',   'mode':'w'},
                 {'id':'success_emails','type':'lines',  'mode':'w'},
                 {'id':'anchorname',  'type': 'string',  'mode':'w'},
                 {'id':'assignment',  'type': 'string',  'mode':'w'},
                 {'id':'fromname',    'type': 'ustring',  'mode':'w'},
                 {'id':'date',        'type': 'date',    'mode':'w'},
                 {'id':'dispatched',  'type': 'boolean', 'mode':'w'},
                 {'id':'new_status',  'type': 'ustring', 'mode':'w'},
                 )

    manage_options = (
        {'label':'Properties', 'action':'manage_propertiesForm'},
        )
        
    # legacy: attributes that have been added later
    assignment = ''

    def __init__(self, id, title, issueID, emails,
                 fromname=u'',
                 comment=u'',
                 date=None, dispatched=False,
                 anchorname='', change=u'',
                 assignment='',
                 REQUEST=None,
                 **extra_headers):
        """ create notification """
        self.id = str(id)
        self.title = title
        self.change = change
        self.issueID = str(issueID)
        self.comment = comment
        self.emails = emails
        self.success_emails = []
        self.anchorname = anchorname
        self.assignment = assignment
        self.fromname = fromname
        self.dispatched = dispatched
        if date is None:
            date = DateTime()
        self.date = date
        self.extra_headers = extra_headers
        
    def getTitle(self):
        """ return title of the notification """
        return self.title
    
    def getIssueID(self):
        """ return issueID of the notification """
        return self.issueID
    
    def getAssignmentObject(self):
        """ return the assignment object this notification was about
        or return None """
        if self.assignment:
            object_id = self.assignment
            # expect the assignment object to be located in the same
            # container as this notification
            parent = aq_parent(aq_inner(self))
            if base_hasattr(parent, object_id):
                obj = getattr(parent, object_id)
                if obj.meta_type == ISSUEASSIGNMENT_METATYPE:
                    return obj
                
        return None
    
    def isDispatched(self):
        """ return dispatched """
        return not not self.dispatched
    
    def dispatch(self):
        """ dispatch self """
        self.dispatcher([self])
        
        
    def setSuccessEmail(self, email):
        """ set an email that was a success to send to.
        
        The email must exist in self.emails and not already a success 
        """
        emails = self.getEmails()
        success_emails = self.getSuccessEmails()
        if Utils.ss(email) in [Utils.ss(each) for each in emails]:
            if Utils.ss(email) not in [Utils.ss(each) for each in success_emails]:
                success_emails.append(email)
        self.success_emails = success_emails
                
    def getEmails(self):
        """ return the list of emails to send to """
        return self.emails
    
    def _setEmails(self, emails):
        self.emails = emails
    
    def getSuccessEmails(self):
        """ return list of emails that have successfully been sent to """
        
        # due to legacy, if the success_emails attribute doesn't exist,
        # it must be because this self is an object that was created
        # _before_ the 'success_emails' attribute was introduced. 
        # If that's the case, return 'emails' instead
        return getattr(self, 'success_emails', self.getEmails())
        
    def MarkNotificationDispatch(self):
        """ set as dispatched """
        self.dispatched = True
        
InitializeClass(IssueTrackerNotification)
