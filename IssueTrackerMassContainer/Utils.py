# Peter Bengtsson <mail@peterbe.com>
# Utility scripts for IssueTrackerMassContainer
#

# zope
from Products.PythonScripts.standard import url_quote


def AddParam2URL(url, params={}):
    """ return url and append params but be aware of existing params """
    p='?'
    if p in url:
        p = '&'
    url = url + p
    for key, value in params.items():
        url = url + '%s=%s&'%(key, url_quote(value))
    return url[:-1]


def cookIdAndTitle(s):
    """ if s='image1~Image One.gif' then return ['image1.gif','Image One']

        Testwork:
        s='image1~Image One.gif'    => ['image1.gif','Image One']
        s='image1.gif'              => ['image1.gif','']
        s='image1~.gif'             => ['image1.gif','']
        s='image1~Image One.gif.gif'=> ['image1.gif','Image One.gif']
    """
    if s.find('~') == -1:
        return s, ''
    splitted = s.split('~',1)
    id = splitted[0]
    rest = s.replace(id+'~','')
    if rest.rfind('.') == -1:
        return id, rest
    else:
        pos_last_dot = rest.rfind('.')
        ext = rest[pos_last_dot:]
        id = id.strip() + ext.strip()
        title = rest[0:pos_last_dot].strip()
        return id, title
