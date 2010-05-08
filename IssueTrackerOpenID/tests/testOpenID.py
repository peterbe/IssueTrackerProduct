import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from AccessControl import User
from base import TestBase, get_test_suite
from Products.IssueTrackerProduct.IssueUserFolder import IssueUser
from Products.IssueTrackerProduct.Permissions import IssueTrackerManagerRole, IssueTrackerUserRole
class SetupError(Exception):
    pass

class TestOpenID(TestBase):
    
    def _create_openid(self, context, id='openid', title=u"OpenID",
                       create_default_providers=False):
        context.manage_addProduct['IssueTrackerOpenID']\
          .manage_addIssueTrackerOpenID(id, title=title,
                        create_default_providers=create_default_providers)
        return getattr(context, id)
    
    def _create_issuetracker_userfolder(self, context):
        if 'acl_users' in context.objectIds():
            raise SetupError("Can't create another acl_users here")
        context.manage_addProduct['IssueTrackerProduct'].manage_addIssueUserFolder()
        instance = getattr(context, 'acl_users')
        assert instance.meta_type == 'Issue Tracker User Folder'
        return instance
    
    def _create_userfolder(self, context):
        if 'acl_users' in context.objectIds():
            raise SetupError("Can't create another acl_users here")
        context.manage_addUserFolder()
        return getattr(context, 'acl_users')
    
    def test_default_providers(self):
        openid = self._create_openid(self.app,
                                    create_default_providers=True)
        
        assert 'providers' in openid.objectIds()
        assert openid.providers.objectValues()
        for provider in openid.providers.objectValues():
            assert isinstance(provider.title, unicode)
            assert provider.title
            assert provider.url
            assert provider.objectValues('Image')
    
    
    def test_finding_acl_users(self):
        """test the private method _find_acl_user()"""
        
        # create one on the root
        openid = self._create_openid(self.app)
        
        result = openid._find_acl_user(self.app.acl_users, 'peter')
        self.assertTrue(result is None)
        
        # create a user in the root acl_users folder
        peter = User.User('peter', 'secret', ['Manager'], [])
        self.app.acl_users.data['peter'] = peter
        
        result = openid._find_acl_user(self.app.acl_users, 'peter')
        self.assertTrue(isinstance(result, tuple))
        self.assertTrue(len(result) == 2)
        self.assertEqual(result[0], 'peter')
        self.assertEqual(result[1], peter)
        
        # try to find a user in something that is not a user folder
        self.app.manage_addFolder('subfolder')
        subfolder = getattr(self.app, 'subfolder')
        self.assertRaises(AttributeError, openid._find_acl_user, subfolder, 'peter')
        
        # even if the users in this userfolder doesn't have email addresses it should
        # still be possible to search by it
        result = openid._find_acl_user(self.app.acl_users, 'nope', 'test@peterbe.com')
        self.assertTrue(result is None)
        
    def test_finding_acl_users_in_issuetracker_userfolders(self):
        self.app.manage_addFolder('subfolder')
        
        subfolder = getattr(self.app, 'subfolder')
        uf = self._create_issuetracker_userfolder(subfolder)
        openid = self._create_openid(subfolder)
        
        chris = IssueUser('chris', 'secret', [IssueTrackerManagerRole], [],
                          'chris@fry-it.com', 'Chris West')
        uf.data['chris'] = chris
        # now search, remember there are two user folders now
        result = openid._find_acl_user(uf, 'chris')
        self.assertTrue(isinstance(result, tuple))
        self.assertTrue(len(result) == 2)
        self.assertEqual(result[0], 'chris')

        
        result = openid._find_acl_user(uf, email='chris@fry-it.com')
        self.assertTrue(result)

        result = openid._find_acl_user(uf, email='CHRIS@fry-it.com')
        self.assertTrue(result)

        result = openid._find_acl_user(uf, 'nothisusername', email='CHRIS@fry-it.com')
        self.assertTrue(not result)

        
    def test_traversing_acl_users(self):
        peter = User.User('peter', 'secret', ['Manager'], [])
        self.app.acl_users.data['peter'] = peter
        
        # that was easy
        # create a another folder with a user inside 
        self.app.manage_addFolder('subfolder')
        subfolder = getattr(self.app, 'subfolder')
        
        # create another userfolder in that subfolder
        uf = self._create_userfolder(subfolder)
        chris = User.User('chris', 'secret', ['Manager'], [])
        uf.data['chris'] = chris
        
        # Now create a sub folder which will be empty followed by another 
        # subfolder which will host a third user folder
        subfolder.manage_addFolder('sub2folder')
        sub2folder = getattr(subfolder, 'sub2folder')
        
        sub2folder.manage_addFolder('sub3folder')
        sub3folder = getattr(sub2folder, 'sub3folder')
        
        uf2 = self._create_userfolder(sub3folder)
        zahid = User.User('zahid', 'secret', ['Manager'], [])
        uf2.data['zahid'] = zahid
        
        openid = self._create_openid(sub3folder)
        result = openid._traverse_find_user(sub3folder, 'zahid')
        self.assertEqual(result, zahid)

        result = openid._traverse_find_user(sub3folder, 'chris')
        self.assertEqual(result, chris)
        
        result = openid._traverse_find_user(sub3folder, 'peter')
        self.assertEqual(result, peter)

def test_suite():
    return get_test_suite(globals())

if __name__ == '__main__':
    framework()


