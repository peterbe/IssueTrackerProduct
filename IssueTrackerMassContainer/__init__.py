import os
from zLOG import LOG, WARNING, ERROR

import MassContainer
"""IssueTrackerMassContainer Product"""

try:
    from Products import IssueTrackerProduct
    DO_INITIALIZE = True
    from Products.IssueTrackerProduct import BetterImageFile
    from Constants import *
    
except:
    LOG(MASSCONTAINER_METATYPE, WARNING,
        'IssueTrackerProduct not install', '')
    DO_INITIALIZE = False
    

def initialize(context):
    """ Initialize IssueTrackerMassContainer product """
    if DO_INITIALIZE:
        try:
            context.registerClass(
                MassContainer.MassContainer,
                constructors = (
                    # This is called when
                    MassContainer.manage_addMassContainerForm,
                    # someone adds the product
                    MassContainer.manage_addMassContainer       
                    ),
                icon = "www/issuetrackermasscontainer.gif"
                )
            
            registerIcon('rss-blue.png')
            registerIcon('file.gif')
            registerIcon('folder-closed.gif')
            registerIcon('folder.gif')
            registerIcon('minus.gif')
            registerIcon('plus.gif')
            registerIcon('treeview-black-line.gif')
            registerIcon('treeview-black.gif')
            registerIcon('treeview-default-line.gif')
            registerIcon('treeview-default.gif')
            registerIcon('treeview-famfamfam-line.gif')
            registerIcon('treeview-famfamfam.gif')
            registerIcon('treeview-gray-line.gif')
            registerIcon('treeview-gray.gif')
            registerIcon('treeview-red-line.gif')
            registerIcon('treeview-red.gif')
            registerIcon('icon_ignore.gif')
            registerIcon('refresh_icon.png')
            registerIcon('loading-bar.gif')

            registerJS('core.js', slim_if_possible=False)
            registerJS('jquery-1.2.3.min.js', slim_if_possible=False)
            registerJS('jquery.treeview.min.js', slim_if_possible=False)
            registerJS('jquery.cookie.js', slim_if_possible=False)
            registerCSS('jquery.treeview.css', slim_if_possible=False)


        except:
            """If you can't register the product, tell someone. 
            
            Zope will sometimes provide you with access to "broken product" and
            a backtrace of what went wrong, but not always; I think that only 
            works for errors caught in your main product module. 
            
            This code provides traceback for anything that happened in 
            registerClass(), assuming you're running Zope in debug mode."""
            import sys, traceback
            type, val, tb = sys.exc_info()
            err = ''.join(traceback.format_exception(type, val, tb))
            sys.stderr.write(err)
            del type, val, tb
            LOG(MASSCONTAINER_METATYPE, ERROR, "Unable to initialize IssueTrackerMassContainer",
                detail=err,
                error=sys.exc_info())
    



import OFS, App

try:
    from slimmer import js_slimmer, css_slimmer
except ImportError:
    css_slimmer = js_slimmer = None


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
    setattr(OFS.misc_.misc_.IssueTrackerMassContainer,
            objectid, 
            #App.ImageFile.ImageFile(os.path.join(path, filename), globals())
            BetterImageFile(os.path.join(path, filename), globals())
            )
            
def registerJS(filename, path='js', slim_if_possible=True):
    product = OFS.misc_.misc_.IssueTrackerMassContainer
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
    

def registerCSS(filename, path='css', slim_if_possible=True):
    product = OFS.misc_.misc_.IssueTrackerMassContainer
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

            
            