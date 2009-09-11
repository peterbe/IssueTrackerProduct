from cStringIO import StringIO
from pprint import pprint

from DateTime import DateTime

from Products.PythonScripts.standard import html_quote
from Products.IssueTrackerProduct.Constants import ISSUETRACKER_METATYPE, ISSUE_METATYPE, ISSUETHREAD_METATYPE
from Products.IssueTrackerMassContainer.Constants import MASSCONTAINER_METATYPE

## Private stuff ###############################################################

def _uniqify_fast(seq, idfun=lambda x:x):
    d = {}
    for e in seq:
        d[idfun(e)] = 1
    return d.keys()
            
def _summorizeActivity(activity):
    messages = []
    for username, activities in activity.items():
        message = []
        if len(activities['added_issues']) == 1:
            message.append("added 1 issue")
        elif len(activities['added_issues']) > 1:
            message.append("added %s issues" % len(activities['added_issues']))

        if len(activities['changed_issues']):
            no_issues = len(_uniqify_fast([x.aq_parent for x in activities['changed_issues']], lambda x:x.getId()))
            if no_issues == 1:
                message.append("changed 1 issue")
            else:
                message.append("changed %s issues" % no_issues)
                
        if len(activities['followedup_issues']):
            no_issues = len(_uniqify_fast([x.aq_parent for x in activities['followedup_issues']], lambda x:x.getId()))
            if no_issues == 1:
                message.append("followed up on 1 issue")
            else:
                message.append("followed up on %s issues" % no_issues)

        print message
        messages.append("%s has " % username + ', '.join(message))
        
    return messages
        
    
        

## Public stuff ################################################################

def getRecentActivity(self, since=None):
    activity = {}
    
    if since is None:
        since = DateTime(DateTime().strftime('%Y/%m/%d')) # since midnight today
    elif type(since) is str:
        since = DateTime(since)

            
    def _init_activity(name):
        activity[name] = {
          'added_issues':[],
          'changed_issues':[],
          'followedup_issues':[],
        }
        
    
    def _addIssueActivity(issue):
        name = issue.fromname
        if not name:
            name = issue.email
        if not name:
            name = issue.acl_adder
        
        if name not in activity:
            _init_activity(name)
           
        activity[name]['added_issues'].append(issue)
        
    def _addThreadActivity(thread):
        name = thread.fromname
        if not name:
            name = thread.email
        if not name:
            name = thread.acl_adder
            
        if name not in activity:
            _init_activity(name)
            
        if thread.title.startswith('Changed status'):
            activity[name]['changed_issues'].append(thread)
        else:
            activity[name]['followedup_issues'].append(thread)
            
    def _getActivityIn(o):
        for masscontainer in o.objectValues(MASSCONTAINER_METATYPE):
            _getActivityIn(masscontainer)
        for issuetracker in o.objectValues(ISSUETRACKER_METATYPE):
            _getActivityIn(issuetracker)
        for issue in o.objectValues(ISSUE_METATYPE):
            _getActivityIn(issue)
            if issue.issuedate > since:
                _addIssueActivity(issue)
        for thread in o.objectValues(ISSUETHREAD_METATYPE):
            if thread.threaddate > since:
                _addThreadActivity(thread)
        
    _getActivityIn(self)
    
    out = StringIO()
    print >>out, "Since %s:\n" % since.strftime('%d %B %Y')

    return _summorizeActivity(activity)

    print >>out, '\n'.join(messages)
    #pprint(activity, out)
    
    return out.getvalue()
                    

def getRecentActivityHTML(self, since=None):
    res = getRecentActivity(self, since=since)
    res = '\n'.join(res)
    return "<html><body>%s</body></html>" % html_quote(res).replace('\n','<br/>\n')
