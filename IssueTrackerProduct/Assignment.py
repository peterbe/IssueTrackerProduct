# IssueTrackerProduct
# www.issuetrackerproduct.com
#
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

# python

# Zope
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from zLOG import LOG, ERROR, INFO, PROBLEM, WARNING
from DateTime import DateTime

# Product
from Issue import IssueTrackerIssue
from Constants import *
from Permissions import *

class IssueTrackerIssueAssignment(IssueTrackerIssue):
    """ Issue Assignment class """

    meta_type = ISSUEASSIGNMENT_METATYPE

    icon = '%s/issueassignment.gif'%ICON_LOCATION

    _properties=({'id':'acl_assignee',  'type': 'string', 'mode':'w'},
                 {'id':'fromname',      'type': 'string', 'mode':'w'},
                 {'id':'email',         'type': 'string', 'mode':'w'},
                 {'id':'assignmentdate','type': 'date',   'mode':'w'},
                 {'id':'acl_adder',     'type': 'string', 'mode':'w'},
                 )
    
    security=ClassSecurityInfo()

    manage_options = (
        {'label':'Properties',  'action':'manage_propertiesForm'},
        {'label':'Contents',    'action':'manage_main'},                     
        )
        
    # legacy
    # All old assignments that have already been sent we can assume
    # that they have been sent.
    email_sent = True

    def __init__(self, id, acl_assignee, state,
                 fromname, email, acl_adder='',
                 email_sent=False):
        """ create assignment """
        self.id = str(id)
        self.acl_assignee = acl_assignee
        self.assignmentdate = DateTime()
        self.fromname = fromname
        self.email = email
        if acl_adder is None:
            acl_adder = ''
        self.acl_adder = acl_adder
        assert state in [-1, 0, 1], "Invalid state of assignment"
        self.state = state # 1=Assigned 0=Reassigned -1=Rejected
        self.email_sent = bool(email_sent)


    def getTitle(self):
        """ return title """
        return self.showState()

    def getAssignmentDate(self):
        """ return assignmentdate """
        return self.assignmentdate

    def getFromname(self, issueusercheck=1):
        """ return fromname """
        acl_adder = self.getACLAdder()
        if issueusercheck and acl_adder:
            ufpath, name = acl_adder.split(',')
            uf = self.unrestrictedTraverse(ufpath)
            issueuserobj = uf.data[name]
            return issueuserobj.getFullname() or self.fromname
        else:
            return self.fromname
       
    def getEmail(self, issueusercheck=1):
        """ return email """
        acl_adder = self.getACLAdder()
        if issueusercheck and acl_adder:
            ufpath, name = acl_adder.split(',')
            uf = self.unrestrictedTraverse(ufpath)
            issueuserobj = uf.data[name]
            return issueuserobj.getEmail() or self.email
        else:
            return self.email        

    def getACLAdder(self):
        """ return acl_adder """
        return self.acl_adder
    
    def _setACLAdder(self, acl_adder):
        """ set acl_adder """
        self.acl_adder = acl_adder

    def getACLAssignee(self):
        """ return acl_assignee """
        return self.acl_assignee

    def _setACLAssignee(self, acl_assignee):
        """ set acl_assignee """
        self.acl_assignee = acl_assignee
    
    def getACLAssigneeUser(self):
        """ return acl_assignee as object from
        its userfolder """
        ufpath, name = self.getACLAssignee().split(',')
        try:
            uf = self.unrestrictedTraverse(ufpath)
        except KeyError:
            uf = self.unrestrictedTraverse(ufpath.split('/')[-1])
        issueuserobj = uf.data[name]
        return issueuserobj

    def hasACLAssigneeUser(self):
        """ return if acl_assignee exists as an object in
        its userfolder """
        ufpath, name = self.getACLAssignee().split(',')
        try:
            uf = self.unrestrictedTraverse(ufpath)
        except KeyError:
            try:
                uf = self.unrestrictedTraverse(ufpath.split('/')[-1])
            except KeyError:
                # user folder doesn't exist
                return False
        return uf.data.has_key(name)

    def isYou(self):
        """ return true if logged in as who is assigned """
        issueuser = self.getIssueUser()
        if issueuser:
            identifier = issueuser.getIssueUserIdentifier()
            identifier = ','.join(identifier)
            acl_assignee = self.getACLAssignee()
            if identifier == acl_assignee:
                return True
        return False

    def getAssigneeFullname(self):
        """ return the fullname from the acl_assignee """
        try:
            issueuserobj = self.getACLAssigneeUser()
        except KeyError:
            return ""
        try:
            return issueuserobj.getFullname()
        except AttributeError:
            # if the issueuserobj doesn't have a getFullname() method,
            # then this object is a plain Zope User Folder instance
            return issueuserobj.getUserName()
            

    def getAssigneeEmail(self):
        """ return the email from the acl_assignee """
        try:
            issueuserobj = self.getACLAssigneeUser()
        except KeyError:
            return ""
        
        try:
            return issueuserobj.getEmail()
        except AttributeError:
            # read the comment in the except clause above in getAssigneeFullname()
            return ""
        
        

    def getState(self):
        """ return state """
        return self.state

    def showState(self, complete=0):
        """ return state nicely """
        state = self.getState()
        if state == -1:
            if complete:
                return "Rejected by"
            else:
                return "Rejected"
        elif state == 0:
            if complete:
                return "Reassigned to"
            else:
                return "Reassigned"
        else:
            if complete:
                return "Assigned to"
            else:
                return "Assigned"
            
    def _setEmailSent(self):
        self.email_sent = True
        
    def isEmailSent(self):
        return self.email_sent

    security.declareProtected(VMS, 'assertAllProperties')
    def assertAllProperties(self):
        """ make sure assignment has all properties """
        props = { # currently nothing
                 }
                 
        count = 0
        for key, default in props.items():
            if not self.__dict__.has_key(key):
                self.__dict__[key] = default
                count += 1
        return count

    

InitializeClass(IssueTrackerIssueAssignment)

