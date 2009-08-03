# IssueTrackerProduct
# www.IssueTrackerProduct.com
# Peter Bengtsson <mail@peterbe.com>
#
import os
import stat
from time import time
import logging

from AccessControl.Permission import registerPermissions
from App.Dialogs import MessageDialog

import IssueTracker
import Thread
import Note
import IssueTrackerNotifyables as Notifyables
import Issue
import Email
import IssueUserFolder
import ReportScript
import CustomField
import Utils
from Constants import *
from Permissions import *
from I18N import *


try:
    from slimmer import js_slimmer, css_slimmer
except ImportError:
    css_slimmer = js_slimmer = None


"""IssueTracker Product"""

def dummyFunction(zope):
    """ dummy function because we don't want to use the ZMI for 
    some classes. """
    return MessageDialog(title="Add Issue Error",
           message="Don't add Issue Tracker Issues with the Zope management interface;"\
                   "instead, use the Issue Tracker only",
                   action="manage_main")
                    

def initialize(context):
    """ Initialize IssueTracker product """
    from Globals import DevelopmentMode
    
    import UnicodeSplitter
    
    try:


        context.registerClass(
            IssueTracker.IssueTracker,
            constructors = (
                # This is called when
                IssueTracker.manage_addIssueTrackerForm,
                # someone adds the product
                IssueTracker.manage_addIssueTracker,
                # also useful in the DTML add template
                IssueTracker.manage_hasAquirableMailHost
                ),
            icon = "www/issuetracker.gif"
            )
                    
        context.registerClass(
            Issue.IssueTrackerIssue,
            constructors = (dummyFunction,),
            permission = AddIssuesPermission,
            icon = 'www/issue.gif',
            #visibility = None # settings this to None disables copy/cut/paste support
            )


        context.registerClass(
            Notifyables.IssueTrackerNotifyableContainer,
            constructors = (
                # This is called when
                Notifyables.manage_addNotifyableContainerForm,
                # someone adds the product
                Notifyables.manage_addNotifyableContainer         
                ),
            icon = "www/issuetracker_notifyablecontainer.gif"

            )

        context.registerClass(
            IssueUserFolder.IssueUserFolder,
            constructors=(
                IssueUserFolder.manage_addIssueUserFolderForm,
                IssueUserFolder.manage_addIssueUserFolder,
                IssueUserFolder.manage_getUsersToConvert
                ),
            icon='www/issueuserfolder.gif',
        )
        
        context.registerClass(
            ReportScript.ReportScript,
            constructors=(
                ReportScript.manage_addIssueReportScriptForm,
                ReportScript.manage_addIssueReportScript,
                ),
            icon='www/issuereportscript.gif',
        )
        
        context.registerClass(
            CustomField.CustomField,
            constructors=(
                CustomField.manage_addCustomFieldForm,
                CustomField.manage_addCustomField,
                ),
            icon='www/customfield.png',
        )
        
        context.registerClass(
            CustomField.CustomFieldFolder,
            constructors=(
                CustomField.manage_addCustomFieldFolderForm,
                CustomField.manage_addCustomFieldFolder,
                ),
            icon='www/customfieldfolder.png',
        )        
        
        def registerIcon(filename, **kw):
            _registerIcon(OFS.misc_.misc_.IssueTrackerProduct, filename, **kw)
            
        def registerJS(filename, **kw):
            _registerJS(OFS.misc_.misc_.IssueTrackerProduct, filename, **kw)
        
        def registerCSS(filename, **kw):
            _registerCSS(OFS.misc_.misc_.IssueTrackerProduct, filename, **kw)

        registerIcon('issue.gif')
        registerIcon('issuedraft.gif')
        registerIcon('issuethreaddraft.gif')
        registerIcon('issuethread.gif')
        registerIcon('issuenote.png')
        registerIcon('new-issuenote.png')
        registerIcon('issuetracker_notifyable.gif')
        registerIcon('issuetracker_notifyablegroup.gif')
        registerIcon('issueassignment.gif')
        registerIcon('notification.gif')
        registerIcon('issuetracker_pop3account.gif')
        registerIcon('issuetracker_acceptingemail.gif')
        registerIcon('issuetracker_logo_error.gif')
        registerIcon('bar.gif')
        registerIcon('issuereportscontainer.gif')
        registerIcon('emailicon.gif')
        registerIcon('spreadsheeticon.png')
        registerIcon('reports.gif')
        registerIcon('statistics.gif')
        registerIcon('report-big.png')
        registerIcon('close.gif')
        registerIcon('paperclip.gif')
        registerIcon('gradhead.png')
        registerIcon('gradissuehead.png')
        registerIcon('gradtablehead.png')
        registerIcon('customfieldfolder.png')
        registerJS('core.js')
        registerJS('jquery-1.3.2.min.js', slim_if_possible=False)
        registerJS('jquery-ui-1.7.1.datepickeronly.min.js', slim_if_possible=False)
        registerJS('manage-customfield.js')
        registerJS('jquery.qtip-1.0.0-rc3.min.js', slim_if_possible=False)
        registerJS('issuenotes.js')
        registerCSS('jquery-ui-1.7.1.datepickeronly.css')
        
        icons = Utils.uniqify(ICON_ASSOCIATIONS.values())
        for icon in icons:
            registerIcon(icon, epath='icons')
        menuicons = ('add.gif', 'list.gif', 'complete.gif', 'home.gif',
                     'user.gif','login.gif', 'logout.gif')
        for micon in menuicons:
            registerIcon(micon, epath='menuicons')
        
        ui_icons = os.listdir(os.path.join(package_home(globals()), 'www', 'ui_icons'))
        ui_icons = [x for x in ui_icons if x.endswith('.png') or x.endswith('.gif')]
        for ui_icon in ui_icons:
            registerIcon(ui_icon, epath='ui_icons')
            
    except:
        if DevelopmentMode:
            raise
        """If you can't register the product, tell someone. 
        
        Zope will sometimes provide you with access to "broken product" and
        a backtrace of what went wrong, but not always; I think that only 
        works for errors caught in your main product module. 
        
        This code provides traceback for anything that happened in 
        registerClass(), assuming you're running Zope in debug mode."""
        import sys, traceback, string
        type, val, tb = sys.exc_info()
        sys.stderr.write(string.join(traceback.format_exception(type, val, tb), ''))
        traceback.print_exc(sys.stdout) # for all those people in debug mode zope
        del type, val, tb
        logging.info("IssueTrackerProduct. Could not be installed",
                     exc_info=True)


import OFS, App

from App.Common import rfc1123_date
from ZPublisher.Iterators import filestream_iterator
from Globals import package_home, DevelopmentMode
try:
    from zope.app.content_types import guess_content_type
except ImportError:
    from OFS.content_types import guess_content_type
    
FILESTREAM_ITERATOR_THRESHOLD = 2 << 16 # 128 Kb (from LocalFS StreamingFile.py)


class BetterImageFile(App.ImageFile.ImageFile): # that name needs to improve
    
    def __init__(self, path, _prefix=None, 
                 max_age_development=3600,
                 max_age_production=3600*24*7,
                 content_type=None, set_expiry_header=True):
        if _prefix is None:
            _prefix = getConfiguration().softwarehome
        elif type(_prefix) is not type(''):
            _prefix = package_home(_prefix)
        path = os.path.join(_prefix, path)
        self.path = path
        self.set_expiry_header = set_expiry_header
        
        if DevelopmentMode:
            # In development mode, a shorter time is handy
            max_age = max_age_development
        else:
            # A longer time reduces latency in production mode
            max_age = max_age_production
        self.max_age = max_age
        self.cch = 'public,max-age=%d' % max_age

        data = open(path, 'rb').read()
        if content_type is None:
            content_type, __ = my_guess_content_type(path, data)
        if content_type:
            self.content_type=content_type
        else:
            raise ValueError, "content_type not set or couldn't be guessed"
            #self.content_type='text/plain'
            
        self.__name__=path[path.rfind('/')+1:]
        self.lmt=float(os.stat(path)[8]) or time.time()
        self.lmh=rfc1123_date(self.lmt)
        self.content_size = os.stat(path)[stat.ST_SIZE]
        
        
    def index_html(self, REQUEST, RESPONSE):
        """Default document"""
        # HTTP If-Modified-Since header handling. This is duplicated
        # from OFS.Image.Image - it really should be consolidated
        # somewhere...
        RESPONSE.setHeader('Content-Type', self.content_type)
        RESPONSE.setHeader('Last-Modified', self.lmh)
        RESPONSE.setHeader('Cache-Control', self.cch)
        RESPONSE.setHeader('Content-Length', self.content_size)
        if self.set_expiry_header:
            RESPONSE.setHeader('Expires', self._expires())
            

        header=REQUEST.get_header('If-Modified-Since', None)
        if header is not None:
            header=header.split(';')[0]
            # Some proxies seem to send invalid date strings for this
            # header. If the date string is not valid, we ignore it
            # rather than raise an error to be generally consistent
            # with common servers such as Apache (which can usually
            # understand the screwy date string as a lucky side effect
            # of the way they parse it).
            try:    mod_since=long(DateTime(header).timeTime())
            except: mod_since=None
            if mod_since is not None:
                if getattr(self, 'lmt', None):
                    last_mod = long(self.lmt)
                else:
                    last_mod = long(0)
                if last_mod > 0 and last_mod <= mod_since:
                    RESPONSE.setStatus(304)
                    return ''

        if self.content_size > FILESTREAM_ITERATOR_THRESHOLD:
            return filestream_iterator(self.path, 'rb')
        else:
            return open(self.path,'rb').read()

    HEAD__roles__=None
    def HEAD(self, REQUEST, RESPONSE):
        """ """
        RESPONSE.setHeader('Content-Type', self.content_type)
        RESPONSE.setHeader('Last-Modified', self.lmh)
        RESPONSE.setHeader('Content-Length', self.content_size)
            
        return ''    

    def _expires(self):
        return rfc1123_date(time()+self.max_age)
    
    
def my_guess_content_type(path, data):
    content_type, enc = guess_content_type(path, data)
    if content_type in ('text/plain', 'text/html'):
        if os.path.basename(path).endswith('.js-slimmed'):
            content_type = 'application/x-javascript'
        elif os.path.basename(path).find('.css-slimmed') > -1:
            # the find() covers both 'foo.css-slimmed' and
            # 'foo.css-slimmed-data64expanded'
            content_type = 'text/css'
    return content_type, enc


def _registerIcon(product, filename, idreplacer={}, epath=None, startpath='www'):
    # A helper function that takes an image filename (assumed
    # to live in a 'www' subdirectory of this package). It 
    # creates an ImageFile instance and adds it as an attribute
    # of misc_.MyPackage of the zope application object (note
    # that misc_.MyPackage has already been created by the product
    # initialization machinery by the time registerIcon is called).
    objectid = filename
    if epath is not None:
        path = os.path.join(startpath, epath)
    else:
        path = startpath
    
    for k,v in idreplacer.items():
        objectid = objectid.replace(k,v)
    setattr(product,
            objectid, 
            #App.ImageFile.ImageFile(os.path.join(path, filename), globals())
            BetterImageFile(os.path.join(path, filename), globals())
            )
            
def _registerJS(product, filename, 
                path='js', slim_if_possible=True):
    objectid = filename
    setattr(product,
            objectid, 
            BetterImageFile(os.path.join(path, filename), globals())
            )            
    obj = getattr(product, objectid)
    if js_slimmer is not None and OPTIMIZE:
        if slim_if_possible:
            slimmed = js_slimmer(open(obj.path,'rb').read())
            new_path = obj.path + '-slimmed'
            open(new_path, 'wb').write(slimmed)
            setattr(obj, 'path', new_path)
    

def _registerCSS(product, filename, path='css', slim_if_possible=True):
    objectid = filename
    setattr(product,
            objectid, 
            BetterImageFile(os.path.join(path, filename), globals())
            )
    obj = getattr(product, objectid)
    if css_slimmer is not None and OPTIMIZE:
        if slim_if_possible:
            slimmed = css_slimmer(open(obj.path,'rb').read())
            new_path = obj.path + '-slimmed'
            open(new_path, 'wb').write(slimmed)
            setattr(obj, 'path', new_path)

            
            
            
            