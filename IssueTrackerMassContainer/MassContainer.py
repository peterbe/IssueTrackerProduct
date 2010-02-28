# IssueTrackerMassContainer
#
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

__doc__="""IssueTrackerMassContainer is a folderish container
for Zope where you have multiple instances of the IssueTrackerProduct
By Peter Bengtsson <mail@peterbe.com>

Credits:
"""


# python
import os, sys
from urlparse import urlparse, urlunparse
import logging
from time import time

# zope
from Products.PageTemplates.PageTemplateFile import PageTemplateFile as PTF
from Globals import Persistent, InitializeClass, package_home, DTMLFile
from Products.PythonScripts.standard import html_quote, url_quote_plus
from OFS import Folder
from DocumentTemplate import sequence
from AccessControl import ClassSecurityInfo
from DateTime import DateTime
from Products.PythonScripts.PythonScript import PythonScript
from Products.PythonScripts.standard import url_quote
from zLOG import LOG, INFO

from Products.IssueTrackerProduct.Constants import ISSUE_METATYPE

# product
from Constants import *
import Utils
from Utils import cookIdAndTitle

from RecentActivity import getRecentActivity

try:
    from Products.IssueTrackerUtils import _replace_special_chars
except:
    _replace_special_chars = None
    
    
__version__=open(os.path.join(package_home(globals()), 'version.txt')).read().strip()    


def logger_info(s, detail=''):
    LOG('IssueTrackerMassContainer', INFO, s, detail=detail)

    
COOKIEKEY_SKIPPABLE_PATHS = '__itmc_skippable_paths'    
#----------------------------------------------------------------------------

manage_addMassContainerForm = PTF('zpt/addMassContainerForm', globals())


def manage_addMassContainer(dispatcher, oid, title='',
                           REQUEST=None):
    """ add IssueTrackerMassContainer instance via the web """
    dest = dispatcher.Destination()
    masscontainer = MassContainer(oid, title)
    dest._setObject(oid, masscontainer)
    self = dest._getOb(oid)
    
    self.DeployMassStandards()

    if REQUEST is not None:
        # whereto next?
        if REQUEST.has_key('addandedit'):
            REQUEST.RESPONSE.redirect(self.absolute_url()+'/manage_workspace')
        elif REQUEST.has_key('DestinationURL'):
            REQUEST.RESPONSE.redirect(REQUEST.DestinationURL+'/manage_workspace')
        else:
            REQUEST.RESPONSE.redirect(REQUEST.URL1+'/manage_workspace')

class MassContainer(Folder.Folder, Persistent):
    """ MassContainer class """
    
    meta_type = MASSCONTAINER_METATYPE

    _properties=({'id':'title',            'type': 'string', 'mode':'w'},
                 )

    security = ClassSecurityInfo()
    
    manage_options = Folder.Folder.manage_options[:3] + \
        ({'label':'Deploy Standards', 'action':'manage_DeployStandards'},) \
        + Folder.Folder.manage_options[3:]    

    def __init__(self, oid, title=''):
        """ Init MassContainer class """
        self.id = str(oid)
        self.title = str(title)
       
    def getRoot(self):
        """ return self class """
        return self
    
    def getRootURL(self):
        """ return self's absolute_url() """
        return self.getRoot().absolute_url()

    def manage_DeployStandards(self):
        """ tab entry to DeployMassStandards """
        durl = self.getRootURL()+'/manage_workspace'
        return self.DeployMassStandards(remove_oldstuff=1, DestinationURL=durl)
        
        
    def DeployMassStandards(self, remove_oldstuff=0, DestinationURL=None):
        """ copy images and other documents into the instance unless they
            are already there
        """
        t={}
        
        # create folders
        root = self.getRoot()
        rootbase = getattr(root, 'aq_base', root)

        osj = os.path.join
        standards_home = osj(package_home(globals()),'standards')
        t = self._deployImages(root, standards_home,
                               t=t, remove_oldstuff=remove_oldstuff)

        #www_home = osj(standards_home,'www')
        #t = self._deployImages(root.www, www_home,
                               #t=t, remove_oldstuff=remove_oldstuff)

        # shortcut
        addPG = root.manage_addProduct['PageTemplates'].manage_addPageTemplate
        AddParam2URL = Utils.AddParam2URL
        
        for filestr in os.listdir(standards_home):
            if filestr[-5:] == '.dtml':
                id, title = cookIdAndTitle(filestr.replace('.dtml',''))
                if hasattr(rootbase, id) and remove_oldstuff:
                    root.manage_delObjects([id])
                
                if not hasattr(rootbase, id):
                    file = DTMLFile('standards/%s'%filestr.replace('.dtml',''), globals()).read()
                    root.manage_addDTMLDocument(id, title, file=file)
                    t[id] ="DTML Document"
            elif filestr[-4:] == '.zpt':
                id, title = cookIdAndTitle(filestr.replace('.zpt',''))
                if hasattr(rootbase, id) and remove_oldstuff:
                    root.manage_delObjects([id])
                    
                if not hasattr(rootbase, id):
                    file = open(osj(standards_home,filestr)).read()
                    addPG(id, title=title, text=file)
                    t[id]="Page Template"                    
            elif filestr[-3:] == '.py':
                id, title = cookIdAndTitle(filestr.replace('.py',''))
                if hasattr(rootbase, id) and remove_oldstuff:
                    root.manage_delObjects([id])
                    
                if not hasattr(rootbase, id):
                    file = open(osj(standards_home, filestr)).read()
                    id = root._setObject(id, PythonScript(id))
                    root._getOb(id).write(file)
                    t[id]="Script (Python)"

        if DestinationURL:
            msg = ''
            for k,v in t.items():
                msg = "%s (%s)\n%s"%(k,v,msg)
            
            url = AddParam2URL(DestinationURL,{'manage_tabs_message':\
                                "Standard objects deployed\n\n%s"%msg})
            self.REQUEST.RESPONSE.redirect(url)
        else:
            return "Standard objects deployed\n%s"%t

    def _deployImages(self, destination, dir, extensions=['.gif','.ico'], t={},
                      remove_oldstuff=0):
        """ do the actual deployment of images in a dir """
        # shortcuts
        osj = os.path.join
        
        for filestr in os.listdir(dir):
            if self._file_has_extensions(filestr, extensions):
                # take the image
                id, title = cookIdAndTitle(filestr)
                base= getattr(destination,'aq_base',destination)
                if hasattr(base, id) and remove_oldstuff:
                    destination.manage_delObjects([id])
                    
                if not hasattr(base, id):
                    destination.manage_addImage(id, title=title, \
                          file=open(osj(dir, filestr),'rb').read())
                    t[id]="Image"
        return t
    
    def _file_has_extensions(self, filestr, extensions):
        """ check if a filestr has any of the give extensions """
        for extension in extensions:
            if filestr.find(extension) > -1:
                return True
        return False
    
    def getHeader(self):               
        """ Return which METAL header&footer to use """
        # Since we might be using CheckoutableTemplates and macro
        # templates are very special we are forced to do the following
        # magic to get the macro 'standard' from a potentially checked
        # out StandardHeader
        zodb_id = 'StandardHeader.zpt'
        template = getattr(self, zodb_id, self.StandardHeader)
        return template.macros['standard']
    
    
    def getTrackersAndMassContainers(self, in_object=None, sort=False):
        """ return a or iterable of all issuetrackers and mass containers """
        if in_object is None:
            in_object = self.getRoot()
        objs = in_object.objectValues(['Issue Tracker','Issue Tracker Mass Container'])
        if sort:
            objs.sort(lambda x, y: cmp(x.title_or_id().lower(), y.title_or_id().lower()))
        return objs
    
        
    def getRecentIssues(self, since=None, recursive=True, batch_size=20, batch_start=0,
                        by_add_date=False):
        """ return a list of all the most recent issues """
        skippable_paths = self.getSkippablePaths()
        root = self.getRoot()
        
        if getattr(self, '_v_skippable_paths', None):
            skippable_paths.extend(self._v_skippable_paths)
            
        elif getattr(self, '_v_oldest_timestamp', since):
            # cool, we can use this to make sure we're not going to sort issues from
            # trackers that are older than this
            older_than = since and float(since) or self._v_oldest_timestamp
            paths = self._getOlderIssueTrackerPaths(root, DateTime(older_than))
            self._v_skippable_paths = paths
            skippable_paths.extend(paths)
            
        issues = self._getAllIssues(root, skippable_paths)
        
        if by_add_date:
            issues = [(float(x.getIssueDate()), 
                       '/'.join(x.getPhysicalPath())) 
                      for x in issues]            
        else:
            issues = [(float(x.getModifyDate()), 
                       '/'.join(x.getPhysicalPath())) 
                      for x in issues]
        if since is not None:
            if hasattr(since, 'strftime'):
                since = float(since)
            else:
                if type(since) is int:
                    since = float(since)
                elif isinstance(since, basestring):
                    if since.isdigit():
                        since = float(int(since))
                    elif since.replace('.','').isdigit():
                        since = float(since)
                    else:
                        since = float(DateTime(since))
            issues = [(t,i) for (t,i) in issues
                      if t > since]
            
        issues.sort()
        issues.reverse()
        
        # Let's now take the opportunity to remember the timestamp of the
        # oldest one of these so that the next time this page is requested
        # at least it won't do anything deeper than this.
        if since is None and not skippable_paths:
            # very first time!
            self._v_oldest_timestamp = issues[int(batch_size)+int(batch_start)][0]
        
        # cut off
        issue_paths = [x[1] for x in issues[int(batch_start):int(batch_size)+int(batch_start)]]
        return [root.unrestrictedTraverse(p) for p in issue_paths]
    
    def _getOlderIssueTrackerPaths(self, in_object, older_than):
        assert hasattr(older_than, 'strftime'), "older_than must be a DateTime instance"
        paths = []
        root_url = self.getRoot().absolute_url()
        for o in in_object.objectValues([MASSCONTAINER_METATYPE, 'Issue Tracker']):
            if o.meta_type == MASSCONTAINER_METATYPE:
                paths.extend(self._getOlderIssueTrackerPaths(o, older_than))
            elif o.meta_type == 'Issue Tracker':
                # the "age" of the tracker is the modify date of the youngest issue
                # fish that out
                mod_dates = [x.getModifyDate()
                             for x in o._getIssueContainer().objectValues(ISSUE_METATYPE)]
                mod_dates.sort()
                mod_dates.reverse()
                try:
                    most_recent = mod_dates[0]
                except IndexError:
                    # doesn't have any issues, then definitely skip this one
                    paths.append(o.absolute_url().replace(root_url, ''))
                    continue
                
                if most_recent < older_than:
                    paths.append(o.absolute_url().replace(root_url, ''))
                    continue
                
        return paths

    def _getAllIssues(self, in_object, skippable_paths):
        issues = []
        root_url = self.getRoot().absolute_url()
        for o in in_object.objectValues([MASSCONTAINER_METATYPE, 'Issue Tracker']):
            path = o.absolute_url().replace(root_url,'')
            if path in skippable_paths:
                continue
            
            if o.meta_type == MASSCONTAINER_METATYPE:
                issues.extend(self._getAllIssues(o, skippable_paths))
            elif o.meta_type == 'Issue Tracker':
                issues.extend(list(o._getIssueContainer().objectValues(ISSUE_METATYPE)))
                
        return issues



    def show_tree(self, context, REQUEST, in_object):
        """ wrapper on rendering the tree in a template for optimization reasons """
        try:
            cache = self._v_show_tree_cache
        except AttributeError:
            cache = {}
        
        try:
            timestamp, tree_rendered = cache[in_object.absolute_url_path()]
            if (DateTime() - timestamp) > (0.5/24.0):
                tree_rendered = None
        except KeyError:
            tree_rendered = None
        
        if tree_rendered is None:
            tree_rendered = self.show_tree_template(context, REQUEST, in_object=in_object)
            cache[in_object.absolute_url_path()] = (DateTime(), tree_rendered)
            self._v_show_tree_cache = cache
            
        return tree_rendered

    # some templates
    security.declareProtected('View', 'index_html')
    index_html = PTF('zpt/index_html', globals())
    show_tree_template = PTF('zpt/show_tree_template', globals())
    show_activity_table = PTF('zpt/show_activity_table', globals())
    show_recent_activity_tbodies = PTF('zpt/show_recent_activity_tbodies', globals())
    activity_macros = PTF('zpt/activity_macros', globals())
    StandardHeader = PTF('zpt/StandardHeader', globals())
    masscontainer_style_css = DTMLFile('dtml/masscontainer_style.css', globals())

    def RSS091(self, batchsize=None, withheaders=1):
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
        <webMaster></webMaster>\n"""%\
           (root.title, root.absolute_url(), root.title)
        #logo = getattr(self, 'issuetracker_logo.gif')
        #header=header+"""<image>
        #<title>%s</title>
        #<url>%s</url>
        #<link>%s</link>
        #<width>%s</width>
        #<height>%s</height>
        #<description>%s</description>
        #</image>\n"""%(logo.title, logo.absolute_url().strip(),
                       #root.absolute_url(),
                       #logo.width, logo.height,
                       #root.title)
        # manually set sortorder
        request.set('sortorder','date')
        request.set('reverse',1)
        xml=''
        if batchsize is None:
            batchsize = 10
        for issue in self.getRecentIssues(batch_size=batchsize, by_add_date=True):
            title = "%s (%s)"%(issue.title, issue.status.capitalize()) 
            title = self._prepare_feed(title)
            description = self._prepare_feed(issue.description)

            xml=xml+"""\n\t<item>
            <title>%s</title>
            <description>%s</description>
            <link>%s</link>
            """%(title, description, issue.absolute_url())
            if issue.fromname != '':
                author = "%s (%s)"%(issue.fromname, issue.email)
                xml="%s\n<author>%s</author>\n"%(xml, author)
            xml=xml+"\n\t</item>"
            
        footer="""</channel></rss>>"""
        if withheaders:
            xml = header+xml+footer
            
        response = request.RESPONSE
        response.setHeader('Content-Type', 'text/xml')
        return xml
    
    def _prepare_feed(self, s):
        """ prepare the text for XML usage """
        _replace = _replace_special_chars
        s = html_quote(s)
        return s
        s = s.replace('\xa3','&#163;')
        if _replace is not None:
            s = _replace(s, html_encoding=1)
        s = s.replace('&','&amp;')
        return s
    
    def findCorrectURL(self):
        """ return the correct URL with the correct spelling.
        This is useful from 404 error handling where people have
        been lazy with the case sensitivity.
        """
        _request_stack = self.REQUEST.TraversalRequestNameStack[:]
        _request_stack.reverse()
        badurl = self.REQUEST.URL + '/' + '/'.join(_request_stack)

        good_start = self.absolute_url()
        good_start_parsed = urlparse(good_start)
        
        url_parsed = urlparse(badurl)
        
        if good_start_parsed[1].lower() == url_parsed[1].lower():
            # same domain name at least
            try:
                correct, wrong = self._getIssueTrackerId(url_parsed)
            except:
                typ, val, tb = sys.exc_info()
                print typ
                print val
            if correct:
                url_parsed = list(url_parsed)
                try:
                    url_parsed[2] = url_parsed[2].replace(wrong, correct)
                except:
                    typ, val, tb = sys.exc_info()
                    print typ
                    print val
                #url_parsed
                
                # check the rest
                path = url_parsed[2].split('/')
                while path:
                    try:
                        object = self.unrestrictedTraverse('/'.join(path))
                        break
                    except:
                        # reduce the path
                        path = path[:-1]
                        if not path:
                            return None
                url_parsed[2] = '/'.join(path)
                goodurl =urlunparse(url_parsed)
                return goodurl        
        
        # if it fails
        return None
    
    def _getIssueTrackerId(self, parsed_badurl):
        """ find out the correct id of the issuetracker """
        try:
            id_requested_alts = parsed_badurl[2].split('/')
        except IndexError:
            return None, None
        
        id_alts = [x.strip().lower() for x in id_requested_alts]
        for id_correct in self.objectIds('Issue Tracker'):
            for id_alt in id_alts:
                if id_alt == id_correct.lower():
                    return id_correct, id_alt            
        return None, None
    
    ##
    ## Some features copied from the IssueTrackerProduct
    ##
    
    def getRootRelativeURL(self):
        """ quick wrapper around getRoot() """
        return self.getRoot().relative_url()

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
    
    def StopCache(self):
        """ Maybe we should set some cachepreventing headers """
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


    ##
    ## Ignored/skipped issuetrackers
    ##
    
    def ignoreIssueTracker(self, path, REQUEST=None):
        """ add this to the cookie """
        # if path == '/Image Test' convert it to '/Image Test'
        path = url_quote(path)
        paths = self.getSkippablePaths()
        if path in paths:
            paths.remove(path)

        paths.insert(0, path)
        self._saveSkippablePaths(paths)
        
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect(self.getRootURL())
            
    def ignoreMassContainer(self, path, REQUEST=None):
        """ add this to the cookie """
        return self.ignoreIssueTracker(path, REQUEST=REQUEST)
    
    def undoIgnoreIssueTracker(self, path, REQUEST=None):
        """ remove this from the cookie """
        paths = self.getSkippablePaths()
        if path in paths:
            paths.remove(path)
            
        self._saveSkippablePaths(paths)
        
        if REQUEST is not None:
            REQUEST.RESPONSE.redirect(self.getRootURL())

    def undoIgnoreMassContainer(self, path, REQUEST=None):
        """ remove this from the cookie """
        return self.undoIgnoreIssueTracker(path, REQUEST=REQUEST)
    
    def _saveSkippablePaths(self, paths):
        """ save the list to a cookie """
        assert isinstance(paths, list)
        value = '|'.join(paths)
        key = COOKIEKEY_SKIPPABLE_PATHS
        then = DateTime()+300
        then = then.rfc822()
        self.REQUEST.RESPONSE.setCookie(key, value, path='/',
                                        expires=then)
        
    
    def getSkippablePaths(self):
        """ return a list of paths to issuetrackers and other mass containers
        that the user is not interested in. 
        """
        r = self.REQUEST.cookies.get(COOKIEKEY_SKIPPABLE_PATHS,'')
        if r:
            return r.split('|')
        else:
            return []

    ##
    ## Misc
    ##
    
    def title_id_different(self, title, oid):
        """ return true if the title is very different from the oid.
        If the title is 'Peter Bengtsson' and the id is 'peter-bengtsson'
        it's not sufficiently different.
        """
        title = title.lower().replace(' ','-')
        return title != oid.lower()
    
    
    ##
    ## Experimental Recent Activity
    ##
    
    security.declareProtected('View', 'RecentActivity')
    def RecentActivity(self, since=None):
        """ return the HTML body of the recent activity """
        res = getRecentActivity(self, since=since)
        res = '\n'.join(res)
        return "<html><body>%s</body></html>" % html_quote(res).replace('\n','<br/>\n')
    
        
    
setattr(MassContainer, 'masscontainer_style.css', MassContainer.masscontainer_style_css)
setattr(MassContainer, 'rss.xml', MassContainer.RSS091)
setattr(MassContainer, 'UNICODE_ENCODING', UNICODE_ENCODING)
    
