__doc__="""Generic Template adder with CheckoutableTemplates

Use like this::
 
 from TemplateAdder import addTemplates2Class as aTC
 
 -----
 class MyProduct(...):
     def foo(...):

 zpts = ('zpt/viewpage', 
         ('zpt/view_index', 'index_html'),
         {'f':'zpt/dodgex', 'n':'do_give', 'd':'Some description'},
         {'f':'zpt/view_page', 'n':'view', 'o':'HTML'},
         # same thing different name on the optimize keyword
         {'f':'zpt/view_page2', 'n':'view2', 'optimize':'HTML'},
         )
 aTC(MyProduct, zpts)
 dtmls = ('manage_delete',
          ('dtml/cool_style.css','stylesheet.css','CSS'),
          )
 aTC(MyProduct, dtmls)
 dtmls_opt_all = ('dtml/page1','dtml/page2')
 aTC(MyProduct, dtmls_opt_all, optimize='HTML')

 ----
 
The second parameter (the list of files to add) can be notated
in these different ways:
  
 1) 'zpt/name_of_file'
    Expect to find a file called 'name_of_file.zpt'
   
 2) ('zpt/name_of_file','name_of_attr')
    Expect to find a file called 'name_of_file.zpt', and once 
    loaded the attribute will be called 'name_of_attr'.
    This is useful if you have dedicated 'index_html' templates
    all sitting in the same directory to be used for different
    classes.

 3) ('zpt/name_of_file','name_of_attr', 'optimzesyntax')
    Same as (2) except the last item in the tuple (or list) is the
    optimization syntax to use.

    
 4) {'f':'zpt/name_of_file'}
    Exactly the same effect as (1)
    
 5) {'f':'zpt/name_of_file', 'n':'name_of_attr'}
    Exactly the same effect as (2)
    
 6) {'f':'zpt/name_of_file', 'd':'Some description'}
    Exactly the same effect as (1) but CT template is flagged
    with 'Some description' for the description.
    
 7) {'f':'zpt/name_of_file', 'n':'name_of_attr', 'd':'Some description'}
    Exactly the same as (4) but with the description set.
 
 8) {'f':'zpt/name_of_file', 'o':'optimizesyntax'}
    Same as (4) but with the optmization syntax variable set.

    
Note:
    
    1) Use of dict-style items, always requires the 'f' key.
    
    2) The addTemplates2Class() constructor accepts a keyword argument
       like optimize='CSS' that sets the optimization argument on all
       templates defined in that tuple/list. Exceptions withing are 
       taken into account.

 
Changelog:

    0.1.10   Cosmetic improvements
    
    0.1.9    Possible to override the usage of checkoutable templates even if 
             installed
    
    0.1.8    Ability to set TEMPLATEADDER_LOG_USAGE environment variable to debug 
             which files get instanciated.
    
    0.1.7    Changed so that it can work with Zope 2.8.0
    
    0.1.6    Removed the need to pass what extension it is
    
    0.1.5    Fixed bug that if one template in 'templates' does optimize,
             then the rest had to suffer from that accept that too.

    0.1.4    If CheckoutableTemplates is not installed, the default template
             handlers are used..
    
    0.1.3    Added support of 'optimize' parameter in CheckoutableTemplates.

    0.1.2    Fixed bug in use of variable name 'template'
    
    0.1.1    Added support for description parameter in dict-
             style.
    
    0.1.0    Started
    
"""

__version__='0.1.10'


import os
import time

try:
    # >= Zope 2.12
    from App.special_dtml import DTMLFile
except ImportError:
    # < Zope 2.12
    from Globals import DTMLFile
    
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

try:
    from Products.CheckoutableTemplates import CTDTMLFile as CTD
    from Products.CheckoutableTemplates import CTPageTemplateFile as CTP
except ImportError:
    CTD = DTMLFile
    CTP = PageTemplateFile

#------------------------------------------------------------------------------

# if you set this to a filepath instead of None or False it will write down
# each template that gets used in a tab separated fashion
LOG_USAGE = os.environ.get('TEMPLATEADDER_LOG_USAGE', None)

from Constants import DISABLE_CHECKOUTABLE_TEMPLATES

class UnrecognizedExtensionError(Exception):
    pass

#------------------------------------------------------------------------------
    

def addTemplates2Class(Class, templates, extension=None, optimize=None, 
                       Globals=globals(), 
                       use_checkoutable_templates=not DISABLE_CHECKOUTABLE_TEMPLATES):
    
    if use_checkoutable_templates:
        dtml_adder = CTD
        zpt_adder = CTP
    else:
        # If you don't want to use checkoutable templates, then reassign
        dtml_adder = DTMLFile
        zpt_adder = PageTemplateFile

    root = ''
    optimize_orgin = optimize

    for template in templates:
        optimize = optimize_orgin
        description = ''
        if type(template)==type([]) or type(template)==type(()):
            if len(template)==3:
                template, dname, optimize = template
            else:
                template, dname = template
        elif type(template)==type({}):
            dname = template.get('n', template['f'].split('/')[-1])
            description = template.get('d','')
            optimize = template.get('o', template.get('optimize', optimize))
            template = template['f']
            
        else:
            # can't set 'optimize' this way
            dname = template.split('/')[-1]

        f = root = os.path.join(*template.split('/'))
        
        # now we need to figure out what extension this file is
        if template.startswith('dtml/') or template.endswith('.dtml'):
            extension = 'dtml'
        elif template.startswith('zpt/') or template.endswith('.zpt'):
            extension = 'zpt'
        else:
            # guess work
            if os.path.isfile(template + '.dtml'):
                extension = 'dtml'
            elif os.path.isfile(template + '.zpt'):
                extension = 'zpt'
                
                
        if LOG_USAGE:
            tmpl = '%s\t%s\t%s\t%s\n'
            open(LOG_USAGE.strip(),'a').write(tmpl % \
                 (Class.__name__, extension, f, description))
            

        if extension == 'zpt':
            setattr(Class, dname, 
                    zpt_adder(f, Globals, d=description, __name__=dname,
                              optimize=optimize))
                              
        elif extension == 'dtml':
            setattr(Class, dname, 
                    dtml_adder(f, Globals, d=description, optimize=optimize))
                                                    
        else:
            raise UnrecognizedExtensionError, \
                  "Unrecognized template extension %r" % extension

