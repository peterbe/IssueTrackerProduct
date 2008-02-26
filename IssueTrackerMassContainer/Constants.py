# Peter Bengtsson <mail@peterbe.com>
# Constants for IssueTrackerMassContainer
#
from Products.IssueTrackerProduct.Constants import getEnvStr

# constants
ICON_LOCATION = 'misc_/IssueTrackerMassContainer'
MASSCONTAINER_METATYPE = 'Issue Tracker Mass Container'

# properties
#
UNICODE_ENCODING = getEnvStr('UNICODE_ENCODING_ISSUETRACKERPRODUCT', 'utf-8')

# cookies and sessions
IGNORE_COOKIEKEY = '__ignore_issuetrackers'

