# IssueTrackerProduct
#
# www.issuetrackerproduct.com
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

import Utils

class IssueTrackerWebservices:
    """ Define an interface of functions that can be used using webservices.
    This class must be used as a base class for the IssueTracker """
    
    def ws_countIssues(self):
        """ return how many issues there in this issuetracker """
        return self.countIssueObjects()

    
    def ws_SubmitIssue(self, title, description, fromname, email, 
                       display_format=None,
                       type=None, urgency=None, sections=None,
                       url2issue='', confidential=False, hide_me=False,
                       status=None, 
                       acl_adder=None,
                       catalog=True):
        """ return the absolute URL of the issue that is created with this 
        function. """
                     
        title = title.strip()
        description = description.strip()
        fromname = fromname.strip()
        email = email.strip()
        
        if not display_format:
            display_format = self.getDefaultDisplayFormat()
            
        if not type:
            type = self.getDefaultType()
            print ("Type defaults to %s"%type)
        elif type not in self.getTypeOptions():
            # badly spellt
            for opt in self.getTypeOptions():
                if Utils.ss(opt) == Utils.ss(type):
                    type = opt 
                    break
            
            print ("Type is set to %s"%type)
            
        if not urgency:
            urgency = self.getDefaultUrgency()
        if not sections:
            sections = self.getDefaultSections()
        elif isinstance(sections, basestring):
            sections = [sections]
        
        confidential = Utils.niceboolean(confidential)
        hide_me = Utils.niceboolean(hide_me)
        
        if not status:
            status = self.getStatuses()[0]

        submission_type = 'Webservices'
        id = self.generateID(self.randomid_length, self.issueprefix)
        self.createIssueObject(id, title, status, type, urgency, sections, 
                               fromname, email, url2issue, confidential,
                               hide_me, description, display_format, 
                               index=catalog, acl_adder=acl_adder, 
                               submission_type=submission_type)
                               
        where = self._getIssueContainer()
        return getattr(where, id).absolute_url()
    