# IssueTrackerProduct
#
# www.issuetrackerproduct.com
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

__doc__="""IssueTrackerProduct is the easiest bug/issue tracker
system to use for Zope.
By Peter Bengtsson <mail@peterbe.com>

Credits:
Gregory Wild-Smith, sack, http://twilightuniverse.com    
issuetracker-development mailinglist community
Gavin Kistner for the the tabbed Properties tab
Danny W. Adair of Asterisk Ltd for getRolesInContext(self) bug report and patch.
"""
# python
import string, os, re, sys
import random
import poplib

try:
    from poplib import POP3, POP3_SSL
    _has_pop3_ssl = True
except ImportError:
    from poplib import POP3
    _has_pop3_ssl = False
    
import cgi
import cStringIO
import inspect
from time import time
from socket import error as socket_error
from urllib import urlopen
try:
    import transaction
except ImportError:
    # we must be in an older than 2.8 version of Zope
    transaction = None

try:
    import csv
except:
    csv = None
    
try:
    from sets import Set
except ImportError:
    # must be old python 
    Set = None
    
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Header import Header
from email.Utils import parseaddr, formataddr    
    
try:
    import email.Parser as email_Parser
    import email.Header as email_Header
except ImportError:
    email_Parser = None


try:
    from stripogram import html2safehtml
except ImportError:
    html2safehtml = None

try:
    from PIL import Image
except ImportError:
    try:
        import Image
    except ImportError:
        Image = None

try:
    from Products.ExternalEditor import ExternalEditor
    _has_ExternalEditor = True
except ImportError:
    _has_ExternalEditor = False
    
try:
    from formatflowed import decode as formatflowed_decode
    _has_formatflowed_ = True
except ImportError:
    _has_formatflowed_ = False

# Zope
from Products.PageTemplates.PageTemplateFile import PageTemplateFile as PTF
from Globals import Persistent, InitializeClass, package_home, DTMLFile
from OFS import SimpleItem, Folder, PropertyManager
from DocumentTemplate import sequence
from AccessControl import ClassSecurityInfo, getSecurityManager
from Products.ZCatalog.CatalogAwareness import CatalogAware
from Acquisition import aq_inner, aq_parent
from zLOG import LOG, ERROR, INFO, PROBLEM, WARNING
from DateTime import DateTime
from App.ImageFile import ImageFile
from ZPublisher.HTTPRequest import record

# Is CMF installed?
try:
    from Products.CMFCore.utils import getToolByName as CMF_getToolByName
except ImportError:
    CMF_getToolByName = None

try:
    from Products.ZCTextIndex.ParseTree import ParseError
    _has_ZCTextIndex = 1
except:
    class ParseError(Exception): # make it up ourselfs
        pass
    _has_ZCTextIndex = 0

# Zope 2.7 has OrderedFolder baked into the core, oldies have to install it manually
try:
    from OFS.OrderedFolder import OrderedFolder as ZopeOrderedFolder
except ImportError:
    try:
        from Products.OrderedFolder.OrderedFolder import OrderedFolder as ZopeOrderedFolder
    except ImportError:
        m = "OrderedFolder not installed. Reports can not be ordered"
        LOG("IssueTrackerProduct", WARNING, m)
        del m
        from OFS.Folder import Folder as ZopeOrderedFolder
    

# Product
from I18N import _
from upgrade import VersionController
from TemplateAdder import addTemplates2Class, CTP
import Notifyables
import Utils
from Utils import unicodify
from Webservices import IssueTrackerWebservices
from Permissions import *
from Constants import *




    
__version__=open(os.path.join(package_home(globals()), 'version.txt')).read().strip()



#----------------------------------------------------------------------------

def manage_hasAquirableMailHost(self):
    """ return if there is a MailHost object in the aqcuisition path """
    return len(self.superValues(['Mail Host', 'Secure Mail Host'])) > 0

manage_addIssueTrackerForm = PTF('zpt/addIssueTrackerForm', globals())

def manage_addIssueTracker(dispatcher, id, title='', REQUEST=None):
    """ add IssueTracker instance via the web """
    dest = dispatcher.Destination()
    issuetracker = IssueTracker(id, title.strip(),
                                sitemaster_name=title)
    dest._setObject(id, issuetracker)
    self = dest._getOb(id)
    
    self.DeployStandards()
    self.InitZCatalog()
    
    # set that 'IssueTracker Manager' and 'IssueTracker User' should by
    # default have 'Access IssueTracker' permission if these are defined
    roles_4_view = [IssueTrackerManagerRole, IssueTrackerUserRole]
    self.manage_permission('View', roles=roles_4_view,
                            acquire=1)

    if REQUEST is not None:
        # whereto next?
        redirect = REQUEST.RESPONSE.redirect
        if REQUEST.has_key('addandedit'):
            url = self.absolute_url()
            url += '/manage_PropertiesWizard?stage=0&firsttime=1'
            redirect(url)
        elif REQUEST.has_key('addandgoto'):
            redirect(self.absolute_url()+'/manage_workspace')
        elif REQUEST.has_key('DestinationURL'):
            redirect(REQUEST.DestinationURL+'/manage_workspace')
        else:
            redirect(REQUEST.URL1+'/manage_workspace')
            


#----------------------------------------------------------------------------

class IssueTrackerFolderBase(Folder.Folder, Persistent):
    """ A base class for the IssueTracker class """

    def doDebug(self):
        """ return True if we're in debug mode """
        return DEBUG
    
    def getAutosaveInterval(self):
        """ return the seconds interval of how often the autosaving function
        should submit. """
        return AUTOSAVE_INTERVAL_SECONDS
    
    def ValidEmailAddress(self, email):
        """ wrap script """
        script = Utils.ValidEmailAddress
        return script(email)

    def html_entity_fixer(self, text, skipchars=[], extra_careful=1):
        """ wrap script """
        return Utils.html_entity_fixer(text, skipchars=skipchars,
                                       extra_careful=extra_careful)
    
    def newline_to_br(self, text):
        """ wrap script """
        script = Utils.newline_to_br
        return script(text)
    
    def encodeEmailString(self, email, title=None, nolink=0):
        """ wrap script """
        script = Utils.encodeEmailString
        return script(email, title, nolink=nolink)
        
    def sortSequence(self, seq, params):
        """ this is useful because Python Scripts don't 
        allow sequence.sort """
        return sequence.sort(seq, params)

    def getOrdinalth(self, daynr, html=0):
        """ what Utils script """
        return Utils.ordinalth(daynr, html=html)
    
    def timeSince(self, date1, date2, afterword=None, minute_granularity=False):
        """ wrap Utils.timeSince() """
        return Utils.timeSince(date1, date2, afterword=afterword,
                               minute_granularity=minute_granularity)

    def ShowFilesize(self, bytes):
        """ pass on to utilities module """
        return Utils.ShowFilesize(bytes)

    def LineIndent(self, text, indent):
        """ wrap script """
        return Utils.LineIndent(text, indent)

    def getFileIconpath(self, filename):
        """ Try to find a suitable file icon """
        default = '/misc_/OFSP/File_icon.gif'
        extension = filename.lower()[filename.rfind('.')+1:]
        if extension.endswith('~'):
            extension = extension[:-1]
            
        if ICON_ASSOCIATIONS.has_key(extension):
            return '/%s/%s'%(ICON_LOCATION,ICON_ASSOCIATIONS[extension])
        else:
            return default

    def getRandomString(self, length=5, loweronly=0, numbersonly=0):
        """ return a completely random piece of string """
        script = Utils.getRandomString
        return script(length, loweronly, numbersonly)

    def lengthLimit(self, string, maxsize=45, append='...'):
        """ show only the first 'maxsize' characters of the string """
        return Utils.AwareLengthLimit(string, maxsize, append)
        
    def safe_html_quote(self, text):
        """ wrap this improvement to Zope's html_quote in Utils """
        return Utils.safe_html_quote(text)
    
    def tag_quote(self, text):
        """ wrap Utils """
        return Utils.tag_quote(text)
    
    def splitTerms(self, term):
        """ wrap Utils script because it's need in ZPTs """
        return Utils.splitTerms(term)
    


#----------------------------------------------------------------------------

# Misc stuff

ss = lambda s: s.strip().lower() # to save some typing space

def ss_remove(list_, element):
    correct_element = None
    element = ss(element)
    for item in list_:
        if ss(item) == element:
            correct_element = item
            break
    if correct_element is not None:
        list_.remove(correct_element)


signature_patterns = {'url':re.compile('\[url\]', re.I),
                      'title':re.compile('\[title\]', re.I),
                      'sitemaster name':re.compile('\[sitemaster name\]', re.I),
                      'sitemaster email':re.compile('\[sitemaster email\]', re.I),
                      'date':re.compile('\[date\]', re.I),
                      }
                      
def debug(s, tabs=0, steps=(1,), f=False):
    if DEBUG or f:
        inspect_dbg = []
        if type(steps)==type(1):
            steps = range(1, steps+1)
        for i in steps:
            try:
                #caller_module = inspect.stack()[i][1]
                caller_method = inspect.stack()[i][3]
                caller_method_line = inspect.stack()[i][2]
            except IndexError:
                break
            inspect_dbg.append("%s:%s"%(caller_method, caller_method_line))
        out = "\t"*tabs + "%s (%s)"%(s, ", ".join(inspect_dbg))
        
        # XXX this needs attention. Consider implementing a ObserverProxy from
        # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/413701
        print out
        open('issuetracker-debug.log','a').write(out+"\n")
        
class Empty:
    pass
    
#----------------------------------------------------------------------------

class IssueTracker(IssueTrackerFolderBase, CatalogAware,
                   Notifyables.Notifyables, IssueTrackerWebservices
                   ):
    """ IssueTracker class """
    
    meta_type = ISSUETRACKER_METATYPE

    security = ClassSecurityInfo()

    security.setPermissionDefault(AddIssuesPermission, 
                                  (IssueTrackerManagerRole, IssueTrackerUserRole,
                                   'Anonymous', 'Owner', 'Manager'))
                                   

    manage_options = Folder.Folder.manage_options[:2] + \
        ({'label':'Properties', 'action':'manage_editIssueTrackerPropertiesForm'},
         {'label':'Management', 'action':'manage_ManagementForm'}, \
         {'label':'POP3',       'action':'manage_POP3ManagementForm'}) \
        + Folder.Folder.manage_options[3:]

    native_properties = NATIVE_PROPERTIES
    
    # used by CheckoutableTemplates to filter templates
    this_package_home = package_home(globals())
    
    # used for some templates
    project_homepage = 'http://www.issuetrackerproduct.com'
    

    def __init__(self, id, title='',
                 sitemaster_name=DEFAULT_SITEMASTER_NAME,
                 sitemaster_email=DEFAULT_SITEMASTER_EMAIL):
        """ Init IssueTracker class """
        self.id = str(id)
        self.title = str(title)
        
        self.types              = list(DEFAULT_TYPES)
        self.urgencies          = list(DEFAULT_URGENCIES)
        self.sections_options   = list(DEFAULT_SECTIONS_OPTIONS)
        self.defaultsections    = list(DEFAULT_SECTIONS)
        self.when_ignore_word   = DEFAULT_WHEN_IGNORE_WORD
        self.display_date       = DEFAULT_DISPLAY_DATE
        self.always_notify      = DEFAULT_ALWAYS_NOTIFY
        self.sitemaster_name    = sitemaster_name
        self.sitemaster_email   = sitemaster_email
        self.default_type       = DEFAULT_TYPE
        self.default_urgency    = DEFAULT_URGENCY
        self.manager_roles      = DEFAULT_MANAGER_ROLES
        self.default_batch_size = DEFAULT_DEFAULT_BATCH_SIZE
        self.issueprefix        = DEFAULT_ISSUEPREFIX
        self.no_fileattachments = DEFAULT_NO_FILEATTACHMENTS
        self.no_followup_fileattachments = DEFAULT_NO_FOLLOWUP_FILEATTACHMENTS
        self.statuses           = list(DEFAULT_STATUSES)
        self.statuses_verbs     = list(DEFAULT_STATUSES_VERBS)
        self.display_formats    = list(DEFAULT_DISPLAY_FORMATS)
        self.default_display_format = DEFAULT_DEFAULT_DISPLAY_FORMAT
        self.dispatch_on_submit = DEFAULT_DISPATCH_ON_SUBMIT
        self.randomid_length = DEFAULT_RANDOMID_LENGTH
        self.allow_issueattrchange = DEFAULT_ALLOW_ISSUEATTRCHANGE
        self.stop_cache         = DEFAULT_STOP_CACHE
        self.allow_subscription = DEFAULT_ALLOW_SUBSCRIPTION
        self.use_tellafriend = DEFAULT_USE_TELLAFRIEND
        self.use_tellafriend_for_anonymous = DEFAULT_USE_TELLAFRIEND_FOR_ANONYMOUS
        self.show_dates_cleverly = DEFAULT_SHOW_DATES_CLEVERLY
        self.private_statistics = DEFAULT_PRIVATE_STATISTICS
        self.private_reports = DEFAULT_PRIVATE_REPORTS
        self.save_drafts = DEFAULT_SAVE_DRAFTS
        self.show_confidential_option = DEFAULT_SHOW_CONFIDENTIAL_OPTION
        self.show_hideme_option = DEFAULT_SHOW_HIDEME_OPTION
        self.show_issueurl_option = DEFAULT_SHOW_ISSUEURL_OPTION
        self.show_download_button = DEFAULT_SHOW_DOWNLOAD_BUTTON
        self.encode_emaildisplay = DEFAULT_ENCODE_EMAILDISPLAY
        self.show_always_notify_status = DEFAULT_SHOW_ALWAYS_NOTIFY_STATUS
        self.images_in_menu = DEFAULT_IMAGES_IN_MENU
        self.use_issue_assignment = DEFAULT_USE_ISSUE_ASSIGNMENT
        self._assignment_blacklist = []
        self.signature_text = DEFAULT_SIGNATURE_TEXT
        self.default_sortorder = DEFAULT_SORTORDER
        self.can_add_new_sections = DEFAULT_CAN_ADD_NEW_SECTIONS
        self.show_id_with_title = DEFAULT_SHOW_ID_WITH_TITLE
        self.show_use_accesskeys_option = DEFAULT_SHOW_USE_ACCESSKEYS_OPTION
        self.show_remember_savedfilter_persistently_option = DEFAULT_SHOW_REMEMBER_SAVEDFILTER_PERSISTENTLY_OPTION
        self.outlook_batch_size = DEFAULT_OUTLOOK_BATCH_SIZE
        self.use_autosave = DEFAULT_USE_AUTOSAVE
        self.disallow_duplicate_issue_subjects = DEFAULT_DISALLOW_DUPLICATE_ISSUE_SUBJECTS
        self.use_estimated_time = DEFAULT_USE_ESTIMATED_TIME
        self.use_actual_time = DEFAULT_USE_ACTUAL_TIME
        self.include_description_in_notifications = DEFAULT_INCLUDE_DESCRIPTION_IN_NOTIFICATIONS
        self.spam_keywords = DEFAULT_SPAM_KEYWORDS
        self.show_spambot_prevention = DEFAULT_SHOW_SPAMBOT_PREVENTION

        self.acl_cookienames = {}
        self.acl_cookieemails = {}
        self.acl_cookiedisplayformats = {}
        
        self.menu_items = DEFAULT_MENU_ITEMS
        
        self.btreefolder_storage = False
        self.brother_issuetracker_paths = []
        self.plugin_paths = []



    ## Getting basic attributes
        
    def getId(self):
        """ return id """
        return self.id
    
    def getTitle(self):
        """ return title """
        return self.title

    def relative_url(self, url=None):
        """ shorter than absolute_url """
        if url:
            return url.replace(self.REQUEST.BASE0, '')
        path = self.absolute_url_path()
        if path == '/':
            # urls should always be return not ending in a slash
            # so that you can be garanteed this in the templates
            return ''
        else:
            return path

    def XXXglobal_relative_url(self, object_or_url):
        """ return a simpler url of any object """
        if Utils.same_type(object_or_url, 's'):
            url = object_or_url
        else:
            url = object_or_url.absolute_url()
        return url.replace(self.REQUEST.BASE0, '')

    def getStatusesVerbs(self):
        """ return statuses_verbs """
        return getattr(self, 'statuses_verbs', DEFAULT_STATUSES_VERBS)
    
    def getStatuses(self):
        """ return statuses """
        return self.statuses
    
    def getStatusesMerged(self, aslist=0, asdict=0, verb_first=0, cleaned=False):
        """ return statuses and statuses_verbs next to each other 
        So it looks like this ['taken, take', 'rejected, reject', ...]
        
        If the 'cleaned' property is set to true, we clean up all the values carefully.
        This is off by default so that the cleaning only happens on rare occasions such
        as when you're on the Properties tab.
        """
        statuses = self.getStatuses()
        verbs = self.getStatusesVerbs()
        
        if cleaned:
            statuses = [x.strip() for x in statuses if x.strip()]
            verbs = [x.strip() for x in verbs if x.strip()]

            _big_warning = False
            if len(statuses) > len(verbs):
                _big_warning = True
                _add_to_verbs = []
                for i in range(len(statuses)-len(verbs)):
                    _add_to_verbs.append(statuses[len(verbs)+i])
                verbs.extend(_add_to_verbs)
            elif len(verbs) > len(statuses):
                _big_warning = True
                _add_to_statuses = []
                for i in range(len(verbs)-len(statuses)):
                    _add_to_statuses.append(verbs[len(statuses)+i])
                statuses.extend(_add_to_statuses)
                
            if _big_warning:
                msg = "The status list (statuses and verbs) is out of sync and "\
                      "has had to be temporarily merged to work. Please revisit "\
                      "the Properties tab."
                LOG(self.__class__.__name__, WARNING, msg)

            self.statuses = statuses
            self.statuses_verbs = verbs
            
        
        nl=[]
        nldict = {}
        delimiter = ', '
        for i in range(len(statuses)):
            if verb_first:
                nldict[verbs[i].strip()] = statuses[i].strip()
            else:
                nldict[statuses[i].strip()] = verbs[i].strip()
            if aslist:
                nl.append([statuses[i], verbs[i]])
            else:
                nl.append(statuses[i]+delimiter+verbs[i])
        if asdict:
            return nldict
        else:
            return nl
        
    def splitStatusesAndVerbs(self, statuses_and_verbs):
        """ list might be ['open, open', 'taken, take', ...]
        then split this up into two lists.
        
        Raise a ValueError if no delimeter is found or if any value is 
        empty. """
        statuses = []
        verbs = []
        for each in [x.strip() for x in statuses_and_verbs if x.strip()]:
            found_delim = max(each.find(','), each.find(';'),
                              each.find('|'))
            if found_delim > -1:
                splitted = [each[:found_delim], each[found_delim+1:]]
                
                if not splitted[0].strip():
                    raise ValueError, "Status item entered blank (%r)" % each
                
                if not splitted[1].strip():
                    raise ValueError, "Verb item entered blank (%r)" % each
                
                statuses.append(splitted[0].strip())
                verbs.append(splitted[1].strip())
            elif each.strip() != '':
                raise ValueError, "Line contains no delimeter (%r)" % each
                
        return statuses, verbs

    
    def getSectionOptions(self):
        """ return section options """
        return self.sections_options
    
    def getTypeOptions(self):
        """ return types """
        return self.types
    
    def getUrgencyOptions(self):
        """ return urgencies """
        return self.urgencies
    
    def getDefaultSections(self):
        """ return default sections """
        return self.defaultsections
    
    def getDefaultType(self):
        """ return default type """
        return self.default_type
    
    def getDefaultUrgency(self):
        """ return default urgency """
        return self.default_urgency
    
    def getDefaultDisplayFormat(self):
        """ return default_display_format """
        return getattr(self, 'default_display_format', 
                       DEFAULT_DEFAULT_DISPLAY_FORMAT)

    def AllowIssueAttributeChange(self):
        """ Determine if the allow_issueattrchange is True """
        return getattr(self, 'allow_issueattrchange',
                       DEFAULT_ALLOW_ISSUEATTRCHANGE)

    def AllowIssueSubscription(self):
        """ Determine if the allow_subscription is True """
        return getattr(self, 'allow_subscription', DEFAULT_ALLOW_SUBSCRIPTION)
    
    def UseTellAFriend(self):
        """ Determine if we're going to use the tell-a-friend feature on the 
        issue view """
        return getattr(self, 'use_tellafriend', DEFAULT_USE_TELLAFRIEND)
    
    def UseTellAFriendForAnonymous(self):
        """ Determine if we're going to use the tell-a-friend feature on the 
        issue view even for anonymous users """
        return getattr(self, 'use_tellafriend_for_anonymous',
                       DEFAULT_USE_TELLAFRIEND_FOR_ANONYMOUS)
    
    def ShowDatesCleverly(self):
        """ Determine if we're going to show dates differently depending on 
        when the date is. What happens is that dates that are today are shown
        as 'Today 11:25' and really old dates are shown without the time part. 
        """
        return getattr(self, 'show_dates_cleverly', DEFAULT_SHOW_DATES_CLEVERLY)
        
    def PrivateStatistics(self):
        """ Determine if private_statistics is False """
        default = DEFAULT_PRIVATE_STATISTICS
        return getattr(self, 'private_statistics', default)
    
    def PrivateReports(self):
        """ Determine if private_reports is False """
        default = DEFAULT_PRIVATE_REPORTS
        return getattr(self, 'private_reports', default)    

    def SaveDrafts(self):
        """ Return if we allow for saving drafts """
        default = DEFAULT_SAVE_DRAFTS
        return getattr(self, 'save_drafts', default)
    
    def UseAutoSave(self):
        """ return if we're going to use autosave """
        default = DEFAULT_USE_AUTOSAVE
        return getattr(self, 'use_autosave', default)
    
    def DisallowDuplicateIssueSubjects(self):
        """ return disallow_duplicate_issue_subjects """
        default = DEFAULT_DISALLOW_DUPLICATE_ISSUE_SUBJECTS
        return getattr(self, 'disallow_duplicate_issue_subjects', default)
    
    def UseEstimatedTime(self):
        """ return use_estimated_time """
        default = DEFAULT_USE_ESTIMATED_TIME
        return getattr(self, 'use_estimated_time', default)
    
    def UseActualTime(self):
        """ return use_actual_time """
        default = DEFAULT_USE_ACTUAL_TIME
        return getattr(self, 'use_actual_time', default)
    
    def _setUseActualTime(self, toggle_to=True):
        """ set use_actual_time """
        self.use_actual_time = bool(toggle_to)        
    
    def IncludeDescriptionInNotifications(self):
        """ return include_description_in_notifications """
        default = DEFAULT_INCLUDE_DESCRIPTION_IN_NOTIFICATIONS
        return getattr(self, 'include_description_in_notifications', default)
    
    def getSpamKeywords(self):
        """ return spam_keywords if possible """
        return getattr(self, 'spam_keywords', DEFAULT_SPAM_KEYWORDS)
    
    def getSpamKeywordsExpanded(self):
        """ the property 'spam_keywords' is a list that contains potentially
        sublists like this:
            ['foo',
             'bar',
             ['kung', 'fu'],
             ]
        Then, return it like this:
            ['foo',
             'bar',
             '\tkung',
             '\tfu',
             ]
        """
        padding_template = '    %s'
        L = self.getSpamKeywords()[:]
        
        listtest = lambda x: isinstance(x, list)
        for item in L:
            if listtest(item):
                i = L.index(item)
                L.pop(i)
                item.reverse()
                for subitem in item:
                    L.insert(i, padding_template % subitem)
                    
        return L
        
    
    def ShowConfidentialOption(self):
        """ return show_confidential_option """
        default = DEFAULT_SHOW_CONFIDENTIAL_OPTION
        return getattr(self, 'show_confidential_option', default)
    
    def ShowHideMeOption(self):
        """ return show_hideme_option """
        default = DEFAULT_SHOW_HIDEME_OPTION
        return getattr(self, 'show_hideme_option', default)

    def ShowIssueURLOption(self):
        """ return show_issueurl_option """
        # the default is probably False but because we don't want to surprise people
        # with existing issuetracker instance we resolve to True if it 
        # hasn't been set.
        if hasattr(self, 'show_issueurl_option'):
            return self.show_issueurl_option
        else:
            #default = DEFAULT_SHOW_ISSUEURL_OPTION
            default = True
            return default

    def ShowDownloadButton(self):
        """ return show_download_button """
        default = DEFAULT_SHOW_DOWNLOAD_BUTTON
        return getattr(self, 'show_download_button', default)
    
    def EncodeEmailDisplay(self):
        """ return encode_emaildisplay """
        default = DEFAULT_ENCODE_EMAILDISPLAY
        return getattr(self, 'encode_emaildisplay', default)

    def getNoFileattachments(self):
        """ return no_fileattachments or default """
        return getattr(self, 'no_fileattachments', DEFAULT_NO_FILEATTACHMENTS)
    
    def getNoFollowupFileattachments(self):
        """ return no_followup_fileattachments or default """
        return getattr(self, 'no_followup_fileattachments',
                       DEFAULT_NO_FOLLOWUP_FILEATTACHMENTS)

    def doDispatchOnSubmit(self):
        """ Check if we shall dispatch emails out """
        return getattr(self, 'dispatch_on_submit', DEFAULT_DISPATCH_ON_SUBMIT)

    def doStopCache(self):
        """ return the stop_cache property """
        return getattr(self, 'stop_cache', DEFAULT_STOP_CACHE)

    def doShowAlwaysNotifyStatus(self):
        """ return show_always_notify_status """
        return getattr(self, 'show_always_notify_status',
                       DEFAULT_SHOW_ALWAYS_NOTIFY_STATUS)

    def imagesInMenu(self):
        """ return if the images_in_menu attribute is True """
        return getattr(self, 'images_in_menu', DEFAULT_IMAGES_IN_MENU)
    
    def CanAddNewSections(self):
        """ return if can_add_new_sections is True """
        return getattr(self, 'can_add_new_sections', DEFAULT_CAN_ADD_NEW_SECTIONS)
    
    def ShowIdWithTitle(self):
        """ return show_id_with_title """
        return getattr(self, 'show_id_with_title', DEFAULT_SHOW_ID_WITH_TITLE)
    
    def ShowCSVExportLink(self):
        """ return show_csvexport_link """
        return getattr(self, 'show_csvexport_link', DEFAULT_SHOW_CVSEXPORT_LINK)
    
    def ShowAccessKeysOption(self):
        """ return show_use_accesskeys_option """
        default=DEFAULT_SHOW_USE_ACCESSKEYS_OPTION
        return getattr(self, 'show_use_accesskeys_option', default)
    
    def ShowRememberSavedfilterPersistentlyOption(self):
        """ return show_remember_savedfilter_persistently_option """
        default=DEFAULT_SHOW_REMEMBER_SAVEDFILTER_PERSISTENTLY_OPTION
        return getattr(self, 'show_remember_savedfilter_persistently_option', default)
    
    def getOutlookBatchSize(self):
        """ return outlook_batch_size (used in zpt/index_html.zpt) """
        default = DEFAULT_OUTLOOK_BATCH_SIZE
        return getattr(self, 'outlook_batch_size', default)
    
    def ShowSpambotPrevention(self):
        """ return show_spambot_prevention """
        default = DEFAULT_SHOW_SPAMBOT_PREVENTION
        return getattr(self, 'show_spambot_prevention', default)

    def getSitemasterEmail(self):
        """ return sitemaster_email """
        return self.sitemaster_email

    def getSitemasterName(self):
        """ return sitemaster_name """
        return self.sitemaster_name
    
    def getSitemasterFromField(self):
        """ return a combination of sitemaster_name and sitemaster_email """
        name = self.getSitemasterName()
        email = self.getSitemasterEmail()
        assert email.strip(), "Must have email for sitemaster"
        if name.strip():
            return "%s <%s>" % (name, email)
        else:
            return email

    def UseIssueAssignment(self):
        """ return use_issue_assignment """
        return getattr(self, 'use_issue_assignment',
                       DEFAULT_USE_ISSUE_ASSIGNMENT)
                       
    def UseExtendedOptions(self):
        """ return if we should allow for extended options to an issue """
        #### XXXXXXX more work needed here
        return 0

    def getIssueAssignmentBlacklist(self, check_each=False):
        """ return _assignment_blacklist """
        list = getattr(self.getRoot(), '_assignment_blacklist',[])
        if check_each:
            checked = []
            for each in list:
                acl_path, username = each.split(',')
                try:
                    userfolder = self.unrestrictedTraverse(acl_path)
                except:
                    continue
                if userfolder.data.has_key(username):
                    checked.append(each)
            return checked
        else:
            return list

        
    def ShowDescription(self, text, display_format=''):
        """ pass on to utilities module """
        script = Utils.ShowDescription
        if self.EncodeEmailDisplay():
            return script(text, display_format, emaillinkfunction=self.encodeEmailString)
        else:
            return script(text, display_format)
        

    def getSignature(self):
        """ return signature_text """
        return getattr(self, 'signature_text', DEFAULT_SIGNATURE_TEXT)


    def showSignature(self):
        """ return getSignature() with the variables replaced with real stuff """
        text = self.getSignature()
        patterns = signature_patterns

        if patterns['url'].findall(text):
            text = re.sub(patterns['url'], self.getRootURL(), text)

        if patterns['title'].findall(text):
            text = re.sub(patterns['title'], self.getRoot().getTitle(), text)

        if patterns['date'].findall(text):
            date = DateTime().strftime(self.display_date)
            text = re.sub(patterns['date'], date, text)

        if patterns['sitemaster name'].findall(text):
            _v = self.getSitemasterName()
            text = re.sub(patterns['sitemaster name'], _v, text)

        if patterns['sitemaster email'].findall(text):
            _v = self.getSitemasterName()
            text = re.sub(patterns['sitemaster email'], _v, text)

        return text
    
    def showDate(self, date, today=None):
        """ return the date formatted nicely """
        if self.ShowDatesCleverly():
            # The whole reason why today is a parameter is because 
            # if this function is called 20 times in one page 
            # eg. richList.zpt then it'd be a shame to create a new
            # DateTime object every time. By creating it once and
            # passing it every time to this function we save some 
            # CPU and memory
            default_fmt = self.display_date
            def abbr(label, date):
                fmt = default_fmt.replace('%H:%M','').strip()
                return '<abbr title="%s">%s</abbr>' % (date.strftime(fmt), label)
                
            if today is None:
                today = DateTime()
                
            if date.strftime('%Y%m%d') == today.strftime('%Y%m%d'):
                return abbr(_("Today"), date) + date.strftime(" %H:%M")
            elif (date+1).strftime('%Y%m%d') == today.strftime('%Y%m%d'):
                return abbr(_("Yesterday"), date) + date.strftime(" %H:%M")
            elif date.strftime('%Y%W') == today.strftime('%Y%W'):
                return abbr(date.strftime('%A'), date) + date.strftime(' %H:%M')
            elif (date+7).strftime('%Y%W') == today.strftime('%Y%W'):
                return abbr(_("Last week") + date.strftime(' %A'), date) + date.strftime(' %H:%M')
            #elif date.strftime('%Y%m') == today.strftime('%Y%m'):
            #    return date.strftime(default_fmt)
            else:
                
                # skip the hour part
                fmt = default_fmt.replace('%H:%M','').strip()
                return date.strftime(fmt)
            
        
        # default thing
        return date.strftime(self.display_date)
    
    def getDefaultSortorder(self):
        """ return the default sort order """
        return getattr(self, 'default_sortorder', DEFAULT_SORTORDER) # new
    
    def doShowThreads(self):
        """ return if threads should be shown after the issue(s) """
        default = True
        try:
            return Utils.niceboolean(self.REQUEST.get('show-threads', default))
        except:
            return default
        
    def getForcedStylesheet(self):
        """ return which if any forced stylesheet to use """
        v = self.REQUEST.get('forced-stylesheet')
        if not v:
            return None
        else:
            if v.startswith('/') or v.startswith('http'):
                return v
            else:
                return "%s/%s" % (self.getRootURL(), v)
        
    def getPluginPaths(self):
        """ return plugin_paths """
        return getattr(self, 'plugin_paths', [])
    
    def getPluginObjects(self):
        """ return a list of Zope objects which are plugins to the issuetracker
        instance like the MoreStatistics or FileArchive """
        objects = []
        for path in self.getPluginPaths():
            if path:
                try:
                    object = self.restrictedTraverse(path)
                    objects.append(object)
                except:
                    pass
        return objects
                
    
            
        

    
    ##
    ## Getting the issue objects
    ##
    
    def _getIssueContainer(self):
        root = self.getRoot()
        if root._isUsingBTreeFolder():
            return getattr(root, BTREEFOLDER2_ID)
        else:
            return root

    def getBrotherPaths(self):
        """ return the paths of the brother issuetrackers we have """
        return getattr(self, 'brother_issuetracker_paths',[])
        
    def _getBrothers(self):
        """ return a list of Issue Tracker instance objects that we have
        defined as brothers """
        paths = self.getBrotherPaths() 
        trackers = [self.restrictedTraverse(x) for x in paths]
        trackers = [x for x in trackers
                      if x.meta_type == ISSUETRACKER_METATYPE]
        return trackers

    def isFromBrother(self, issue):
        """ return true if the passed issue doesn't belong to this issuetracker """
        return not issue.absolute_url_path().startswith(self.getRoot().absolute_url_path())
    
    def getBrotherFromIssue(self, issue):
        """ return the issuetracker instance this issue belongs to """
        parent = aq_parent(aq_inner(issue))
        if parent.meta_type == 'BTreeFolder2':
            parent = aq_parent(aq_inner(parent))
        return parent
    
    def getIssueObjects(self):
        """ return what objectValues does but with varying container """
        container = self._getIssueContainer()
        brothers = self._getBrothers()
        if brothers:
            all = list(container.objectValues(ISSUE_METATYPE))
            for brother in brothers:
                all.extend(brother.getIssueObjects())
            return all
        else:
            return container.objectValues(ISSUE_METATYPE)
    
    def getIssueItems(self):
        """ return what objectItems does but with varying container """
        container = self._getIssueContainer()
        brothers = self._getBrothers()
        if brothers:
            all = list(container.objectValues(ISSUE_METATYPE))
            for brother in brothers:
                all.extend(list(brother.getIssueItems()))
            return all
        else:
            return container.objectItems(ISSUE_METATYPE)
    
    def getIssueIds(self):
        """ return what objectIds does but with varying container """
        container = self._getIssueContainer()
        brothers = self._getBrothers()
        if brothers:
            all = list(container.objectIds(ISSUE_METATYPE))
            for brother in brothers:
                all.extend(list(brother.getIssueIds()))
            return all
        else:
            return container.objectIds(ISSUE_METATYPE)        
    
    def countIssueObjects(self):
        """ return what objectValues does """
        return len(self.getIssueObjects())
    
    def hasAnyIssues(self):
        """ return if there are any issues in the root at all """
        return self.countIssueObjects() > 0
    
    def ageOfOldestIssue(self):
        """ return the datetime object of the oldest issue """
        oldest = DateTime()
        for issue in self.getIssueObjects():
            if issue.getIssueDate() < oldest:
                oldest = issue.getIssueDate()
        return oldest
    
    def hasIssue(self, issueid):
        """ see if this issue exists """
        return hasattr(self._getIssueContainer(), issueid)
    
    def getIssueObject(self, issueid):
        """ because a plain getattr() wasn't enough """
        return getattr(self._getIssueContainer(), issueid)
    
    def _isUsingBTreeFolder(self):
        """ return if we're using a BTreeFolder2 for storing all issues """
        if not hasattr(self, 'btreefolder_storage'):
            root = self.getRoot()
            self.btreefolder_storage = BTREEFOLDER2_ID in root.objectIds('BTreeFolder2')
        return self.btreefolder_storage
        

    ## Editing the IssueTracker

    def getDisplayDateFormatOptions(self):
        """ return a list of a different formats """
        return ['%d/%m %Y', '%d/%m %Y %H:%M',
                '%m/%d %Y', '%m/%d %Y %H:%M', # US style
                '%d %b %Y', '%d %b %Y %H:%M',
                '%d %B %Y', '%d %B %Y %H:%M',
                '%d-%m-%Y', '%d-%m-%Y %H:%M',
                '%m-%d-%Y', '%m-%d-%Y %H:%M', # US style
                '%d-%b %Y', '%d-%b %Y %H:%M',
                '%d-%B %Y', '%d-%B %Y %H:%M',
                '%Y/%m/%d', '%Y/%m/%d %H:%M',
                '%d/%m/%Y', '%d/%m/%Y - %H:%M',
                '%m/%d/%Y', '%m/%d/%Y - %H:%M',
                ]
                
    def getDefaultSortorderOptions(self):
        """ return which default sort orders we can have """
        return SORTORDER_ALTERNATIVES
    
    def translateSortorderOption(self, variable):
        """ return a nice representation of the variable for the Properties tab. """
        if variable == 'modifydate':
            return _("Modification date")
        elif variable == 'issuedate':
            return _("Creation date")
        else:
            return variable.capitalize()
    
        

    security.declareProtected(VMS, 'manage_findPotentialBrothers')
    def manage_findPotentialBrothers(self):
        """ return a list of all issue tracker instances that can be found in the 
        proximity """
        all = []
        root = self.getRoot()
        root_parent = aq_parent(aq_inner(root))
        
        all = self._getPotentialBrothers(root_parent, skip_id=root.getId())
        
        all.sort(lambda x,y: cmp(x.getTitle(), y.getTitle()))

        return all
            
        
    def _getPotentialBrothers(self, inobject, skip_id=None):
        """ recursively return all issuetracker instances """
        found = []
        for obj in inobject.objectValues():
            # Check that the found object is something sane
            try:
                obj.meta_type
            except:
                continue
            try:
                obj.isPrincipiaFolderish
            except:
                continue

            if obj.meta_type==ISSUETRACKER_METATYPE:
                if skip_id and skip_id == obj.getId():
                    continue
                found.append(obj)
                
            elif obj.isPrincipiaFolderish:
                found.extend(self._getPotentialBrothers(obj, skip_id=skip_id))
                
        return found
    
    
    def _savePluginPaths(self, paths):
        """ filter and save the paths list """
        if isinstance(paths, basestring):
            paths = [paths]
        paths = [x.strip() for x in paths if x.strip()]
        ok = []
        
        for each in paths:
            try:
                obj = self.restrictedTraverse(each)
            except:
                continue
            
            if each not in ok:
                ok.append(each)
                
        self.plugin_paths = ok
        
    security.declareProtected(VMS, 'manage_savePluginPath')
    def manage_savePluginPath(self, path):
        """ add one plugin path to this instance """
        assert path, "Path can't be empty"
        all_paths = self.getPluginPaths() + [path]
        self._savePluginPaths(all_paths)
        
            
    security.declareProtected(VMS, 'manage_editIssueTrackerProperties')
    def manage_editIssueTrackerProperties(self, carefulbooleans=False, 
                                          REQUEST=None):
        """ save all IssueTracker related issues 
        Since booleans are controlled from checkboxes where non-existance
        is the same as False. This is not good because sometimes you don't
        even ask for these checkboxes like in the PropertiesWizard.
        When carefulbooleans=True, non-existant booleans are not set to 
        False.
        """
        hk = self.REQUEST.has_key
        get = self.REQUEST.get
        strings = ['title','display_date','sitemaster_name',
                   'sitemaster_email',
                   'default_type','default_urgency','issueprefix',
                   'default_display_format',
                   'default_sortorder',
                   'signature_text']
        lists = ['types','urgencies','sections_options','defaultsections',
                 'statuses','statuses_verbs','display_formats',
                 'manager_roles',]
        ints = ['default_batch_size','randomid_length','no_fileattachments',
                'no_followup_fileattachments', 'outlook_batch_size']
        booleans = ['dispatch_on_submit','allow_issueattrchange','stop_cache',
                    'allow_subscription',
                    'use_tellafriend',
                    'use_tellafriend_for_anonymous',
                    'private_statistics',
                    'private_reports',
                    'show_confidential_option','show_hideme_option',
                    'show_issueurl_option',
                    'show_download_button','encode_emaildisplay',
                    'show_always_notify_status',
                    'images_in_menu',
                    'use_issue_assignment',
                    'save_drafts',
                    'can_add_new_sections',
                    'show_id_with_title',
                    'show_use_accesskeys_option',
                    'show_remember_savedfilter_persistently_option',
                    'use_autosave',
                    'show_csvexport_link',
                    'disallow_duplicate_issue_subjects',
                    'use_estimated_time',
                    'use_actual_time',
                    'include_description_in_notifications',
                    'show_dates_cleverly',
                    'show_spambot_prevention',
                    ]
        dict = self.__dict__
        for each in strings:
            if hk(each) and Utils.same_type(get(each), 's'):
                dict[each] = get(each).strip()

        for each in ints:
            if hk(each):
                if Utils.same_type(get(each), 3):
                    dict[each] = get(each)
                else:
                    LOG(self.meta_type, WARNING,
                        '%s not integer'%get(each), '')
        for each in lists:
            if hk(each) and Utils.same_type(get(each), []):
                dict[each] = Utils.uniqify(get(each))

        for each in booleans:
            if hk(each) and get(each):
                dict[each] = True
            elif not carefulbooleans:
                dict[each] = False
                
        # now for a special one
        if hk('statuses-and-verbs'):
            if Utils.same_type(get('statuses-and-verbs'), []):
                L1, L2 = self.splitStatusesAndVerbs(get('statuses-and-verbs'))
                self.statuses = L1
                self.statuses_verbs = L2
            else:
                LOG(self.__class__.__name__, PROBLEM,
                    "Statuses and verbs not list type")

        # another special one
        if hk('always_notify'):
            # Every item must be recognized properly
            always_notify = get('always_notify') 

            # clean upp the variable a bit
            always_notify = Utils.uniqify(always_notify)
            always_notify = [x.strip() for x in always_notify]
            while '' in always_notify:
                always_notify.remove('')

            checked = []
            for each in always_notify:
                valid, better_spelling = self._checkAlwaysNotify(each)
                if valid:
                    checked.append(better_spelling)

            self.always_notify = checked
            
        # another special one
        if get('brother_issuetracker_paths'):
            # every item must be recognized properly as an issuetracker instance
            paths = get('brother_issuetracker_paths')
            paths = [x.strip() for x in paths if x.strip()]
            
            # this will raise an error if it can't be reached
            trackers = [self.restrictedTraverse(x) for x in paths]
            
            # this will assert the meta_type
            trackers = [y for y in trackers if y.meta_type == ISSUETRACKER_METATYPE]
            
            self.brother_issuetracker_paths = paths
        else:
            self.brother_issuetracker_paths = []
            
        # another special one
        self._savePluginPaths(get('plugin_paths',[]))

        # for the custom properties
        if REQUEST is not None:
            self.manage_editProperties(REQUEST)
        return self.manage_editIssueTrackerPropertiesForm(self.REQUEST,
                        manage_tabs_message='IssueTracker properties updated.')

    
    def _checkAlwaysNotify(self, item, format='show'):
        """ return a tuple of (validity, spelling). An item is valid if it is
        a valid email address, an exising notifyable or an exisitng
        notifyable group.
        'format' can either be 'show' or list (e.g. [name, email])"""

        item_lower = ss(item)
        
        # check the acl_users
        for iuf in self.superValues(ISSUEUSERFOLDER_METATYPE):
            for username, userdata in iuf.data.items():
                showname = "%s, %s"%(userdata.getFullname(), username)
                if format == 'list':
                    display = [userdata.getFullname(), userdata.getEmail()]
                else:
                    display = showname
                    
                if ss(showname) == item_lower:
                    return True, display
                elif ss(username) == item_lower:
                    return True, display
                elif ss(userdata.getFullname()) == item_lower:
                    return True, display
                elif ss(userdata.getEmail()) == item_lower:
                    return True, display
                elif item_lower.find(ss("(%s)"%username)) > -1:
                    # fragmented possibly because fullname has changed
                    return True, display
                elif not not re.search("\w\s*,\s*%s$"%username, item_lower, re.I):
                    return True, display
                    

        # check the notifyables
        all_notifyables = self.getNotifyables()
        for notifyable in all_notifyables:
            if notifyable.getName():
                showname = "%s, %s"%(notifyable.getName(), notifyable.getEmail())
                if format == 'list':
                    display = [notifyable.getName(), notifyable.getEmail()]
                else:
                    display = showname
            else:
                showname = notifyable.getEmail()
                if format == 'list':
                    display = ['', notifyable.getEmail()]
                else:
                    display = showname
                    
                
            if item_lower == ss(showname):
                return True, display
            elif notifyable.getName().lower()==item_lower or \
                   notifyable.getEmail().lower()==item_lower:
                return True, display
            

        # check all groups
        if item.startswith('group: '):
            item_lower = item_lower[len('group:'):].strip()
        all_groups = self.getNotifyableGroups()
        for group in all_groups:
            if group.getId().lower() == item_lower or \
               group.getTitle().lower() == item_lower:
                if format == 'list':
                    return True, ["group: %s"%group.getTitle(), ""]
                else:
                    return True, "group: %s"%group.getTitle()
            
        # check if it's a plain email address
        if Utils.ValidEmailAddress(item):
            if format == 'list':
                return True, ["", item]
            else:
                return True, item
            
        # default is to deny
        if format == 'list':
            return False, []
        else:
            return False, item

    security.declareProtected(VMS, 'manage_editMenuItems')
    def manage_editMenuItems(self, hrefs, inurls, labels,
                             reset_to_default=False,
                             REQUEST=None):
        """ wrap up the values and save it to _setMenuItems().
        _setMenuItems() accepts a list of dicts. Each inurl can be
        either a string or a tuple, consider it a token. """
        if reset_to_default:
            menu_items = DEFAULT_MENU_ITEMS
        else:
            menu_items = []
            assert len(hrefs)==len(inurls)==len(labels), \
            "Missmatch of no. of hrefs, inurls, labels"
            for i in range(len(hrefs)):
                href = hrefs[i].strip()
                inurl = inurls[i].strip()
                label = labels[i].strip()
                if href+inurl+label == "":
                    continue
                elif not label and href:
                    label = href.split('/')[-1]
                elif not href and label:
                    href = "/" + label
                if len(inurl.split()) > 1:
                    inurl = tuple(inurl.split())
                menu_items.append(
                  dict(href=href, 
                       inurl=inurl,
                       label=label))
                   
        # nothing can really go wrong, 
        # load it in!
        self._setMenuItems(menu_items)
        
        # for the custom properties
        if REQUEST is not None:
            return self.manage_configureMenuForm(self.REQUEST,
                        manage_tabs_message='Menu changed.')
        
        

                
        

    security.declareProtected(VMS, 'manage_addOtherProperty')
    def manage_addOtherProperty(self, id, value, type):
        """ Add arbitrary property """
        self.manage_addProperty(id, value, type)
        page = self.manage_editIssueTrackerPropertiesForm
        return page(self.REQUEST, manage_tabs_message='Other property added.', 
                    activetab='custom' # used by the CSS magic on the Properties tab
                    )

    security.declareProtected(VMS, 'manage_delOtherProperties')
    def manage_delOtherProperties(self, ids):
        """ remove arbitrary properties """
        self.manage_delProperties(ids)
        page = self.manage_editIssueTrackerPropertiesForm
        return page(self.REQUEST, manage_tabs_message='Property deleted',
                    activetab='custom' # See comment about this parameter above
                    )

    ## General IssueTracker maintenance
    
    security.declareProtected(VMS, 'manage_canUseBTreeFolder')
    def manage_canUseBTreeFolder(self):
        """ return True if the BTreeFolder2 product is installed """
        if self.filtered_meta_types():
            all = self.filtered_meta_types()
            for each in all:
                if each.get('product')=='BTreeFolder2':
                    return True
                
        return False
    
    security.declareProtected(VMS, 'manage_isUsingBTreeFolder')
    def manage_isUsingBTreeFolder(self):
        """ just a wrapping """
        return self._isUsingBTreeFolder()
    
   
    
    security.declareProtected(VMS, 'manage_convert2BTreeFolder')
    def manage_convert2BTreeFolder(self, REQUEST=None):
        """ change where we store issues, before they were stored in 
        the issue tracker root (i.e. self.getRoot()) but now we want to 
        store them inside a container of kind BTreeFolder2. """
        
        # 1. Do some basic tests
        assert self.manage_canUseBTreeFolder(), "BTreeFolder2 not installed"
        assert not self.manage_isUsingBTreeFolder(), "BTreeFolder already in use"
        
        # 1. Set up the container
        root = self.getRoot()
        _adder = root.manage_addProduct['BTreeFolder2'].manage_addBTreeFolder
        _adder(id=BTREEFOLDER2_ID)
        container = getattr(self, BTREEFOLDER2_ID)
        
        # 2. Transfer all issues
        cut = root.manage_cutObjects(ids=root.objectIds(ISSUE_METATYPE))
        container.manage_pasteObjects(cut)
        
        # 3. Persistently remember this so that we don't have to look 
        # for a BTreeFolder2 instance every time to deduce if we're
        # storing the issues in a BTree
        root.btreefolder_storage = True
        
        # 4. Copy the internal ID counter
        dest_key = '_nextid_%s' % ss(container.meta_type).replace(' ','')
        source_key = '_nextid_%s' % ss(root.meta_type).replace(' ','')
        if hasattr(root, source_key) and getattr(root, source_key) >= getattr(container, dest_key, 0):
            # do the copy!
            container.__dict__[dest_key] = getattr(root, source_key)
            
        # 5. Update the ZCatalog and everything else
        self.UpdateEverything()
        
        msg = "Converted to storing issues in BTreeFolder"
        if REQUEST is None:
            return msg
        else:
            url = root.absolute_url()+'/manage_ManagementForm'
            url = Utils.AddParam2URL(url, {'manage_tabs_message':msg})
            REQUEST.RESPONSE.redirect(url)        
    
    security.declareProtected(VMS, 'manage_convertFromBTreeFolder')
    def manage_convertFromBTreeFolder(self, REQUEST=None):
        """ change back to storing the issues right inside the
        issue tracker itself"""
        
        # 1. Do some basic tests
        assert self.manage_canUseBTreeFolder(), "BTreeFolder2 not installed"
        assert self.manage_isUsingBTreeFolder(), "BTreeFolder already in use"

        # 2. Transfer all issues
        root = self.getRoot()
        container = getattr(root, BTREEFOLDER2_ID)
        cut = container.manage_cutObjects(ids=container.objectIds(ISSUE_METATYPE))
        root.manage_pasteObjects(cut)
                
        # 3. Persistently remember this so that we don't have to look 
        # for a BTreeFolder2 instance every time to deduce if we're
        # storing the issues in a BTree
        root.btreefolder_storage = False
            
        # 4. Copy the internal ID counter
        dest_key = '_nextid_%s' % ss(root.meta_type).replace(' ','')
        source_key = '_nextid_%s' % ss(container.meta_type).replace(' ','')
        if hasattr(container, source_key) and getattr(container, source_key) >= getattr(root, dest_key, 0):
            # do the copy!
            root.__dict__[dest_key] = getattr(container, source_key)
            
        # 5. Remove the Btreefolder if possible
        if len(container.objectValues()) == 0:
            root.manage_delObjects([BTREEFOLDER2_ID])
            
            
        # 6. Update the ZCatalog and everything else
        root.UpdateEverything()
        
        msg = "Converted back to store issues in Issue Tracker instead of BTreeFolder"
        if REQUEST is None:
            return msg
        else:
            url = root.absolute_url()+'/manage_ManagementForm'
            url = Utils.AddParam2URL(url, {'manage_tabs_message':msg})
            REQUEST.RESPONSE.redirect(url)

    security.declareProtected(VMS, 'ReplaceEmail')
    def ReplaceEmail(self, old, new, caseinsensitive=1, REQUEST=None):
        """ Method that lets you change an occurance of an email address
            to another.
            Useful if a frequence user has changed email accout or something.
        """
        if caseinsensitive:
            old = old.lower()
        root = self.getRoot()
        nochanges_issues = 0
        nochanges_threads = 0
        for issue in root.getIssueObjects():
            iemail = issue.email
            if caseinsensitive:
                iemail = iemail.lower()
            if iemail == old:
                issue.email = new
                nochanges_issues = nochanges_issues + 1
            for thread in issue.objectValues(ISSUETHREAD_METATYPE):
                temail = thread.email
                if caseinsensitive:
                    temail = temail.lower()
                if temail == old:
                    thread.email = new
                    nochanges_threads = nochanges_threads + 1
        
        msg = "Changed %s issues and %s threads"%\
              (nochanges_issues, nochanges_threads)
        if REQUEST is None:
            return msg
        else:
            method = Utils.AddParam2URL
            desturl = root.absolute_url()+"/manage_ManagementForm"
            url = method(desturl,{'manage_tabs_message':msg})
            self.REQUEST.RESPONSE.redirect(url)

    security.declareProtected(VMS, 'ManagementTabs')
    def ManagementTabs(self, whichon='main'):
        """ return a HTML chunk with tabs """
        tabs = (('manage_ManagementForm','Main'),
                ('manage_ManagementNotifyables','Notifyables'),
                ('manage_ManagementUsers','Users'),
                ('manage_ManagementUpgrade','Upgrade'),
                ('manage_ManagementSpamProtection','Spam protection'),
               )
        tabdicts = []
        for tab in tabs:
            item = {}
            url, name = tab
            item['href'] = url
            item['name'] = name
            item['current'] = name.lower()==whichon.lower()
            tabdicts.append(item)

        page = self.management_tabs
        return page(self, self.REQUEST, tabdicts=tabdicts)

    
    def manage_beforeDelete(self, item, container):
        """ we're about to be deleted! """
        self._old_instance_physicalpath = self.getPhysicalPath()
    
    def _postCopy(self, container, op=0):
        """ Called after the copy is finished to accomodate special cases.
        The op var is 0 for a copy, 1 for a move.
        """
        if hasattr(self, '_old_instance_physicalpath'):
            old_path = self._old_instance_physicalpath
            new_path = self.getPhysicalPath()
            self._renameOldPaths(old_path, new_path)
        self.UpdateCatalog()
        
    def _renameOldPaths(self, old_path, new_path):
        """ this issuetracker has changed path from 'old_path' to 'new_path'.
        Change all the references where this appears. For example, there might
        be assignments withing issues that point to users who are defined as
        acl users within this issue tracker. """
        
        old_path_joined = '/'.join(old_path)
        new_path_joined = '/'.join(new_path)
        
        count = {}
        
        for issue in self.getIssueObjects():
            acl_adder = issue.getACLAdder()
            if acl_adder.find(old_path_joined) > -1:
                new_acl_adder = acl_adder.replace(old_path_joined, new_path_joined)
                issue._setACLAdder(new_acl_adder)
                count['issues'] = count.get('issues',0) + 1
                
            for thread in issue.getThreadObjects():
                acl_adder = thread.getACLAdder()
                if acl_adder.find(old_path_joined) > -1:
                    new_acl_adder = acl_adder.replace(old_path_joined, new_path_joined)
                    thread._setACLAdder(new_acl_adder)
                    count['threads'] = count.get('threads',0) + 1
                    
            for assignment in issue.getAssignments(sort=False):
                acl_adder = assignment.getACLAdder()
                if acl_adder.find(old_path_joined) > -1:
                    new_acl_adder = acl_adder.replace(old_path_joined, new_path_joined)
                    assignment._setACLAdder(new_acl_adder)
                    count['assignments'] = count.get('assignments',0) + 1
                    
                acl_assignee = assignment.getACLAssignee()
                if acl_assignee.find(old_path_joined) > -1:
                    new_acl_assignee = acl_assignee.replace(old_path_joined, new_path_joined)
                    assignment._setACLAssignee(new_acl_assignee)
                    count['assignees'] = count.get('assignees',0) + 1
                    
        msg = ''
        if count:
            for k, v in count.items():
                msg += "postcopy fix %s %s\n" %(v, k)
                
        if msg:
            LOG(self.__class__.__name__, INFO, "Post copy fixup: %s" % msg)

    security.declareProtected(VMS, 'UpdateEverything')
    def UpdateEverything(self, DestinationURL=None):
        """ do a DeployStandards(), AssertAllProperties() and UpdateCatalog()
        """

        msgs = []
        
        msgs.append(self.DeployStandards())
            
        msgs.append(self.AssertAllProperties())
            
        msgs.append(self.UpdateCatalog())
            
        msgs.append(self.PrerenderDescriptionsAndComments())
            
        msgs.append(self._cleanTempFolder(implode_if_possible=True))
        
        msgs.append(self.CleanOldSavedFilters(user_excess_clean=True,
                                              implode_if_possible=True,
                                              clean_keyed_only_filtervaluers=True))
                                    
        #msg.append(self.FixNonUnicodeIssues())
        
        msg = '\n'.join([x for x in msgs if x])
        
        if DestinationURL:
            method = Utils.AddParam2URL
            params = {'manage_tabs_message':"Everything updated\n\n%s"%msg,
                      }

            try:
                pingurl = "http://www.issuetrackerproduct.com/UserStories/ping"
                pingable = urlopen(pingurl)
                if pingable:
                    if hasattr(self, 'userstory_plea'):
                        no_previous_pleas = int(getattr(self, 'userstory_plea'))
                    else:
                        no_previous_pleas = 0
                    if no_previous_pleas < 3:
                        params['userstory'] = 'plea'
                    self.userstory_plea = no_previous_pleas + 1
            except:
                pass
            
            url = method(DestinationURL, params)
            self.REQUEST.RESPONSE.redirect(url)
        else:
            return msg

                
    security.declarePrivate('_cleanTempFolder')
    def _cleanTempFolder(self, hours=CLEAN_TEMPFOLDER_INTERVAL_HOURS,
                         implode_if_possible=False):
        """ remove all relativly old files in the temporary directory """

        tempfolder = self._getTempFolder(clean_if_necessary=False)
        folders2del = []

        now = DateTime()
        for folder in tempfolder.objectValues('Folder'):
            if now - folder.bobobase_modification_time() > hours/24.0:
                folders2del.append(folder.getId())

        if folders2del:
            # need to use 'folders2del' here (before the action)
            # because manage_delObjects()
            # will reset the list after execution
            if len(folders2del) < 5:
                del_info = ', '.join(folders2del)
            else:
                del_info = "%s folders in total"%len(folders2del)
            tempfolder.manage_delObjects(folders2del)
            msg = "Deleted temp files: " + del_info
        else:
            msg = ""
            
        if implode_if_possible:
            # maybe the temp-folder is now totally empty, if so, 
            # delete it
            if not len(tempfolder.objectValues()):
                parent = tempfolder.aq_parent
                folderid = tempfolder.getId()
                parent.manage_delObjects([folderid])
                msg += "\nDeleted temp folder because it was empty"
                msg = msg.strip()
                
        return msg
    

    def _getTempFolder(self, clean_if_necessary=True):
        """ make sure there's a folder called `TEMPFOLDER_ID` in the root """
        id = TEMPFOLDER_ID
        root = self.getRoot()
        if id not in root.objectIds(['Folder','BTreeFolder2']):
            title = 'Used for temporary file uploads'
            if self.manage_canUseBTreeFolder():
                _adder = root.manage_addProduct['BTreeFolder2'].manage_addBTreeFolder
            else:
                _adder = root.manage_addFolder
            _adder(id, title)
        elif clean_if_necessary:
            # clean it up from old junk
            self._cleanTempFolder()

        return getattr(root, id)

    
    security.declareProtected(VMS, 'PrerenderDescriptionsAndComments')
    def PrerenderDescriptionsAndComments(self, REQUEST=None):
        """ invoke the _prerender_* function on all issues and threads """
        count_issues = 0
        count_threads = 0
        root = self.getRoot()
        
        for issue in root.getIssueObjects():
            # fix a few possible legacy issues with the issue
            if isinstance(issue.getTitle(), str):
                issue._unicode_title()
            if isinstance(issue.getDescription(), str):
                issue._unicode_description()
            if isinstance(issue.fromname, str):
                issue.fromname = unicodify(issue.fromname)
            
                
            d_before = issue._getFormattedDescription()
            issue._prerender_description()
            d_after = issue._getFormattedDescription()
            if d_before != d_after:
                count_issues += 1
            
            for thread in issue.getThreadObjects():
                # fix a few possible legacy issues with the issue
                if isinstance(thread.getComment(), str):
                    thread._unicode_comment()
                if isinstance(thread.fromname, str):
                    thread.fromname = unicodify(thread.fromname)
                    
                    
                c_before = thread._getFormattedComment()
                thread._prerender_comment()
                c_after = thread._getFormattedComment()
                if d_before != d_after:
                    count_threads += 1
                    
        if count_issues and count_threads:
            if count_issues == 1: msg = "1 issue and "
            else: msg = "%s issues and " % count_issues
            if count_threads == 1: msg += "1 followup "
            else: msg += "%s followups " % count_threads
            msg += "prerendered"
            
        elif not count_threads:
            if count_issues == 1: msg = "1 issue "
            else: msg = "%s issues " % count_issues
            msg += "prerendered"
            
        elif not count_issues:
            if count_threads == 1: msg = "1 followup "
            else: msg = "%s followups " % count_threads
            msg += "prerendered"
            
        else:
            msg = ""

        if REQUEST is None:
            return msg
        else:
            root = self.getRoot()
            desturl = root.absolute_url() + "/manage_ManagementForm"
            url = Utils.AddParam2URL(desturl, {'manage_tabs_message':msg})
            REQUEST.RESPONSE.redirect(url)
        
    
    security.declareProtected(VMS, 'CleanOldSavedFilters')
    def CleanOldSavedFilters(self, user_excess_clean=False, 
                             implode_if_possible=False,
                             clean_keyed_only_filtervaluers=False,
                             REQUEST=None):
        """ remove all saved filters that are X days old. 
        If you pass user_excess_clean=True then it goes through how many
        saved filters each user has. If a user has more than X saved
        filters, all the >X oldest ones are deleted."""
        del_ids = []
        treshold = FILTERVALUER_EXPIRATION_DAYS
        today = DateTime()
        container = self._getFilterValueContainer()
        for filtervaluer in container.objectValues(FILTEROPTION_METATYPE):
            try:
                age = today - filtervaluer.getModificationDate()
            except AttributeError:
                # if the filter valuer doesn't have a mod_date it must be very old
                # ie. a legacy object that we still need to support
                age = today - filtervaluer.bobobase_modification_time()
                
            if filtervaluer.acl_adder:
                # If the filtervaluer is done by some posh person who has a Zope
                # acl user access account, then we give them more breathing space
                # by increasing the treshold limit quite a lot
                used_treshold = treshold * 3
                
            elif clean_keyed_only_filtervaluers and filtervaluer.getKey():
                # This is quite special, filtervaluers that have a "key" have 
                # that because they don't have an acl_adder, 
                # adder_fromname or adder_email. Ie. users who haven't bothered
                # to identify themselfs at all. This kind of people glog up the
                # saved-filters folder with stuff that they might not reuse
                # because either they don't use the issuetracker more than once
                # or they don't support cookies (eg. Googlebot).
                # If this is the case, take out the filtervaluers that are 
                # half-expired (see elif statement above) thus being less 
                # lenient against these kind of objects.
                treshold = treshold / 2
                
            if age > treshold:
                del_ids.append(filtervaluer.getId())
                
        if del_ids:
            msg = "Deleted %s old saved filters" % len(del_ids)
        else:
            msg = ""
        container.manage_delObjects(del_ids)
        
        if not user_excess_clean:
            if implode_if_possible:
                if self._implodeFilterValueContainerIfPossible():
                    msg += "\nDeleted saved filters folder because it was empty"
            
            if REQUEST is None:
                return msg
            else:
                root = self.getRoot()
                desturl = root.absolute_url() + "/manage_ManagementForm"
                url = Utils.AddParam2URL(desturl, 
                                         {'manage_tabs_message':msg})
                REQUEST.RESPONSE.redirect(url)            
                
        
        # Now for an even more anal cleaning. For every user, 
        # we only want them to have a max of FILTERVALUEFOLDER_MAX_PER_USER
        # filtervaluers in their name. There is actually nothing
        # stopping a user having more but that's only because we
        # don't want to annoy them with this restriction when they're
        # using saved filters. It is only here in the cleanup function
        # that we care. 
        
        max_per_user = FILTERVALUER_MAX_PER_USER
        user_valuers = {}
        filtervaluers = container.objectValues(FILTEROPTION_METATYPE)
        sorted_filtervaluers = self.sortSequence(filtervaluers, 
                                                 (('mod_date',),))
        # reversing puts the youngest first in the list
        sorted_filtervaluers.reverse()
        
        del_ids = []
        for filtervaluer in sorted_filtervaluers:
            k = []
            if filtervaluer.acl_adder: 
                k.append(filtervaluer.acl_adder)
            if filtervaluer.adder_fromname:
                k.append(filtervaluer.adder_fromname)
            if filtervaluer.adder_email:
                k.append(filtervaluer.adder_email)
            if filtervaluer.getKey():
                k.append(filtervaluer.getKey())
            k = ','.join(k)
            # k is now the user key. Notice that it doesn't matter
            # how we identified this as long as it's unique.
            # But these in buckets now
            if k:
                if not user_valuers.has_key(k):
                    user_valuers[k] = [filtervaluer.getId()]
                elif len(user_valuers) > max_per_user:
                    # this one goes into the bin
                    del_ids.append(filtervaluer.getId())
                else:
                    user_valuers[k].append(filtervaluer.getId())
                    
                    
        # and we're done, let's see what we caught
        if del_ids:
            msg += "\nDeleted %s user excessive saved filters" % len(del_ids)
            container.manage_delObjects(del_ids)
            
            
        if implode_if_possible:
            if self._implodeFilterValueContainerIfPossible():
                msg += "\nDeleted saved filters folder because it was empty"
            
        if REQUEST is None:
            return msg
        else:
            root = self.getRoot()
            desturl = root.absolute_url() + "/manage_ManagementForm"
            url = Utils.AddParam2URL(desturl, 
                                     {'manage_tabs_message':msg})
            REQUEST.RESPONSE.redirect(url)                    
        

        
    security.declareProtected(VMS, 'AssertAllProperties')
    def AssertAllProperties(self, REQUEST=None):
        """ invoke the assertAllProperties() on all objects """
        count = 0
        count += self._assertAllProperties()
        root = self.getRoot()
        for issue in root.getIssueObjects():
            count += issue.assertAllProperties()
            for thread in issue.objectValues(ISSUETHREAD_METATYPE):
                count += thread.assertAllProperties()

        if count:
            msg = "Made sure %s objects have all properties."%count
        else:
            msg = "No objects needed assurance on new properties."
            
        if REQUEST is None:
            return msg
        else:
            root = self.getRoot()
            method = Utils.AddParam2URL
            desturl = root.absolute_url()+"/manage_ManagementForm"
            url = method(desturl,{'manage_tabs_message':msg})
            self.REQUEST.RESPONSE.redirect(url)
        
    security.declarePrivate('_assertAllProperties')
    def _assertAllProperties(self): # sorry about the ugly name
        """ Return how many properties we made sure we have.
        Make sure the the root has the correct properties. """
        self = self.getRoot() # be certain that we're in the root object
        count = 0
        
        checks = {'menu_items':DEFAULT_MENU_ITEMS,
                  'show_id_with_title':DEFAULT_SHOW_ID_WITH_TITLE,
                  'show_use_accesskeys_option':DEFAULT_SHOW_USE_ACCESSKEYS_OPTION,
                  'can_add_new_sections':DEFAULT_CAN_ADD_NEW_SECTIONS,
                  'images_in_menu':DEFAULT_IMAGES_IN_MENU,
                  'use_estimated_time':DEFAULT_USE_ESTIMATED_TIME,
                  'use_actual_time':DEFAULT_USE_ACTUAL_TIME,
                  'include_description_in_notifications':DEFAULT_INCLUDE_DESCRIPTION_IN_NOTIFICATIONS,
                  'use_tellafriend':DEFAULT_USE_TELLAFRIEND,
                  'brother_issuetracker_paths':[],
                  'plugin_paths':[],
                  }
        for key, default in checks.items():
            if not hasattr(self, key):
                self.__dict__[key] = default
                count += 1
            
        return count
        
        
            

    security.declareProtected(VMS, 'DeployStandards')
    def DeployStandards(self, remove_oldstuff=0, DestinationURL=None,
                        initzcatalog=1):
        """ copy images and other documents into the instance unless they
            are already there
        """
        t={}
        
        if initzcatalog:
            t = self.InitZCatalog(t=t)
            
        # create folders
        root = self.getRoot()
        #for f in ['notifyables', 'www', 'tinymce']:
        for f in ['notifyables', 'www']:
            if not f in root.objectIds('Folder'):
                root.manage_addFolder(f)
                t[f]='Folder'

        osj = os.path.join
        standards_home = osj(package_home(globals()),'standards')
        self._deployImages(root, standards_home,
                           t=t, remove_oldstuff=remove_oldstuff,
                           skipfolders=('mainbuttons','actionbuttons','.svn','CVS'))

        www_home = osj(standards_home,'www')
        self._deployImages(root.www, www_home,
                           t=t, remove_oldstuff=remove_oldstuff,
                           skipfolders=('.svn','CVS'))
                               
        ##home = osj(standards_home, 'tinymce')
        ##self._deployImages(root.tinymce, home,
        ##                   t=t, remove_oldstuff=remove_oldstuff,
        ##                   check_updates=True)
        ##self._deployDocuments(root.tinymce, home,
        ##                      t=t, remove_oldstuff=remove_oldstuff,
        ##                      check_updates=True)
                              
        # perhaps TinyMCE is now installed but 'html' is not a recognized
        # display format option
        if self.hasWYSIWYGEditor() and 'html' not in self.display_formats:
            df = list(self.display_formats)
            df.append('html')
            self.display_formats = df
        

        msg = "Standard objects deployed\n"
        if t:
            for k,v in t.items():
                msg += "(%s)\n%s" % (k, v)
        else:
            msg = "No standard objects deployed."
        if DestinationURL:
            method = Utils.AddParam2URL
            url = method(DestinationURL,{'manage_tabs_message':msg})
            self.REQUEST.RESPONSE.redirect(url)
        else:
            return msg

    def _deployImages(self, destination, directory, 
                      extensions=['.gif','.ico','.jpg','.png'],
                      t={}, 
                      remove_oldstuff=False,
                      check_updates=False,
                      skipfolders=[]):
        """ do the actual deployment of images in a dir """
    
        # expect 'skipfolders' to be a list of tuple
        if skipfolders is None:
            skipfolders = []
        elif not isinstance(skipfolders, (tuple, list)):
            skipfolders = [skipfolders]
        
        osj = os.path.join
        base= getattr(destination,'aq_base',destination)
        for filestr in os.listdir(directory):
            if os.path.isdir(osj(directory, filestr)):
                if filestr in skipfolders:
                    continue
                
                if hasattr(base, filestr) and remove_oldstuff:
                    destination.manage_delObjects([filestr])
                    
                if not hasattr(base, filestr):
                    destination.manage_addFolder(filestr)
                    t[filestr] = "Folder"
                
                new_destination = getattr(destination, filestr)
                self._deployImages(new_destination, osj(directory, filestr),
                      extensions=extensions, t=t, remove_oldstuff=remove_oldstuff,
                      check_updates=check_updates,
                      skipfolders=skipfolders)
                
                
            elif self._file_has_extensions(filestr, extensions):
                # take the image
                id, title = Utils.cookIdAndTitle(filestr)
                
                if hasattr(base, id) and remove_oldstuff:
                    destination.manage_delObjects([id])
                    
                if hasattr(base, id) and check_updates:
                    # if the new file is different, delete the existing current one
                    this_image = getattr(destination, id)
                    this_length = len(this_image.data)
                    that_image = open(osj(directory, filestr),'rb').read()
                    that_length = len(that_image)
                    if this_length != that_length:
                        destination.manage_delObjects([id])
                    
                if not hasattr(base, id):
                    destination.manage_addImage(id, title=title, \
                          file=open(osj(directory, filestr),'rb').read())
                    t[id]="Image"
        
    def _file_has_extensions(self, filestr, extensions):
        """ check if a filestr has any of the give extensions """
        for extension in extensions:
            if filestr.find(extension) > -1:
                return True
        return False


    def _deployDocuments(self, destination, directory,
                      extensions=('.js','.css','.html','.htm'),
                      t={}, remove_oldstuff=False,
                      check_updates=False):
        """ do the actual deployment of images in a dir """
        osj = os.path.join
        base= getattr(destination,'aq_base',destination)
        for filestr in os.listdir(directory):
            if os.path.isdir(osj(directory, filestr)):
                
                if hasattr(base, filestr) and remove_oldstuff:
                    destination.manage_delObjects([filestr])
                    
                if not hasattr(base, filestr):
                    destination.manage_addFolder(filestr)
                    t[filestr] = "Folder"
                
                new_destination = getattr(destination, filestr)
                self._deployDocuments(new_destination, osj(directory, filestr),
                      extensions=extensions, t=t, remove_oldstuff=remove_oldstuff,
                      check_updates=check_updates)
                
            elif self._file_has_extensions(filestr, extensions):
                # take the image
                id, title = Utils.cookIdAndTitle(filestr)
                
                if hasattr(base, id) and remove_oldstuff:
                    destination.manage_delObjects([id])
                    
                if hasattr(base, id) and check_updates:
                    this_content = open(osj(directory, filestr)).read()
                    this_content = self._massageDTMLDocumentContent(filestr, this_content)
                    that_content = getattr(destination, id).document_src()
                    if this_content != that_content:
                        destination.manage_delObjects([id])
                    
                if not hasattr(base, id):
                    content = open(osj(directory, filestr)).read()
                    content = self._massageDTMLDocumentContent(filestr, content)
                    destination.manage_addDTMLDocument(id, title,
                       file=content)
                    #destination.manage_addImage(id, title=title, \
                    #      file=open(osj(directory, filestr),'rb').read())
                    t[id]="Document"

    def _massageDTMLDocumentContent(self, filename, content):
        """ return the content slightly modified. 
        The purpose of this method is to improve and prepare the document for the 
        usage. If the filename ends in '.js' put some caching header and some
        DTML code that sets the correct Content-Type. """
        if content.lower().find("setHeader('Content-Type')".lower()) == -1:
            if filename.endswith('.js'):
                add = '<dtml-call "RESPONSE.setHeader(\'Content-Type\',\'application/x-javascript\')">'
            elif filename.endswith('.css'):
                add = '<dtml-call "RESPONSE.setHeader(\'Content-Type\',\'text/css\')">'
            else:
                add = None
                
            if add:
                content = add + content.strip()
                
        if content.find('doCache(') == -1:
            content = '<dtml-call "doCache(hours=12)">' + content.strip()

        return content
            

    ## Properties wizard

    security.declareProtected(VMS, 'manage_PropertiesWizard')
    def manage_PropertiesWizard(self, REQUEST, *args, **kw):
        """ Overridden template """

        try:
            firsttime = int(REQUEST.get('firsttime',0))
        except:
            firsttime = 0

        stage, msg, error = self._saveFromPropertiesWizard(REQUEST)

        if msg:
            kw['manage_tabs_message'] = msg.strip()+'\n'

        if error:
            kw['error'] = error
            
        kw['stage'] = stage
        kw['firsttime'] = firsttime
        file = 'dtml/PropertiesWizard'
        name = 'PropertiesWizard'
        return apply(DTMLFile(file, globals(), __name__=name
                              ).__of__(self), (), kw)

    def _saveFromPropertiesWizard(self, request):
        """ return message a dict of submission error """

        try:
            submit = int(request.get('submit',1))
        except:
            submit = 1
            
        try:
            stage = int(request.get('stage',0))
        except:
            stage = 0

        try:
            firsttime = int(request.get('firsttime',0))
        except:
            firsttime = 0

        msg = None
        error = {}


        if not submit:
            return stage, msg, error


        if stage == 1 and firsttime:
            msg = []
            # attempt to save properties from stage 1
            whatuse = ss(request.get('whatuse','softwaredevelopment'))
            if whatuse == 'helpdesk_external':
                
                sections = ['General','Front office','Back office','Other']
                self.sections_options = sections
                msg.append("Set section options to: " + ', '.join(sections))

                types = ['general', 'announcement', 'idea', 'content',
                         'feature request','question','other']
                self.types = types
                msg.append("Set type options to: " +', '.join(types))
                
                if not self.allow_subscription:
                    self.allow_subscription = True
                    msg.append("Allowed issue subscription")
                    
                if not self.show_confidential_option:
                    self.show_confidential_option = True
                    msg.append("Allowed for confidential issues")

                if not self.show_hideme_option:
                    self.show_hideme_option = True
                    msg.append("Allowed for \"hide me\" option")
                    
                   
                
            elif whatuse == 'helpdesk_internal':
                sections = ['General','Back office','Other']
                self.sections_options = sections
                msg.append("Set section options to: " + ', '.join(sections))

                types = ['general', 'announcement', 'idea', 'content',
                         'feature request','question','other']
                self.types = types
                msg.append("Set type options to: " +', '.join(types))
                
                if self.isViewPermissionOn():
                    self.manage_ViewPermissionToggle()
                    msg.append("Switched off Anonymous access")

                if not self.UseIssueAssignment():
                    self.manage_UseIssueAssignmentToggle()
                    msg.append("Switched on Issue Assignment")

                if not self.private_statistics:
                    self.private_statistics = True
                    msg.append("Allow statistics")

                if self.encode_emaildisplay:
                    self.encode_emaildisplay = False
                    msg.append("Email addresses not encoded")

                if not self.show_always_notify_status:
                    self.show_always_notify_status = True
                    msg.append("Always show who was notified")
                
                if not self.CanAddNewSections():
                    self.can_add_new_sections = True
                    msg.append("Can add new sections with each issue")
                
            else:
                # first time typical sections
                sections = ['General','Database','Interface','Support',
                            'Documentation','Other']
                self.sections_options = sections
                msg.append("Set section options to: " + ', '.join(sections))

                types = ['general','announcement','bug report',
                         'feature request','content request',
                         'usability','other']
                self.types = types
                msg.append("Set type options to: " +', '.join(types))

                if not self.UseIssueAssignment():
                    self.manage_UseIssueAssignmentToggle()
                    msg.append("Switched on Issue Assignment")

                if not self.show_always_notify_status:
                    self.show_always_notify_status = True
                    msg.append("Always show who was notified")

                if self.no_followup_fileattachments == 0:
                    self.no_followup_fileattachments = 1
                    _m = "Allowed for at least one file "
                    _m += "attachment on follow up"
                    msg.append(_m)

            msg = '\n'.join(msg)

            # can now move on to stage 2
            stage += 1

        elif stage == 2:
            msg = []
            sections_options = request.get('sections_options',[])

            # clean them a bit
            sections_options = [x.strip() for x in sections_options if x.strip()]
            sections_options = Utils.uniqify(sections_options)
            
            if not sections_options:
                error['sections_options'] = "No sections entered"
            else:
                self.sections_options = sections_options
                msg = "Set section options to: " + ', '.join(sections_options)
                stage += 1

        elif stage == 3:
            defaultsections = request.get('defaultsections',[])
            if not defaultsections:
                request.set('defaultsections', [self.sections_options[0]])
                m = "None selected, try %s?"%self.sections_options[0]
                error['defaultsections'] = m
            else:
                # filter out unrecognized ones
                checked = []
                for each in defaultsections:
                    if each in self.sections_options:
                        checked.append(each)

                if not checked:
                    m = "None of selected was recognized"
                    error['defaultsections'] = m
                else:
                    self.defaultsections = checked
                    if len(checked) > 1:
                        msg = "Set default sections to: "
                    else:
                        msg = "Set default section to: "
                    msg += ', '.join(checked)
                    
                    stage += 1

        elif stage == 4:
            types = request.get('types',[])
            urgencies = request.get('urgencies',[])

            # clean them a bit
            types = [x.strip() for x in types]
            urgencies = [x.strip() for x in urgencies]
            while '' in types:
                types.remove('')
            while '' in urgencies:
                urgencies.remove('')
            types = Utils.uniqify(types)
            urgencies = Utils.uniqify(urgencies)

            if not types:
                error['types'] = "None entered"
                
            if not urgencies:
                error['urgencies'] = "None entered"

            if types and urgencies:
                self.types = types
                self.urgencies = urgencies
                msg = "Set types to: " + ', '.join(types) + '\n'
                msg += "Set urgencies to: " + ', '.join(urgencies)

                stage += 1
                

        elif stage == 5:
            default_type = request.get('default_type','').strip()
            ok = True
            if default_type not in self.types:
                error['default_type'] = "Unrecognized"
                ok = False

            default_urgency = request.get('default_urgency','').strip()
            if default_urgency not in self.urgencies:
                error['default_urgency'] = "Unrecognized"
                ok = False

            if ok:
                self.default_type = default_type
                self.default_urgency = default_urgency
                msg = "Default type set to: " + default_type + '\n'
                msg += "Default urgency set to: " + default_urgency
                stage += 1
                

        elif stage == 6:
            _default = self.getDefaultSortorder()
            default_sortorder = request.get('default_sortorder', _default)
            if default_sortorder not in self.getDefaultSortorderOptions():
                error['default_sortorder'] = "Unrecognized option"
                ok = False
            else:
                self.default_sortorder = default_sortorder
                _translated = self.translateSortorderOption(default_sortorder)
                msg = "Default sort order set to %s"%_translated
                stage += 1

        elif stage == 8:
            always_notify = request.get('always_notify',[])
            always_notify = [x.strip() for x in always_notify]
            while '' in always_notify:
                always_notify.remove('')

            # Check that each is either a notifyable or a valid
            # email address.
            notifyables = self.getNotifyables()
            notifyables_names = [x.getName() for x in notifyables]
            email_checker = Utils.ValidEmailAddress

            checked = []
            invalids = []
            for each in always_notify:
                if each in notifyables_names:
                    checked.append(each)
                elif Utils.ValidEmailAddress(each):
                    checked.append(each)
                else:
                    invalids.append(each)

            
            self.always_notify = checked

            if invalids:
                m = "Invalid entries: "+ ', '.join(invalids)
                error['always_notify'] = m
            else:
                msg = "Set to always be notified: "
                msg += ', '.join(checked)
                
                stage += 1

        
        elif stage == 9:
            sitemaster_name = request.get('sitemaster_name','').strip()
            sitemaster_email = request.get('sitemaster_email','').strip()

            ok = True
            if not sitemaster_name:
                error['sitemaster_name'] = "Empty"
                ok = False
            if sitemaster_email != DEFAULT_SITEMASTER_EMAIL and \
               not Utils.ValidEmailAddress(sitemaster_email):
                error['sitemaster_email'] = "Invalid"
                ok = False

            if ok:
                self.sitemaster_name = sitemaster_name
                self.sitemaster_email = sitemaster_email
                msg = "Site name set to:  %s\n"%sitemaster_name
                msg +="Site email set to: %s"%sitemaster_email
                
                stage += 1
            
        elif stage==10:
            no_fileattachments = request.get('no_fileattachments',1)
            no_followup_fileattachments = request.get('no_followup_fileattachments',1)
            display_date = request.get('display_date','').strip()
            show_dates_cleverly = bool(request.get('show_dates_cleverly',0))

            ok = True
            try:
                no_fileattachments = int(no_fileattachments)
            except ValueError:
                error['no_fileattachments'] = "Not a number"
                ok = False

            try:
                no_followup_fileattachments = int(no_followup_fileattachments)
            except ValueError:
                error['no_followup_fileattachments'] = "Not a number"
                ok = False

            if not display_date:
                error['display_date'] = "No display date format"
                ok = False
                
            # nothing to test on the show_dates_cleverly

            if ok:
                self.no_fileattachments = no_fileattachments
                self.no_followup_fileattachments = no_followup_fileattachments
                self.display_date = display_date
                self.show_dates_cleverly = show_dates_cleverly
                msg = ""
                if no_fileattachments == 0:
                    msg += "No file attachments to issues.\n"
                elif no_fileattachments == 1:
                    msg += "One file attachment to issues.\n"
                else:
                    msg += "%s file attachments to issues.\n"%no_fileattachments
                    
                if no_followup_fileattachments == 0:
                    msg += "No file attachments to follow ups.\n"
                elif no_followup_fileattachments == 1:
                    msg += "One file attachment to follow ups.\n"
                else:
                    msg += "%s file attachments to follow ups.\n"%no_followup_fileattachments

                msg += "Displays date in this format:"
                msg += DateTime().strftime(display_date)
                if show_dates_cleverly:
                    msg += " (and dates are shown differently depending on how far from today)"
                msg = msg.strip()
                
                stage += 1
                

        elif stage == 11:

            bool_keys = ('allow_issueattrchange', 'allow_subscription',
                         'use_tellafriend',
                         'private_statistics', 'encode_emaildisplay',
                         'show_always_notify_status',
                         'show_confidential_option', 'show_hideme_option',
                         'show_issueurl_option',
                         'can_add_new_sections', 'images_in_menu',
                         )
            for key in bool_keys:
                try:
                    value = bool(int(request.get(key, getattr(self, key))))
                except:
                    continue

                self.__dict__[key] = value
                msg = "Yes/No questions set."
                stage = 12

        else:
            stage += 1 #pass #raise "WhatNow", "What do we do now?"
            if stage == 1 and not firsttime:
                stage = 2

        if msg == []:
            msg = None
            
        return stage, msg, error
            


    def ShowError(self, error, id, htmlwrap=1):
        """ show the error (used only by PropertiesWizard.dtml """
        
        if error and error.has_key(id):
            s = error.get(id)
            if htmlwrap:
                s = '<span class="submiterror">%s</span><br />'%s
                return s
            else:
                return s
        else:
            return ''
        
        
    

    ## Users part of Management related

    def getAllIssueUserFolders(self):
        """ return all objects that are IssueUserFolders """
        return self.superValues(ISSUEUSERFOLDER_METATYPE)


    def getAllIssueUsers(self, userfolders=None, filter=1, exclude_assignee=None):
        """ return all the acl users as identifiers """
        if userfolders is None:
            userfolders = self.getAllIssueUserFolders()
        elif not Utils.same_type(userfolders, []):
            userfolders = [userfolders]

        users = []
        if filter:
            blacklist = self.getIssueAssignmentBlacklist()
        else:
            blacklist = []

        for userfolder in userfolders:
            userfolderpath = userfolder.getIssueUserFolderPath()
            for username, user in userfolder.data.items():
                username = userfolderpath+','+username
                if username not in blacklist:
                    
                    # skip 
                    if exclude_assignee and  username == exclude_assignee:
                        continue
                    
                    users.append({'userfolder':userfolder,
                                  'user':user,
                                  'identifier':username})
        return users
                
            
        
    security.declareProtected(VMS, 'manage_UseIssueAssignmentToggle')
    def manage_UseIssueAssignmentToggle(self, DestinationURL=None):
        """ inverse the value of self.use_issue_assignment """
        self.use_issue_assignment = not self.UseIssueAssignment()
        if self.UseIssueAssignment():
            msg = "Issue Assignment switched on"
        else:
            msg = "Issue Assignment switched off"
        if DestinationURL:
            method = Utils.AddParam2URL
            url = method(DestinationURL,{'manage_tabs_message':msg})
            self.REQUEST.RESPONSE.redirect(url)
        else:
            return msg

    security.declareProtected(VMS, 'manage_AddToBlacklist')
    def manage_AddToBlacklist(self, add_identifiers, DestinationURL=None):
        """ add some identifiers to the blacklist """
        before = self.getIssueAssignmentBlacklist(check_each=True)
        blacklist = before + add_identifiers
        checked = []
        for identifier in blacklist:
            if identifier not in checked:
                checked.append(identifier)
        self._assignment_blacklist = checked

        if len(add_identifiers) == 1:
            msg = "User blacklisted"
        else:
            msg = "Users blacklisted"
        if DestinationURL:
            method = Utils.AddParam2URL
            url = method(DestinationURL,{'manage_tabs_message':msg})
            self.REQUEST.RESPONSE.redirect(url)
        else:
            return msg


    security.declareProtected(VMS, 'manage_RemoveFromBlacklist')
    def manage_RemoveFromBlacklist(self, remove_identifiers,
                                   DestinationURL=None):
        """ remove some identifiers from the blacklist """
        before = self.getIssueAssignmentBlacklist()
        checked = []
        for identifier in before:
            if identifier not in remove_identifiers:
                checked.append(identifier)
        self._assignment_blacklist = checked

        if len(remove_identifiers) == 1:
            msg = "User blacklisted"
        else:
            msg = "Users blacklisted"
        if DestinationURL:
            method = Utils.AddParam2URL
            url = method(DestinationURL,{'manage_tabs_message':msg})
            self.REQUEST.RESPONSE.redirect(url)
        else:
            return msg

    def isAnonymous(self):
        """ return true if the user is not logged into zope in any way. """
        username = getSecurityManager().getUser().getUserName()
        return username.lower().replace(' ','') == 'anonymoususer'

    security.declareProtected(VMS, 'isViewPermissionOn')
    def isViewPermissionOn(self):
        """ return True if View permission is on for Anonymous """
        return not not self.acquiredRolesAreUsedBy('View')

    security.declareProtected(VMS, 'manage_ViewPermissionToggle')
    def manage_ViewPermissionToggle(self, DestinationURL=None):
        """ Change the Aquire attribute for the View permission """
        viewpermission_on = self.isViewPermissionOn()
        roles_4_view = ['Manager', IssueTrackerManagerRole, IssueTrackerUserRole]
        self.manage_permission('View', roles=roles_4_view,
                               acquire=not viewpermission_on)

        if viewpermission_on:
            msg = "View permission disabled for Anonymous"
        else:
            msg = "View permission enabled for Anonymous"
        if DestinationURL:
            method = Utils.AddParam2URL
            url = method(DestinationURL,{'manage_tabs_message':msg})
            self.REQUEST.RESPONSE.redirect(url)
        else:
            return msg


    ## Useful root instance methods

    def getRoot(self):
        """ Get the root instance object """
        mtype = ISSUETRACKER_METATYPE
        r = self
        while r.meta_type != mtype:
            r = aq_parent(aq_inner(r))
        return r

    def titleTag(self):
        """ return suitable content for <title> tag """
        root_title = self.getRoot().title_or_id()
        title = root_title
        if self.meta_type == ISSUE_METATYPE:
            prefix = ""
            if Utils.niceboolean(self.REQUEST.get('autorefresh')):
                prefix = _("(auto refreshed)")
                
            if self.ShowIdWithTitle():
                title = "%s %s - #%s %s" 
                title = title % (prefix, root_title, self.getIssueId(), self.getTitle())
            else:
                title = "%s %s - %s" % (prefix, root_title, self.getTitle())

        else:
            page = self.REQUEST.URL.split('/')[-1]
            _rtdict = {'root_title':root_title}
            if page == 'ListIssues':
                title = _('%(root_title)s - List Issues') % _rtdict
            elif page == 'CompleteList':
                title = _('%(root_title)s - Complete List') % _rtdict
            elif page == 'AddIssue':
                if self.REQUEST.form.has_key('previewissue'):
                    title = _('Preview before adding issue - %(root_title)s') % _rtdict
                else:
                    title = _('%(root_title)s - Add Issue') % _rtdict
            elif page == 'QuickAddIssue':
                title = _('%(root_title)s - Quick Add Issue') % _rtdict
            elif page == 'User':
                title = '%(root_title)s - User' % _rtdict
            elif page == 'About.html':
                title = _('About the IssueTrackerProduct version %s')
                title = title % self.getIssueTrackerVersion()
            elif page == 'SubmitIssue':
                if self.REQUEST.get('HTTP_REFERER').find('QuickAddIssue'):
                    title = _('%(root_title)s - Quick Add Issue') % _rtdict
                else:
                    title = _('%(root_title)s - Add Issue') % _rtdict
            elif page == 'What-is-WYSIWYG':
                title = "WYSIWYG = What You See Is What You Get"
            elif page == 'What-is-StructuredText':
                title = "About Structured Text"
        
        if isinstance(title, str):
            # legacy
            return Utils.html_entity_fixer(title)
        else:
            # new way
            return title
    
    
    def hasWYSIWYGEditor(self):
        """ return true if we have a WYSIWYG editor available """
        return self.getWYSIWYGEditor() is not None
    
    def getWYSIWYGEditor(self):
        """ return the ztinymce configuration with the expected name """
        ztinymce_conf_id = 'tinymce-issuetracker.conf'
        if hasattr(self.getRoot(), ztinymce_conf_id):
            return getattr(self.getRoot(), ztinymce_conf_id)
        return None
            


    def getCookiekey(self, which):
        """ return the cookiekey constants depending on key """
        which_orig = which
        match_decorate = lambda x: x.lower().strip().replace('_','').replace('-','')
        which = match_decorate(which)
        
        keys = {'name': NAME_COOKIEKEY,
                'fullname': NAME_COOKIEKEY,
                'email': EMAIL_COOKIEKEY,
                'displayformat': DISPLAY_FORMAT_COOKIEKEY,
                'sortorder': SORTORDER_COOKIEKEY,
                'sortorderreverse': SORTORDER_REVERSE_COOKIEKEY,
                'draftissueids': DRAFT_ISSUE_IDS_COOKIEKEY,
                'draftthreadids': DRAFT_THREAD_IDS_COOKIEKEY,
                'autologin': AUTOLOGIN_COOKIEKEY,
                'useaccesskeys': USE_ACCESSKEYS_COOKIEKEY,
                'saved-filters': SAVED_FILTERS_COOKIEKEY,
                'remember_savedfilter_persistently': REMEMBER_SAVEDFILTER_PERSISTENTLY_COOKIEKEY,
                'draft_followup_ids': DRAFT_THREAD_IDS_COOKIEKEY,
                'show_nextactions': SHOW_NEXTACTIONS_COOKIEKEY,
        }
        for k, v in keys.items():
            if match_decorate(k) == which:
                return v
        
        if self.doDebug():
            debug("Unable to find cookiekey for %s" % which_orig, steps=4)

        
    def __before_publishing_traverse__(self, object, request=None):
        """ sort things out before publising object """
        self.get_environ()

    
    def get_environ(self):
        """ Populate REQUEST as appropriate """
        request = self.REQUEST
        stack = request['TraversalRequestNameStack']
        popped = []

        _special = 'REQUEST'
        # things to pop out
        queryitems = ({'key':'start', 'mkey':'start', 'type':'int'},
                      {'key':'sortorder', 'mkey':'sortorder', 'type':'string'},
                      {'key':'reverse', 'mkey':'reverse', 'type':'boolean'},
                      {'key':'show', 'mkey':'show', 'type':'string'},
                      {'key':'report', 'mkey':'report', 'type':'string'},
                      
                      )

        
        splitter = '-'
        if stack:
            stack_copy = stack[:]
            
            found_item = 1
            for each in range(len(stack_copy)):
                found_item = 0
                stack_item = stack_copy[each]
                for each in queryitems:
                    key, value = each['key'], each.get('mkey')

                    if value is None and stack_item==key:
                        # this is a valueless item
                        found_item = 1
                        request.set(key, 1)
                    elif stack_item.startswith("%s%s"%(key,splitter)) \
                         and value==_special:
                        found_item = 1
                        first_key = stack_item.replace("%s%s"%(key,splitter),'')
                        
                        try:
                            key, value = first_key.split(splitter,1)
                            value = int(value)
                            request.set(key, value)
                        except ValueError:
                            try:
                                key, value = first_key.split(splitter,1)
                                request.set(key, value)
                            except:
                                pass
                            
                    elif stack_item.startswith("%s%s"%(key,splitter)):
                        found_item = 1
                        replace_what = "%s%s"%(key,splitter)
                        if each['type']=='boolean':
                            key = stack_item.replace(replace_what,'')
                            key = Utils.niceboolean(key)
                        elif each['type']=='int':
                            key = int(stack_item.replace(replace_what,''))
                        else:
                            key = stack_item.replace(replace_what,'')
                        
                        request.set(value, key)

                if found_item:
                    stack.remove(stack_item)
                    popped.append(stack_item)

            request.set('popped',popped)



    ## General for file attachments to issues

    def getFileattachmentInput(self, index, initsize=40):
        """ return either a file input field or a keep option """
        request = self.REQUEST

        input_field = '<input size="%s" name="fileattachment:list" '
        input_field += 'type="file" />'
        icon_html = '<img hspace="2" src="%s" alt="File" '\
                    'title="File size %s" border="0" />'
        if request.has_key(TEMPFOLDER_REQUEST_KEY):
            upload_folder = request[TEMPFOLDER_REQUEST_KEY]
            # Maybe the actual folder doesn't exist any more
            tempfolder = self._getTempFolder()
            if upload_folder is None or not hasattr(tempfolder, upload_folder):
                return input_field%initsize
            files = tempfolder[upload_folder].objectValues('File')
            try:
                file = files[index]
                file_src = self.getFileIconpath(file.getId())
                file_size = self.ShowFilesize(file.getSize())
                icon = icon_html%(file_src, file_size)
                
                confirm_title = _("Tick if you want to keep this file attachment")
                confirm = '<input type="checkbox" checked="checked" '
                confirm += 'name="confirm_fileattachment:list" '
                confirm += 'value="%s" title="%s" />'%(file.getId(),
                                                     confirm_title)

                icon = '%s<a href="%s" title="File size %s">%s%s (%s)</a>'%\
                       (confirm, file.absolute_url(), file_size, 
                        icon, file.getId(), file_size)
                return icon
                
            except:
                return input_field % initsize
        else:
            return input_field % initsize
    
    def _uploadTempFiles(self):
        """ Attempt to upload fileattachments to temp-folder and stick
        some information in the REQUEST """
        request = self.REQUEST
        temp_folder_id = None
        rkey = TEMPFOLDER_REQUEST_KEY

        # first, delete all unconfirmed files
        self._removeUnConfirmedFiles()
        
        if request.get(rkey, None) not in [None,'']:
            temp_folder_id = request.get(rkey)
        
        if request.has_key('fileattachment'):
            # fileattachment is a list, deal with each item
            for file in request.get('fileattachment'):
                if self._isFile(file):
                    if temp_folder_id is None:
                        temp_folder_id = self._generateTempFolder()

                    temp_folder = self._getTempFolder()[temp_folder_id]
                    filename = getattr(file, 'filename')
                    id=filename[max(filename.rfind('/'),
                                    filename.rfind('\\'),
                                    filename.rfind(':'),
                                    )+1:]
                    if id.startswith('_'):
                        id=id[1:]
                    id = Utils.badIdFilter(id)
                    temp_folder.manage_addFile(id, file=file)
                    fileobject = getattr(temp_folder, id)
                    
                    if self._canCreateThumbnail(fileobject):
                        try:
                            self._createThumbnail(fileobject)
                        except IOError:
                            # we failed to create thumbnail not good. 
                            # A log message will already have been 
                            # sent.
                            pass
                        
            # This tests whether any files were uploaded
            if temp_folder_id is not None:
                request.set(rkey, temp_folder_id)

        return "anything"
    
    security.declarePublic('_removeUnConfirmedFiles')
    def _removeUnConfirmedFiles(self):
        """ if we have a tempfolder with files that don't have a matching 
        confirm, then delete them """
        request = self.REQUEST
        rkey = TEMPFOLDER_REQUEST_KEY
        if request.get(rkey, None) not in [None,'']:
            temp_folder = self._getTempFolder()[request.get(rkey)]
            confirms = self._getConfirmFileattachments()
            un_upload_ids = []
            for fileid in temp_folder.objectIds('File'):
                if not fileid in confirms:
                    un_upload_ids.append(fileid)
                
            self._deleteTempFiles(temp_folder, un_upload_ids)
            
            # Anything left now?
            if len(temp_folder.objectIds('File'))==0:
                request.set(rkey, None)
                self._getTempFolder().manage_delObjects([temp_folder.getId()])
            
            
    def _deleteTempFiles(self, source, ids):
        """ simply delete some files """
        source.manage_delObjects(ids)
        

    def _isFile(self, file):
        """ Check if Publisher file is a real file """
        if hasattr(file, 'filename'):
            if getattr(file, 'filename').strip() != '':
                # read 1 byte
                if file.read(1) == "":
                    m = _("Filename provided (%s) but not file content")
                    m = m%getattr(file, 'filename')
                    raise "NotAFile", m
                else:
                    file.seek(0) #rewind file
                    return True
            else:
                return False
        else:
            return False

        
    security.declarePublic('_generateTempFolder')
    def _generateTempFolder(self):
        """ Create a folder in temp_folder with randomish id and return
        its id """
        root = self._getTempFolder()
        timestamp = str(int(self.ZopeTime()))
        randstr = self.getRandomString(length=3, numbersonly=1)
        rand_id_start = "uploadtmp-it-%s"%timestamp
        rand_id = "%s-%s"%(rand_id_start, randstr)
        while hasattr(root, rand_id):
            new_rand_str = self.getRandomString(length=3, numbersonly=1)
            rand_id = "%s-%s"%(rand_id_start, new_rand_str)

        try:
            root.manage_addFolder(rand_id)
            tempfolder = getattr(root, rand_id)
        except "Unauthorized":
            LOG(self.__class__, PROBLEM, 
                "Could not create temporary folder")
            
        return rand_id

    def getFileattachmentContainer(self, only_temporary=0):
        """ if TEMPFOLDER_REQUEST_KEY is set in REQUEST return folder
        object, otherwise return self. """
        request = self.REQUEST
        rkey = TEMPFOLDER_REQUEST_KEY
        if request.has_key(rkey) and request.get(rkey) is not None:
            return getattr(self._getTempFolder(), request[rkey])
        elif only_temporary:
            return None
        else:
            return self

    def showFileattachments(self, container=None, only_temporary=0):
        """ return HTML with the file attachments """

        if container is None and only_temporary:
            container = self.getFileattachmentContainer(only_temporary=1)
            if not container:
                return ''
            
        elif container is None:
            # find then manually
            
            if self.meta_type == ISSUE_METATYPE:
                container = self

            if not container:
                return ''

        files = container.objectValues('File')

        if not files:
            return ''

        html = []
        for file in files:
            url = file.absolute_url()
            url = self.relative_url(url)
            size = self.ShowFilesize(file.getSize())
            alt = "File size: %s"%size
            href = '<a href="%s" title="%s">'%(url, alt)
            _html = '%s<img src="%s" alt="%s" title="%s" border="0" '
            _html += 'class="fileatt" />'
            thumbid = 'thumbnail--%s'%file.getId()
            if hasattr(container, thumbid) and \
               getattr(container, thumbid).meta_type == 'Image':
                src = getattr(container, thumbid).absolute_url_path()
            else:
                src = self.getFileIconpath(file.getId())
            _html = _html%(href, src, alt, alt)

            _html += '</a>\n'

            file_id = file.getId()
            if len(file_id) > 50:
                file_id = file_id[:25]+'...'+file_id[-25:]
                
            _html += '%s%s</a>'%(href, self.HighlightQ(file_id, highlight_digits=True))
            
            _html += ' <span class="shade"> (%s)</span>\n'%size

            html.append(_html)

        return '<br clear="left" />\n'.join(html)+'<br clear="left"/>'
    
        
    def nullifyTempfolderREQUEST(self):
        """ if request has tempfolder, make it None """
        request = self.REQUEST
        rkey = TEMPFOLDER_REQUEST_KEY
        if request.has_key(rkey):
            request.set(rkey, None)    

    ## Using ACL objects
    
    def getACLCookieNames(self):
        """ return acl_cookienames dict property """
        return getattr(self, 'acl_cookienames', {})

    def getACLCookieEmails(self):
        """ return acl_cookieemails dict property """
        return getattr(self, 'acl_cookieemails', {})

    def getACLCookieDisplayformats(self):
        """ return acl_cookiedisplayformats dict property """
        return getattr(self, 'acl_cookiedisplayformats', {})
    
    def setACLCookieName(self, fromname):
        """ append to acl_cookienames """
        acluser = self._getACLUserName()
        if acluser:
            prev = self.getACLCookieNames()
            prev[acluser] = fromname
            self.acl_cookienames = prev
            
    def setACLCookieEmail(self, email):
        """ append to acl_cookieemails """
        acluser = self._getACLUserName()
        if acluser:
            prev = self.getACLCookieEmails()
            prev[acluser] = email
            self.acl_cookieemails = prev
            
    def setACLCookieDisplayformat(self, displayformat):
        """ append to acl_cookiedisplayformats """
        assert displayformat in self.display_formats, \
        "Invalid displayformat value %r" % displayformat
        acluser = self._getACLUserName()
        if acluser:
            prev = self.getACLCookieDisplayformats()
            prev[acluser] = displayformat
            self.acl_cookiedisplayformats = prev

    def _getACLUserName(self):
        """ return ACL username or None """
        usr = getSecurityManager().getUser().getUserName()
        if usr.lower().replace(' ','')=='anonymoususer':
            return None
        else:
            return usr

    ## Adding an Issue

    def fixSectionsSubmission(self):
        """ here's a special script that converts 'section' into
        ['section'] if present and 'sections' if not present. """
        request = self.REQUEST

        if not request.has_key('sections') and request.get('section'):
            request.set('sections', [request.get('section')])
            return True
        return False


    security.declareProtected(AddIssuesPermission, 'SubmitIssue')
    def SubmitIssue(self, REQUEST):
        """ This is the method to create an Issue Tracker Issue. It
        relies only on the REQUEST object.
        1) Check data
        2) Try to create issue
            2a) If success, RESPONSE.redirect to issue plus Thank you message
            2b) If failure, print failed data and urge to submit again
        """

        request = self.REQUEST
        SubmitError = {}
        
        has_cookie = self.has_cookie
        get_cookie = self.get_cookie
        set_cookie = self.set_cookie

      
        #
        # Tune the data a bit
        #

        # strip whitespace
        for property in ['title','fromname','email',
                         'url2issue','display_format']:
            request[property] = request.get(property,'').strip()
        # Special treatment needed in case STX is used upon display
        request['description'] = request.get('description','').strip()+' '

        email_cookiekey = self.getCookiekey('email')
        name_cookiekey = self.getCookiekey('name')
        display_format_cookiekey = self.getCookiekey('display_format')
        # use cookie if not else specified

        # assume that it is not a ACL user who adds the issue
        acl_adder = None
        issueuser = self.getIssueUser()
        cmfuser = self.getCMFUser()
        zopeuser = self.getZopeUser()
        if issueuser:
            acl_adder = issueuser.getIssueUserIdentifierString()
            if request.get('display_format'):
                if request.get('display_format') in self.display_formats:
                    issueuser.setDisplayFormat(request.get('display_format'))
                
        elif zopeuser:
            path = '/'.join(zopeuser.getPhysicalPath())
            name = zopeuser.getUserName()
            acl_adder = ','.join([path, name])

        _invalid_name_chars = re.compile('|'.join([re.escape(x) for x in list('<>;\\')]))

        if issueuser and issueuser.getEmail():
            request['email'] = issueuser.getEmail()
        elif cmfuser and cmfuser.getProperty('email'):
            request['email'] = cmfuser.getProperty('email')
        elif not request.get('email','') and get_cookie(email_cookiekey):
            request['email'] = get_cookie(email_cookiekey)
        elif not request.get('email','') and self.getSavedUser('email'):
            request['email'] = self.getSavedUser('email')
            
        if issueuser and issueuser.getFullname():
            request['fromname'] = issueuser.getFullname()
        elif cmfuser and cmfuser.getProperty('fullname'):
            request['fromname'] = cmfuser.getProperty('fullname')
        elif not request.get('fromname','') and get_cookie(name_cookiekey):
            request['fromname'] = get_cookie(name_cookiekey)
        elif not request.get('fromname','') and self.getSavedUser('fromname'):
            request['fromname'] = self.getSavedUser('fromname')
        
            
        # this prevents dodgy XSS attempts
        if _invalid_name_chars.findall(request['fromname']):
            SubmitError['fromname'] = u'Contains not allowed characters'
        if _invalid_name_chars.findall(request['email']):
            SubmitError['email'] = u'Contains not allowed characters'
        
            
        if not request.get('display_format','').strip():
            request['display_format'] = self.getSavedTextFormat()

        newsection = None
        if request.get('newsection'):
            ns = request.get('newsection').strip()
            if ns and ns != 'New section...':
                if ns in self.sections_options:
                    request.set('newsection','')
                else:
                    newsection = ns
        
        # append the default sections if not specified
        if len(request.get('sections',[])) == 0 and not newsection:
            request['sections'] = self.defaultsections
            
        #
        # Check data
        #

        if not request.get('title','').strip():
            SubmitError['title'] = _("Empty")
        elif self.DisallowDuplicateIssueSubjects():
            this_subject = ss(request.get('title').strip())
            for issue in self.getIssueObjects():
                if ss(issue.getTitle()) == this_subject:
                    link = '<a href="%s">#%s</a>' % (issue.absolute_url_path(), issue.getId())
                    SubmitError['title'] = _("Issue subject already used in %s" % link)
                    break
            
        description_purified = Utils.SimpleTextPurifier(request.get('description',''))
        if not description_purified:
            SubmitError['description'] = _("Empty")
        elif self.containsSpamKeywords(request.get('description',''), verbose=True):
            SubmitError['description'] = _("Contains spam keywords")

        valid_emailaddress = 1
        # to prevent problems with sending mail
        if not self.ValidEmailAddress(request.get('email','')):
            valid_emailaddress = 0

        # Check issue assignment
        assignee = None
        if request.get('assignee'):

            ok_assignees = [x['identifier'] for x in self.getAllIssueUsers()]
            
            if not self.UseIssueAssignment():
                SubmitError['assignee'] = _("Issue assignment disabled")
            elif request.get('assignee') in self.getIssueAssignmentBlacklist():
                SubmitError['assignee'] = _("Invalid assignee")
            elif request.get('assignee') in ok_assignees:
                assignee = request.get('assignee')


        # Check that all attempts of file attachments really are files
        fake_fileattachments = self._getFakeFileattachments()
        if fake_fileattachments:
            m = _("Filename entered but no actual file content")
            SubmitError['fileattachment'] = m
            
        # Check the spambot prevention
        if self.useSpambotPrevention():
            captcha_numbers = request.get('captcha_numbers','').strip()
            captchas_used = request.get('captchas')
            if isinstance(captchas_used, basestring):
                captchas_used = [captchas_used]
                
            if not captcha_numbers:
                m = _("Enter the numbers shown to that you are not a spambot")
                SubmitError['captcha_numbers'] = m
            else:
                errors = None
                for i, nr in enumerate(captcha_numbers):
                    try:
                        if int(nr) != int(self.captcha_numbers_map.get(captchas_used[i])):
                            errors = True
                            break
                    except ValueError:
                        errors = True
                        break
                
                    
                if errors:
                    # use this oppurtunity to clean up what they tried to enter
                    captcha_numbers = request.get('captcha_numbers','').strip()
                    captcha_numbers = re.sub('[^\d]','', captcha_numbers).strip()
                    request.set('captcha_numbers', captcha_numbers)
                    
                    m = _("Incorrect numbers matching")
                    SubmitError['captcha_numbers'] = m
                else:
                    self._rememberProvenNotSpambot()
            
            

        if SubmitError:
            if request.get('previewissue'):
                request.set('previewissue', False)
            if request.get('addform','')=='quick':
                page = self.QuickAddIssue
            else:
                page = self.AddIssue
            return page(REQUEST, SubmitError=SubmitError)

        
        #
        # Let's submit the issue!
        #

        # if these are valid, save them
        if request.get('fromname') and not issueuser:
            set_cookie(self.getCookiekey('name'), request.get('fromname'))
            self.setACLCookieName(request.get('fromname'))

        if valid_emailaddress and not issueuser:
            set_cookie(self.getCookiekey('email'), request.get('email'))
            self.setACLCookieEmail(request.get('email'))
                
        if request.get('display_format') in self.display_formats \
               and not issueuser:
            if request.get('display_format') in self.display_formats:
                set_cookie(self.getCookiekey('display_format'),
                           request.get('display_format'))
                self.setACLCookieDisplayformat(request.get('display_format'))
            
        
        # filter out empty item from sections
        sections_newlist = request.get('sections', [])
        if not Utils.same_type(sections_newlist, []):
            sections_newlist = [sections_newlist]
            
        sections_newlist = [x.strip() for x in sections_newlist]
        while '' in sections_newlist:
            sections_newlist.remove('')
            
        if newsection and self.CanAddNewSections():
            sections_newlist.insert(0, newsection)
            
            _options = self.sections_options
            _options.append(newsection)
            self.sections_options = _options

        # add all the properties
        _rfg = request.form.get
        _rg = request.get
        title           = unicodify(_rg('title'))
        fromname        = unicodify(_rg('fromname'))
        email           = _rg('email')
        url2issue       = _rg('url2issue')
        type            = _rg('type')
        urgency         = _rg('urgency')
        description     = unicodify(_rg('description'))
        display_format  = _rg('display_format')
        confidential    = int(_rg('confidential',0))
        hide_me         = int(_rg('hide_me',0))
        status          = _rfg('status', self.getStatuses()[0])
        sections        = sections_newlist

        # Let's massage up the description a bit
        description = description.strip()
        if display_format == 'html':
            while description.endswith('<p>&nbsp;</p>'):
                description = description[:-len('<p>&nbsp;</p>')].strip()
            while description.startswith('<p>&nbsp;</p>'):
                description = description[len('<p>&nbsp;</p>'):].strip()
        
        #
        # before we submit the issue, let's just check that it
        # hasn't been submitted before. This can happen if people 
        # accidently press the Save Issue button twice.
        #
        _existing_issue = self._check4Duplicate(title, description,
                                      sections, type, urgency)
        
        if _existing_issue:
            url = _existing_issue.absolute_url()
            url += '?NewIssue=Submitted'
            
            if _rfg('draft_issue_id'):
                self._dropDraftIssue(_rfg('draft_issue_id'))
                
            return self.REQUEST.RESPONSE.redirect(url)
        

        prefix = self.issueprefix
        genid = self.generateID(self.randomid_length, prefix,
                  incontainer=self._getIssueContainer())
        
        # Do the actual object adding
        cIO = self.createIssueObject
        
        issue = cIO(genid, request.title, status, type, urgency,
                    sections, fromname, email, url2issue,
                    confidential, hide_me, description,
                    display_format, acl_adder=acl_adder)
                    

        # catalog it
        issue.index_object()
        
        # remember it
        #self.RememberAddedIssue(genid)
        self.RememberRecentIssue(genid, 'added')

        
        if _rfg('draft_issue_id'):
            self._dropDraftIssue(_rfg('draft_issue_id'))
            
        if self.SaveDrafts():
            # (see bug report on http://real.issuetrackerproduct.com/0126)
            self._dropMatchingDraftIssues(issue)

            
        # Also upload the fileattachments
        self._moveTempfiles(issue)

        # upload new file attachments
        self._uploadFileattachments(issue)

        # create assignment object
        if assignee is not None:
            _send_email = False
            if _rfg('notify-assignee'):
                _send_email = True
            issue.createAssignment(assignee,
                                   send_email=_send_email)

        # tell the people who wants to know
        try:
            self.sendAlwaysNotify(issue, email=email, assignee=assignee)
        except:
            try:
                err_log = self.error_log
                err_log.raising(sys.exc_info())
            except:
                pass                
            typ, val, tb = sys.exc_info()
            _classname = self.__class__.__name__
            _methodname = inspect.stack()[1][3]
            LOG("IssueTrackerProduct.SubmitIssue()", ERROR,
                'Could not send always-notify emails',
                error=sys.exc_info())            
            

        # tune some exisiting data
        if not newsection:
            # when adding a new section, don't do this
            self._moveUpSections(sections)

        # Where to next?
        redirect_url = '%s?NewIssue=Submitted'%(issue.absolute_url())
        request.RESPONSE.redirect(redirect_url)



    def _check4Duplicate(self, title, description, sections, 
                         type, urgency, email_message_id=None
                         ):
        """ check if there is an exact replica of this issue """
        for issue in self.getIssueObjects():
            
            # most basic test, the title
            if unicodify(issue.title) == title:
                
                # potentially match email 'Message-Id'
                if email_message_id and issue.getEmailMessageId():
                    if ss(email_message_id)==ss(issue.getEmailMessageId()):
                        return issue
                
                # match description, sections, type and urgencies
                if unicodify(issue.description) == description and \
                   issue.sections == sections and \
                   issue.type == type and \
                   issue.urgency == urgency:
                    return issue
                
        return None
        
    
                             
    def createIssueObject(self, id, title, status, type, urgency, sections,
                          fromname, email, url2issue, confidential, hide_me,
                          description, display_format, issuedate=None, index=0,
                          acl_adder=None,
                          submission_type='',
                          email_message_id=None):
        """ wrap the the self._createIssueObject() method """
        if id is None or id=='':
            # create id
            prefix = self.issueprefix
            randlength = self.randomid_length
            id = self.generateID(randlength, prefix, incontainer=self._getIssueContainer())
            
        if title.strip() == '':
            raise "NoSubject", "Issue has no subject line"
        
        if status.lower() not in [x.lower() for x in self.getStatuses()]:
            raise "NoStatus", "Unrecognized issue status %r" % status
        
        if type not in self.types:
            raise "NoType", "Unrecognized issue type"
        
        if urgency not in self.urgencies:
            raise "NoUrgency", "Unrecognized issue urgency"
        
        if not Utils.same_type(sections, []):
            raise "NotList", "Sections is not a list"

        if confidential not in [1,0]:
            raise "NotBoolean", "Confidential value is not boolean (1 or 0)"
        
        if hide_me not in [1,0]:
            raise "NotBoolean", "Hide_me value is not boolean (1 or 0)"
        
        if display_format not in self.display_formats:
            raise "InvalidDisplayFormat", "Invalid display format %r" % display_format
        
        if issuedate is None or issuedate =='':
            issuedate = DateTime()
            
        if fromname is None:
            fromname = ""
            
        if email is None:
            email = ""

        if acl_adder:
            userfolderpath, name = acl_adder.split(',')
            try:
                object = self.unrestrictedTraverse(userfolderpath)
                assert name in object.user_names()
            except:
                raise "NoACLAdder", "No ACL user object found"
            
        # Fine, submit it
        create_method = self._createIssueObject
        return create_method(id, title, status, type, urgency,
                             sections, fromname, email, url2issue,
                             confidential, hide_me, description,
                             display_format, issuedate, index=index,
                             acl_adder=acl_adder,
                             submission_type=submission_type,
                             email_message_id=email_message_id)
                             
    def _createIssueObject(self, id, title, status, type, urgency, sections,
                           fromname, email, url2issue, confidential, hide_me,
                           description, display_format, issuedate, index=0,
                           acl_adder=None, submission_type='',
                           email_message_id=None):
        """ crudely create issue object. No checking """
        issueinst = IssueTrackerIssue(id, title, status, type, urgency,
                                      sections, fromname, email, url2issue,
                                      confidential, hide_me, description,
                                      display_format, issuedate=issuedate,
                                      acl_adder=acl_adder,
                                      submission_type=submission_type)

        # not here
        where = self._getIssueContainer()
        
        where._setObject(id, issueinst)
        issue = getattr(where, id)
        
        if email_message_id:
            issue._setEmailMessageId(email_message_id)

        if index:
            # catalog it
            issue.index_object()
            
        return issue    



    def _getFakeFileattachments(self):
        """ upload all new file attachments """
        request = self.REQUEST

        fakes = []

        for file in request.get('fileattachment', []):
            try:
                ok = self._isFile(file)
            except "NotAFile":
                # if this exception is raised, it means that the user
                # didn't press the "Browse..." button but rather wrote
                # something for the file name.
                filename = getattr(file, 'filename')
                id=filename[max(filename.rfind('/'),
                                filename.rfind('\\'),
                                filename.rfind(':'),
                                )+1:]

                fakes.append(id)

        return fakes
    
    
    def useSpambotPrevention(self):
        """ return true if spambot prevention should be used """
        if self.ShowSpambotPrevention():
            if self.getIssueUser() or self.getZopeUser() or self.getCMFUser():
                return False
            skey = ALREADY_NOT_SPAMBOT_SESSION_KEY
            if self.get_session(skey, False):
                return False
            
            return True
        
        return False
                
            
    def _rememberProvenNotSpambot(self):
        """ set a session variable on this user that proves that she's not a 
        spambot. 
        """
        # XXX Perhaps this should be a cookie??
        skey = ALREADY_NOT_SPAMBOT_SESSION_KEY
        self.set_session(skey, True)

                

    def generateID(self, length, prefix='', meta_type=ISSUE_METATYPE,
                   incontainer=None, use_stored_counter=1):
        """ see if there is an internal counter already,
        otherwise call up the old generateID() function
        that is now called _do_generateID(). """
        if incontainer is None:
            incontainer = self

        counter_key = '_nextid_%s' % ss(incontainer.meta_type).replace(' ','')
        if use_stored_counter and incontainer.__dict__.has_key(counter_key):
            
            nextid_nr = incontainer.__dict__.get(counter_key)
            incontainer.__dict__[counter_key] = nextid_nr + 1
            
            increment = nextid_nr
            return self._do_generateID(incontainer, length, prefix,
                                       meta_type, increment=increment)
        else:
            nextid_str = self._do_generateID(incontainer, length,
                                             prefix, meta_type)
                                             
            # in python2.1 you can't replace with an empty string.
            # thanks Thomas Kruger
            if prefix:
                nextid_nr_str = nextid_str.replace(prefix,'')
            else:
                nextid_nr_str = nextid_str
            nextid_nr = int(nextid_nr_str)
            
            incontainer.__dict__[counter_key] = nextid_nr
            return nextid_str
            
    def _do_generateID(self, incontainer, length, prefix='',
                       meta_type=ISSUE_METATYPE, increment=None,
                       ):
        """ generate IDs for different objects """
        if increment is None:
            idnr = len(incontainer.objectIds(meta_type))+1
            increment = idnr + 1
        else:
            idnr = increment
            increment = increment +1
        id='%s%s'%(prefix, string.zfill(str(idnr), length))
        base= getattr(incontainer,'aq_base',incontainer)
        if hasattr(base, id):
            # ah! Id already exists, try again
            return self._do_generateID(incontainer, length, prefix, meta_type, 
                                       increment=increment)
        else:
            return id


    def _moveUpSections(self, sections):
        """ when an issue has been created, prioritize it's sections globally.
        """
        if type(self.sections_options)==type(()): 
            # fix for badly defined sections options.
            # this can go away in the future.
            self.sections_options = list(self.sections_options)
        
        sections_options = self.sections_options
            
        Utils.moveUpListelement(sections, sections_options)
        self.sections_options = sections_options
        

    def _canCreateThumbnail(self, fileobject):
        """ return True if recognized as a image that we can
        resize with PIL """
        if not Image:
            return False
        
        try:
            if fileobject.getSize() < 100:
                return False
        except:
            return False
        
        ct = fileobject.content_type
        if ct in ('image/pjpeg','image/jpeg','image/gif','image/png',
                  'image/x-png'):
            return True
        return False


    def _createThumbnail(self, fileobject):
        """ create a thumbnail of the fileobject and name it
        'thumbnail--'+fileobject.getId() """
        oriFile = cStringIO.StringIO(str(fileobject.data))

        try:
            image = Image.open(oriFile)
        except IOError:
            m = "PIL.Image could not read %s bytes imagefile"
            m = m%len(oriFile.getvalue())
            LOG(self.__class__.__name__, WARNING, m, error=sys.exc_info())
            raise
        except:
            # all other
            typ, val, tb = sys.exc_info()
            m = "Unable to create Image instance with open()"
            LOG(self.__class__.__name__, ERROR, m, error=sys.exc_info())
            return 

        image.thumbnail((45, 45))
        image_type = image.format

        thumFile = cStringIO.StringIO()
        image.save(thumFile, image_type)
        thumFile.seek(0)

        container = fileobject.aq_parent
        thumbid = 'thumbnail--%s'%fileobject.getId()
        container.manage_addImage(thumbid, thumFile.getvalue())

        # del!!
        
    
    def _uploadFileattachments(self, destination):
        """ upload all new file attachments """
        request = self.REQUEST

        for file in request.get('fileattachment', []):
            if self._isFile(file):
                filename = getattr(file, 'filename')
                id=filename[max(filename.rfind('/'),
                                filename.rfind('\\'),
                                filename.rfind(':'),
                                )+1:]
                if id.startswith('_'):
                    id=id[1:]
                id = Utils.badIdFilter(id)
                try:
                    destination.manage_addFile(id, file)
                    fileobject = getattr(destination, id)
                    if self._canCreateThumbnail(fileobject):
                        try:
                            self._createThumbnail(fileobject)
                        except IOError:
                            # _createThumbnail() will already have logged 
                            # this IOError
                            pass
                except:
                    LOG(self.__class__, PROBLEM, "Could not upload file "\
                        "id=%s"%id)


    security.declarePublic('_moveTempfiles')
    def _moveTempfiles(self, destination):
        """ move from temp folder to destination """
        request = self.REQUEST
        rkey = TEMPFOLDER_REQUEST_KEY
        if request.has_key(rkey):
            files_copied = []
            upload_folder_id = request.get(rkey)
            if not hasattr(self._getTempFolder(), upload_folder_id):
                return             
            upload_folder = self._getTempFolder()[upload_folder_id]
            confirms = self._getConfirmFileattachments()

            cut_ids = []
            for file in upload_folder.objectValues(['File','Image']):
                if file.getId().replace('thumbnail--','') in confirms:
                    cut_ids.append(file.getId())
                    upload_id = file.getId()
                    upload_id = Utils.badIdFilter(upload_id)
                    if file.meta_type == 'Image':
                        destination.manage_addImage(upload_id, file.data)
                    else:
                        destination.manage_addFile(upload_id, file.data)

            self._getTempFolder().manage_delObjects([upload_folder_id])
            
            
    def _getConfirmFileattachments(self):
        """ return the 'confirm_fileattachments' request list """
        confirms = self.REQUEST.get('confirm_fileattachment', [])
        if type(confirms) != type([]):
            confirms = [confirms]
        return confirms

                    
    def sendAlwaysNotify(self, issue, email=None, assignee=None):
        """ send out emails to those who always notify """
        ## Check that the sitemaster_email has been set
        #if self.sitemaster_email == DEFAULT_SITEMASTER_EMAIL:
        #    m = "Sitemaster email not changed from default. Email not sent."
        #    LOG(self.__class__.__name__, ERROR, m)
        #    return
        
        
        assignee_email = None
        if assignee:
            if Utils.same_type(assignee, 's'):
                acl_path, username = assignee.split(',')
                try:
                    userfolder = self.unrestrictedTraverse(acl_path)
                    if userfolder.data.has_key(username):
                        assignee_user = userfolder.data.get(username)
                        assignee_email = assignee_user.getEmail()
                except:
                    pass
                
        
        always_emailstring = ', '.join(self.getAlwaysNotify())
        tosend = self._alwaysNotifyMessage(issue, always_emailstring)
        msg, to, fr, subject = tosend
        
        issueid_header = issue.getGlobalIssueId()

        if to is not None:
            email = ss(str(email))
            for to_each in self.preParseEmailString(to, aslist=1):
                if ss(to_each) == email:
                    continue
                elif assignee_email and ss(to_each) == assignee_email:
                    continue
                self.sendEmail(msg, to_each, fr, subject, swallowerrors=True,
                               headers={EMAIL_ISSUEID_HEADER: issueid_header})


    def _acceptEmailsToSiteMaster(self):
        """ return true if there is a POP3 account where one of the 
        accepting emails is the same as that of sitemaster_email 
        """
        ss_sitemaster_email = ss(self.getSitemasterEmail())
        for account in self.getPOP3Accounts():
            for ae in account.getAcceptingEmails():
                if ss(ae.getEmailAddress()) == ss_sitemaster_email:
                    return True
        return False
            

    def _alwaysNotifyMessage(self, issue, emailstring):
        """ return the message, to, from and subject for a message to
        those who always get emails about new issues. """
        br = "\r\n"
        root = self.getRoot()
        
        fromname = issue.getFromname()
        fromemail = issue.getEmail()
        
        _fromemail_valid = Utils.ValidEmailAddress(fromemail)

        if self._acceptEmailsToSiteMaster():
            fr = self.getSitemasterFromField()
        else:
            if not fromname and fromemail and _fromemail_valid:
                fr = fromemail
            elif fromname and fromemail and _fromemail_valid:
                fr = "%s <%s>"%(fromname, fromemail)
            else:
                fr = self.getSitemasterFromField()
            
        if Utils.same_type(issue, 's'):
            issue = getattr(self, issue)

        _issuetitle = issue.getTitle()
        
        to = self.preParseEmailString(emailstring)
        
        _r_dict = {'root_title':root.getTitle()}
        if self.ShowIdWithTitle():
            _r_dict['issue_id'] = issue.getId()
            subject = _("%(root_title)s: new issue: #%(issue_id)s ") % _r_dict
        else:
            subject = _("%(root_title)s: new issue: ") % _r_dict
            
        subject += _issuetitle

        if fromname is None:
            msg = _('An issue has been added to your attention at '\
                    '%(root_title)s with the following title:') % _r_dict + br
        else:
            
            if fromemail:
                _from = "%s (%s)"%(fromname, fromemail)
            else:
                _from = fromname
            _r_dict['from_name'] = _from
            msg = _('%(from_name)s has entered an issue in %(root_title)s and '\
                    'wanted you to know about it, with the following title:') % _r_dict + br

        msg += _issuetitle + br * 2
        msg += _("The issue can be found at") + br
        msg += self.ActionURL(url=issue.absolute_url()) + br * 2
        
        if self.IncludeDescriptionInNotifications():
            # if this is true, enter the full text of the added issue
            # right here. 
            if fromname:
                msg += _("%(fromname)s wrote:") % {'fromname':fromname} + br
            msg += Utils.LineIndent(issue.getDescriptionPure(), ' '*3, 67)
            msg += br * 2

        msg += br
        # Footer
        signature = self.showSignature()
        if signature:
            msg += "--" + br +signature

        return msg, to, fr, subject
        

    ## Misc methods

    def getUrgencyCSSSelector(self, urgency=None):
        """ compare this with the parents option to return a CSS selector
        like 'ur-3' between [0-4] where 1 is default """
        selector = 'ur-%s'
        if urgency is None:
            # self is an issue
            urgency = self.urgency
        
        if urgency in self.urgencies:
            index = self.urgencies.index(urgency)
            if index not in [0,1,2,3,4]:
                index = 1
        else:
            index = 1

        return selector%index
    
    def getIssueTrackerVersion(self):
        """ return global variable """
        return __version__
    
    security.declarePublic('About')
    def About(self):
        """ Show some info about the product """
        
        osj = os.path.join
        f = open(osj(package_home(globals()), 'CHANGES.txt'), "r")
        changelog = f.read()
        f.close()
        changelog = self.ShowDescription(changelog.strip()+' ',
                                         'structuredtext')
        version_number_re = re.compile(r'(<li>(\d.\d.\d\w))|(<li>(\d.\d.\d))')
        for version_number_html in version_number_re.findall(changelog):
            if version_number_html[2]:
                whole, number = version_number_html[2], version_number_html[3]
            else:
                whole, number = version_number_html[0], version_number_html[1]

            better = whole.replace(number, '<b>%s</b>'%number)
            changelog = changelog.replace(whole, better)
        
        version = self.getIssueTrackerVersion()

        f = 'zpt/About'
        name='About'
        return CTP(f, globals(), optimize=OPTIMIZE and 'xhtml',
                   __name__=name).__of__(self)(changelog=changelog,
                                               version=version)

                                               
    security.declareProtected('View', 'ListIssues_CSV')
            
    def ListIssues_CSV(self, batchsize=None, withheaders=True, 
                       REQUEST=None):
        """ return a CSV file with the issues you're currently
        looking at. """
        return self.CSVExport(batchsize=batchsize, 
                              withheaders=withheaders,
                              issue_export=False,
                              filename='ListIssues.csv',
                              REQUEST=REQUEST)
                              
    
    security.declareProtected('View', 'CSVExport')
    
    def CSVExport(self, batchsize=None, withheaders=True, 
                  issue_export=True, filename='export.csv',
                  REQUEST=None):
        """ return a CSV file with all issue information """
        outfile = cStringIO.StringIO()
        if csv is None:
            return "Sorry, CSV not supported"
        writer = csv.writer(outfile)
        
        if withheaders:
            self._write_csv_headers(writer)
            
        # if 'issue_export' is true we don't do any filtering
        # or any nonsense like that, we just dump all issues 
        # there are and sort by 'issuedate'
        
        if issue_export:
            issues = self.getIssueObjects()
            issues = self._dosort(issues, 'issuedate')
        else:
            issues = self.ListIssuesFiltered()
            
        try:
            if batchsize:
                batchsize = abs(int(batchsize))
        except:
            batchsize = None
            
        if batchsize:
            issues = issues[:batchsize]
            
        
        default_sortorder = self.getDefaultSortorder()
        
        for issue in issues:
            title = issue.getTitle()
            if self.isFromBrother(issue):
                title += "(%s)" % self.getBrotherFromIssue(issue).getTitle()
            row = ['#%s' % issue.getIssueId(), 
                   title.encode(UNICODE_ENCODING),
                   issue.getStatus(), 
                   issue.getFromname().encode(UNICODE_ENCODING),
                   issue.getEmail()]
            if default_sortorder == 'issuedate':
                row.append(issue.getIssueDate())
            else:
                row.append(issue.getModifyDate())
            row.append(', '.join(issue.getSections()))
            row.append(issue.getUrgency())
            row.append(issue.getType())
            writer.writerow(row)
            
            
        if REQUEST is not None:
            R = REQUEST.RESPONSE
            
            ct = 'application/msexcel-comma'
            R.setHeader('Content-Type', ct)
            
            cd = 'inline;filename="%s"' % filename
            R.setHeader('Content-Disposition', cd)

            
        return outfile.getvalue()
    
    def _write_csv_headers(self, writer):
        """ append the header for a csv file """
        row = ['ID','Subject', 'Status', 'Fromname','Email',
               self.translateSortorderOption(self.getDefaultSortorder()),
               'Sections', 'Urgency', 'Type']
        writer.writerow(row)
        
    
    security.declarePublic('RSS091')
    security.declarePublic('RSS10')
    security.declarePublic('rss.xml')

    
    security.declarePublic('CDATAText')
    def CDATAText(self, text):
        """ return text wrapped in CDATA tags """
        return "<![CDATA[%s]]>" % text.strip()
        
    
    def RDF(self, batchsize=None, issues=None):
        """ return an RDF feed issues """
        request = self.REQUEST
        
        template = self.rdf_template
        root = self.getRoot()
        about_url = root.absolute_url() + '/rdf.xml'
        
        if issues is None:
            request.set('keep_sortorder', False)
            request.set('sortorder', 'issuedate')
            request.set('reverse', False)
            issues = self.ListIssuesFiltered(skip_filter=True)
        else:
            for issue in issues:
                assert issue.meta_type == ISSUE_METATYPE, \
                "Object meta_type not %r its %r" % (ISSUE_METATYPE, issue.meta_type)
                
        if batchsize is None:
            batchsize = self.getBatchSize()
        else:
            batchsize = int(batchsize)
        issues = issues[:batchsize]
        
        content_type = 'application/rdf+xml'
        request.RESPONSE.setHeader('Content-Type', content_type)
        
        return template(self, self.REQUEST, about_url=about_url, issues=issues)
        
    
    def RSS10(self, batchsize=None, withheaders=True, show='normal'):
        """ return RSS XML 1.0 """
        request = self.REQUEST
        root = self.getRoot()
        header = '<?xml version="1.0" encoding="ISO-8859-1"?>\n\n'
        header += '<rdf:RDF\n'
        header +=' xmlns="http://purl.org/rss/1.0/"\n'
        header +=' xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
        header +=' xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
        header +=' xmlns:sy="http://purl.org/rss/1.0/modules/syndication/"'
        header +='\n>\n\n'

        rss_url = root.absolute_url()+'/rss.xml'
        header += '<channel rdf:about="%s">\n'%rss_url
        header += '  <title>%s</title>\n'%root.getTitle()
        header += '  <link>%s</link>\n'%root.absolute_url()
        header += '  <description>IssueTrackerProduct</description>\n'
        header += '  <dc:language>English</dc:language>\n'
        header += '  <dc:publisher>%s</dc:publisher>\n'%self.getSitemasterEmail()

        xml = ''
        items = '<items>\n  <rdf:Seq>\n'
        if batchsize is None:
            batchsize = self.default_batch_size
        else:
            batchsize = int(batchsize)

        # manually set sortorder
        request.set('keep_sortorder',False)
#        request.set('sortorder','modifydate')
        request.set('reverse', True)
        
        comments_as_items = False
        if show.lower() in ['all','everything']:
            # then don't only show issues that are created new but
            # even those that are only follow ups
            request.set('sortorder', 'modifydate')
            comments_as_items = True
        else:
            request.set('sortorder', 'issuedate')

        
        self.REQUEST.set('keep_sortorder', 0)
        self.REQUEST.set('sortorder', self.getDefaultSortorder())
        self.REQUEST.set('reverse', 0)
        
        allissues = self.ListIssuesFiltered(skip_filter=True)
        
        for issue in allissues[:batchsize]:
            sections = ", ".join(issue.sections)
            url = issue.absolute_url()
            if comments_as_items and issue.hasThreads():
                _all_threads = issue.objectValues(ISSUETHREAD_METATYPE)
                lasthread = _all_threads[-1]
                issuetitle = Utils.html_quote(issue.getTitle())
                threadtitle = Utils.html_quote(lasthread.getTitle())
                if self.ShowIdWithTitle():
                    title = u"%s #%s (%s)"%(unicodify(issue.getTitle()), issue.getId(), lasthread.getTitle())
                else:
                    title = u"%s (%s)"%(unicodify(issue.getTitle()), lasthread.getTitle())
                description = unicodify(lasthread.showComment())
                fromname = unicodify(lasthread.getFromname())
                fromemail = lasthread.getEmail()
                date = lasthread.getThreadDate()
                url += '#i%s'%len(_all_threads)
            else:
                #issuetitle = Utils.html_quote(issue.title)
                #issuestatus = Utils.html_quote(issue.status.capitalize())
                if self.ShowIdWithTitle():
                    title = u"%s #%s (%s)"%(unicodify(issue.title), issue.getId(), issue.status.capitalize())
                else:
                    title = u"%s (%s)"%(unicodify(issue.title), issue.status.capitalize())
                description = issue.showDescription() #issue.description.strip()
                fromname = issue.getFromname()
                fromemail = issue.getEmail()
                date = issue.getIssueDate()
            #if isinstance(title, unicode):
            #    title = title.encode('ascii','xmlcharrefreplace')
            title = self._prepare_feed(title)
            #if isinstance(description, unicode):
            #    description = description.encode('ascii','xmlcharrefreplace')
            description = self._prepare_feed(description)
                
            date = date.strftime("%Y-%m-%dT%H:%M:%S+00:00")

            item = '<item rdf:about="%s">\n' % url
            item += '  <title>%s</title>\n' % title
            item += '  <description>%s</description>\n' % description
            item += '  <link>%s</link>\n' % url
            item += '  <dc:subject>%s</dc:subject>\n' % sections
            item += '  <dc:date>%s</dc:date>\n' % date
            item += '</item>\n\n'

            xml += item

            items += '  <rdf:li rdf:resource="%s" />\n'%url

        items += ' </rdf:Seq>\n</items>\n'

        footer = '</rdf:RDF>\n'

        # Combine things
        header += items + '</channel>\n\n'

        rss = header + xml + footer

        request.RESPONSE.setHeader('Content-Type','application/rdf+xml')
        return rss


    def RSS091(self, batchsize=None, withheaders=1, show='normal'):
        """ return RSS XML """
        request = self.REQUEST
        root = self.getRoot()
        header="""<?xml version="1.0"?><rss version="0.91">
        <channel>
        <title>%s</title>
        <link>%s</link>
        <description>%s</description>
        <language>en-uk</language>
        <copyright></copyright>
        <webMaster>%s</webMaster>\n"""%\
           (root.title, root.absolute_url(), root.title,
            self.sitemaster_email)
        logo = getattr(self, 'issuetracker_logo.gif')
        header=header+"""<image>
        <title>%s</title>
        <url>%s</url>
        <link>%s</link>
        <width>%s</width>
        <height>%s</height>
        <description>%s</description>
        </image>\n"""%(logo.title, logo.absolute_url().strip(),
                       root.absolute_url(),
                       logo.width, logo.height,
                       root.title)
        # manually set sortorder
        request.set('sortorder','date')
        request.set('reverse',True)
        xml=''
        if batchsize is None:
            batchsize = self.default_batch_size
            

        comments_as_items = 0
        if show.lower() in ['all','everything']:
            # then don't only show issues that are created new but
            # even those that are only follow ups
            request.set('sortorder', 'changedate')
            comments_as_items = 1
        else:
            request.set('sortorder', 'creationdate')
            
        allissues = self.ListIssuesFiltered()
        for issue in allissues[:batchsize]:
            if comments_as_items and issue.hasThreads():
                lasthread = issue.objectValues(ISSUETHREAD_METATYPE)[-1]
                title = "%s (%s)"%(issue.getTitle(), lasthread.getTitle())
                description = lasthread.comment
                fromname = lasthread.fromname
                fromemail = lasthread.email
            else:
                title = "%s (%s)"%(issue.title, issue.status.capitalize()) 
                description = issue.description
                fromname = issue.fromname
                fromemail = issue.email
            title = self._prepare_feed(title)
            description = self._prepare_feed(description)

            xml=xml+"""\n\t<item>
            <title>%s</title>
            <description>%s</description>
            <link>%s</link>
            """%(title, description, issue.absolute_url())
            if fromname != '':
                author = "%s (%s)"%(fromname, fromemail)
                xml="%s\n<author>%s</author>\n"%(xml, author)
            xml=xml+"\n\t</item>"
            
        footer="""</channel>\n</rss>"""
        if withheaders:
            xml = header+xml+footer
            
        response = request.RESPONSE
        response.setHeader('Content-Type', 'text/xml')
        return xml
    

    
    def _prepare_feed(self, s):
        """ prepare the text for XML usage """
        return "<![CDATA[%s]]>" % s

    def showURL2Issue(self, url=None, href=0, maxlength=60):
        """ display the url2issue for ShowIssueData """
        if url is None:
            url = self.url2issue
            
        protocols = ('http','svn+ssh','svn','ftp')
        if href:
            
            if not [i for i in protocols if url.startswith(i)]:
                url = 'http://'+url
            return url
        else:
            if url.startswith('http://www.'):
                url = url.replace('http://','')
            return self.showBriefURL(url, maxlength)
        
    def showBriefURL(self, url, maxlength=70):
        """ show begining and end of a URL """
        if len(url) > maxlength:
            half = int(maxlength/2)
            url = url[0:half]+'...'+url[-half:]
        return url

    
    def displayBriefTitle(self, title):
        """ return the title or truncate it a bit """
        limit = BRIEF_TITLE_MAX_LENGTH
        if self.ShowIdWithTitle():
            limit -= self.randomid_length
        if isinstance(title, str):
            # the old way
            return self.tag_quote(
                     Utils.html_entity_fixer(
                         self.lengthLimit(title, limit, '...')
                       )
                 )
        else:
            return self.tag_quote(self.lengthLimit(title, limit, '...'))
                 
    def getOutlookDaylabels(self, issues):
        """ return a dictionary where the keys are the issue ids and the value is the
        string that expresses the day bucket. """

        all={}
        def equal(date1, date2, fmt):
            return date1.strftime(fmt) == date2.strftime(fmt)
   
        today = DateTime()
        for issue in issues:
            all_values = all.values()
            modify_date = issue.getModifyDate()
            if equal(today, modify_date, '%Y%m%d'):
                if 'Today' not in all_values:
                    all[issue.getId()] = 'Today'
                    
            elif equal(today, modify_date+1, '%Y%m%d'):
                if 'Yesterday' not in all_values:
                    all[issue.getId()] = 'Yesterday'
                    
            elif equal(today, modify_date, '%Y%m%W'):
                if 'This week' not in all_values:
                    all[issue.getId()] = 'This week'
                    
            elif equal(today, modify_date+7, '%Y%m%W'):
                if 'Last week' not in all_values:
                    all[issue.getId()] = 'Last week'
                    
            elif equal(today, modify_date+14, '%Y%m%W'):
                if 'Two weeks ago' not in all_values:
                    all[issue.getId()] = 'Two weeks ago'
                    
            elif equal(today, modify_date, '%Y%m'):
                if 'This month' not in all_values:
                    all[issue.getId()] = 'This month'
                    
            elif equal(today, modify_date + 30, '%Y%m'):
                if 'Last month' not in all_values:
                    all[issue.getId()] = 'Last month'
                    
        return all

    #def _findIssueLinks(self, text):
    #    """ return a compiled regular expression of where there are 
    #    links to other issues. The rules for making a link is:
    #        <issuetracker id>#<issue id> (eg. Real#0103)
    #        #<issue id> (eg. #0103)
    #        #prefix<issue id> (eg. #ibm0103)
    #    Bare in mind that the text might contain hyperlinks to issues
    #    from before, ignore them.
    #    """
        
        

    ## Cookies!


    def saveEmailstring(self, to):
        """ Save to string as a cookie """
        raise "DeprecatedError"
        key = EMAILSTRING_COOKIEKEY
        key = self.defineInstanceCookieKey(key)
        self.set_cookie(key, to)

    def getSavedEmailstring(self):
        """ Return cookie translated or nothing """
        key = EMAILSTRING_COOKIEKEY
        key = self.defineInstanceCookieKey(key)
        
        if self.REQUEST.cookies.has_key(key):
            to = self.REQUEST.cookies[key]
            for item in self.getNotifyables():
                to = to.replace(item.getEmail(), item.getName())
            return to
        else:
            return None

    def saveEmailfriends(self, friends):
        """ Save to string as a cookie with '|' between each """
        raise "DeprecatedError"
        if not Utils.same_type(friends, []):
            friends = [friends]
        key = EMAILFRIENDS_COOKIEKEY
        key = self.defineInstanceCookieKey(key)
        friends = '|'.join([str(x).strip() for x in friends])
        self.set_cookie(key, friends)
        
    def getSavedEmailfriends(self):
        """ return cookie translated or nothing """
        key = EMAILFRIENDS_COOKIEKEY
        key = self.defineInstanceCookieKey(key)

        if self.REQUEST.cookies.has_key(key):
            friends = self.REQUEST.cookies.get(key)
            return [x.strip() for x in friends.split('|')]
        else:
            return []
        

    def getSavedTextFormat(self, no_default=False):
        """
        This method returns what display_format value the user has. 
        If none found, then the default one is returned.
        """
        
        issueuser = self.getIssueUser()
        if issueuser:
            if issueuser.getDisplayFormat():
                return issueuser.getDisplayFormat()

        if no_default:
            default = ""
        else:
            default = self.getDefaultDisplayFormat()

        s=None
        cookiekey = self.getCookiekey('display_format')

        if self.has_cookie(cookiekey):
            s = self.get_cookie(cookiekey)

        if s not in self.display_formats:
            s = None

        if s is None:
            return default
        else:
            return s    

    def get_cookie(self, name, default=None):
        """ return RESPONSE cookie """
        value = self.REQUEST.cookies.get(name,default)
        return value
    
    def set_cookie(self, name, value, days=365):
        """ set RESPONSE cookie """
        later = DateTime() + days
        later = later.rfc822()
        try:
            value = str(value)
        except UnicodeEncodeError:
            value = value.encode(UNICODE_ENCODING)
            
        self.REQUEST.RESPONSE.setCookie(name, value, expires=later, path='/')
        
        
    def has_cookie(self, name):
        """ return cookie presence """
        return self.REQUEST.cookies.has_key(name)
    
    def expire_cookie(self, name):
        """ expire a cookie """
        self.REQUEST.RESPONSE.expireCookie(name, path='/')

    def getSavedUser(self, name_email='email', d=0):
        """
        Return the name or email from request,
        if not found, return from cookie,
        else return ""
        """
        request = self.REQUEST

        if name_email =='email':
            s='email'
            cookie=self.getCookiekey('email')
        else:
            s='fromname'
            cookie=self.getCookiekey('name')
            
        issueuser = self.getIssueUser()
        if issueuser:
            if s == 'email':
                issueuser_email = issueuser.getEmail()
                if issueuser_email:
                    return issueuser_email
            elif s == 'fromname':
                issueuser_name = issueuser.getFullname()
                if issueuser_name:
                    return issueuser_name
                
        # now we know what we're looking for
        acl_username = getSecurityManager().getUser().getUserName()
        if acl_username.lower().replace(' ','') == 'anonymoususer':
            acl_username = None
            
        if request.get(s):
            return request[s]
        elif self.get_cookie(cookie):
            if s =='fromname':
                return unicodify(self.get_cookie(cookie))
            else:
                return self.get_cookie(cookie)
        elif acl_username:
            r = self._getACLCookie(acl_username, s)
            if r is None:
                r = ""
            return r
        else:
            return ""

    def getSavedUserName(self):
        """ wrap getSavedUser() """
        return self.getSavedUser('fromname')

    def getSavedUserEmail(self):
        """ wrap getSavedUser() """
        return self.getSavedUser('email')

    def _getACLCookie(self, name, action='email'):
        if action == 'fromname':
            return self.getACLCookieNames().get(name)
        elif action == 'email':
            return self.getACLCookieEmails().get(name)
        elif action == 'displayformat':
            return self.getACLCookieDisplayformats().get(name)
        

    ##
    ## Sessions!
    ##

    def getFilterValue(self, key, filterlogic=None,
                       request_only=False,
                       default=None):
        """ return what the value should be. """
        if filterlogic is None:
            filterlogic = self.getFilterlogic()

        filterkey = 'f-%s-%s'%(key, filterlogic)
        filterkey_simple = 'f-%s'%(key)
        request = self.REQUEST

        value = default
        if request.has_key(filterkey_simple):
            value = request.get(filterkey_simple)
            if key in ('statuses', 'sections', 'urgencies', 'types') \
                   and Utils.same_type(value, 's'):
                value = [value]
                
        elif not request_only and self.has_session(filterkey):
            value = self.get_session(filterkey)
            
        if default is not None and value is None:
            return default
        else:
            return value
                


    def _getDefaultFilterValueBlock(self, key):
        """ return default values """
        if key == 'fromname' or key == 'email':
            return ""
        else:
            return []


    def _getDefaultFilterValueShow(self, key):
        """ return default values """
        if key == 'sections':
            return []
            return self.sections_options
        elif key == 'fromname' or key == 'email':
            return ""
        else:
            return []
            return self.__dict__[key]
            
            

    def ShowFilter(self, filtername, sequence=[]):
        """ Check whether to show filter or not """
        request = self.REQUEST
        key = FILTEROPTIONS_KEY
        if request.has_key(filtername):
            return request[filtername]
        elif self.has_session(key):
            filteroptions = self.get_session(key)
            if filteroptions.has_key(filtername):
                return filteroptions[filtername]
        return []


    def getListPageTitle(self, default='List Issues'):
        """ return a suitable page title for this list (ListIssues or CompleteList) """
        request = self.REQUEST
        if request.get('q'):
            return "Search Results"
        elif request.get('report'):
            try:
                # try to find the actual title of the report itself
                container = self.getReportsContainer()
                if hasattr(container, request.get('report')):
                    report = getattr(container, request.get('report'))
                    return "Report: %s" % report.title_or_id()
                
            except:
                return "Report"
        elif request.get('i'):
            i = ss(request.get('i'))
            if i == 'assigned':
                return "Issues assigned to you"
            elif i == 'added':
                return "Issues you have added"
            elif i == 'followedup':
                return "Issues you have followed up on"
            elif i == 'subscribed':
                return "Issues you have subscribed to"
            else:
                return "Your Issues"
        else:
            return "List Issues"
            
    
    def setWhichList(self, what):
        """ set a SESSION with which list """
        key = WHICHLIST_COOKIEKEY
        what = ss(what)
        if what in ['completelist','listissues']:
            issueuser = self.getIssueUser()
            if issueuser:
                # set the which list 
                issueuser.setMiscProperty('whichlist', what)
            else:
                # put it in a cookie
                self.set_cookie(key, what)
                
        return None
    
    def whichList(self):
        """ inspect the SESSION object if there's information
        about either "ListIssues" or "CompleteList"
        """
        key = WHICHLIST_COOKIEKEY
        issueuser = self.getIssueUser()
        default = 'ListIssues'
        if issueuser and issueuser.hasMiscProperty('whichlist'):
            # get it from the acl user
            value = issueuser.getMiscProperty('whichlist')
        else:
            # get it from cookie
            value = self.get_cookie(key)
            
        if value and ss(value) == 'completelist':
            return 'CompleteList'
        else:
            return default

    def setWhichSubList(self, what):
        """ determines 'compact' or 'rich' """
        key = WHICHSUBLIST_COOKIEKEY
        what = ss(what)
        
        if what in ('rich','compact'):
            issueuser = self.getIssueUser()
            if issueuser:
                # set the which list 
                issueuser.setMiscProperty('whichsublist', what)
            else:
                # set it in a cookie
                self.set_cookie(key, what)
        return None
    
    def whichSubList(self):
        """ return either 'rich' (default) or 'compact'
        If it's defined in REQUEST, remember that forever """
        
        c_key = WHICHSUBLIST_COOKIEKEY
        default = 'rich'
        
        ok_values = ('rich', 'compact')
        issueuser = self.getIssueUser()

        if ss(self.REQUEST.get('list-type','')) in ok_values:
            # remember it!
            value = ss(self.REQUEST.get('list-type',''))
            if issueuser:
                issueuser.setMiscProperty('whichsublist', value)
            else:
                self.set_cookie(c_key, value)
            return value
        else:
            # look for an old one
            if issueuser and issueuser.hasMiscProperty('whichsublist'):
                value = issueuser.getMiscProperty('whichsublist')
                if value in ok_values:
                    return value
                else:
                    return default
            else:
                # use cookies instead
                cookie_value = self.get_cookie(c_key, None)
                if cookie_value in ok_values:
                    return cookie_value
                else:
                    return default
                
    def getListIssuesList(self, sublist):
        """ return the template for a particular sublist """
        
        if self.doDebug():
            assert sublist in ('rich','compact'), "Unrecognized sublist %r" % sublist
           
        # Read the comment inside getHeader() regard CheckoutableTemplates to understand
        # why we do what we do here. 
        if sublist == 'rich':
            zodb_id = 'richList.zpt'
            base_tmpl = self.richList
        else:
            zodb_id = 'compactList.zpt'
            base_tmpl = self.compactList
            
        return getattr(self, zodb_id, base_tmpl)
        
                
    def changeWhichSubListURL(self, newtype):
        """ return the URL for the interface which is links that lets 
        you change the sublist behaviour to Compact or Rich. """
        assert newtype in ('Compact','Rich')
        
        request = self.REQUEST
        key = "list-type"
        
        params = {key:newtype}
        
        for e in ('q','i','f-statuses','f-fromname','f-email','f-sections',
                  'f-urgencies','f-types','report'):
            if request.get(e):
                params[e] = request.get(e)
            
        url = self.relative_url()+'/ListIssues'
        return Utils.AddParam2URL(url, params)
    
    def CSVExportURL(self):
        """ return the URL for the interface which is links that lets 
        you export to csv with the ListIssues.csv function. """
        
        request = self.REQUEST
        
        params = {}
        
        for e in ('q','i','f-statuses','f-fromname','f-email','f-sections',
                  'f-urgencies','f-types','report'):
            if request.get(e):
                params[e] = request.get(e)
            
        url = self.relative_url()+'/ListIssues.csv'
        return Utils.AddParam2URL(url, params, plus_quote=True)
    

    def ResetFilter(self, page='ListIssues', redirectafter=True):
        """ reset the filter then show the ListIssues or eq. again """
        for key in ('statuses','sections','urgencies','types',
                    'fromname','email'):
            subkey1 = 'f-%s-show'%key
            subkey2 = 'f-%s-block'%key
            if self.has_session(subkey1):
                self.delete_session(subkey1)

            if self.has_session(subkey2):
                self.delete_session(subkey2)
                
        if self.has_session('last_savedfilter_id'):
            self.delete_session('last_savedfilter_id')
            
            
        key = LAST_SAVEDFILTER_ID_COOKIEKEY
        key = self.defineInstanceCookieKey(key)
        if self.has_cookie(key):
            debug("Expire cookie %s" % key, steps=1)
            self.expire_cookie(key)

        if redirectafter:
            page = page.lower().strip()
            if page == 'listissues':
                page = '/ListIssues'
            elif page == 'completelist':
                page = '/CompleteList'
            else:
                raise "NotFound"
            self.REQUEST.RESPONSE.redirect(self.getRootURL()+page)
        
    def HideFilter(self, page='ListIssues', REQUEST=None):
        """ hide the filter then show the ListIssues or eq. again """
        key = SHOW_FILTEROPTIONS_KEY
        self.set_session(key, False)
        page = page.lower().strip()
        if page == 'listissues':
            page = '/ListIssues'
        elif page == 'completelist':
            page = '/CompleteList'
        else:
            raise "NotFound"
        
        url = self.getRootURL()+page
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect(url)
        else:
            return url

        
    def get_session(self, name, default=None, globally=0):
        """ Override the session.get method a little bit """
        if not globally:
            name = self.defineInstanceCookieKey(name)
        try:
            value = self.REQUEST.SESSION.get(name, default)
            return value
        
        except KeyError:
            # something's gone wrong with the SESSION object
            return default
    
    def set_session(self, name, value, globally=0):
        """ Overrode the session.set method a little bit """
        if not globally:
            name = self.defineInstanceCookieKey(name)
        self.REQUEST.SESSION.set(name, value)
        
    def has_session(self, name, globally=0):
        """ Override the session.has_key method a little big """
        if not globally:
            name = self.defineInstanceCookieKey(name)
        return self.REQUEST.SESSION.has_key(name)

    def delete_session(self, name, globally=0):
        """ override the session.delete method """
        if not globally:
            name = self.defineInstanceCookieKey(name)
        self.REQUEST.SESSION.delete(name)

    ## URL related
    
    def aurl(self, url, params={}, ignore=[]):
        """ modify the URL to include url-request-variables """
        request = self.REQUEST
        
        splitted = url.split('/')
        
        #             # internal name     # what it's called in REQUEST
        queryitems = ({'key':'start',     'mkey':'start'},
                      {'key':'sortorder', 'mkey':'sortorder'},
                      {'key':'reverse',   'mkey':'reverse'},
                      {'key':'show',      'mkey':'show'},
                      {'key':'report',    'mkey':'report'}
                      )
        
        splitter = '-'
        # Use old things
        if not Utils.same_type(ignore, []):
            ignore = [ignore]
        keys_applied = []
        for key, value in params.items():
            keys_applied.append(key)
            if value is not None and key not in ignore:
                splitted.append("%s%s%s"%(key, splitter, value))
                
        # Add new things
        for each in queryitems:
            key, mkey = each['key'], each.get('mkey')
            if mkey is not None:
                if key not in keys_applied and key not in ignore and\
                request.has_key(mkey) and request[mkey] is not None:
                    splitted.append("%s%s%s"%(key, splitter, request[mkey]))
        
        return '/'.join(splitted)

    def getRootURL(self, relative=None):
        """ quick wrapper around getRoot() """
        return self.getRoot().absolute_url()

    def getRootRelativeURL(self):
        """ quick wrapper around getRoot() """
        return self.getRoot().relative_url()

    def issueURLbyID(self, issueID):
        """ Return absolute_url of an issue from its id """
        return getattr(self.getRoot(),issueID).absolute_url()

    def thisInURL(self, page, homepage=0):
        """ To find if a certain objectid is in the URL """
        URL = self.ActionURL(self.REQUEST.URL)
        rootURL = self.getRootURL()
        if homepage and URL==rootURL:
            return True
        else:
            URL = URL.lower()
            if isinstance(page, (list, tuple)):
                # 'page' is iterable, think of an OR between each
                for each in page:
                    expected = rootURL +'/'+ each
                    if URL == expected.lower():
                        return True
                return False
            else:
                expected = rootURL +'/'+ page
                if URL == expected.lower():
                    return True
                elif not URL.startswith(rootURL):
                    # most likely because we're inspecting a brother issue
                    expected = '/'.join(rootURL.split('/')[:-1]+[URL.split('/')[-2]]+[page])
                    return URL == expected.lower()
                else:
                    return False

    def ActionURL(self, url=None):
        """
        If URL is http://host/index_html
        I prefer to display it http://host
        Just a little Look&Feel thing
        """
        if url is None:
            url = self.REQUEST.URL

        URLsplitted = url.split('/')
        if URLsplitted[-1] == 'index_html':
            return '/'.join(URLsplitted[:-1])

        return url
    
    ## ZCatalog related


    def getCatalog(self):
        """ return the installed ICatalog object """
        if hasattr(self, 'ICatalog'):
            return self.ICatalog
        else: # backward compatability
            return self.Catalog
        
    def InitZCatalog(self, t={}):
        """ create a ZCatalog called 'ICatalog' and change its properties
        accordingly """
        if not 'ICatalog' in self.objectIds('ZCatalog'):
            self.manage_addProduct['ZCatalog'].manage_addZCatalog('ICatalog','')
            t['ICatalog'] = "ZCatalog"
        zcatalog = self.getCatalog()
        indexes = zcatalog._catalog.indexes
        
        if not hasattr(zcatalog, 'Lexicon'):
            # This default lexicon sucks because it doesn't support unicode.
            # Consider creating a http://www.zope.org/Members/shh/UnicodeLexicon
            # instead.
            script = zcatalog.manage_addProduct['ZCTextIndex'].manage_addLexicon
            
            wordsplitter = Empty()
            wordsplitter.group = 'Word Splitter'
            wordsplitter.name = 'Whitespace splitter'
            
            casenormalizer = Empty()
            casenormalizer.group = 'Case Normalizer'
            casenormalizer.name = 'Case Normalizer'
            
            stopwords = Empty()
            stopwords.group = 'Stop Words'
            stopwords.name = 'Remove listed stop words only'
            
            script('Lexicon', 'Default Lexicon',
                   [wordsplitter, casenormalizer, stopwords])
            t['Lexicon'] = "Lexicon for ZCTextIndex created"
        
#        if not hasattr(zcatalog, 'Vocabulary'):
#            script = zcatalog.manage_addProduct['ZCatalog'].manage_addVocabulary
#            script(id='Vocabulary', title='', globbing=1)
#            t['Vocabulary'] = "It is recommended that you now run Update Catalog"
    
        for fieldindex in ('id','meta_type'):
            if not indexes.has_key(fieldindex):
                zcatalog.addIndex(fieldindex, 'FieldIndex')
                
        for keywordindex in ('filenames',):
            if not indexes.has_key(keywordindex):
                zcatalog.addIndex(keywordindex, 'KeywordIndex')
            
        
        textindexes = ('email','url2issue')
        for idx in textindexes:
            if not indexes.has_key(idx):
                zcatalog.addIndex(idx, 'TextIndex')
                
        #wrapped_textindexes = [('fromname','getTitle_idx')]
        #for idx, indexed_attrs in wrapped_textindexes:
        #    if indexes.has_key(idx) and not indexes[idx].call_methods:
        #        # the old way!
        #        indexes.pop(idx)
        #    if not indexes.has_key(idx):
        #        extra = record()
        #        extra.indexed_attrs = indexed_attrs
        #        extra.vocabulary = 'Vocabulary'
        #        zcatalog.addIndex(idx, 'TextIndex', extra)
            
        #raise "STOP", 'lukasz'
    
        zctextindexes = (
          ('title', 'getTitle_idx'),
          ('description', 'getDescription_idx'),
          ('comment', 'getComment_idx'),
          ('fromname', 'getFromname_idx'),
        )
        for idx, indexed_attrs in zctextindexes:
            
            
            
            extras = Empty()
            extras.doc_attr = indexed_attrs
            # 'Okapi BM25 Rank' is good if you match small search terms
            # against big texts. 
            # 'Cosine Rule' is useful to match similarity between two texts
            extras.index_type = 'Okapi BM25 Rank'
            extras.lexicon_id = 'Lexicon'
            
            if indexes.has_key(idx) and indexes.get(idx).meta_type \
              not in ('ZCTextIndex', 'TextIndexNG2'):
                zcatalog.delIndex(idx)
                
            if indexes.has_key(idx):# and indexes.get(idx)
                if indexed_attrs not in indexes.get(idx).getIndexSourceNames():
                    # The old way
                    zcatalog.delIndex(idx)
            
            if not indexes.has_key(idx):
                zcatalog.addIndex(idx, 'ZCTextIndex', extras)
                t['ZCTextIndex'] = idx
                
        # now we need to say that certain indexes must use
        # the vocabulary.
        #titleidx = indexes.get('title')
        #if titleidx.vocabulary_id != 'Vocabulary':
        #    titleidx.manage_setPreferences('Vocabulary')
            
        return t


    def UpdateCatalog(self, REQUEST=None):
        """ Re-find items in the Catalog """
        request = self.REQUEST

        catalog = self.getCatalog()
        
        # Zope 2.8.0 migration hell
        if not hasattr(catalog._catalog, '_length'):
            if hasattr(catalog._catalog, 'migrate__len__'):
                # perform the zope 2.8.0 migration script
                catalog._catalog.migrate__len__()
            else:
                # That's ok. This means that the _catalog object didn't
                # have the zope 2.8.0 migration method which effectively means that
                # we don't need to do the migration :)
                pass
            
        
        catalog.manage_catalogClear()
        
        for issue in self.getIssueObjects():
            issue.index_object()
            for thread in issue.objectValues(ISSUETHREAD_METATYPE):
                thread.index_object()

        msg = "%s updated."%catalog.getId()
        if REQUEST is None:
            return msg
        else:
            method = Utils.AddParam2URL
            desturl = self.getRootURL()+"/manage_ManagementForm"
            url = method(desturl,{'manage_tabs_message':msg})
            self.REQUEST.RESPONSE.redirect(url)


    ## Notification related

    def dispatcher(self, notificationobjects=None):
        """ Sends out all the emails or at least returns the string to use """
        if notificationobjects is None:
            notificationobjects = self.getAllNotifications()

        if not isinstance(notificationobjects, (list, tuple)):
            notificationobjects = [notificationobjects]
            
        sendworthy = [x for x in notificationobjects if not x.isDispatched()]

        roottitle = self.getRoot().getTitle()
        sitemaster_name = self.getSitemasterName()
        sitemaster_email = self.getSitemasterEmail()
        
        if not sitemaster_name:
            LOG(self.__class__.__name__, INFO, "Sitemaster name not set")
        if not Utils.ValidEmailAddress(sitemaster_email):
            m = "(%s) Sitemaster email not valid. Email might not work"
            m = m%self.getRoot().getTitle()
            LOG(self.__class__.__name__, WARNING, m)
            
        From ="%s <%s>"%(sitemaster_name, sitemaster_email)

        senttos = {}

        
        for notification in sendworthy:
            
            issueID = notification.issueID
            #issue_url = self.issueURLbyID(issueID)
            issue = self.getIssueObject(issueID)
            issueid_header = issue.getGlobalIssueId()
            issue_url = issue.absolute_url()

            if self.ShowIdWithTitle():
                Subject = "%s: #%s %s"%(roottitle, issueID, 
                                        notification.title)
            else:
                Subject = "%s: %s"%(roottitle, notification.title)
            fromname = notification.fromname
            if not fromname:
                fromname = '(No name)'

            br = '\r\n' 

            msg = notification.date.strftime(self.display_date) +  br
            msg += '%s has responded to "%s"'%(fromname, notification.title) + br
            msg += issue_url + br*2
            
            msg += 'Change:' + br + ' '*4 + notification.change + br * 2

            msg += 'Comment:' + br
            if notification.comment.strip():
                msg += Utils.LineIndent(notification.comment, ' ' * 3, 67)
            else:
                msg += "(no comment)"

            msg += br*2
            msg += issue_url +\
                   '#i%s'%notification.anchorname

            msg += br*2

            signature = self.showSignature()
            if signature:
                msg += '--' + br + signature

            emails = [x.strip() for x in notification.emails]
            while '' in emails:
                emails.remove('')
            emails = [x for x in emails if Utils.ValidEmailAddress(x)]
            emails = Utils.uniqify(emails)
            
            for email in emails:
                if senttos.has_key(issueID):
                    senttos[issueID].append(email)
                else:
                    senttos[issueID] = [email]

                To = email

                # send it!
                success = self.sendEmail(msg, To, From, Subject, swallowerrors=True,
                                         headers={EMAIL_ISSUEID_HEADER: issueid_header})
                if success:
                    notification.setSuccessEmail(To)
                    
            notification.MarkNotificationDispatch()

        # show some output now
        if senttos:
            out = "Notifications sent.\n\n"
            for issueID, emails in senttos.items():
                out += '*%s*\n'%issueID
                for email in emails:
                    out += '  %s\n'%email
                out += '\n'
        else:
            out = "No notifications sent"

        return out
            
    

    def getAlwaysNotify(self, except_email=None):
        """ return always_notify or default """
        always = getattr(self, 'always_notify', DEFAULT_ALWAYS_NOTIFY)
        
        if except_email is not None:
            except_email = except_email.lower().strip()
            always_checked = []
            for each in always:
                emails = self.preParseEmailString(each, aslist=1)
                if emails:
                    if emails[0].lower().strip() != except_email:
                        always_checked.append(each)
            always=always_checked
                
        return always

    
    def Always2Notify(self, format='email', emailtoskip=None, requireemail=False,
                      include_assignee=False):
        """ return a list of strings of people who will be notified
        when this issue gets submitted.
        'format' can take three forms: email, name, both or merged.
            both returns 'Peter <peter@email.com>'
            merged returns whatever self.ShowNameEmail() does
        """
        if format not in ('email','name','both', 'merged'):
            format = 'email'
        if emailtoskip is None:
            issueuser = self.getIssueUser()
            if issueuser:
                emailtoskip = issueuser.getEmail()
            elif self.REQUEST.get('email'):
                emailtoskip = self.REQUEST.get('email')
            elif self.has_cookie(self.getCookiekey('email')):
                emailtoskip = self.get_cookie(self.getCookiekey('email'))
                
        all = []
        
        appended_email_addresses = []
        
        always = self.getAlwaysNotify()
        checked = [self._checkAlwaysNotify(x, format='list') for x in always]
        
        if include_assignee and self.REQUEST.get('notify-assignee'):
            assignment_acl_user = self.REQUEST.get('assignee')
            acl_path, username = assignment_acl_user.split(',')
            try:
                userfolder = self.unrestrictedTraverse(acl_path)
                if userfolder.data.has_key(username):
                    u = userfolder.data.get(username)
                    checked.append((True, [u.getFullname(), u.getEmail()]))
            except:
                pass
        elif include_assignee and self.objectValues(ISSUEASSIGNMENT_METATYPE):
            first_assignment = self.objectValues(ISSUEASSIGNMENT_METATYPE)[0]
            assignee_name = first_assignment.getAssigneeFullname()
            assignee_email = first_assignment.getAssigneeEmail()
            if requireemail:
                if assignee_email:
                    checked.append((True, [assignee_name, assignee_email]))
            else:
                checked.append((True, [assignee_name, assignee_email]))
            
            
        for valid, name_and_email in checked:
            add = ''
            if valid:
                _name = name_and_email[0]
                _email = name_and_email[1]
                if emailtoskip is not None and ss(_email) == ss(emailtoskip):
                    continue # skip!
                
                if requireemail and not self.ValidEmailAddress(_email):
                    continue # skip!
                
                if format == 'email':
                    add = _email or _name
                    if add in all:
                        continue # skip!
                elif format == 'name':
                    add = _name or _email
                    if add in all:
                        continue # skip!
                else:
                    if _name and _email:
                        if format == 'both':
                            if _email.lower() in appended_email_addresses:
                                continue # skip!
                            else:
                                add = "%s <%s>"%(_name, _email)
                                appended_email_addresses.append(_email.lower())
                                
                        else:
                            if _email.lower() in appended_email_addresses:
                                continue # skip!
                            else:
                                add = self.ShowNameEmail(_name, _email, highlight=0)
                                appended_email_addresses.append(_email.lower())
                    elif _name:
                        if format == 'both':
                            add = _name
                        else:
                            add = _name
                    elif _email:
                        if _email.lower() in appended_email_addresses:
                            continue # skip!
                        else:
                            if format == 'both':
                                add = _email
                            else:
                                add = self.ShowNameEmail(_name, _email, highlight=0)
                            appended_email_addresses.append(_email.lower())

            if add and add not in all:
                all.append(add)
                
        return all
            
    
    
    def getAllNotifications(self):
        """ Go through all issues and find all notification objects """
        all = []
        for issue in self.getIssueObjects():
            all = all+issue.objectValues(NOTIFICATION_META_TYPE)
        return all

    def preParseEmailString(self, email_string, aslist=0, allnotifyables=1):
        """ wrapper around utils """
        if Utils.same_type(email_string, []):
            email_string = ', '.join(email_string)
        parsemethod = Utils.preParseEmailString
        all_notifyables = self.getNotifyables()
        if not allnotifyables:
            all_notifyables = []

        names2emails = {}
        for item in all_notifyables:
            email = item.getEmail()
            name = item.getName()
            names2emails[name] = email
            names2emails["%s, %s"%(name, email)] = email
            
        # add acl_users
        for iuf in self.superValues(ISSUEUSERFOLDER_METATYPE):
            for username, userdata in iuf.data.items():
                email = userdata.getEmail()
                names2emails[username] = email
                showname = "%s, %s"%(userdata.getFullname(), username)
                names2emails[showname] = email
                showname = "%s (%s)"%(userdata.getFullname(), username)
                names2emails[showname] = email
                
        all_groups = self.getNotifyableGroups()
        for group in all_groups:
            notifyables = self.getNotifyablesByGroup(group)
            their_email_addresses = [x.getEmail() for x in notifyables]
            names2emails['group: %s'%group.getTitle()] = their_email_addresses

        result = parsemethod(email_string, names2emails=names2emails,
                             aslist=aslist)
        return result


    ## Manager related

    def getManagerRoles(self):
        """ Return the roles that makes an IssueTracker Manager """
        return getattr(self, 'manager_roles', DEFAULT_MANAGER_ROLES)

    def hasManagerRole(self):
        """
            This method determines if the current user
            is allowed to do stuff that only the Zope manager is
            supposed to be able to do.
            Feel free to edit appropriatly to what suits you.
        """
        #user_roles = self.REQUEST.AUTHENTICATED_USER.getRoles()
        #user_roles = self.REQUEST.AUTHENTICATED_USER.getRolesInContext(self)
        user_roles = getSecurityManager().getUser().getRolesInContext(self)

        for role in self.getManagerRoles():
            if role in user_roles:
                return True
        # still here!
        return False
    
            

    ## Helpers to templates

    def getHeader(self):               
        """ Return which METAL header&footer to use """
        # Since we might be using CheckoutableTemplates and macro
        # templates are very special we are forced to do the following
        # magic to get the macro 'standard' from a potentially checked
        # out StandardHeader
        zodb_id = 'StandardHeader.zpt'
        template = getattr(self, zodb_id, self.StandardHeader)
        return template.macros['standard']
    
    # backwards compatability
#    StandardLook = StandardHeader

    def ManagerLink(self, shortlink=False, absolute_url=False):
        """ For the little hyperlink where you can login with """
        if shortlink:
            link = '/redirectlogin'
        else:
            root = self.getRoot()
            if absolute_url:
                link = root.absolute_url()+'/redirectlogin'
            else:
                link = root.relative_url()+'/redirectlogin'

        if absolute_url:
            came_from = self.absolute_url()+'/'
        else:
            came_from = self.relative_url()+'/'
            
        if self.meta_type == ISSUETRACKER_METATYPE:
            page = self.REQUEST.URL.split('/')[-1]
            if page in ('AddIssue','QuickAddIssue',
                        'ListIssues','CompleteList',
                        'User'):
                came_from += page
                
        rurl=random.randrange(100, 200)
        return "%s?came_from=%s&r=%s"%(link, came_from, rurl)
    
    def standard_html_header(self):
        """ to make it possible to use DTML objects here """
        breakword = '<!--METALbody-->'
        page = self.StandardHeader()
        return page[:page.find(breakword)]

    def standard_html_footer(self):
        """ to make it possible to use DTML objects here """
        breakword = '<!--METALbody-->'
        page = self.StandardHeader()
        return page[page.find(breakword)+len(breakword)+1:]

    def BatchedQueryString(self, batchdict={}, encode=False):
        """
        return QUERY_STRING but make sure stuff in
        the batchdict isn't duplicated.
        """
        request = self.REQUEST
        actionurl = self.ActionURL()
        if Utils.same_type(batchdict, 's') and batchdict=='all':
            #request.set('start', None)
            url = self.aurl(actionurl, {'show':'all'}, ignore='start')
        elif Utils.same_type(batchdict, 's') and batchdict.lower()=='none':
            url = self.aurl(actionurl, ignore=['start','show'])
        else:
            batchdict = self._Zero2None(batchdict)
            url = self.aurl(actionurl, batchdict)
        url = self._addQuerystring(url, encode=encode)
        return url
    

    def _Zero2None(self, dict):
        """ Replace all occurances of 0 (as tested int) to None """
        n_dict={}
        for key, value in dict.items():
            try:
                if int(value)==0:
                    n_dict[key]=None
                else:
                    n_dict[key]=value
            except:
                n_dict[key]=value
        return n_dict
    
    
    def rememberSavedfilterPersistently(self):
        """ return if the last saved filter should be saved persistently.
        (this means, in a cookie for `FILTERVALUER_EXPIRATION_DAYS` days)
        """
        issueuser = self.getIssueUser()
        default = False
        if issueuser:
            return issueuser.rememberSavedfilterPersistently(default=default)
        else:
            # look in cookies
            ckey = self.getCookiekey('remember_savedfilter_persistently')
            return Utils.niceboolean(self.get_cookie(ckey, default))

    def useAccessKeys(self):
        """ return if the interface should use Accesskeys """
        issueuser = self.getIssueUser()
        default = False
        if issueuser:
            return issueuser.useAccessKeys(default=default)
        else:
            # look in cookies
            ckey = self.getCookiekey('use_accesskeys')
            return Utils.niceboolean(self.get_cookie(ckey, default))
        
    def showNextActionIssues(self):
        """ return if the interface should show the 'Your next action issues'
        on the home page. """
        issueuser = self.getIssueUser()
        default = False
        if issueuser:
            return issueuser.showNextActionIssues(default=default)
        else:
            # look in cookies
            ckey = self.getCookiekey('show_nextactions')
            return Utils.niceboolean(self.get_cookie(ckey, default))
        

    def ShowNameEmail(self, fromname, email=None, hideme=None, highlight=1,
                      nolink=0, encode=0, angle_brackets=1):
        """ Show name and email depending on certain criterias """
        out = ''

        if not Utils.same_type(fromname, 's') and hasattr(fromname, 'meta_type'):
            # This is a very special case. The fromname isn't a name but instead
            # an issue user object. Enabling for this strange parameter is why
            # the 'email' parameter has a default None.
            if fromname.meta_type == ISSUEUSERFOLDER_METATYPE:
                email = fromname.getEmail()
                fromname = fromname.getFullname()

        if isinstance(fromname, str):
            # old way
            fromname = Utils.html_entity_fixer(self.safe_html_quote(fromname))
            fromname = self.safe_html_quote(fromname)
        else:
            # new way
            fromname = self.safe_html_quote(fromname.encode('ascii', 'xmlcharrefreplace'))
            
        email = Utils.html_quote(email)
        show_email = email
        
        if highlight:
            fromname = self.HighlightQ(fromname)
            #email = self.HighlightQ(email)
            show_email = self.HighlightQ(email)


        if not fromname and not email:
            name_email = NONAME_NOEMAIL
        elif not fromname:
            # Show only the email address
            if self.EncodeEmailDisplay():
                email = self.encodeEmailString(email)
            else:
                email = '<a href="mailto:%s">%s</a>'%(email, email)
            if angle_brackets:
                name_email ='&lt;%s&gt;'%email
            else:
                name_email = email
        elif not email:
            # only name was specified
            name_email = fromname
        else:
            # both were specified
            if self.EncodeEmailDisplay():
                name_email = self.encodeEmailString(email, fromname)
            else:
                name_email = '<a href="mailto:%s">%s</a>'%(email, fromname)
            if angle_brackets:
                name_email = '&lt;%s&gt;'%(name_email)

        if hideme is not None and hideme:
            out += NAME_EMAIL_HIDDEN 
            if self.hasManagerRole():
                out += "<br />" + name_email
        else:
            out += name_email

        return out

    
    def showFilterOptions(self, checkrequest=True):
        """ Determine if we want to display the filter options """
        request = self.REQUEST
        
        showkey = SHOW_FILTEROPTIONS_KEY
        rkey = 'ShowFilterOptions'
        if checkrequest and request.get(rkey) and int(request[rkey]):
            # Someone has chosen to show filter options
            return True

        for key in ('statuses','sections','urgencies','types',
                    'fromname','email'):
            if checkrequest and request.get('f-%s'%key):
                return True
            elif self.get_session('f-%s-show'%key) or self.get_session('f-%s-block'%key):
                
                return True

        return False

    def hasStoredFilter(self):
        """ Check if filter is stored in session """
        return self.showFilterOptions(checkrequest=False)

    
    def hasFilter(self):
        """ check if filter is being used at all """
        return self.showFilterOptions(checkrequest=True)
    
    
    def guessNewFiltername(self):
        """ pass """
        
        default = ""
        if self.hasFilter():
            name = ''

            # get filter setup
            filterlogic = self.getFilterlogic()

            def getFVal(key, zope=self, filterlogic=filterlogic):
                return zope.getFilterValue(key, filterlogic,
                                       request_only=True)

            f_statuses = getFVal('statuses')
            f_sections = getFVal('sections')
            f_urgencies = getFVal('urgencies')
            f_types = getFVal('types')
            f_fromname = getFVal('fromname')
            f_email = getFVal('email')            
            
            main_option = self.getFilterlogic()
            
            if main_option == 'show':
                start = _("Only ")
            else:
                start = _("Hide ")
                
            name = ""
            if f_statuses:
                name += ", ".join(f_statuses) + _(" issues ")
            if f_sections:
                name += _("in ") + ", ".join(f_sections) + " "
            if f_urgencies:
                name += _("that are ") + ", ".join(f_urgencies) + " "
            if f_types:
                name += _("of type ") + ", ".join(f_types) + " "
                
            if f_fromname and f_email:
                L = [f_fromname.strip(), f_email.strip()]
                name += _("by ") + ', '.join(L) + " "
            elif f_fromname:
                name += _("by ") + f_fromname.strip() + " "
            elif f_email:
                name += _("by ") + f_email.strip() + " "
                
            if name:
                return start + name.strip()
            else:
                return default
        else:
            return default
        
        
    def useFilterName(self, saved_filter=None):
        """ help return to the list page again but with the 'saved-filter' variable
        applied on the REQUEST. This method basically supports those people who use
        the Go button on the filter_options. The Go button is hidden by stylesheets
        plus that the accompanying select input redirects on change."""
        
        if saved_filter is None:
            saved_filter = self.REQUEST.get('saved-filter','')
        
        page = self.whichList()
        url = "%s/%s" % (self.getRootURL(), page)
        url = Utils.AddParam2URL(url, {'saved-filter':saved_filter})
        self.REQUEST.RESPONSE.redirect(url)
        
        
    def saveFilterOption(self, fname=None, REQUEST=None):
        """ here we store the current filter options into the instance
        and save the reference to it into the user. If the user is
        not an Issue User we'll have to store it as a cookie. """
        
        # 1. get all the values of the filter. when we do this
        # it will automatically pick up all the new values and store
        # them in a session.
        
        filterlogic = self.getFilterlogic()

        def getFVal(key, zope=self, filterlogic=filterlogic):
            return zope.getFilterValue(key, filterlogic,
                                       request_only=True)

        f_statuses = getFVal('statuses')
        f_sections = getFVal('sections')
        f_urgencies = getFVal('urgencies')
        f_types = getFVal('types')
        f_fromname = getFVal('fromname')
        f_email = getFVal('email')        
        
        
        _c_key = LAST_SAVEDFILTER_ID_COOKIEKEY
        _c_key = self.defineInstanceCookieKey(_c_key)
        
        # 2. Get a nice filter name
        if fname is None:
            fname = ""
        elif fname == 'null': # might come from javascript
            fname = ""
        fname = fname.strip()
        if not fname:
            fname = self.guessNewFiltername()
            if fname == '':
                # no filter settings to save from.
                # Perhaps the user manually reset each and every filter
                if self.has_session('last_savedfilter_id'):
                    self.delete_session('last_savedfilter_id')
                
                    if self.has_cookie(_c_key):
                        debug("Expire cookie %s" % _c_key, steps=1)
                        self.expire_cookie(_c_key)

                return 
    
        # 2.1. (optimisation)
        # if the last saved filter is the same as this one,
        # then don't bother saving it again
        
        last_savedfilter_id = self.get_session('last_savedfilter_id')
        if not last_savedfilter_id and self.rememberSavedfilterPersistently():
            # try fetching it via a cookie and transfer it to a session
            last_savedfilter_id = self.get_cookie(_c_key, None)
            if last_savedfilter_id:
                self.set_session('last_savedfilter_id', last_savedfilter_id)
                
        if last_savedfilter_id:
            last_saved_filter = self.getSavedFilterObject(last_savedfilter_id)
            if last_saved_filter.getTitle() == fname:
                return
        
        
        # 3.5. Load the basic properties
        issueuser = self.getIssueUser()
        zopeuser = self.getZopeUser()
        acl_adder = fromname = email = cookie_key = None
        if issueuser:
            acl_adder = issueuser.getIssueUserIdentifierString()
        elif zopeuser:
            path = '/'.join(zopeuser.getPhysicalPath())
            name = zopeuser.getUserName()
            acl_adder = ','.join([path, name])
        else:
            email_cookiekey = self.getCookiekey('email')
            name_cookiekey = self.getCookiekey('name')
            fromname = self.get_cookie(name_cookiekey)
            email = self.get_cookie(email_cookiekey)

        if not (acl_adder or fromname and email):
            # the user hasn't identified herself, then create a cookie key
            # and use that instead
            
            # save this in a cookie
            ckey = self.getCookiekey('saved-filters')
            ckey = self.defineInstanceCookieKey(ckey)
            if self.has_cookie(ckey):
                cookie_key = self.get_cookie(ckey)
            else:
                cookie_key = Utils.getRandomString()
                # attach this to the user
                self.set_cookie(ckey, cookie_key, 
                                days=FILTERVALUER_EXPIRATION_DAYS)
        
        valuer = self._getOrCreateFilterValuer(fname, acl_adder,
                           fromname=fromname, email=email,
                           cookie_key=cookie_key)
        
        
        # 3.4. 
        # to save time the next time, save that id that was created here
        self.set_session('last_savedfilter_id', valuer.getId())
        if self.rememberSavedfilterPersistently():
            #self.set_session('last_savedfilter_id', valuer.getId())
            key = LAST_SAVEDFILTER_ID_COOKIEKEY
            key = self.defineInstanceCookieKey(key)
            self.set_cookie(key, valuer.getId(),
                            days=FILTERVALUER_EXPIRATION_DAYS)
        
        
        
        # 3.5. Load all the values in for the filter
        valuer.set('filterlogic', filterlogic)
        valuer.set('statuses', f_statuses)
        valuer.set('sections', f_sections)
        valuer.set('urgencies', f_urgencies)
        valuer.set('types', f_types)
        valuer.set('fromname', f_fromname)
        valuer.set('email', f_email)
        
        
        if REQUEST is not None:
            # return the listing issues but now with this filter as
            # the chosen one
            page = REQUEST.get('page', self.whichList())
            page = ss(page)
            if page == 'listissues':
                page = '/ListIssues'
            elif page == 'completelist':
                page = '/CompleteList'
            else:
                raise "NotFound"
            url = self.getRootURL()+page
            url = Utils.AddParam2URL(url, {'saved-filter':id})
            REQUEST.RESPONSE.redirect(url)
        
        else:
            return id
        
        
    def _getOrCreateFilterValuer(self, filtername, acl_adder, fromname, email, 
                                 cookie_key):
        """ if we can't find a matching filtername already, create a new one """
        # 1. create a container if not already having one
        container = self._getFilterValueContainer()
        
        found_filters = self._findOldMatchingFilters(filtername, acl_adder,
                            adder_fromname=fromname, adder_email=email,
                            cookie_key=cookie_key)
                            
        if found_filters:
            found_filters = self.sortSequence(found_filters, (('mod_date',),))
            valuer = found_filters[0] # default sort is newest first
            
            # update the mod_date on the most recent one and...
            valuer.updateModDate()
            
            # ...delete the rest
            rest = found_filters[1:]
            if rest:
                ids = [x.getId() for x in rest]
                try:
                    container.manage_delObjects(ids)
                except:
                    for restid in ids:
                        try:
                            container.manage_delObjects([restid])
                        except:
                            LOG(self.__class__.__name__, INFO, 
                                "Could not delete valuerid %r" % restid,
                                error=sys.exc_info())
                        

            return valuer
        
        # 2. generate a suitable id
        if hasattr(container, 'id_counter'):
            id = getattr(container, 'id_counter') # this is an int
            container.manage_changeProperties({'id_counter':id + 1})
            id = str(id + 1)
        else:
            id = str(len(container.objectValues())+1)
            if hasattr(container, id):
                id = str(int(id) + 1)
                while hasattr(container, id):
                    id = str(int(id) + 1)
            container.manage_addProperty('id_counter', int(id)+1, 'int')
        
        # 3.3. create instance and register as object
        instance = FilterValuer(id, filtername)
        container._setObject(id, instance)
        valuer = container._getOb(id)        
        
        if acl_adder:
            valuer.set('acl_adder', acl_adder)
        if fromname:
            valuer.set('adder_fromname', fromname)
        if email:
            valuer.set('adder_email', email)
        if cookie_key:
            valuer.set('key', cookie_key)
        

        try:
            if len(container) > FILTERVALUEFOLDER_THRESHOLD_CLEANING:
                msg = self.CleanOldSavedFilters(user_excess_clean=1)
                LOG(self.__class__.__name__, INFO, str(msg))
        except:
            LOG(self.__class__.__name__, ERROR, "Failed to check for filtervaluer excess",
                error=sys.exc_info())
            try:
                err_log = self.error_log
                err_log.raising(sys.exc_info())
            except:
                pass                
        
        return valuer
    
        
    def _findOldMatchingFilters(self, filtername, acl_adder=None,
                                adder_fromname=None, adder_email=None,
                                cookie_key=None):
        """ delete filtervaluers that have this exact filtername, and match also
        either the acl_adder or adder_fromname and adder_email together. """
        if not (acl_adder or adder_fromname and adder_email or cookie_key):
            raise "Unmatchable", "must provide either acl_adder or "\
                                 "adder_fromname and adder_email or cookie_key"

        container = self._getFilterValueContainer()
        finds = []
        for filtervaluer in container.objectValues(FILTEROPTION_METATYPE):
            if filtervaluer.getTitle() == filtername:
                if acl_adder and filtervaluer.acl_adder == acl_adder:
                    finds.append(filtervaluer)
                elif cookie_key and filtervaluer.getKey() == cookie_key:
                    finds.append(filtervaluer)
                else: # match by fromname and email
                    fn = filtervaluer.adder_fromname
                    fe = filtervaluer.adder_email
                    if fn == adder_fromname and fe == adder_email:
                        finds.append(filtervaluer)
                            
        return finds
    
    def _getFilterValueContainer(self):
        """ return a BTreeFolder2 or a folder object where we can
        save all the filter value objects """
        folderid = FILTERVALUEFOLDER_ID
        root = self.getRoot()
        if hasattr(root, folderid):
            return getattr(root, folderid)
        else:
            if self.manage_canUseBTreeFolder():
                _adder = root.manage_addProduct['BTreeFolder2'].manage_addBTreeFolder
            else:
                _adder = root.manage_addFolder
            _adder(folderid)
            return getattr(root, folderid)
        
    def _implodeFilterValueContainerIfPossible(self):
        """ delete the save-filters container if it's empty """
        container = self._getFilterValueContainer()
        if len(container) == 0:
            objid = container.getId()
            assert objid == FILTERVALUEFOLDER_ID
            parent = aq_parent(aq_inner(container))
            parent.manage_delObjects([objid])
            return True
        return False
        
        
    def hasSavedFilterObject(self, objectid):
        """ return if there is an object like this """
        # do we have a container?
        if hasattr(self.getRoot(), FILTERVALUEFOLDER_ID):
            try:
                return hasattr(self._getFilterValueContainer(), objectid)
            except:
                return False
        else:
            return False
        
    def getSavedFilterObject(self, objectid):
        """ return the filtervaluer object """
        return getattr(self._getFilterValueContainer(), objectid)
    
    def getMySavedFilters(self, howmany=10):
        """ return an list of filtervaluer objects that belongs
        to the current user """
        folderid = FILTERVALUEFOLDER_ID
        root = self.getRoot()
        if not hasattr(root, folderid):
            return []
        
        try:
            container = self._getFilterValueContainer()
            all = container.objectValues(FILTEROPTION_METATYPE)
        except:
            try:
                err_log = self.error_log
                err_log.raising(sys.exc_info())
            except:
                pass            
            all = []
        mine = []
        if all:
            issueuser = self.getIssueUser()
            zopeuser = self.getZopeUser()
            acl_adder = fromname = email = key = None
            if issueuser:
                acl_adder = issueuser.getIssueUserIdentifierString()
            elif zopeuser:
                path = '/'.join(zopeuser.getPhysicalPath())
                name = zopeuser.getUserName()
                acl_adder = ','.join([path, name])
            
            if not issueuser:
                email_cookiekey = self.getCookiekey('email')
                name_cookiekey = self.getCookiekey('name')
                key = self.getCookiekey('saved-filters')
                key = self.defineInstanceCookieKey(key)
                
                fromname = self.get_cookie(name_cookiekey)
                email = self.get_cookie(email_cookiekey)
                key = self.get_cookie(key)

            for each in all:
                if acl_adder is not None and acl_adder == each.acl_adder:
                    mine.append(each)
                elif fromname and email and fromname == each.adder_fromname and \
                           email == each.adder_email:
                    mine.append(each)
                elif key and each.getKey() == key:
                    mine.append(each)

        if howmany:
            mine = mine[:howmany]
            
        # sort them by add_date
        mine = self.sortSequence(mine, (('mod_date',),))
        mine.reverse()
        
        return mine

    def getCurrentlyUsedSavedFilter(self, request_only=True):
        """ look for saved-filter key in request or in session """
        rkey = 'saved-filter'
        request = self.REQUEST
        if request_only:
            return request.get(rkey)
        else:
            return request.get(rkey, self.get_session('last_savedfilter_id'))
        

    def HighlightQ(self, text, q=None, highlight_html=None, highlight_digits=False):
        """ Highlight a piece of a text from q """
        _checker = lambda p: p.find('ListIssues') + p.find('CompleteList') > -2
        
        if highlight_html is None:
            highlight_html = '<span class="q_highlight">%s</span>'
            
        if q is None:
            # then look for it in REQUEST
            q = self.REQUEST.get('q',None)
            current_page = self.REQUEST.URL
            list_or_complete = _checker(current_page)
            if q is None and not list_or_complete:
                # look at the HTTP_REFERER
                referer = self.REQUEST.get('HTTP_REFERER','')
                if referer and _checker(referer):
                    try:
                        querystring = referer.split('?')[1]
                        qs = cgi.parse_qs(querystring)
                        if qs.has_key('q'):
                            q = qs.get('q')[0]
                            if q:
                                # so that consecutive calls to HighlightQ()
                                # doesn't need to dig it out again
                                self.REQUEST.set('q',q)
                    except IndexError:
                        pass
                       
                        
        if q is None:
            return text
        else:
            
            transtab = string.maketrans('/ ','_ ')
            q=string.translate(q, transtab, '?&!;<=>*#[]{}')
            
            highlightfunction = lambda x: highlight_html % x
            
            for q in self.QasList(q):
                if highlight_digits and q.isdigit():
                    #text = re.sub('(%s)'% re.escape(q), highlightfunction(r'\1'), text)
                    text = Utils.highlightCarefully(q, text, highlightfunction,
                                                    word_boundary=False)
                #r=re.compile(r'\b(%s)\b' % re.escape(q), re.I)
                #text = r.sub(highlightfunction(r'\1'), text)
                text = Utils.highlightCarefully(q, text, highlightfunction)

            return text
        
    def _text_replace(self, text, old, new):
        """ A custom string replace that doesn't have choke on tags.
        Don't do string replace on tags basically."""
        t=[]
        for part in text.split('<'):
            if part.find('>')>-1:
                t.append('<%s>'%part[0:part.find('>')])
                t.append(part[part.find('>')+1:].replace(old, new))
            else:
                t.append(part.replace(old,new))
        return ''.join(t)        

    def _getrandstr(self,l=5):
        """ """
        pool="0123456789"
        s=''
        for i in range(l):
            s='%s%s'%(s,random.choice(list(pool)))
        return s


    def colorizeThreadChange(self, title):
        """ Make "Changed status from Open to...
            to "Changed status from <span style="color:red;">Open</span> to...
        """
        highlight_html = '<span class="cth'
        highlight_html += r'">\1</span>'

        statuses = self.getStatuses()
        assignment_statuses = ['Rejected','Accepted','Reassigned']
        combined = statuses + assignment_statuses
        regex = regex = '|'.join([r'\b%s\b'%x for x in combined])
        regex = '(%s)'%regex
        status_reg = re.compile(regex, re.I)
        title = re.sub(status_reg, highlight_html, title)

        return title

    
    def QasList(self, q):
        """ q is a string that might contain 'and' and/or 'or'.
        Remove that and make it a list. """
        r=re.compile(r"\band\b|\bor\b", re.IGNORECASE)
        return r.sub("", q).split()

    def HeadingLinks(self, display, sortname, default=0, inverted=0,
                     sortinfo=None):
        """Returns a hyperlink that can
           be used for resorting the listing.
           'inverted' means that it's default behaviour is not ASC,
           it's DESC.
        """
        request = self.REQUEST
        querystring = request.QUERY_STRING
        
        if sortinfo is None:
            sortorder, reverse = self.getSortOrder(self.REQUEST)
        else:
            sortorder, reverse = sortinfo
            
        if sortorder == sortname:
            # have sorted by this, just let them reverse
            if reverse:
                descending = self.www['descarrow.gif'].tag(hspace=2,
                                                alt="Descending order")
                ps = {'sortorder':sortname, 'reverse':None}
                url = self.aurl(request.URL, ps)
                url = self._addQuerystring(url)
                url = self.relative_url(url)
                return '<a href="%s" title="%s %s">%s</a>%s'\
                       % (url, SORT_BY, display, display, descending)
            else:
                ascending = self.www['ascarrow.gif'].tag(hspace=2,
                                                 alt="Ascending order")
                ps = {'sortorder':sortname, 'reverse':'true'}
                url = self.aurl(request.URL, ps)
                url = self._addQuerystring(url)
                url = self.relative_url(url)
                return '<a href="%s" title="%s">%s</a>%s'\
                       % (url, SORT_REVERSE, display, ascending)
        else:
            if 0:#startreversed:
                ps = {'sortorder':sortname, 'reverse':True}
                url = self.aurl(request.URL, ps)
                url = self._addQuerystring(url)
                url = self.relative_url(url)
                return '<a href="%s" title="%s %s">%s</a>'\
                   % (url, SORT_BY, display, display )
            else:
                ps = {'sortorder':sortname, 'reverse':None}
                url = self.aurl(request.URL, ps)
                url = self._addQuerystring(url)
                url = self.relative_url(url)
                return '<a href="%s" title="%s %s">%s</a>' \
                   % (url, SORT_BY, display, display )

    def _addQuerystring(self, url, encode=True):
        """ Add REQUEST querystring """
        querystring = self.REQUEST.get('QUERY_STRING','')
        if querystring is not None and querystring.strip()!='':
            if encode:
                url = "%s?%s"%(url, querystring.replace('&','&amp;'))
            else:
                url = "%s?%s"%(url, querystring)
        return url

    

    ## Form submission helpers

    def has_key_special(self, name, shorten=0):
        """
        Normally you would do REQUEST.has_key('IssueAction')
        but if an imagebutton is used you'll find that you have
        REQUEST['IssueAction.y'] and REQUEST['IssueAction.x']
        But the result should be the same.
        """
        request = self.REQUEST
        if request.has_key(name):
            return True
        elif request.has_key('%s.y'%name) and request.has_key('%s.x'%name):
            return True
        elif shorten:
            for key in request.keys():
                if key[:len(name)]==name:
                    return True
            return False
        else:
            return False

    def get_special_key(self, name):
        """
        Normally you would do REQUEST.has_key('IssueAction')
        but if an imagebutton is used you'll find that you have
        REQUEST['IssueAction.y'] and REQUEST['IssueAction.x']
        But the result should be the same.
        """
        try:
            return self.REQUEST[name]
        except KeyError:
            try:
                return self.REQUEST['%s.x'%name]
            except:
                raise KeyError, name


    ## Error related
            
    def ShowSubmitError(self, options, id, linebreak=0):
        """ errordict is a dictionary of errors """
        s = ''
        errordict = options.get('SubmitError',{})
        
        if errordict and errordict.has_key(id):
            s = errordict.get(id)

        if s and linebreak:
            s += '<br />'
            
        return s
    

    ## Deleting an issue

    security.declareProtected(DeleteIssues, 'DeleteIssue')
    def DeleteIssue(self):
        """ Delete an Issue from the IssueTracker instance """
        request = self.REQUEST

        if request.has_key('issueID') and self.hasManagerRole():
            container = self._getIssueContainer()
            issue = getattr(container, request['issueID'])
            issue.unindex_object()
            
            container.manage_delObjects(request['issueID'])

            # delete all notifications about this Issue
            del_notify_ids = []
            for notifyobject in self.objectValues('Issue Notification'):
                if notifyobject.issueID == request['issueID']:
                    del_notify_ids.append(notifyobject.id)
          
            self.manage_delObjects(del_notify_ids)

            listpage = '/%s'%self.whichList()
            request.RESPONSE.redirect(request.URL1+listpage)
        else:
            msg = "The issueID could not be found in the REQUEST"
            raise "IssueTrackerError", msg


    ## Sys admin

    security.declareProtected('Access IssueTracker', 'redirectlogin')
    def redirectlogin(self, came_from=None):
        """ this method is protected so that when viewed the user
        will have been logged in. """
        if not came_from:
            came_from = self.getRootURL() + '/'
        elif came_from.startswith('/'):
            came_from = self.REQUEST.BASE0 + came_from

        issueuser = self.getIssueUser()
        if issueuser and issueuser.mustChangePassword():
            url = self.getRootURL()+'/User_must_change_password'
            params = {'cf':came_from}
            came_from = Utils.AddParam2URL(url, params)
            
            
        self.REQUEST.RESPONSE.redirect(came_from)        

        
    def StopCache(self):
        """ Maybe we should set some cachepreventing headers """
        if self.doStopCache():
            response = self.REQUEST.RESPONSE
            now = DateTime().toZone('GMT').rfc822()
            response.setHeader('Expires', now)
            response.setHeader('Cache-Control','public,max-age=0')
            response.setHeader('Pragma','no-cache') # for HTTP 1.0

            
    def doCache(self, hours=10):
        """ set cache headers on this request if not in debug mode """
        if not self.doDebug() and hours > 0:
            response = self.REQUEST.RESPONSE
            now = DateTime()
            then = now+int(hours/24.0)
            response.setHeader('Expires',then.rfc822())
            response.setHeader('Cache-Control', 'public,max-age=%d' % int(3600*hours))

            
    def sendEmail(self, msg, to, fr, subject, swallowerrors=False, headers={}):
        """ Attempt to send emails un protectedly. Return true if 
        managed to send it, false otherwise. (except when 'swallowerrors'
        is true where errors can be raised) """
        mailhost = self._findMailHost()
        
        headers_clean={}
        for key, value in headers.items():
            if isinstance(key, str) and key.strip():
                key = key.strip()
                if key.endswith(':'):
                    key = key[:-1]
                value = str(value).strip()
                headers_clean[key] = value
            
        try:
            if hasattr(mailhost, 'secureSend'):
                # Using improved SecureMailHost
                mailhost.secureSend(msg, to, fr, subject, **headers_clean)
            else:
                # since we're changing the code here, the creation of a body
                # is done here in the sendEmail() function instead. If the msg
                # is already made into a body, then don't proceed.
                if msg.find('To: %s' % to) + msg.find('From: %s' % fr) > -2:
                    body = msg
                else:
                    merge = ["From: %s"%fr,
                             "To: %s"%to,
                             "Subject: %s"%subject]
                    for key, value in headers_clean.items():
                        merge.append('%s: %s' % (key, value))
                             
                    merge.extend(["", msg])
                    body = '\r\n'.join(merge)
                
                mailhost.send(body, to, fr, subject)
                debug(body)
            return True
        except:
            debug("Failed to send email")
            debug(msg, steps=4)
            typ, val, tb = sys.exc_info()
            if swallowerrors:
                try:
                    err_log = self.error_log
                    err_log.raising(sys.exc_info())
                except:
                    pass                
                _classname = self.__class__.__name__
                _methodname = inspect.stack()[1][3]
                LOG("%s.%s"%(_classname, _methodname), ERROR,
                    'Could not send email to %s'%to,
                    error=sys.exc_info())
                return False
            else:
                raise typ, val
            

    def sendEmail(self, msg, to, fr, subject, swallowerrors=False, headers={}):
        """ this is the new sendEmail that works much better but with Unicode instead
        """
        if 1:#try:
            header_charset = 'ISO-8859-1'
            #header_charset = UNICODE_ENCODING
            # We must choose the body charset manually
                
            for body_charset in 'US-ASCII', 'ISO-8859-1', 'UTF-8', 'LATIN-1':
                try:
                    msg.encode(body_charset)
                except UnicodeError:
                    pass
                else:
                    break
            #body_charset = UNICODE_ENCODING
                
            # Split real name (which is optional) and email address parts
            fr_name, fr_addr = parseaddr(fr)
            to_name, to_addr = parseaddr(to)
            
            # Make sure email addresses do not contain non-ASCII characters
            fr_addr = fr_addr.encode('ascii')
            to_addr = to_addr.encode('ascii')            
            
            # We must always pass Unicode strings to Header, otherwise it will
            # use RFC 2047 encoding even on plain ASCII strings.
            fr_name = str(Header(unicode(fr_name), header_charset))
            to_name = str(Header(unicode(to_name), header_charset))
            
            headers_clean={}
            for key, value in headers.items():
                if isinstance(key, str) and key.strip():
                    key = key.strip()
                    if key.endswith(':'):
                        key = key[:-1]
                    value = str(value).strip()
                headers_clean[key] = value
            
            # Create the message ('plain' stands for Content-Type: text/plain)
            #print repr(msg)
            try:
                msg_encoded = msg.encode(body_charset)
                #print "\t1", repr(msg_encoded)
            except UnicodeDecodeError:
                if isinstance(msg, str):
                    try:
                        msg_encoded = unicode(msg, body_charset).encode(body_charset)
                        #print "\t\t2", repr(msg_encoded)
                    except UnicodeDecodeError:
                        logger.warn("Unable to encode msg (type=%r, body_charset=%s)" %\
                            (type(msg), body_charset),
                            exc_info=True)
                        msg_encoded = Utils.internationalizeID(msg)
                        
                else:
                    logger.warn("Unable to encode msg (type=%r, body_charset=%s)" %\
                            (type(msg), body_charset),
                            exc_info=True)
                    msg_encoded = Utils.internationalizeID(msg)
                    
            message = MIMEText(msg_encoded, 'plain', body_charset)
            message['From'] = formataddr((fr_name, fr_addr))
            message['To'] = formataddr((to_name, to_addr))
            message['Subject'] = Header(unicode(subject), header_charset)
            for k, v in headers_clean.items():
                message[k] = Header(unicode(v), header_charset)
            
            mailhost = self._findMailHost()
            # We like to do our own (more unicode sensitive) munging of headers and 
            # stuff but like to use the mailhost to do the actual network sending.
            mailhost._send(fr, to, message.as_string())
            
            return True
        
        else:#except:
            debug("Failed to send email")
            debug(msg, steps=4)
            typ, val, tb = sys.exc_info()
            if swallowerrors:
                try:
                    err_log = self.error_log
                    err_log.raising(sys.exc_info())
                except:
                    pass                
                _classname = self.__class__.__name__
                _methodname = inspect.stack()[1][3]
                LOG("%s.%s"%(_classname, _methodname), ERROR,
                    'Could not send email to %s'%to,
                    error=sys.exc_info())
                return False
            else:
                raise typ, val
            
    def _findMailHost(self):
        """ find a suitable MailHost object and return it. """
        # root instance object of issuetracker
        root = self.getRoot() 
        
        # root instance object but without deeper acquisition
        rootbase = getattr(root, 'aq_base', root) 
        
        ## Notice the order of this if-statement.
        
        # 1. 'MailHost' explicitly in the issuetrackerroot
        # (would fail if the MailHost is defined "deeper")
        if hasattr(rootbase, 'MailHost'):
            mailhost = self.MailHost
            
        # 2. 'SecureMailHost' explicitly in the issuetrackerroot
        # (would fail if the SecureMailHost is defined "deeper")
        elif hasattr(rootbase, 'SecureMailHost'):
            mailhost = self.SecureMailHost
            
        # 3. Any 'MailHost' in acquisition
        elif hasattr(self, 'MailHost'):
            mailhost = self.MailHost
            
        # 4. Any 'SecureMailHost' in acquisition
        elif hasattr(self, 'SecureMailHost'):
            mailhost = self.SecureMailHost
        
        else: # desperate search
            all_mailhosts = self.superValues(['Secure Mail Host', 'Mail Host'])
            if all_mailhosts:
                mailhost = all_mailhosts[0] # first one
            else:
                raise "AttributeError", "MailHost object not found"
            
        return mailhost
        
                

    ##
    ## Listing issues
    ##
    
    def searchWithOR(self, q=None):
        """ return true if there is a search and if that search isn't
        already "orified" :) """
        if q is None:
            request = self.REQUEST
            q = request.get('q')
        
        if q:
            if str(q).lower().find(' or ') == -1:
                terms_list = Utils.splitTerms(q)
                if len(terms_list) > 1:
                    return " or ".join(terms_list)
        
        return False
        

    def useFilterInSearch(self):
        """ default is to use filter in search, but first check if there's
        something in session. """
        key = USE_FILTER_IN_SEARCH_SESSION_KEY
        default = False
        if self.REQUEST.has_key('filter_in_search'):
            filter_in_search = self.REQUEST.get('filter_in_search')
            try:
                return not not int(filter_in_search)
            except ValueError:
                return not not filter_in_search
        else:
            return self.get_session(key, default)
        
    
    def ListIssuesFiltered(self, q=None, **kw):
        """ wrapper around _ListIssuesFiltered() that prepares a search
        if REQUEST holds 'q'
        """
        
        request = self.REQUEST
        q_orig = q
        
        if q is None and request.get('q','').strip():
            q = q_orig = request.get('q').strip()
            transtab = string.maketrans('/ ','_ ')
            q = string.translate(q, transtab, '?&!;<=>*#[]{}')
            ##q=q.replace('%','*') # allow both wildcards # needs thought
            
        i = None
        if request.has_key('i'):
            # user filtering
            welcomed_i = ('Added','FollowedUp','Assigned','Subscribed')
            welcomed_i = [ss(x) for x in welcomed_i]
            if ss(request.get('i')) in welcomed_i:
                i = request.get('i')
                
        report = None
        if request.has_key('report'):
            # check that the report script exists
            container = self.getReportsContainer()
            if hasattr(container, request.get('report')):
                report = getattr(container, request.get('report'))
            else:
                # try case insensitivity
                lowercase_key = str(request.get('report')).lower().strip()
                for scriptid, scriptobject in container._getAllScriptItems():
                    if scriptid.lower() == lowercase_key:
                        report = scriptobject
                        request.set('report', scriptid)
                        break

        if request.has_key('filter_in_search'):
            filter_in_search = request.get('filter_in_search')
        elif request.has_key('q'):
            filter_in_search = False
        else:
            filter_in_search = True
            
        try:
            filter_in_search = not not int(filter_in_search)
        except ValueError:
            filter_in_search = not not filter_in_search
            
        # remember this
        self.set_session(USE_FILTER_IN_SEARCH_SESSION_KEY, filter_in_search)
        
        if q is not None and q_orig.startswith('#') and q in self.getIssueIds():
            # q was like '#00123', just go to the issue
            response = request.RESPONSE
            url = self.getIssueObject(q).absolute_url()
            response.redirect(url, lock=1)
            return []
        
        elif q is not None and len(q.split(',')) > 1 and self._validIssueIDList(q):
            issue_ids = self._splitIssueIDList(q)
            seq = []
            for issue_id in issue_ids:
                seq.append(self.getIssueObject(issue_id))
            
        elif q is not None:
            # Use catalog to search
            try:
                seq = self._searchCatalog(q, search_only_on=request.get('search_only_on'))
            except ParseError, msg:
                request.set('SearchError', msg)
                seq = []
            except:
                try:
                    err_log = self.error_log
                    err_log.raising(sys.exc_info())
                except:
                    pass                                
                seq = []

            # searched and found one?
            if len(seq) == 1 and not filter_in_search:
                # then redirect
                response = request.RESPONSE
                url = seq[0].absolute_url()
                params = {}
                
                # So, only one issue has been found. We'll redirect there.
                # Now it's just a question of whether we'll include the searchterm
                # they used or if we're just going to go there. 
                # We'll just go there if the searchterm was a issuenumber but if it
                # wasn't then include the search term in the redirect
                if not str(q).replace('#','').replace(self.issueprefix,'').isdigit():
                    params = {'q':q}
                url = Utils.AddParam2URL(url, params)
                response.redirect(url, lock=1)
                return []
                

        elif i is not None:
            # The source is by this user
            seq = self.getMyIssues(i)
            
        elif report is not None:
            seq = self._generateReport(report)
            self.RememberReportRun(report.getId(), len(seq))
            
        else:
            # We won't need the ZCatalog, we can use objectValues() which
            # is many times faster
            seq = self.getIssueObjects()
                                     

        if q_orig is not None:
            # Remember this searchterm
            self.RememberSearchTerm(q_orig, len(seq))

        skip_filter = kw.get('skip_filter', not filter_in_search)
        skip_sort = kw.get('skip_sort', False)

        # transfer some parameters over to request,
        # because that's how they are being fetched inside
        # _ListIssuesFiltered()
        if kw.has_key('sortorder'):
            request.set('sortorder', kw.get('sortorder'))
            
        if kw.has_key('keep_sortorder'):
            request.set('keep_sortorder', kw.get('keep_sortorder'))
            
        if kw.has_key('reverse'):
            request.set('reverse', kw.get('reverse'))
            
        return self._ListIssuesFiltered(seq, skip_filter=skip_filter,
                                        skip_sort=skip_sort)


    def _validIssueIDList(self, comma_delimited_string):
        """ return true or false, a wrapper around _splitIssueIDList() """
        return bool(self._splitIssueIDList(comma_delimited_string))
    
    def _splitIssueIDList(self, comma_delimited_string):
        """ return true if the 'comma_delimited_string' is a comma separated list
        of valid issue ids that can be found. 
        The format of the string might be like 
          '#0234, #0456' or
          '#234, #456' or
          '234,  456' or
          '0234, 0456' or
          any combination of each but nothing else.
        The issue formatting might correct for this issue tracker instance
        but the issue must still exist in the database.
        """
        parts = [x.strip() for x in comma_delimited_string.split(',')]
        assert len(parts) > 1, "String %r not comma separated" % comma_delimited_string
        
        zfill_length = self.randomid_length
        if self.issueprefix:
            _regex = '^(\d{1,%s}|\#\d{1,%s}|%s\d{1,%s)$'
            ok_issue_id = re.compile(_regex % (zfill_length, zfill_length, 
                                               self.issueprefix, zfill_length))
        else:
            _regex = '^(\d{1,%s}|\#\d{1,%s})$'
            ok_issue_id = re.compile(_regex % (zfill_length, zfill_length))
        
        all_issue_ids = self.getIssueIds()
        ok = []
        for part in parts:
            # this is an inversion of the regular expression test.
            # If there's nothing but the OK issue id pattern, then 
            # it's ok.
            if not ok_issue_id.sub('', part) and bool(ok_issue_id.findall(part)):
                part = part.replace('#','')
                part = string.zfill(part, zfill_length)
                if part in all_issue_ids:
                    ok.append(part)

        return ok
    
    def _generateReport(self, report):
        """ return a sequence of issues where each issues yields a true
        result when applied on the report script. """
        checked = []
        # XXX might want to use an iterator here
        for issue in self.getIssueObjects():
            if report(issue):
                checked.append(issue)

        report.setYieldCount(len(checked))
        return checked
    
    
    def _searchCatalog(self, q, search_only_on=None):
        """ return a sequence of issue objects by searching and possibly
        searching inside the threads. """
        request = self.REQUEST
        catalog = self.getCatalog()
        seq = []
        titleq = '*'+q+'*'

        # prepare the search result variables
        _exact_title_search = []
        _title_search = []
        _description_search = []
        _fromname_search = []
        _email_search = []
        
        if search_only_on:
            if isinstance(search_only_on, basestring):
                search_only_on = [search_only_on]
            search_only_on = [ss(s) for s in search_only_on]
        else:
            search_only_on = None

        # all the different searches
        catalogs = []
        
        if not search_only_on or 'title' in search_only_on:
            _exact_title_search = catalog.searchResults(title=q)
            catalogs += _exact_title_search
        
            _title_search = catalog.searchResults(title=titleq)
            catalogs += _title_search
        
        ss_q = ss(q)
        
        if ss_q in [ss(x) for x in self.statuses]:
            # find the correct case
            for each in self.statuses:
                if ss(each) == ss_q:
                    self._setSearchFilterWarning(status=each)
                    break
                
        elif ss_q in [ss(x) for x in self.sections_options]:
            # find the correct case
            for each in self.sections_options:
                if ss(each) == ss_q:
                    self._setSearchFilterWarning(section=each)
                    break
            
        elif ss_q in [ss(x) for x in self.urgencies]:
            # find the correct case
            for each in self.urgencies:
                if ss(each) == ss_q:
                    self._setSearchFilterWarning(urgency=each)
                    break
            
        elif ss_q in [ss(x) for x in self.types]:
            # find the correct case
            for each in self.types:
                if ss(each) == ss_q:
                    self._setSearchFilterWarning(type_=each)
                    break
                
        
        if len(catalogs) < self.default_batch_size:
            _description_search = catalog.searchResults(description=q)
            catalogs += _description_search
            
            # there now?
            if len(catalogs) < self.default_batch_size:
                # dig deeper
                _author_search = []
                if not search_only_on or 'fromname' in search_only_on:
                    _author_search.extend(catalog.searchResults(fromname=q))
                if not search_only_on or 'email' in search_only_on:
                    _author_search.extend(catalog.searchResults(email=q))
                catalogs += _author_search
                if len(_author_search) > 0:
                    # advise people to use the filter
                    msg = self._setSearchFilterWarning(author=q)

        # Now, also search on comment
        catalogs_threads = []
        if not search_only_on or 'comment' in search_only_on:
            catalogs_threads = catalog.searchResults(comment=q)
                            

        if len(catalogs)+len(catalogs_threads)==0:
            # nothing found, maybe user typed in an id
            _issue_objectids = self.getIssueIds()
            if q in _issue_objectids:
                object = getattr(self, q)
                return [object]
            elif string.zfill(q, self.randomid_length) in _issue_objectids:
                object = getattr(self, string.zfill(q, self.randomid_length))
                return [object]
            

        
        # these variables are used in the loop to avoid calling LOG()
        # for every bloody object that goes wrong
        _has_logged_about_NoneType = 0; _has_logged_about_metatype = 0
        _has_logged_about_Issue_metatype = 0
        
        # Convert our search result to a list of unique issue objects
        for brain in catalogs:
            object = brain.getObject()
            if getattr(object, 'meta_type','') != ISSUE_METATYPE:
                if not _has_logged_about_Issue_metatype:
                    _has_logged_about_Issue_metatype = 1
                    m = "%s has cataloged thread objects with titles. "
                    m = m % catalog.getId() 
                    m += "Have you done a manual update on the catalog? "
                    m += "Please press the Update Everything button under the "\
                         "Management tab in the Zope management interface."
                    LOG(self.__class__.__name__, WARNING, m)
                continue
            
            if object not in seq:
                seq.append(object)

        # Also, search the file attachments
        if len(q) >= 2:
            indexes = catalog._catalog.indexes
            if 'filenames' in indexes:
                _finder = self._searchByFilename
            else:
                import warnings
                warnings.warn("It appears you don't have the 'filenames' index in your ZCatalog. "\
                              "To enable much quicker searches, press the Update Everything "\
                              "button in the Zope management interface.",
                              DeprecationWarning)
                _finder = self._findby_filename
            
            for issue in _finder(q):
                if issue not in seq:
                    seq.append(issue)
                    
        first_thread_id = None
        
        for threadbrain in catalogs_threads:
            threadobject = threadbrain.getObject()
            if threadobject is None:
                if not _has_logged_about_NoneType:
                    _has_logged_about_NoneType = 1
                    m = "%s has references to Zope objects that do not exist. "
                    m = m%self.getCatalog().getId()
                    m += "Please press the Update Everything button under the "\
                         "Management tab in the Zope management interface."
                    LOG(self.__class__.__name__, WARNING, m)
                continue
            elif getattr(threadobject, 'meta_type', '') != ISSUETHREAD_METATYPE:
                if not _has_logged_about_metatype:
                    _has_logged_about_metatype = 1
                    m = "%s has references to Zope objects that are not of type %s. "
                    m = m%(self.getCatalog().getId(), ISSUETHREAD_METATYPE)
                    m += "Please press the Update Everything button under the "\
                         "Management tab in the Zope management interface."
                    LOG(self.__class__.__name__, WARNING, m)
                continue
            
            object = threadobject.aq_parent
            if object not in seq:
                if first_thread_id is None:
                    first_thread_id = object.getId()
                    request.set('FirstThreadResultId', first_thread_id)
                seq.append(object)
                        
        if self.searchWithOR(q) and search_only_on is None:
            for issue in self._searchCatalog(self.searchWithOR(q)):
                if issue not in seq:
                    seq.append(issue)
        
        return seq
        

    def _searchByFilename(self, q):
        """ Search all file attachments """
        sR = self.getCatalog().searchResults
        qparts = [ss(x) for x in q.split() if ss(x) not in ('and','or','not')]
        brains = sR(filenames=qparts)
        issues = []
        for brain in brains:
            obj = brain.getObject()
            if obj:
                if obj.meta_type == ISSUETHREAD_METATYPE:
                    issue = aq_parent(aq_inner(obj))
                else:
                    issue = obj
                if issue not in issues:
                    issues.append(issue)
        return issues
    
    def _findby_filename(self, q):
        """ Search all file attachments """
        q = q.lower()
        issues = []
        r = self.ZopeFind(self, obj_metatypes=['File'], search_sub=1)
        valid_meta_types = [ISSUE_METATYPE, ISSUETHREAD_METATYPE]
        for file in r:
            path, fileobject = file
            parent = fileobject.aq_parent
            
            if parent.meta_type in valid_meta_types and path.lower().find(q)>-1:
                if parent.meta_type == ISSUETHREAD_METATYPE:
                    issues.append(aq_parent(aq_inner(parent)))
                else:
                    issues.append(parent)
        return issues
    
    def _setSearchFilterWarning(self, author=None, status=None, section=None,
                                urgency=None, type_=None):
        """ put a HTML chunk in REQUEST about how the user can user the
        filter feature instead of search based on what they searched
        for. """
        msg = None
        
        url = self.getRootURL()+'/'+self.whichList()
        params = {'ShowFilterOptions':'1'}
        
        if author:
            msg = 'You can use the <a href="%s">filter options</a> to filter on people'
            if Utils.ValidEmailAddress(author):
                params['f-email'] = author
            else:
                params['f-fromname'] = author
            url = Utils.AddParam2URL(url, params)
            msg = msg%url
            
        elif section:
            msg = 'You can use the <a href="%s">filter options</a> to filter on sections'
            params['f-sections'] = section
            url = Utils.AddParam2URL(url, params)
            msg = msg%url
            
        elif status:
            msg = 'You can use the <a href="%s">filter options</a> to filter on status'
            params['f-statuses'] = status
            url = Utils.AddParam2URL(url, params)
            msg = msg%url
            
        elif urgency:
            msg = 'You can use the <a href="%s">filter options</a> to filter on different urgencies'
            params['f-urgencies'] = urgency
            url = Utils.AddParam2URL(url, params)
            msg = msg%url            
            
        elif type_:
            msg = 'You can use the <a href="%s">filter options</a> to filter on different types'
            params['f-types'] = type_
            url = Utils.AddParam2URL(url, params)
            msg = msg%url                        
            

        if msg:
            self.REQUEST.set('SearchFilterWarning', msg)
            


    def _ListIssuesFiltered(self, issues, skip_filter=False, skip_sort=False):
        """ Filter and sort """
        request = self.REQUEST

        # 1. Remember how many issues there are before filtering
        request.set('TotalNoIssues', len(issues))

        # 2. Filter issues
        if not skip_filter:
            issues = self._filterIssues(issues)
        
        # 3. Mandatory filter
        if not self.hasManagerRole():
            issues = [issue for issue in issues if not issue.IsConfidential()]

        # 4. Sort them
        if not skip_sort:
            issues = self._sortIssues(issues, request)

        # 5. and we're done!
        return issues


    def _filterIssues(self, issues):
        """ look for things that shouldn't appear or should only appear """

        # assume that we always save the current filter options
        _do_save_filter = True
        
        request = self.REQUEST
        
        _c_key = LAST_SAVEDFILTER_ID_COOKIEKEY
        _c_key = self.defineInstanceCookieKey(_c_key)
        
        #
        # o 'filteroptions' gets set if people press the 
        #   "Apply filter options" button on filter_options.zpt
        # o 'f-statuses' is from the Home page where you can clicl
        #   all the various statuses
        # o 'f-sections' is from the More statistics page
        #
        if request.get('filteroptions') or request.get('f-statuses') or \
          request.get('f-sections'):
            # they have applied some filter options
            
            # by default we want to save the filter for later
            _do_save_filter = True
            
            # Has this been overridden
            if request.has_key('remember-filterlogic'):
                _do_save_filter = Utils.niceboolean(request.get('remember-filterlogic'))
            
        elif request.get('saved-filter'):
            if self.hasSavedFilterObject(request.get('saved-filter')):
                filtervaluer = self.getSavedFilterObject(request.get('saved-filter'))
                filtervaluer.populateRequest(request)
                filtervaluer.incrementUsageCount()
                filtervaluer.updateModDate()
            
        elif self.has_session('last_savedfilter_id') or \
                self.has_cookie(_c_key) and self.rememberSavedfilterPersistently():
                    
            if not self.has_session('last_savedfilter_id'):
                # transfer from cooke to session
                last_savedfilter_id = self.get_cookie(_c_key, None)
                if last_savedfilter_id:
                    self.set_session('last_savedfilter_id', last_savedfilter_id)
                    
            saved_filter_id = request.get('saved-filter', 
                                  self.get_session('last_savedfilter_id'))
            if self.hasSavedFilterObject(saved_filter_id):
                filtervaluer = self.getSavedFilterObject(saved_filter_id)
                filtervaluer.populateRequest(request)
                
                # since we're using a selected saved-filter, there's
                # no need to save again
                _do_save_filter = False
                


        # get filter setup
        filterlogic = self.getFilterlogic()

        def getFVal(key, zope=self, filterlogic=filterlogic):
            return zope.getFilterValue(key, filterlogic,
                                       request_only=True,
                                       )
                                   
        
        f_statuses = getFVal('statuses')
        f_sections = getFVal('sections')
        f_urgencies = getFVal('urgencies')
        f_types = getFVal('types')
        f_fromname = getFVal('fromname')
        f_email = getFVal('email')
        
        
        if _do_save_filter:
            self.saveFilterOption()

        has_managerrole = self.hasManagerRole()
    
        checked = []
        if filterlogic == 'show' and \
               f_statuses is None and f_sections is None and \
               f_urgencies is None and f_types is None and \
               f_fromname is None and f_email is None:
            # Filter logic is to show only selected items but
            # nothing has been set so just return everything
            for issue in issues:
                if not issue.IsConfidential() or has_managerrole:
                    checked.append(issue)

            return checked
        
        
        if f_fromname:
            _maker = Utils.createStandaloneWordRegex
            f_fromname_regex = _maker(f_fromname)
        
        for issue in issues:
            if issue.IsConfidential() and not has_managerrole:
                continue
                
            if filterlogic == 'show':

                #do_add = true
                if f_statuses is not None:
                    if issue.status not in f_statuses:
                 #       do_add = False
                        continue
                    
                if f_sections is not None:
                    do_continue = 0
                    for subsection in f_sections:
                        if subsection in issue.sections:
                            # good!
                            do_continue = 1
                            break
                    if not do_continue:
                        continue
                        
                if f_urgencies is not None:
                    if issue.urgency not in f_urgencies:
                   #     checked.append(issue)
                        continue
                    
                if f_types is not None:
                    if issue.type not in f_types:
                    #    checked.append(issue)
                        continue

                if f_fromname is not None:
                    ##if f_fromname and ss(f_fromname) != ss(issue.getFromname()):
                    if f_fromname and not f_fromname_regex.findall(issue.getFromname()):
                     #   checked.append(issue)
                        continue

                if f_email is not None:
                    if f_email and ss(f_email) != ss(issue.getEmail()):
                      #  checked.append(issue)
                        continue

                    
                checked.append(issue)
                    
            else:
                # block things out then

                if f_statuses is not None:
                    if issue.status in f_statuses:
                        continue
                    
                if f_sections is not None:
                    do_continue = 0
                    for subsection in issue.sections:
                        if subsection in f_sections:
                            do_continue = 1
                            break
                    if do_continue:
                        continue
                    
                if f_urgencies is not None:
                    if issue.urgency in f_urgencies:
                        continue
                    
                if f_types is not None:
                    if issue.type in f_types:
                        continue

                if f_fromname: # conditional covers both None and ""
                    if f_fromname_regex.findall(issue.getFromname()):
                        continue
                    
                if f_email: # conditional covers both None and ""
                    if ss(f_email) == ss(issue.getEmail()):
                        continue
                # if none of the above skipped the loop, do this
                checked.append(issue)
        return checked
    
    security.declarePublic('forceFilterValuerUpdate')
    def forceFilterValuerUpdate(self):
        """ checks if there is a filtervaluer used in the session and if so, 
        do what _filterIssues() does, ie. to populate the REQUEST.
        (see larger comment in filter_options.zpt)
        """
        request = self.REQUEST
        if self.has_session('last_savedfilter_id'):
            saved_filter_id = request.get('saved-filter', self.get_session('last_savedfilter_id'))
            if self.hasSavedFilterObject(saved_filter_id):
                filtervaluer = self.getSavedFilterObject(saved_filter_id)
                filtervaluer.populateRequest(request)
        

    def _sortIssues(self, issues, request):
        """ inspect request for how we should sort and remember the sort order """

        session_key = 'sortorder'
        session_key_reverse = 'sortorder_reverse'

        if request.get('sortorder','').lower()=='search' and \
           request.get('q','').strip():
            return issues
        
        # If this is True, we remember the sortorder found this time
        # so that it can be used in the future.
        keep_sortorder = request.get('keep_sortorder', True)
        
        sortorder, sortorder_reverse = self.getSortOrder(request)

        # use special methods for some sorting
        if sortorder == 'urgency':
            issues = self._sortByUrgency(issues, not sortorder_reverse)
        elif sortorder == 'status':
            issues = self._sortByStatus(issues, sortorder_reverse)
        elif sortorder == 'type':
            issues = self._sortByType(issues, sortorder_reverse)
        else:
            do_reverse = sortorder_reverse
            
            # dates are naturally sorted in reverse
            if sortorder in ('modifydate', 'issuedate'):
                do_reverse = not do_reverse

            # define a dictionary of the renaming of sortorder keys.
            # For example, in REQUEST you can find 'sortorder=from'
            # but the actual attribute is called 'fromname' so it
            # should have been called 'sortorder=fromname'
            _translations = {'from':'fromname',
                             'changedate':'modifydate', # legacy
                              }
            
            issues = self._dosort(issues, 
                           _translations.get(sortorder, sortorder))
            if do_reverse:
                issues.reverse()

        if keep_sortorder:
            self.set_session(session_key, sortorder)
            self.set_session(session_key_reverse, sortorder_reverse)
            
        return issues
    
    

    def getSortOrder(self, request=None):
        """ return (sortorder, sortorder_reverse) based on request and 
        SESSION """
        
        if request is None:
            request = self.REQUEST

        session_key = 'sortorder'
        session_key_reverse = 'sortorder_reverse'

        #default_sortorder = 'modifydate'
        default_sortorder = self.getDefaultSortorder()
        default_sortorder_reverse = 0

        sortorder = request.get('sortorder',
                                self.get_session(session_key,
                                                default_sortorder))
        
        if request.has_key('reverse'):
            sortorder_reverse = request.get('reverse',
                                        self.get_session(session_key_reverse,
                                                        default_sortorder_reverse))
        else:
            # then it might be deliberatly left out
            if request.get('sortorder'):
                # if so, and there is no reverse set, assume it to be
                # False
                sortorder_reverse = False
                
            else:
                sortorder_reverse = self.get_session(session_key_reverse,
                                                     default_sortorder_reverse)
            request.set('reverse', sortorder_reverse)

        return sortorder, sortorder_reverse
                

    def _sortByStatus(self, issues, reverse=0):
        """ Use self.getStatuses() which is a humanly ordered list. """
        statuses = {}
        for issue in issues:
            if statuses.has_key(issue.status):
                statuses[issue.status].append(issue)
            else:
                statuses[issue.status] = [issue]

        # recreate the list
        issues = []

        default = 'modifydate'
        all_statuses = self.getStatuses()[:]
        if reverse:
            all_statuses.reverse()
            
        for status in all_statuses:
            if statuses.has_key(status):
                these = self._dosort(statuses[status], default)
                these.reverse()
                issues += these

        return issues


    def _sortByType(self, issues, reverse=0):
        """ Use self.types to sort the issues """
        types = {}
        for issue in issues:
            if types.has_key(issue.type):
                types[issue.type].append(issue)
            else:
                types[issue.type] = [issue]

        # recreate the list
        issues = []
                        
        default = 'modifydate'
        all_types = self.types[:]
        all_types.sort()

        if reverse:
            all_types.reverse()
   
        for type in all_types:
            if types.has_key(type):
                these = self._dosort(types[type], default)
                these.reverse()
                issues += these

        return issues
    
        
    def _sortByUrgency(self, issues, reverse=0):
        """ Use self.urgencies to sort the issues """
        urgencies = {}
        for issue in issues:
            if urgencies.has_key(issue.urgency):
                urgencies[issue.urgency].append(issue)
            else:
                urgencies[issue.urgency] = [issue]

        # recreate the list
        issues = []
                        
        default = 'modifydate'
        all_urgencies = self.urgencies[:]
        if reverse:
            all_urgencies.reverse()
   
        for urgency in all_urgencies:
            if urgencies.has_key(urgency):
                these = self._dosort(urgencies[urgency], default)
                these.reverse()
                issues += these

        return issues
    
        
    
##    def _getFilter(self, request):
##        """ Inspect 'request' for appropriate filter data and
##        return a dictionary of filters. """
##
##        key = FILTEROPTIONS_KEY
##
##        # Convert data from session into request
##        filteroptions = self.get_session(key, {})
##        for each in ['ignorestatuses','ignoresections', 'ignoreurgencies', 
##                     'ignoretypes','showfromname','showemail']:
##            if filteroptions.has_key(each):
##                request.set(each, filteroptions[each])
##
##        filter = {}
##        
##        # statuses
##        if request.has_key('ignorestatuses'):
##            filter['status'] = request.ignorestatuses
##        elif request.has_key('status'):
##            filter['status'] = self._pop_from_list(request['status'],
##                                                   self.getStatuses())
##        else:
##            filter['status'] = []
##            
##        # sections
##        if request.has_key('ignoresections'):
##            filter['sections'] = request.ignoresections
##        elif request.has_key('section'):
##            filter['sections'] = [request.section.strip()]
##        else:
##            filter['sections'] = []
##
##        # urgencies
##        if request.has_key('ignoreurgencies'):
##            filter['urgency'] = request.ignoreurgencies
##        elif request.has_key('urgency'):
##            filter['urgency'] = [request.urgency.strip()]
##        else:
##            filter['urgency'] = []
##            
##        # types
##        if request.has_key('ignoretypes'):
##            filter['type'] = request.ignoretypes
##        elif request.has_key('type'):
##            filter['type'] = [request.type.strip()]
##        else:
##            filter['type'] = []
##            
##        ## fromname
##        # Either a name to ignore or show only.
##        # It does not make sense to have both showfromname and ignorefromname
##        if request.has_key('showfromname') and \
##           request.showfromname <> self.when_ignore_word:
##                filter['showfromname'] = request.showfromname.strip()
##        elif request.has_key('ignorefromname') and \
##             request.ignorefromname <> self.when_ignore_word:
##            filter['ignorefromname'] = request.fromname.strip()
##
##        # email
##        if request.has_key('showemail') and \
##           request.showemail <> self.when_ignore_word:
##                filter['showemail'] = string.strip(request.showemail)
##        elif request.has_key('ignoreemail') and \
##           request.ignoreemail <> self.when_ignore_word:
##            filter['ignoreemail'] = request.email
##
##
##        # prepare for caseindependence
##        filter = Utils.fixDictofLists(filter)
##
##        return filter
    
##    def _pop_from_list(self, item, olist):
##        """ remove one item from a list """
##        nlist = []
##        for oitem in olist:
##            if item!=oitem:
##                nlist.append(oitem)
##        return nlist
    
##    def _filter_fromnameemail(self, issue, filter):
##        """ do the advanced filtering.
##            If filter has ignorefromname then reject this issue.
##            If filter has showfromname, then ignore this issue
##            if not == showfromname
##        """
##        ss = lambda x: x.strip().lower()
##        # if asked to be ingored return False
##        if filter.get('ignorefromname','') and \
##           ss(issue.fromname) == filter['ignorefromname']:
##            return False
##        elif filter.get('ignoreemail','') !='' and \
##           ss(issue.email) == filter['ignoreemail']:
##            return False
##        elif filter.get('showfromname','') !='' and \
##           ss(issue.fromname) != filter['showfromname']:
##            return False
##        elif filter.get('showemail','') !='' and \
##           ss(issue.email) != filter['showemail']:
##            return False
##        else:
##            # not trapped in anything
##            return true

    def _dosort(self, seq, key):
        """ do the actual sort """
        if not (Utils.same_type(key, ()) or Utils.same_type(key, [])):
            key = (key,)
        return sequence.sort(seq, (key,))
    
    def getBatchStart(self):
        """ return the batchstart value """
        try:
            return int(self.REQUEST.get('start',0))
        except:
            return False

    def getBatchSize(self, default=None, factor=None):
        """ return the batchsize value """
        request = self.REQUEST
        if request.get('show','')=='all':
            if factor:
                return int(1000*factor)
            else:
                return 1000
        if default is None:
            default = self.default_batch_size
        try:
            s = int(request.get('size', default))
            if factor:
                return int(s * factor)
            else:
                return s
        except:
            return 0


    ## Recent history related

    # Recent reports usage
    #
    
    def RememberReportRun(self, reportid, result):
        """ remember that we've run this report """
        request = self.REQUEST
        key = RECENTHISTORY_REPORTSKEY
        
        reports = self.get_session(key, [])
        as_dict = {'reportid': reportid, 'yield':result}
        
        #request.set('NotYetRecent'
        if as_dict not in reports:
            reports.insert(0, as_dict)
            if len(reports) > 25:
                # we don't want to store too much in the session
                # manager so limit it.
                reports = reports[:25]
                
            self.set_session(key, reports)

    def hasRecentReportRuns(self):
        """ return if any exist """
        key = RECENTHISTORY_REPORTSKEY
        return self.get_session(key, {}) != {}
    
    def getRecentReportRuns(self, length=None):
        """ return all the recently run reports if any """
        key = RECENTHISTORY_REPORTSKEY

        reports = self.get_session(key, {})
        if length:
            reports = reports[:length]
        return reports
    
    def getNiceRecentReportRuns(self, reports):
        """ return a hyperlink and bracket for each yield """
        reportscontainer = self.getReportsContainer()
        rooturl = self.getRootRelativeURL()
        items = []
        for reportrun in reports:
            reportid = reportrun['reportid']
            reportobject = getattr(reportscontainer, reportid, None)
            if not reportobject:
                continue
            href = "/%s/report-%s" % (self.whichList(), reportid)
            href = rooturl + href
            htmlchunk = '<a href="%s">%s</a> (%s found)'
            items.append(htmlchunk % (href, reportobject.title_or_id(), reportrun['yield']))
            
        return items
            
            
            
    
    # Recent history SearchTerm
    #

    def RememberSearchTerm(self, q, result):
        """ Stick this in a session variable """
        request = self.REQUEST
        key = RECENTHISTORY_SEARCHKEY
        
        searches = self.get_session(key, [])
        as_dict = {'q':unicodify(q), 'yield':result}
        
        request.set('NotYetRecent', as_dict)
        if as_dict not in searches:
            searches.insert(0, as_dict)
            #searches.append(as_dict)
            if len(searches)>25:
                # we don't want to store too much in the session
                # manager so limit it.
                searches = searches[:25]
            
            self.set_session(key, searches)


    def hasRecentSearchTerms(self):
        """ check if any exists """
        key = RECENTHISTORY_SEARCHKEY
        return self.get_session(key, {})!={}

    
    def getRecentSearchTerms(self, length=None):
        """ Return if any exists """
        key = RECENTHISTORY_SEARCHKEY
        searches = self.get_session(key, {})
        if length:
            searches = searches[:length]
        return searches

    def getNiceRecentSearchTerms(self, searches):
        """ return a hyperlink and a bracket with the yield """
        if self.thisInURL('CompleteList'):
            page = '/CompleteList'
        else:
            page = '/ListIssues'

        actionurl = self.getRootRelativeURL()+page
        actionurl = self.aurl(actionurl, {'sortorder':'search'})
        items = []
        for term in searches:
            q = term['q']
            if isinstance(q, str):
                q_quoted = Utils.url_quote_plus(q)
            else:
                try:
                    q_quoted = Utils.url_quote_plus(q.encode(UNICODE_ENCODING))
                except UnicodeEncodeError:
                    q_quoted = Utils.url_quote_plus(q.encode('ascii','xmlcharrefreplace'))
            href = actionurl + '?q=%s' % q_quoted
            if isinstance(q, str):
                # old way
                q_nice = Utils.html_entity_fixer(q)
            else:
                q_nice = q
            htmlchunk = '<a href="%s">%s</a> '%(href, q_nice)
            htmlchunk += '(%s found)'%term['yield']
            items.append(htmlchunk)

        return items


    # Recent history IssueVisit
    #


    def RememberIssueVisit(self, issueid):
        """ Remember that this issue has been visited """
        request = self.REQUEST

        key = RECENTHISTORY_ISSUEIDVISITKEY
        
        if not Utils.same_type(issueid, 's'):
            # we only want objects id
            issueid = issueid.getId()

        visits = self.get_session(key, [])
        added_issueids = self.getRecentAddedIssues(ids=1)
        if issueid not in visits and issueid not in added_issueids:
            visits.append(issueid)
            if len(visits)>20:
                # we don't want to store too much in the session
                # manager so limit it.
                visits.reverse()
                visits = visits[:20]
                visits.reverse()
            self.set_session(key, visits)
            request.set('NotYetRecent', issueid)


    def hasRecentIssueVisits(self):
        """ check if any exists """
        if self.getRecentIssueVisits():
            return True
        else:
            return False
            
    def getRecentIssueVisits(self, length=None):
        """ Return if any exists """
        request = self.REQUEST

        key = RECENTHISTORY_ISSUEIDVISITKEY
        try:
            issueids = self.get_session(key, [])
        except:
            issueids = []
        # make them objects
        issues=[]
        
        issuecontainer = self._getIssueContainer()
        for issueid in self.filterTooRecent(issueids):
            try:
                issues.append(getattr(issuecontainer, issueid))
            except:
                # Could have been deleted
                pass
        issues.reverse()

        if length:
            issues = issues[:length]
            
        return issues


    # Recent history AddedIssue
    #


    def RememberAddedIssue(self, issueid):
        """ Stick this in a session variable """
        request = self.REQUEST

        key = RECENTHISTORY_ADDISSUEIDKEY

        if not Utils.same_type(issueid, 's'):
            # we only want objects id
            issueid = issueid.getId()
        added = self.get_session(key, [])
        if issueid not in added:
            added.append(issueid)
            self.set_session(key, added)
            request.set('NotYetRecent', issueid)

    def hasRecentAddedIssues(self):
        """ check if any exists """
        return bool(self.getRecentAddedIssues())
            
    def getRecentAddedIssues(self, ids=0, length=None):
        """ Return if any exists """
        request = self.REQUEST

        key = RECENTHISTORY_ADDISSUEIDKEY

        issueids = self.get_session(key, [])
        # make them objects
        if ids:
            return issueids
        issues=[]
        issuecontainer = self._getIssueContainer()
        for issueid in self.filterTooRecent(issueids):
            try:
                issues.append(getattr(issuecontainer, issueid))
            except:
                # Could have been deleted
                pass
        issues.reverse()

        if length:
            return issues[:length]
        
        return issues
    
    # Combination of recent additions and recent views
    #
    
    def RememberRecentIssue(self, issueid, action):
        """ return that we've touched this issue """
        assert action in ('viewed','added')
        
        key = RECENTHISTORY_ISSUESKEY
        issues = self.get_session(key, [])
        as_dict = {'issueid': issueid, 'action':action}
        
        if issueid not in [each['issueid'] for each in issues]:
            issues.insert(0, as_dict)
            if len(issues) > 25:
                # keep the numbers small
                issues = issues[:25]
            self.set_session(key, issues)
        
    

    def hasRecentIssues(self, check_each=False):
        """ return true if have either recent issue visits or
        recent issue adds """
        return bool(self.getRecentIssues(check_each=check_each))
    
    def getRecentIssues(self, length=None, check_each=True):
        """ return a combination of added issues and visited issues """
        key = RECENTHISTORY_ISSUESKEY
        issues = self.get_session(key, [])
        if length:
            issues = issues[:length]
            
        if check_each:
            issuecontainer = self._getIssueContainer()
            checked = []
            for recentissue in issues:
                if hasattr(issuecontainer, recentissue['issueid']):
                    checked.append(recentissue)
            return checked
        else:
            return issues
    
    def getNiceRecentIssues(self, length=None):
        """ return a list of nicely formatted links to recent issues """
        issues = self.getRecentIssues(length=length)
        issuecontainer = self._getIssueContainer()
        show_with_ids = self.ShowIdWithTitle()
        items = []
        for recentissue in issues:
            chunks = []
            issueobject = getattr(issuecontainer, recentissue['issueid'], None)
            if not issueobject:
                continue
            if show_with_ids:
                chunks.append('<span class="id">#%s </span>' % issueobject.getId())
            chunks.append('<a href="%s">' % issueobject.absolute_url_path())
            chunks.append(self.displayBriefTitle(issueobject.getTitle()))
            if recentissue['action'] == 'added':
                chunks.append('</a> (added)')
            else:
                #chunks.append('</a> (viewed)')
                chunks.append('</a>')
                
            items.append(''.join(chunks))
            
        return items

    
    def hasRecentHistory(self):
        """ check if anything is stored """
        test1 = self.hasRecentIssues(check_each=True)
        test2 = self.hasRecentSearchTerms()
        test3 = self.hasRecentReportRuns()
        return test1 or test2 or test3


    def filterTooRecent(self, recenthistory):
        """ Go through list and take out something too new """
        request = self.REQUEST
        too_recent_element = None
        if request.get('NewIssue') == 'Submitted' and self.meta_type == ISSUE_METATYPE:
            too_recent_element = self.getId()
        n_recenthistory = []
        for each in recenthistory:
            if each != too_recent_element:
                n_recenthistory.append(each)
        return n_recenthistory

    ## Misc. methods


    def defineInstanceSessionKey(self, key):
        """ We use the default session key, but add to it for this
        issuetracker only. """
        id = self.getRoot().getId()
        return '%s-%s'%(key, id)

    def defineInstanceCookieKey(self, key):
        """ We use the default cookie key, but add to it for this
        issuetracker only. """
        # since that method is the same
        return self.defineInstanceSessionKey(key)
    

    ## POP3

    def getPOP3Accounts(self):
        """ return the POP3 Account objects """
        root = self.getPOP3Root(create_if_necessary=0)
        if root:
            return root.objectValues(POP3ACCOUNT_METATYPE)
        else:
            return []
    
        
    def SupportPOP3SSL(self):
        """ return true if we're able to support POP3_SSL """
        return _has_pop3_ssl
    
    security.declareProtected(VMS, 'createPOP3Account')
    def createPOP3Account(self, hostname, username,
                          password, portnr=110,
                          ssl=False,
                          delete_after=False, REQUEST=None):
        """ create POP3Account object """
        genid = "%s-%s"%(hostname, username)
        genid = genid.lower().strip()
        genid = Utils.safeId(genid, nospaces=1)

        try:
            portnr = int(portnr)
        except ValueError:
            raise "InvalidPort", "Port number must be a number"
        
        root = self.getPOP3Root()
        if hasattr(root, genid):
            raise "DuplicateId", "POP3Account already exists"
        
        pop3account = POP3Account(genid, hostname, username, password,
                                  portnr,
                                  ssl=ssl,
                                  delete_after=delete_after)
        
        root._setObject(genid, pop3account)
        pop3account = getattr(root, genid)
        
        if REQUEST is not None:
            url = self.getRootURL()+'/manage_POP3ManagementForm'
            url = '%s?manage_tabs_message=%s'%(url, 'POP3 Account created')
            response = self.REQUEST.RESPONSE
            response.redirect(url)
        
            
    security.declareProtected(VMS, 'editPOP3Account')
    def editPOP3Account(self, id, hostname=None, portnr=None, username=None, 
                        password=None, password_dummy=None, 
                        delete_after=False, REQUEST=None):
        """ old method name """
        import warnings 
        m = "editPOP3Account() is an old name. Use manage_editPOP3Account() instead",
        warnings.warn(m, DeprecationWarning, 2)
        return self.manage_editPOP3Account(id, hostname, portnr, username, 
                        password, password_dummy, 
                        delete_after, REQUEST)
                        
    
    def manage_hasFormatFlowedInstalled(self):
        """ return if formatflowed_decode is installed """
        return _has_formatflowed_
    
    security.declareProtected(VMS, 'manage_enableEmailRepliesSetting')
    def manage_enableEmailRepliesSetting(self, email, include_description_in_notifications=False,
                                  pop3accountid=None,
                                  REQUEST=None):
        """ set this email address to be the sitemaster_email """
        assert Utils.ValidEmailAddress(email), "Not a valid email address"
        found_email = None
        for pop3account in self.getPOP3Accounts():
            for ae in self.getAcceptingEmails(pop3account.getId()):
                if ss(ae.getEmailAddress()) == ss(email):
                    found_email = ae.getEmailAddress()
                    break
                
        if not found_email:
            if pop3accountid:
                pop3account = self.getPOP3Account(pop3accountid)
            else:
                pop3account = self.getPOP3Accounts()[0]
            
            self.createAcceptingEmail(pop3account.getId(), email, self.getDefaultSections(),
                                      self.getDefaultType(), self.getDefaultUrgency(),
                                      True)
            found_email = email
        
        self.sitemaster_email = found_email
        self.include_description_in_notifications = bool(include_description_in_notifications)
        
        if REQUEST is not None:
            # redirect back to POP3 management form
            url = self.getRootURL()+'/manage_POP3ManagementForm'
            params = {'manage_tabs_message':'Email replies made possible'}
            if pop3accountid:
                params['pop3accountid'] = pop3accountid
            url = Utils.AddParam2URL(url, params)
            response = self.REQUEST.RESPONSE
            response.redirect(url)
                    
        
    
    security.declareProtected(VMS, 'manage_hasEmailRepliesPossible')
    def manage_hasEmailRepliesPossible(self):
        """ true if the email address of one of the accepting emails is the same
        as the sitemaster_email. """
        sitemaster_email = ss(self.getSitemasterEmail())
        for pop3account in self.getPOP3Accounts():
            for acceptingemail in self.getAcceptingEmails(pop3account.getId()):
                if ss(acceptingemail.getEmailAddress()) == sitemaster_email:
                    return True
        return False
    
    security.declareProtected(VMS, 'manage_saveBlackWhitelist')
    def manage_saveBlackWhitelist(self, id, acceptingemail_id, 
                                  whitelist_emails, blacklist_emails, REQUEST=None):
        """ save blacklist and whitelists for an accepting email """
        account = self.getPOP3Account(id)
        acceptingemail = getattr(account, acceptingemail_id)
        
        if isinstance(whitelist_emails, basestring):
            whitelist_emails = [whitelist_emails]
        if isinstance(blacklist_emails, basestring):
            blacklist_emails = [blacklist_emails]
            
        # clean up the lists
        whitelist_emails = [x.strip() for x in whitelist_emails if x.strip()]
        blacklist_emails = [x.strip() for x in blacklist_emails if x.strip()]

        acceptingemail.editDetails(whitelist_emails=whitelist_emails,
                                   blacklist_emails=blacklist_emails)
                                   
            
        if REQUEST is not None:
            # redirect back to POP3 management form
            url = self.getRootURL()+'/manage_POP3ManagementForm'
            params = {'pop3accountid':id, 
                      'manage_tabs_message':"White-, blacklist saved"}
            url = Utils.AddParam2URL(url, params)
            REQUEST.RESPONSE.redirect(url)                                   
        
    
    security.declareProtected(VMS, 'manage_editPOP3Account')
    def manage_editPOP3Account(self, id, hostname=None, portnr=None, username=None, 
                        password=None, password_dummy=None, 
                        delete_after=False, ssl=False, REQUEST=None):
        """ edit POP3 account details """
        account = self.getPOP3Account(id)
        if hostname is not None and hostname.strip() != '':
            account.manage_editAccount(hostname=hostname.strip())
        if portnr is not None:
            try:
                portnr = int(portnr)
                account.manage_editAccount(portnr=portnr)
            except ValueError:
                raise "InvalidPort", "Port number must be a number"
        if username is not None and username.strip() != '':
            account.manage_editAccount(username=username.strip())
        if password is not None and password.strip() != password_dummy:
            account.manage_editAccount(password=password.strip())
            
        account.manage_editAccount(delete_after=bool(delete_after), ssl=bool(ssl))
            
        if REQUEST is not None:
            # redirect back to POP3 management form
            url = self.getRootURL()+'/manage_POP3ManagementForm'
            url = '%s?pop3accountid=%s'%(url, id)
            url = '%s&manage_tabs_message=%s'%(url, 'POP3 Account saved')
            response = self.REQUEST.RESPONSE
            response.redirect(url)
            
    def manage_testPOP3Account(self, accountid, REQUEST=None):
        """ do a welcome test on this POP3 account """
        account = self.getPOP3Account(accountid)
        
        if account.doSSL():
            connect_class = POP3_SSL
        else:
            connect_class = POP3
            
        try:
            M = connect_class(account.getHostname(), port=account.getPort())
            M.user(account.getUsername())
            M.pass_(account._password)
            
            result = M.welcome
            try:
                if result.find('OK') > -1:
                    result = result.strip() + '\n(# messages: %s)' % len(M.list()[1])
            except:
                pass
            M.quit()
        except poplib.error_proto, msg:
            result = msg
        except Exception, msg:
            result = str(msg)
            
        if REQUEST is not None:
            url = self.getRootURL() + '/manage_POP3ManagementForm'
            params = {'pop3accountid':accountid}
            params.update({'connectiontest_result':result})
            url = Utils.AddParam2URL(url, params)
            REQUEST.RESPONSE.redirect(url)
            
        else:
            return result
        
                    
    security.declareProtected('View management screens','createAcceptingEmail')
    def createAcceptingEmail(self, id, email_address, defaultsections=None, 
                             default_type=None, default_urgency=None,
                             send_confirm=False, reveal_issue_url=False,
                             REQUEST=None):
        """ create accepting email objet in this account """
        account = self.getPOP3Account(id)
        if defaultsections is None:
            defaultsections = self.defaultsections
        if default_type is None:
            default_type = self.default_type
        if default_urgency is None:
            default_urgency = self.default_urgency
            
        email_address = email_address.strip()
        if not self.ValidEmailAddress(email_address):
            raise "InvalidEmailAddress", "Email address is invalid"

        always_notify = ",".join(self.always_notify)
        always_notify = self.preParseEmailString(always_notify, aslist=1)
        if email_address.lower() in [x.lower() for x in always_notify]:
            raise "BusyEmailAddress", "%s is already used as always-notify"%\
                  email_address
        
        genid = email_address.replace('@','-at-').lower()
        account.createAcceptingEmail(genid, email_address, defaultsections,
                                     default_type, default_urgency,
                                     send_confirm, reveal_issue_url=reveal_issue_url)
        
        if REQUEST is not None:
            url = self.getRootURL()+'/manage_POP3ManagementForm'
            url = '%s?pop3accountid=%s'%(url, id)
            url = '%s&manage_tabs_message=%s'%(url, 'Accepting email created')
            response = self.REQUEST.RESPONSE
            response.redirect(url)
        
        
    def hasAcceptingEmails(self, id):
        """ return if any accepting emails """
        return len(self.getAcceptingEmails(id))>0
    
    def getAcceptingEmails(self, id):
        """ return accepting email objects """
        if getattr(id, 'meta_type','') == POP3ACCOUNT_METATYPE:
            root = id
        else:
            root = self.getPOP3Account(id)
        return root.objectValues(ACCEPTINGEMAIL_METATYPE)
    
    def getPOP3Account(self, id):
        """ get an object by id """
        return getattr(self.getPOP3Root(), id)
    

    security.declareProtected('View management screens','saveAcceptingEmails')
    def saveAcceptingEmails(self, id, allids):
        """ save all accepting emails. Find info via REQUEST object """
        request = self.REQUEST
        account = self.getPOP3Account(id)
        for each_id in allids:
            acceptingemail = getattr(account, each_id)
            rkey_email_address = 'email_address-%s'%each_id
            rkey_defaultsections = 'defaultsections-%s'%each_id
            rkey_default_type = 'default_type-%s'%each_id
            rkey_defaul_urgency = 'default_urgency-%s'%each_id
            rkey_send_confirm = 'send_confirm-%s'%each_id
            rkey_reveal_issue_url = 'reveal_issue_url-%s'%each_id

            email_address = request.get(rkey_email_address)
            if not self.ValidEmailAddress(email_address):
                raise "InvalidEmail", "Invalid email address %s"%email_address
            defaultsections = request.get(rkey_defaultsections)
            default_type = request.get(rkey_default_type)
            default_urgency = request.get(rkey_defaul_urgency)
            send_confirm = request.get(rkey_send_confirm, False)
            reveal_issue_url = bool(request.get(rkey_reveal_issue_url, False))
            
            acceptingemail.editDetails(email_address, defaultsections,
                                       default_type, default_urgency,
                                       send_confirm, 
                                       reveal_issue_url=reveal_issue_url)
            
        url = self.getRootURL()+'/manage_POP3ManagementForm'
        url = '%s?pop3accountid=%s'%(url, id)
        url = '%s&manage_tabs_message=Accepting emails saved'%url
        response = request.RESPONSE
        response.redirect(url)
    
    
        
    security.declareProtected(VMS, 'manage_delPOP3Accounts')
    def manage_delPOP3Accounts(self, ids=[], REQUEST=None):
        """ delete some POP3 Accounts """
        if Utils.same_type(ids, 's'):
            ids = [ids]
            
        root = self.getPOP3Root()
        root.manage_delObjects(ids)
        if REQUEST is not None:
            if len(ids)==0:
                mtm = "Nothing to delete"
            else:
                mtm = "Deleted %s POP3 Accounts"%len(ids)
            page = self.manage_POP3ManagementForm
            return page(self.REQUEST, manage_tabs_message=mtm)
        
    def getPOP3Root(self, create_if_necessary=True):
        """ return root/pop3 folder object. Create if necessary """
        root = self.getRoot()
        folderid = 'pop3'
        if create_if_necessary:
            if not folderid in root.objectIds('Folder'):
                root.manage_addFolder(folderid)
            return getattr(root, folderid)
        else:
            return getattr(root, folderid, None)
    
    def manage_delAcceptingEmails(self, id, ids=[], REQUEST=None):
        """ delete some accepting email objects """
        account = self.getPOP3Account(id)
        if Utils.same_type(ids, 's'):
            ids = [ids]
        account.manage_delObjects(ids)
        
        if REQUEST is not None:
            url = self.getRootURL()+'/manage_POP3ManagementForm'
            url = '%s?pop3accountid=%s'%(url, id)
            url = '%s&manage_tabs_message=%s accepting emails deleted'%\
                (url, len(ids))
            response = self.REQUEST.RESPONSE
            response.redirect(url)
            
    def check4MailIssues(self, verbose=False):
        """ connect to a pop3 account and possibly create 
        some issues """
        
        if email_Parser is None:
            raise "NoEmailPackage", "The email package is not installed"
        
        # a variable where we will collect all the messages if the verbose
        # parameter is True
        v = []
        
        # Optimization: The combos variable is created here so that it only
        # gets filled with useful stuff if there are any interesting
        # emails to deal with. As soon as there is such an email, the
        # fill this variable. 
        combos = None
        
        count = 0 # total count
        
        for account in self.getPOP3Accounts():
            v.append('Opening account host %s:%s' % (account.getHostname(),account.getPort()))
            
            if account.doSSL():
                connect_class = POP3_SSL
            else:
                connect_class = POP3
            
            try:
                M = connect_class(account.getHostname(), port=account.getPort())
            except poplib.error_proto, msg:
                return "poplib.error_proto: " + str(msg)
            except socket_error, msg:
                return "socket.error: " + str(msg)
            
            M.user(account.getUsername())
            v.append('Using username %r' % account.getUsername())
            M.pass_(account._password)
            
            # Get messages...
            #
            emails = self.getPOP3Messages(M, account)
            v.append('Downloaded %s emails' % len(emails))
            
            # ...parsed.
            emails = self._appendEmailIssueData(emails, account)
            v.append('Keep and process %s of them' % len(emails))
        
        
            # Now, create the issues
            #
            for email in emails:
                
                if combos is None:
                    # In case we only have an email address this can possibly help
                    combos = self.getEmailFromnameCombos()

                if email.get('is_spam', False):
                    v.append('\tDownloaded email is spam')
                elif email.get('is_blacklisted', False):
                    v.append('\tEmail originator is blacklisted (%s)' % email['email'])
                    
                elif self._processInboundEmail(email, combos=combos):
                    v.append('\tSaved email %r' % email.get('subject', email.get('title','')[:50]))
                    count += 1
                elif verbose:
                    v.append('\tDid not keep the email and it was not spam')
                    
                if account.doDeleteAfter():
                    v.append('\tDelete the email')
                    M.dele(email.get('message_number'))
                    

            v.append('')

            M.quit()

        if count == 1:
            msg = "Created 1 issue"
        else:
            msg = "Created %s issues" % count
            
        if verbose:
            br = '\r\n'
            msg += br + br.join(v)
            
        return msg
        
        
    def _processInboundEmail(self, email, combos):
        """ take this accepting email and upload it as an issue """
        if email.get('fromname','') == '':
            email['fromname'] = combos.get(email.get('email','').lower(),'')
            email['fromname'] = email['fromname'].replace('<','').replace('>','')
            email['fromname'] = email['fromname'].replace('"','').strip()
        else:
            email['fromname'] = email['fromname'].replace('"','').strip()
                
        try:
            # DateTime paranoia
            ok = DateTime(str(email['date']))
        except:
            email['date'] = DateTime()
            
        if email.has_key('display_format'):
            display_format = email['display_format']
        else:
            display_format = self.getDefaultDisplayFormat()
            
        _root_title = self.getRoot().getTitle()
        _root_id = self.getRoot().getId()
        _issueid_pattern = r'\d' * self.randomid_length

        def matchUrlInBody(body, url):
            if url.find('http://localhost') > -1:
                if body.find(url.replace('http://localhost', 'http://127.0.0.1')) > -1:
                    return True
            elif url.find('http://127.0.0.1') > -1:
                if body.find(url.replace('http://127.0.0.1', 'http://localhost')) > -1:
                    return True
            return body.find(url) > -1
                
    
        reply_issue_id_found = None
        
        # special header for the emails
        _key = EMAIL_ISSUEID_HEADER
        if email.get(_key, email.get(_key.lower(), None)):
            reply_issue_id_found = email.get(_key, email.get(_key.lower()))
            reply_issue_id_found = reply_issue_id_found.replace('%s#' % _root_id, '')
            reply_issue_id_found = reply_issue_id_found.strip()
            if reply_issue_id_found:
                return self._processInboundEmailReply(email, reply_issue_id_found)
            
            
        # is the root of the issuetracker to be found in the email body
        elif matchUrlInBody(email['body'], self.getRoot().absolute_url()):


            if self.issueprefix:
                issue_url_regex = r'(http|https)://\S+/%s/(%s|%s%s)' % \
                  (_root_id, _issueid_pattern, self.issueprefix, _issueid_pattern)
            else:
                issue_url_regex = r'(http|https)://\S+/%s/(%s)'
                issue_url_regex = issue_url_regex % \
                  (_root_id, _issueid_pattern)
                  
            # check if the email contains a URL to an issue that follows 
            # pattern we've defined above.
            if re.findall(issue_url_regex, email['body']):
                __, reply_issue_id_found = re.findall(issue_url_regex, email['body'])[0]
                reply_issue_id_found = reply_issue_id_found.strip()
                
            else:
                # it could very well be that the issuetracker is pointed to by
                # a top domain (eg. real.issuetrackerproduct.com) so the root
                # issuetracker instance id won't be in the URL. If this is the
                # case, look for any URL that might match and check the domain
                # name with that used right now.
                issue_url_regex = issue_url_regex.replace('/%s' % _root_id, '')
                whole_url_regex = '(%s)' % issue_url_regex
                if re.findall(whole_url_regex, email['body']):
                    whole_url, __, reply_issue_id_found = re.findall(whole_url_regex, email['body'])[0]
                    
                
        if reply_issue_id_found:
            try:
                self.getIssueObject(reply_issue_id_found)
            except:
                reply_issue_id_found = None

        

        # Is this email a reply to something this issuetracker has already
        # sent out. The first test checks if the body contains a URL to 
        # an issue on this issuetracker
        if reply_issue_id_found:
            # we passed the first test, now let's dig deeper!
            
            # Perhaps the email is a reply on an email sent out from this 
            # issuetracker before. It would then have the same signature and
            # at least a reference to an issue by URL.
            rendered_signature = self.showSignature()
            if email['body'].find(rendered_signature) > -1:
                # if we find an exact match on the signature, this email is a reply
                # of some sort on an email sent from this issuetracker
                return self._processInboundEmailReply(email, reply_issue_id_found)
        
            elif 0 < email['title'].find('%s: new issue:' % _root_title) < 6:
                # the subject line of the email has the "new issue:" thing
                # in the subject line near the begning.
                return self._processInboundEmailReply(email, reply_issue_id_found)
            
            elif 0 < email['title'].find('%s: ' % _root_title) < 6:
                # if the subject line starts like 'Re: <Issue Tracker Title>: bla blab ...'
                # (where <Issue Tracker Title> is self.getRoot().getTitle()) then we should
                # be able to find a title of an issue in the email title.
                if self.ShowIdWithTitle():
                    title_finder_regex = re.compile('%s: #(%s) (.*?)$' % (_root_title, _issueid_pattern))
                    _found = title_finder_regex.findall(email['title'])
                    if _found:
                        issueid, found_title = _found[0]
                        # if we now can find a title in this issuetracker that
                        # matches we know we're safe
                        found_seq = self._searchCatalog(found_title, search_only_on=['title'])
                        if list(found_seq):
                            return self._processInboundEmailReply(email, reply_issue_id_found)
                else:
                    title_finder_regex = re.compile('%s: (.*?)$' % _root_title)
                    _found = title_finder_regex.findall(email['title'])
                    if _found:
                        # if we now can find a title in this issuetracker that
                        # matches we know we're safe
                        found_seq = self._searchCatalog(_found[0], search_only_on=['title'])
                        if list(found_seq):
                            return self._processInboundEmailReply(email, reply_issue_id_found)
                        
                if email['body'].find(_("Thank you for submitting this issue via email.")) > -1:
                    # it was one of those Thank you messages that the issue has been
                    # added. Not overly happy about this test check.
                    return self._processInboundEmailReply(email, reply_issue_id_found)
                        
        body = unicodify(email['body'].strip())
        
        # Before we can create this issue, we need to make a duplication
        # check to prevent duplicate issues with the exact same 
        # input.
        title = unicodify(email['title'])
        if self._check4Duplicate(title, body,
                          sections=email['sections'], type=email['type'],
                          urgency=email['urgency'],
                          email_message_id=email.get('message_id', None)):
            return False
                          
            
        create = self.createIssueObject
        issue = create(None, unicodify(email['title']), 
                       self.getStatuses()[0],
                       email['type'], 
                       email['urgency'], 
                       email['sections'],
                       unicodify(email['fromname']),
                       email.get('email',''), '', 0, 0, 
                       body,
                       display_format,
                       email['date'], index=True,
                       submission_type='email',
                       email_message_id=email.get('message_id', None))

        for name, file in email.get('fileattachments', {}).items():
            name = Utils.badIdFilter(name)
            issue.manage_addFile(name, file)
            
        try:
            issue._setEmailOriginal(email['originalfile'].read())
        except:
            LOG(self.__class__.__name__, ERROR, "Failed to upload the original as a file",
                error=sys.exc_info())

        # Possibly send a return email
        if email['acceptingemail'].doSendConfirm():
            if email['fromname'] is not None and email['fromname'].strip() !='':
                fromname = email['fromname']
            else:
                fromname = None
                    
                    
            # <legacy stuff> In the old days around the 0.5 version, 
            # there used to be a standards script called 
            # SendInboundEmailConfirm_script which would be used for 
            # the email confirmations. Now it's not used anymore but
            # for the few people who are still using it, we'll stick 
            # to it.
            if hasattr(self, 'SendInboundEmailConfirm_script'):
                script = self.SendInboundEmailConfirm_script
                
                m = "Your deployed 'SendInboundEmailConfirm_script' "
                m += "object is no longer necessary unless you have "
                m += "customized it beyond default now. Consider "
                m += "deleting it from the instance."
                parent_url = aq_parent(aq_inner(script)).absolute_url()
                m += "\n%s" % parent_url
                import warnings
                warnings.warn(m, DeprecationWarning)
                #LOG(self.__class__.__name__, WARNING, m)
                
            else:
                script = self.SendInboundEmailConfirm

            kwargs = {}

            if email.has_key('reveal_issue_url'):
                kwargs['reveal_issue_url'] = email['reveal_issue_url']
            
            try:
                result = script(issue, email['email'], fromname, **kwargs)
            except:
                try:
                    err_log = self.error_log
                    err_log.raising(sys.exc_info())
                except:
                    pass                
                typ, val, tb = sys.exc_info()
                _classname = self.__class__.__name__
                _methodname = inspect.stack()[1][3]
                LOG("IssueTrackerProduct.check4MailIssues()", ERROR,
                    'Could not send autoreply',
                    error=sys.exc_info())                        
                        
                    
            # Notify always notifyables
            try:
                self.sendAlwaysNotify(issue, email=email.get('email', None))
            except:
                try:
                    err_log = self.error_log
                    err_log.raising(sys.exc_info())
                except:
                    pass                
                typ, val, tb = sys.exc_info()
                _classname = self.__class__.__name__
                _methodname = inspect.stack()[1][3]
                LOG("IssueTrackerProduct.check4MailIssues()", ERROR,
                    'Could not send always-notify emails',
                    error=sys.exc_info())        
            
            # if we made it all the way down to here, then the email
            # was added as an issue.
            return True
                        

    def _processInboundEmailReply(self, email, issueid):
        """ the emaildict is a parsed email with all it's content that we can 
        now create as a followup to the issue """
        issueobject = self.getIssueObject(issueid)
        
        text = email['body']
        _character_set = email.get('_character_set','us-ascii')
        
        if _has_formatflowed_:
            CRLF = '\r\n'
            text = text.replace('\n', CRLF)
            try:
                textflow = formatflowed_decode(text, character_set=_character_set)
                try:
                    text, old = Utils.parseFlowFormattedResult(textflow)
                except AttributeError, msg:
                    raise AttributeError, "%s (_character_set=%r)" %(msg, _character_set)
                    
            except LookupError:
                # _character_set is quite likly 'iso-8859-1;format=flowed'
                _character_set = _character_set.split(';')[0].strip()
                textflow = formatflowed_decode(text, character_set=_character_set)
                try:
                    text, old = Utils.parseFlowFormattedResult(textflow)
                except AttributeError, msg:
                    raise AttributeError, "%s (_character_set=%r)" %(msg, _character_set)

            except UnicodeDecodeError:
                try:
                    text = formatflowed_decode(text, 'latin-1')
                    text, old = Utils.parseFlowFormattedResult(text)
                except UnicodeDecodeError, err:
                    try:
                        text = formatflowed_decode(text, 'utf-8')
                        text, old = Utils.parseFlowFormattedResult(text)
                    except UnicodeDecodeError:
                        pass
                    
                raise UnicodeDecodeError, err # raise the original error

            
            _originalmessage_regex =  re.compile('''(-----\s*Original Message\s*-----\s+[From\:|Sent\:|To\:])''')
            # Some email clients don't use > on the replied-to lines but instead
            # splits the whole message with a "-----Original Message-----"
            # If the message can't be splitted correctly with formatflowed, do 
            # the following:
            if not old.strip() and _originalmessage_regex.split(text) > 1:
                text = _originalmessage_regex.split(text)[0]
            
            # if the reply was parsed it's quite likely that it will contain 
            # something like:
            # "On 10/19/05, Peter Bengtsson <mail@peterbe.com> wrote:"
            # remove that if possible.
            original_email = self.sitemaster_email
            wrote_line_regex = r'^.*?<%s> .*?:$' % original_email
            for line in re.compile(wrote_line_regex, re.M).findall(text):
                text = text.replace(line, CRLF)
                
            # Until the IssueTracker supports storing all attributes in unicode,
            # do the following which is self-explanatory:
            if isinstance(text, unicode):
                text = text.encode(_character_set)
            
        else:
            # crude! Kill all lines that start with '> '
            m = "Formatflowed is not installed. Email replies can't be parsed properly."
            LOG(self.__class__.__name__, WARNING, m)
            
            keeplines = []
            for line in text.splitlines():
                if not line.startswith('> '):
                    keeplines.append(line)
            text = '\n'.join(keeplines)

        gentitle = _("Added Issue followup")

        # Before we can create this thread, we need to make a duplication-
        # check to prevent duplicate threads with the exact same 
        # input.
        if issueobject._check4Duplicate(gentitle, text,
                          email['fromname'], email['email'],
                          email_message_id=email.get('message_id', None)):
            return False
            
        create = issueobject._createThreadObject
        
        randomid_length = self.randomid_length
        #if action == 'addfollowup':
        #    gentitle = "Added Issue followup"
        #else:
        #    gentitle = 'Changed status from %s to %s'%\
        #                (oldstatus.capitalize(), past_tense.capitalize())
        prefix = self.issueprefix
        genid = issueobject.generateID(randomid_length, prefix+'thread',
                                       meta_type=ISSUETHREAD_METATYPE,
                                       use_stored_counter=0)
        
        
        if not email.has_key('display_format'):
            email['display_format'] = self.getDefaultDisplayFormat()
        
        thread = create(genid, gentitle, text, DateTime(), 
                        email['fromname'], email['email'],
                        email['display_format'],
                        submission_type='email',
                        email_message_id=email.get('message_id', None)
                        )
                        
        # make sure the issue object is updated now that this change has
        # been made
        issueobject._updateModifyDate()

        try:
            thread._setEmailOriginal(email['originalfile'].read())
        except:
            LOG(self.__class__.__name__, ERROR, 
                "Failed to upload the original as a file to a followup",
                error=sys.exc_info())
                
        for name, file in email.get('fileattachments', {}).items():
            name = Utils.badIdFilter(name)
            thread.manage_addFile(name, file)
            

        email_addresses = issueobject.Others2Notify(do='email', emailtoskip=email['email'])
        if email_addresses:
            issueobject.sendFollowupNotifications(thread, email_addresses, gentitle)
        
        # nothing else to complain about
        return True
    
    
    def SendInboundEmailConfirm(self, issueobject, emailaddress, fromname=None,
                                reveal_issue_url=True):
        """ script for sending out a confirmation message back to the person
        who added an issue via email. Return true if the email was sent or
        False otherwise. """
        
        br = "\r\n"
        
        if self.sitemaster_name:
            mfrom = "%s <%s>"%(self.sitemaster_name, 
                               self.sitemaster_email)
        else:
            mfrom = self.sitemaster_email
        
        subject = "%s: Your issue has been added" % self.getRoot().getTitle()
        
        msg = "Thank you for submitting this issue via email.%s%s" % (br, br)
        if reveal_issue_url:
            issueurl = issueobject.absolute_url()
            msg += "Your issue can be found here:%s%s" % (br, issueurl)
        else:
            issueid = issueobject.getId()
            msg += "Your issue id for this is: #%s" % issueid
        msg += br + br
                           
        # Footer
        signature = self.showSignature()
        if signature:
            msg += "--" + br +signature
            
        if fromname is not None:
            mTo = "%s <%s>"%(fromname, emailaddress)
        else:
            mTo = emailaddress

        issueid_header = issueobject.getGlobalIssueId()
        self.sendEmail(msg, mTo, mfrom, subject, swallowerrors=True,
                       headers={EMAIL_ISSUEID_HEADER: issueid_header})
        
        

    def getEmailFromnameCombos(self):
        """ look through all issues and followups for combinations
        of fromname and email """
        combos = {}
        for issue in self.getIssueObjects():
            issue_email = issue.getEmail()
            if issue_email is None:
                continue
            if not combos.has_key(issue_email.lower()):
                combos[issue_email.lower()] = issue.getFromname()
            for thread in issue.objectValues(ISSUETHREAD_METATYPE):
                thread_email = thread.getEmail()
                if not combos.has_key(thread_email.lower()):
                    combos[thread_email.lower()] = thread.getFromname()
        return combos
    
    def _appendEmailIssueData(self, emails, account):
        """ inspect message for certain issue data. """
        allissueids = self.getIssueIds()
        allsections = self.getSectionOptions()
        allsections_ss = [ss(x) for x in allsections]
        alltypes = self.types
        allurgencies = self.urgencies
        
        reg_issueids = "|".join(allissueids)
        reg_sections = "|".join(allsections)
        reg_types = "|".join(alltypes)
        reg_urgencies = "|".join(allurgencies)
        reg_structuredtext = r'STX|structuredtext|structured-text'
        
        reg_issueids = re.compile(reg_issueids, re.I)
        reg_sections = re.compile(reg_sections, re.I)
        reg_types = re.compile(reg_types, re.I)
        reg_urgencies = re.compile(reg_urgencies, re.I)
        reg_structuredtext = re.compile(reg_structuredtext, re.I)
        
        correct_caser = self._getCorrectCase
        nemails = []
        for email in emails:
            s = email.get('subject','').strip()
            if s == '':
                m = "Subject line can not be empty"
                self.sendReturnErrorEmail(email, m)
                continue
            
            subject, parsable, delimiter = self._getParsableSubject(s)
            parsable = [x.strip() for x in parsable.split(',')]
            
            # Sections
            sections = []
            for eachpart in parsable[:]:
                if ss(eachpart) in allsections_ss:
                    sections.append(correct_caser(eachpart, allsections))
                    #parsable.remove(eachpart) # Real0265
                    ss_remove(parsable, eachpart)
                    
            
            if sections:
                email['sections'] = sections
                
            # Type
            types = []
            for eachpart in parsable:
                types.extend(reg_types.findall(eachpart))
            if types:
                email['type'] = correct_caser(types[0], alltypes)
                parsable.remove(types[0])
                
            # Urgency
            urgencies = []
            for eachpart in parsable:
                urgencies.extend(reg_urgencies.findall(eachpart))
            if urgencies:
                email['urgency'] = correct_caser(urgencies[0], allurgencies)
                parsable.remove(urgencies[0])
                
            # Structured or plain text
            # This one is a bit special.
            structured_text = []
            for eachpart in parsable:
                structured_text.extend(reg_structuredtext.findall(eachpart))
            if structured_text:
                email['display_format'] = 'structuredtext'
                parsable.remove(structured_text[0])
                
            if parsable:
                leftovers = ', '.join(parsable)
                if delimiter in ['[',']']:
                    subject = "[%s] %s"%(leftovers, subject)
                elif delimiter == ':':
                    subject = "%s: %s"%(leftovers, subject)

            email['title'] = subject
            
            # Retrospect, and fill in with default values.
            # This is where we use the default* values from the
            # matching accepting email object
            acceptingemail = account.getAcceptingEmailbyTo(email['to'])
            email['acceptingemail'] = acceptingemail
            if not email.has_key('sections'):
                email['sections'] = acceptingemail.defaultsections
            if not email.has_key('type'):
                email['type'] = acceptingemail.default_type
            if not email.has_key('urgency'):
                email['urgency'] = acceptingemail.default_urgency
            
            email['reveal_issue_url'] = acceptingemail.revealIssueURL()

            extractor = self.preParseEmailString
            
            email['email'] = extractor(email['from'], allnotifyables=0)

            if email['email'] is None:
                # no valid email address was extracted
                continue
            
            assert isinstance(email['email'], basestring), \
              "email['email'] not string (email['email']=%r, (%s))" % (email['email'], type(email['email']))
              
            f = email['from'].replace(email['email'],'').strip()
            f = f.replace('<','').replace('>','').strip().replace('"','')
            email['fromname'] = f
            
            nemails.append(email)
            
        return nemails
    
    def sendReturnErrorEmail(self, email, msg):
        """ Send a simple email when there is an error """
        # Check that the sitemaster_email has been set
        if self.sitemaster_email == DEFAULT_SITEMASTER_EMAIL:
            m = "Sitemaster email not changed from default. Email not sent."
            LOG(self.meta_type, WARNING, m)
            return

        mFrom = self.sitemaster_email
        mTo = email['from']
        mSubject = "[Autoreply] Inbound issue email incorrect"
        mBody = "There was an error in your inbound email to %s\n\n"%\
              self.getRoot().getTitle()
        mBody = mBody + "Error: %s"%msg
        self.sendEmail(mBody, mTo, mFrom, mSubject, swallowerrors=True)
        
    def _getParsableSubject(self, subject):
        """ check the subject line for what is really the parsable
        bit and the textual bit.
        Return (textual, parsable, delimiter) 
        Where delimiter is either '[' or ':'"""
        
        # default
        textual = subject
        delimiter = parsable = ''
        if subject[0]=='[' and subject[1:].find(']') > -1 and not \
           subject[-1]==']':
            # Used like this -  [Bug, Help] Bla bla bla
            parsable = subject[1:subject.find(']')].strip()
            textual = subject[subject.find(']')+1:].strip()
            delimiter = '['
        elif subject.find(':')>0:
            # Used like this -  Bug, Help: Bla bla bla
            parsable = subject[:subject.find(':')].strip()
            textual = subject[subject.find(':')+1:].strip()
            delimiter = ':'
        return textual, parsable, delimiter
    
        
    def _getCorrectCase(self, item, list):
        """ item might be 'abc' and list ['Abc','Def'] 
        then return 'Abc' """
        for correct_item in list:
            if item.lower()==correct_item.lower():
                return correct_item
        else:
            return item
            
            
    def getPOP3Messages(self, pop3instance, account, dele=None):
        """ get messages from pop3 object """
        
        if dele is not None:
            import warnings
            m = 'getPOP3Messages() will not continue to accept the '
            m += "'dele' parameter since it will no longer be able "
            m += "to delete emails."
            warnings.warn(m, DeprecationWarning)
            
        numMessages = len(pop3instance.list()[1])
        if not numMessages:
            return [] # no point going on
        
        emails = []
        accepting_email_objects = account.getAcceptingEmails()
        
        already_message_ids = [x.getEmailMessageId() for x in self.getIssueObjects()]
        already_message_ids = [ss(x) for x in already_message_ids if x]
        
            
        basepath = os.path.join(INSTANCE_HOME, 'var') 
        for i in range(numMessages):
            emailfile = cStringIO.StringIO()
            
            for line in pop3instance.retr(i+1)[1]:
                # XXX Hmm? Should this perhaps be 
                # emailfile.write(line.encode('latin-1')+'\n')
                # instead. 
                emailfile.write(line+'\n')
            
            p = email_Parser.Parser()
            emailfile.seek(0) # rewind for reading
            msg = p.parse(emailfile)
            
            emailfile.seek(0)
            # again, should that second line not be 
            # cStringIO.StringIO(emailfile.read().encode('latin-1')) ??
            e = {'is_spam': False, 
                 'originalfile':cStringIO.StringIO(emailfile.read()),
                 '_character_set':'us-ascii',
                 }
            e['fileattachments']={}

            charset_regex = re.compile(r'charset=["\']?([^"\']+)["\']?', re.I)
            
            
            # this makes sure all the headers are written in lowercase 
            # whitespace stripped
            for key, value in msg.items():
                e[ss(key)] = value
                if ss(key) == 'content-type':
                    if charset_regex.findall(value):
                        e['_character_set'] = charset_regex.findall(value)[0]
                        
                elif ss(key) == 'subject':
                    if isinstance(value, str) and value.lower().find('?iso-8859') > -1:
                        unicode_value, value_encoding = email_Header.decode_header(value)[0]
                        if value_encoding is not None:
                            value = unicode_value.decode(value_encoding)
                            value = value.encode(value_encoding)
                        else:
                            value = unicode_value
                        e[ss(key)] = value
                    
                if not e.has_key('message_id') and ss(key) in ('message-id','messageid'):
                    # This might seem stupid but it makes sure that if possible
                    # there is a header in 'e' that is spellt exactly like 
                    # this. Not all emails might call the header 'Message-Id'
                    e['message_id'] = value
                    
                    # this is a crucial check. The whole point of bothering about the
                    # Message-ID is to prevent processing emails that have already
                    # been uploaded. See above how we create the variable 
                    # 'already_message_ids' and now we can use that to test if this
                    # email has already been processed
                    if ss(value) in already_message_ids:
                        # a ha! We have already processed this email as an issue!
                        continue
                    
                
            content_html = ''
            content_plain = ''
            for part in msg.walk():
                if part.get_main_type() == 'multipart':
                    continue
                name = part.get_param('name')
                if name is None:
                    name = part.get_filename()
                try:
                    content = part.get_payload(decode=1)
                except:
                    # This might happen if the part is too unnormal
                    # for the email package to deal with. In that
                    # case, this attachment is ignorable. Tough!
                    continue
                if name == None:
                    if str(part.get_subtype()).lower() == 'html':
                        content_html = content
                    else:
                        content_plain = content
                else:
                    e['fileattachments'][name] = content
                    
            if content_html and content_plain:
                e['body'] = content_plain
                e['body_html'] = content_html
            elif content_html:
                if self._isHTMLBody(content_html):
                    if html2safehtml is not None:
                        content_html = self._stripHTMLBody(content_html)
                        e['display_format'] = 'plaintext'
                    else:
                        m = "stripogram module not installed to strip HTML emails"
                        LOG(self.__class__.__name__, WARNING, m)
                        e['display_format'] = 'html'
                e['body'] = content_html
            else:
                e['body'] = content_plain
                

            if SPAMBAYES_CHECK:
                # http://spambayes.sourceforge.net
                header = 'X-Spambayes-Classification'
                if e.get(header, '') == SPAMBAYES_CHECK or e.get(header.lower()) == SPAMBAYES_CHECK:
                    # this is spam!!
                    e['is_spam'] = True
                    
            # Maybe it wasn't sent directly To, but CC
            if e.get('cc','') != '':
                e['to'] = "%s, %s"%(e.get('to',''), e['cc'])
            # check whom it's to
            extractor = self.preParseEmailString
            tolist = extractor(e['to'], aslist=1, allnotifyables=0)
            
            tolist_simplified = [ss(x) for x in tolist]
            intersection = []
            originator = self.preParseEmailString(e['from'])
            for ae in accepting_email_objects:
                if ss(ae.getEmailAddress()) in tolist_simplified:
                    intersection.append(ae.getEmailAddress())
                    try:
                        if not ae.acceptOriginatorEmail(originator):
                            e['is_blacklisted'] = True
                    except:
                        LOG(self.__class__.__name__, WARNING,
                            "Failed to do a white-/blacklist check on %s" % e['from'],
                            error=sys.exc_info())
                        
            if intersection:
                e['to'] = intersection[0]
                e['message_number'] = i + 1
                emails.append(e)
        
            emailfile.close()
            del emailfile
            
        return emails
                
    def _getIntersection(self, list1, list2):
        """ if 'A, C, D' in ['a','b'] should return True """
        intersection = []
        if list1 is None:
            return []
        elif not Utils.same_type(list1, []):
            list1 = [list1]
            
        if not Utils.same_type(list2, []):
            list2 = [list2]
        list2lower = [x.lower().strip() for x in list2]
        for item in list1:
            if item.lower().strip() in list2lower:
                intersection.append(item)
        return intersection
    
    def _isHTMLBody(self, body):
        """ check if the body is html encoded """
        if body is None:
            return False
        body = self._rmDoctype(body)
        return body.startswith('<html>') and body.endswith('</html>')
        
    def _rmDoctype(self, s):
        """ remove if s starts with <!DOCTYPE ...> """
        s = s.lower().strip()
        if s.startswith('<!doctype'):
            s = s[s.find('>')+1:]
        return s.strip()
    
    def _stripHTMLBody(self, body):
        """ strip out all HTML if possible from the email """
        accept_tags = ('b','strong','br','i','em','p','a',
                       'ol','ul','li','div')
        return html2safehtml(body, valid_tags=accept_tags)


    ## Menu
    
    
    def canLogout(self):
        """ return true if we have a method of logging this user out """
        if self.get_cookie(LOGOUT_PAGE_COOKIEKEY):
            return True
        
        # defaulty
        return False
        
    def Logout(self, REQUEST):
        """ logout if possible via the web """
        assert self.canLogout(), \
          "No method for loggin out. Shut down your browser maybe"
          
        if self.has_cookie(LOGOUT_PAGE_COOKIEKEY):
            # This will most likely only happen if you have 
            # logged in via a CookieCrumbler. Find it and go to
            # its logged_out method.
            url = self.get_cookie(LOGOUT_PAGE_COOKIEKEY)
            if url.startswith('/'):
                url = REQUEST.BASE0 + url
            elif not url.startswith('http'):
                url = self.getRootURL() + '/' + url
            return REQUEST.RESPONSE.redirect(url)
        
        # rough default
        return _("Logged out")
            
    security.declareProtected(VMS, 'getMenuItemsList')
    def getMenuItemsList(self):
        """ return the self.menu_items property if we have it """
        return getattr(self, 'menu_items', DEFAULT_MENU_ITEMS)
    
    _getMenuItems = getMenuItemsList    
    
    def _setMenuItems(self, menu_items):
        """ set the 'menu_items' property """
        # validate 
        if isinstance(menu_items, tuple):
            menu_items = list(menu_items)
        assert isinstance(menu_items, list), "menu_items is not a list"
        for item in menu_items:
            assert isinstance(item, dict), "%r is not a dict" % item
            # the dict should have three keys
            try:
                href = item['href']
                assert isinstance(href, basestring), "href not a string"
            except KeyError:
                raise KeyError, "Every item must have a 'href'"

            try:
                inurl = item['inurl']
                assert isinstance(inurl, (basestring, tuple, list)), \
                "inurl must be string, tuple or list"
            except KeyError:
                raise KeyError, "Every item must have a 'inurl'"
            
            try:
                label = item['label']
                assert isinstance(label, basestring), "inurl not a string"
            except KeyError:
                raise KeyError, "Every item must have a 'inurl'"
            
        # all menu items checked, save
        self.menu_items = menu_items
            
        

    def getMenuItems(self):
        """ return a list of three items (Title, Href, On) """
        rooturl = self.getRoot().relative_url()
        inURL = self.thisInURL
        # massage the menu_items list (full of dicts) so that we turn
        # the 'inurl' info into a boolean based on where the user is now
        items = self.getMenuItemsList()
        menu = []
        for e in items:
            if e['inurl'] == '':
                _inurl = inURL(e['inurl'], homepage=1)
            else:
                _inurl = inURL(e['inurl'])
            menu.append([e['label'], e['href'], _inurl])
                
        issueuser = self.getIssueUser()
        zopeuser = self.getZopeUser()
        cmfuser = self.getCMFUser()
        
        if issueuser:
            menu.append([issueuser.getFullname(), '/User', inURL('User')])

        elif cmfuser:
            menu.append([cmfuser.getProperty('fullname'), '/User', inURL('User')])

        elif zopeuser:
            _name = zopeuser.getUserName()
            if self.getSavedUser('fullname'):
                _name = self.getSavedUser('fullname')
            menu.append([_name, '/User', inURL('User')])
        else:
            menu.append(['Login', self.ManagerLink(1), False])
            
        if self.has_cookie(LOGOUT_PAGE_COOKIEKEY) and (issueuser or zopeuser):
            # if we have this cookie, it means that we know the cookie
            # name of the cookie that logged the person in in the 
            # first place. This we can use to log a user out.
            menu.append(['Log out', self.get_cookie(LOGOUT_PAGE_COOKIEKEY), False])

        for i in range(len(menu)):
            href = menu[i][1]
            if href.startswith('/') and len(href.split('?')[0].split('/'))==2:
                menu[i][1] = rooturl + href
                
        return menu

    
    def displayMenuItem(self, menuinfo, underline_first_letter=None):
        """ proxy showing of the title through this and maybe we
        append a little gif with it. """
        imgdata = MENUICONS_DATA

        # e.g. menuinfo = [title, url, on]
        title = show_title = menuinfo[0]
        if underline_first_letter and underline_first_letter.lower()==title[0].lower():
            show_title = "<u>%s</u>%s" % (title[0], title[1:])
        
        if self.imagesInMenu():
            tmpl = '<img align="left" src="%(src)s" width="%(width)s" height="%(height)s" '
            tmpl += 'alt="%(alt)s" border="0" />'
            identifier = menuinfo[1].split('/')[-1]
            if identifier == '':
                identifier = 'Home'
            if title == 'Login':
                identifier = 'Login'
            if title == 'Log out':
                identifier = 'Logout'
                
            if imgdata.has_key(identifier):
                return tmpl%imgdata[identifier] + '&nbsp;' + show_title
            else:
                return show_title
        else:
            return show_title
        
                

    ## Statistics

    def getStatus2ListLink(self, status):
        """ return the URL to ListIssues or CompleteList with this status
        as parameter. """
        url = self.relative_url()+'/'+self.whichList()
        params = {'f-statuses':status,
                  #'remember-filterlogic':'no'
                         }
        params['Filterlogic'] = 'show'
        url = Utils.AddParam2URL(url, params)
        return url

    def getSection2ListLink(self, section):
        """ return the URL to ListIssues or CompleteList with this section
        as parameter. """
        url = self.relative_url()+'/'+self.whichList()
        params = {'f-sections':section,
                      #'remember-filterlogic':'no'
                         }
        params['Filterlogic'] = 'show'
        url = Utils.AddParam2URL(url, params)
        return url
    
    def CountStatuses(self, since=None):
        """ Return how many Issues there are under each status since
            a certain time
        """
        #
        # NEEDS WORK!!
        #
        
        #return {}
        request = self.REQUEST

        # check that since isn't a string
        if Utils.same_type(since, 's'):
            since = DateTime(since)
        elif request.has_key('count_status_since'):
            since = DateTime()-int(request['count_status_since'])


        res={}
        tres=[]
        for issue in self.getIssueObjects():
            if since is None or issue.getModifyDate() >= since:
                status = issue.status.lower()
                if res.has_key(status):
                    res[status]=res[status]+1
                else:
                    res[status] = 1

        # Lastly we want to organize res by self.statuses order
        for status in self.getStatuses():
            status = status.lower()
            if res.has_key(status):
                #sc = StatusCount(status, res[status])
                tres.append([status, res[status]])
            else:
                #sc = StatusCount(status)
                tres.append([status, 0])
        return tres
    
    def totalCountStatus(self, statuslist):
        """ in a status list [['open',4], ...] 
        sum up all the numbers """
        count = 0
        for item in statuslist:
            count += item[1]
        return count
            
    def CountSections(self):
        """ for every section, count how many for each status 
        return as [['General', {'open':4, 'taken':6, ...}], ...] """
        res = []
        allsections = {}
        allissues = self.getIssueObjects()
        for issue in allissues:
            status = issue.status.lower()
            for section in issue.sections:
                if not allsections.has_key(section):
                    allsections[section] = {}
                if not allsections[section].has_key(status):
                    allsections[section][status] = 0
                allsections[section][status] += 1
                
        # add all zeros
        for section in self.getSectionOptions():
            if not allsections.has_key(section):
                allsections[section] = {}
            allsections[section] = self._allStatuses(allsections[section])
            res.append([section, allsections[section]])
                
        return res
                
    def _allStatuses(self, dict):
        """ dict might be {'open':2, 'taken':0}
        then make sure it as all possible statuses """
        for status in self.getStatuses():
            if not dict.has_key(status.lower()):
                dict[status] = 0
        return dict
    
    def totalCountSections(self, sectiondict):
        """ sum the total in {'open':2, 'taken':1, ...} """
        count = 0
        for value in sectiondict.values():
            count += value
        return count
    
    def issueInflux(self, from_date=None, till_date=None,
                    issues=None, returncount=0):
        """ calculate for different day periods approximately how 
        many issues are coming in """
        if from_date is not None and Utils.same_type(from_date, 's'):
            from_date = DateTime(from_date)
            
        if issues is not None:
            allissues = issues
        else:
            allissues = self.getIssueObjects()
            allissues = sequence.sort(allissues, (('issuedate',),))
            
        # if from_date is None, then make the first issue the from_date
        if from_date is None:
            from_date = allissues[0].issuedate
        if till_date is None:
            till_date = DateTime()

        count = 0 
        for issue in allissues:
            if issue.issuedate >= from_date and issue.issuedate < till_date:
                count += 1
        
        day_span = till_date - from_date
        
        if returncount:
            return count
        else:
            issue_per_day = count / day_span
            return issue_per_day
            
        
    def issueInfluxbyPeriod(self, period=14):
        """ prepare a issues per period list """
        allissues = self.getIssueObjects()
        allissues = sequence.sort(allissues, (('issuedate',),))
        
        try:
            period = int(period)
        except:
            raise "PeriodNotInteger", "The period must be an integer"
        start_date = allissues[0].issuedate
        end_date = allissues[-1].issuedate
        difference_days = end_date - start_date
        
        influxes = []
        today = DateTime()
        highest = 0
        for i in range(int(difference_days/period)+1):
            from_date = start_date + i * period
            till_date = from_date + period
            if till_date > today:
                till_date = today
            data = {'from':from_date, 'till':till_date}
            influx = self.issueInflux(from_date, till_date,
                                      allissues, 1)
            data['influx'] = influx
            if influx > highest:
                highest = influx
            influxes.append(data)
            
        return influxes, highest

    def showTableRowsOfDates(self, influxes):
        """ return 3 TR rows of days, months, years with correct colspan """
        days, months, years = [], [], []

        prev_month = ''
        prev_year = ''

        month_counts = {}
        year_counts = {}
        
        c_m = 0
        c_y = 0
        for influx in influxes:
            day = influx['from'].strftime('%d')
            days.append(day)
            
            month = influx['from'].strftime('%m-%Y')
            if prev_month != month:
                months.append(month)
                prev_month = month
            if month_counts.has_key(month):
                month_counts[month] += 1
            else:
                month_counts[month] = 1

            year = influx['from'].strftime('%Y')
            if prev_year != year:
                years.append(year)
                prev_year = year
                
            if year_counts.has_key(year):
                year_counts[year] += 1
            else:
                year_counts[year] = 1


        _attrs = r'align="center" style="font-size:80%"'

        
        days_row = '<tr>'
        for day in days:
            days_row += '<td %s>%s</td>'%(_attrs, day)
        days_row += '</tr>\n'
        
        months_row = '<tr>'
        for month in months:
            _m = month.split('-')[0]
            if month_counts[month] > 1:
                months_row += '<td colspan="%s" %s>%s</td>'%\
                              (month_counts[month], _attrs, _m)
            else:
                months_row += '<td %s>%s</td>'%(_attrs, _m)
        months_row += '</tr>\n'

        years_row = '<tr>'
        for year in years:
            if year_counts[year] > 1:
                years_row += '<td colspan="%s" %s>%s</td>'%\
                             (year_counts[year], _attrs, year)
            else:
                years_row += '<td %s>%s</td>'%(_attrs, year)
        years_row += '</tr>\n'
        
        return days_row + months_row + years_row

        

    ## User related
            
    
    def getFilterlogic(self):
        """ not only inspect user object and cookies but
        also set if something new is in the REQUEST """
        request = self.REQUEST

        key = 'Filterlogic'
        
        ok_values = ('show','block')
        issueuser = self.getIssueUser()
        
        if not request.has_key(key):
            if ss(key) in [ss(x) for x in request.keys()]:
                m = "If you want to set the Filterlogic parameter in REQUEST, "
                m += "use the correct case which is %s" % key
                m += "\n%s"%self.absolute_url()
                LOG(self.__class__.__name__, WARNING, m)
                for k,v in request.items():
                    if ss(key)==ss(k):
                        request.set(key, v)
                        break
        
        if ss(str(request.get(key,''))) in ok_values:
            # save it
            value = request.get(key)
            
            save_value = True
            
            if request.has_key('remember-filterlogic'):
                save_value = Utils.niceboolean(request.get('remember-filterlogic'))
            
            if save_value:
                if issueuser:
                    issueuser.setMiscProperty(key,value)
                else:
                    self.set_cookie(key, value)
                    self.set_session(key, value, True) # faster to read from
                

            return value
        else:
            default = 'block'
            if issueuser:
                return issueuser.getMiscProperty(key, default)
            else:
                return request.get(key,
                                   self.get_session(key,
                                                    self.get_cookie(key,
                                                        default)))
                                   
            
        
    def getZopeUser(self):
        """ return the user object iff not Anonymous """
        #user = self.REQUEST.AUTHENTICATED_USER
        user = getSecurityManager().getUser()
        uname = user.getUserName()
        if uname != 'Anonymous User':
            return user
        else:
            return None
        
    def getCMFUser(self):
        """ return the user object if it's got the portal_memberdata functions """
        if CMF_getToolByName is None:
            return None
        
        try:
            mtool = CMF_getToolByName(self, 'portal_membership')
            authenticated_member = mtool.getAuthenticatedMember()
            assert authenticated_member.getProperty('fullname')
            assert authenticated_member.getProperty('email')
            return authenticated_member
        except AssertionError:
            debug("No 'fullname' or 'email' property")
            return None
        except AttributeError:
            # then an authenticated user that is not a IssueUser
            return None
        
        
    def getIssueUser(self):
        """ use REQUEST to get the IssueUser object or None """
        user = getSecurityManager().getUser()
        try:
            user.getIssueUserPath()
            return user
        except AttributeError:
            # then an authenticated user that is not a IssueUser
            return None

    def getIssueUserObject(self, identifier):
        """ deconstruct an identifier to find the actual user object """
        if not identifier:
            return None
        acl_path, username = identifier.split(',')
        userfolder = self.unrestrictedTraverse(acl_path)
        return userfolder.data[username]

    def isIssueUser(self):
        """ return True if self.getIssueUser() is not None """
        return self.getIssueUser() is not None

    
    security.declareProtected('View', 'getNextActionIssuesWeb')
    def getNextActionIssuesWeb(self):
        """ this wraps the getNextActionIssues() function but prepares it a bit more
        for the web. """
        issues, reasonsdict = self.getNextActionIssues()
        self.REQUEST.set('nextaction_reasons', reasonsdict)
        
        return issues
        
        
    security.declareProtected('View', 'getNextActionIssues')
    def getNextActionIssues(self, skip_sort=False):
        """ return a list of issues sorted by urgency that points to the current user """
        zopeuser = self.getZopeUser()
        issueuser = self.getIssueUser()
        if not issueuser and not zopeuser:
            fromname = self.getSavedUser('fromname')
            email = always_email = self.getSavedUser('email')
            acl_user = None

        if issueuser:
            acl_user = ','.join(issueuser.getIssueUserIdentifier())
            email = always_email = issueuser.getEmail()
            
        elif zopeuser:
            path = '/'.join(zopeuser.getPhysicalPath())
            name = zopeuser.getUserName()
            acl_user = path+','+name
            
            email = always_email = self.getACLCookieEmails().get(name, None)
            if not always_email:
                email = always_email = self.getSavedUser('email')
            
        
        always_notify_emails = self.getAlwaysNotify()
        always_notify_emails = self.preParseEmailString(','.join(always_notify_emails),
                                                        aslist=True)
        # convert that string to a bool
        always_email = ss(always_email) in [ss(x) for x in always_notify_emails]

        include_statuses = [ss(x) for x in self.getStatuses()[:2]]
        
        issues = [x for x in self.getIssueObjects() \
                   if ss(x.getStatus()) in include_statuses]

        # now, look for all issues where You haven't had the last word such as
        # issues you've added but haven't posted the last followup,
        # issues assigned to your name,
        # issues you have taken,
        keep_issues = []
        
        # we assign each issue with a score based on how it's matched
        highest_score = len(self.getUrgencyOptions()) #+ 1

        _ASSIGNED = (_("Because it is assigned to you"), highest_score)
        _TAKEN = (_("Because it is taken by you"), highest_score + 1)

        urgency_scores = {}
        urgency_options = self.getUrgencyOptions()
        for i in range(len(urgency_options)):
            urgency_scores[urgency_options[i]] = i
            
        today = DateTime()
        
        for issue in issues:

            # check assignment
            assignments = issue.getAssignments()
            if assignments:
                last_ass = assignments[-1]
                if acl_user and last_ass.getACLAssignee() == acl_user:
                    keep_issues.append(dict(issue=issue, reason=_ASSIGNED))
                    continue
            
            threads = issue.ListThreads()
            
            _taken_match = False
            # check if it's taken by you
            if ss(issue.getStatus()) == _('taken'):
                if not threads:
                    if acl_user and issue.getACLAdder() == acl_user:
                        _taken_match = True
                    elif not acl_user and email and issue.getEmail() == email:
                        _taken_match = True
            
                elif threads:
                    # did you post a followup that changed the status?
                    for thread in threads:
                        if thread.getTitle().lower().endswith(_('taken')):
                            if acl_user and thread.getACLAdder() == acl_user:
                                _taken_match = True
                                break
                            elif not acl_user and email and thread.getEmail() == email:
                                _taken_match = True
                                break
            if _taken_match:
                keep_issues.append(dict(issue=issue, reason=_TAKEN))
                continue
            
            # check if you participated but not posted the last followup
            if threads:
                _participated = False
                if acl_user and issue.getACLAdder() == acl_user:
                    _participated = True
                elif not acl_user and email and issue.getEmail() == email:
                    _participated = True
                    
                for thread in threads[:-1]:
                    if acl_user and thread.getACLAdder() == acl_user:
                        _participated = True
                    elif not acl_user and email and thread.getEmail() == email:
                        _participated = True
                        
                if not _participated:
                    # can't have NOT had the last word
                    continue
                
                last_thread = threads[-1]
                _other_match = False
                
                # it could however be that the last thread was submitted via email.
                # Then the acl_adder test will never match, only an email match
                if last_thread.getSubmissionType()=='email':
                    if acl_user and last_thread.getEmail() != email:
                        _other_match = True
                    elif not acl_user and email and last_thread.getEmail() != email:
                        _other_match = True                    
                else:
                    if acl_user and last_thread.getACLAdder() != acl_user:
                        _other_match = True
                    elif not acl_user and email and last_thread.getEmail() != email:
                        _other_match = True
                    
                if _other_match:
                    urgency_score = urgency_scores.get(issue.getUrgency(), 1)
                    reason = (_("Because you have not had the last word"), urgency_score)
                    keep_issues.append(dict(issue=issue, reason=reason))
                    continue
                
            
            elif always_email: # no threads

                # let's only do this for those issues that are relatively young
                if today - issue.getIssueDate() > 14: 
                    # 14 days old and they can be ignore now
                    continue

                # lastly, was it not opened by you but you're one of the 
                # always-notify people
                urgency_score = urgency_scores.get(issue.getUrgency(), 1)
                # because this is least priority...:
                urgency_score -= 1
                reason = (_("Because you have been emailed about it"), urgency_score)
                keep_issues.append(dict(issue=issue, reason=reason))
                
            
        if not skip_sort:
            def sorter(x, y):
                diff = cmp(x['reason'][1], y['reason'][1])
                if diff == 0:
                    return cmp(x['issue'].getIssueDate(), y['issue'].getIssueDate())
                else:
                    return diff
            keep_issues.sort(sorter)
            keep_issues.reverse()

        r = []
        reasons_dict = {}
        for d in keep_issues:
            r.append(d['issue'])
            reasons_dict[d['issue'].getId()] = d['reason'][0]
            
        return r, reasons_dict
                
            

    def getMyIssuesAndThreads(self, sort=None, issueuser=None, 
                              include_subscriptions=False):
        """ Get all assigned issues and all issues that have
        acl_adder == issueuser or issueuser.name and
        issueuser.email == issue.name and issue.email """
        zopeuser = self.getZopeUser()
        if issueuser is None:
            issueuser = self.getIssueUser()
        if not issueuser:
            if not zopeuser:
                if include_subscriptions:
                    return [], [], [], 0, []
                else:
                    return [], [], [], 0

        if issueuser:
            acl_user = ','.join(issueuser.getIssueUserIdentifier())
        else:
            path = '/'.join(zopeuser.getPhysicalPath())
            name = zopeuser.getUserName()
            acl_user = path+','+name
            
        assignments = []
        issues = []
        subscriptionissues = []
        threads = []
        root = self.getRoot()

        # prepare with what we will compare with
        if issueuser:
            user_fullname = ss(issueuser.getFullname())
            user_email = ss(issueuser.getEmail())
        else:
            user_fullname = self.getSavedUser('fromname')
            user_email = self.getSavedUser('email')


        # a dict that keeps control of thread.absolute_url and
        # their counted number in the order it appears
        threadcounts = {}

        
        # loop through all issues
        for issue in root.getIssueObjects():
            # simplyfy fromname and email without a check from
            # the issue.
            issue_fromname = issue.getFromname(issueusercheck=0)
            issue_email = issue.getEmail(issueusercheck=0)
            if issue_fromname is None or issue_email is None:
                # an issue that is no longer attached to a username,
                # can't be matched
                continue 
            
            fromname = ss(issue_fromname)
            email = ss(issue_email)

            # check if any of it matches
            if issue.getACLAdder() == acl_user:
                issues.append(issue)
            elif unicodify(fromname) == user_fullname and \
                 email == user_email:
                issues.append(issue)
                
            if include_subscriptions:
                _subscribers = issue.getSubscribers()
                if acl_user in _subscribers or user_email in _subscribers:
                    subscriptionissues.append(issue)

            # loop through all assignments in this issue
            issue_assignments = issue.objectValues(ISSUEASSIGNMENT_METATYPE)
            if issue_assignments:
                if issue_assignments[-1].getACLAssignee() == acl_user:
                    assignments.append(issue_assignments[-1])
                    
            # loop through all threads in this issue
            count = 1
            for thread in issue.objectValues(ISSUETHREAD_METATYPE):
                # simplyfy fromname and email without a check from
                # the thread
                fromname = ss(thread.getFromname(issueusercheck=0))
                email = ss(thread.getEmail(issueusercheck=0))

                # check if any of it matches
                if thread.getACLAdder() == acl_user:
                    threads.append(thread)
                    threadcounts[thread.absolute_url()] = count
                elif unicodify(fromname) == user_fullname and \
                     email == user_email:
                    threads.append(thread)
                    threadcounts[thread.absolute_url()] = count

                count += 1

        if sort:
            _sorter = self.sortSequence
            assignments = _sorter(assignments, (('assignmentdate',),))
            assignments.reverse()
           
            issues = _sorter(issues, (('issuedate',),))
            issues.reverse()
            
            threads = _sorter(threads, (('threaddate',),))
            threads.reverse()
            
            subscriptionissues = _sorter(subscriptionissues, (('issuedate',),))
            subscriptionissues.reverse()
        
        if include_subscriptions:
            return assignments, issues, threads, threadcounts, subscriptionissues
        else:
            # legacy reasons
            return assignments, issues, threads, threadcounts

        
        
    ## Access keys stuff
    ##
    
    security.declareProtected('View', 'enableAccessKeys')
    def enableAccessKeys(self, REQUEST=None):
        """ set a user setting for AccessKeys or cookie """
        issueuser = self.getIssueUser()
        if issueuser:
            issueuser.setAccessKeys(True)
        else:
            c_key = self.getCookiekey('use_accesskeys')
            self.set_cookie(c_key, 1)
            
        msg = 'Keyboard shortcuts enabled'
        if REQUEST is not None:
            url = self.getRootURL()+'/User'
            url = Utils.AddParam2URL(url, {'changemsg':msg})
            REQUEST.RESPONSE.redirect(url)
        else:
            return msg            
        
        
    security.declareProtected('View', 'disableAccessKeys')
    def disableAccessKeys(self, REQUEST=None):
        """ set a user setting for AccessKeys or cookie """
        issueuser = self.getIssueUser()
        if issueuser:
            issueuser.setAccessKeys(False)
        else:
            c_key = self.getCookiekey('use_accesskeys')
            self.set_cookie(c_key, 0)

        msg = 'Keyboard shortcuts disabled'
        if REQUEST is not None:
            url = self.getRootURL()+'/User'
            url = Utils.AddParam2URL(url, {'changemsg':msg})
            REQUEST.RESPONSE.redirect(url)
        else:
            return msg
            

    ## Remember Savedfilter Persistently stuff
    ##
    
    security.declareProtected('View', 'enableRememberSavedfilterPersistently')
    def enableRememberSavedfilterPersistently(self, REQUEST=None):
        """ remember that the user wants to remember filters persistently """
        issueuser = self.getIssueUser()
        if issueuser:
            issueuser.setRememberSavedfilterPersistently(True)
        else:
            c_key = self.getCookiekey('remember_savedfilter_persistently')
            self.set_cookie(c_key, 1)
            
        msg = 'Used filter will be remembered persistently'
        if REQUEST is not None:
            url = self.getRootURL()+'/User'
            url = Utils.AddParam2URL(url, {'changemsg':msg})
            REQUEST.RESPONSE.redirect(url)
        else:
            return msg
        
    
    security.declareProtected('View', 'disableRememberSavedfilterPersistently')
    def disableRememberSavedfilterPersistently(self, REQUEST=None):
        """ remember that the user wants to remember filters persistently """
        issueuser = self.getIssueUser()
        if issueuser:
            issueuser.setRememberSavedfilterPersistently(False)
        else:
            c_key = self.getCookiekey('remember_savedfilter_persistently')
            self.set_cookie(c_key, 0)
        
        m = 'Used filters will only be remembered within the session'
        if REQUEST is not None:
            url = self.getRootURL()+'/User'
            url = Utils.AddParam2URL(url, {'changemsg':m})
            REQUEST.RESPONSE.redirect(url)
        else:
            return m
        
        
    ## Use 'Your next action issues'
    ##
    
    security.declareProtected('View', 'enableShowNextactionIssues')
    def enableShowNextactionIssues(self, REQUEST=None):
        """ remember that the user wants to show next actions on the homepage """
        issueuser = self.getIssueUser()
        if issueuser:
            issueuser.setUseNextActionIssues(True)
        else:
            c_key = self.getCookiekey('show_nextactions')
            self.set_cookie(c_key, 1)
            
        msg = "'Your next actions issues' shown on home page"
        if REQUEST is not None:
            url = self.getRootURL()+'/User'
            url = Utils.AddParam2URL(url, {'changemsg':msg})
            REQUEST.RESPONSE.redirect(url)
        else:
            return msg
        
    security.declareProtected('View', 'disableShowNextactionIssues')
    def disableShowNextactionIssues(self, REQUEST=None):
        """ remember that the user wants to show next actions on the homepage """
        issueuser = self.getIssueUser()
        if issueuser:
            issueuser.setUseNextActionIssues(False)
        else:
            c_key = self.getCookiekey('show_nextactions')
            self.set_cookie(c_key, 0)
            
        msg = "No 'Your next actions issues' on home page"
        if REQUEST is not None:
            url = self.getRootURL()+'/User'
            url = Utils.AddParam2URL(url, {'changemsg':msg})
            REQUEST.RESPONSE.redirect(url)
        else:
            return msg      
        
    ## AutoLogin stuff
    ##
    
    def testAutoLogin(self):
        """ return "" or redirect to login """
        do_redirect = False
        if not self.get_session('tested_autologin'):
            # make sure we never have to do this again in the 
            # near future
            self.set_session('tested_autologin',1)
            
            # check if the user has the cookie to True
            if self.doAutoLogin():
                # proceed only if user us anonymous
                #a_user = self.REQUEST.AUTHENTICATED_USER
                a_user = getSecurityManager().getUser()
                user_roles = a_user.getRolesInContext(self)
                if 'Anonymous' in user_roles:
                    do_redirect = True
            
        if do_redirect:
            loginlink = self.ManagerLink(absolute_url=True)
            self.REQUEST.RESPONSE.redirect(loginlink)
        else:
            return ""
        
        
    def showAutoLoginOption(self):
        """ return True if there is a point to having the auto login
        checkbox displayed. """
        #
        # We might want to crawl further up the tree
        # to see if the view permission is switched off
        # there too.
        #
        if self.isViewPermissionOn():
            return True
        else:
            return False
    
    def doAutoLogin(self):
        """ return True if this user has enabled the cookie for
        auto_login """
        c_key = self.getCookiekey('autologin')
        default = 0
        value = self.get_cookie(c_key, default)
        try:
            value = int(value)
        except ValueError:
            value = default
        return not not value
        
    security.declareProtected('View', 'enableAutoLogin')
    def enableAutoLogin(self, REQUEST=None):
        """ set a cookie for autologin """
        c_key = self.getCookiekey('autologin')
        self.set_cookie(c_key, 1)
        msg = 'Auto login enabled'
        if REQUEST is not None:
            url = self.getRootURL()+'/User'
            url = Utils.AddParam2URL(url, {'changemsg':msg})
            REQUEST.RESPONSE.redirect(url)
        else:
            return msg
        
        
    security.declareProtected('View', 'disableAutoLogin')
    def disableAutoLogin(self, REQUEST=None):
        """ set a cookie for autologin """
        c_key = self.getCookiekey('autologin')
        self.set_cookie(c_key, 0)
        
        msg = 'Auto login disabled'
        if REQUEST is not None:
            url = self.getRootURL()+'/User'
            url = Utils.AddParam2URL(url, {'changemsg':msg})
            REQUEST.RESPONSE.redirect(url)
        else:
            return msg
            
            
            

    security.declareProtected('View', 'changeUserOptions')
    def changeUserOptions(self, remember_savedfilter_persistently=False,
        autologin=False, use_accesskeys=False, 
        show_nextactions=False, REQUEST=None):
        """ if you submit the form on User.zpt that asks the various 
        questions such as use accesskeys, autologin and persistent 
        filters this is the method it goes to. It means that we 
        have to assume false for all those options and call the 
        various enable* and disable* functions above. """
        msgs = []
        
        was_remember = self.rememberSavedfilterPersistently()
        if remember_savedfilter_persistently:
            m = self.enableRememberSavedfilterPersistently()
            if not was_remember:
                msgs.append(m)
        else:
            m = self.disableRememberSavedfilterPersistently()
            if was_remember:
                msgs.append(m)

            
        was_autologin = self.doAutoLogin()
        if autologin:
            m = self.enableAutoLogin()
            if not was_autologin:
                msgs.append(m)
        else:
            m = self.disableAutoLogin()
            if was_autologin:
                msgs.append(m)
            
        was_use_accesskeys = self.useAccessKeys()
        if use_accesskeys:
            m = self.enableAccessKeys()
            if not was_use_accesskeys:
                msgs.append(m)
        else:
            m = self.disableAccessKeys()
            if was_use_accesskeys:
                msgs.append(m)
                
        was_show_nextactions = self.showNextActionIssues()
        if show_nextactions:
            m = self.enableShowNextactionIssues()
            if not was_show_nextactions:
                msgs.append(m)
        else:
            m = self.disableShowNextactionIssues()
            if was_show_nextactions:
                msgs.append(m)                
            
        msg = ', '.join(msgs)
        if REQUEST is not None:
            url = self.getRootURL()+'/User'
            url = Utils.AddParam2URL(url, {'changemsg':msg})
            REQUEST.RESPONSE.redirect(url)
        else:
            return msg
        
        

    security.declareProtected('View', 'UserChangeDetails')
    def UserChangeDetails(self, fullname, email, display_format, REQUEST=None):
        """ change the password of the issueuser object """
        SubmitError = {}
        
        issueuser = self.getIssueUser()
        cmfuser = self.getCMFUser()
        zopeuser = self.getZopeUser()
        
        if not (issueuser or cmfuser or zopeuser):
            raise "Unauthorized", "Not logged in"
        
        if issueuser:
            path = issueuser.getIssueUserIdentifier()[0]
            userfolder = self.unrestrictedTraverse(path)
            user = userfolder.data[issueuser.getUserName()]

        # perform some checking
        if not fullname.strip():
            SubmitError['fullname'] = "Missing"
        if not email.strip():
            SubmitError['email'] = "Missing"
        elif not Utils.ValidEmailAddress(email.strip()):
            SubmitError['email'] = "Invalid"
            
        

        if SubmitError and REQUEST is not None:
            REQUEST.set('change','details')
            return self.User(REQUEST, SubmitError=SubmitError)
        elif SubmitError:
            raise "SubmitError", SubmitError
        
        
        # Go on, make the changes

        # 1. Change the details of the user object
        fullname = unicodify(fullname.strip())
        email = email.strip()
        if issueuser:
            userfolder._changeUserDetails(issueuser.name, fullname, email)
            issueuser.setDisplayFormat(display_format)
            # Change all issues and followups
            # since when this user adds an issue or followup the fullname and
            # email is stored too.
            self._changeACLadds(issueuser or zopeuser, fullname, email)
            
        elif cmfuser and CMF_getToolByName:
            mtool = CMF_getToolByName(self, 'portal_membership')
            authenticated_member = mtool.getAuthenticatedMember()
            authenticated_member.setProperties(fullname=fullname)
            authenticated_member.setProperties(email=email)
            #XXX not yet self._changeACLadds(self, 
            
        else:
            self.set_cookie(self.getCookiekey('fullname'), fullname)
            self.setACLCookieName(fullname)
            
            self.set_cookie(self.getCookiekey('email'), email)
            self.setACLCookieEmail(email)

            self.set_cookie(self.getCookiekey('display_format'), display_format)
            self.setACLCookieDisplayformat(display_format)

        # Leave
        m = "Details changed"
        if REQUEST is not None:
            url = self.getRoot().absolute_url()+'/User'
            url += '?changemsg=%s'%Utils.url_quote_plus(m)
            REQUEST.RESPONSE.redirect(url)
        else:
            return m
        
        
        
    security.declareProtected('View', 'IssueUserChangeDetails')
    def IssueUserChangeDetails(self, fullname, email, REQUEST=None):
        """ change the password of the issueuser object """
        SubmitError = {}
        
        issueuser = self.getIssueUser()
        if not issueuser:
            m = "Not logged in as a user of Issue User Folder"
            raise "NoIssueUser", m

        path = issueuser.getIssueUserIdentifier()[0]
        userfolder = self.unrestrictedTraverse(path)
        user = userfolder.data[issueuser.getUserName()]

        # perform some checking
        if not fullname.strip():
            SubmitError['fullname'] = "Missing"
        if not email.strip():
            SubmitError['email'] = "Missing"
        elif not Utils.ValidEmailAddress(email.strip()):
            SubmitError['email'] = "Invalid"

        if SubmitError and REQUEST is not None:
            REQUEST.set('change','details')
            return self.User(REQUEST, SubmitError=SubmitError)
        elif SubmitError:
            raise "SubmitError", SubmitError

        # Go on, make the changes

        # 1. Change the details of the user object
        fullname = fullname.strip()
        email = email.strip()
        userfolder._changeUserDetails(issueuser.name, fullname, email)

        # 2. Change all issues and followups
        # since when this user adds an issue or followup the fullname and
        # email is stored too.
        self._changeACLadds(issueuser, fullname, email)

        # Leave
        m = "Details changed"
        if REQUEST is not None:
            url = self.getRoot().absolute_url()+'/User'
            url += '?changemsg=%s'%Utils.url_quote_plus(m)
            REQUEST.RESPONSE.redirect(url)
        else:
            return m

    def _changeACLadds(self, issueuser, fullname, email):
        """ change the fromname and email of all issues and threads
        that belong to this issueuser """
        data = self.getMyIssuesAndThreads(sort=None, issueuser=issueuser)
        assignments, issues, threads, threadcounts = data
        
        for issue in issues:
            issue.fromname = fullname
            issue.email = email

        for thread in threads:
            thread.fromname = fullname
            thread.email = email

        for assignment in assignments:
            assignment.fromname = fullname
            assignment.email = email


    def IssueUserChangePasswordFirsttime(self, new, confirm, REQUEST, came_from=None):
        """ accompanying method to the 'User_must_change_password'
        template. The difference between this method and that
        of IssueUserChangePassword() is that here we don't require
        to match the old password and the user object must be such
        that he has to change password (using mustChangePassword())
        """
        
        SubmitError = {}

        # Check 1. Must be a IssueUser()
        issueuser = self.getIssueUser()
        if not issueuser:
            m = "Not logged in as a user of Issue User Folder"
            raise "NoIssueUser", m

        # Check 2. Must have to change password
        if not issueuser.mustChangePassword():
            m = "You do not *have* to change password"
            raise "NoMustChangePassword", m

        path = issueuser.getIssueUserIdentifier()[0]
        userfolder = self.unrestrictedTraverse(path)
            
        # Check 3. Is the new password good enough
        if not new:
            SubmitError['new'] = "Empty"
        elif new != confirm:
            SubmitError['confirm'] = "Mismatch"
        else:
            # they might be lazy and set a new one that is
            # identical to the old. That is wrong.
            
            user = userfolder.data[issueuser.getUserName()]
            if userfolder._isPasswordEncrypted(user._getPassword()):
                if userfolder._encryptPassword(new) == user._getPassword():
                    SubmitError['new'] = "Not different from before"
            else:
                if new == user._getPassword():
                    SubmitError['new'] = "Not different from before"

        if SubmitError:
            page = self.User_must_change_password
            return page(self, REQUEST, SubmitError=SubmitError)
        #else:

        # cool, let's do it!
        vars = {'name':issueuser.getUserName(),
                'password':new,
                'confirm':confirm,
                'roles':issueuser.getRoles()}
        ok = userfolder.manage_users(submit="Change", REQUEST=vars)

        # report back that this has been done
        issueuser._unmust_mustChangePassword()

        issueuser.authenticate(new, REQUEST)

        if came_from:
            url = came_from
        else:
            url = self.getRoot().absolute_url()+'/User'

        REQUEST.RESPONSE.redirect(url)
            
        
        
#    security.declareProtected(PERM_ACCESS_ISSUEUSER_INFORMATION,
#                              'IssueUserChangePassword')
    def IssueUserChangePassword(self, old, new, confirm, 
                                REQUEST=None):
        """ change the password of the issueuser object """
        SubmitError = {}
        
        issueuser = self.getIssueUser()
        if not issueuser:
            m = "Not logged in as a user of Issue User Folder"
            raise "NotIssueUser", m

        path = issueuser.getIssueUserIdentifier()[0]
        userfolder = self.unrestrictedTraverse(path)
        user = userfolder.data[issueuser.getUserName()]
        if userfolder._isPasswordEncrypted(user._getPassword()):
            if not userfolder._encryptPassword(old) == user._getPassword():
                SubmitError['old'] = "Incorrect"
        else:
            if not old == user._getPassword():
                SubmitError['old'] = "Incorrect"

        # Check that the new password matches the second
        if not new:
            SubmitError['new'] = "Empty"
        elif new != confirm:
            SubmitError['confirm'] = "Mismatch"
            

        # Did everything work as expected?
        if SubmitError and REQUEST is not None:
            page = self.User
            REQUEST.set('change', 'password')
            return page(REQUEST, SubmitError=SubmitError)
        elif SubmitError:
            raise "SubmitError", SubmitError

        # Cool, let's move on
        vars = {'name':issueuser.getUserName(),
                'password':new,
                'confirm':confirm,
                'roles':issueuser.getRoles()}
        ok = userfolder.manage_users(submit="Change", REQUEST=vars)

        issueuser._unmust_mustChangePassword()

        issueuser.authenticate(new, REQUEST)

        m = "Password changed"
        if REQUEST is not None:
            url = self.getRoot().absolute_url()+'/User'
            url += '?changemsg=%s'%Utils.url_quote_plus(m)
            REQUEST.RESPONSE.redirect(url)
        else:
            return m
        
        

    ## Overridden template definitions

    def getDraftsContainer(self):
        """ makes sure and returns a folder where the drafts are saved """
        root = self.getRoot()
        folderid = DRAFTSFOLDER_ID
        if not folderid in root.objectIds(['Folder','BTreeFolder2']):
            _adder = root.manage_addFolder
            if self.manage_canUseBTreeFolder():
                try:
                    _adder = root.manage_addProduct['BTreeFolder2'].manage_addBTreeFolder
                except:
                    pass
            _adder(folderid)

        return getattr(root, folderid)

    
    def getMyFollowupDrafts(self, skip_draft_id=None, autosaved_only=False):
        """ return a list of thread draft objects """
        
        if not self.SaveDrafts():
            return []
        
        ids = self._getDraftThreadIds()
        container = self.getDraftsContainer()
        objects = []
        for id in ids:
            if id == skip_draft_id:
                continue
            
            if hasattr(container, id):
                object = getattr(container, id)
                if object.meta_type == ISSUETHREAD_DRAFT_METATYPE:
                    if not autosaved_only or object.isAutoSave():
                        objects.append(object)
                        
        return objects
    

    def _getDraftThreadIds(self, separate=False):
        """ return the possible draft ids (of threads) for this user """
        c_key = self.getCookiekey('draft_followup_ids')
        c_key = self.defineInstanceCookieKey(c_key)
        #ids_cookie = self.get_cookie(c_key, '')
        # in the code cleanup the variable 'draft_thread_id(s)' was changed to 
        # 'draft_followup_id(s)'. For legacy reasons we here dig out if the
        # user has some old cookies left under that name. This legacy hack 
        # can be removed in 2006.
        _legacy_c_key = '__issuetracker_draft_thread_ids'
        ids_cookie = self.get_cookie(c_key, self.get_cookie(_legacy_c_key, ''))
        
        ids_cookie = [x.strip() for x in ids_cookie.split('|') if x.strip()]
        
        issueuser = self.getIssueUser()
        ids_user = []
        if issueuser:
            container = self.getDraftsContainer()
            all_draftobjects = container.objectValues(ISSUETHREAD_DRAFT_METATYPE)
            acl_adder = ','.join(issueuser.getIssueUserIdentifier())
            for draft in all_draftobjects:
                if draft.getACLAdder()==acl_adder:
                    ids_user.append(draft.getId())
            

        if separate:
            return Utils.uniqify(ids_cookie), Utils.uniqify(ids_user)
        else:
            return Utils.uniqify(ids_cookie+ids_user)
        


            
    def getMyIssueDrafts(self, skip_draft_issue_id=None, autosaved_only=False):
        """ return a list of issue draft objects """
        if not self.SaveDrafts():
            return []
        
        ids = self._getDraftIssueIds()
        if not ids:
            return []
        
        container = self.getDraftsContainer()
        objects = []
        for id in ids:
            if id == skip_draft_issue_id:
                continue
            
            if hasattr(container, id):
                object = getattr(container, id)
                if object.meta_type == ISSUE_DRAFT_METATYPE:
                    if not autosaved_only or object.isAutoSave():
                        objects.append(object)

        return objects

    def getMyIssueDraftsSeparated(self):
        """ return a tuple of length 2 of issue drafts and autosaved issues """
        drafts=[]; autosaves=[]
        for draft in self.getMyIssueDrafts():
            if draft.isAutoSave():
                autosaves.append(draft)
            else:
                drafts.append(draft)
        return drafts, autosaves

    def _getDraftIssueIds(self, separate=False):
        """ return the possible draft ids we have """    
        c_key = self.getCookiekey('draft_issue_ids')
        c_key = self.defineInstanceCookieKey(c_key)
        ids_cookie = self.get_cookie(c_key, '')
        ids_cookie = [x.strip() for x in ids_cookie.split('|') if x.strip()]
        
        issueuser = self.getIssueUser()
        ids_user = []
        if issueuser:
            container = self.getDraftsContainer()
            all_draftobjects = container.objectValues(ISSUE_DRAFT_METATYPE)
            acl_adder = ','.join(issueuser.getIssueUserIdentifier())
            for draft in all_draftobjects:
                if draft.getACLAdder()==acl_adder:
                    ids_user.append(draft.getId())
            

        if separate:
            return Utils.uniqify(ids_cookie), Utils.uniqify(ids_user)
        else:
            return Utils.uniqify(ids_cookie+ids_user)
    

    def _dropDraftIssue(self, id):
        """ remove this draft issue object if it exists """
        container = self.getDraftsContainer()

        # remove potential client cookie
        ids_cookie, ids_user = self._getDraftIssueIds(separate=True)
        issueuser = self.getIssueUser()
        if id in ids_cookie:
            ids_cookie.remove(id)
        
        # shorten the list of ids_cookie to only contain those
        # where draft objects exits
        ids_cookie = [x for x in ids_cookie if hasattr(container, x)]
        all_draft_ids = '|'.join(ids_cookie)
        c_key = self.getCookiekey('draft_issue_ids')
        c_key = self.defineInstanceCookieKey(c_key)
        if all_draft_ids:
            self.set_cookie(c_key, all_draft_ids, days=14)
        else:
            self.expire_cookie(c_key)
            

        # remove draft object
        if hasattr(container, id):
            container.manage_delObjects([id])

    def _dropMatchingDraftIssues(self, issue):
        """ delete (if any) all issue drafts that match this issue """
        title = issue.getTitle()
        description = issue.getDescription()
        
        del_draft_ids = []
        container = self.getDraftsContainer()
        
        # the requirement for matching what to delete is if a draft matches
        # either:
        #   - exactly on title and description
        #   - exactly on title, starts on description
        #   - starts on title, exactly on description
        
        for draft in container.objectValues(ISSUE_DRAFT_METATYPE):
            if not draft.getTitle() or not draft.getDescription(): # odd draft!
                continue
            
            draft_desc = unicodify(draft.getDescription())
            draft_title = unicodify(draft.getTitle())
            if draft_title == title and draft_desc == description:
                self._dropDraftIssue(draft.getId())
            elif title.startswith(draft_title) and draft_desc == description:
                self._dropDraftIssue(draft.getId())
            elif description.startswith(draft_desc) and draft_title == title:
                self._dropDraftIssue(draft.getId())
                

    def _createDraftIssue(self, id):
        """ create a draftissue and return it """
        root = self.getDraftsContainer()
        inst = IssueTrackerDraftIssue(id)
        root._setObject(id, inst)
        object = root._getOb(id)
        return object
    
    def showExternalEditorDraftLink(self, draft_issue_id):
        """ return the link for the AddIssue template """
        if not draft_issue_id:
            return ""
        if not _has_ExternalEditor:
            return ""
        container = self.getDraftsContainer()
        if not hasattr(container, draft_issue_id):
            return ""
        #draftobjects = getattr(container, draft_issue_id)
        url = container.absolute_url()+'/externalEdit_/'+draft_issue_id
        out = '<a href="%s" title="Edit using external editor">'%url
        out += '<img src="/misc_/ExternalEditor/edit_icon" '\
               'align="middle" hspace="2" '\
                   'alt="External Editor" border="0" />'
        out += '</a>'
        return out
        


    security.declareProtected('View', 'DeleteDraftIssue')
    def DeleteDraftIssue(self, id, return_show_drafts_simple=False,
                         return_show_drafts=False,
                         REQUEST=None):
        """ delete this id from issue user or cookies and delete the
        draft issue object. """
        ids_cookie, ids_user = self._getDraftIssueIds(separate=True)
        matched = False
        
        if id in ids_cookie:
            matched = True
            ids_cookie.remove(id)
            # save this
            c_key = self.getCookiekey('draft_issue_ids')
            c_key = self.defineInstanceCookieKey(c_key)
            all_draft_ids = '|'.join(ids_cookie)
            self.set_cookie(c_key, all_draft_ids, days=14)

        issueuser = self.getIssueUser()
        if id in ids_user and issueuser:
            matched = True

        if matched:
            # mark the draft issue as obsolete
            container = self.getDraftsContainer()
            container.manage_delObjects([id])
            
        if Utils.niceboolean(return_show_drafts_simple):
            # Exceptional case where we render and return the show_drafts_simple 
            # template again.
            return self.show_drafts_simple(self, self.REQUEST)
        elif Utils.niceboolean(return_show_drafts):
            # Another exceptional case where we render and return the
            # show_drafts template. This featurette is exploited by
            # the AJAX calling DeleteDraftIssue from index_html
            return self.show_drafts(self, self.REQUEST)

        if REQUEST is not None:
            if REQUEST.get('back','').lower() == 'home':
                url = self.absolute_url()
            else:
                url = self.absolute_url()+'/AddIssue'
            REQUEST.RESPONSE.redirect(url)
            
            
    security.declareProtected('View', 'DeleteDraftFollowup')
    def DeleteDraftFollowup(self, id, return_show_drafts_simple=False,
                         return_show_drafts=False,
                         REQUEST=None):
        """ delete this id from issue user or cookies and delete the
        draft issue object. """
        ids_cookie, ids_user = self._getDraftThreadIds(separate=True)
        matched = False
        issueID = None
        
        if id in ids_cookie:
            matched = True
            ids_cookie.remove(id)
            # save this
            c_key = self.getCookiekey('draft_thread_ids')
            c_key = self.defineInstanceCookieKey(c_key)
            all_draft_ids = '|'.join(ids_cookie)
            self.set_cookie(c_key, all_draft_ids, days=14)

        issueuser = self.getIssueUser()
        if id in ids_user and issueuser:
            matched = True

        if matched:
            # mark the draft issue as obsolete
            container = self.getDraftsContainer()
            if hasattr(container, id):
                draft = getattr(container, id)
                issueID = draft.getIssueId()
                container.manage_delObjects([id])
            
        if Utils.niceboolean(return_show_drafts_simple):
            # Exceptional case where we render and return the show_drafts_simple 
            # template again.
            return self.show_drafts_simple(self, self.REQUEST)
        elif Utils.niceboolean(return_show_drafts):
            # Another exceptional case where we render and return the
            # show_drafts template. This featurette is exploited by
            # the AJAX calling DeleteDraftIssue from index_html
            return self.show_drafts(self, self.REQUEST)

        if REQUEST is not None:
            if REQUEST.get('back','').lower() == 'home':
                url = self.absolute_url()
            elif issueID:
                url = self.absolute_url()+'/%s' % issueID
            else:
                url = self.absolute_url()
            REQUEST.RESPONSE.redirect(url)
            
            
        
    security.declareProtected('View', 'SaveDraftIssue')
    def SaveDraftIssue(self, REQUEST, draft_issue_id=None,
                       prevent_preview=True,
                       *args, **kw):
        """ basically just show AddIssue again except that we
        save a draft on the side. """
            
        if prevent_preview:
            REQUEST.set('previewissue', False)

        __saver = self._saveDraftIssue
        if self.SaveDrafts() and \
               (\
                 (draft_issue_id is None and self._reason2saveDraft(REQUEST)) \
                 or \
                 draft_issue_id is not None \
               ):

            draft_issue_id = __saver(REQUEST, draft_issue_id)
            
            kw['draft_issue_id'] = draft_issue_id
            kw['draft_saved'] = True
            
        return self.AddIssue(REQUEST, *args, **kw)
    
    
    security.declareProtected('View', 'AutoSaveDraftIssue')
    def AutoSaveDraftIssue(self, REQUEST, draft_issue_id=None):
        """ called potentially by the Ajax script """

        _saver = self._saveDraftIssue
        if self.SaveDrafts() and REQUEST.form and \
               (\
                 (not draft_issue_id and self._reason2saveDraft(REQUEST)) \
                 or \
                 draft_issue_id \
               ):

            draft_issue_id = _saver(REQUEST, draft_issue_id, is_autosave=True)
            return draft_issue_id
        else:
            return ""

    def _reason2saveDraft(self, request):
        """ no draft has been created. Inspect this 'request' see if
        there is reason enough to save a draft. """
        enough_request_data = False
            
        for key in ('title','description'):
            if Utils.SimpleTextPurifier(request.get(key,'')):
                enough_request_data = True
                break
        
        if enough_request_data:    
            # check that a draft like this doesn't exist already
            _finder = self._findMatchingIssueDraft
            draft = _finder(unicodify(request.get('title','')),
                            unicodify(request.get('description','')))
            if draft:
                return False
        
        return enough_request_data
    
    def _findMatchingIssueDraft(self, title, description):
        """ return drafts that match exactly. Return None if nothing found """
        container = self.getDraftsContainer()
        draftobjects = container.objectValues(ISSUE_DRAFT_METATYPE)
        for draft in draftobjects:
            if unicodify(draft.title) == title and unicodify(draft.description) == description:
                return draft
        return None
        

    def _saveDraftIssue(self, REQUEST, draft_issue_id=None, is_autosave=False):
        """ return the id this created """
        draftscontainer = self.getDraftsContainer()
        if draft_issue_id:
            if not hasattr(draftscontainer, draft_issue_id):
                # you're lying!
                draft_issue_id = None 

        if not draft_issue_id:
            # need to create a draft issue object
            id = self.generateID(5, prefix='issue-',
                                 meta_type=ISSUE_DRAFT_METATYPE,
                                 incontainer=draftscontainer
                                 )
            # create a draft issue
            draftissue = self._createDraftIssue(id)
            draft_issue_id = id
        else:
            draftissue = getattr(draftscontainer, draft_issue_id)

        issueuser = self.getIssueUser()
        acl_adder = None
        if issueuser:
            acl_adder = ','.join(issueuser.getIssueUserIdentifier())
            
        # now, populate this draftissue with as much data as
        # we can find
        modifier = draftissue.ModifyIssue
        rget = REQUEST.get
        
        modifier(title=unicodify(rget('title')),
                 description=unicodify(rget('description')),
                 fromname=unicodify(rget('fromname')),
                 email=rget('email'),
                 acl_adder=acl_adder,
                 display_format=rget('display_format', self.getSavedTextFormat()),
                 status=rget('status'),
                 type=rget('type'),
                 urgency=rget('urgency'),
                 sections=rget('sections'),
                 url2issue=rget('url2issue'),
                 confidential=rget('confidential'),
                 hide_me=rget('hide_me'),
                 is_autosave=is_autosave,
                 Tempfolder_fileattachments=rget('Tempfolder_fileattachments'),
                 )

        # remember this
        issueuser = self.getIssueUser()
        if not issueuser:
            # stick this in a cookie
            c_key = self.getCookiekey('draft_issue_ids')
            c_key = self.defineInstanceCookieKey(c_key)
            all_draft_ids = self._getDraftIssueIds()
            if draft_issue_id not in all_draft_ids:
                all_draft_ids.append(draft_issue_id)
                all_draft_ids = '|'.join(all_draft_ids)
                self.set_cookie(c_key, all_draft_ids, days=14)
            
        return draft_issue_id

    def _getIssueDraftObject(self, id):
        """ return the object from the id """
        container = self.getDraftsContainer()
        return getattr(container, id, None)


    def getWhoYouAre(self, issueuser=None):
        """ return the issueuser identifier or '' for this current issueuser """
        if issueuser is None:
            return ""
        else:
            return issueuser.getIssueUserIdentifierstring()
        
    def Cancel(self, REQUEST, *args, **kw):
        """ Button pressable when in form_followup. """
        return REQUEST.RESPONSE.redirect(self.absolute_url())

    
    def AddIssue(self, REQUEST, *args, **kw):
        """ Override this template so we can upload temp file
        attachments when needing to """
        try:
            self._uploadTempFiles()
        except "NotAFile":
            REQUEST.set('previewissue', None)
            m = _("Filename entered but no actual file content")
            if kw.has_key('SubmitError'):
                kw['SubmitError']['fileattachment'] = m
            else:
                kw['SubmitError'] = {'fileattachment':m}

        if REQUEST.get('previewissue') and self.SaveDrafts():
            draft_issue_id = REQUEST.get('draft_issue_id')
            draft_issue_id = self._saveDraftIssue(REQUEST, draft_issue_id)
            if draft_issue_id:
                REQUEST.set('draft_issue_id', draft_issue_id)
                kw['draft_saved'] = True
        elif REQUEST.get('draft_issue_id') and self.SaveDrafts():
            object = self._getIssueDraftObject(REQUEST.get('draft_issue_id'))
            if object:
                object.populateREQUEST(REQUEST)

        return self.AddIssueTemplate(self, REQUEST, **kw)
    
    def getPreviewSections(self):
        """ Return a string of suitable sections. 
        Helper for when you preview the issue. """
        newsection = None
        rget = self.REQUEST.get
        if self.CanAddNewSections() and rget('newsection'):
            if rget('newsection') != 'New section...':
                newsection = rget('newsection')
                
        sections = rget('sections', [])
        if newsection:
            sections.insert(0, newsection)
            
        sections = Utils.uniqify(sections)
        
        return ', '.join(sections)

    def QuickAddIssue(self, REQUEST, **kw):
        """ override this template if we need to do anything special
        before we show the template """
        return self.QuickAddIssueTemplate(self, REQUEST, **kw)

    def AddManyIssues(self, REQUEST, **kw):
        """ override this template if we need to do anything special
        before we show the template """
        return self.AddManyIssuesTemplate(self, REQUEST, **kw)

    def _getListsToExpand(self):
        """ the user is either a Zope ACL user or a IssueTracker User.
        Inspect their data and cookies for information about which lists
        to expand on the User page. """
        issueuser = self.getIssueUser()
        zopeuser = self.getZopeUser()

        all_possible = POSSIBLE_USER_LISTS

        if issueuser:
            lists = issueuser.getUserLists()
            if lists is None:
                return all_possible
            else:
                return lists

        #elif zopeuser:
            
        # Need to rely on cookies :(
        if self.REQUEST.get('_user_lists_request'):
            return self.REQUEST.get('_user_lists_request')
        elif self.has_cookie('_user_lists'):
            stringlist = self.get_cookie('_user_lists')
            return stringlist.split(',')
        else:
            self.set_cookie('_user_lists', ','.join(all_possible))
            return all_possible

        #else:
        #    # something's gone wrong
        #    return []


    def _setListsToExpand(self, newlist):
        """ save it to user or zope user (cookie) """
        issueuser = self.getIssueUser()
        zopeuser = self.getZopeUser()

        if issueuser:
            issueuser.setUserLists(newlist)
        
        self.set_cookie('_user_lists', ','.join(newlist))
        self.REQUEST.set('_user_lists_request', newlist)
            

    def _changeListsToExpand(self, hide=[], add=[]):
        """ change the user list the user has """
        before = self._getListsToExpand()
        all_possible = POSSIBLE_USER_LISTS

        if not Utils.same_type(hide, []):
            hide = [hide]
        for each in hide:
            if each in before:
                before.remove(each)

        if not Utils.same_type(add, []):
            add = [add]
        for each in add:
            if each in all_possible:
                before.append(each)

        self._setListsToExpand(Utils.uniqify(before))
            

    def User(self, REQUEST, **kw):
        """ Override this template and pass also the myissues and
        mythreads from getMyIssuesAndThreads() """

        # 1. Make sure we're logged in
        if self.getZopeUser() is None and self.getIssueUser() is None:
            REQUEST.RESPONSE.redirect(self.ManagerLink(absolute_url=True))
            return 
         
        # 2. Potentially modify user_lists
        if REQUEST.get('hide'):
            self._changeListsToExpand(hide=REQUEST.get('hide'))
        elif REQUEST.get('expand'):
            self._changeListsToExpand(add=REQUEST.get('expand'))

        # 3. Get the assignments, issues and threads
        data = self.getMyIssuesAndThreads(sort=True, include_subscriptions=1)

        myassignments, myissues, mythreads, threadcounts, mysubscriptions = data

        kw['myassignments'] = myassignments
        kw['myissues'] = myissues
        kw['mythreads'] = mythreads
        kw['threadcounts'] = threadcounts
        kw['mysubscriptions'] = mysubscriptions
        kw['user_lists'] = self._getListsToExpand()

        # Since we might be using CheckoutableTemplates and macro
        # templates are very special we are forced to do the following
        # magic to get the macro 'standard' from a potentially checked
        # out StandardHeader
        zodb_id = 'User.zpt'
        template = getattr(self, zodb_id, self.UserTemplate)
        return apply(template, (self, REQUEST), kw)


    def getMyIssues(self, i):
        """ return a sequence of issue objects that belong to this
        user. 
        """
        if ss(i) == 'assigned':
            data = self.getMyIssuesAndThreads()
            myassignments = data[0]
            issues = []
            for assignment in myassignments:
                if assignment.aq_parent not in issues:
                    issues.append(assignment.aq_parent)
        
        elif ss(i) == 'added':
            data = self.getMyIssuesAndThreads()
            #myassignments, myissues, mythreads, threadcounts = data
            issues = data[1]

        elif ss(i) == 'followedup':
            data = self.getMyIssuesAndThreads()
            mythreads = data[2]
            issues = []
            for thread in mythreads:
                if thread.aq_parent not in issues:
                    issues.append(thread.aq_parent)
                    
        elif ss(i) == 'subscribed':
            data = self.getMyIssuesAndThreads(include_subscriptions=1)
            #myassignments, myissues, mythreads, threadcounts, subscriptions = data
            issues = data[4]

                    
        return issues
    
    def getUserAchievements(self):
        """ return a dict of dicts which (at the deepest level) tells
        how many issues you have opened and closed within each level
        of timeperiod.
        The dict should then look like this:
            {'today': {'opened':2, 'closed':3},
             'week': {'opened':4, 'closed':9},
             'last_week': {'opened':12, 'closed':3},
             'month': {'opened':23, 'closed':18},
             'last_month': {'opened':33, 'closed':8},
             'ever': {'opened':79, 'closed':49},
            }
        For each key in the dict, don't include it if the value is
        {'opened':0, 'closed':0}
        """
        
        statuses_closed = self.getStatuses()[-2:]
        
        bucket = {}
        today = DateTime()
        yesterday = today - 1
        last_week = DateTime()-7
        yyyy = int(today.strftime('%Y'))
        mm = int(today.strftime('%m'))
        last_month = mm -1
        if last_month < 1:
            last_month = 12
            yyyy -= 1
        

        today_date = today.strftime('%Y%m%d')
        yesterday_date = today.strftime('%Y%m%d')
        this_week_date = today.strftime('%U%Y')
        last_week_date = last_week.strftime('%U%Y')
        this_month_date = today.strftime('%Y%m')
        last_month_date = '%s%s' % (yyyy, last_month)
        
        zopeuser = self.getZopeUser()
        issueuser = self.getIssueUser()
        acl_user = None
        if issueuser:
            acl_user = ','.join(issueuser.getIssueUserIdentifier())
            fromname = ss(issueuser.getFullname())
            email = ss(issueuser.getEmail())
        else:
            if zopeuser:
                path = '/'.join(zopeuser.getPhysicalPath())
                name = zopeuser.getUserName()
                acl_user = path+','+name
            fromname = ss(self.getSavedUser('fromname'))
            email = ss(self.getSavedUser('email'))
            
        if not fromname and not email:
            return []

        # loop through all the issues and slot into the buckets
        for issue in self.getIssueObjects():
            # Start by assuming that this issue wasn't opened by you
            opened = False
            
            issue_fromname = issue.getFromname(issueusercheck=0)
            issue_email = issue.getEmail(issueusercheck=0)
            if issue_fromname is None:
                issue_fromname = ''
            if issue_email is None:
                issue_email = ''
            issue_fromname = ss(issue_fromname)
            issue_email = ss(issue_email)
            
            if issue.getACLAdder() == acl_user:
                opened = True
            elif unicodify(issue_fromname) == fromname and \
                 issue_email == email:
                opened = True
                
            if opened:
                date = issue.getIssueDate()
                
                if date.strftime('%Y%m%d') == today_date:
                    self._add2bucket(bucket, 'today', opened=1)
                elif date.strftime('%Y%m%d') == yesterday_date:
                    self._add2bucket(bucket, 'yesterday', opened=1)
                    
                if date.strftime('%U%Y') == this_week_date:
                    self._add2bucket(bucket, 'week', opened=1)
                elif date.strftime('%U%Y') == last_week_date:
                    self._add2bucket(bucket, 'last_week', opened=1)
                    
                if date.strftime('%Y%m') == this_month_date:
                    self._add2bucket(bucket, 'month', opened=1)
                elif date.strftime('%Y%m') == last_month_date:
                    self._add2bucket(bucket, 'last_month', opened=1)
                    
                self._add2bucket(bucket, 'ever', opened=1)
                
            if issue.getStatus().lower() in statuses_closed:
                # yeah, find out which thread was the closing one
                expect_title_start = 'Changed status '
                expect_title_end = 'to %s' % issue.getStatus().lower()
                
                # now, check if YOU closed it (status -> Completed or Rejected)
                for thread in issue.getThreadObjects():
                    t = thread.getTitle().lower()
                    
                    if t.endswith(expect_title_end.lower()) and \
                       t.startswith(expect_title_start.lower()):
                        # It was closed, but by you?
                        
                        thread_fromname = thread.getFromname(issueusercheck=0)
                        thread_email = thread.getEmail(issueusercheck=0)
                        if thread_fromname is None:
                            thread_fromname = ''
                        if thread_email is None:
                            thread_email = ''
                            thread_fromname = ss(thread_fromname)
                            thread_email = ss(thread_email)
                            
                        closed = False
                        if thread.getACLAdder() == acl_user:
                            closed = True
                        elif thread_fromname and thread_email:
                            if thread_fromname == fromname and thread_email == email:
                                closed = True
                        elif thread_fromname and not thread_email:
                            if thread_fromname == fromname:
                                closed = True
                        elif not thread_fromname and thread_email:
                            if thread_email == email:
                                closed = True
                        
                        if not closed:
                            break
                        
                        # Wow! You closed this issue
                        date = thread.getThreadDate()
                
                        if date.strftime('%Y%m%d') == today_date:
                            self._add2bucket(bucket, 'today', closed=1)
                        elif date.strftime('%Y%m%d') == yesterday_date:
                            self._add2bucket(bucket, 'yesterday', closed=1)
                    
                        if date.strftime('%U%Y') == this_week_date:
                            self._add2bucket(bucket, 'week', closed=1)
                        elif date.strftime('%U%Y') == last_week_date:
                            self._add2bucket(bucket, 'last_week', closed=1)
                    
                        if date.strftime('%Y%m') == this_month_date:
                            self._add2bucket(bucket, 'month', closed=1)
                        elif date.strftime('%Y%m') == last_month_date:
                            self._add2bucket(bucket, 'last_month', closed=1)
                    
                        self._add2bucket(bucket, 'ever', closed=1)                   
                        
                        break

        return bucket
                    
                
                
            
                    
    def _add2bucket(self, bucket, key, opened=False, closed=False):
        """ read the doc commment of getUserAchievements() """
        assert opened or closed
        value = bucket.get(key, {'opened':0, 'closed':0})
        if opened:
            value['opened'] = value.get('opened', 0) + 1
        else:
            value['closed'] = value.get('closed', 0) + 1
        bucket[key] = value
            
        
    def ListMyIssues(self, REQUEST, i, Complete=0, *args, **kws):
        """ Return ListIssues or CompleteList but with a sequence of
        issues that we generate here instead."""

        if ss(i) == 'assigned':
            data = self.getMyIssuesAndThreads()
            myassignments = data[0]
            issues = []
            for assignment in myassignments:
                if assignment.aq_parent not in issues:
                    issues.append(assignment.aq_parent)
            pagetitle = "Issue assigned to you "
            
        elif ss(i) == 'added':
            data = self.getMyIssuesAndThreads()
            #myassignments, myissues, mythreads, threadcounts = data
            issues = data[1]
            pagetitle = "Issues you have added "

        elif ss(i) == 'followedup':
            data = self.getMyIssuesAndThreads()
            mythreads = data[2]
            issues = []
            for thread in mythreads:
                if thread.aq_parent not in issues:
                    issues.append(thread.aq_parent)

            pagetitle = "Issues you have followed up on "

        else:
            raise "NothingToList", "No recognized action of what to list"

        nr_issues = len(issues)
        if nr_issues == 0:
            pagetitle += "(none)"
        elif nr_issues == 1:
            pagetitle += "(1 issue)"
        else:
            pagetitle += "(%s issues)"%nr_issues
        REQUEST.set('TotalNoIssues', len(issues))
            
        try:
            Complete = int(Complete)
        except ValueError:
            Complete = True
        
        if Complete:
            page = self.CompleteList
        else:
            page = self.ListIssues

        issues = self._ListIssuesFiltered(issues)
        return page(self, REQUEST, filteredissues=issues,
                    pagetitle=pagetitle)

                    
    ##
    ## Reports related code
    ##
    
    def getReportsContainer(self):
        """ return the folder where all the Reports are in """
        zodb_id = "Reports"
        root = self.getRoot()
        rootbase = getattr(root, 'aq_base', root)
        if not hasattr(rootbase, zodb_id):
            inst = ReportsContainer(zodb_id)
            root._setObject(zodb_id, inst)
        return getattr(root, zodb_id)
    
    
                    
    ##
    ## Error helping functions
    ##

    # ignored_exceptions = e_log.getProperties().get('ignored_exceptions', [])
    
    def createErrorFileObject(self, options):
        """ create a Zope File object called error-[date].log """
        

        
        err_type = options.get('error_type')
        err_message = options.get('error_message')
        err_tb = options.get('error_tb')
        err_value = options.get('error_value')
        err_traceback = options.get('error_traceback')
        err_log_url = options.get('error_log_url')
        
        # stop this madness if we can find a reason for ignoring the error
        try:
            e_log = self.error_log
            ignorables = e_log.getProperties().get('ignored_exceptions', [])
            if err_type in ignorables:
                return None
        except:
            # carry on then
            pass
        
        
        file = cStringIO.StringIO()
        file.write("Bug Reporting File\n%s\n\n"%DateTime())
        file.write("Error type: %s\n"%err_type)
        file.write("Error value: %s\n\n"%err_value)
        
        error_log = self.error_log
            
        try:
            security_user = getSecurityManager().getUser()
            def _check_permission(perm, object, user=security_user):
                return user.has_permission(perm, object)
        except:
            def _check_permission(*a, **k):
                return False
            LOG("standard_error_message", ERROR, 
                "_check_permission() function disabled", error=sys.exc_info())

        try:
            if _check_permission(VMS, error_log):
                entries = error_log.getLogEntries()
                last_entry = entries[0]
                file.write(error_log.getLogEntryAsText(id=last_entry.get('id')))
                file.write("\n\n")
        except:
            LOG("standard_error_message", ERROR, 
                "Could not get the last traceback",
                error=sys.exc_info())
                
        version = self.getIssueTrackerVersion()
        file.write("IssueTrackerProduct version: %s\n"%version)
        if _check_permission(VMS, self.Control_Panel):
            cp = self.Control_Panel
            
            try: file.write("Zope: %s\n"%cp.version_txt())
            except: pass
            
            try: file.write("Python: %s\n"%cp.sys_version())
            except: pass
            
            try: file.write("Platform: %s\n"%cp.sys_platform())
            except: pass
            
        
            
            
        temp_folder_id = self._generateTempFolder()
        temp_folder = self._getTempFolder()[temp_folder_id]
        
        fileid = DateTime().strftime('Error-%d%B%Y.log')
        
        try:
            temp_folder.manage_addFile(fileid, file=file,
                           content_type='text/plain')
        except:
            LOG("standard_error_message", ERROR, 
                    "Could not create error file object",
                    error=sys.exc_info())
            return None            
            
        fileobject = getattr(temp_folder, fileid)
        
        # necessary to be able to keep the file persistently
        # when in an error.
        if transaction is None:
            get_transaction().commit()
        else:
            # the modern way of doing it
            transaction.get().commit()
        
        return fileobject

        
    def bugreportingURL(self, error_type=None, error_value=None,
                        error_traceback=None):
        """ return a quoted url for reporting bugs """
        url, params = self._getBugReportingParameters(error_type=error_type,
                                                      error_value=error_value,
                                                      error_traceback=error_traceback)
        
        return Utils.AddParam2URL(url, params, unicode_encoding=UNICODE_ENCODING)
    
    def bugreportingForm(self, error_type=None, error_value=None,
                        error_traceback=None, submit_value='Issue Tracker'):
        url, params = self._getBugReportingParameters(error_type=error_type,
                                                      error_value=error_value,
                                                      error_traceback=error_traceback)
        html = ['<form action="%s" method="post">' % url]
        for k, v in params.items():
            html.append(u'<input type="hidden" name="%s" value="%s" />' % (k, Utils.html_quote(v)))
            
        html.append(u'<input type="submit" value="%s" />' % submit_value)
        html.append('</form>')
        return '\n'.join(html)
        
    def _getBugReportingParameters(self, error_type=None, error_value=None,
                                   error_traceback=None):
        url = "http://real.issuetrackerproduct.com/AddIssue"
        params = {'type':'bug report'}
        this_name = self.getSavedUser('fromname')
        if this_name:
            params['fromname'] = this_name
        this_email = self.getSavedUser('email')
        if this_email:
            params['email'] = this_email
        display_format = self.getSavedTextFormat()
        if display_format:
            params['display_format'] = display_format
            
        text = "An error occured when I tried to...\n\n"
        text += "\n"+"-"*50+"\n"
        if error_type:
            text += "Error type: %s\n"%error_type
            if error_value:
                text += "Error value: %s\n"%error_value
                

        if error_traceback:
            
            try:
                security_user = getSecurityManager().getUser()
                def _check_permission(perm, object, user=security_user):
                    return user.has_permission(perm, object)
            except:
                def _check_permission(*a, **k):
                    return False
                LOG("standard_error_message", ERROR, 
                            "_check_permission() function disabled", 
                            error=sys.exc_info())

            try:
                error_log = self.error_log
                if _check_permission(VMS, error_log):
                    entries = error_log.getLogEntries()
                    last_entry = entries[0]
                    error_traceback = error_log.getLogEntryAsText(id=last_entry.get('id'))
            except:
                LOG("bugreportingURL()", ERROR, 
                    "Could not get the last traceback",
                    error=sys.exc_info())
                
            
            text += "\n%s"%error_traceback

        params['description'] = text
        
        return url, params
        
    
    def guessPages(self, url=None, howmany=10):
        """ return [[URL,Title], ...] alternatives if any. This is used on the
        Page Not Found error page."""
        if url is None:
            url = self.REQUEST.URL
           
        root = self.getRoot()
        rooturl = root.absolute_url()
        assert url.lower().startswith(rooturl.lower())
        
        guesses = []
        
        
        # traversable
        path = url.replace(rooturl, '')
        if self._isUsingBTreeFolder():
            _issue = self.restrictedTraverse(BTREEFOLDER2_ID+path, None)
            if _issue and _issue.meta_type == ISSUE_METATYPE:
                _issue_url = _issue.absolute_url()
                if self.REQUEST.QUERY_STRING:
                    _issue_url += "?%s"%self.REQUEST.QUERY_STRING
                self.REQUEST.RESPONSE.redirect(_issue_url, lock=1)
                return [[_issue.absolute_url(), _issue.getTitle()]]
            
        elif path.find(BTREEFOLDER2_ID) > -1:
            try:
                fixedpath = self.REQUEST.PATH_INFO.replace('/%s'%BTREEFOLDER2_ID,'')
            except:
                fixedpath = path.replace('/%s'%BTREEFOLDER2_ID,'')                    
            _issue = self.restrictedTraverse(fixedpath, None)
            if _issue and _issue.meta_type == ISSUE_METATYPE:
                _issue_url = _issue.absolute_url()
                if self.REQUEST.QUERY_STRING:
                    _issue_url += "?%s"%self.REQUEST.QUERY_STRING
                self.REQUEST.RESPONSE.redirect(_issue_url, lock=1)
                return [[_issue.absolute_url(), _issue.getTitle()]]
            
        case_corrections = ('check4MailIssues','About.html')
        for case in case_corrections:
            if path.lower().endswith(case.lower()) and not path.endswith(case):
                # case insensitive method for this one
                _url = rooturl+'/'+case
                self.REQUEST.RESPONSE.redirect(_url, lock=1)
                return [[_url,_url]]
                
        unpadded_zeros_regex = re.compile(r'/(\d\d+)$')
        if unpadded_zeros_regex.findall(url):
            # the user most likely use /issuetracker/177
            # when she was supposed to use /issuetracker/0177
            
            digits = unpadded_zeros_regex.findall(url)[0]
            if len(digits) < self.randomid_length:
                issueid = string.zfill(digits, self.randomid_length)
                if self.hasIssue(issueid):
                    _issue = self.getIssueObject(issueid)
                    self.REQUEST.RESPONSE.redirect(_issue.absolute_url(), lock=1)
                    return [[_issue.absolute_url(), _issue.getTitle()]]
                
        elif url.find('/user') > -1: # It's spelled 'User' not 'user'
            url = url.replace('/user','/User')
            return self.REQUEST.RESPONSE.redirect(url, lock=1)
                    
                    
                
            
        
        typicals = {'/AddIssue':'Add Issue', 
                    '/QuickAddIssue':'Quick Add Issue',
                    '/ListIssues':'List Issues',
                    '/CompleteList':'Complete List',
                    }
        for k, v in typicals.items():
            if path.lower()==k.lower() and path != k:
                return [[rooturl+k,v]]
            
        if url.lower().endswith('management'):
            guesses.append([rooturl+'/manage_ManagementForm', 'Management'])
        elif url.lower().endswith('properties'):
            guesses.append([rooturl+'/manage_editIssueTrackerPropertiesForm', 'Properties (Zope)'])

        id_with_junk = re.compile('/(' + '\d'*self.randomid_length + ')\w+')
        if id_with_junk.findall(path):
            issueid = id_with_junk.findall(path)[0]
            # does it exit?
            for objectid, object in root.getIssueItems():
                if objectid == issueid:
                    title = object.getTitle()
                    objecturl = object.absolute_url()
                    guesses.append([objecturl, title])
                    break
                
        guesses.append([rooturl,'Home page'])
        
        return guesses
    
    ##
    ## Status scores related 
    ##
    
    def getStatusScoreValues(self, return_incomplete=False):
        """ return a dict where the keys are from getStatus() and the 
        values are integers (or None) from 0-100.
        """
        status_values = getattr(self, '_status_score_values', {})
        assert type(status_values) == type({})
        
        if return_incomplete:
            # don't do a validity check on it
            return status_values
        
        # perform a validity check...
        if Set is not None:  # ...using sets
            # use sets to check that
            status_keys = self.getStatuses()
            if not Set(status_keys) == Set(status_values.keys()):
                return None
            
        else: # ...using slow loops
            for status_key in status_keys:
                if status_key not in status_values.keys():
                    return None
            for key in status_values.keys():
                if key not in status_keys:
                    return None
            
        return status_values
    
    def hasStatusValues(self, values=None):
        """ check if the status values are sufficiently set """
        if values is None:
            values = self.getStatusScoreValues()
            
        if not values:
            # values is an empty dict
            return False
        else:
            # must have a summable values
            try:
                Utils.sum(values.values())
                return True
            except:
                return False
        
    
    def manage_saveStatusScores(self, used_statuses, values, REQUEST=None):
        """ used_statuses is a list of statuses that was used to set values
        on each status. """
        assert len(used_statuses) == len(values)
        
        status_values = self.getStatusScoreValues(return_incomplete=True)
        
        for i in range(len(used_statuses)):
            status = used_statuses[i]
            value = values[i]
            if value == '':
                value = None
            else:
                value = int(value)
                assert value >= 0 and value <= 100, "Invalid value for score on status %s" % status
                    
            status_values[status] = value
            
        # save this
        self._status_score_values = status_values
        
        if REQUEST is not None:
            url = self.getRootURL()+'/manage_PropertiesStatusScores'
            url += '?manage_tabs_message=Status+scores+saved'
            REQUEST.RESPONSE.redirect(url)
            
            
    def calculateStatusScoreProgress(self, status_values):
        """ return a calculated average score as an integer between
        1-100 """
        statuslist = self.CountStatuses()
        
        statuslist_count = self.totalCountStatus(statuslist)
        
        statuslist_dict = {}
        for status, count in statuslist:
            statuslist_dict[status] = count
            
        # status_values is a dict where each key is a status. 
        # The calculation is the sum of count*score divided by
        # the sum of all counts. See the source code
        
        _statuscount_times_values = [status_values[x] * y 
                                     for (x, y) in statuslist_dict.items() 
                                     if status_values[x] is not None]
                                     
        _statuses_valued = [count 
                            for (x, count) in statuslist_dict.items() 
                            if status_values[x] is not None]
        return Utils.sum(_statuscount_times_values) / \
               float(Utils.sum(_statuses_valued))
               
    
    ##
    ## Upgrade related
    ##
    
    def _getVersionControllerInstance(self):
        """ return an instance of the upgrade.VersionController class """
        here = package_home(globals())
        assert here.endswith('IssueTrackerProduct')
        return VersionController(here)

    security.declareProtected(VMS, 'manage_canUpgrade')
    def manage_canUpgrade(self):
        """ return true or false if the issuetracker can be upgraded """
        vc = self._getVersionControllerInstance()
        if vc.isUsingCVS():
            ## currently we do can't support this
            return False
        else:
            return vc.canUpgrade()
        
    security.declareProtected(VMS, 'manage_getUpgradeInfo')
    def manage_getUpgradeInfo(self):
        """ return which version we can upgrade to """
        vc = self._getVersionControllerInstance()
        return {'version':vc.latest_version, 'url':vc.latest_version_url}

    security.declareProtected(VMS, 'manage_isUsingCVS')
    def manage_isUsingCVS(self):
        """ return true or false on whether we're using CVS for this installation. """
        vc = self._getVersionControllerInstance()
        return vc.isUsingCVS()
    
    security.declareProtected(VMS, 'manage_doUpgrade')
    def manage_doUpgrade(self, REQUEST=None):
        """ perform a IssueTrackerProduct using the upgrade script """
        
        assert self.manage_canUpgrade()
        
        output = cStringIO.StringIO()
        errors = cStringIO.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            sys.stdout = output
            sys.stderr = errors
            vc = self._getVersionControllerInstance()
            vc.upgrade()
        finally:
            sys.stdout = old_stdout
            sys.stderr = sys.stderr
        
        errors_value = errors.getvalue()
        output_value = output.getvalue()
        
        msg = output_value
        if errors_value:
            msg += "\n%s" % errors_value
        
        # Note: we create this URL here _before_ we call _refreshIssueTrackerProduct()
        # because after that function has been called, the whole product goes into
        # asyncrounous refreshingstate meaning that all modules become None (dont'
        # ask me to explain it). All code below the _refreshIssueTrackerProduct() does
        # not use any of the IssueTrackerProduct modules and should thus be safe.
        management_url = self.getRootURL()+'/manage_ManagementUpgrade'
        
        
        try:
            self._refreshIssueTrackerProduct()
        except:
            try:
                err_log = self.error_log
                err_log.raising(sys.exc_info())
            except:
                pass
            LOG(self.__class__.__name__, ERROR, "Could not perform product refresh",
                error=sys.exc_info())
            msg += "\n**COULD NOT PERFORM PRODUCT REFRESH. See error_log**"
            
        msg = msg.strip()
            
        del output, errors
        
        if REQUEST is not None:
            #url = Utils.AddParam2URL(management_url, {'manage_tabs_message':msg})
            from urllib import quote
            url = management_url + '?manage_tabs_message=%s' % quote(msg)
            #REQUEST.RESPONSE.redirect(url)
            return '''<html><head>
            <meta http-equiv="refresh" content="10; url=%(url)s" />
            </head><body style="font-family:sans-serif"><h2>Refreshing...</h2>
            <p>Please wait while the IssueTrackerProduct is being refreshed</p>
            </body></html>''' % {'url':url}
        else:
            return msg
        
    def _refreshIssueTrackerProduct(self):
        """ perform a refresh of the IssueTrackerProduct """
        itp = self.Control_Panel.Products.IssueTrackerProduct
        itp.manage_performRefresh()
        
        
    def _emptyFunction(self, REQUEST, RESPONSE):
        """ fake empty function """
        return REQUEST
    
    
    ##
    ## Spam protection stuff
    ##
    
    def getCaptchaNumbersHTML(self, keys=None, howmany=4):
        """ return the HTML needed to be included in the forms to catch out
        spambots. 
        """
        skey = ALREADY_NOT_SPAMBOT_SESSION_KEY
        if self.get_session(skey):
            return ''
        
        parts = []
        if keys:
            for key in keys:
                src = key
                parts.append('<img src="%s" class="captcha" alt="number?" />' % src)
                parts.append('<input type="hidden" name="captchas" value="%s" />' % src)
        else:
            keys = self.captcha_numbers_map.keys()
            random.shuffle(keys)
            for i in range(howmany):
                src = keys[i % len(keys)]
                parts.append('<img src="%s" class="captcha" alt="number?" />' % src)
                parts.append('<input type="hidden" name="captchas" value="%s" />' % src)
        return ''.join(parts)
            
            
        
        
    
    def containsSpamKeywords(self, text, verbose=False):
        """ find any spam keywords in the text if possible. """
        keywords = self.getSpamKeywords()
        
        listtest = lambda x: isinstance(x, list)
        
        text = text.lower()
        
        def exit(*words):
            if verbose:
                if len(words) > 1:
                    msg = "Matched spam keywords: %s" % ', '.join(words)
                else:
                    msg = "Matched spam keyword: %s" % words[0]
                    
                LOG("IssueTrackerProduct Spam Protection", INFO, msg)
                    
            # return True means that Yes, there are spam keywords in text
            return True
        
        def testmatch(keyword, text):
            """ if the keyword we're looking for is something like
            'poker' that we'll do a word delimiter around the keyword
            for the match. If it contains anything else, we do a 
            regular string find match.
            """
            if re.findall('[^\w]', keyword):
                # this keyword contains other stuff than just A-z
                return text.lower().find(keyword.lower()) > -1
            else:
                regex = re.compile(r'\b%s\b' % re.escape(keyword), re.I)
                return regex.findall(text)
                
        sub_keywords = {}
        single_keywords = []
        for i, keyword in enumerate(keywords):
            is_part = False
            try:
                next_keyword = keywords[i+1]
                if listtest(next_keyword):
                    sub_keywords[keyword] = next_keyword
                elif not listtest(keyword):
                    single_keywords.append(keyword)
            except IndexError:
                if not listtest(keyword):
                    single_keywords.append(keyword)
                
        for keyword in single_keywords:
            if testmatch(keyword, text):
                return exit(keyword)
            
        for keyword, keywords in sub_keywords.items():
            if testmatch(keyword, text):
                for keyword_ in keywords:
                    if testmatch(keyword_, text):
                        return exit(keyword, keyword_)
                    
        return False

    
    security.declareProtected(VMS, 'manage_saveSpamKeywords')
    def manage_saveSpamKeywords(self, keywords, REQUEST=None):
        """ save the 'spam_keywords' """
        checked = []
        
        # remove blank lines
        keywords = [x for x in keywords if x.strip()]
        
        subwordtest = lambda x: x.startswith(' ') or x.startswith('\t')
        subwords = None
        for word in keywords:
            if subwordtest(word):
                if checked:
                    if subwords is None:
                        subwords = [word.rstrip()]
                    else:
                        subwords.append(word.rstrip())
            else:
                if subwords:
                    subwords = [x.strip() for x in subwords]
                    subwords.sort()
                    checked.append(Utils.iuniqify(subwords))
                    subwords = None
                checked.append(word.strip())
                
        if subwords:
            subwords = [x.strip() for x in subwords]
            subwords.sort()
            checked.append(Utils.iuniqify(subwords))
            
        def merge_duplicates(list_of_lists):
            """ suppose you have a list like this:
                ['foo',
                 'Key1', ['a','b','c'],
                 'bar',
                 'Key1', ['d','e','f']
                 'foobar',
                 ...
            That means that the values of the two Key1 can be merged into one:
                ['foo',
                 'Key1', ['a','b','c','d','e','f'],
                 'bar',
                 'foobar',
                 ...
            """
            all = {}
            listtest = lambda x: isinstance(x, list)
            skip_next = False
            for i, item in enumerate(list_of_lists):
                if skip_next:
                    skip_next = False
                    continue
                
                try:
                    next_item = list_of_lists[i+1]
                    if listtest(next_item):
                        p = all.get(item, [])
                        p.extend(next_item)
                        all[item] = p
                        skip_next = True
                    else:
                        all[item] = []
                except IndexError:
                    # we're at the last item
                    all[item] = []
            
    
            _keys = all.keys()
            _keys.sort(lambda x,y:cmp(x.lower(), y.lower()))
            new_list_of_lists = []
            for k in _keys:
                v = all[k]
                new_list_of_lists.append(k)
                if v:
                    new_list_of_lists.append(v)
                    
            return new_list_of_lists
            
        checked = merge_duplicates(checked)
        self.spam_keywords = checked
        
        if REQUEST is not None:
            url = self.getRootURL()+'/manage_ManagementSpamProtection'
            url += '?manage_tabs_message=Spam+keywords+saved'
            REQUEST.RESPONSE.redirect(url)

    security.declareProtected(VMS, 'manage_findIssuesContainingSpam')
    def manage_findIssuesContainingSpam(self):
        """ return all issues that contain spam """
        issues = []
        for issue in self.getIssueObjects():
            text = issue.getTitle() + " " + issue.getDescription()
            if self.containsSpamKeywords(text):
                issues.append(issue)
                
        return issues
    
    security.declareProtected(VMS, 'manage_findThreadsContainingSpam')
    def manage_findThreadsContainingSpam(self):
        """ return all threads that contain spam """
        threads = []
        thread_counts = {}
        for issue in self.getIssueObjects():
            count = 1
            for thread in issue.getThreadObjects():
                text = thread.getComment()
                if self.containsSpamKeywords(text):
                    thread_counts[thread.absolute_url_path()] = count
                    threads.append(thread)
                count += 1
                
        # The reason for maintaining this dict is so that on 
        # manage_ManagementSpamProtection we can link to followups
        # with the correct anchor link.
        self.REQUEST.set('thread_counts', thread_counts)
        return threads
    
    security.declareProtected(VMS, 'manage_deleteIssuesAndThreads')
    def manage_deleteIssuesAndThreads(self, issuepaths=[], threadpaths=[],
                                      REQUEST=None):
        """ used on the ManagementSpamProtection page when you've found
        some issues with spam in it. """
        rooturl = self.getRoot().absolute_url()
        # check each path
        dels = {}
        all_paths = issuepaths + threadpaths
        for path in all_paths:
            obj = self.restrictedTraverse(path)
            if obj.absolute_url().find(rooturl) == -1:
                raise "SubmitError", "Invalid path to object %r" % path

            container = aq_parent(aq_inner(obj))
            container.manage_delObjects([obj.getId()])

        if REQUEST is not None:
            url = self.getRootURL()+'/manage_ManagementSpamProtection'
            if all_paths:
                url += '?manage_tabs_message=Issues+and+followups+deleted'
            else:
                url += '?manage_tabs_message=Nothing+deleted'
            REQUEST.RESPONSE.redirect(url)
        
                

#----------------------------------------------------------------------------
zpts = ('zpt/StandardHeader',
        {'f':'zpt/QuickAddIssue', 'n':'QuickAddIssueTemplate',
         'optimize':OPTIMIZE and 'xhtml'},
        {'f':'zpt/AddManyIssues', 'n':'AddManyIssuesTemplate',
         'optimize':False},#OPTIMIZE and 'xhtml'},         
        'zpt/preview_issue',
        {'f':'zpt/index_html', 'optimize':OPTIMIZE and 'xhtml'},
        'zpt/list_issues_top_bar',
        {'f':'zpt/ListIssues', 'optimize':0}, #OPTIMIZE and 'xhtml'},
        {'f':'zpt/CompleteList', 'optimize':0}, #OPTIMIZE and 'xhtml'},        
        'zpt/show_submissionerror_message',
        {'f':'zpt/AddIssue', 'n':'AddIssueTemplate',
         'optimize':OPTIMIZE and 'xhtml'},
        {'f':'zpt/User', 'n':'UserTemplate',
         'optimize':OPTIMIZE and 'xhtml'},
        'zpt/User_must_change_password',
        'zpt/show_drafts',
        'zpt/show_drafts_simple',
        'zpt/show_next_actions',        
        'zpt/filter_options',
        'zpt/richList',
        'zpt/compactList',
        'zpt/search_widget',
        'zpt/recent_history_widget',
        
        'zpt/Statistics',
        'zpt/ShowIssueData',
        'zpt/ShowIssueThreads',
        'zpt/What-is-StructuredText',
        'zpt/What-is-WYSIWYG',        
        'zpt/Keyboard-shortcuts',
        'zpt/Your-next-action-issues',
        ('zpt/rdf', 'rdf_template'),
        'zpt/show_user_achievements',
        
        )

#addTemplates2Class(IssueTracker, zpts, extension='zpt')

dtmls = ({'f':'dtml/screen.css', 'optimize':OPTIMIZE and 'css'},
         {'f':'dtml/print.css',  'optimize':OPTIMIZE and 'css'},
         {'f':'dtml/home.css',   'optimize':OPTIMIZE and 'css'},
         'dtml/tw-sack.js', # here for legacy
         'dtml/js-core.js', # here for legacy
         ('dtml/editIssueTrackerPropertiesForm',
          'manage_editIssueTrackerPropertiesForm'),
         ('dtml/configureMenuForm', 'manage_configureMenuForm'),
         'dtml/management_tabs',
         ('dtml/ManagementForm','manage_ManagementForm'),
         ('dtml/POP3ManagementForm', 'manage_POP3ManagementForm'),
         ('dtml/ManagementNotifyables','manage_ManagementNotifyables'),
         ('dtml/ManagementUsers','manage_ManagementUsers'),
         ('dtml/ManagementUpgrade','manage_ManagementUpgrade'),
         ('dtml/ManagementSpamProtection','manage_ManagementSpamProtection'),
         'dtml/tabtastic-combined.js',
         {'f':'dtml/keyboardshortcuts.js', 
          'optimize':OPTIMIZE and 'js', 
          },
         {'f':'dtml/AddIssueJavascript', 'n':'addissue.js',
          'optimize':OPTIMIZE and 'js', 
          },
         {'f':'dtml/QuickAddIssueJavascript', 'n':'quickaddissue.js',
          'optimize':OPTIMIZE and 'js', 
          },
         {'f':'dtml/followup.js', 'optimize':OPTIMIZE and 'js', 
          },

         ('dtml/PropertiesStatusScores', 'manage_PropertiesStatusScores'),
         
         # TinyMCE stuff
         {'f':'dtml/tiny_mce_itp.js', 'optimize':OPTIMIZE and 'js'},
         )
         

         
# Attach some tiny GIFs that are numbers. Make the Id's slightly more random 
# so that spambots can't work out that:
# <img src="0.gif"><img src="4.gif"><img src="1.gif"> == 041

numbers_map = {}
_home = package_home(globals())
_imageshome = os.path.join(_home,'www/numbers')
for e in [x for x in os.listdir(_imageshome) if x.endswith('.gif')]:
    attribute_id = Utils.getRandomString(3)+'.gif'
    while numbers_map.has_key(attribute_id):
        attribute_id = Utils.getRandomString(4)+'.gif'
    setattr(IssueTracker, attribute_id, ImageFile(os.path.join(_imageshome, e)))
    numbers_map[attribute_id] = int(e.replace('.gif',''))
setattr(IssueTracker, 'captcha_numbers_map', numbers_map)
    
         
all = list(dtmls+zpts)
if not DEBUG:
    all.append('zpt/standard_error_message')
addTemplates2Class(IssueTracker, tuple(all))

setattr(IssueTracker, 'About.html', IssueTracker.About)
setattr(IssueTracker, 'rss-0.91.xml', IssueTracker.RSS091)
# default RSS
setattr(IssueTracker, 'rss.xml', IssueTracker.RSS10)
setattr(IssueTracker, 'rdf.xml', IssueTracker.RDF)
# CSV link
setattr(IssueTracker, 'export.csv', IssueTracker.CSVExport)
# CSV link 2
setattr(IssueTracker, 'ListIssues.csv', IssueTracker.ListIssues_CSV)


# Set some of the security declaration outside the class
security = ClassSecurityInfo()
security.declareProtected('View', 'index_html')
#security.declareProtected('View', 'ShowIssue')
security.declareProtected('View', 'Statistics')
security.declareProtected('View', 'CompleteList')
security.declareProtected('View', 'ListIssues')
security.declareProtected('View', 'export.csv')
security.declareProtected('View', 'ListIssues.csv')
security.declareProtected(VMS, 'manage_POP3ManagementForm')
security.declareProtected(VMS, 'manage_configureMenuForm')
security.declareProtected(VMS, 'manage_ManagementNotifyables')
security.declareProtected(VMS, 'manage_ManagementNotifyables')
security.declareProtected(VMS, 'manage_editIssueTrackerPropertiesForm')
security.declareProtected(VMS, 'manage_ManagementForm')
security.declareProtected(VMS, 'manage_ManagementUsers')
security.declareProtected(VMS, 'manage_ManagementUpgrade')
security.declareProtected(VMS, 'manage_PropertiesWizard')
security.declareProtected(VMS, 'manage_PropertiesStatusScores')

security.declareProtected(AddIssuesPermission, 'AddIssue')
security.declareProtected(AddIssuesPermission, 'QuickAddIssue')

security.apply(IssueTracker)

InitializeClass(IssueTracker)


setattr(IssueTracker, 'UNICODE_ENCODING', UNICODE_ENCODING)

#----------------------------------------------------------------------------

# Need to import these here otherwise
from Notification import IssueTrackerNotification 
from Issue import IssueTrackerIssue, IssueTrackerDraftIssue
from Thread import IssueTrackerIssueThread
from Email import POP3Account


#----------------------------------------------------------------------------

class FilterValuer(SimpleItem.SimpleItem, PropertyManager.PropertyManager):
    """ a simple class that helps us remember a set of filter options. """
    
    meta_type = FILTEROPTION_METATYPE
    
    _properties = ({'id':'title',         'type':'string', 'mode':'w'},
                   {'id':'adder_fromname','type':'string', 'mode':'w'},
                   {'id':'adder_email',   'type':'string', 'mode':'w'},
                   {'id':'acl_adder',     'type':'string', 'mode':'w'},
                   {'id':'key',           'type':'string', 'mode':'r'},
                   {'id':'mod_date',      'type':'date',   'mode':'w'},
                   {'id':'filterlogic',   'type':'string', 'mode': 'w'},
                   {'id':'statuses',      'type':'lines',  'mode': 'w'},
                   {'id':'sections',      'type':'lines',  'mode': 'w'},
                   {'id':'urgencies',     'type':'lines',  'mode': 'w'},
                   {'id':'types',         'type':'lines',  'mode': 'w'},
                   {'id':'fromname',      'type':'string', 'mode': 'w'},
                   {'id':'email',         'type':'string', 'mode': 'w'},
                   )

    manage_options = PropertyManager.PropertyManager.manage_options
    
    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.acl_adder = ''
        self.adder_fromname = ''
        self.adder_email = ''
        self.key = '' # Used by people who don't have a name
        self.mod_date = DateTime()
        self.usage_count = 0

    def getId(self):
        return self.id
    
    def getTitle(self, length_limit=None):
        title = self.title
        if length_limit is not None:
            if len(title) > length_limit:
                return title[:length_limit] + '...'
        return title
    
    def getModificationDate(self):
        """ return when it was last changed """
        return self.mod_date
    
    def getKey(self):
        return getattr(self, 'key', None)
        
    def set(self, key, value):
        assert key in [x['id'] for x in self._properties], "Unrecognized property key"
        self.__dict__[key] = value

        
    def populateRequest(self, request):
        """ put all the filter values in this class into self.REQUEST """
        rset = request.set

        rset('Filterlogic', self.filterlogic)
        rset('f-statuses', self.statuses)
        rset('f-sections', self.sections)
        rset('f-urgencies', self.urgencies)
        rset('f-types', self.types)
        rset('f-fromname', self.fromname)
        rset('f-email', self.email)
        
        
    def incrementUsageCount(self):
        self.usage_count = self.getUsageCount() + 1
	
    def updateModDate(self):
        self.mod_date = DateTime()
        
    def getUsageCount(self):
        """ return how many times this has been used """
        return getattr(self, 'usage_count', 0)






#----------------------------------------------------------------------------

class ReportsContainer(ZopeOrderedFolder):
    """ A simple class that is more or less like the Folder class. This 
    is the home where we put all the reports and information about them. 
    """
    
    meta_type = REPORTS_CONTAINER_METATYPE

    icon = '%s/issuereportscontainer.gif'%ICON_LOCATION
    
    security = ClassSecurityInfo()
    
    def __init__(self, id, title=''):
        self.id = id 
        self.title = title
        
    def _getAllScripts(self):
        """ return all ReportScript objects plainly """
        return self.objectValues(REPORTSCRIPT_METATYPE)
    
    def _getAllScriptIds(self):
        """ return all ReportScript objects plainly """
        return self.objectIds(REPORTSCRIPT_METATYPE)
    
    def _getAllScriptItems(self):
        """ return all ReportScript objects plainly """
        return self.objectItems(REPORTSCRIPT_METATYPE)
    

    def getScripts(self, sort=False, reverse=False):
        """ return all report scripts this user can see """
        checked = []
        for script in self._getAllScripts():
            checked.append(script)
            
        if sort:
            if isinstance(sort, bool):
                # use default sort key
                sort = 'bobobase_modification_time'
            checked = sequence.sort(checked, ((sort,),))
            
            if reverse:
                checked.reverse()

        return checked
    

    def script_log(self, summary, text=''):
        """ print the summary and text to the event log
        (idea taken from Plone's plone_log() """
        LOG('Report Script', INFO, summary, text)

    def __before_publishing_traverse__(self, object, request=None):
        """ sort things out before publising object """
        self.get_environ()

    def get_environ(self):
        """ Populate REQUEST as appropriate """
        request = self.REQUEST
        stack = request['TraversalRequestNameStack']
        
        # look in the stack to see if we have getId()+'.py'
        # and if so, replace that with Download2FS
        if len(stack)==1:
            if stack[0].endswith('.py'):
                script_id = stack[0][:-3]
                if script_id in self._getAllScriptIds():
                    stack = ['Download2FS', script_id]
                    request.set('TraversalRequestNameStack', stack)
        
    
zpts = ({'f':'zpt/Reports', 'n':'index_html'},
        )

addTemplates2Class(ReportsContainer, zpts, extension='zpt')
    
    
InitializeClass(ReportsContainer)    


