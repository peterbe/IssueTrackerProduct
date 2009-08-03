# IssueTrackerProduct
# www.IssueTrackerProduct.com
# Peter Bengtsson <mail@peterbe.com>
#
# Constants for IssueTrackerProduct
#

import os
def getEnvBool(key, default):
    """ return an boolean from the environment variables """    
    value = os.environ.get(key, default)
    try:
        value = not not int(value)
    except ValueError:
        if str(value).lower().strip() in ['yes','on','t','y']:
            value = 1
        elif str(value).lower().strip() in ['no','off','f','n']:
            value = 0
        else:
            value = default
    return value

def getEnvInt(key, default):
    """ return an integer from the environment variables """
    value = os.environ.get(key, default)
    try:
        return int(value)
    except ValueError:
        return default
    
def getEnvStr(key, default):
    """ return a string from the environment variables """
    value = os.environ.get(key, default)
    return str(value)
    
true = not 0
false = not true
try:
    True = not False
except NameError:
    True = true
    False = false
    
from I18N import _    

# Optimize the output
OPTIMIZE = getEnvBool('OPTIMIZE_ISSUETRACKERPRODUCT', True)

# Debug
# shows some verbose dev data and doesn't actually send emails
DEBUG = getEnvBool('DEBUG_ISSUETRACKERPRODUCT', False)

UNICODE_ENCODING = getEnvStr('UNICODE_ENCODING_ISSUETRACKERPRODUCT', 'utf-8')

# Global variable if you want to disable CheckoutableTemplates
# even if it's installed and working. This can be useful to disable 
# if you're doing development or want to supress all checked out 
# templates in ZODB.
DISABLE_CHECKOUTABLE_TEMPLATES = getEnvBool('DISABLE_CHECKOUTABLE_TEMPLATES', False)

# constants
ICON_LOCATION = 'misc_/IssueTrackerProduct'
ISSUETRACKER_METATYPE = 'Issue Tracker'
ISSUE_METATYPE = 'Issue Tracker Issue'
ISSUE_DRAFT_METATYPE = 'Issue Tracker Draft Issue'
ISSUETHREAD_DRAFT_METATYPE = 'Issue Tracker Draft Issue Thread'
NOTIFYABLE_METATYPE = 'Issue Tracker Notifyable'
ISSUETHREAD_METATYPE = 'Issue Tracker Issue Thread'
ISSUENOTE_METATYPE = 'Issue Tracker Issue Note'
NOTIFICATION_META_TYPE = 'Issue Tracker Notification'
NOTIFYABLEGROUP_METATYPE = 'Issue Tracker Notifyable Group'
NOTIFYABLECONTAINER_METATYPE = 'Issue Tracker Notifyable Container'
POP3ACCOUNT_METATYPE = 'Issue Tracker POP3 Account'
ACCEPTINGEMAIL_METATYPE = 'Issue Tracker Accepting Email'
ISSUEUSERFOLDER_METATYPE = 'Issue Tracker User Folder'
ISSUEASSIGNMENT_METATYPE = 'Issue Tracker Assignment'
FILTEROPTION_METATYPE = 'Issue Tracker Filter Option'
REPORTSCRIPT_METATYPE = 'Issue Tracker Report Script'
REPORTS_CONTAINER_METATYPE = 'Report Scripts Container'
CUSTOMFIELD_METATYPE = 'Issue Tracker Custom Field'
CUSTOMFIELDFOLDER_METATYPE = 'Issue Tracker Custom Field Folder'
CUSTOMFIELD_VALIDATION_EXPRESSION_METATYPE = 'Issue Tracker Custom Field Validation Expression'

# properties
#DEFAULT_TYPES = ('general', 'announcement', 'idea', 'bug report',
#                 'feature request','question',
#                 'usability','other')
DEFAULT_TYPES = (_(u'general'), _(u'announcement'), _(u'idea'), 
                 _(u'bug report'), _(u'feature request'), _(u'question'),
                 _(u'usability'), _(u'other'),
                 )

DEFAULT_TYPE = DEFAULT_TYPES[0]
#DEFAULT_URGENCIES = ('low','normal','high','critical')
DEFAULT_URGENCIES = (_(u'low'), _(u'normal'), _(u'high'), _(u'critical'))
DEFAULT_ALWAYS_NOTIFY = ()
DEFAULT_URGENCY = DEFAULT_URGENCIES[1]
DEFAULT_SECTIONS_OPTIONS = (_(u'General'), _(u'Homepage'), _(u'Other'))
DEFAULT_SECTIONS = [DEFAULT_SECTIONS_OPTIONS[0]]
DEFAULT_WHEN_IGNORE_WORD = 'ignored'
DEFAULT_DISPLAY_DATE = '%d/%m %Y %H:%M'
DEFAULT_SITEMASTER_NAME = 'Issue Tracker'
DEFAULT_SITEMASTER_EMAIL = 'noreply@localhost'
DEFAULT_MANAGER_ROLES = ['Manager', 'IssueTracker Manager']
DEFAULT_DEFAULT_BATCH_SIZE = getEnvInt('ITP_DEFAULT_BATCH_SIZE', 20)
DEFAULT_OUTLOOK_BATCH_SIZE = getEnvInt('ITP_OUTLOOK_BATCH_SIZE', 10)
DEFAULT_ALLOW_SHOW_ALL = True
DEFAULT_ISSUEPREFIX = ''
DEFAULT_NO_FILEATTACHMENTS = getEnvInt('ITP_NO_FILEATTACHMENTS', 3)
DEFAULT_NO_FOLLOWUP_FILEATTACHMENTS = getEnvInt('ITP_NO_FOLLOWUP_FILEATTACHMENTS', 3)
DEFAULT_STATUSES = (_(u'open'), _(u'taken'), _(u'on hold'), _(u'rejected'), _(u'completed'))
DEFAULT_STATUSES_VERBS = (_(u'open'), _(u'take'), _(u'put on hold'), _(u'reject'), _(u'complete'))
DEFAULT_DISPLAY_FORMATS = ('plaintext','structuredtext')
DEFAULT_DEFAULT_DISPLAY_FORMAT = DEFAULT_DISPLAY_FORMATS[0]
DEFAULT_DISPATCH_ON_SUBMIT = True
DEFAULT_RANDOMID_LENGTH = getEnvInt('ITP_ID_LENGTH', 3)
DEFAULT_ALLOW_ISSUEATTRCHANGE = True
DEFAULT_STOP_CACHE = True
DEFAULT_ALLOW_SUBSCRIPTION = False
DEFAULT_PRIVATE_STATISTICS = False
DEFAULT_PRIVATE_REPORTS = True
DEFAULT_SAVE_DRAFTS = True
DEFAULT_SHOW_CONFIDENTIAL_OPTION = False
DEFAULT_SHOW_HIDEME_OPTION = False
DEFAULT_SHOW_ISSUEURL_OPTION = False
DEFAULT_ENCODE_EMAILDISPLAY = True
DEFAULT_SHOW_ALWAYS_NOTIFY_STATUS = True
DEFAULT_IMAGES_IN_MENU = True
DEFAULT_USE_ISSUE_ASSIGNMENT = False
DEFAULT_DISALLOW_DUPLICATE_ISSUE_SUBJECTS = False
DEFAULT_CAN_ADD_NEW_SECTIONS = False
DEFAULT_SIGNATURE_TEXT = _('''[title] <[url]>''')
SORTORDER_ALTERNATIVES = ('issuedate','modifydate')
DEFAULT_SORTORDER = SORTORDER_ALTERNATIVES[0]
DEFAULT_SHOW_ID_WITH_TITLE = False
DEFAULT_SHOW_CVSEXPORT_LINK = False
DEFAULT_SHOW_USE_ACCESSKEYS_OPTION = True
DEFAULT_SHOW_REMEMBER_SAVEDFILTER_PERSISTENTLY_OPTION = True
DEFAULT_USE_AUTOSAVE = True
DEFAULT_USE_ESTIMATED_TIME = False
DEFAULT_USE_ACTUAL_TIME = False
DEFAULT_INCLUDE_DESCRIPTION_IN_NOTIFICATIONS = True
DEFAULT_USE_TELLAFRIEND = True
DEFAULT_USE_TELLAFRIEND_FOR_ANONYMOUS = True
DEFAULT_SHOW_DATES_CLEVERLY = True
DEFAULT_SHOW_SPAMBOT_PREVENTION = False
DEFAULT_SPAM_KEYWORDS = ['poker-stadium.com',
                         '<a href=', ['roulette.html','cialisonline','buy-viagra'],
                         'diet-pills.com',
                         'buyvalium.html',
                         ]
DEFAULT_ENABLE_DUE_DATE = False

NATIVE_PROPERTIES = ('title', 'types', 'urgencies', 'sections_options',
                     'defaultsections', 'when_ignore_word', 'display_date',
                     'sitemaster_name', 'sitemaster_email', 'default_type',
                     'default_urgency', 'default_batch_size', 'issueprefix',
                     'statuses', 'name_cookiekey', 'email_cookiekey',
                     'display_format_cookiekey', 'display_formats',
                     'default_display_format', 'randomid_length',
                     'dispatch_on_submit', 'statuses_translation_verbs',
                     'statuses_translation_adjectives')

# Default constants that aren't available as properties
BRIEF_TITLE_MAX_LENGTH = 50
CLEAN_TEMPFOLDER_INTERVAL_HOURS = 2.0

# special properties
DEFAULT_NOTIFYABLECONTAINER_ID = "global_notifyables"
DEFAULT_NOTIFYABLECONTAINER_TITLE = "Global IssueTracker notifyables"

# object ids
TEMPFOLDER_ID = 'temp-uploadfolder'
DRAFTSFOLDER_ID = 'drafts'
FILTERVALUEFOLDER_ID = 'saved-filters'
FILTERVALUECATALOG_ID = 'saved-filters-catalog'
ISSUENOTIFICATIONS_ID = 'notifications'

# Keys
TEMPFOLDER_REQUEST_KEY = 'Tempfolder_fileattachments'
WHICHLIST_SESSION_KEY = 'WhichListView' # XXX used anymore?
WHICHSUBLIST_SESSION_KEY = 'WhichSubListView' # XXX used anymore?
USE_FILTER_IN_SEARCH_SESSION_KEY = 'FilterInSearch'
ALREADY_NOT_SPAMBOT_SESSION_KEY = 'AlreadyNotSpambot'
EMAIL_ISSUEID_HEADER = 'IssueTrackerProduct_IssueID'
LIST_URL_SESSION_KEY = 'ListURL'

# Language constants
FAILURE_SUBJECT = _('Subject')
FAILURE_SUBJECT_DESC = _('You must at least enter a subject')
NONAME_NOEMAIL = _('No name or email')
NAME_EMAIL_HIDDEN = _('Name and email hidden')
SORT_BY = _('Click to sort by')
SORT_REVERSE = _('Click one more time and the sorting will be reversed')


# Default menu
DEFAULT_MENU_ITEMS = [
    {'label':_('Home'), 'href':'/', 'inurl':''},
    {'label':_('Add Issue'), 'href':'/AddIssue', 'inurl':('AddIssue','SaveDraftIssue')},
    {'label':_('Quick Add Issue'), 'href':'/QuickAddIssue', 'inurl':'QuickAddIssue'},
    {'label':_('List Issues'), 'href':'/ListIssues', 'inurl':'ListIssues'},
    {'label':_('Complete List'), 'href':'/CompleteList', 'inurl':'CompleteList'},
    ]

# File icons
ICON_ASSOCIATIONS={'bat':'bat.gif',  'chm':'chm.gif',  'dll':'dll.gif',
                   'doc':'doc.gif',  'exe':'exe.gif',  'gz':'gz.gif',
                   'tgz':'gz.gif',   'mpeg':'video.png', 'mpg':'mpg.gif',
                   'pdf':'pdf.gif',  'ppt':'ppt.gif',  'py':'py.png',
                   'pyw':'py.png',   'pyc':'py.png',   'reg':'reg.gif',
                   'tar':'tar.gif',  'txt':'txt.png',  'nfo':'txt.png',
                   'xls':'xls.gif',  'xml':'xml.gif',  'zip':'zip.gif',
                   'wav':'mpg.gif',  'mp3':'music.gif','ini':'ini.gif',
                   'gif':'img.png',  'jpg':'img.png',  'jpeg':'img.png',
                   'png':'img.png',  'avi':'video.png',  'js':'js.gif',
                   'pyo':'py.png',   'html':'html.gif','htm':'html.gif',
                   'psd':'psd.gif',  'fla':'fla.gif',  'swf':'swf.gif',
                   'zexp':'zope.gif','tif':'img.png',  'csv':'xls.gif',
                   'pps':'pps.gif',  'm3u':'mp3.gif',  'shtml':'html.gif',
                   'rtf':'doc.gif',  'mov':'mov.gif',  'bmp':'img.png',
                   'java':'java.png','jar':'java.png', 'jsp':'java.png',
                   'log':'txt.png',  'dtml':'dtml.gif','bz2':'gz.gif',
                   'sxc':'sxc.gif',  'ra':'ra.gif',    'sxd':'sxd.gif',
                   'zpt':'zpt.gif',  'pt':'zpt.gif',   'djvu':'djvu.gif',
                   'djv':'djvu.gif', 'ogg':'music.gif','wma':'music.gif',
                   'vsd':'vsd.gif',  'tex':'tex.png',  'sxc':'sxc.png',
                   'sxi':'sxi.png',  'sxw':'sxw.png',  'rar':'rar.png',
                   'deb':'deb.png',  'rpm':'package.png','ods':'sxc.png',
                   'odt':'sxw.png',  'zcml':'xml.gif',
                   }

# cookies and sessions
NAME_COOKIEKEY = '__issuetracker_fromname'
EMAIL_COOKIEKEY = '__issuetracker_email'
DISPLAY_FORMAT_COOKIEKEY = '__issuetracker_display_format'
EMAILSTRING_COOKIEKEY = '__issuetracker_emailstring'
EMAILFRIENDS_COOKIEKEY = '__issuetracker_emailfriends'
SORTORDER_COOKIEKEY = '__issuetracker_sortorder'
SORTORDER_REVERSE_COOKIEKEY = '__issuetracker_sortorder_reverse'
DRAFT_ISSUE_IDS_COOKIEKEY = '__issuetracker_draft_issue_ids'
DRAFT_THREAD_IDS_COOKIEKEY = '__issuetracker_draft_followup_ids'
AUTOLOGIN_COOKIEKEY = '__issuetracker_autologin'
WHICHLIST_COOKIEKEY = '__issuetracker_list'
WHICHSUBLIST_COOKIEKEY = '__issuetracker_sublist'
LAST_SAVEDFILTER_ID_COOKIEKEY = '__issuetracker_savedfilter_id'
REMEMBER_SAVEDFILTER_PERSISTENTLY_COOKIEKEY = '__issuetracker_rsp'
LOGOUT_PAGE_COOKIEKEY = '__issuetracker_logout_page' 

USE_ACCESSKEYS_COOKIEKEY = '__issuetracker_use_akeys'
SAVED_FILTERS_COOKIEKEY = '__issuetracker_saved_filters'
SHOW_NEXTACTIONS_COOKIEKEY = '__issuetracker_show_nextactions'

RECENTHISTORY_SEARCHKEY = '__issuetracker_recenthistory_searches'
RECENTHISTORY_ISSUEIDVISITKEY = '__issuetracker_recenthistory_issueidvisit'
RECENTHISTORY_ISSUESKEY = '__issuetracker_recenthistory_issues'
RECENTHISTORY_ADDISSUEIDKEY = '__issuetracker_recenthistory_addissueid'
RECENTHISTORY_REPORTSKEY = '__issuetracker_recenthistory_reports'
SHOW_FILTEROPTIONS_KEY = '__issuetracker_show_filteroptions'
FILTEROPTIONS_KEY = '__issuetracker_filteroptions'
ALREADY_NOT_SPAMBOT_COOKIE_KEY = '__it_AlreadyNotSpambot'


# Misc
AUTOSAVE_INTERVAL_SECONDS = 4
FILTERVALUER_EXPIRATION_DAYS = 30 # saved filters > this gets cleaned away
FILTERVALUER_MAX_PER_USER = 20 # how many saved filters one person can have
FILTERVALUEFOLDER_THRESHOLD_CLEANING = 1000 # when 
SPAMBAYES_CHECK = 'spam' # if X-Spambayes-Classification=$this delete the inbound email
BTREEFOLDER2_ID = 'issues' # if a BTreeFolder2 is used, use this id
POSSIBLE_USER_LISTS = ['assignments', 'added', 'followedup', 'subscribed']

MENUICONS_DATA = {'Home':{'src':'home.gif', 'size':'16x16'},
                  'AddIssue':{'src':'add.gif', 'size':'16x16', 'alt':'Add Issue'},
                  'QuickAddIssue':{'src':'add.gif', 'size':'16x16', 'alt':'Quick Add Issue'},
                  'ListIssues':{'src':'list.gif', 'size':'16x16', 'alt':'List Issues'},
                  'CompleteList':{'src':'complete.gif', 'size':'16x16', 'alt':'Complete List'},
                  'User':{'src':'user.gif', 'size':'16x16'},
                  'Login':{'src':'login.gif', 'size':'16x16'},
                  'Logout':{'src':'logout.gif', 'size':'16x16'},
                  
                  }
for title, data in MENUICONS_DATA.items():
    if not data.has_key('width'):
        data['width'] = data['size'].split('x')[0]        
    if not data.has_key('height'):
        data['height'] = data['size'].split('x')[1]
    if not data['src'].startswith('/'):
        data['src'] = '/misc_/IssueTrackerProduct/%s'%data['src']
    if not data.has_key('alt'):
        data['alt'] = title
    MENUICONS_DATA[title] = data


DEFAULT_DATEPICKER_OPTIONS = """
dateFormat: 'yy-mm-dd',
minDate: -1,
showButtonPanel: true,
changeMonth: true,
changeYear: true
"""