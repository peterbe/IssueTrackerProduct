import os
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from OFS.Folder import Folder
from Products.IssueTrackerProduct.Constants import UNICODE_ENCODING

manage_addIssueTrackerOpenIDProviderForm = \
  PageTemplateFile('zpt/addIssueTrackerOpenIDProviderForm', globals())

def manage_addIssueTrackerOpenIDProvider(dispatcher, oid, url, title=u'', 
                                         icon=None, REQUEST=None):
    """Create and OpenID authenticator"""
    dest = dispatcher.Destination()
    
    if isinstance(title, str):
        title = unicode(title, UNICODE_ENCODING)
    
    provider = IssueTrackerOpenIDProvider(oid, url, title.strip())
    dest._setObject(oid, provider)
    
    instance = dest._getOb(oid)
    
    if icon and getattr(icon, 'filename', None):
        filename = getattr(icon, 'filename')
        filename = 'icon' + os.path.splitext(filename)[1]
        instance.manage_addImage(filename, file=icon, title=instance.getTitle())
    
    if REQUEST is not None:
        return dispatcher.manage_main(dispatcher, REQUEST)


class IssueTrackerOpenIDProvider(Folder):
    meta_type = 'Issue Tracker OpenID provider'
    
    _properties = ({'id':'title', 'type': 'ustring', 'mode':'w'},
                   {'id':'url', 'type': 'string', 'mode':'w'},
                   )
    
    def __init__(self, id, url, title=u''):
        super(IssueTrackerOpenIDProvider, self).__init__(id)
        assert self.id
        self.url = url
        self.title = title
        
    def getId(self):
        return self.id
    
    def getTitle(self):
        return self.title
        
    def getIcon(self):
        return getattr(self, 'icon.png',
                       getattr(self, 'icon.gif',
                               getattr(self, 'icon.jpg', None)))
    
    def getFinalURL(self, username=None):
        if self.requiresUsername():
            assert 'USERNAME' in self.url
            assert username, "username must be provided for %s" % self.url
            return self.url.replace('USERNAME', username)
        else:
            return self.url
        
    def requiresUsername(self):
        return 'USERNAME' in self.url
    
    
        
    

        
    