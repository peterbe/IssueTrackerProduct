# IssueTrackerProduct
#
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

# Zope
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from Globals import InitializeClass, DTMLFile
from Products.ZCatalog.CatalogAwareness import CatalogAware 
from AccessControl import ClassSecurityInfo
from DateTime import DateTime
from Acquisition import aq_inner, aq_parent

# Is CMF installed?
try:
    from Products.CMFCore.utils import getToolByName as CMF_getToolByName
except ImportError:
    CMF_getToolByName = None

# Product
from IssueTracker import IssueTrackerFolderBase
from TemplateAdder import addTemplates2Class
from Permissions import VMS
from I18N import _
from Constants import *
from Utils import unicodify, asciify

#----------------------------------------------------------------------------

manage_addIssueNoteForm = DTMLFile('dtml/NotImplemented', globals())
def manage_addIssueNote(*args, **kw):
    """ This is not supported """
    raise NotImplementedError("This method should not be used")

#----------------------------------------------------------------------------


class IssueNote(SimpleItem, PropertyManager, CatalogAware, 
                IssueTrackerFolderBase,# needed?
               ):
    """
    A note is put on an issue or a followup inside an issue.
    """

    meta_type = ISSUENOTE_METATYPE
    icon = '%s/issuenote.png' % ICON_LOCATION


    _properties=({'id':'title',         'type': 'ustring', 'mode':'w'},
                 {'id':'comment',       'type': 'utext',   'mode':'w'},
                 {'id':'public',        'type': 'boolean', 'mode':'w'},
                 {'id':'notedate',      'type': 'date',    'mode':'w'},
                 {'id':'fromname',      'type': 'ustring', 'mode':'w'},
                 {'id':'email',         'type': 'string',  'mode':'w'},
                 {'id':'acl_adder',     'type': 'string',  'mode':'w'},
                 {'id':'threadID',      'type': 'string',  'mode':'w'},
                 {'id':'display_format','type': 'string',  'mode':'w'},
                 )
    
    security=ClassSecurityInfo()

    manage_options = (
        {'label':'Properties', 'action':'manage_propertiesForm'},
        )

    acl_adder = '' # backward compatability

    def __init__(self, id, title, comment, fromname, email,
                 public=False, notedate=None, 
                 display_format=None, acl_adder='', threadID=''):
        """ create thread """
        self.id = str(id)
        self.title = unicodify(title)
        self.comment = unicodify(comment)
        if isinstance(notedate, basestring):
            notedate = DateTime(notedate)
        elif not notedate:
            notedate = DateTime()
        self.notedate = notedate
        self.public = bool(public)
        self.fromname = unicodify(fromname)
        if isinstance(email, basestring):
            email = asciify(email, 'ignore')
        self.email = email
        self.display_format = display_format

        if acl_adder is None:
            acl_adder = ''
        self.acl_adder = acl_adder
        self.threadID = threadID
        
    def _getIssue(self):
        """a note always belongs to an issue"""
        return aq_parent(aq_inner(self))
        
    def getModifyDate(self):
        return self.bobobase_modification_time()
    
    def isPublic(self):
        return self.public

    def getFromname(self, issueusercheck=True):
        """ return fromname """
        acl_adder = self.getACLAdder()
        if issueusercheck and acl_adder:
            ufpath, name = acl_adder.split(',')
            try:
                uf = self.unrestrictedTraverse(ufpath)
            except KeyError:
                try:
                    uf = self.unrestrictedTraverse(ufpath.split('/')[-1])
                except KeyError:
                    # the userfolder (as it was saved) no longer exists
                    return self.fromname
            
            if uf.meta_type == ISSUEUSERFOLDER_METATYPE:
                if uf.data.has_key(name):
                    issueuserobj = uf.data[name]
                    return issueuserobj.getFullname() or self.fromname
            elif CMF_getToolByName and hasattr(uf, 'portal_membership'):
                mtool = CMF_getToolByName(self, 'portal_membership')
                member = mtool.getMemberById(name)
                if member and member.getProperty('fullname'):
                    return member.getProperty('fullname')                
            
        return self.fromname
        

    def getEmail(self, issueusercheck=True):
        """ return email """
        acl_adder = self.getACLAdder()
        if issueusercheck and acl_adder:
            ufpath, name = acl_adder.split(',')
            try:
                uf = self.unrestrictedTraverse(ufpath)
            except KeyError:
                try:
                    uf = self.unrestrictedTraverse(ufpath.split('/')[-1])
                except KeyError:
                    # the userfolder (as it was saved) no longer exists
                    return self.email
            
            if uf.meta_type == ISSUEUSERFOLDER_METATYPE:
                if uf.data.has_key(name):
                    issueuserobj = uf.data[name]
                    return issueuserobj.getEmail() or self.email
            elif CMF_getToolByName and hasattr(uf, 'portal_membership'):
                mtool = CMF_getToolByName(self, 'portal_membership')
                member = mtool.getMemberById(name)
                if member and member.getProperty('email'):
                    return member.getProperty('email')
            
        return self.email        

    def getACLAdder(self):
        """ return acl_adder """
        return self.acl_adder    
    
    def _setACLAdder(self, acl_adder):
        """ set acl_adder """
        self.acl_adder = acl_adder
        
    def getThreadID(self):
        return self.threadID
    
    def getThread(self):
        return getattr(self, self.getThreadID(), None)
    
    def getComment(self):
        """ return comment """
        return self.comment
    
    def getCommentPure(self):
        """ return comment purified.
        If the comment contains HTML for example, remove it."""
        comment = self.getComment()
        if self.getDisplayFormat() =='html':
            # textify() coverts "<tag>Something</tag>" to "Something". Simple.
            comment = Utils.textify(comment)
            
            # a very common thing is that the description contains
            # these faux double linebreaks and when you run textify()
            # on '<p>&nbsp;</p>' the result is '&nbsp;'. Too many of
            # those result in '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;' which 
            # isn't pure and purifying is what this method aims to do
            comment = comment.replace('<p>&nbsp;</p>','')
            
        return comment

    def _unicode_comment(self):
        """ make the comment of this thread a unicode string """
        self.comment = unicodify(self.comment)
        self._prerendered_comment = unicodify(self._prerendered_comment)
    
    def _prerender_comment(self):
        """ Run the methods that pre-renders the comment of the issue. """
        comment = self.getComment()
        display_format = self.display_format
        formatted = self.ShowDescription(comment+' ', display_format)
        
        formatted = self._getIssue()._findIssueLinks(formatted)
        
        self._prerendered_comment = formatted    
    
    def _getFormattedComment(self):
        """ return the comment formatted """
        if getattr(self, '_prerendered_comment', None):
            formatted = self._prerendered_comment
        else:
            comment = self.getComment()
            display_format = self.display_format
            formatted = self.ShowDescription(comment+' ', display_format)
            
        return formatted
        

    def showComment(self):
        """ combine ShowDescription (which is generic) with this
        threads display format."""
        formatted = self._getFormattedComment()
        return self.HighlightQ(formatted)

    def index_object(self, idxs=None):
        """A common method to allow Findables to index themselves."""
        path = '/'.join(self.getPhysicalPath())
        catalog = self.getCatalog()
        
        if idxs is None:
            # because I don't want to put mutable defaults in 
            # the keyword arguments
            idxs = ['comment', 'meta_type', 'fromname', 'email',
                    'path', 'modifydate']#, 'public']
        else:
            # No matter what, when indexing you must always include 'path'
            # otherwise you might update indexes without putting the object
            # brain in the catalog. If that happens the object won't be 
            # findable in the searchResults(path='/some/path') even if it's
            # findable on other indexes such as comment.
            if 'path' not in idxs:
                idxs.append('path')
        
        catalog.catalog_object(self, path, idxs=idxs)


    def getFromname_idx(self):
        return self.getFromname()
    
    def getComment_idx(self):
        return self.getComment()
        
    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        self.getCatalog().uncatalog_object('/'.join(self.getPhysicalPath()))
        
    def manage_afterAdd(self, REQUEST, RESPONSE):
        """ intercept so that we prerender always """
        try:
            self._prerender_comment()
        except:
            if DEBUG:
                raise
            else:
                try:
                    err_log = self.error_log
                    err_log.raising(sys.exc_info())
                except:
                    pass
                logging.error("Unable to _prerender_comment() after add",
                              exc_info=True)


    security.declareProtected(VMS, 'assertAllProperties')
    def assertAllProperties(self):
        """ make sure it has all properties """
        return 0
        
InitializeClass(IssueNote)
