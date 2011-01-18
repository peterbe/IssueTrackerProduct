
from Testing import ZopeTestCase

ZopeTestCase.installProduct('MailHost')
ZopeTestCase.installProduct('ZCatalog')
ZopeTestCase.installProduct('ZCTextIndex')
ZopeTestCase.installProduct('SiteErrorLog')
ZopeTestCase.installProduct('PythonScripts')
ZopeTestCase.installProduct('IssueTrackerProduct')


# Open ZODB connection
app = ZopeTestCase.app()

# Set up sessioning objects
ZopeTestCase.utils.setupCoreSessions(app)

# Close ZODB connection
ZopeTestCase.close(app)




class TestBase(ZopeTestCase.ZopeTestCase):

    def dummy_redirect(self, *a, **kw):
        self.has_redirected = a[0]
        if kw:
            print "*** Redirecting to %r + (%s)" % (a[0], kw)
        else:
            print "*** Redirecting to %r" % a[0]

    def afterSetUp(self):
        # install an issue tracker
        dispatcher = self.folder.manage_addProduct['IssueTrackerProduct']
        dispatcher.manage_addIssueTracker('tracker', 'Issue Tracker')

        # install an error_log
        dispatcher = self.folder.manage_addProduct['SiteErrorLog']
        dispatcher.manage_addErrorLog()


        # if you set this override you won't be able to do a transaction.get().commit()
        # in the unit tests.
        #self.mexpenses.http_redirect = self.dummy_redirect

        request = self.app.REQUEST
        sdm = self.app.session_data_manager
        request.set('SESSION', sdm.getSessionData())

        #self.has_redirected = False
        self._mockMailHost()



    def _mockMailHost(self):
        context = self.folder.tracker
        context.sendEmail = fake_sendEmail



    def set_cookie(self, key, value, expires=365, path='/',
                   across_domain_cookie_=False,
                   **kw):

        self.app.REQUEST.cookies[key] = value


snatched_emails = []
def fake_sendEmail(msg, to, fr, subject, **kw):
    snatched_emails.append(
      dict(kw, msg=msg, to=to, fr=fr, subject=subject)
    )
    return True # that it worked



from Products.IssueTrackerProduct.IssueTracker import IssueTracker
from Products.IssueTrackerProduct.Issue import IssueTrackerIssue

def functional_fake_sendEmail(self, msg, to, fr, subject, **kw):
    return fake_sendEmail(msg, to, fr, subject, **kw)
#    return TestBase.fake_sendEmail(self, msg, to, fr, subject, **kw)

#    return TestBase.snatched_emails.append(
#      dict(kw, msg=msg, to=to, fr=fr, subject=subject)
#    )

#def foo(self, *args, **kwargs):
IssueTracker.sendEmail = functional_fake_sendEmail
