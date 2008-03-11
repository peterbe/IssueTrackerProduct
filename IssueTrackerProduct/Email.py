# IssueTrackerProduct
#
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

"""
Email is for accepting inbound emails into the issue tracker
"""

# python
import sys, os, re

# Zope
from OFS import SimpleItem
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

# Product
import IssueTracker
from Permissions import *
from Constants import *
from Utils import ss



class POP3Account(IssueTracker.IssueTrackerFolderBase):
    """ POP3Account class """
    
    meta_type = POP3ACCOUNT_METATYPE
    icon = '%s/issuetracker_pop3account.gif'%ICON_LOCATION

    _properties = ({'id':'hostname',     'type': 'string',  'mode':'w'},
                   {'id':'portnr',       'type': 'int',     'mode':'w'},
                   {'id':'username',     'type': 'string',  'mode':'w'},
                   {'id':'delete_after', 'type': 'boolean', 'mode':'w'},
                   {'id':'ssl', 'type': 'boolean', 'mode':'w'},
                   )

    # for legacy reasons
    delete_after = True
    ssl = False
    
    security = ClassSecurityInfo()

    # default
    portnr = 110
    
    def __init__(self, id, hostname, username, password, portnr=110,
                 delete_after=False, ssl=False):
        """ init """
        self.id = str(id)
        self.hostname = str(hostname)
        self.portnr = int(portnr)
        self.username = str(username)
        self._password = str(password)
        self.delete_after = bool(delete_after)
        self.ssl = bool(ssl)
        
    def getTitle(self):
        """ return hostname for title """
        return self.hostname
        
    def getId(self):
        """ return id """
        return self.id
    
    def getHostname(self):
        """ return hostname """
        return self.hostname

    def getPort(self):
        """ return portnr """
        return getattr(self, 'portnr', 110)
    
    def getUsername(self):
        """ return username """
        return self.username
    
    def doDeleteAfter(self):
        """ return delete_after """
        return self.delete_after

    def doSSL(self):
        """ return ssl """
        return self.ssl
    
    def getAcceptingEmails(self, ids=0):
        """ return accepting email objects here """
        if ids:
            return self.objectIds(ACCEPTINGEMAIL_METATYPE)
        else:
            return self.objectValues(ACCEPTINGEMAIL_METATYPE)
        
    def doSendConfirmSuggestion(self):
        """ return true if most accepting emails herein use doSendConfirm """
        total = 0
        for ae in self.getAcceptingEmails():
            if ae.doSendConfirm():
                total += 1
            else:
                total -= 1
                
        # since default is True, be more lenient to total=0
        return total >= 0
        
    def getAcceptingEmailbyTo(self, to, default=None):
        """ which accepting email here has 'to' 
        for email_address """
        to = to.lower().strip()
        for object in self.getAcceptingEmails():
            if object.email_address.lower().strip() == to:
                return object
        else:
            return default
        
    security.declareProtected(VMS, 'editAccount')
    def editAccount(self, hostname=None, portnr=None,
                    username=None, password=None, delete_after=False):
        """ old name """
        import warnings 
        warnings.warn("editAccount() is an old name. Use manage_editAccount() instead",
                      DeprecationWarning, 2)
        return self.manage_editAccount(hostname, portnr, username, password, delete_after)

    
    security.declareProtected(VMS, 'manage_editAccount')
    def manage_editAccount(self, hostname=None, portnr=None,
                    username=None, password=None, delete_after=False, ssl=False):
        """ change the attributes """
        if hostname is not None:
            self.hostname = hostname
        if portnr is not None:
            self.portnr = portnr
        if username is not None:
            self.username = username
        if password is not None:
            self._password = password
            
        self.delete_after = bool(delete_after)
        self.ssl = bool(ssl)
            
        
    security.declareProtected(VMS, 'createAcceptingEmail')
    def createAcceptingEmail(self, id, email_address, defaultsections,
                             default_type, default_urgency,
                             send_confirm, reveal_issue_url):
        """ create object and return it """
        
        acceptingemail = AcceptingEmail(id, email_address, defaultsections,
                                        default_type, default_urgency,
                                        send_confirm,
                                        reveal_issue_url=reveal_issue_url)
        self._setObject(id, acceptingemail)
        return getattr(self, id)
    
        
InitializeClass(POP3Account)



class AcceptingEmail(SimpleItem.SimpleItem,
                     IssueTracker.IssueTrackerFolderBase):
    """ AcceptingEmail class """

    meta_type = ACCEPTINGEMAIL_METATYPE
    icon = '%s/issuetracker_acceptingemail.gif'%ICON_LOCATION
    
    meta_types = []

    _properties=({'id':'email_address',   'type': 'string', 'mode':'w'},
                 {'id':'defaultsections', 'type': 'lines',  'mode':'w'},
                 {'id':'default_type',    'type': 'string', 'mode':'w'},
                 {'id':'default_urgency', 'type': 'string', 'mode':'w'},
                 {'id':'send_confirm',    'type': 'boolean','mode':'w'},
                 {'id':'whitelist_emails','type': 'lines',  'mode':'w'},
                 {'id':'blacklist_emails','type': 'lines',  'mode':'w'},
                 {'id':'reveal_issue_url','type': 'lines',  'mode':'w'},
                 )
    
    security=ClassSecurityInfo()

    
    def __init__(self, id, email_address, defaultsections,
                 default_type, default_urgency, send_confirm=True,
                 reveal_issue_url=True):
        """ init """
        self.id = str(id)
        self.email_address = str(email_address)
        if type(defaultsections) == type('s'):
            defaultsections = [defaultsections]
        self.defaultsections = defaultsections
        self.default_type = str(default_type)
        self.default_urgency = str(default_urgency)
        self.send_confirm = bool(send_confirm)
            
        self.whitelist_emails = []
        self.blacklist_emails = []
        self.reveal_issue_url = bool(reveal_issue_url)

    def getId(self):
        """ return id """
        return self.id
    
    def getTitle(self):
        """ return email_address """
        return self.getEmailAddress()
    
    def getEmailAddress(self):
        """ return email_address """
        return self.email_address
    
    def doSendConfirm(self):
        """ return send_confirm """
        return getattr(self, 'send_confirm', False)
    
    def getWhitelistEmails(self):
        """ return whitelist_emails """
        return getattr(self, 'whitelist_emails', [])
    
    def getBlacklistEmails(self):
        """ return blacklist_emails """
        return getattr(self, 'blacklist_emails', [])

    def revealIssueURL(self):
        """ return if the URL of the issue should be revealed in the
        email coming back. 
        Since this attribute was introduced late, we have to assume 
        that the attribute isn't always available. 
        """
        default = True
        return getattr(self, 'reveal_issue_url', default)
    
    def acceptOriginatorEmail(self, email, default_accept=True):
        """ return true if this email is either whitelisted or 
        not blacklisted """
        whitelist = self.getWhitelistEmails()
        blacklist = self.getBlacklistEmails()
        
        # note the order 
        for reject, emaillist in ([False, whitelist], [True, blacklist]):
            for okpattern in emaillist:
                _okpattern = re.compile(okpattern.replace('*','\S+'), re.I)
                if _okpattern.findall(email):
                    # match!
                    if reject:
                        return False
                    else:
                        return True
                   
        # default is to accept all
        return default_accept
                    
    
    def editDetails(self, email_address=None, defaultsections=None,
                    default_type=None, default_urgency=None,
                    send_confirm=None,
                    reveal_issue_url=None,
                    whitelist_emails=None,
                    blacklist_emails=None):
        """ edit details if not None """
        if email_address is not None:
            self.email_address = email_address
        if defaultsections is not None:
            if type(defaultsections) == type('s'):
                defaultsections = [defaultsections]
            self.defaultsections = defaultsections
        if default_type is not None:
            self.default_type = default_type
        if default_urgency is not None:
            self.default_urgency = default_urgency
        if send_confirm is not None:
            self.send_confirm = bool(send_confirm)
        if reveal_issue_url is not None:
            self.reveal_issue_url = bool(reveal_issue_url)
        if whitelist_emails is not None:
            self.whitelist_emails = self._tidyEmailList(whitelist_emails)
        if blacklist_emails is not None:
            self.blacklist_emails = self._tidyEmailList(blacklist_emails)
            
    def _tidyEmailList(self, emaillist):
        """ only accept either valid email addresses or
        those with * in them. """
        emaillist = [x.strip() for x in emaillist if x.strip()]
        for e in emaillist:
            if e.find('**') > -1:
                m = "Email wildcard repeated excessively %s"
                raise ValueError, m % e
            elif e.find(' ') > -1:
                m = "Email wildcard contains whitespace %r"
                raise ValueError, m % e
        return emaillist

        
    
    def assertAllProperties(self):
        """ make sure accepting email has all properties """
        props = {'email_address':'', 'defaultsections':[], 
                 'default_type':self.default_type,
                 'default_urgency':self.default_urgency,
                 'send_confirm':1,
                 'whitelist_emails':[],
                 'blacklist_emails':[],
                 }
                 
        count = 0
        for key, default in props.items():
            if not self.__dict__.has_key(key):
                self.__dict__[key] = default
                count += 1
        return count    
    
InitializeClass(AcceptingEmail)
