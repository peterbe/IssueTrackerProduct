import warnings
warnings.warn("This file is deprecated in favor of Notifyables.py",
              DeprecationWarning, 2)

# python
from types import ListType

# Zope
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from OFS import SimpleItem, Folder
from AccessControl import ClassSecurityInfo
from Globals import MessageDialog, InitializeClass, DTMLFile

# Product
import Utils
from Constants import *



class Notifyables:

    # Global container
    #
    def hasGlobalContainer(self):
        """ Check if a global container exists """
        if hasattr(self, DEFAULT_NOTIFYABLECONTAINER_ID):
            return true
        else:
            return false

    def isGlobalHere(self):
        """ Check if we're "standing" in a global container """
        if hasattr(self, 'notifyables'):
            return false
        else:
            return true

    def _getManagementFormURL(self, msg=None):
        """ return the URL to redirect to for returning to
        the appropriate interface. """
        if self.isGlobalHere():
            url = self.absolute_url()
            url += '/manage_GlobalManagementForm'
        else:
            url = self.absolute_url()
            url += '/manage_ManagementNotifyables'
        if msg is not None:
            params = {'manage_tabs_message':msg}
            url = Utils.AddParam2URL(url, params)
        return url

    def getGlobalContainer(self):
        """ Return the global_notifyables object """
        return getattr(self, DEFAULT_NOTIFYABLECONTAINER_ID)
        

    def getManagementForm(self):
        """ Return correct management form depending on container """
        if self.isGlobalHere():
            return self.manage_GlobalManagementForm
        else:
            return self.manage_ManagementNotifyables
            #return self.manage_ManagementForm

        
    # Notifyables
    #

    def hasNotifyables(self):
        """ see if there are any notifyables at all """
        if len(self.getNotifyables()) > 0:
            return 1
        else:
            return 0

  
    def getNotifyables(self, only=None):
        """ Return all Notifyable objects """
        if only =='':
            only = None
            
        if only == 'global':
            local_container = None
        else:
            local_container = self.getNotifyablesObjectContainer(only='local')

        if only == 'local':
            global_container = None
        else:
            global_container = self.getNotifyablesObjectContainer(only='global')
            
        meta_type = NOTIFYABLE_METATYPE
        if local_container is None:
            local_notifyables = []
        else:
            local_notifyables = local_container.objectValues(meta_type)
        if global_container:
            global_notifyables = global_container.objectValues(meta_type)
            return local_notifyables + global_notifyables
        else:
            return local_notifyables

    def getNotifyablesByGroup(self, group, only=None):
        """ return a list of all notiyables belonging to this group """
        checked = []
        for notifyable in self.getNotifyables(only=only):
            if notifyable.partofGroup(group):
                checked.append(notifyable)

        return checked
        
    def getNotifyablesEmailName(self, only=None):
        """ wrap getNotifyables and return dictionary """
        email_name = {}
        for nf in self.getNotifyables(only=only):
            email_name[nf.getEmail()] = nf.getName()
        return email_name

    def manage_addNotifyables(self, REQUEST):
        """ Save notifyables (only via the web) """

        new_emails = REQUEST.get('new_email',[])
        no_created = 0
        no_attempted = 0
        for c in range(len(new_emails)):
            email = REQUEST['new_email'][c]
            alias = REQUEST['new_alias'][c]
            groups = REQUEST.get('new_groups',[])
            if email != '':
                no_attempted += 1
            if not isinstance(groups, list):
                groups = [groups]
            if Utils.ValidEmailAddress(email):
                self.manage_addNotifyable(email, alias, groups)
                no_created += 1

        if no_created == no_attempted:
            if len(new_emails) > 1:
                mtm = "Notifyables created."
            else:
                mtm = "Notifyable created."
        else:
            if len(new_emails) > 1:
                mtm = """%s out of %s were created.
                Check your input data."""%(no_created, no_attempted)
            else:
                mtm = "Notifyable not created. Check your input data"
        form = self.getManagementForm()
        return form(REQUEST, manage_tabs_message=mtm)

    def manage_addNotifyable(self, email, alias='', groups=[], REQUEST=None):
        """ Create notifyable object """
        email, alias = email.strip(), alias.strip()
        if Utils.ValidEmailAddress(email):
            container = self.getNotifyablesObjectContainer()
            id = self.GenerateNotifyableId(email)
            n = IssueTrackerNotifyable(id, alias, email, groups)
            container._setObject(id, n)

            if REQUEST is not None:
                mtm= "%s created."%NOTIFYABLE_METATYPE
                return MessageDialog(title=mtm, message=mtm,
                                     action='%s/manage_main' % REQUEST['URL1'])
        else:
            raise "InvalidEmailAddress", \
                  "Email address used (%s) was invalid"%email
            

    def manage_delNotifyables(self, REQUEST):
        """ Prepare which notifyable ids to remove """
        ids = REQUEST.get('del_notify_ids',[])
        container = self.getNotifyablesObjectContainer()
        container.manage_delObjects(ids)

        msg = "Notifyables deleted."
        url = self._getManagementFormURL(msg)

        REQUEST.RESPONSE.redirect(url)


    def _filterNotifyGroups(self, groups):
        """ Return the list groups but filter out groups that
            don't exists in getNotifyableGroups()
        """
        existing_group_ids = []
        for group in self.getNotifyableGroups():
            existing_group_ids.append(group.getId())
        n_groups=[]
        for group in groups:
            if group.strip() in existing_group_ids and \
               group.strip() not in n_groups:
                n_groups.append(group.strip())
        return n_groups
        

    # Notify groups
    #

    def hasOldProperty(self):
        """ Returns how many items in the old property """
        if hasattr(self, 'notify_groups') and \
           type(self.notify_groups)==ListType:
            return len(self.notify_groups)
        else:
            return 0

    def convertOldGroups2Objects(self, REQUEST=None):
        """ If still having the old property, recreate as objects """
        all_object_groups = self.getNotifyableGroupIds()
        if self.hasOldProperty():
            for each in self.notify_groups:
                try:
                    self.manage_addNotifyableGroup(each)
                except:
                    pass
            self.notify_groups = []

            if REQUEST is not None:
                form = self.getManagementForm()
                mtm = "Old property now updated for groups."
                return form(REQUEST, manage_tabs_message=mtm)


    def getGroupsByIds(self, ids):
        """ Return the objects of notifyable group ids """
        objects = self.getNotifyableGroups()
        r_objects = []
        for object in objects:
            if object.getId() in ids:
                r_objects.append(object)

        return r_objects
    
    def getNotifyableGroups(self, only=None):
        """ Get all notifyable groups """
        if only =='':
            only = None

        if only=='global':
            local_container = None
        else:
            local_container = self.getNotifyablesObjectContainer(only='local')

        if only=='local':
            global_container = None
        else:
            global_container = self.getNotifyablesObjectContainer(only='global')
            
        meta_type = NOTIFYABLEGROUP_METATYPE
        if local_container is None:
            local_notifyables = []
        else:
            local_notifyables = local_container.objectValues(meta_type)
        if global_container:
            global_notifyables = global_container.objectValues(meta_type)
            return local_notifyables + global_notifyables
        else:
            return local_notifyables

    def getNotifyableGroupIds(self):
        """ return the ids of all group objects """
        ids=[]
        for object in self.getNotifyableGroups():
            ids.append(object.getId())
        return ids
        
        
    def manage_delNotifyGroups(self, notify_groups, REQUEST=None):
        """ delete some groups from self.notify_groups """
        container = self.getNotifyablesObjectContainer()
        container.manage_delObjects(notify_groups)
        msg = 'Notifygroups deleted.'
        if REQUEST is not None:
            url = self._getManagementFormURL(msg)
            REQUEST.RESPONSE.redirect(url)
        else:
            return msg        

    def manage_saveNotifyGroup(self, notify_group, REQUEST):
        """ add one group (via the web only) """
        self.manage_addNotifyableGroup(notify_group)

        msg = "%s created."%NOTIFYABLEGROUP_METATYPE
        url = self._getManagementFormURL(msg)
        REQUEST.RESPONSE.redirect(url)
        

    def GenerateNotifyableId(self, email, length=10, int_length=None):
        """ generate a random id for a notifyable string """
        email= email.replace('@','_at_')
        return email

    def createNotifyGroupId(self, group):
        """ generate a random id for a notifyable string """
        group = Utils.safeId(group.strip())
        group = group.replace(' ','_').replace('-','_').lower()
        return group

    def manage_addNotifyableGroup(self, notify_group, REQUEST=None):
        """ Create a notifyable group """
        dest = self.getNotifyablesObjectContainer()
        id = self.createNotifyGroupId(notify_group)
        group = IssueTrackerNotifyableGroup(id, notify_group)
        dest._setObject(id, group)
        self = dest._getOb(id)

        if REQUEST is not None:
            mtm= "%s created."%NOTIFYABLEGROUP_METATYPE
            return MessageDialog(title=mtm, message=mtm,
                                 action='%s/manage_main' % REQUEST['URL1'])

    def getNotifyablesObjectContainer(self, only=None):
        """ Return the container where notifyables and groups"""
        # Tests whether we are in an IssueTracker
        if only is None:
            if hasattr(self, 'notifyables'):
                return self.notifyables
            else:
                return getattr(self,DEFAULT_NOTIFYABLECONTAINER_ID)
        elif only=='local':
            if hasattr(self, 'notifyables'):
                return self.notifyables
            else:
                return None
        elif only=='global':
            if hasattr(self, DEFAULT_NOTIFYABLECONTAINER_ID):
                return getattr(self,DEFAULT_NOTIFYABLECONTAINER_ID)
            else:
                return None
        else:
            return None


    # Templates
    #

    dtml_file = 'dtml/NotifyableManagementPartForm'
    NotifyableManagementPartForm = DTMLFile(dtml_file, globals())
    

class IssueTrackerNotifyable(SimpleItem.SimpleItem):
    """ IssueTrackerNotifyable class """

    meta_type = NOTIFYABLE_METATYPE
    icon = '%s/issuetracker_notifyable.gif'%ICON_LOCATION
    
    meta_types = []

    _properties=({'id':'alias',         'type': 'string', 'mode':'w'},
                 {'id':'email',         'type': 'string', 'mode':'w'},
                 {'id':'groups',        'type': 'lines',  'mode':'w'},
                 )
    
    security=ClassSecurityInfo()

    manage_editNotifyableForm = DTMLFile('dtml/editNotifyableForm', globals())
    
    manage_options = (
        {'label':'Properties', 'action':'manage_editNotifyableForm'},
        )
    
    def __init__(self, id, alias, email, groups=[]):
        """ init """
        if not Utils.ValidEmailAddress(email):
            raise "InvalidEmailAddress",\
                  "The email address (%s) was incorrect"%email
        else:
            self.id = id
            self.alias = alias.strip()
            self.email = email.strip()
            self.groups = groups

    def getName(self):
        """ Return self.alias. This might be in the future:
            self.firstname + self.lastname
        """
        return self.alias

    def getEmail(self):
        """ return the email address """
        return self.email

    def getTitle(self):
        """ return alias or email address """
        name = self.getName()
        if name:
            return name
        else:
            return self.getEmail()

    def getGroups(self):
        """ return groups """
        return self.groups

    def partofGroup(self, group):
        """ case insensitivly check if 'group' is part of this
        'self.groups' """
        these = [Utils.ss(x) for x in self.getGroups()]
        if isinstance(group, basestring):
            return Utils.ss(group) in these
        else:
            return Utils.ss(group.getTitle()) in these

    def showGroups(self):
        """ return blank or comma separated with brackets """
        

    def manage_editNotifyable(self, alias=None, email=None, groups=None,
                              REQUEST=None):
        """ save changes to Notifyable """
        no = self
        n={'id':no.id}
        if alias is not None:
            self.alias = alias.strip()
        if email is not None and Utils.ValidEmailAddress(email.strip()):
            self.email = email.strip()
        if groups is not None:
            if type(groups) != ListType:
                groups = [groups]
            self.groups = groups

        msg = 'Notifyable updated.'
        if REQUEST is not None:
            url = self.absolute_url()+'/manage_editNotifyableForm'
            params = {'manage_tabs_message':msg}
            url = Utils.AddParam2URL(url, params)
            REQUEST.RESPONSE.redirect(url)
        else:
            return msg
        

    def getEmail(self):
        """ Return self.email """
        return self.email

    def getAlias(self):
        """ Return self.alias """
        return self.alias


        
InitializeClass(IssueTrackerNotifyable)


class IssueTrackerNotifyableGroup(SimpleItem.SimpleItem):
    """ IssueTrackerNotifyableGroup class """

    meta_type = NOTIFYABLEGROUP_METATYPE
    icon = '%s/issuetracker_notifyablegroup.gif'%ICON_LOCATION
    
    meta_types = []

    _properties=({'id':'title', 'type': 'string', 'mode':'w'},
                 )
    
    security=ClassSecurityInfo()

    manage_editNotifyableGroupForm = DTMLFile('dtml/editNotifyableGroupForm', globals())
    
    manage_options = (
        {'label':'Properties', 'action':'manage_editNotifyableGroupForm'},
        )
    
    def __init__(self, id, title):
        """ init """
        self.id = id
        self.title = title
        
    def getId(self):
        """ return id """
        return self.id

    def getTitle(self):
        """ return title """
        return self.title

    def manage_editNotifyableGroup(self, title=None, REQUEST=None):
        """ edit properties """
        if title is not None:
            self.title = title

        if REQUEST is not None:
            mtm="Group changed."
            form = self.manage_editNotifyableGroupForm
            return form(REQUEST, manage_tabs_message=mtm)
                                                       
        

        
InitializeClass(IssueTrackerNotifyable)

zpt_file = 'zpt/addNotifyableContainerForm'
manage_addNotifyableContainerForm = PageTemplateFile(zpt_file, globals())

def manage_addNotifyableContainer(dispatcher, REQUEST=None):
    """ Create a notifyable container object """
    id = DEFAULT_NOTIFYABLECONTAINER_ID
    title = DEFAULT_NOTIFYABLECONTAINER_TITLE
    
    dest = dispatcher.Destination()
    container = IssueTrackerNotifyableContainer(id, title)
    dest._setObject(id, container)
    self = dest._getOb(id)

    if REQUEST is not None:
        mtm= "%s created."%NOTIFYABLECONTAINER_METATYPE
        if int(REQUEST.get('goto_after',0)):
            page = self.manage_GlobalManagementForm
            return page(self, REQUEST, manage_tabs_message=mtm)
        else:
            return MessageDialog(title=mtm, message=mtm,
                             action='%s/manage_main' % REQUEST['URL1'])
    

class IssueTrackerNotifyableContainer(Folder.Folder, 
                                      Notifyables):
    """ IssueTrackerNotifyableContainer class """

    meta_type = NOTIFYABLECONTAINER_METATYPE
    icon = '%s/issuetracker_notifyablegroup.gif'%ICON_LOCATION
    
    #meta_types = [NOTIFYABLEGROUP_METATYPE]

    _properties=({'id':'title',         'type': 'string', 'mode':'w'},
                 {'id':'groups',        'type': 'lines',  'mode':'w'},
                 )
    
    security=ClassSecurityInfo()

    dtml_file = 'dtml/GlobalManagementForm'
    manage_GlobalManagementForm = DTMLFile(dtml_file, globals())
    
    manage_options = (
        {'label':'Management', 'action':'manage_GlobalManagementForm'},
        Folder.Folder.manage_options[0]
        )
    
    def __init__(self, id, title, groups=[]):
        self.id = id
        self.title = title
        self.groups = groups

    def getRandomString(self, length=5, loweronly=0, numbersonly=0):
        """ return a completely random piece of string """
        script = Utils.getRandomString
        return script(length, loweronly, numbersonly)
    
InitializeClass(IssueTrackerNotifyableContainer)
