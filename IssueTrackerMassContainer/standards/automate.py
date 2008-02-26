## Script (Python) "automate"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
"""
Automate process script.
Change at own will. The code below is just an example of what can be 
done in this script.
"""

request = context.REQUEST
response = request.RESPONSE
session = request.SESSION

for o in context.objectValues('Issue Tracker'):
    o.UpdateEverything()
    
return "done at %s"%context.ZopeTime()

