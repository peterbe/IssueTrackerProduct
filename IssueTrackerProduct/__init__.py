# IssueTrackerProduct
# www.IssueTrackerProduct.com
# Peter Bengtsson <mail@peterbe.com>
#
import os

from AccessControl.Permission import registerPermissions
from zLOG import LOG, ERROR, INFO
from App.Dialogs import MessageDialog

import IssueTracker
import Thread
import IssueTrackerNotifyables as Notifyables
import Issue
import Email
import IssueUserFolder
import ReportScript
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
    if 1:#try:


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

        registerIcon('issue.gif')
        registerIcon('issuedraft.gif')
        registerIcon('issuethreaddraft.gif')
        registerIcon('issuethread.gif')
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
        registerIcon('reports.gif')
        registerIcon('statistics.gif')
        registerIcon('report-big.png')
        registerIcon('close.gif')
        registerIcon('paperclip.gif')
        registerIcon('gradhead.png')
        registerIcon('gradissuehead.png')
        registerIcon('gradtablehead.png')
        registerJS('tw-sack.js')
        registerJS('core.js')
        
        
        icons = Utils.uniqify(ICON_ASSOCIATIONS.values())
        for icon in icons:
            registerIcon(icon, epath='icons')
        menuicons = ('add.gif', 'list.gif', 'complete.gif', 'home.gif',
                     'user.gif','login.gif', 'logout.gif')
        for micon in menuicons:
            registerIcon(micon, epath='menuicons')
        
#        tiny_mce_images = {'tinymce/themes/simple/images':
#                           ('bold.gif','bullist.gif','cleanup.gif','italic.gif',
#                            'numlist.gif','redo.gif','spacer.gif','strikethrough.gif',
#                            'underline.gif','undo.gif'),
#                           }
#        for path, imagenames in tiny_mce_images.items():
#            for imagename in imagenames:
#                registerIcon(imagename, epath=path,
#                             startpath='')
        


        ##context.registerHelp()
        ##context.registerHelpTitle('IssueTrackerProduct Help')
    else:#except:
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
        LOG("IssueTrackerProduct", ERROR, "Could not be installed", 
            error=sys.exc_info())



import OFS, App

def registerIcon(filename, idreplacer={}, epath=None, startpath='www'):
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
    setattr(OFS.misc_.misc_.IssueTrackerProduct, 
            objectid, 
            App.ImageFile.ImageFile(os.path.join(path, filename), globals())
            )
            
def registerJS(filename, path='js'):
    product = OFS.misc_.misc_.IssueTrackerProduct
    objectid = filename
    setattr(product,
            objectid, 
            App.ImageFile.ImageFile(os.path.join(path, filename), globals())
            )
    obj = getattr(product, objectid)
    if js_slimmer is not None and OPTIMIZE:
        slimmed = js_slimmer(open(obj.path,'rb').read())
        new_path = obj.path + '-slimmed'
        open(new_path, 'wb').write(slimmed)
        setattr(obj, 'path', new_path)
    

