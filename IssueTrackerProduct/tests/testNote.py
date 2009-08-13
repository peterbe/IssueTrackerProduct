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

class NoteTestCase(TestBase):
    """
    Test adding, finding rendering notes
    """
    
    def test_note_creation_basic(self):
        """create a note inside an issue and to a followup in that issue."""
        
        # make an issue
        title = u"Fat people"
        description = u"bla bla bla"
        
        tracker = self.folder.tracker
        request = self.app.REQUEST
        request.set('title', title)
        request.set('fromname', u'B\xc3\xa9b')
        request.set('email', u'email@address.com')
        request.set('description', description)
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        
        tracker.SubmitIssue(request)
        issue = tracker.getIssueObjects()[0]
        
        from Products.IssueTrackerProduct.Note import IssueNote
        # create a note inside this issue
        note = IssueNote('1', u'A note about something',
                         u"Some note about something which is a long string",
                         u'B\xc3\xa9b',
                         'email@address.com'
                         )
        issue._setObject('1', note)
        note = issue._getOb('1')
        note.index_object()
        
        self.assertEqual(note.getFromname(),
                         u'B\xc3\xa9b')
        self.assertEqual(note.getEmail(),
                         u'email@address.com')
        self.assertEqual(note.getACLAdder(), '')
        
        self.assertEqual(list(issue.getNotes()),
                         [note])
        
        
    def test_note_creation_by_issue(self):
        """test to let the issue create the note"""
        # make an issue
        title = u"Fat people"
        description = u"bla bla bla"
        
        tracker = self.folder.tracker
        request = self.app.REQUEST
        request.set('title', title)
        request.set('fromname', u'B\xc3\xa9b')
        request.set('email', u'email@address.com')
        request.set('description', description)
        request.set('type', tracker.getDefaultType())
        request.set('urgency', tracker.getDefaultUrgency())
        
        tracker.SubmitIssue(request)
        issue = tracker.getIssueObjects()[0]
        
        # use the view createNote()
        issue.createNote("Bla bla bla")
        note = issue.getNotes()[0]
        self.assertEqual(note.getComment(), u"Bla bla bla")
        self.assertTrue(type(note.getComment()) is unicode)
        
        # can't set getFromname() and getEmail() because the request isn't
        # completed these things aren't set in the cookies
        #self.assertEqual(note.getFromname(), u'B\xc3\xa9b')
        #self.assertEqual(note.getEmail(), 'email@address.com')
        self.assertEqual(note.getThread(), None)
        


        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(NoteTestCase))
    return suite
    
if __name__ == '__main__':
    framework()
        


