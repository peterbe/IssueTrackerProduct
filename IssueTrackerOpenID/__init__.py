##
## IssueTrackerOpenID
## (c) Peter Bengtsson, mail@peterbe.com
## 2010
##
## Please visit www.issuetrackerproduct.com for more info
##
import os
import OFS
import OpenID
import Providers
from Products.IssueTrackerProduct import _registerIcon

def initialize(context):
    context.registerClass(
        OpenID.IssueTrackerOpenID,
        constructors=(OpenID.manage_addIssueTrackerOpenIDForm,
                      OpenID.manage_addIssueTrackerOpenID),
        icon='www/openid_icon.png',
        )
    
    context.registerClass(
        Providers.IssueTrackerOpenIDProvider,
        constructors=(Providers.manage_addIssueTrackerOpenIDProviderForm,
                      Providers.manage_addIssueTrackerOpenIDProvider),
        #icon='www/openid_icon.png',
        )    
    
    def registerIcon(filename, **kw):
        epath = os.path.join(os.path.dirname(__file__), 'www')
        _registerIcon(OFS.misc_.misc_.IssueTrackerOpenID, filename, epath=epath, **kw)
    
    #registerIcon('google.png')
    #registerIcon('yahoo.png')
    registerIcon('openid-input.png')
    
    
