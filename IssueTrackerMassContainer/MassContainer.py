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

# product
from Constants import *
import Utils
from Utils import cookIdAndTitle

try:
    from Products.IssueTrackerUtils import _replace_special_chars
except:
    _replace_special_chars = None
    
    
__version__=open(os.path.join(package_home(globals()), 'version.txt')).read().strip()    


def logger_info(s, detail=''):
    LOG('IssueTrackerMassContainer', INFO, s, detail=detail)
    
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
    
        
    
    def getRecentIssues(self, recursive=True, batch_size=20, batch_start=0):
        """ return a list of all the most recent issues """
        skippable_paths = self.getSkippablePaths()
        
        issues = self._getAllIssues(self.getRoot(), skippable_paths)
        
        # sort them all
        issues.sort(lambda x,y: cmp(y.getModifyDate(), x.getModifyDate()))
        
        # cut off
        issues = issues[int(batch_start):int(batch_size)]
        
        return issues
    

    def _getAllIssues(self, in_object, skippable_paths):
        issues = []
        root_url = self.getRoot().absolute_url()
        for o in in_object.objectValues([MASSCONTAINER_METATYPE,'Issue Tracker']):
            path = o.absolute_url().replace(root_url,'')
            if o.absolute_url().find('wolvespct') > -1:
                logger_info("path=%r, skippable_paths=%s in? %s"%(path, str(skippable_paths), path in skippable_paths))
            if path in skippable_paths:
                continue
            
            if o.meta_type == MASSCONTAINER_METATYPE:
                issues.extend(self._getAllIssues(o, skippable_paths))
            elif o.meta_type == 'Issue Tracker':
                issues.extend(o.getIssueObjects())
                
        return issues
        

    # some templates
    #security.declareProtected('View', 'AllrecentIssues')
    #AllrecentIssues = DTMLFile('dtml/AllrecentIssues', globals())
    #trackersOfInterestForm = DTMLFile('dtml/trackersOfInterestForm', globals())

    security.declareProtected('View', 'index_html')
    index_html = PTF('zpt/index_html', globals())
    show_tree = PTF('zpt/show_tree', globals())
    show_activity_table = PTF('zpt/show_activity_table', globals())
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
        for issue in self.getAllRecentIssues()[:batchsize]:
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
        key = '__masscontainer_skippable_paths'
        then = DateTime()+300
        then = then.rfc822()
        logger_info("Setting this cookie %r" % value)
        self.REQUEST.RESPONSE.setCookie(key, value, path='/', 
                                        expires=then)
        
    
    def getSkippablePaths(self):
        """ return a list of paths to issuetrackers and other mass containers
        that the user is not interested in. 
        """
        r = self.REQUEST.cookies.get('__masscontainer_skippable_paths','')
        logger_info("r=%r" % r)
        logger_info(str(self.REQUEST.cookies.items()))
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
        
    
setattr(MassContainer, 'masscontainer_style.css', MassContainer.masscontainer_style_css)
setattr(MassContainer, 'rss.xml', MassContainer.RSS091)
setattr(MassContainer, 'UNICODE_ENCODING', UNICODE_ENCODING)
    
