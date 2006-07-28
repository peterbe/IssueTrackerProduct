## Script (Python) "SendInboundEmailConfirm"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=issueobject, emailaddress, fromname=None
##title=
##
""" 
This script lets you return an email to someone who has submitted
an issue via email. 
Feel free to change it if you're unhappy with the predefined text.
"""

request = context.REQUEST
mailhost = context.MailHost

issueurl = issueobject.absolute_url()

subject = "%s: Your issue has been added"%context.getRoot().getTitle()
msg = """Thank you for submitting this issue via email.

Your issue can be found here:
%s

Regards, %s"""%(issueurl, context.sitemaster_name)

if fromname is not None:
    mTo = "%s <%s>"%(fromname, emailaddress)
else:
    mTo = emailaddress

mFrom = "%s <%s>"%(context.sitemaster_name, 
                   context.sitemaster_email)

br = "\r\n"
body = string.join(("From: %s"%mFrom,
             "To: %s"%mTo,
             "Subject: %s"%subject,
             "",msg),br)

try:
    context.sendEmail(body, mTo, mFrom, subject)
    return 1
except:
    return 0