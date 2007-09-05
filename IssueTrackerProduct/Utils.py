# -*- coding: iso-8859-1 -*
# Peter Bengtsson <mail@peterbe.com>
# Utility scripts for IssueTrackerProduct
#

# python 
import string
from string import translate, maketrans
import sys, re, os
import codecs
from random import shuffle
from math import floor
from htmlentitydefs import entitydefs

# import line used by textify
import formatter, htmllib, StringIO


entitydefs_inverted = {}
for k,v in entitydefs.items():
    entitydefs_inverted[v] = k



# zope
from Products.PythonScripts.standard import html_quote, newline_to_br, \
         url_quote, url_quote_plus

from StructuredText.StructuredText import HTML

def structured_text(txt):
    return HTML(txt,
                level=int(os.environ.get('STX_DEFAULT_LEVEL',3)),
                header=0)

from addhrefs import addhrefs, __version__ as addhrefs_version
_major, _minor = addhrefs_version.split('.')[:2]
try: 
    _major = int(_major)
except ValueError:
    pass
try:
    _minor = int(_minor)
except ValueError:
    pass
assert _minor >= 6, "You don't have the latest addhrefs.py module"


try:
    import itertools
    def anyTrue(pred, seq):
        return True in itertools.imap(pred,seq)
except ImportError:
    def anyTrue(pred, seq):
        for e in seq:
            if pred(e):
                return True
        return False

from Constants import UNICODE_ENCODING

def unicodify(s, encodings=(UNICODE_ENCODING, 'latin1', 'utf8')):
    if isinstance(s, str):
        if not isinstance(encodings, (tuple, list)):
            encodings = [encodings]
        for encoding in encodings:
            try:
                return unicode(s, encoding)
            except UnicodeDecodeError:
                pass
        raise UnicodeDecodeError, \
            "Unable to unicodify %r with these encodings %s" % (s, encodings)
    return s
        

def SimpleTextPurifier(text):
    text = text.replace('<p>&nbsp;</p>','')
    text = text.replace('&nbsp;',' ')
    text = textify(text)
    return text.strip()

def highlightCarefully(word, text, highlightfunction,
                       word_boundary=True):
    """ return the word carefully highlighted using 
    highlightfunction in a text. 
    
    The word is only matched if wordsplitted on both sides.
    The highlightfunction (eg. hlf()) can be something simple like::
        hlf = lambda x: '<span>%s</span>'%x
    
    By carefully we mean that the highlighting shouldn't need to
    be done if the word found is inside a HTML tag.
    
    If this is the word: 'bug' and this is the text:
        I saw a bug on <a href=# title="a bug">this page</a>
    then this is the expected result::
        I saw a <span>bug</span> on <a href=# title="a bug">this page</a>
    """
    if word_boundary:
        regex = re.compile(r'\b(%s)\b' % re.escape(word), re.I)
    else:
        regex = re.compile(r'(%s)' % re.escape(word), re.I)
    
    def matchTester(match):
        before = text[:match.start()]
        if before.rfind('<') > before.rfind('>'):
            return match.group(1)
        else:
            return highlightfunction(match.group(1))
    
    return regex.sub(matchTester, text)
    

def filenameSplitter(filename):
    """ return a list of parts of the filename. The whole filename is
    always included first in the list of parts. The parts are 
    splitted from the filename by caMel notation, [._-] and digits.
    
    see http://www.peterbe.com/plog/filename-splitter
    """

    def _cleanSplit(splitted):
        splitted = [x for x in splitted if len(x) > 1 or x.isdigit()]
        for i in range(len(splitted)):
            if splitted[i][0] == '.':
                splitted.append(splitted[i][1:])
            if splitted[i][0] in ('-','_'):
                splitted[i]=splitted[i][1:]
            if splitted[i][-1] in ('.','-','_'):
                splitted[i]=splitted[i][:-1]
        return splitted
    
    keys = [filename]
    camel_regex = re.compile('([A-Z][a-z0-9]+)')
    keys.extend(_cleanSplit(camel_regex.split(filename)))
    for point in ('\.','_','-','\d+','\s+'):
        keys.extend(_cleanSplit(re.compile('(%s)'%point).split(filename)))
    
    return uniqify(keys)
    
    
def textify(html_snippet):
    return re.sub('<.*?>', '', html_snippet)

##def textify(html_snippet, maxwords=None):
##    """ Thank you Fredrik Lundh
##    http://online.effbot.org/2003_08_01_archive.htm#20030811
##    """
##    
##
##    class Parser(htmllib.HTMLParser):
##        def anchor_end(self):
##            self.anchor = None
##
##    class Formatter(formatter.AbstractFormatter):
##        pass
##
##    class Writer(formatter.DumbWriter):
##        def send_label_data(self, data):
##            self.send_flowing_data(data)
##            self.send_flowing_data(" ")
##
##    o = StringIO.StringIO()
##    p = Parser(Formatter(Writer(o)))
##    p.feed(html_snippet)
##    p.close()
##
##    words = o.getvalue().split()
##
##
##    if maxwords:
##        if len(words) <= 2*maxwords:
##            return string.join(words)
##        
##        return string.join(words[:maxwords]) + " ..."
##    else:
##        return string.join(words)
    
    
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/436833
def printu(ustr):
    print ustr.encode('raw_unicode_escape')
    
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/436833
def saveu(ustr, filename='output.txt'):
    file(filename,'wb').write(codecs.BOM_UTF8 + ustr.encode('utf8'))


def parseFlowFormattedResult(flow):
    """ return (replytext, origtext) """
    replylines = []
    origlines = []
    for e in flow:
        if e[0]['quotedepth']==0:
            replylines.append(e[1].strip())
        elif e[0]['quotedepth']==1:
            origlines.append(e[1].strip())
                  
    while '' in replylines:
        replylines.remove('')
    while '' in origlines:
        origlines.remove('')

    replytext = '\n'.join(replylines)
    origtext = '\n'.join(origlines)
    
    return replytext, origtext
    
    
_bad_file_id = re.compile(r'[^a-zA-Z0-9-_~,.$\(\)# ]')    
def badIdFilter(fileid, replacement=''):
    for badchar in _bad_file_id.findall(fileid):
        fileid = fileid.replace(badchar, replacement)
    return fileid
    
def getFindIssueLinksRegex(zfill, trackerids=None, prefix=None):
    """ return a compiled regular expression that can be used to 
    find references to other issues in a text
    
    TODO: When it starts a string eg. '#1234 bla bla' doesn't work
    because the \b gadget doesn't seem to work in conjunction with 
    '\b#'. If I put the regex like '^<regex>|<regex>' it does find
    with or without starting the string but returns an inconvenient
    regex pattern which is clumpsy. Investigate how to properly 
    (alternative to using ^) find the start of the string. Either that
    or find out how to use \b together with a # symbol.
    """
    assert isinstance(zfill, int), "zfill param must be integer"
    _use_I_ = False
    if prefix:
        if re.findall('[^\d]', prefix):
            # the prefix contains non-numericals, use case insensitive
            # search
            _use_I_ = True
        regex = r'#%s%s|#%s' % (prefix, '\d'*zfill, '\d'*zfill)
    else:
        regex = r'#%s|\B#[1-9][0-9]{0,%s}' % (('\d'*zfill), zfill-1)
        
    if trackerids:
        _use_I_ = True
        if isinstance(trackerids, basestring):
            trackerids = [trackerids]
        _inner = []
        for trackerid in trackerids:
            _inner.append(r'\b%s%s' % (trackerid, regex))
        regex = r'(%s|\B%s)\b' % ('|'.join(_inner), regex)
    else:
        regex = r'\B(%s)\b' % regex
        
    if _use_I_:
        return re.compile(regex, re.I)
    else:
        return re.compile(regex)
        
                                    

def sum(seq):
    return reduce(lambda x,y: x+y, seq)

def splitTerms(s):
    """ if s = 'peter "anders bengt" bengtsson' return
    ['peter','"anders bengt"','bengtsson'] 
    """
    words = []
    if s.count('"') % 2 or s.count('"')==0:
        # the quotes don't balance out, pointless doing this
        return [x.strip() for x in s.split()]
    
    in_quote = None
    for word in s.split(' '):
        if word.count('"') % 2:
            if in_quote is None:
                in_quote = [word]
            else:
                in_quote.append(word)
        elif in_quote:
            words.append(' '.join(in_quote))
            in_quote = None
            words.append(word)
        else:
            words.append(word)
            
    if in_quote:
        words.append(' '.join(in_quote))
        
    return words
    r= re.compile('".*?"')
    wordcomps = r.findall(s)
    for wordcomp in wordcomps:
        words.append(wordcomp[1:-1])
        s = s.replace(wordcomp, '')
    return words
        

            
def createStandaloneWordRegex(word):
    """ return a regular expression that can find 'peter' only if it's written
    alone (next to space, start of string, end of string, comma, etc) but
    not if inside another word like peterbe """
    return re.compile(r'\b%s\b' % word, re.I)     


def dict_popper(dict, key):
    """ simulate what {}.pop() does in Python 2.3 """
    if not dict:
        raise KeyError, 'dict_popper(): dictionary is empty'
        
    if not dict.has_key(key):
        raise KeyError, repr(key)
        
    new_dict = {}
    for k, v in dict.items():
        if k == key:
            value = v
        else:
            new_dict[k] = v
    return value, new_dict

hex_entity_regex = re.compile('&#\d+;')
def AwareLengthLimit(string, maxsize=50, append='...'):
    """ instead of just chopping off a bit of a string
    we do it more carefully. """
    count = 0
    maxsize_orig = maxsize
    for each in hex_entity_regex.findall(string):
        count += 1
        if count > maxsize_orig:
            break
        maxsize += len(each) - 1
        
    if len(string) > maxsize:
        try:
            if string[maxsize-1:maxsize+1] == '&#':
                maxsize += 1
        except IndexError:
            pass
        shortened = string[:maxsize]
        # avoid this '&#1234;&#2345;&#345'. Rather have '&#1234;&#2345;'
        if shortened.rfind('&#') > shortened.rfind(';'):
            shortened = shortened[:shortened.rfind('&#')]
        return shortened.rstrip() + append
    else:
        return string
    

def tag_quote(text):
    """ similiar to html_quote but only fix < and > """
    return text.replace('<','&lt;').replace('>','&gt;')


destroyed_hex_entities = re.compile('&amp;#(\d+);')
def safe_html_quote(text):
    """ like html_quote but allow things like &#1234; """
    text = html_quote(text)
    text = destroyed_hex_entities.sub(r'&#\1;', text)
    return text
    

def highlight_signature(text, attribute='style="color:#ccc"', 
                        tag="span", use_newline_to_br=False):
    text = text.replace('<p>--\n','<p>\n--\n')
    signature_regex = re.compile('(^--\s*(\n|<br\s*/>|<br>))', re.MULTILINE|re.I)
    found_signatures = signature_regex.findall(text)
    if found_signatures:
        whole, linebreak = found_signatures[-1]
        parts = text.split(whole)
        signature = parts[-1]
        if use_newline_to_br:
            whole = newline_to_br(whole)
            signature = newline_to_br(signature)
            
            double_endbreaks = re.compile(r'<br\s*/><br\s*/>$', re.M)
            whole = double_endbreaks.sub('<br />', whole)
            signature = double_endbreaks.sub('<br />', signature)
            
        whitespace = signature.replace(signature.strip(), '')
        signature = '%s<%s %s>%s%s</%s>'%(whitespace,
                                          tag,
                                          attribute,
                                          whole,
                                          signature.strip(),
                                          tag)
        return whole.join(parts[:-1])+signature
    else:
        signature_regex = re.compile('(^|<p>)(--\s*)', re.MULTILINE|re.I)
        splitted = signature_regex.split(text)
        if len(splitted)==4:
            part1, start, dashes, part2 = splitted
            part1 += start
            if start =='<p>':
                _p_splitted = part2.split('</p>')
                joined = '%s<%s %s>'%(part1, tag, attribute)
                joined += '%s%s</%s>%s</p>'%(dashes, _p_splitted[0], tag, _p_splitted[1])
            else:
                joined = '%s<%s %s>%s%s</%s>'%(part1,
                                          tag,
                                          attribute,
                                          dashes,
                                          part2,
                                          tag)
            return joined
        return text

def niceboolean(value):
    falseness = ('','no','off','false','none','0', 'f')
    return str(value).lower().strip() not in falseness
    

_badchars_regex = re.compile('|'.join(entitydefs.values()))
_been_fixed_regex = re.compile('&\w+;|&#[0-9]+;')
def html_entity_fixer(text, skipchars=[], extra_careful=1):
    """ return a text properly html fixed """
    if not text:
        # then don't even begin to try to do anything
        return text

    # if extra_careful we don't attempt to do anything to
    # the string if it might have been converted already.
    if extra_careful and _been_fixed_regex.findall(text):
        return text

    if isinstance(skipchars, basestring):
        skipchars = [skipchars]

    keyholder= {}
    for x in _badchars_regex.findall(text):
        if x not in skipchars:
            keyholder[x] = 1
            
    text = text.replace('&','&amp;')
    text = text.replace(u'\x80', '&#8364;')
    for each in keyholder.keys():
        if each == '&':
            continue

        try:
            better = entitydefs_inverted[each]
            if not better.startswith('&#'):
                better = '&%s;'%entitydefs_inverted[each]
        except KeyError:
            continue
        
        text = text.replace(each, better)
    return text
    


def uniqify(seq, idfun=None): # Alex Martelli ******* order preserving
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        # in old Python versions:
        # if seen.has_key(marker)
        # but in new ones:
        ##if marker in seen: continue
        if seen.has_key(marker): continue
        seen[marker] = 1
        result.append(item)
    return result

def iuniqify(seq):
    """ return a list of strings unique case insensitively.
    If the input is ['foo','bar','Foo']
    return ['foo','bar']
    """
    def idfunction(x):
        if isinstance(x, basestring):
            return x.lower()
        else:
            return x
    return uniqify(seq, idfunction)


                                                                                                            

def moveUpListelement(element, xlist):
    """ move an element in a _mutable_ list up one position
    if possible. If the element is a list, then the function
    is self recursivly called for each subelement.
    """
    
    assert type(xlist)==type([]), "List to change not of list type "\
                                  "(%r)"%type(xlist)
        
    if type(element)==type([]):
        for subelement in element:
            moveUpListelement(subelement, xlist)
            
    if element==xlist[0]:
        pass
    elif element in xlist:
        i=xlist.index(element)
        xlist[i], xlist[i-1] = xlist[i-1], xlist[i]
        

def encodeEmailString(email, title=None, nolink=0):
    """ just write the email like
    <span class="aeh">peter_AT_peterbe_._com</span>
    and a 'onLoad' Javascript will convert it to look nice.
    The way we show the email address must match the Javascript
    that converts it on the fly. """

    methods = ['_dot_','%20dot%20', '_._']
    shuffle(methods)

    # replace . after @
    if '@' in list(email):
        afterbit = email.split('@')[1]
        newbit = afterbit.replace('.', methods[0])
        email = email.replace(afterbit, newbit)

    methods = ['_', '~']
    shuffle(methods)

    atsigns = ['at','AT']
    shuffle(atsigns)
    
    # replace @ with *AT*
    email = email.replace('@','%s%s%s'%(methods[0], atsigns[0], methods[0]))

    if title is None or title == email:
        title = email

    spantag = '<span class="aeh">%s</span>'
    spantag_link = '<a class="aeh" href="mailto:%s">%s</a>'
    if nolink:
        return spantag % email
    else:
        return spantag_link % (email, title)
        

    
def safebool(value):
    try:
        return not not int(value)
    except ValueError:
        return 0
    

def XXX_NO_LONGER_USED_encodeEmailString(email, title=None, nolink=0):
    """ if encode_emaildisplay then use JavaScript to encode it """
    if title is None:
        title = email

    basic = email.replace('@','(at)').replace('.',' dot ')
    if title != email:
        basic = "%s, %s"%(title, basic)

    if nolink:
        js_string = """document.write('%s')"""%email
    else:
        js_string = """document.write('<a href="mailto:%s">"""%email
        js_string += """%s</a>')"""%title
    hexed = _hex_string(js_string)
    js_script = """<script language="JavaScript" type="text/javascript">eval(unescape('"""
    js_script += hexed + """'))</script>"""
    js_script += "<noscript>%s</noscript>"%basic
    return js_script



def _hex_string(oldstring):
    """ hexify a string """
    # Taken from http://www.happysnax.com.au/testemail.php
    # See Credits

    def _tohex(n):
        hs='0123456789ABCDEF'
        return hs[int(floor(n/16))]+hs[n%16]

    newstring=''
    length=len(oldstring)
    for i in range(length):
        newstring=newstring+'%'+_tohex(ord(oldstring[i]))
    return newstring


def same_type(one, two):
    """ use this because 'type' as variable can be used elsewhere """
    return type(one)==type(two)



def safeId(id, nospaces=0):
    """ Just make sure it contains no dodgy characters """
    lowercase = 'abcdefghijklmnopqrstuvwxyz'
    digits = '0123456789'
    specials = '_-.'
    allowed = lowercase + lowercase.upper() + digits + specials
    if not nospaces:
        allowed = ' ' + allowed
    n_id=[]
    allowed_list = list(allowed)
    for letter in list(id):
        if letter in allowed_list:
            n_id.append(letter)
    return ''.join(n_id)


def ShowFilesize(bytes):
    """ Return nice representation of size """
    if bytes < 1024:
        return "1 Kb"
    elif bytes > 1048576:
        mb_bytes = '%0.02f'%(bytes / 1048576.0)
        return "%s Mb"%mb_bytes
    else:
        return "%s Kb"%int(bytes / 1024)
    

def preParseEmailString(es, names2emails={}, aslist=0):
    """ Take any string and strip out only a string of email
    addresses delimited by 'sep'
    "Peter <mail@peterbe.com>, John;peter@grenna.net, Joe"
    =>
    "mail@peterbe.com; peter@grenna.net"
    But suppose names2email={'joe','joey@host.com')
    then you would expect:
    "mail@peterbe.com; peter@grenna.net; joey@host.com"
    Bare in mind that names2emails can have values that are
    lists, like this: {'group: Friends':['foo@bar.com',...]}
    """
    
    sep = ','
    
    real_emails=[]
    #es = es.replace(';',' ').replace(',',' ')

    # first remove any junk
    es = es.replace(';',sep)
    es = es.replace('>',' ').replace('<',' ')
    transtab = maketrans('/ ','  ')
    es = translate(es, transtab, '?&!()<=>*#[]{}')

    # fix so that, the keys are lower case and 'group:' gone
    n2e = {}
    for k, v in names2emails.items():
        n2e[k.lower().replace('group:', '').strip()] = v

    grand_list = []
    for chunk in es.split(sep):
        subchunks = []
        _found_one_valid = 0
        for subchunk in chunk.split(): # by space
            subchunks.append(subchunk)
            if ValidEmailAddress(subchunk):
                grand_list.append(subchunk)
                _found_one_valid = 1
                break
        if not _found_one_valid:
            grand_list.extend(subchunks)
            grand_list.append(chunk)
        

    # expand the names2emails
    for item in grand_list[:]:
        if n2e.has_key(ss(item)):
            value = n2e.get(ss(item))
            if same_type(value, []):
                for each in value:
                    if each:
                        grand_list.append(each.strip())
            elif value:
                grand_list.append(value)

    # uniqify
    grand_list = uniqify(grand_list)

    # filter on valid email address
    real_emails = []
    mentioned = []
    for e in grand_list:
        if '@' in e and ValidEmailAddress(e) and ss(e) not in mentioned:
            real_emails.append(e)
            mentioned.append(ss(e))
    

    if real_emails:
        if aslist:
            return real_emails
        else:
            return sep.join(real_emails)
    else:
        if aslist:
            return []
        else:
            return None
        

        

def AddParam2URL(url, params={}, unicode_encoding='utf8', 
                 plus_quote=False, **kwargs):
    """ return url and append params but be aware of existing params """
    if plus_quote:
        url_quoter = url_quote_plus
    else:
        url_quoter = url_quote
    if kwargs:
        params.update(kwargs)
    p='?'
    if p in url:
        p = '&'
    url = url + p
    for key, value in params.items():
        if same_type(value, []) or same_type(value, ()):
            for e in value:
                if isinstance(e, unicode):
                    e = e.encode(unicode_encoding)
                url += '%s=%s&'%(key, url_quoter(e))
        else:
            if isinstance(value, unicode):
                value = value.encode(unicode_encoding)
            url += '%s=%s&'%(key, url_quoter(value))
    return url[:-1]

def fixDictofLists(dict):
    " throw it a dictionary and it returns the values lowercased "
    for key,value in dict.items():
        if same_type(value, []):
            dict[key] = _lowercaseList(value)
        elif same_type(value, 's'):
            dict[key] = value.lower()
    return dict

def _lowercaseList(lst):
    " lowercase and strip all items in a list "
    return [ss(x) for x in lst]

def getRandomString(length=10, loweronly=1, numbersonly=0):
    """ return a very random string """
    if numbersonly:
        l = list('0123456789')
    else:
        lowercase = 'abcdefghijklmnopqrstuvwxyz'+'0123456789'
        l = list(lowercase + lowercase.upper())
    shuffle(l)
    s = string.join(l,'')
    if len(s) < length:
        s = s + getRandomString(loweronly=1)
    s = s[:length]
    if loweronly:
        return s.lower()
    else:
        return s
    
    
# Language constants
MINUTE = 'minute'
MINUTES = 'minutes'
HOUR = 'hour'
HOURS = 'hours'
YEAR = 'year'
YEARS = 'years'
MONTH = 'month'
MONTHS = 'months'
WEEK = 'week'
WEEKS = 'weeks'
DAY = 'day'
DAYS = 'days'
AND = 'and'
    

def timeSince(firstdate, seconddate, afterword=None, 
              minute_granularity=False):
    """
    Use two date objects to return in plain english the difference between them.
    E.g. "3 years and 2 days"
     or  "1 year and 3 months and 1 day"
    
    Try to use weeks when the no. of days > 7
    
    If less than 1 day, return number of hours.
    
    If there is "no difference" between them, return false.
    """
    
    def wrap_afterword(result, afterword=afterword):
        if afterword is not None:
            return "%s %s" % (result, afterword)
        else:
            return result

    fdo = firstdate
    sdo = seconddate

    day_difference = int(abs(sdo-fdo))

    years = day_difference/365
    months = (day_difference % 365)/30
    days = (day_difference % 365) % 30
    minutes = ((day_difference % 365) % 30) % 24

        
    if days == 0 and months == 0 and years == 0:
        # use hours
        hours=int(round(abs(sdo-fdo)*24, 2))
        if hours == 1:
            return wrap_afterword("1 %s" % (HOUR))
        elif hours > 0:
            return wrap_afterword("%s %s" % (hours, HOURS))
        elif minute_granularity:
            minutes = int(round(abs(sdo-fdo) * 24 * 60, 3))
            if minutes == 1:
                return wrap_afterword("1 %s" % MINUTE)
            elif minutes > 0:
                return wrap_afterword("%s %s" % (minutes, MINUTES))
            else:
                # if the differnce is smaller than 1 minute,
                # return 0.
                return 0
        else:
            # if the difference is smaller than 1 hour, 
            # return it false
            return 0
    else:
        s = []
        if years == 1:
            s.append('1 %s'%(YEAR))
        elif years > 1:
            s.append('%s %s'%(years,YEARS))
        
        if months == 1:
            s.append('1 %s'%MONTH)
        elif months > 1:
            s.append('%s %s'%(months,MONTHS))
        
        if days == 1:
            s.append('1 %s'%DAY)
        elif days == 7:
            s.append('1 %s'%WEEK)
        elif days == 14:
            s.append('2 %s'%WEEKS)
        elif days == 21:
            s.append('3 %s'%WEEKS)
        elif days > 14:
            weeks = days / 7
            days = days % 7
            if weeks == 1:
                s.append('1 %s'%WEEK)
            else:
                s.append('%s %s'%(weeks, WEEKS))
            if days % 7 == 1:
                s.append('1 %s'%DAY)
            elif days > 0:
                
                s.append('%s %s'%(days % 7,DAYS))
        elif days > 1:
            s.append('%s %s'%(days,DAYS))
        
        if len(s)>1:
            return wrap_afterword("%s" % (string.join(s,' %s '%AND)))
        else:
            return wrap_afterword("%s" % s[0])




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


def LineIndent(text, indent, maxwidth=None):
    """ indent each new line with 'indent' """
    if maxwidth:
        parts = []
        for part in text.split('\n'):
            words = part.split(' ')
            lines = []
            tmpline = ''
            for word in words:
                if len(tmpline+' '+word) > maxwidth:
                    lines.append(tmpline.strip())
                    tmpline = word
                else:
                    tmpline += ' ' + word
                
            lines.append(tmpline.strip())
            start = "\n%s"%indent
            parts.append(indent + start.join(lines))
        return "\n".join(parts)
    else:
        text = indent+text
        text = text.replace('\n','\n%s'%indent)
    return text





def ShowDescription(text, display_format='',
                    emaillinkfunction=None,
                    urllinkfunction=None):
    """
    Display text, using harmless HTML
    """
    if not text: # blank or None
        return ""

    if display_format == 'structuredtext':
        #st=_replace_special_chars(text)
        st=text
        
        # if the text is just a number (and a full stop), then
        # structured_text is going to make this the first of a numbered
        # HTML list. Prevent that with this "hack".
        found_only_number = re.compile('\d[\d \.]+').findall(st)
        if found_only_number:
            if found_only_number[0] == st:
                return st

        for k,v in {'<':'&lt;', '>':'&gt;',
                    '[':'|[|'}.items():
            st = st.replace(k,v)

        if isinstance(st, str):
            st = html_entity_fixer(st, skipchars=('"',))
            
        st = structured_text(st)
        
        for k,v in {'&amp;lt;':'&lt;', '&amp;gt;':'&gt;',
                    '|[|':'['}.items():
            st = st.replace(k,v)

        st = addhrefs(st, emaillinkfunction=emaillinkfunction,
                      urllinkfunction=urllinkfunction)
            
        return st
    
    elif display_format == 'html':
        return text
    
    else:
        t = '<p>%s</p>'%safe_html_quote(text)
        t = t.replace('&amp;lt;','&lt;').replace('&amp;gt;','&gt;')
        t = addhrefs(t, emaillinkfunction=emaillinkfunction,
                     urllinkfunction=urllinkfunction)
        t = newline_to_br(t)
        
        return t


def _replace_special_chars(text, simplify=1, html_encoding=0):
    """ Replace special characters with placeholder keys back and forth.
        The reason for doing this is that structured_text() doesn't support
        special characters such as umlats.
    """
    
    # THIS NEEDS WORK
    return text
 
    #if simplify:
        #for k, v in reps.items():
            #if html_encoding:
                #k='&%s;'%k
            #else:
                #k='__%s__'%k
            #text = text.replace(v,k)
    #else:
        #for k, v in reps.items():
            #k='__%s__'%k
            #text = text.replace(k,v)
    #return text
    

#def getNowdate():
#    """
#    This method determines the format 
#    with which new objects get a date property
#    """
#   return DateTime()


def _ShouldBeNone(result): return result is not None
def _ShouldNotBeNone(result): return result is None

tests = (
    # Thank you Bruce Eckels for these (some modifications by Peterbe)
  (re.compile("^[0-9a-zA-Z\.\'\+\-\_]+\@[0-9a-zA-Z\.\-\_]+$"),
   _ShouldNotBeNone, "Failed a"),
  (re.compile("^[^0-9a-zA-Z]|[^0-9a-zA-Z]$"),
   _ShouldBeNone, "Failed b"),
  (re.compile("([0-9a-zA-Z\_]{1})\@."),
   _ShouldNotBeNone, "Failed c"),
  (re.compile(".\@([0-9a-zA-Z]{1})"),
   _ShouldNotBeNone, "Failed d"),
  (re.compile(".\.\-.|.\-\..|.\.\..|.\-\-."),
   _ShouldBeNone, "Failed e"),
  (re.compile(".\.\_.|.\-\_.|.\_\..|.\_\-.|.\_\_."),
   _ShouldBeNone, "Failed f"),
  (re.compile(".\.([a-zA-Z]{2,3})$|.\.([a-zA-Z]{2,4})$"),
   _ShouldNotBeNone, "Failed g"),
  # no underscore just left of @ sign or _ after the @
  (re.compile("\_@|@[a-zA-Z0-9\-\.]*\_"), 
   _ShouldBeNone, "Failed h"),
)
def ValidEmailAddress(address, debug=None):
    for test in tests:
        if test[1](test[0].search(address)):
            if debug: return test[2]
            return 0
    return 1

def ss(s):
    """ simple string """
    return s.strip().lower()

  
def test():

    print "----------\n"
    print "TEST AddParam2URL()"
    print AddParam2URL('http://www.peterbe.com')
    print AddParam2URL('http://www.peterbe.com',{'a':'A','b':'B'})
    message="""Line1
Line2"""
    print AddParam2URL('http://www.peterbe.com?o=O',{'a':message,'b':'B spaced'})

    print "----------\n"
    print "TEST preParseEmailString()"
    print preParseEmailString("mail@peterbe.com;JOE,peter@grenna.net,Peter Bengtsson<ppp@ppp.se>; Peter <pete@peterbe.com", \
                              names2emails={'Joe':'joey@peterbe.com', 'Peter bengtsson':'ppp@ppp.se'})
    print preParseEmailString("mail@ ", \
                              names2emails={'Joe':'joey@peterbe.com', 'Peter bengtsson':'ppp@ppp.se'})
    

    print " ++ cookIdAndTitle() ++ "
    print cookIdAndTitle('image1~Image One.gif'), " AND ['image1.gif','Image One']"
    print cookIdAndTitle('image1.gif'), " AND ['image1.gif','']"
    print cookIdAndTitle('image1~.gif'), " AND ['image1.gif','']"
    print cookIdAndTitle('image1~Image One.gif.gif'), " AND ['image1.gif','Image One.gif']"
    print cookIdAndTitle('monk ~ Monkey.dtml'), " AND ['monk.dtml','Monkey']"

    print " ++ ValidEmailAddress() ++ "
    print ValidEmailAddress(''), " AND 0"
    print ValidEmailAddress('issuetracker@peterbe.com'), " AND 1"
    print ValidEmailAddress('issuetracker @peterbe.com'), " AND 0"

    print " ++ getRandomString() ++ "
    print getRandomString(), " "
    print getRandomString(length=50), " AND (length=50)"
    print getRandomString(loweronly=1), " AND (loweronly=1)"

def benchmark_ShowDescription():
    from time import time
    text = open('text.txt','r').read()

    sections = text.split('-'*20)
    sections = [x.strip() for x in sections]
    print len(sections)

    total_time = 0
    total_count = 0
    for i in range(2):
        for section in sections:
            t0 = time()
            stx = ShowDescription(section, 'structuredtext')
            t1 = time()-t0
            total_time += t1
            total_count += 1

    print "Average time:", total_time/total_count
            


def test__preParseEmailString():
    def T(s, d={}, expect=None):
        if d:
            print "From: %r, with %r"%(s,d)
            r = preParseEmailString(s, names2emails=d, aslist=1)
            print "To: %r" % r
        else:
            print "From: %r"%s
            r = preParseEmailString(s, aslist=1)
            print "To: %r" % r
        if expect is not None:
            assert r == expect, "Not what we expected"
        print
        
    es = 'mail@peterbe.com, peter@grenna.net'
#    T(es)

    es = 'mail@peterbe.com, will@.not.work'
    T(es, expect=['mail@peterbe.com'])

    es = 'Mail mail@peterbe.com; Peter peter@grenna.net, Sven <sven@peterbe.com>; SVEN@Peterbe.com  ,'
    T(es, expect=['mail@peterbe.com', 'peter@grenna.net', 'sven@peterbe.com'])

    es = ''
    T(es, expect=[])

    es = 'peter; jOhn'
    d = {'JOHN':'John@peterbe.com', 'peter be':'PeterBe@peterbe.com'}
    T(es, d, expect=['John@peterbe.com'])

    es = 'peter <peter@grena..net>, john <john@ok.com>; group: Friends'
    d['group:friends'] = ['abc@def.com',' PETER@grenna.NET']
    T(es, d, expect=['john@ok.com', 'abc@def.com', 'PETER@grenna.NET'])

    es = 'peter <peter@grena..net>, john <john@ok.com>;GROUP: Friends'
    d['friends'] = ['abc@def.com',' PETER@grenna.NET']
    T(es, d, expect=['john@ok.com','abc@def.com','PETER@grenna.NET'])
    # ------------
    es ='Ed Leafe, Ed Leafe'
    names2emails={'Ed Leafe': 'Ed.Leafe@peterbe.com', 
                  'Ed Leafe, Ed Leafe': 'Ed.Leafe@peterbe.com', 
                  'Ed Leafe (Ed Leafe)': 'Ed.Leafe@peterbe.com'}
    T(es, names2emails, expect=['Ed.Leafe@peterbe.com'])
    
    

def test__addhrefs():
    br='-'*78+'\n'
    print br
    t="this some text http://www.peterbe.com/ with links www.peterbe.com in it"
#    print addhrefs(t)
 #   print br
    
    t='this <a href="http://www.google.com">some</a> text http://www.peterbe.com/ '\
       'with links www.peterbe.com in it '\
      '<a href="http://www.example.com">Example</a>'
    print addhrefs(t)
    print br

#    t='this <a href="http://www.google.com">some</a> text '\
 #     "http://www.peterbe.com/ with links www.peterbe.com in it "\
  #    '<a href="http://www.example.com">Example</a>'
  #  print addhrefs(t)
   # print br
    
    t="this some text http://www.peterbe.com/ with links www.peterbe.com in it"
  #  print addhrefs(t)
   # print br
    
    t='Starts <a href="bajs.com">bajs.com</a> '\
       "this some text http://www.peterbe.com/ with links www.peterbe.com in it "\
      '<a href="http://www.example.com">Example</a>'
   # print addhrefs(t)
    #print br

def test__LineIndent():
    t='''There seems to be a problem with paragraphs that are long and multiple. Thanks for taking a few moments to join us here at Rebel Solutions. We're a new business managed by old hands in the hospitality sector.

After months of market research, planning, and development, we're ready to offer you the best menu of internet enabled tools and solutions. To learn how your business can benefit from a Rebel Solution, click here.'''
    print LineIndent(t, ' '*4, maxwidth=50)
    
def test_niceboolean():
    def x(inp):
        print "%r -> %r"%(inp, niceboolean(inp))
    
    for e in [False, True, 1, 0, '1', '0', 'On','Off','False','No','Yes','T','F']:
        x(e)
        
def test_ShowDescription():
    # what happens if it's None or blank
    print repr(ShowDescription("", 'structuredtext'))
    print repr(ShowDescription(None, 'structuredtext'))
    
    

def test_highlight_signature():
    sign1='''bla bla bla and -- this bla bla
--
Signature here'''

    print highlight_signature(sign1)
    sign2='''<b>Hej</b>
--<br />
signature here'''
    print "-+"*20
    print highlight_signature(sign2, tag='div', attribute="class='hej'")

    sign3='<p>In this email I use -- double hyphens or like Jan<br />\n--<br />\ndoes with his emails. That must work.<br />\n<br />\n-- <br />\nPeter Bengtsson, <a href="http://www.peterbe.com">www.peterbe.com</a> </p>'
    print "-+"*20
    print highlight_signature(sign3)
    
    sign4='''Bla bla bla
-- Peter B'''
    print "-+"*20
    print highlight_signature(sign4)
    
    sign5 = '''<p>You can also use\n<a href="http://www.issuetrackerproduct.com/Demo/What-is-StructuredText">StructuredText</a>\nif you put the word "stx" or "structuredtext" in the subjectline\nbefore the colon.</p>\n<p>-- \nPeter Bengtsson, <a href="http://www.fry-it.com">http://www.fry-it.com</a>  </p>\n'''
    print "-+"*20
    print highlight_signature(sign5)
    

def test_ValidEmailAddress():
    def T(s, expect):
        assert ValidEmailAddress(s) == expect, s
        
    T('peter@peterbe.com', True)
    T('peter @peterbe.com', False)
    T('peter+julika@peterbe.com', True)
    T("peter'julika@peterbe.com", True)
    
    invalids='''_invalid@foo.com
    invalid_@foo.com
    invalid.@foo.com
    inv@lid@foo.com
    inv#lid@foo.com
    invalid@foo..com
    invalid@-foo.com
    invalid@foo-.com
    invalid@foocom
    invalid@f#o.com
    invalid@foo.commie
    invalid@foo.c0m
    invalid@foo.b@r.com
    invalid@foo.b#r.com
    invalid@foo.
    invalid@foo_bar.com'''
    
    invalids = [x.strip() for x in invalids.split()]
    
    oks = '''ok@911.com
    ok@foo.b-r.com
    o.k@foo.com
    ok7@foo.com
    ok@dmv.ca.us
    '''
    oks = [x.strip() for x in oks.split()]

    map(lambda i: T(i, True), oks)
    
    map(lambda i: T(i, False), invalids)
    
def test_safe_html_quote():
    def x(s):
        print s
        print safe_html_quote(s)
        print
        
    x("<input name=t /> &#1234; &copy;")
    
    
def test_AwareLengthLimit():
    def T(s,L):
        print AwareLengthLimit(s, L)
        print
        
    T("Peter Bengtsson", 5)
    T("Peter Bengtsson", 25)
    T("", 100)
    T("", 0)
    T("&#111;&#222;&#333;&#444;&#555;&#666;&#777;&#888;&#999;", 10)
    T("&#111;&#222;&#333;&#444;&#555;&#666;&#777;&#888;&#999;", 6)
    T("&#111;&#222;&#333;&#444;&#555;&#666;&#777;&#888;&#999;", 5)
    T("&#111;&#222;&#333;&#444;&#555;&#666;&#777;&#888;&#999;", 4) 
    T("&#111;&#222;&#333;&#444;&#555;&#666;&#777;&#888;&#999;", 3)   
    
    
def test_ShowDescription():
    s="0201023120"
    print ShowDescription(s, 'structuredtext')

    s="0201023120."
    print ShowDescription(s, 'structuredtext')

    s="0201 023 120."
    print ShowDescription(s, 'structuredtext')
    
    s="1."
    print ShowDescription(s, 'structuredtext')
    
    s="0123123123,"
    print ShowDescription(s, 'structuredtext')
    
    
def test_timeSince():
    def T(x, y, minute_granularity=0):
        print timeSince(x,y, minute_granularity=minute_granularity)
    T(0, 0)    
    T(0, 1)
    T(0, 1.0)    
    T(0, 1.5)
    T(0, 6.9999)
    T(0, 0, 1)    
    T(0, 1, 1)
    T(0, 1.0, 1)    
    T(0, 1.5, 1)
    T(0, 6.9999, 1)
    T(0, 1/24.0, 1)
    T(0, (1/24.0)/3, 1)
    
def test_createStandaloneWordRegex():
    def T(word, text):
        print createStandaloneWordRegex(word).findall(text)
        
    T("peter", "So Peter Bengtsson wrote this")
    T("peter", "peter")
    T("peter bengtsson", "So Peter Bengtsson wrote this")
    
def test_getFindIssueLinksRegex():
    def T(text, z, t=None, p=None):
        compiled_regex = getFindIssueLinksRegex(z, t, p)
        return compiled_regex.findall(text)
    
    t='This is #1234 a text #666 like #5421 this'
    assert T(t, 4)==['#1234', '#5421'], T(t, 4)
    t='Remember Real#1234? or #9876 but not Demo#2468 or then:#1235'
    assert T(t, 4, 'Real')==['Real#1234', '#9876', '#1235'], T(t, 4, 'Real')
    t='#123 is what is starts with and ends with #432'
    assert T(t, 3)==['#123', '#432'], T(t, 3)
    t='prefixed with 000- is #000-0103 but not Real#000-0104'
    assert T(t, 4, p='000-')== ['#000-0103']
    t='In brackets (#1234) with tracker id demo like (demo#0987)'
    assert T(t, 4, 'Demo')==['#1234', 'demo#0987']
    t = '#111 or (#113) or (Real#115) but not (#1122) or (Real#8989) or (OReal#116)'
    print T(t, 3, 'real')
    t = '#111 or (#113) or (Real#115) but not (#1122) or (Demo#898)'
    print T(t, 3, ('real','demo'))
    
    
def test_html_entity_fixer():
    def T(x):
        print repr(x), "becomes", repr(html_entity_fixer(x))
    T("header & footer")
    T('& £ öå')
    
    
def test_filenameSplitter():
    def T(x):
        print x, filenameSplitter(x)
    T('Error-02September2005.log')
    T('Someting.log')
    T('Some-ting.log')
    T('issue_listing.gif')
    assert 'listing.gif' in filenameSplitter('issue_listing.gif')
    T('issue listing.gif')
    
def test_highlightCarefully():
    def T(word, text):
        hlf = lambda x: '<span class="h">%s</span>' % x
        print highlightCarefully(word, text, hlf)
        
    T("bug", '''I saw a bug on <a href=# title="a bug">this page</a>''')
    T("bug", '''I saw a <bug> on <a href=# title="a bug">this page</a>''')
    T("bug", '''I <em>saw a bug</em> on <a href=# title="a bug">this page</a>''')
    T("bug", '''<p>I saw a bug on <a href=# title="a bug">this page</a></p>''')
    
def test_iuniqify():
    def T(words, expect=None):
        print iuniqify(words)
    T(['foo','bar','Foo'])
    T(['foo','bar','foo'])
    T(['foo',None,'fOO', 4])
    
    
if __name__=='__main__':
    #test()
    #benchmark_ShowDescription()
    #test__preParseEmailString()
    #test__addhrefs()
    #test__LineIndent()
    #test_niceboolean()
    #test_highlight_signature()
    #test_ValidEmailAddress()
    #test_safe_html_quote()
    #test_AwareLengthLimit()
    #test_ShowDescription()
    #test_timeSince()
    #test_createStandaloneWordRegex()
    #test_getFindIssueLinksRegex()
    #test_html_entity_fixer()
    #test_filenameSplitter()
    #test_highlightCarefully()
    test_iuniqify()
    


