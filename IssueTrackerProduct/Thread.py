# IssueTrackerProduct
# www.issuetrackerproduct.com
#
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

# python
import sys

# Zope
from Globals import InitializeClass, DTMLFile
from AccessControl import ClassSecurityInfo
from zLOG import LOG, ERROR, INFO, PROBLEM, WARNING
from DateTime import DateTime

# Is CMF installed?
try:
    from Products.CMFCore.utils import getToolByName as CMF_getToolByName
except ImportError:
    CMF_getToolByName = None


# Product
from Issue import IssueTrackerIssue
from TemplateAdder import addTemplates2Class
import Utils
from Constants import *
from Permissions import VMS
from I18N import _

#----------------------------------------------------------------------------

manage_addIssueTrackerIssueThreadForm = DTMLFile('dtml/NotImplemented', globals())
def manage_addIssueTrackerIssueThread(*args, **kw):
    """ This is not supported """
    raise "WrongUse", "This method should not be used"

#----------------------------------------------------------------------------


class IssueTrackerIssueThread(IssueTrackerIssue): 
    """ Issuethreads class """

    meta_type = ISSUETHREAD_METATYPE
    icon = '%s/issuethread.gif'%ICON_LOCATION
    

    _properties=({'id':'title',         'type': 'string', 'mode':'w'},
                 {'id':'comment',       'type': 'text',   'mode':'w'},
                 {'id':'threaddate',    'type': 'date',   'mode':'w'},
                 {'id':'fromname',      'type': 'string', 'mode':'w'},
                 {'id':'email',         'type': 'string', 'mode':'w'},
                 {'id':'acl_adder',     'type': 'string', 'mode':'w'},
                 {'id':'display_format','type': 'string', 'mode':'w'},
                 )
    
    security=ClassSecurityInfo()

    manage_options = (
        {'label':'Properties', 'action':'manage_propertiesForm'},
        {'label':'Contents', 'action':'manage_main'},                     
        )

    acl_adder = '' # backward compatability

    def __init__(self, id, title, comment, threaddate, fromname, email,
                 display_format=None, acl_adder='', submission_type=''):
        """ create thread """
        self.id = str(id)
        self.title = title
        self.comment = comment
        if Utils.same_type(threaddate, 's'):
            threaddate = DateTime(threaddate)
        self.threaddate = threaddate
        self.fromname = fromname
        self.email = email
        if display_format:
            self.display_format = display_format
        else:
            self.display_format = self.default_display_format

        if acl_adder is None:
            acl_adder = ''
        self.acl_adder = acl_adder
        self.submission_type = submission_type
        self.email_message_id = None

    def getTitle(self):
        """ return title """
        return self.title

    def getThreadDate(self):
        """ return threaddate """
        return self.threaddate

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
                authenticated_member = mtool.getAuthenticatedMember()
                if authenticated_member.getProperty('fullname'):
                    return authenticated_member.getProperty('fullname')                
            
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
                authenticated_member = mtool.getAuthenticatedMember()
                if authenticated_member.getProperty('email'):
                    return authenticated_member.getProperty('email')                
            
        return self.email        

    def getACLAdder(self):
        """ return acl_adder """
        return self.acl_adder    
    
    def _setACLAdder(self, acl_adder):
        """ set acl_adder """
        self.acl_adder = acl_adder
        
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
    
    
    def _prerender_comment(self):
        """ Run the methods that pre-renders the comment of the issue. """
        comment = self.getComment()
        display_format = self.display_format
        formatted = self.ShowDescription(comment+' ', display_format)

        
        if self.getSubmissionType()=='email':
            formatted = Utils.highlight_signature(formatted, 'class="sig"')
        
        formatted = self._findIssueLinks(formatted)
        
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
    
    def getSubmissionType(self):
        """ return how it was submitted, empty string if not found """
        return getattr(self, 'submission_type', '')
    
    def getEmailMessageId(self):
        """ if the email was submitted via email it will most likely have
        a message id """
        # important to use the aq_base because otherwise we might pick it up
        # from the parenting issue
        base = getattr(self, 'aq_base', self)
        
        return getattr(base, 'email_message_id', None)
    
    def _setEmailMessageId(self, message_id):
        """ set the email message id """
        assert message_id.strip(), "Message_id not valid"
        self.email_message_id = message_id.strip()
    
    def _setEmailOriginal(self, original_email):
        """ set the original_email attribute """
        self.original_email = original_email
        
    def hasEmailOriginal(self):
        """ return if we have a 'original_email' attribute set """
        return hasattr(self, 'original_email')
    
    def ShowOriginalEmail(self, REQUEST):
        """ return the original email text """
        if REQUEST:
            REQUEST.RESPONSE.setHeader('Content-Type','text/plain')
        return self.original_email
    
    def index_object(self, idxs=['comment','meta_type','fromname','email']):
        """A common method to allow Findables to index themselves."""
        path = '/'.join(self.getPhysicalPath())
        catalog = self.getCatalog()
        
        # because the ZCatalog might not yet have the 
        # 'filenames' KeywordIndex we can't catalog this object
        # with that index.
        # Performing the following check every time takes
        # time so by 2007 this whole if statement below can probably
        # be removed because by then, must people will have updated
        # their issuetrackers to enable the new 'filenames' 
        # KeywordIndex 
        indexes = catalog._catalog.indexes
        if 'filenames' not in idxs and indexes.has_key('filenames'):
            idxs.append('filenames')
        catalog.catalog_object(self, path, idxs=idxs)

    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        self.getCatalog().uncatalog_object('/'.join(self.getPhysicalPath()))

        
    security.declareProtected(VMS, 'manage_editProperties')
    def manage_editProperties(self, REQUEST):
        """ re-prerender the description of the issue after manual change """
        result = IssueTrackerIssue.manage_editProperties(self, REQUEST)
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
                LOG(self.__class__.__name__, ERROR, 
                    "Unable to _prerender_comment() in manage_editProperties()",
                    error=sys.exc_info())        
        return result
    
    
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
                LOG(self.__class__.__name__, ERROR, 
                    "Unable to _prerender_comment() after add",
                    error=sys.exc_info())

                    
    security.declareProtected(VMS, 'assertAllProperties')
    def assertAllProperties(self):
        """ make sure issue has all properties """
        props = { # currently nothing
                 }
                 
        count = 0
        for key, default in props.items():
            if not self.__dict__.has_key(key):
                self.__dict__[key] = default
                count += 1
                
        # check that self.fromname is as good as self.getFromname()
        attr_fromname = self.getFromname(issueusercheck=False)
        linked_fromname = self.getFromname(issueusercheck=True)
        if linked_fromname != attr_fromname:
            # for sanity, check that the linked fromname is ok
            if linked_fromname:
                self.fromname = linked_fromname
                count += 1
                
        # check that self.email is as good as self.getFromname()
        attr_email = self.getEmail(issueusercheck=False)
        linked_email = self.getEmail(issueusercheck=True)
        if linked_email != attr_email:
            # for sanity, check that the linked email is ok
            if linked_email:
                self.email = linked_email
                count += 1
                
        return count    


    def showThreadFileattachments(self, only_temporary=0):
        """ wrap around the showFileattachments() method """
        files = []
        container = self.getFileattachmentContainer(only_temporary=only_temporary)
        return self.showFileattachments(container)
    


InitializeClass(IssueTrackerIssueThread)

#-----------------------------------------------------------------------------

class IssueTrackerDraftIssueThread(IssueTrackerIssueThread):
    """ There are used for the 'Save as draft' feature
    when writing a followup on an issue. The major difference
    between these and IssueTrackerIssueThread is that these
    draft objects must not be indexed in the Catalog. """
    
    meta_type = ISSUETHREAD_DRAFT_METATYPE
    icon = '%s/issuethreaddraft.gif'%ICON_LOCATION
    
    security=ClassSecurityInfo()
    
    manage_options = (
        {'label':'Contents',   'action':'manage_main'},
        {'label':'Properties', 'action':'manage_draftthread_properties'},
        )
        
    def __init__(self, id, issueid, action, title=None,
                 comment=None, threaddate=None,
                 fromname=None, email=None,
                 display_format=None, acl_adder=None,
                 is_autosave=False):
        """ create draft thread """
        self.id = str(id)
        self.issueid = issueid
        self.action = action
        self.title = title
        self.comment = comment
        if Utils.same_type(threaddate, 's'):
            threaddate = DateTime(threaddate)
        self.threaddate = threaddate
        self.fromname = fromname
        self.email = email
        self.display_format = display_format
        
        self.is_autosave = bool(is_autosave)
            
        if not acl_adder: # '', 0 or None
            acl_adder = ''
        self.acl_adder = acl_adder

    # legacy support
    is_autosave = False
        
    def getIssueId(self):
        """ return issueid """
        return self.issueid
    
    def getIssuePath(self):
        """ return a relative URL to where the issue is """
        rootpath = self._getIssueContainer().absolute_url_path()
        if rootpath == '/':
            return '/' + self.getIssueId()
        else:
            return rootpath + '/' + self.getIssueId()
        
    
    def index_object(self, *args, **kws):
        """ do NOT index this object """
        pass
    
    def unindex_object(self, *args, **kws):
        """ nothing to unindex """
        pass
    
    def manage_afterAdd(self, REQUEST, RESPONSE):
        """ the base class defines this to prerender the comment, something we
        don't want to do. """
        pass
    
    
    def ModifyThread(self, 
                     title=None,
                     comment=None,
                     display_format=None,
                     fromname=None,
                     email=None,
                     acl_adder=None,
                     is_autosave=False,
                     REQUEST=None):
        """ since normal threads don't allow changes, we need to
        add this very custom method to the drafts """
        if title is not None:
            self.title = title
            
        if comment is not None:
            self.comment = comment
            
        if display_format is not None:
            self.display_format = display_format
            
        if fromname is not None:
            self.fromname = fromname

        if email is not None:
            self.email = email

        if acl_adder is not None:
            self.acl_adder = acl_adder
            
        self.is_autosave = bool(is_autosave)
            
    def isAutosave(self):
        """ return if this was saved as an autosave or a plain draft """
        return self.is_autosave
    
    def shortDescription(self, maxlength=55, html=True):
        """ return a simplified description where the title is shown
        and then as much of the description as possible. """
        title = self.getTitle()
        if title is None:
            title = self.action
        if not title.strip():
            if html:
                title = "<i>(%s)</i>" % _("No subject")
            else:
                title = "(%s)" % _("No subject")
        desc = self.getCommentPure()
        
        shortened = self.lengthLimit(title, maxlength, "|...|")
        if shortened.endswith('|...|'):
            # the title was shortened
            shortened = shortened[:-len('|...|')]
            if html:
                return "<b>%s</b>..."%shortened
            else:
                return shortened+'...'
        else: 
            # i.e. title==shortened
            # put some of the description ontop
            if len(shortened) + len(desc) > maxlength:
                desc = self.lengthLimit(desc, maxlength-len(title))
                
            if html:
                return "<b>%s</b>, %s"%(shortened, desc)
            else:
                return "%s, %s"%(shortened, desc)
    
            
    def get__dict__keys(self):
        """ return the names of the keys we might have """
        return ('issueid', 'action', 'title', 'comment', 
                'fromname', 'email', 'display_format',
                'acl_adder', 'is_autosave')

    def get__dict__nicely(self):
        """ same as get__dict__keys() but we wrap it nicely """
        ok = []
        for key in self.get__dict__keys():
            if self.__dict__.get(key, None) is not None:
                ok.append({'key':key,
                           'value':self.__dict__.get(key)})
        return ok 
            
    
dtmls = ({'f':'dtml/draftissuethread_properties', 'n':'manage_draftthread_properties'},
         )
addTemplates2Class(IssueTrackerDraftIssueThread, dtmls, "dtml")

InitializeClass(IssueTrackerDraftIssueThread)

