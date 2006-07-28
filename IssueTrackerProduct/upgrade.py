#!/usr/bin/env python

"""
  The upgrade script downloads the latest IssueTrackerProduct
  from www.issuetrackerproduct.com and upgrades and installs the new
  files.
  
  Peter Bengtsson, mail@peterbe.com, (c) 2005
"""



__changes__='''
  1.2   July 2005    Ability to create a new IssueTrackerProduct if not found 
  
  1.1   July 2005    First CVSed version
'''
__version__='1.2'


import os, sys, glob, gzip, tarfile
from cStringIO import StringIO
from urllib import urlopen
import urllib2

latest_versionnr_url = "http://www.issuetrackerproduct.com/Download/getLatestVersionNumber"
latest_versionurl_url = "http://www.issuetrackerproduct.com/Download/getLatestVersionURL"

CVS_ANON_LOGIN = "cvs -d:pserver:anonymous@cvs.sourceforge.net:/cvsroot/issuetracker login"
CVS_ANON_CHECKOUT = "cvs -z3 -d:pserver:anonymous@cvs.sourceforge.net:/cvsroot/issuetracker co IssueTrackerProduct"



class VersionController:
    
    def __init__(self, home_path='.', verbose=False):
        self.home_path = home_path
        self.latest_version = _getLatestVersion()
        self.this_version = _getCurrentVersion(home_path)
        self.latest_version_url = _getLatestVersionURL()
        self.verbose = verbose
        
    def isUsingCVS(self):
        """ return true if in the home_path there is a CVS dir """
        poss_path = os.path.join(self.home_path, 'CVS')
        return os.path.exists(poss_path)
    
    def cvsUpdate(self):
        """ try to do a CVS update """
        _update = 1
        if self.verbose:
            _update = raw_input("Upgrade %s [Y/n] " % shortname)
            if _update.lower().strip() not in ('y',''):
                _update = 0
        
        if _update:
            _prev = os.path.abspath(os.curdir)
            os.chdir('..')
            os.system(CVS_ANON_LOGIN)
            os.system(CVS_ANON_CHECKOUT)
            os.chdir(_prev)
        
    def canUpgrade(self):
        """ return true if there is a newer version to download and install """
        return self.this_version != self.latest_version
    
    def upgrade(self, pretend=False):
        return self._installURL(self.latest_version_url, pretend=pretend)
    
    def _installURL(self, URL, pretend=False):
        """ given a URL to a gzipped file, download it and replace the existing 
        stuff """
        assert URL.endswith('.tgz') or URL.endswith('.tar.gz')
        
        filename = URL.split('/')[-1]
        
        # download it
        downloadfile = open(filename, 'wb')
        req = urllib2.Request(URL)
        req.add_header('User-agent', 'Upgrade script (www.issuetrackerproduct.com)')
        furl = urllib2.urlopen(req)
        downloadfile.write(furl.read())
        downloadfile.close()
        
        tar = tarfile.open(filename)
        _current_files = _listdir_fullpaths_filtered(self.home_path)
        _current_folders = _filter_whatispaths(_current_files)
        
        _current_files_copy = _current_files[:]
        for tarinfo in tar:
            
            assert tarinfo.name.startswith('IssueTrackerProduct'), \
                   "Incorrectly gzipped file"

            shortname = tarinfo.name.replace('IssueTrackerProduct/','')
            if not shortname:
                continue
            if shortname in _current_folders or \
                shortname[:-1] in _current_folders:
                continue # directories aren't important
            elif shortname.find('mainbuttons') > -1 or \
                 shortname.find('actionbuttons') > -1:
                # old crap that might be in the tgz
                continue
                
            if shortname in _current_files:
                # the default value depends on if the file has changed
                
                shortname_path = os.path.abspath(os.path.join(self.home_path, shortname))
                if tarinfo.size > 1000:
                    if tarinfo.size == len(open(shortname_path).read()):
                        _upgrade = 0
                    else:
                        _upgrade = 1
                else:
                    # if the file is less than 1000 bytes, don't do a size comparison 
                    # because it can fail with really small files like 'version.txt' 
                    # whose content can change from "0.6.12" to "0.6.13" which is the same
                    # length but different in content. Larger files and larger probability
                    # that the changes also change the total file length.
                    extracted_content = tar.extractfile(tarinfo).read()
                    if extracted_content == open(shortname_path).read():
                        _upgrade = 0
                    else:
                        _upgrade = 1                
                
                
                # if verbose, ask about each
                if self.verbose and _upgrade:
                    _upgrade = raw_input("Upgrade %s [Y/n] " % shortname)
                    if _upgrade.lower().strip() not in ('y',''):
                        _upgrade = 0
                
                if _upgrade:
                    print "U %s" % shortname
                    tar.extract(tarinfo, os.path.join(self.home_path, '..'))
            else:
                _install = 1
                if self.verbose:
                    _install = raw_input("Install %s [Y/n] " % shortname)
                    if _install.lower().strip() not in ('y',''):
                        _install = 0
                
                if _install:
                    print "I %s" % tarinfo.name.replace('IssueTrackerProduct','')
                    tar.extract(tarinfo, os.path.join(self.home_path, '..'))
                    
            if shortname in _current_files_copy:
                _current_files_copy.remove(shortname)

        this_script_filename = globals()['__file__']
        if this_script_filename in _current_files_copy:
            _current_files_copy.remove(this_script_filename)
        elif this_script_filename.replace('./','') in _current_files_copy:
            _current_files_copy.remove(this_script_filename.replace('./',''))

        if self.verbose:
            if _current_files_copy:
                print >>sys.stderr, "The following files are not needed anymore"
            for f in _current_files_copy:
                print >>sys.stderr, f
                _delete = raw_input("\tDelete %s [y/N] " % f)
                if _delete.lower().strip() not in ('y',''):
                    _delete = 1
                if _delete:
                    os.remove(f)
        
                
                    

def _filter_whatispaths(files):
    """ return a list of what is directories from a list of 
    files and directories """
    dirs = {}
    for v in files:
        splitted = os.path.split(v)
        if splitted[0]:
            dirs[splitted[0]] = 1
    return dirs.keys()
        
def _listdir_fullpaths_filtered(root, relpath=True):
    """ return a list of filepaths similar to os.path but open each
    directory. """
    all = []
    def _rejectFile(f):
        if f[-3:] in ('pyc','bak'):
            return True
        if f.endswith('~'):
            return True
        if f.startswith('#') or f.startswith('.#'):
            return True
        return False
    
    for base, dirs, files in os.walk(root):
        if base.endswith('CVS'):
            continue
        for file in files:
            if not _rejectFile(file):
                _path = os.path.join(base, file)
                
                if relpath:
                    _path = _path.replace(root,'')
                    if _path.startswith('/'):
                        _path = _path[1:]
                all.append(_path)
        
    return all
        

def _getCurrentVersion(home_path=None):
    if home_path:
        f = os.path.join(home_path, 'version.txt')
    else:
        f = 'version.txt'
    return open(f).read().strip()

def _getLatestVersion():    
    return urlopen(latest_versionnr_url).read().strip()

def _getLatestVersionURL():    
    return urlopen(latest_versionurl_url).read().strip()

#-------------------------------------------------------------------------------    



    
    
    
    

    
def cli():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose",
                      help="Each step is confirmed by the user"
                      )
  #  parser.add_option(
    options, args = parser.parse_args()
    verbose = not not options.verbose
    
    if os.path.abspath('.').endswith('IssueTrackerProduct'):
        home_path = os.path.abspath('.')
    elif 'IssueTrackerProduct' in os.listdir('.'):
        home_path = os.path.abspath(os.path.join('.','IssueTrackerProduct'))
    elif sys.argv[1:] and (sys.argv[1].endswith('IssueTrackerProduct') or sys.argv[1].endswith('IssueTrackerProduct/')):
        home_path = sys.argv[1]
    else:
        # perhaps they just want to download it!
        _mkdir = raw_input("IssueTrackerProduct folder can't be found. Create? [y/N] ")
        if _mkdir.lower().strip() in ('n',''):
            raise OSError, "IssueTrackerProduct can't be found. See(k) help."
        else:
            os.mkdir('IssueTrackerProduct')
            home_path = os.path.abspath(os.path.join('.','IssueTrackerProduct'))
            open(os.path.join(home_path, 'version.txt'),'w').write('0.0.0')
                
    vc = VersionController(home_path, 
                           verbose=verbose)
    if vc.isUsingCVS():
        vc.cvsUpdate()
    elif vc.canUpgrade():
        vc.upgrade()
    else:
        print >>sys.stderr, "Latest version (%s) already installed" % vc.latest_version
    
    return 0 # everything went fine


if __name__=='__main__':
    sys.exit(cli())
