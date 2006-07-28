##parameters=issue

# You're given an issue as the first parameter on this report
# script. Your job, with this script, is to look at this issue 
# object and decide if you want to show it or not. Either return
# True or False at the end of this script.


# example code
if issue.countThreads() > 1:
    return True


# default thing to do is to NOT include the issue
return False