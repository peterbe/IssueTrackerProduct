##
## IssueTrackerOpenID
## (c) Peter Bengtsson, mail@peterbe.com
## 2010
##
## Please visit www.issuetrackerproduct.com for more info
##
import re
import os
import logging
from pprint import pprint
from cgi import parse_qs
from urllib import urlencode
from openid.yadis.discover import DiscoveryFailure
from openid.consumer.consumer import Consumer, SUCCESS
from openid.extensions.sreg import SRegRequest, SRegResponse, supportsSReg
from base64 import encodestring, decodestring

from DateTime import DateTime
import transaction
from Products.CookieCrumbler.CookieCrumbler import CookieCrumbler
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl import ClassSecurityInfo, getSecurityManager
from AccessControl.SecurityManagement import newSecurityManager
from Acquisition import aq_inner, aq_parent, aq_base

try:
    # >= Zope 2.12
    from App.class_init import InitializeClass
except ImportError:
    # < Zope 2.12
    from Globals import InitializeClass

from Products.IssueTrackerProduct.Constants import UNICODE_ENCODING

from Products.IssueTrackerProduct.TemplateAdder import addTemplates2Class as AT2C
def addTemplates2Class(klass, templates, optimize=None):
    AT2C(klass, templates, optimize, Globals=globals())
        

from store import ZopeStore

logger = logging.getLogger("IssueTrackerOpenID")

class InitializationError(Exception):
    pass

manage_addIssueTrackerOpenIDForm = \
  PageTemplateFile('zpt/addIssueTrackerOpenIDForm', globals())

def manage_addIssueTrackerOpenID(dispatcher, oid, title=u'OpenID Authentication',
                                 create_default_providers=True,
                                 REQUEST=None):
    """Create and OpenID authenticator"""
    dest = dispatcher.Destination()
    
    if isinstance(title, str):
        title = unicode(title, UNICODE_ENCODING)
    
    issuetracker_openid = IssueTrackerOpenID(oid, title.strip())
    dest._setObject(oid, issuetracker_openid)
    instance = dest._getOb(oid)
    
    
    # create an ordered folder
    instance.manage_addOrderedFolder('providers')
    if create_default_providers:
        _create_default_providers(instance.providers)
        
    if REQUEST is not None:
        return dispatcher.manage_main(dispatcher, REQUEST)

def _create_default_providers(container):
    
    adder = container.manage_addProduct['IssueTrackerOpenID']\
    .manage_addIssueTrackerOpenIDProvider
    
    # inside this create the known providers
    default_providers_dir = os.path.join(os.path.dirname(__file__),
                                        'default_providers')
    default_providers = sorted(os.listdir(default_providers_dir))
    
    # create these
    for each in default_providers:
        if each.startswith('.'):
            # e.g. '.svn'
            continue
        id = re.sub('\d+_', '', each)
        _folder = os.path.join(default_providers_dir, each)
        try:
            title = open(os.path.join(_folder, 'title.txt')).read().strip()
            url = open(os.path.join(_folder, 'url.txt')).read().strip()
        except IOError:
            logging.warn("Invalid provider folder %s" % _folder)
            continue
        
        # also expect a file like icon.(gif|png|jpg)
        adder(id, url, title=title)
        provider = getattr(container, id)
        if os.path.isfile(os.path.join(_folder, 'icon.png')):
            icon_path = os.path.join(_folder, 'icon.png')
        elif os.path.isfile(os.path.join(_folder, 'icon.gif')):
            icon_path = os.path.join(_folder, 'icon.gif')
        elif os.path.isfile(os.path.join(_folder, 'icon.jpg')):
            icon_path = os.path.join(_folder, 'icon.jpg')
        else:
            raise OSError("Expected a file called icon.(gif|jpg|png)")
        
        provider.manage_addImage(os.path.basename(icon_path),
                                open(icon_path, 'rb'),
                                title=title)


class IssueTrackerOpenID(CookieCrumbler):
    
    meta_type = 'Issue Tracker OpenID'

    security = ClassSecurityInfo()
    
    _properties = CookieCrumbler._properties
    
    def __init__(self, oid, title=u""):
        super(IssueTrackerOpenID, self).__init__(oid)
        self.title = title
        self.long_login_days = 60
        self.store = ZopeStore()        
    
    def getConsumer(self):
        session = self.REQUEST["SESSION"]
        return Consumer(session, self.store)
    
    def getAvailableProviders(self):
        return self.providers.objectValues('Issue Tracker OpenID provider')
    
        
    # taken from CookieCrumblerIssueTrackerProduct
    def setAuthCookie(self, resp, cookie_name, cookie_value):
        """ this method overrides the default setAuthCookie so that we can
        set the cookie for a longer time. """
        kw = {}
        req = getattr(self, 'REQUEST', None)
        if req is not None and req.get('SERVER_URL', '').startswith('https:'):
            # Ask the client to send back the cookie only in SSL mode
            kw['secure'] = 'y'

        if req.get('remember_login_days'):
            days = int(req.get('remember_login_days'))
            then = DateTime() + days
            kw['expires'] = then.rfc822()
            resp.setCookie('use_remember_login_days', '1',
                           path=self.getCookiePath(), **kw)
        else:
            resp.setCookie('use_remember_login_days', '0',
                           path=self.getCookiePath(), **kw)
            
        resp.setCookie(cookie_name, cookie_value,
                       path=self.getCookiePath(), **kw)
        
        logout_url_start = self.absolute_url()
        
        if self.REQUEST.SESSION.get('cc_in_path'):
            # that means the user authenticated in a different root
            # to where the openid instance is located
            cc_in_path = self.REQUEST.SESSION.get('cc_in_path')
            assert cc_in_path.startswith('/')
            context = aq_parent(aq_inner(self)).unrestrictedTraverse(cc_in_path.split('/')[1:])
            logout_url_start = context.absolute_url() + '/%s' % self.getId()

        resp.setCookie('__issuetracker_logout_page',
                       logout_url_start+'/logout', # that's how it's defined in CookieCrumbler
                       path=self.getCookiePath(), **kw)
        
        
    def initiateOpenID(self, REQUEST):
        """start the OpenID redirection business"""
        provider_id = REQUEST.get('provider')
        url = REQUEST.get('url')
        username = REQUEST.get('username')
        
        if provider_id:
            try:
                provider = getattr(self.providers, provider_id)
            except AttributeError:
                raise InitializationError("Unrecognized provider ID (%r)" % provider_id)

            assert provider.meta_type == 'Issue Tracker OpenID provider'
            
            if provider.requiresUsername() and not username:
                raise InitializationError("username must be provided for that URL")
            
            url = provider.getFinalURL(username=username)
            
        elif not url or (url and not url.strip()):
            raise InitializationError("No URL")
        
        if username:
            REQUEST.SESSION['desired_username'] = username
        
        if not self.REQUEST.SESSION.get('cc_in_path'):
            # this will set the cc_in_path session variable
            self._set_cc_in_path()
            
            
        consumer = self.getConsumer()
        try:
            auth_request = consumer.begin(url)
        except DiscoveryFailure, e:
            raise InitializationError(
                "openid consumer discovery error for identity %s: %s" % (url, e[0])
                )
        except KeyError, e:
            raise InitializationError(
                "openid consumer error for identity %s: %s" % (url, e.why))
        
        realm = self.absolute_url()
        return_to = realm + '/authenticate'
        
        url = auth_request.redirectURL(realm, return_to)
        
        parameters = {
            'openid.ns.sreg': 'http://openid.net/extensions/sreg/1.1',
            'openid.sreg.optional' : 'fullname,country',
            'openid.sreg.required': 'email',
            'openid.sreg.policy_url': 'https://www.snapexpense.com/privacy-policy',

            'openid.ns.ax':'http://openid.net/srv/ax/1.0',
            'openid.ax.mode':'fetch_request',
            # if I don't make these required, Google won't serve them as optional
            'openid.ax.required':'email,firstname,lastname,country',
            #'openid.ax.if_available':'firstname,lastname,country',
            'openid.ax.type.firstname':'http://axschema.org/namePerson/first',
            'openid.ax.type.lastname':'http://axschema.org/namePerson/last',
            'openid.ax.type.email':'http://axschema.org/contact/email',
            'openid.ax.type.country':'http://axschema.org/contact/country/home',
        }
        qs = url.split('?', 1)[1]
        qs_parsed = parse_qs(qs)

        for parameter in parameters:
            if parameter not in qs_parsed:
                qs_parsed[parameter] = [parameters[parameter]]
        #pprint(qs_parsed)
        qs = urlencode(qs_parsed, True)
        url = url.split('?')[0] + '?' + qs
            
        return REQUEST.RESPONSE.redirect(url)
    
    def remember_came_from(self, came_from):
        self.REQUEST.SESSION['cc_came_from'] = came_from
        
    def getRememberedOpenIDUsername(self):
        return self.REQUEST.cookies.get('openid_username', '')
    
    def authenticate(self, REQUEST):
        """called back"""
        creds = self._extractOpenIdServerResponse(REQUEST)
        #print "CREDS"
        #pprint(creds)
        identity = self._authenticateCredentials(creds)
        if not identity:
            return REQUEST.RESPONSE.redirect(self.absolute_url()+'/authentication_failed')
        
        #print "IDENTITY"
        #pprint(identity)
        
        email = creds.get('openid.ext1.value.email',
                        creds.get('openid.ax.value.email',
                                creds.get('openid.sreg.email')))
        fullname = creds.get('openid.sreg.fullname', u'')
        if not fullname:
            firstname = creds.get('openid.ext1.value.firstname', u'')
            lastname = creds.get('openid.ext1.value.lastname', u'')
            if firstname or lastname:
                fullname = u"%s %s" % (firstname, lastname)
        
        username = REQUEST.SESSION.get('desired_username')
        if username:
            # it worked! remember this
            one_year_from_now = (DateTime() + 365).rfc822()
            REQUEST.RESPONSE.setCookie('openid_username', 
                                       username,
                                       expires=one_year_from_now,
                                       path='/')
        if not username and email:
            username = email.split('@')[0]
            
        assert username, "No username"
        
        search_context = self
        
        if self.REQUEST.SESSION.get('cc_in_path'):
            cc_in_path = self.REQUEST.SESSION.get('cc_in_path')
            # this is expected to be a relative path compared to the parent of
            # the openid instance itself and we can expect to tack this on
            assert cc_in_path.startswith('/')
            search_context = aq_parent(aq_inner(self)).unrestrictedTraverse(cc_in_path.split('/')[1:])
        
        # Now we just need to find this user in the acl_users folder here
        found_user = self._traverse_find_user(search_context, username, email=email)
        if not found_user and email:
            found_user = self._traverse_find_user(search_context, None, email=email)
        
        if found_user:
            #print "FOUND USER", found_user
            #print dir(found_user)
            #print "roles:", found_user.getRoles()
            # programmatically log in the user here
            REQUEST.set(self.name_cookie, found_user.getUserName())
            REQUEST.set(self.pw_cookie, found_user._getPassword())
            self.modifyRequest(REQUEST, REQUEST.RESPONSE)
        else:
            url = self.absolute_url()+'/authentication_failed'
            return REQUEST.RESPONSE.redirect(url + '?username=%s' % username.encode('utf8'))
        
        if self.REQUEST.SESSION.get('cc_came_from'):
            url = self.REQUEST.SESSION.get('cc_came_from')
        elif self.REQUEST.SESSION.get('cc_in_path'):
            url = aq_parent(aq_inner(self)).absolute_url_path() + \
              self.REQUEST.SESSION.get('cc_in_path')
        else:
            # desperate
            url = aq_parent(aq_inner(self)).absolute_url()
        return REQUEST.RESPONSE.redirect(url)
    
    def _traverse_find_user(self, container, username=None, email=None):
        c = 1
        found_username = found_user = None
        while True:
            acl_users = getattr(container, 'acl_users', None)
            
            if not acl_users:
                break
                
            try:
                found_username, found_user = self._find_acl_user(acl_users, username, email=email)
                found_user = found_user.__of__(acl_users)
                break
            except TypeError:
                # carry on
                pass
            
            container = aq_parent(aq_parent(acl_users))

            c += 1
            if c > 100:
                break
            
        return found_user
        
    
    def _find_acl_user(self, userfolder, username=None, email=None):
        assert username or email, "at least one must be set"
        if username:
            try:
                return username, userfolder.data[username]
            except KeyError:
                return 
        else:
            # not that simple :(
            for username_, user in userfolder.data.items():
                if getattr(user, 'email', '_marker_').lower() == email.lower():
                    return username_, user
        
        
        
    def _extractOpenIdServerResponse(self, request):
        """Process incoming redirect from an OpenId server.

        The redirect is detected by looking for the openid.mode
        form parameters. If it is found the creds parameter is
        cleared and filled with the found credentials.
        """
        creds = {}
        mode=request.form.get("openid.mode", None)
        if mode=="id_res":
            # id_res means 'positive assertion' in OpenID, more commonly
            # described as 'positive authentication'
            creds.clear()
            creds["openid.source"]="server"
            creds["janrain_nonce"]=request.form.get("janrain_nonce")
            for (field,value) in request.form.iteritems():
                if field.startswith("openid.") or field.startswith("openid1_"):
                    creds[field]=request.form[field]
        elif mode=="cancel":
            # cancel is a negative assertion in the OpenID protocol,
            # which means the user did not authorize correctly.
            pass
        
        return creds
    
        
    def _authenticateCredentials(self, credentials):
        if not credentials.has_key("openid.source"):
            return
        
        if credentials["openid.source"]=="server":
            consumer=self.getConsumer()

            # remove the extractor key that PAS adds to the credentials,
            # or python-openid will complain
            query = credentials.copy()
            if 'extractor' in query:
                del query['extractor']
       
            result=consumer.complete(query, self.REQUEST.ACTUAL_URL)
            identity=result.identity_url

            if result.status==SUCCESS:
                return identity
            else:
                logger.info("OpenId Authentication for %s failed: %s",
                                identity, result.message)
                
                
    #security.declarePrivate('modifyRequest')
    #def modifyRequest(self, req, resp):
    #    """let the madness begin"""
    #    return super(IssueTrackerOpenID, self).modifyRequest(req, resp)
    
    security.declarePublic('logout')
    def logout(self):
        """override the CookieCrumbler logout() because we want redirect
        not to the absolute url of the openid instance but instead 
        where you are
        """
        super(IssueTrackerOpenID, self).logout()
        url = self.REQUEST.URL1 + '/logged_out'
        self.REQUEST.RESPONSE.redirect('%s?disable_cookie_login__=1' % url)
        return ''
         
    
    security.declarePublic('getUnauthorizedURL')
    def getUnauthorizedURL(self):
        """Before we redirect to the login screen remember where you came
        from properly because when we later manage to authenticate this is 
        where we'll be looking for your user object.
        """
        url = super(IssueTrackerOpenID, self).getUnauthorizedURL()
        
        self._set_cc_in_path()
        # because CookieCrumbler will soon raise an Redirect error to make
        # zope actually do the redirect setting this session won't be saved
        transaction.commit()
        
        return url

    def _set_cc_in_path(self):
        openid_parent = aq_parent(aq_inner(self))
        
        in_path = self.REQUEST.URL1
        if '/%s' % self.getId() in in_path:
            in_path = self.REQUEST.URL2
            
        in_path = in_path.replace(openid_parent.absolute_url(), '')
        assert in_path.startswith('/')
        assert not in_path.endswith('/')
        print "-> in_path", in_path
        self.REQUEST.SESSION['cc_in_path'] = in_path
        

    
    
zpts = ('zpt/header_footer',
        'zpt/logged_out',
        'zpt/login_form',
        'zpt/logged_in',
        'zpt/login_macros',
        'zpt/authentication_failed',
        )
addTemplates2Class(IssueTrackerOpenID, zpts)

setattr(IssueTrackerOpenID, 'index_html', IssueTrackerOpenID.login_form)

InitializeClass(IssueTrackerOpenID)