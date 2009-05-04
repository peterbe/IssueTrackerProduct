# -*- coding: iso-8859-1 -*
##
## <peter@fry-it.com>
##

import re

import sys, os
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from base import TestBase

#------------------------------------------------------------------------------
#
# Some constants
#


#------------------------------------------------------------------------------



class SearchTestCase(TestBase):
    """
    Test searching, indexing, spellcorrection, catalog stuff
    """
    
    def test_unicode_search(self):
        """you should be able to enter an issue in unicode, then search for any
        of the words you wrote and find it"""
        
        title = u"Les opposants au r\xc3\xa9gime tha\xc3\xaflandais"
        description = u"\xc3\xa0 l'occupation du si\xc3\xa8g\n\n"\
                      u"Au Parlement, un air d'union sacr\xc3\xa9e face \xc3\xa0"
        
        tracker = self.folder.tracker
        request = self.app.REQUEST
        request.set('title', title)
        request.set('fromname', u'B\xc3\xa9b')
        request.set('email', u'email@address.com')
        request.set('description', description)
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        
        tracker.SubmitIssue(request)
        
        # it should be possible to display it
        issue = tracker.getIssueObjects()[0]
        html = issue.index_html(self.app.REQUEST)
        self.assertTrue(isinstance(html, unicode))
        self.assertTrue(u'r\xc3\xa9gime' in html)
        
        # now search for one of those words
        q = u'R\xc3\xa9GIME'
        search_results = tracker._searchCatalog(q)
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0], issue)

        highlit = re.compile('<span class="q_highlight">(.*?)</span>')

        # if you view the issue with a q variable set,
        # it should highlight the text
        self.app.REQUEST.set('q', u'air')
        html = issue.index_html(self.app.REQUEST)
        self.assertEqual(highlit.findall(html), [u'air'])
        
        # and do the same with a search with non-ascii characters
        self.app.REQUEST.set('q', u'R\xc3\xa9GIME')
        html = issue.index_html(self.app.REQUEST)
        self.assertEqual(highlit.findall(html), [u'r\xc3\xa9gime'])
        
    
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(SearchTestCase))
    return suite
    
if __name__ == '__main__':
    framework()
        

