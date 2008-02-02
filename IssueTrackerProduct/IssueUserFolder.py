# IssueTrackerProduct
#
# www.issuetrackerproduct.com
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

__version__='0.0.7'

# python

# Zope
from AccessControl import User
from Globals import DTMLFile, MessageDialog, Persistent
from AccessControl import ClassSecurityInfo

# Product
import Utils
from I18N import _
from Constants import *
from Permissions import IssueTrackerManagerRole, IssueTrackerUserRole, VMS

#----------------------------------------------------------------------------

manage_addIssueUserFolderForm=DTMLFile('dtml/addIssueUserFolder', globals())

def manage_addIssueUserFolder(self, title='', webmaster_email='',
                              keep_usernames=None, REQUEST=None):
    """ ads  """
    id="acl_users"
    webmaster_email = str(webmaster_email).strip()
    old_users = None
    if keep_usernames and id in self.objectIds('User Folder'):
        old_users = self.manage_getUsersToConvert(withpasswords=True)
        self.manage_delObjects([id])
        
    
    i=IssueUserFolder(webmaster_email)
    self._setObject(id,i)
    userfolder = self._getOb(id)

    for role in [IssueTrackerManagerRole, IssueTrackerUserRole]:
        # only add these roles if they don't already exist
        if role not in self.valid_roles():
            self.REQUEST.set('role', role)
            self.manage_defined_roles(submit='Add Role', REQUEST=self.REQUEST)

    if old_users and REQUEST is not None:
        old_users_dict = {}
        for user in old_users:
            old_users_dict[user['username'].replace(' ','')] = user

        keys = REQUEST.get('keys')
        for key in keys:
            username = REQUEST.get('username_%s'%key)
            if key not in keep_usernames:
                continue
            if not username:
                raise "IllegalValue", 'A username must be specified'
            password = old_users_dict[key]['__']
            fullname = REQUEST.get('fullname_%s'%key)
            if not fullname:
                fullname = username
            email = REQUEST.get('email_%s'%key)
            if not Utils.ValidEmailAddress(email):
                raise "InvalidEmail", "Email (%r) not valid email address"%email
            roles = REQUEST.get('roles_%s'%key)
            domains = REQUEST.get('domains_%s'%key)
            if domains and not self.domainSpecValidate(domains):
                raise "IllegalValue", 'Illegal domain specification'

            userfolder._doAddUser(username, password, roles, domains,
                                  email=email,
                                  fullname=fullname)
                                  
    if REQUEST:
        return self.manage_main(self, REQUEST)


def _uniqify(somelist):
    d={}
    for i in somelist:
        d[i]=1
    return d.keys()

def _merge_dicts_nicely(dict1, dict2):
    """ make all dict values into lists
    into one dict """
    new = {}
    for k,v in (dict1.items()+dict2.items()):
        if new.has_key(k):
            # that we haven't seen before
            if type(v)==type([]):
                new[k].extend(v)
            else:
                new[k].append(v)
        else:
            if type(v)==type([]):
                new[k] = v
            else:
                new[k] = [v]
    for k,v in new.items():
        thatlist = _uniqify(v)
        thatlist.sort()
        new[k] = thatlist
    return new

def _find_issuetrackers(context):
    issuetrackers = []
    for object in context.objectValues():
        if object.meta_type == ISSUETRACKER_METATYPE:
            issuetrackers.append(object)
        elif object.isPrincipiaFolderish:
            issuetrackers.extend(_find_issuetrackers(object))
    return issuetrackers

def manage_getUsersToConvert(self, withpasswords=False):
    """ find all the users in the acl_users folder here, and
    try to find a suitable name and email address. """
    if not 'acl_users' in self.objectIds('User Folder'):
        # just double checking that we have a old user folder here
        return []
    
    old_user_folder = self.acl_users
    old_users = []

    issuetrackers = _find_issuetrackers(self)
    if self.meta_type == ISSUETRACKER_METATYPE:
        if self not in issuetrackers:
            issuetrackers.append(self)
            
    acl_cookienames = acl_cookieemails = {}
    for issuetracker in issuetrackers:
        _cookienames = issuetracker.getACLCookieNames()
        
        if _cookienames:
            acl_cookienames = _merge_dicts_nicely(acl_cookienames, _cookienames)

        _cookieemails = issuetracker.getACLCookieEmails()
        if _cookieemails:
            acl_cookieemails = _merge_dicts_nicely(acl_cookieemails, _cookieemails)
        
    for user in old_user_folder.getUsers():
        fullname = acl_cookienames.get(str(user), [])
        email = acl_cookieemails.get(str(user),[])
        
        if not fullname and email:
            _email1 = email[0].split('@')[0]
            if len(_email1.split('.'))>1:
                fullname = [x.capitalize() \
                             for x in _email1.split('.')]
                fullname = ' '.join(fullname)
                
            elif len(_email1.split('_'))>1:
                fullname = [x.capitalize() \
                            for x in _email1.split('_')]
                fullname = ' '.join(fullname)
                
            else:
                fullname = str(user).capitalize()

        d = {'username':str(user),
             'domains':user.domains,
             'roles':user.roles,
             'fullname':fullname,
             'email':email}
        
        if email and email[0] and Utils.ValidEmailAddress(email[0]):
            d['invalid_email'] = False
        else:
            d['invalid_email'] = True
            
        if withpasswords:
            d['__'] = user.__
        old_users.append(d)
        
    return old_users
    
#----------------------------------------------------------------------------

class IssueUserFolder(User.UserFolder):
    """ user folder for managing IssueUsers """

    meta_type = ISSUEUSERFOLDER_METATYPE

    ## these variables need to be in the new class so they are used in the
    ## correct context and won't be taken from the base class and consequently 
    ## from the wrong directory
    _mainUser = DTMLFile('dtml/mainIssueUser', globals())
    _mainUser._setName('_mainUser')
    
    manage = _mainUser
    manage_main = _mainUser

    _add_User = DTMLFile('dtml/addIssueUser', globals())
    _editUser = DTMLFile('dtml/editIssueUser', globals())
    _passwordReminder = DTMLFile('dtml/passwordReminder', globals())
    
    security = ClassSecurityInfo()

    def __init__(self, webmaster_email=''):
        """ Same as inherited but a possible webmaster_email attribute """
        self.webmaster_email = webmaster_email
        apply(User.UserFolder.__init__, (self,), {})

    def _addUser(self, name, password, confirm, roles, domains, REQUEST=None):
        if not name:
            return MessageDialog(
                title  ='Illegal value', 
                message='A username must be specified',
                action ='manage_main')
        if not password or not confirm:
            if not domains:
                return MessageDialog(
                    title  ='Illegal value', 
                    message='Password and confirmation must be specified',
                    action ='manage_main')
        if self.getUser(name) or (self._emergency_user and
                                  name == self._emergency_user.getUserName()):
            return MessageDialog(
                title  ='Illegal value', 
                message='A user with the specified name already exists',
                action ='manage_main')
        if (password or confirm) and (password != confirm):
            return MessageDialog(
            title  ='Illegal value', 
            message='Password and confirmation do not match',
            action ='manage_main')
        
        if not roles: roles=[]
        if not domains: domains=[]

        if domains and not self.domainSpecValidate(domains):
            return MessageDialog(
                title  ='Illegal value', 
                message='Illegal domain specification',
                action ='manage_main')
        if not Utils.ValidEmailAddress(REQUEST['email']):
            return MessageDialog(
                title  ='Illegal value',
                message='Not a valid email address',
                action ='manage_main')
        if not REQUEST.get('fullname',''):
            REQUEST.set('fullname',name)
        self._doAddUser(name, password, roles, domains,
                        email=REQUEST['email'],
                        fullname=REQUEST['fullname'],
                        must_change_password=REQUEST.get('must_change_password', False),
                        display_format=REQUEST.get('display_format',''),
                        )
        if REQUEST: return self._mainUser(self, REQUEST)


    def _changeUser(self,name,password,confirm,roles,domains,REQUEST=None):
        if password == 'password' and confirm == 'pconfirm':
            # Protocol for editUser.dtml to indicate unchanged password
            password = confirm = None
        if not name:
            return MessageDialog(
                           title  ='Illegal value', 
                           message='A username must be specified',
                           action ='manage_main')
        if password == confirm == '':
            if not domains:
                return MessageDialog(
                    title  ='Illegal value', 
                    message='Password and confirmation must be specified',
                    action ='manage_main')
        if not self.getUser(name):
            return MessageDialog(
                           title  ='Illegal value', 
                           message='Unknown user',
                           action ='manage_main')
        if (password or confirm) and (password != confirm):
            return MessageDialog(
                           title  ='Illegal value', 
                           message='Password and confirmation do not match',
                           action ='manage_main')

        if not roles: roles=[]
        if not domains: domains=[]

        if domains and not self.domainSpecValidate(domains):
            return MessageDialog(
                           title  ='Illegal value', 
                          message='Illegal domain specification',
                           action ='manage_main')
        if REQUEST.get('email') and not Utils.ValidEmailAddress(REQUEST['email']):
            return MessageDialog(
                title  ='Illegal value',
                message='Not a valid email address',
                action ='manage_main')
        self._doChangeUser(name, password, roles, domains,
                           email=REQUEST.get('email'),
                           fullname=REQUEST.get('fullname'),
                           must_change_password=REQUEST.get('must_change_password'))
        if REQUEST:
            return self._mainUser(self, REQUEST)

    def _changeUserDetails(self, name, fullname, email, REQUEST=None):
        """ Simple method that does what _changeUser() does but without
        password and roles """
        fullname = fullname.strip()
        email = email.strip()
        if not fullname:
            raise "NoFullname", "Full name must be specified"
        if not email:
            raise "NoEmail", "Email must be specified"
        elif not Utils.ValidEmailAddress(email):
            raise "InvalidEmail", "Email not valid email address"

        self._doChangeUserDetails(name, fullname, email)

        if REQUEST:
            return self._mainUser(self, REQUEST)

    def _doChangeUserDetails(self, name, fullname, email,
                             must_change_password=None):
        user = self.data[name]
        user.fullname = fullname
        user.email = email
        if must_change_password is not None:
            user.must_change_password = must_change_password
        self.data[name] = user
            
        
    def _doAddUser(self, name, password, roles, domains, **kw):
        """Create a new user"""
        email=kw['email']
        fullname=kw['fullname']
        must_change_password=kw.get('must_change_password',False)
        display_format = kw.get('display_format','')
        if password is not None and self.encrypt_passwords:
            password = self._encryptPassword(password)
        self.data[name]=IssueUser(name, password, roles, domains,
                                  email, fullname, must_change_password,
                                  display_format)

    def _doChangeUser(self, name, password, roles, domains, **kw):
        user = self.data[name]
        if password is not None:
            if self.encrypt_passwords:
                password = self._encryptPassword(password)
            user.__ = password
        user.roles = roles
        user.domains = domains
        if kw.get('email'):
            email=kw['email']
            user.email = email
        if kw.get('fullname'):
            fullname=kw['fullname']
            user.fullname = fullname
        if kw.get('display_format'):
            display_format=kw['display_format']
            user.display_format = display_format
        user.must_change_password=kw.get('must_change_password', False)
        self.data[name]=user

    def getIssueTrackerRoot(self):
        """ Try to return the IssueTracker instance root or None """
        try:
            root = self.getRoot() # from aquisition
            if root.meta_type == ISSUETRACKER_METATYPE:
                return root
            else:
                return None
        except:
            # Means it's deploy outside an issuetracker
            return None
            
    def getWebmasterEmail(self):
        """ return webmaster_email or try to find a IssueTracker instance """
        # returns None if not found
        issuetrackerroot = self.getIssueTrackerRoot() 
        if issuetrackerroot:
            wherefrom = "Issue Tracker"
            email = issuetrackerroot.getSitemasterEmail()
        else:
            wherefrom = "Issue User Folder"
            email = self.webmaster_email
        if not Utils.ValidEmailAddress(email):
            m = "Webmaster email (%s) taken from %s invalid"
            m = m%(email, wherefrom)
            raise "InvalidWebmasterEmail", m

    def getIssueUserFolderPath(self):
        """ return the absolute real path of this object parent """
        return '/'.join(self.getPhysicalPath())
    
    
    security.declareProtected(VMS, 'manage_sendReminder')
    def manage_sendReminder(self, name, email_from, email_subject,
                            remindertext):
        """ actually send the password reminder """
        try:
            user = self.getUser(name)
        except:
            return MessageDialog(
                            title  ='Illegal value',
                            message='The specified user does not exist',
                            action ='manage_main')
                            
        issuetrackerroot = self.getIssueTrackerRoot()
        
        if not email_from:
            raise "NoEmailFromError", "You must specify a from email address"
        elif not self.webmaster_email:
            self.webmaster_email = email_from

        email_to = user.getEmail()
        if not email_to or email_to and not Utils.ValidEmailAddress(email_to):
            raise "NoEmailToError", "User does not have a valid email address"
            
            
        replacement_key = "<password shown here>"
        if remindertext.find(replacement_key) == -1:
            raise "NoPasswordReplacementError",\
                  "No place to put the password reminder"
                  
        if self.encrypt_passwords:
            # generate a new password and save it
            password = Utils.getRandomString(length=6, loweronly=1)
            user.__ = password
        
        else:
            password = user.__
        
        if not email_subject:
            email_subject = "Issue Tracker password reminder"
        
        remindertext = remindertext.replace(replacement_key, password)
        
        # send it!
        

        if issuetrackerroot:
            # send via the issuetracker
            issuetrackerroot.sendEmail(remindertext, email_to, email_from, 
               email_subject, swallowerrors=False)
        else:
            body = '\r\n'.join(['From: %s'%email_from, 'To: %s'%email_to,
                                'Subject: %s'%email_subject, "", remindertext])
                            
            # Expect a mailhost object. Note that here we're outside the Issuetracker
            try:
                mailhost = self.MailHost
            except:
                try:
                    mailhost = self.SecureMailHost
                except:
                    try:
                        mailhost = self.superValues('MailHost')[0]
                    except IndexError:
                        raise "NoMailHostError", "No 'MailHost' available to send from"
            if hasattr(mailhost, 'secureSend'):
                mailhost.secureSend(remindertext, email_to, email_from, email_subject)
            else:
                mailhost.send(body, email_to, email_from, email_subject)
            
        m = "Password reminder sent to %s" % email_to
        return self.manage_main(self, self.REQUEST, manage_tabs_message=m)

        
        
    
    security.declareProtected(VMS, 'manage_passwordReminder')
    def manage_passwordReminder(self, name):
        """ wrap up a template """
        try:
            user = self.getUser(name)
        except:
            return MessageDialog(
                            title  ='Illegal value',
                            message='The specified user does not exist',
                            action ='manage_main')
                            
        issuetrackerroot = self.getIssueTrackerRoot()
                            
        if self.webmaster_email:
            from_field = self.webmaster_email
        elif issuetrackerroot:
            from_field = issuetrackerroot.getSitemasterFromField()
        else:
            from_field = ""
            
        
        subject = _("Password reminder")
        
        if issuetrackerroot is not None:
            subject = "%s: %s" % (issuetrackerroot.getTitle(), subject)
            
        
        msg = "Dear %(fullname)s,\n\n"
        msg += "This is a password reminder for you to use on %(url)s.\n"
        if self.encrypt_passwords:
            msg += "Since your previous password was encrypted we have had "\
                   "to recreate a new password for you.\n"
        msg += "Your username is still: %(username)s\nand your password is: "\
               "<password shown here>"
        msg += "\n\n"
        msg += "PS. The administrator sending this password reminder will"\
               " not able to read your password at any time."
        #if issuetrackerroot is not None:
        #    msg += "Now you can go to %s and log in"%(issuetrackerroot.absolute_url()
            
        d = {'fullname':user.getFullname(),
             'username':name}
        if issuetrackerroot is not None:
            d['url'] = issuetrackerroot.absolute_url()
        else:
            d['url'] = self.absolute_url().replace('/acl_users','')
             
        msg = msg % d
            
        return self._passwordReminder(self, self.REQUEST, user=user,
                username=name,
                subject=subject, message=msg, from_field=from_field)
            
#----------------------------------------------------------------------------

class IssueUser(User.SimpleUser, Persistent):
    """ User with additional email property """

    misc_properties = {} # backwardcompatability
    
    def __init__(self, name, password, roles, domains,
                 email, fullname, must_change_password=False,
                 display_format='', use_accesskeys=False,
                 remember_savedfilter_persistently=False,
                 show_nextactions=False):
        """ constructor method """
        self.name = name
        self.__ = password
        self.roles = roles
        self.domains = domains
        self.email = email
        self.fullname = fullname
        self.must_change_password = must_change_password
        self.display_format = display_format
        self.use_accesskeys = use_accesskeys
        self.remember_savedfilter_persistently = remember_savedfilter_persistently
        self.show_nextactions = show_nextactions

        self._user_lists = None # For the User page. if None, not set
        #self._user_display_format = None

        self.misc_properties = {}


    def getIssueUserPath(self):
        """ return the absolute real path of this object parent """
        return '/'.join(self.getPhysicalPath())

    def getIssueUserIdentifier(self):
        """ return the parents physical path and username """
        return self.getIssueUserPath(), self.name
    
    def getIssueUserIdentifierString(self):
        """ return getIssueUserIdentifier() as a comma separated
        string. """
        return ','.join(self.getIssueUserIdentifier())

    def getIssueUserIdentifierstring(self):
        """ return getIssueUserIdentifier() as one string """
        path, name = self.getIssueUserIdentifier()
        return "%s,%s"%(path, name)
    
    def getEmail(self):
        """ returns the user's email """
        return self.email

    def getFullname(self):
        """ returns the fullname """
        return self.fullname

    def getUserLists(self):
        """ return _user_lists """
        if not hasattr(self, '_user_lists'): 
            self._user_lists = None           
            return None                      
        return self._user_lists

    def setUserLists(self, lists):
        """ add these lists """
        was = self.getUserLists()
        if was is None:
            was = []
        new = was+lists
        self._user_lists = Utils.uniqify(new)

    def getDisplayFormat(self):
        """ return prefered displayformat """
        if hasattr(self, 'display_format'):
            return getattr(self, 'display_format')
        else:
            # old bad code
            return getattr(self, '_user_display_format', None)

    def setDisplayFormat(self, displayformat):
        """ set prefered displayformat """
        self.display_format = displayformat
        
    def useAccessKeys(self, default=False):
        """ return prefered displayformat """
        return getattr(self, 'use_accesskeys', default)
    
    def rememberSavedfilterPersistently(self, default=False):
        """ return if last savedfilter id should be remembered persistently
        (for more info read rememberSavedfilterPersistently() in IssueTracker.py) 
        """
        return getattr(self, 'remember_savedfilter_persistently', default)
    
    def showNextActionIssues(self, default=False):
        """ return if 'Your next action issues' should be shown on the homepage
        """
        return getattr(self, 'show_nextactions', default)
    
    def setRememberSavedfilterPersistently(self, toggle):
        """ set to saved last savedfilter id persistently or not """
        self.remember_savedfilter_persistently = not not toggle
        
    def setUseNextActionIssues(self, toggle):
        """ set to saved last savedfilter id persistently or not """
        self.show_nextactions = not not toggle

    def setAccessKeys(self, toggle):
        """ set prefered displayformat """
        self.use_accesskeys = not not toggle # makes sure it's bool type

    def getMiscProperty(self, key, default=None):
        """ return from misc_properties """
        return self.misc_properties.get(key, default)

    def hasMiscProperty(self, key):
        """ do we have it in misc_properties """
        return self.misc_properties.has_key(key)
        #if not hasattr(self, 'misc_properties'):
        #    return False
        #else:
            

    def setMiscProperty(self, key, value):
        """ set in misc_properties dict """
        was = self.misc_properties
        was[key] = value
        self.misc_properties = was
        
    def debugInfo(self):
        """ return the misc_properties """
        if DEBUG: # from Constants
            out = []
            out.append("misc_properties:%s" % self.misc_properties)
            out.append("must_change_password:%s" % self.must_change_password)
            out.append("display_format:%s" % self.display_format)
            out.append("use_accesskeys:%s" % getattr(self, 'use_accesskeys', False))
            out.append("remember_savedfilter_persistently:%s" % getattr(self, 'remember_savedfilter_persistently', False))
            
            out.append("_user_lists:%s" % self._user_lists)
            return ', '.join(out)
        else:
            return "Not in debug mode"

    def mustChangePassword(self):
        """ return if 'self.must_change_password' is True """
        if not hasattr(self, 'must_change_password'):
            self.must_change_password = False # default
        return self.must_change_password

    def _unmust_mustChangePassword(self):
        """ toggle the boolean value """
        newvalue = False
        self.must_change_password = newvalue

    def sendPasswordReminder(self):
        """ will send the password in an email """
        raise "DeprecatedError"
    
        if self.encrypt_passwords:
            m = "Password reminders disabled since passwords are encrypted"
            raise "PasswordsEncrypted", m
        S = "Issue User Password Reminder"
        M = "Dear %s,\nYour password is: "%self.getFullname()
        M += self.__
        M += '\n'

        F = self.getWebmasterEmail()
        T = self.getEmail()

        # Find the nearest MailHost object
        mailhost = self.MailHost

        mailhost.send(M, T, F, S)

        page = self.manage_main
        m = "Email password reminder sent to %s"%T
        return page(self, self.REQUEST, manage_tabs_message=m)




