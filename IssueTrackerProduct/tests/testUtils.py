import unittest

import sys, os
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
        

from Products.IssueTrackerProduct import Utils
from DateTime import DateTime

class IssueLinkFinderTestCase(unittest.TestCase):
    
    def _find(self, text, zfill, trackerid=None, prefix=None):
        c = Utils.getFindIssueLinksRegex(zfill, trackerid, prefix)
        return c.findall(text)
        
    def testBasic(self):
        t='This is #1234 issue'
        self.assertEqual(self._find(t, 4), ['#1234'])
        
    def testBasicMultiple(self):
        t='This is #1234 issues #5421 test'
        self.assertEqual(self._find(t, 4), ['#1234', '#5421'])
        
    def testWithTrackerid(self):
        t='Remember Real#1234? or #9876 but not Demo#2468 or then:#1235'
        self.assertEqual(self._find(t, 4, 'real'), ['Real#1234', '#9876','#1235'])

    def testWithTrackerid2(self):
        t='Remember Real#1234? or #9876 but not Demo#2468 or then:#1235'
        self.assertEqual(self._find(t, 4, 'DEMO'), ['#9876','Demo#2468','#1235'])

    def testPrefixed(self):
        t='prefixed with 000- is #000-0103 but not Real#000-0104'
        self.assertEqual(self._find(t, 4, prefix='000-'), ['#000-0103'])
        
    def testPrefixedWithTrackerid(self):
        t='prefixed with 000- is #000-0103 but not Real#000-0104'
        self.assertEqual(self._find(t, 4, 'real', prefix='000-'), 
                         ['#000-0103','Real#000-0104'])
                         
    def testWithBracketsNoTrackerid(self):
        t='In brackets (#1234) with tracker id demo like (demo#0987)'
        self.assertEqual(self._find(t, 4), ['#1234'])
        
    def testWithBracketsWithTrackerid(self):
        t='In brackets (#1234) with tracker id demo like (demo#0987)'
        self.assertEqual(self._find(t, 4, 'DeMo'), ['#1234','demo#0987'])
        
    def testLinebroken(self):
        t = 'First there is #00000\nThen there is #99999'
        self.assertEqual(self._find(t, 5, ''), ['#00000', '#99999'])
        
    def testStringstart(self):
        t = '#111 or (#113) or (Real#115) but not (#1122) or (Real#8888) or (OReal#116)'
        self.assertEqual(self._find(t, 3, 'real'), ['#111','#113','Real#115'])
        
    def testWithTrackeridS(self):
        t='Theres Real#1234 and theres Demo#1235'
        self.assertEqual(self._find(t, 4, ('DeMo','real')), 
                         ['Real#1234', 'Demo#1235'])


class TimeSinceTestCase(unittest.TestCase):
    
    def testYears1A(self):
        t1 = DateTime('2005/01/01')
        # 2004 was a leap year
        t2 = DateTime('2003/01/01')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "2 years and 1 day")

    def testYears1B(self):
        t1 = DateTime('2004/01/01')
        t2 = DateTime('2002/01/01')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "2 years")
        
    def testYears2A(self):
        t1 = DateTime('2005/01/01')
        # 2004 was a leap year
        t2 = DateTime('2003/01/02')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "2 years")
        
    def testYears2B(self):
        t1 = DateTime('2004/01/02')
        t2 = DateTime('2002/01/01')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "2 years and 1 day")
        
    def testYears3A(self):
        t1 = DateTime('2005/02/01')
        # 2004 was a leap year
        t2 = DateTime('2003/01/01')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "2 years and 1 month and 2 days")
        
    def testYears3B(self):
        t1 = DateTime('2004/02/01')
        # 2004 was a leap year
        t2 = DateTime('2002/01/01')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "2 years and 1 month and 1 day")
        
    def testMonths(self):
        t1 = DateTime('2005/04/01')
        t2 = DateTime('2005/05/01')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "1 month")
        
    def testDays1(self):
        t1 = DateTime('2005/04/01')
        t2 = DateTime('2005/04/02')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "1 day")

    def testDays2(self):
        t1 = DateTime('2005/04/01')
        t2 = DateTime('2005/04/03')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "2 days")
        
        
    def testHours1(self):
        t1 = DateTime('2005/04/01 12:00')
        t2 = DateTime('2005/04/01 13:00')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "1 hour")
        
    def testHours2(self):
        t1 = DateTime('2005/04/01 12:00')
        t2 = DateTime('2005/04/01 14:00')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "2 hours")
        
    def testHours3(self):
        # the timeSince() function drops the hour
        # part if the difference is in days
        t1 = DateTime('2005/04/01 12:00')
        t2 = DateTime('2005/04/02 14:00')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "1 day")
        
    def testMinutes1(self):
        # the timeSince() function drops the hour
        # part if the difference is in days
        t1 = DateTime('2005/04/01 12:00')
        t2 = DateTime('2005/04/01 12:30')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, 0)
        
    def testMinutes2(self):
        # the timeSince() function drops the hour
        # part if the difference is in days
        t1 = DateTime('2005/04/01 12:00')
        t2 = DateTime('2005/04/01 12:30')
        difference = Utils.timeSince(t1, t2, minute_granularity=1)
        self.assertEqual(difference, "30 minutes")
        
    def testMinutes2(self):
        # the timeSince() function drops the hour
        # part if the difference is in days
        t1 = DateTime('2005/04/01 12:00')
        t2 = DateTime('2005/04/01 12:01')
        difference = Utils.timeSince(t1, t2, minute_granularity=1)
        self.assertEqual(difference, "1 minute")
        
    def testWeek1(self):
        # use the week notation
        t1 = DateTime('2005/04/01')
        t2 = DateTime('2005/04/08')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "1 week")
        
    def testWeek2(self):
        # use the week notation
        t1 = DateTime('2005/04/01')
        t2 = DateTime('2005/04/15')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "2 weeks")
        
    def testWeek2point1(self):
        # use the week notation
        t1 = DateTime('2005/04/01')
        t2 = DateTime('2005/04/16')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "2 weeks and 1 day")
        
    def testWeek3(self):
        # use the week notation
        t1 = DateTime('2005/04/01')
        t2 = DateTime('2005/04/22')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, "3 weeks")
        
    def test2Weeks(self):
        # use the week notation
        t1 = DateTime('2005/12/08 15:54:18.715 GMT')
        t2 = DateTime('2006/01/06 10:26:18.571 GMT')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, '4 weeks')
        
    def test2Weeks(self):
        # use the week notation
        t1 = DateTime('2005/11/12 00:08:30.937 GMT')
        t2 = DateTime('2006/01/09 09:47:07.123 GMT')
        difference = Utils.timeSince(t1, t2)
        self.assertEqual(difference, '1 month and 4 weeks')
        
    def testLongDistanceDates(self):
        # If the result contains a year part, month part, week part
        # and day part the number of parts is controlled by
        # @max_no_sections (default 3)
        t1 = DateTime('2004/11/12 00:08:30.937 GMT')
        t2 = DateTime('2006/05/01 09:47:07.123 GMT')
        difference_default = Utils.timeSince(t1, t2)
        self.assertEqual(difference_default, '1 year and 5 months and 2 weeks')
        
        difference_2_parts = Utils.timeSince(t1, t2, max_no_sections=2)
        self.assertEqual(difference_2_parts, '1 year and 5 months')

        difference_99_parts = Utils.timeSince(t1, t2, max_no_sections=99)
        self.assertEqual(difference_99_parts, '1 year and 5 months and 2 weeks and 6 days')
        
        
class SplitTermsTestCase(unittest.TestCase):
    
    def testBasic1(self):
        inp = "peter anders bengt"
        exp = ['peter','anders','bengt']
        self.assertEqual(Utils.splitTerms(inp), exp)
        
    def testUnbalanced(self):
        inp = 'peter "bengt anders bengtsson'
        exp = ['peter','"bengt','anders','bengtsson']
        self.assertEqual(Utils.splitTerms(inp), exp)
        
    def testOneQuote(self):
        inp = 'peter "bengt anders" bengtsson'
        exp = ['peter','"bengt anders"','bengtsson']
        self.assertEqual(Utils.splitTerms(inp), exp)
        
    def testTwoQuotes(self):
        inp = 'peter "bengt anders" bengtsson "and again" peter'
        exp = ['peter','"bengt anders"','bengtsson',
               '"and again"','peter']
        self.assertEqual(Utils.splitTerms(inp), exp)
        
    def testEndingQuote(self):
        inp = 'peter "bengt anders"'
        exp = ['peter','"bengt anders"']
        self.assertEqual(Utils.splitTerms(inp), exp)
        
    def testStartingQuote(self):
        inp = '"bengt anders" bengtsson'
        exp = ['"bengt anders"','bengtsson']
        self.assertEqual(Utils.splitTerms(inp), exp)        
        

class AddParam2URLTestCase(unittest.TestCase):
    
    def testBasic(self):
        inpu, inpp = "http://www.com", {'msg':'foo bar'}
        exp = "http://www.com?msg=foo%20bar"
        self.assertEqual(Utils.AddParam2URL(inpu, inpp), exp)
        
    def testBasicPlus(self):
        inpu, inpp = "http://www.com", {'msg':'foo bar'}
        exp = "http://www.com?msg=foo+bar"
        self.assertEqual(Utils.AddParam2URL(inpu, inpp, plus_quote=1), exp)
        

class StandaloneWordRegex(unittest.TestCase):
    
    def _find(self, word, text):
        return Utils.createStandaloneWordRegex(word).findall(text)
    
    def testOneAgainstOne(self):
        word = "peter"
        text = "Peter"
        exp = ['Peter']
        self.assertEqual(self._find(word, text), exp)
    
    def testOneAgainstSentence(self):
        word = "peter"
        text = "Peter Bengtsson"
        exp = ['Peter']
        self.assertEqual(self._find(word, text), exp)
        
    def testSentenceAgainstOne(self):
        word = "Peter Bengtsson"
        text = "peter"
        exp = []
        self.assertEqual(self._find(word, text), exp)
        
    def testSentenceAgainstSentenceI(self):
        word = "Peter Bengtsson"
        text = "Peter Bengtsson"
        exp = [text]
        self.assertEqual(self._find(word, text), exp)
        
    def testSentenceAgainstSentenceII(self):
        word = "PETER BENGTSSON"
        text = "peter bengtsson"
        exp = ['peter bengtsson']
        self.assertEqual(self._find(word, text), exp)
        
    def testFred(self):
        word = 'Fred Damberger'
        text = 'Fred Damberger'
        exp = [text]
        self.assertEqual(self._find(word, text), exp)
        
        
class ValidEmailAddressTestCase(unittest.TestCase):
    
    def testPositives(self):
        T = lambda email: self.assertEqual(Utils.ValidEmailAddress(email), True)
        T('peter@fry-it.com')
        T(u'peter@fry-it.com')
        T('peter+julika@peterbe.com')
        T("peter'julika@peterbe.com")
        T('o.k@foo.com')
        T('ok@911.com')
        
    def testNegatives(self):
        F = lambda email: self.assertEqual(Utils.ValidEmailAddress(email), False)
        F('ASD@GHJG.7')
        F('peter @fry-it.com')
        F('invalid@foo.c0m')
        F(u'invalid@foo.c0m')
        F('invalid@foo.b@r.com')
        F('invalid@f#o.com')
        F('invalid.@foo.com')
        F('invalid@foo.')
        

class UnicodifyAsciifyStrings(unittest.TestCase):
    
    def test_unicodify(self):
        """ unicodify turns any string into unicode """
        func = Utils.unicodify
        
        # ascii to unicode
        s = 'ok'
        self.assertEqual(func(s), u'ok')
        self.assertTrue(isinstance(func(s), unicode))
        
        # unicode to unicode
        s = u'ok'
        self.assertEqual(func(s), u'ok')
        self.assertTrue(isinstance(func(s), unicode))
        
        # ascii with unicode within
        s = '\xa3'
        self.assertEqual(func(s), u'\xa3')
        self.assertTrue(isinstance(func(s), unicode))
        
        # unicode with unicode within
        s = u'\xa3'
        self.assertEqual(func(s), u'\xa3')
        self.assertTrue(isinstance(func(s), unicode))
        

    def test_asciify(self):
        """ asciify turns any string into an ascii string """
        func = Utils.asciify
        
        # ascii to ascii
        s = 'ok'
        self.assertEqual(func(s), 'ok')
        self.assertTrue(isinstance(func(s), str))
        
        # unicode to ascii
        s = u'ok'
        self.assertEqual(func(s), 'ok')
        self.assertTrue(isinstance(func(s), str))
        
        # uncode with unicode characters in it
        s = u'\xa3'
        # since default error hander is 'xmlcharrefreplace'
        self.assertEqual(func(s), '&#163;')
        self.assertEqual(func(s, 'replace'), '?')
        self.assertEqual(func(s, 'ignore'), '')
        self.assertTrue(isinstance(func(s), str))
        
        # ascii with unicode in it
        s = '\xa3'
        # since default error hander is 'xmlcharrefreplace'
        self.assertEqual(func(s), '&#163;')
        self.assertEqual(func(s, 'replace'), '?')
        self.assertEqual(func(s, 'ignore'), '')
        self.assertTrue(isinstance(func(s), str))
        
    
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(IssueLinkFinderTestCase))
    suite.addTest(makeSuite(TimeSinceTestCase))
    suite.addTest(makeSuite(SplitTermsTestCase))
    suite.addTest(makeSuite(AddParam2URLTestCase))
    suite.addTest(makeSuite(StandaloneWordRegex))
    suite.addTest(makeSuite(ValidEmailAddressTestCase))
    suite.addTest(makeSuite(UnicodifyAsciifyStrings))
    
    return suite
    
if __name__ == '__main__':
    framework()
        

