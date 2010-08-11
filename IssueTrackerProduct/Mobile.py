# Ripped from http://github.com/brosner/minidetector/

SEARCH_STRINGS = """
# Adapted from http://pub.mowser.com/wiki/Main/CodeExamples
# With a few additions by Moof
# The latest version of this file is always available from:
# http://minidetector.googlecode.com/svn/trunk/minidetector/search_strings.txt
#
# This list is public domain, please feel free to use it for your own projects
# If HTTP_USER_AGENT.lower() contains any of these strings, it's a mobile
# Also include some games consoles, see below
sony
symbian
nokia
samsung
mobile
windows ce
epoc
opera mini
nitro
j2me
midp-
cldc-
netfront
mot
up.browser
up.link
audiovox
blackberry
ericsson,
panasonic
philips
sanyo
sharp
sie-
portalmmm
blazer
avantgo
danger
palm
series60
palmsource
pocketpc
smartphone
rover
ipaq
au-mic,
alcatel
ericy
up.link
docomo
vodafone/
wap1.
wap2.
plucker
480x640
sec
# The Google transcoder
google wireless transcoder
# These are games consoles that either have a small screen or display on a
# TV. Best to treat them as mobiles for web display
nintendo
webtv
playstation
"""
SEARCH_STRINGS = [s.strip() for s in SEARCH_STRINGS.splitlines() 
                  if not s.startswith('#') and s.strip()]

class MobileBase(object):
    """mixin class for dealing with and mobile web users"""
    
    def isMobileUserAgent(self, user_agent_string, ignore_disabling=False):
        user_agent_string = user_agent_string.lower()
        for search_string in SEARCH_STRINGS:
            if search_string in user_agent_string:
                # but has the user got a session saying they don't want to 
                # use the mobile version
                if not ignore_disabling and self.get_session('disable_mobile_version'):
                    return False
                return True
        return False
    
    
    def DisableMobileVersion(self, REQUEST):
        """set a session variable that this user doesn't want to use the mobile
        web version"""
        self.set_session('disable_mobile_version', True)
        if REQUEST.HTTP_REFERER:
            return REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)
        else:
            return REQUEST.RESPONSE.redirect(self.getRootURL())
        
    def EnableMobileVersion(self, REQUEST):
        """UNset a session variable that this user doesn't want to use the mobile
        web version"""
        self.delete_session('disable_mobile_version')
        if REQUEST.HTTP_REFERER:
            return REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)
        else:
            return REQUEST.RESPONSE.redirect(self.getRootURL())
        
    
    
    
    