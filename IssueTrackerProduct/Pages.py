# IssueTrackerProduct
#
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

# python
#import warnings
#import re, sys, cgi, os
#from time import time
#from string import zfill
#try:
#    import transaction
#except ImportError:
#    # we must be in an older than 2.8 version of Zope
#    transaction = None
    
    
# Zope
#from Acquisition import aq_inner, aq_parent
from AccessControl import ClassSecurityInfo, getSecurityManager
from DateTime import DateTime
from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem
from Acquisition import aq_inner, aq_parent

try:
    # >= Zope 2.12
    from webdav.interfaces import IWriteLock
    from Persistence import Persistent
    from App.class_init import InitializeClass
except ImportError:
    # < Zope 2.12
    from webdav.WriteLockInterface import WriteLockInterface as IWriteLock
    from Globals import InitializeClass, Persistent

try:
    from persistent.mapping import PersistentMapping
    from persistent.list import PersistentList
except ImportError:
    # for old versions of Zope
    PersistentMapping = dict
    PersistentList = list



# Product
from TemplateAdder import addTemplates2Class
#import Utils
from Utils import unicodify, asciify, safeId
from Constants import *
from Errors import *
from Permissions import VMS
from I18N import _

#----------------------------------------------------------------------------


# Misc stuff

class BodyValidationError(Exception):
    pass


class Empty:
    pass


def _title_to_id(title):
    oid = asciify(title, 'ignore')
    oid = oid.replace(' ','-')
    oid = safeId(oid)
    if len(oid) > 50:
        oid = oid[:50]
        while oid.endswith('-'):
            oid = oid[:-1]
    
    return oid


#----------------------------------------------------------------------------


class PageBase(object):
    """Mixin class for the issuetracker to use"""
    
    def EnablePages(self):
        return getattr(self, 'enable_pages', DEFAULT_ENABLE_PAGES)
    
    def getPageFolder(self):
        try:
            return self.Pages
        except AttributeError:
            if self.EnablePages():
                self._initPageFolder()
                return self.Pages
            else:
                raise AttributeError("Pages not enabled")
    
    def getPages(self):
        return self.Pages.objectValues(PAGE_METATYPE)
    
    def countPages(self):
        return len(self.getPages())
    
    def _initPageFolder(self):
        """make sure there is a PageFolder in this issuetracker called 
        'Pages' """
        root = self.getRoot()
        if not getattr(root, 'Pages', None):
            instance = PageFolder('Pages', _(u"Pages"))
            root._setObject('Pages', instance)
        
    
#----------------------------------------------------------------------------

class PageFolder(Folder, Persistent):
    
    meta_type = PAGE_FOLDER_METATYPE
    
    def __init__(self, id, title):
        self.id = str(id)
        self.title = unicodify(title)
        
    def getId(self):
        return self.id
    
    def getTitle(self):
        return self.title
    
    def _createPageObject(self, id, title, body,
                            fromname, email,
                            acl_adder='', ):
        """ Crudely create thread object. No checking. """
        raise NotImplementedError
        thread = IssueTrackerIssueThread(id, title, comment, threaddate,
                                         fromname, email, display_format,
                                         acl_adder=acl_adder,
                                         submission_type=submission_type)
        self._setObject(id, thread)

        # get that object
        threadobject = getattr(self, id)
        
        return threadobject
    
    def manage_afterAdd(self, REQUEST, RESPONSE):
        """make sure there is a catalog in place"""
        self._init_catalog()
        
    def _init_catalog(self):
        """make sure there is a ZCatalog here"""
        if not 'PCatalog' in self.objectIds('ZCatalog'):
            self.manage_addProduct['ZCatalog'].manage_addZCatalog('PCatalog','')
            
        zcatalog = self.getCatalog()
        indexes = zcatalog._catalog.indexes
        
        if 'meta_type' not in zcatalog.schema():
            zcatalog.addColumn('meta_type')
            
        if not hasattr(zcatalog, 'Lexicon'):
            # This default lexicon sucks because it doesn't support unicode.
            # Consider creating a http://www.zope.org/Members/shh/UnicodeLexicon
            # instead.
            script = zcatalog.manage_addProduct['ZCTextIndex'].manage_addLexicon
            
            wordsplitter = Empty()
            wordsplitter.group = 'Word Splitter'
            #wordsplitter.name = 'Whitespace splitter'
            wordsplitter.name = 'Unicode Whitespace splitter'
            
            casenormalizer = Empty()
            casenormalizer.group = 'Case Normalizer'
            #casenormalizer.name = 'Case Normalizer'
            casenormalizer.name = 'Unicode Case Normalizer'
            
            stopwords = Empty()
            stopwords.group = 'Stop Words'
            stopwords.name = 'Remove listed stop words only'
            
            script('Lexicon', 'Default Lexicon',
                   [wordsplitter, casenormalizer, stopwords])
            t['Lexicon'] = "Lexicon for ZCTextIndex created"
        
    
        for fieldindex in ('id','meta_type'):
            if not indexes.has_key(fieldindex):
                zcatalog.addIndex(fieldindex, 'FieldIndex')
                
        for keywordindex in ('filenames',):
            if not indexes.has_key(keywordindex):
                zcatalog.addIndex(keywordindex, 'KeywordIndex')
                
        pathindexes = [('path','getPhysicalPath'),]
        for idx, indexed_attrs in pathindexes:
            if not indexes.has_key(idx):
                extra = record()
                extra.indexed_attrs = indexed_attrs
                zcatalog.addIndex(idx, 'PathIndex', extra)                
        
                
        dateindexes = ['modifydate','pagedate']
            
        for idx in dateindexes:
            if not indexes.has_key(idx):
                #extra = record()
                zcatalog.addIndex(idx, 'DateIndex')
                
        zctextindexes = (
          ('title', 'getTitle_idx'),
          ('body', 'getBody_idx'),
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
                
                
    ##
    ## For adding new pages
    ##
    
    def addNewPage(self, REQUEST, RESPONSE):
        """page for adding new pages"""
        
        SubmitError = {}
        
        if REQUEST.REQUEST_METHOD == 'POST':
            print REQUEST.form
            title = REQUEST.form.get('title', '').strip()
            
            if not title:
                SubmitError['title'] = _(u"Title missing")
                
            if not SubmitError:
                page = self._createNewPage(title)
                
                return RESPONSE.redirect(page.absolute_url()+'/edit')
            
        return self.addNewPage_template(REQUEST, RESPONSE,
                                        SubmitError=SubmitError)
        
        
    def _createNewPage(self, title):
        """create the new Page instance and return it"""
        
        oid = _title_to_id(title)
        page = Page(oid, title, u"")
        self._setObject(oid, page)
        return getattr(self, oid)
        
    
zpts = ('zpt/Pages/index_html',
        'zpt/Pages/addNewPage_template',
)    
addTemplates2Class(PageFolder, zpts, extension='zpt')

InitializeClass(PageFolder)

#----------------------------------------------------------------------------


#----------------------------------------------------------------------------


class Page(Folder, Persistent):
    """A page is like a wiki page but without all the wiki aspects"""

    meta_type = PAGE_METATYPE
    
    _properties=({'id':'title',         'type': 'ustring', 'mode':'w'},
                 {'id':'pagedate',      'type': 'date',   'mode':'w'},
                 {'id':'modifydate',    'type': 'date',   'mode':'w'},
                 {'id':'body',          'type': 'utext',  'mode':'w'},
                 )
    
    
    security = ClassSecurityInfo()

    #manage_options = (
    #    {'label':'Contents', 'action':'manage_main'},
    #    {'label':'View', 'action':'index_html'},
    #    {'label':'Properties', 'action':'manage_propertiesForm'}
    #    )

    def __init__(self, id, title, body):
        self.id = str(id)
        self.title = unicodify(title.strip())
        self.body = unicodify(body.strip())
        self.pagedate = DateTime()
        
        #self.blocks_changelog = PersistentMapping()
        self.related_pages = PersistentMapping()
        self.subscribers = []
        

    def getId(self):
        """ return id """
        return self.id
    
    def getTitle(self):
        """ return title """
        return self.title

    def showTitle(self):
        """ return title html quoted """
        t = self.getTitle()
        return self.HighlightQ(Utils.tag_quote(t))

    def getModifyDate(self):
        """ return modifydate """
        return self.modifydate        

    security.declareProtected('View', 'getModifyTimestamp')
    def getModifyTimestamp(self):
        """ return the modify date as a integer timestamp """
        return int(self.getModifyDate())

    def _updateModifyDate(self):
        """ set the modify date again """
        self.modifydate = DateTime()        

    def getPageDate(self):
        return self.pagedate
    
    def getBody(self):
        return self.body

    def getBodyPure(self):
        """return body purified"""
        body = self.getBody()
        # a very common thing is that the body contains
        # these faux double linebreaks and when you run textify()
        # on '<p>&nbsp;</p>' the result is '&nbsp;'. Too many of
        # those result in '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;' which 
        # isn't pure and purifying is what this method aims to do
        body = body.replace('<p>&nbsp;</p>','')
        
        # textify() coverts "<tag>Something</tag>" to "Something". Simple.
        body = Utils.textify(body)
        return body
    
            
    security.declareProtected(VMS, 'assertAllProperties')
    def assertAllProperties(self):
        """ make sure issue has all properties """
        props = {}
                 
        count = 0
        for key, default in props.items():
            if not self.__dict__.has_key(key):
                self.__dict__[key] = default
                count += 1
        
        return count
                
    security.declareProtected('View', 'index_html')
    def index_html(self, REQUEST, *args, **kw):
        """show the page"""
        if self.canViewPage():
            self.RememberRecentPage(self.getId(), 'viewed')
            
            #if REQUEST.get('fileattachment', []):
            #    fake_fileattachments = self._getFakeFileattachments(REQUEST.get('fileattachment'))
            #    if fake_fileattachments:
            #        m = "Filename entered but no file content"
            #        SubmitError = {'fileattachment':m}
            #        self.REQUEST.set('previewissue',None)
            #        return self.ShowIssue(self, self.REQUEST, FollowupSubmitError=SubmitError, **kw)
            
            
            return self.ShowPage(self, self.REQUEST, **kw)
        else:
            response = self.REQUEST.RESPONSE
            listpage = '/%s'%self.whichList()
            response.redirect(self.getRootURL()+listpage)

        
    def canViewPage(self):
        # stubby
        return 1
    
    def edit(self, REQUEST, RESPONSE):
        """save changes to page"""
        SubmitError = {}
        
            
        if not self.canViewPage():
            # the chosen action requires manager role,
            # but the person is not a manager
            self.redirectlogin(came_from=self.absolute_url())
            return 

        if REQUEST.REQUEST_METHOD == "POST":
            
            title = REQUEST.form.get('title', '').strip()
            body = REQUEST.form.get('body', '').strip()
            
            parent = aq_parent(aq_inner(self))
            
            if not title:
                SubmitError['title'] = _(u"Missing")
            else:
                # check that there isn't already a page by this exact title
                for page in parent.getPages():
                    if page is not self:
                        if page.getTitle().lower() == title.lower():
                            SubmitError['title'] = \
                              _(u"Duplicate title. Already used on another page")
                            break
                
            body = unicodify(body)
            try:
                body = self._validate_and_clean_body(body)
            except BodyValidationError, msg:
                SubmitError['body'] = unicodify(msg)
                
            if not SubmitError:
                
                if title != self.getTitle():
                    # new title, need to rename
                    oid = _title_to_id(title)
                    
                    parent.manage_renameObjects([self.getId()], [oid])
                
                self._savePage(title, body, REQUEST)

                # ready ! redirect!
                RESPONSE.redirect(self.absolute_url()+'/edit')
            
        return self.edit_template(REQUEST, RESPONSE, SubmitError=SubmitError)
    
    def _validate_and_clean_body(self, html):
        # try to clean it and if we encounter any serious errors we can't
        # recover from then raise a BodyValidationError
        
        raise NotImplementedError("Use page templates as a final check")
        return html
    
                                  
    def _savePage(self, title, body, request):
        
        issueuser = self.getIssueUser()
        #cmfuser = self.getCMFUser()
        zopeuser = self.getZopeUser()
        if issueuser:
            acl_adder = ','.join(issueuser.getIssueUserIdentifier())
        elif zopeuser:
            path = '/'.join(zopeuser.getPhysicalPath())
            name = zopeuser.getUserName()
            acl_adder = ','.join([path, name])

        fromname = request.get('fromname','').strip()
        ckey = self.getCookiekey('name')
        if issueuser and issueuser.getFullname():
            fromname = issueuser.getFullname()
        #elif cmfuser and cmfuser.getProperty('fullname'):
        #    fromname = cmfuser.getProperty('fullname')
        elif not request.get('fromname') and self.has_cookie(ckey):
            fromname = self.get_cookie(ckey)
        elif request.get('fromname'):
            self.set_cookie(ckey, fromname)

        email = request.get('email','').strip()
        ckey = self.getCookiekey('email')
        if issueuser and issueuser.getEmail():
            email = issueuser.getEmail()
        #elif cmfuser and cmfuser.getProperty('email'):
        #    email = cmfuser.getProperty('email')
        elif not request.get('email') and self.has_cookie(ckey):
            email = self.get_cookie(ckey)
        elif request.get('email'):
            self.set_cookie(ckey, asciify(email, 'replace'))

        
        self._updateModifyDate()
        
        # Also upload the fileattachments
        self._moveTempfiles(self)

        # upload new file attachments
        if request.get('fileattachment', []):
            self._uploadFileattachments(self, request.get('fileattachment'))
            #followupobject.index_object(idxs=['filenames'])
        
        self.nullifyTempfolderREQUEST()
        
            
        #if self.SaveDrafts():
        #    # make sure there aren't any drafts that match
        #    # this recently added followupobject
        #    self._dropMatchingDraftThreads(followupobject)
        #    
        #    # in fact, drop all drafts in this issue
        #    self._cancelDraftThreads(autosaved_only=True)
            
            
        if request.get('notify-more-options'):
            email_addresses = request.get('notify_email')
            # check that they're all email address that are possible
            possible_email_addresses = self.Others2Notify(do='email',
                                                          emailtoskip=email)
            email_addresses = [x.strip() for x 
                               in email_addresses 
                               if x.strip() and x.strip() in possible_email_addresses]
            if email_addresses:
                self.sendFollowupNotifications(followupobject, 
                          email_addresses, gentitle,
                          status_change=action == 'add followup')
        
        elif request.has_key('notify'):
                    
            # now, create and email-alert-queue object
            # using filtered email address
            # get who to notify
            email_addresses = self.Others2Notify(do='email',
                                                 emailtoskip=email)

                                                 
            if email_addresses:
                self._sendPageChangeNotifications(change,
                          email_addresses, title)
                          
            
        # catalog
        self.unindex_object()
        self.index_object()
        
        
        
        
    def _sendFollowupNotifications(self, change, email_addresses,
                                  status_change=False):
                                      
        raise NotImplementedError
        prefix = self.issueprefix
        
        # create id for notification
        mtype = NOTIFICATION_META_TYPE
        notifyid = self.generateID(4, prefix+"notification",
                                   meta_type=mtype,
                                   use_stored_counter=0)

        title = self.title
        issueID = self.id
        anchorname = len(self.objectIds(ISSUETHREAD_METATYPE))
        emails = email_addresses
        date = DateTime()
        
        assert self.hasIssue(issueID), "This notification has no issue"
        
        if status_change:
            new_status = self.getStatus()
        else:
            new_status = ''


        notification_comment = followupobject.getCommentPure()
        notification = IssueTrackerNotification(
                            notifyid, title, issueID,
                            emails, 
                            followupobject.fromname,
                            comment=notification_comment, 
                            anchorname=anchorname, 
                            change=change,
                            new_status=new_status,
                            )
        self._setObject(notifyid, notification)
        notifyobject = getattr(self, notifyid)
          
        # use the dispatcher to try to send
        # this notification right now.
        # there is no big deal if the dispatcher crashes here
        # because the notification is saved and the dispatcher
        # can be invoked some other time manually
        if self.doDispatchOnSubmit():
            try:
                self.dispatcher()
            except:
                try:
                    err_log = self.error_log
                    err_log.raising(sys.exc_info())
                except:
                    pass
                LOG(self.__class__.__name__, PROBLEM,
                   'Email could not be sent', error=sys.exc_info())



    def getUserDetailsByACLAdder(self, acl_adder):
        """ return (name, email) of the user that is this acl user """
        ufpath, name = acl_adder.split(',')
        try:
            uf = self.unrestrictedTraverse(ufpath)
        except KeyError:
            try:
                uf = self.unrestrictedTraverse(ufpath.split('/')[-1])
            except KeyError:
                # the userfolder (as it was saved) no longer exists
                return {}

        if uf.meta_type == ISSUEUSERFOLDER_METATYPE:
            if uf.data.has_key(name):
                issueuserobj = uf.data[name]            
                return dict(fromname=issueuserobj.getFullname() or self.fromname,
                            email=issueuserobj.getEmail() or self.email)
                        
        elif CMF_getToolByName and hasattr(uf, 'portal_membership'):
            mtool = CMF_getToolByName(self, 'portal_membership')
            member = mtool.getMemberById(name)
            if member.getProperty('fullname'):
                return dict(fromname=member.getProperty('fullname'),
                            email=member.getProperty('email'))
                            
        return {}
    

    
    def getCameFromSearchURL(self):
        """ if the previous page was a search, return the URL back to the same """
        raise NotImplementedError, "This method has be deprecated"
    
        referer = self.REQUEST.get('HTTP_REFERER')
        if not referer:
            return None
        
        if referer.find(self.getRootURL()) == -1:
            return None
        
        if referer.find('?') > -1 and referer.split('?')[1].find('q') > -1:
            querystring = referer.split('?')[1]
            qs = cgi.parse_qs(querystring)
            if qs.has_key('q'):
                #q = qs.get('q')[0]
                return referer
                
                
        return None
        
    ## Changing the issue in mid-air

    
    def Others2Notify(self, format='email', emailtoskip=None, requireemail=False, 
                      do=None # legacy parameter
                      ):
        """
        Returns a list of names and emails of people to notify if this page
        changes
        
        if format == email:
            return [foo@bar.com, bar@foo.com,...]
        elif format == name:
            return [Foo, Bar, ...]
        elif format == both:
            return ['Foo <foo@bar.com>', ...]
        elif format == merged:
            return [self.ShowNameEmail(Foo, foo@bar.com),...]
        
        """
        raise NotImplementedError
    
        if emailtoskip is None:
            # caller was lazy not to specify this 
            # we do it here in the code
            issueuser = self.getIssueUser()
            if issueuser:
                emailtoskip = issueuser.getEmail()
            elif self.REQUEST.get('email'):
                emailtoskip = self.REQUEST.get('email')
            elif self.has_cookie(self.getCookiekey('email')):
                emailtoskip = self.get_cookie(self.getCookiekey('email'))

        all = []
        nameemailshower = lambda n,e: self.ShowNameEmail(n, e, highlight=0)
        
        names_and_emails = self._getOthers(emailtoskip)
        for _name, _email in names_and_emails:
            add = ''
            if emailtoskip is not None and ss(_email) == ss(emailtoskip):
                continue # skip it!
            
            if requireemail and not Utils.ValidEmailAddress(_email):
                continue # skip it!
            
            if format == 'tuple':
                add = (_email, nameemailshower(_name and _name or _email, _email))
            elif format == 'email':
                add = _email or _name
            elif format == 'name':
                add = _name or _email
            else:
                if _name and _email:
                    if format == 'both':
                        add = "%s <%s>"%(_name, _email)
                    else:
                        add = nameemailshower(_name, _email)
                elif _name:
                    if format == 'both':
                        add = _name
                    else:
                        add = _name
                elif _email:
                    if format == 'both':
                        add = _email
                    else:
                        add = nameemailshower(_email, _email)
            if add and add not in all:
                all.append(add)
            
        return all
                        

    def _getOthers(self, avoidemail=None):
        """ return a 2D list of names and emails that _should_ be notified """
        all = []        # what we will return
        allemails = {}  # avoid duplicates

        # 1. The issue at hand.
        # proceed only if Manager or open-name on the issue
        if self.hasManagerRole() or not self.hide_me:
            # self.email is the email of the thread
            # emailtoskip comes from the param/cookie if applicable
            issue_email = self.getEmail()
            if issue_email and issue_email != avoidemail:
                issue_fromname = self.getFromname()
                item = [issue_fromname, issue_email]
                all.append(item)
                allemails[ss(issue_email)] = 1

        # 2. All authors of followups/threads
        for thread in self.objectValues(ISSUETHREAD_METATYPE):
            thread_email = thread.getEmail()
            if thread_email and thread_email != avoidemail:
                ss_thread_email = ss(thread_email)
                if not allemails.has_key(ss_thread_email):
                    thread_fromname = thread.getFromname()
                    item = [thread_fromname, thread_email]
                    all.append(item)
                    allemails[ss_thread_email] = 1
                    

        # 3. Get all subscribers
        notifyables = self.getNotifyablesEmailName()
        for subscriber in self.getSubscribers():

            if notifyables.has_key(subscriber):
                #       Name                     Email
                item = [notifyables[subscriber], subscriber]
                ss_subscriber = ss(subscriber)
                if not allemails.has_key(ss_subscriber):
                    all.append(item)
                    allemails[ss_subscriber] = 1

            elif len(subscriber.split(','))==2: 
                # quite possibly an acl user
                ufpath, name = subscriber.split(',')
                try:
                    uf = self.unrestrictedTraverse(ufpath)
                except KeyError:
                    continue
                if uf.meta_type == ISSUEUSERFOLDER_METATYPE:
                    issueuserobj = uf.data[name]
                    ss_email = ss(issueuserobj.getEmail())
                    if not allemails.has_key(ss_email):
                        item = [issueuserobj.getFullname(),
                                issueuserobj.getEmail()]
                        all.append(item)
                        allemails[ss_email] = 1
                    
                
            elif Utils.ValidEmailAddress(subscriber):
                ss_subscriber = ss(subscriber)
                if not allemails.has_key(ss_subscriber):
                    all.append(['', subscriber])
                    allemails[ss_subscriber] = 1
                
        
        del allemails
        return all

        
    def countFileattachments(self):
        """ return [no files in issue, no files in threads] """
        raise NotImplementedError
        return len(self.ZopeFind(self, obj_metatypes=['File'], search_sub=1))
    
    def filenames(self):
        """ return all the filenames of this issue splitted """
        files = self.objectValues('File')
        all = []
        for file in files:
            all.extend(Utils.filenameSplitter(file.getId()))
        return Utils.uniqify([x.lower() for x in all])
        
        
    def manage_beforeDelete(self, REQUEST=None, RESPONSE=None):
        """ uncatalog yourself """
        self.unindex_object()

    def index_object(self, idxs=None):
        """A common method to allow Findables to index themselves."""
        path = '/'.join(self.getPhysicalPath())
        catalog = self.getCatalog()
        
        if idxs is None:
            # because I don't want to put mutable defaults in 
            # the keyword arguments
            idxs = ['id','title','body', 'meta_type','path','modifydate',
                    'filenames','pagedate']
        else:
            # No matter what, when indexing you must always include 'path'
            # otherwise you might update indexes without putting the object
            # brain in the catalog. If that happens the object won't be 
            # findable in the searchResults(path='/some/path') even if it's
            # findable on other indexes such as comment.
            
            if 'path' not in idxs:
                idxs.append('path')
        
        indexes = catalog._catalog.indexes
        
        catalog.catalog_object(self, path, idxs=idxs)
 
    def getTitle_idx(self):
        return self.getTitle()
    
    def getBody_idx(self):
        return self.getBodyPure()

    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        path = '/'.join(self.getPhysicalPath())
        self.getCatalog().uncatalog_object(path)
        
    def isImplicitlySubscribing(self, email):
        """ return if they're already involved in this issue such that there is
        no point for them becoming a subscriber """
        raise NotImplementedError
        
        # was it you who added this issue?
        issue_email = self.getEmail()
        if email and issue_email == email:
            return True
        
        # have you made any kind of followup?
        for thread in self.ListThreads():
            if email and thread.getEmail() == email:
                return True            
        
        return False # fallback
    
    def isSubscribing(self, email):
        """ check if in subscribers list """
        raise NotImplementedError
        subscribers = self.getSubscribers()
        email = ss(str(email))
        return email in [ss(x) for x in subscribers]
    
    def getSubscribers(self):
        """ return subscribers list """
        return self.subscribers
    
    def _addSubscriber(self, name_or_email):
        """ add subscriber to subscribers list """
        subscribers = self.getSubscribers()
        email = None
        name_or_email = name_or_email.strip()
        
        if Utils.ValidEmailAddress(name_or_email):
            email = name_or_email
        elif len(name_or_email.split(','))==2:
            # it's a acl user
            email = name_or_email
        else:
            # what we're adding is not an email,
            # expect it to be the name of a notifyable
            ss_name_or_email = ss(name_or_email)
            for notifyable in self.getNotifyables():
                if ss_name_or_email == ss(notifyable.getName()):
                    email = notifyable.getEmail()
                    break

        if email is not None:
            if not self.isSubscribing(email):
                if isinstance(subscribers, tuple):
                    subscribers = list(subscribers)
                subscribers.append(email)
                
                self.subscribers = subscribers
                return True
            
        return False
            
    def _delSubscriber(self, email):
        """ remove item from subscribers list """
        n_subscribers = []
        ss_email = ss(email)
        for subscriber in self.getSubscribers():
            if ss_email != ss(subscriber):
                n_subscribers.append(subscriber)
        self.subscribers = n_subscribers
            
    def Subscribe(self, subscriber, unsubscribe=0, REQUEST=None):
        """ analyse subscriber and add accordingly """
        
        if subscriber == 'issueuser':
            issueuser = self.getIssueUser()
            assert issueuser, "Not logged in as Issue User"
            identifier = issueuser.getIssueUserIdentifierString()
            if unsubscribe:
                self._delSubscriber(identifier)
            else:
                self._addSubscriber(identifier)
        else:
            
            emails = self.preParseEmailString(subscriber, aslist=1)
            for email in emails:
                if unsubscribe:
                    self._delSubscriber(email)
                else:
                    self._addSubscriber(email)
                    
            # Exceptional case. If the user doesn't already have an email
            # address, but has asked to subscribe with only one email 
            # address, then we can assume that that is the email address he wants
            # to use all the time.
            if not self.getSavedUser('email') and len(emails)==1:
                if Utils.ValidEmailAddress(emails[0]):
                    # add this 
                    self.set_cookie(self.getCookiekey('email'), emails[0])
                
                
        if REQUEST is not None:
            url = self.absolute_url() + '/'
            REQUEST.RESPONSE.redirect(url)


                       
    ##
    ## The page's notifications
    ##
    
                       
    def getCreatedNotifications(self, sort=False):
        objects = list(self._getCreatedNotifications())
        if sort:
            objects.sort(lambda x, y: cmp(x.date, y.date))
        return objects
    
    def _getCreatedNotifications(self):
        return self.objectValues(NOTIFICATION_META_TYPE)
    
    ##
    ## Misc.
    ##
    
    ##
    ## Notes
    ##
    
    def getNotes(self):
        """return all note objects"""
        return self.objectValues(ISSUENOTE_METATYPE)
    
    def getYourNotes(self, threadID=None):
        raise NotImplementedError
        # first figure out if there are any notes in the issue
        # before we figure out who we can and search for them
        # properly.
        # The reason for this is that
        any_notes = False
        for __ in self.findNotes(threadID=threadID):
            any_notes = True
            break
        
        note_objects = []
        
        # before we fetch all private notes, just check that there are any
        # before we start the expensive operation of figuring out your
        # identifier and doing the search
        if any_notes:
            acl_adder = ''
            issueuser = self.getIssueUser()
            cmfuser = self.getCMFUser()
            zopeuser = self.getZopeUser()
            if issueuser:
                acl_adder = ','.join(issueuser.getIssueUserIdentifier())
            elif zopeuser:
                path = '/'.join(zopeuser.getPhysicalPath())
                name = zopeuser.getUserName()
                acl_adder = ','.join([path, name])
    
            ckey = self.getCookiekey('name')
            if issueuser and issueuser.getFullname():
                fromname = issueuser.getFullname()
            elif cmfuser and cmfuser.getProperty('fullname'):
                fromname = cmfuser.getProperty('fullname')
            elif self.has_cookie(ckey):
                fromname = self.get_cookie(ckey)
            else:
                fromname = ''
    
            ckey = self.getCookiekey('email')
            if issueuser and issueuser.getEmail():
                email = issueuser.getEmail()
            elif cmfuser and cmfuser.getProperty('email'):
                email = cmfuser.getProperty('email')
            elif self.has_cookie(ckey):
                email = self.get_cookie(ckey)
            else:
                email = ''
            
            if acl_adder:
                note_objects += list(self.findNotes(acl_adder=acl_adder,
                                                    threadID=threadID))
            elif email and fromname:
                note_objects += list(self.findNotes(fromname=fromname,
                                                    email=email,
                                                    threadID=threadID))
        
        note_objects.sort(lambda x,y: cmp(x.notedate, y.notedate))
        
        return note_objects
        
    

    security.declareProtected('View', 'createNote')
    def createNote(self, comment, public=False, block_id='',
                   REQUEST=None):
        """create a note via the web"""
        raise NotImplementedError
    
        acl_adder = ''
        issueuser = self.getIssueUser()
        cmfuser = self.getCMFUser()
        zopeuser = self.getZopeUser()
        if issueuser:
            acl_adder = ','.join(issueuser.getIssueUserIdentifier())
        elif zopeuser:
            path = '/'.join(zopeuser.getPhysicalPath())
            name = zopeuser.getUserName()
            acl_adder = ','.join([path, name])

        ckey = self.getCookiekey('name')
        if issueuser and issueuser.getFullname():
            fromname = issueuser.getFullname()
        elif cmfuser and cmfuser.getProperty('fullname'):
            fromname = cmfuser.getProperty('fullname')
        elif self.has_cookie(ckey):
            fromname = self.get_cookie(ckey)
        else:
            fromname = ''

        ckey = self.getCookiekey('email')
        if issueuser and issueuser.getEmail():
            email = issueuser.getEmail()
        elif cmfuser and cmfuser.getProperty('email'):
            email = cmfuser.getProperty('email')
        elif self.has_cookie(ckey):
            email = self.get_cookie(ckey)
        else:
            email = ''

        saved_display_format = self.getSavedTextFormat()
        if saved_display_format:
            display_format = saved_display_format
        else:
            display_format = self.getDefaultDisplayFormat()
            
        
        try:
            note = self._createNote(comment, fromname=fromname, email=email,
                                      acl_adder=acl_adder,
                                      public=public, display_format=display_format,
                                      threadID=threadID)
        except ValueError, msg:
            if REQUEST is not None:
                return "Error: %s" % str(msg)
            else:
                raise
            
        if REQUEST is not None:
            redirect_url = self.absolute_url()
            request.RESPONSE.redirect(redirect_url)
        else:
            return note
            
        
    def _createNote(self, comment, fromname=None, email=None, acl_adder=None,
                    public=False, display_format='', block_id='',
                    REQUEST=None):
        
        # the comment can not be blank
        if not comment:
            raise IssueNoteError("Note comment can not be empty")
        
        if threadID:
            try:
                thread = getattr(self, threadID)
            except AttributeError:
                raise ValueError("thread does not exist")
        
                
        # test if the comment doesn't already exist
        for note in self.findNotes(comment=comment,
                                    fromname=fromname, email=email,
                                    acl_adder=acl_adder,
                                    threadID=threadID):
            # already created
            # perhaps user doubleclick the submit button
            return note
            
        randomid_length = self.randomid_length
        if randomid_length > 3:
            randomid_length = 3
        genid = self.generateID(randomid_length,
                                prefix=self.issueprefix + 'note',
                                meta_type=ISSUENOTE_METATYPE,
                                use_stored_counter=False)
        
        from Products.IssueTrackerProduct.Note import IssueNote
        # create a note inside this issue
        note = IssueNote(genid, title, comment, fromname, email,
                         display_format=display_format,
                         acl_adder=acl_adder, threadID=threadID
                         )
        self._setObject(genid, note)
        note = self._getOb(genid)
        note.index_object()
        
        return note
        
    def findNotes(self, comment=None, fromname=None, email=None,
                  acl_adder=None, threadID=None):
        
        for note in self.getNotes():
            if comment is not None:
                if note.getComment() != comment:
                    continue
            if fromname is not None:
                if note.fromname != fromname:
                    continue
            if email is not None:
                if note.email != email:
                    continue
            if threadID is not None:
                if note.threadID != threadID:
                    continue
            yield note
            
                                    

zpts = ('zpt/Pages/ShowPage',
        'zpt/Pages/edit_template',
        )

        
addTemplates2Class(Page, zpts, extension='zpt')

InitializeClass(Page)

    

#----------------------------------------------------------------------------

VALID_CHANGES = ('add','edit','delete')


class PageChange(SimpleItem, Persistent):
    
    meta_type = PAGE_CHANGE_METATYPE
     
    def __init__(self, id, fromname, email, acl_adder='',
                 blocks=None, change='add', change_html=None):
                     
        self.id = str(id)
        self.fromname = unicodify(fromname)
        self.email = asciify(email)
        self.acl_adder = acl_adder
        
        if blocks is None:
            blocks = []
        self.blocks = blocks
        if change not in VALID_CHANGES:
            raise ValueError("Invalid change value %r" % change)
        self.change = change
        if isinstance(change_html, str):
            change_html = unicodify(change_html)
        self.change_html = change_html
                  
     

