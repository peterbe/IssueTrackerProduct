from setuptools import setup, find_packages

name = 'IssueTrackerProduct'
version = '0.14.3.dev0'

setup(name='IssueTrackerProduct',
      version=version,
      description="Bug/issue tracker for Zope2.",
      long_description=open("README.txt").read() + \
                       open("docs/CHANGES.txt").read(),
      classifiers=[
        "Framework :: Zope2",
        "Programming Language :: Python",
      ],
      keywords='Zope tracker issue bug',
      author='Peter Bengtsson',
      author_email='mail@peterbe.com',
      url='https://github.com/sureshvv/IsssueTrackerProduct',
      license='GPL',
      packages=['IssueTrackerProduct',
                'IssueTrackerMassContainer',
                'IssueTrackerOpenID',
               ],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'setuptools',
      ],
)
