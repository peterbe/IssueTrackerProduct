import sys
from unittest import TestSuite, makeSuite
from Testing import ZopeTestCase


ZopeTestCase.installProduct('CookieCrumbler')
ZopeTestCase.installProduct('IssueTrackerProduct')
ZopeTestCase.installProduct('IssueTrackerOpenID')


# Open ZODB connection
app = ZopeTestCase.app()
        
# Set up sessioning objects
ZopeTestCase.utils.setupCoreSessions(app)

#
ZopeTestCase.utils.setupSiteErrorLog(app)

# Set up example applications
#if not hasattr(app, 'Examples'):
#    ZopeTestCase.utils.importObjectFromFile(app, examples_path)
        
# Close ZODB connection
ZopeTestCase.close(app)


def get_test_suite(globals_):
    suite = TestSuite()
    
    for class_ in [x for x in globals_.values()
                   if type(x) is type(TestBase) and \
                      issubclass(x, TestBase) and \
                      not x is TestBase]:
        suite.addTest(makeSuite(class_))
    return suite

#class TestBaseMetaClass(type):
#    def __new__(cls, name, bases, attrs):
#        new_class = super(TestBaseMetaClass, cls).__new__(cls, name, bases, attrs)
#        
#        if name != 'TestBase':
#            model_module = sys.modules[new_class.__module__]
#            try:
#                all_test_classes[model_module.__name__].append(name)
#            except KeyError:
#                all_test_classes[model_module.__name__] = [name]
#        return new_class
                                    
                

class TestBase(ZopeTestCase.ZopeTestCase):
    pass#__metaclass__ = TestBaseMetaClass

