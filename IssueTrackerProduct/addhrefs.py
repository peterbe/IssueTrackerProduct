##
## addhrefs.py
## by Peter Bengtsson, 2004-2005, mail@peterbe.com
##
## License: ZPL (http://www.zope.org/Resources/ZPL)
##
__doc__='''A little function that puts HTML links into text.'''
__version__='0.7'


__changes__ = '''
0.7           addhrefs() checks that emaillinkfunction and urllinkfunction if passed
              are callable.
    
0.6           three new parameters:
                 return_everything=0 - returns (text, urlinfo, emailinfo)
				       where urlinfo and emailinfo are lists
		 emaillinkfunction=None - callback function for making an email
		                          into a HTML link the way you want it
		 urllinkfunction=None - callback function for making an URL into
					a HTML link the way you want it
					
0.5           "foo https bar" created one link

0.4           Python2.1 compatible with custom True,False

0.3           Only one replace which solved the problem with
              "www.p.com bla bla http://www.p.com"
	      
0.2           Lots of fine tuning. Created unit tests.

0.1           Project started. First working draft
'''

__credits__='''
David Otton,
"flump cakes"
'''

True = not not 1
False = not True
		     
import re, sys


_end_dropouts = list(')>.;:,"')
_start_dropouts = list('(<')
def _massageURL(url):
    while url[-1] in _end_dropouts:
        url = url[:-1]
    if url[0] in _start_dropouts:
        url = url[1:]
  
    return url

def _improveURL(url):
    if url.startswith('www.'):
        return 'http://'+url
    return url


def _makeLink(url):
    return '<a href="%s">%s</a>'%(_improveURL(url), url)

def _makeMailLink(url):
    return '<a href="mailto:%s">%s</a>'%(_improveURL(url), url)

def _rejectEmail(email, start):
    if email.find(':') > -1:
	return True
    return False

_bad_in_url = list('!()<>')
_dont_start_url = list('@')
def _rejectURL(url, start):
    """ return true if the URL can't be a URL """
    if url.lower()=='https':
	return True
    for each in _bad_in_url:
	if url.find(each) > -1:
	    return True
    whereat = url.find('@')
    if whereat > -1:
	url = url.replace('http://','').replace('ftp://','')
	if not -1 < url.find(':') < whereat:
	    return True
    if start in _dont_start_url:
	return True
    return False
    

_mailto_regex = re.compile('((^|\(|<|\s|)(\S+@\S+\.\S+)(\)|>|\s|$))')
_url_regex = re.compile('((^|\(|<|@|\s|)(ftp\S+|http\S+|www\.\S+)(\)|>|\s|$))')
def addhrefs(text, return_everything=0, 
	     emaillinkfunction=_makeMailLink,
	     urllinkfunction=_makeLink):
    
    if not callable(emaillinkfunction):
	if emaillinkfunction is not None:
	    print >>sys.stderr, "%r is not callable email link function"%emaillinkfunction
	emaillinkfunction = _makeMailLink
    
    if not callable(urllinkfunction):
	if urllinkfunction is not None:
	    print >>sys.stderr, "%r is not callable URL link function"%urllinkfunction
	urllinkfunction = _makeLink
    
    info_emails = []
    info_urls = []
    
    urls = _url_regex.findall(text)
    for each in urls:
        whole, start, url, end = each

        url = _massageURL(url)
	if _rejectURL(url, start):
	    continue
	link = urllinkfunction(url)
	if return_everything:
	    info_urls.append((url, link))
        better = whole.replace(url, link)
        text = text.replace(whole, better, 1)
        
    
    for each in _mailto_regex.findall(text):
        whole, start, url, end = each
        url = _massageURL(url)
	if _rejectEmail(url, start):
	    continue
	if url.find(':') > -1:
	    link = urllinkfunction(url)
	    if return_everything:
		info_urls.append((url, link))
	    better = whole.replace(url, link)
	else:
	    link = emaillinkfunction(url)
	    info_emails.append((url, link))
	    better = whole.replace(url, link)
        text = text.replace(whole, better)        

    if return_everything:
	return text, info_urls, info_emails
    else:
	return text


def test():
    t="this some text http://www.peterbe.com/ with links www.peterbe.com in it"
    t='''this <a href="http://www.google.com">some</a> text http://www.peterbe.com/
    with links www.peterbe.com in it <a href="http://www.example.com">Example</a>'''
    

    

    t2='this <a href="http://www.google.com">some</a> text http://www.peterbe.com/ '\
       'with links www.peterbe.com in it '\
      '<a href="http://www.example.com">Example</a>'

    t3='''this <a href="http://www.google.com">some</a> text http://www.peterbe.com/
with links www.peterbe.com in it <a href="http://www.example.com">Example</a>
www,peterbe.com and <a href="www.peterbe.com">www.peterbe.com</a>
    '''

    t4='''https://www.imdb.com (www.peterbe.com/?a=e) asd tra la www.google.com'''
    
    t = 'word (www.peterbe.com) word'
    
    t = 'word <http://www.peterbe.com?poage=2314> and so on'
    
    t = 'Go to: http://www.peterbe.com. There youll find'
    
    t = 'Go to: http://www.peterbe.com:'
    t = '''https://www.imdb.com.'''
    t = 'Hello mail@peterbe.com to you'
    t = 'Hello <mail@peterbe.com> and <www.google.com> to you'
    #t = open('sample-htmlfree.txt').read()
    t = '<a href="link1.html">Link1</a> link www.2.com'
    t = "<a href='www.google.com'>Link1</a> link www.2.com"
    t = '''1. http://www.peterbe.com
2. www.peterbe.com
3. <http://www.peterbe.com>
4. mail@foobar.com
5. "Name <mail@foobar.com>"'''
    t = 'xxx mail@peterbe.com peter@grenna.net'
    t += ' xxx www.peterbe.com www.google.com xxx'

    t = 'mail@peterbe.com 123@a.com or www2.ibm.com or www.ibm.com?asda=ewr&amp;gr:int=34.'
    
    t = 'peter@grenna.net 123@a.com ftp://ftp.uk.linux.org/'
    t = 'http://david:otton@www.something.com david:otton@www.something.com'
    t = ''' <http://www.google.com/?asd=q32> xxx
    <http://www.peterbe.com> abc <mail@peterbe.com>'''
    t='''www.msn.co.uk

http://msn.co.uk
http://www.msn.co.uk

ftp:/google.com
'''
    t = 'At http://localhost/ I have apache and at http://localhost:8080 '\
        ' I have Zope David used http://enchanter or http://enchanter/'
    t = 'See http://www.something.com/page?this=that#001'
    t = 'Bla bla https bla bla and http bla'
    print addhrefs(t, emaillinkfunction=None)
    


        
    
    
if __name__=='__main__':
    test()
