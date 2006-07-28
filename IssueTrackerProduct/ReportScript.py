# IssueTrackerProduct
#
# www.issuetrackerproduct.com
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

# python
from urllib import quote
import urllib2

try:
    import timeoutsocket
    # set a timeout for TCP connections
    timeoutsocket.setDefaultSocketTimeout(60)
except ImportError:
    timeoutsocket = None
    

# zope
from Globals import DTMLFile, InitializeClass, package_home
from Products.PythonScripts.PythonScript import PythonScript
from AccessControl import ClassSecurityInfo
from Acquisition import aq_inner, aq_parent
from DateTime import DateTime
from zLOG import LOG, INFO

from Shared.DC.Scripts.Script import defaultBindings # Script, BindingsUI,

from Constants import *
from Permissions import VMS
import Utils

#-------------------------------------------------------------------------------

manage_addIssueReportScriptForm = DTMLFile('dtml/addReportScript', globals())

_default_file = os.path.join(package_home(globals()),
                             'www', 'default_report_script.py')
                        
def _suck_url(url):
    return urllib2.urlopen(url).read()
        
def manage_addIssueReportScript(self, id, name='', url2script=None, 
                                REQUEST=None, submit=None):
    """ Add Isse Report Script object """
    url = url2script
    
    if not id and name:
        name = name.strip()
        if name.find('-') > -1:
            id = name.replace(' ','_')
        else:
            id = name.replace(' ','-')
        id = Utils.safeId(id)
    elif not id:
        id = url.split('/')[-1]
        if id.endswith('.py'):
            id = id[:-3]
        
    id = str(id)
    id = self._setObject(id, ReportScript(id))
    if REQUEST is not None:
        file = REQUEST.form.get('file', '')
        if type(file) is not type(''): file = file.read()
        
        
        if not file:
            
            if url:
                # download it from the net
                file = _suck_url(url)
            else:
                file = open(_default_file).read()
        self._getOb(id).write(file)
        if name:
            self._getOb(id).ZPythonScript_setTitle(name)
        try: u = self.DestinationURL()
        except: u = REQUEST['URL1']
        if submit==" Add and Edit ": u="%s/%s" % (u,quote(id))
        REQUEST.RESPONSE.redirect(u+'/manage_main')
    return ''


class ReportScript(PythonScript):
    """ A ReportScript is a script where issue objects are passed
    through. The script looks at the issue and decides if it should be
    included in this particular report.
    """

    meta_type = REPORTSCRIPT_METATYPE

    manage_options = (PythonScript.manage_options[0],) + \
                     ({'label':'Test', 'action':'manage_TestReport'},) + \
                     (PythonScript.manage_options[1],) + \
                     PythonScript.manage_options[3:]
    
    security = ClassSecurityInfo()

    def __init__(self, id):
        self.id = id
        self.ZBindings_edit(defaultBindings)
        self._makeFunction()
        
        self.last_yield_parentpath = None
        self.last_yield_count = None
        self.last_yield_date = None
        

    def getId(self):
        return self.id
    
    def getTitle(self):
        """ return title """
        return self.title_or_id()
    
    security.declareProtected(VMS, 'Download2FS')
    def Download2FS(self, REQUEST=None, RESPONSE=None):
        """ return as a file for download """
        if RESPONSE is not None:
            RESPONSE.setHeader('Content-Type', 'text/x-python')
            _inline = 'inline;filename="%s.py"'
            RESPONSE.setHeader('Content-Disposition', _inline % self.getId())
        return self.read()
    
    
    def manage_afterAdd(self, REQUEST, RESPONSE):
        """ clear the last_yield_* in case this script has been copied from 
        another issuetracker. """
        if getattr(self, 'last_yield_count', None):
            if self.last_yield_parentpath != '/'.join(aq_parent(aq_inner(self)).getPhysicalPath()):
                self.last_yield_count = None
                self.last_yield_parentpath = None
                self.last_yield_date = None
                
        
    def setYieldCount(self, count):
        """ a yield count is an integer number of how many issues were returned
        when this report is run. This number is stored with a date and which 
        issuetracker path was used. The last thing is required because the script
        might be moved to a different issuetracker where the count doesn't 
        make sense because the issues are different. """
        count = int(count)
        assert count > -1, "count must be 0 or greater"
        self.last_yield_parentpath = '/'.join(aq_parent(aq_inner(self)).getPhysicalPath())
        self.last_yield_count = count
        self.last_yield_date = DateTime()
        
    def getYieldCountAndDate(self):
        """ return a tuple of the the (count, date) if possible """
        if getattr(self, 'last_yield_count', None):
            return (self.last_yield_count, self.last_yield_date)
        return None
        
    
        
        
    security.declareProtected(VMS, 'manage_TestReport')
    manage_TestReport = DTMLFile('dtml/test_report', globals())
    
    ZPythonScriptHTML_editForm = DTMLFile('dtml/ReportScriptEdit', globals())
    manage = manage_main = ZPythonScriptHTML_editForm
    ZPythonScriptHTML_editForm._setName('ZPythonScriptHTML_editForm')
    
    
        
InitializeClass(ReportScript)    