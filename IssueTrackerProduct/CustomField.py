# IssueTrackerProduct
#
# Peter Bengtsson <mail@peterbe.com>
# License: ZPL
#

# python
import os, sys, re
import logging
from sets import Set
from types import InstanceType

# Zope
from zope.interface import implements
from persistent.mapping import PersistentMapping
from OFS.Folder import Folder
from Globals import DTMLFile, InitializeClass, DevelopmentMode
from AccessControl import ClassSecurityInfo
from Acquisition import aq_inner, aq_parent, aq_base
from DateTime import DateTime
from DateTime.DateTime import DateError

# Product
import Utils
from Utils import unicodify
from TemplateAdder import addTemplates2Class
from interfaces import ICustomField
from Constants import *
from Permissions import VMS
from Expression import Expression, getExprContext

#----------------------------------------------------------------------------

DEFAULT_TEXTAREA_COLS = 70
DEFAULT_TEXTAREA_ROWS = 10

logger = logging.getLogger('IssueTrackerProduct.CustomField')

OK_input_types = ('text', 'password', 'checkbox', 'textarea', 'select',
                  'radio', 'file')
                  
OK_python_types = (
      'boolean',
      'date',
      'float',
      'int',
      'lines',
      'long',
      'string',
      'ulines',
      'ustring',
)

CORE_ATTRIBUTES = ('title','input_type','extra_css','extra_js','options',
                   'mandatory','options_expression','python_type',
                   'visibility_expression',
                   'include_in_filter_options',
                   )

                   
#----------------------------------------------------------------------------

def _flatten_lines(nested_list):
    all = []
    for item in nested_list:
        if isinstance(item, (tuple, list)):
            all.extend(_flatten_lines(item))
        else:
            all.append(item)
    return all
    
#----------------------------------------------------------------------------

manage_addCustomFieldForm = DTMLFile('dtml/addCustomField', globals())

def manage_addCustomField(self, oid, title=u'', input_type='text', python_type='ustring',
                          extra_css=u'', extra_js=u'', mandatory=False,
                          include_in_filter_options=False, 
                          options=[],
                          create_in_folder=False,
                          add_and_edit=False, REQUEST=None):
    """ This adds a custom field object inside a CustomFieldFolder.
    
    A custom field is best added inside a custom field folder object but it's
    not a must. 
    """
    
    # by default the place to put it is in self
    container = self
    if create_in_folder:
        # either find or create a CustomFieldFolder
        if self.meta_type == CUSTOMFIELDFOLDER_METATYPE:
            # great!
            pass
        elif self.objectValues(CUSTOMFIELDFOLDER_METATYPE):
            container = self.objectValues(CUSTOMFIELDFOLDER_METATYPE)[0]
        else:
            # create one and put it in that
            container = manage_addCustomFieldFolder(self)
            
    if input_type != 'text':
        # check that it's a valid on
        if not input_type in OK_input_types:
            raise ValueError, "invalid input_type"
        
        #if input_type in ('select','radio'):
        #    assert options, "No options set when using select"
        
    if not python_type in OK_python_types:
        raise ValueError, "Invalid python type"

    instance = CustomField(oid, title=unicode(title), input_type=input_type,
                           python_type=python_type, 
                           extra_css=unicode(extra_css).strip(),
                           extra_js=unicode(extra_js).strip(),
                           mandatory=bool(mandatory), 
                           options=options,
                           include_in_filter_options=include_in_filter_options,
                           )
    container._setObject(oid, instance)
    
    object = container._getOb(oid)
    object._prepareByType()
    
    if REQUEST is not None:
        url = container.absolute_url() + '/manage_main'
        if add_and_edit:
            url = object.absolute_url() + '/manage_field'
        REQUEST.RESPONSE.redirect(url)
    else:
        return object
    

    
def list_to_flat(sequence):
    items = []
    for item in sequence:
        if isinstance(item, (list, tuple)):
            items.append(u'%s | %s' % (item[0], item[1]))
        else:
            items.append(item)
            
    return u'\n'.join(items)

def flat_to_list(string):
    # fist convert it to a decent list
    flat_list = [x.strip() for x in string.splitlines() if x.strip()]
    items = []
    for item in flat_list:
        if len(item.split('|')) == 2:
            items.append([x.strip() for x in item.split('|')])
        else:
            items.append(item.strip())
            
    return items
            
    
    

#----------------------------------------------------------------------------


class CustomField(Folder):
    """
    A CustomField is an object that becomes automatically included
    as part of the Add Issue page. The ID of the custom field becomes the
    name of the input. So if the ID is 'foo' the input rendered becomes
    <input name="foo">
    
    This class defines:
        
    Type of input
    ---------------------------------------------------------------------------
    
      You can select one of the following:
          text, textarea, password, hidden, select, checkbox, radio or file
          
      Depending on which one you select you'll specify parameters such as 
      'cols' (for type 'textarea' of course) or size. By having first selected
      a type, the field will autogenerate some default parameters that you can
      later modify.
    
    
    Default value
    ---------------------------------------------------------------------------
    
      The default value can be either a simple string inputted or it can be a
      reference to something else callable that will get the default value and
      this is done with a TALES expression. 
    
    Being mandatory or optional
    ---------------------------------------------------------------------------
    
      By default every field is optional but by making it mandatory, you'll 
      most likely going to have to specify a validation because sometimes it's 
      not as simple as checking that a value is boolean or not (e.g. bool(''))
    
    Validation
    ---------------------------------------------------------------------------
    
      This is where you specify either a reference to a script or a TALES 
      expression that will work out if a particular value is valid or not. 
    
    Javascript events hooks (onchange, onclick, onfocus, onblur)
    ---------------------------------------------------------------------------
    
      You'll be responsible for what you write in the values for these. The 
      values must be available javascript functions.
    
    Setting persistent values on issues
    ---------------------------------------------------------------------------
    
      (This is actually implemented in IssueTrackerProduct/IssueTracker.py)
    
      When saving the issue, we'll add an attribute to the issue like this::
          
          <id of custom field>: <value at input>
          
      This will pass through the validation a second time but unlike the first
      time, if the validation fails this time a hard error is raised. The type
      of the value is by default a unicode string or what else is appropriate 
      based on the input type. 
      You can specify an expression that will massage the input before it's 
      saved. So, suppose you want to save it as a floating point number you
      enter this expression::
          
          python:float(value)
          
    Getting persistent values on issues
    ---------------------------------------------------------------------------
    
      (This is actually implemented in IssueTrackerProduct/IssueTracker.py)

      You can ask the issuetracker for the value of a custom field simply by
      specifying the ID of the custom field and an optional default value. 
      Quite possibly you'll have an issuetracker where issues were added before
      the creation of the custom field so it'll be important to supply a 
      default value.
    
    Additionally loaded Javascript and CSS
    ---------------------------------------------------------------------------
    
      You get an area for entering the Javascript and the CSS and this is 
      automatically loaded on the Add Issue page. If you in your input of this
      (on the first line) enter a name of a file or DTML Method/Document that
      exists, that is instead rendered.
      The input can also be a valid URL if it looks relative and valid.
    
    """
    
    implements(ICustomField)
    
    meta_type = CUSTOMFIELD_METATYPE
    
    manage_options = ({'label':'Manage', 'action':'manage_field'}, 
                      {'label':'Validation', 'action':'manage_validation'},) +\
                      Folder.manage_options
    

    _properties = ({'id':'title',         'type': 'ustring', 'mode':'w'},
                   {'id':'disabled',      'type': 'boolean', 'mode':'w'},
                   {'id':'python_type',   'type': 'selection', 'mode':'w',
                    'select_variable':'getOKPythonTypes'},
                   {'id':'include_in_filter_options',  'type': 'boolean', 'mode':'w'},
                   )
    
    security = ClassSecurityInfo()
    
    def __init__(self, id, title=u'', input_type="text", python_type='ustring',
                 extra_js=u'', extra_css=u'', mandatory=False, 
                 options=[], options_expression='', visibility_expression='',
                 include_in_filter_options=False):
        self.id = str(id)
        self.title = title
        self.input_type = input_type
        self.python_type = python_type
        self.attributes = PersistentMapping()
        self.extra_css = extra_css
        self.extra_js = extra_js
        self.mandatory = mandatory
        self.options = options
        self.options_expression = options_expression
        self.disabled = False
        self.visibility_expression = visibility_expression
        self.include_in_filter_options = include_in_filter_options
        
    ##
    ## Attributes of the object
    ##
        
    def getId(self):
        return self.id
    
    def getTitle(self):
        return self.title
    
    def isMandatory(self):
        return self.mandatory
        
    def isDisabled(self):
        return self.disabled
    
    def getOptions(self):
        return self.options
    
    def getInputType(self):
        return self.input_type
    
    def getPythonType(self):
        return self.python_type
    
    security.declareProtected(VMS, 'getOptionsFlat')
    def getOptionsFlat(self):
        """ return the list of options with a | pipe sign to split tuples """
        return list_to_flat(self.getOptions())
    
    def getOptionsExpression(self):
        """ true if it looks like a TALES expression """
        return self.options_expression
    
    def getVisibilityExpression(self):
        return self.visibility_expression
    
    def includeInFilterOptions(self):
        return self.include_in_filter_options

    ##
    ## Special Zope magic
    ##
    
    def getOKPythonTypes(self):
        return OK_python_types
    
    ##
    ## Special massaging on the class attributes
    ##
    
    def _prepareByType(self):
        """ set all the appropriate default bits and pieces by the 
        input_type. For example, if the input type is 'textarea' set a
        default cols and rows.
        """
        if self.input_type == 'textarea':
            self.attributes['cols'] = DEFAULT_TEXTAREA_COLS
            self.attributes['rows'] = DEFAULT_TEXTAREA_ROWS
            
        elif self.input_type == 'checkbox':
            pass
           #if 'value' in self.attributes:
           #     del self.attributes['value']
            
        elif self.input_type == 'radio':
            if 'value' in self.attributes:
                del self.attributes['value']

        elif self.input_type == 'file':
            if 'value' in self.attributes:
                del self.attributes['value']
                
    
    ##
    ## Rendering stuff
    ##
            
        
    def render(self, *value, **extra_attributes):
        """ return the tag (e.g. <textarea>) and any other accompanying
        HTML stuff. 
        """
        
            
        if value and isinstance(value[0], InstanceType) and \
          value[0].__class__.__name__ =='HTTPRequest':
            # this method has been called with REQUEST as the value parameter.
            # Note that it's still a list or tuple but convert it to the actual value.
            value = value[0].form.get(self.getId(), None)
            if value is None:
                value = ()
            else:
                value = (value,) # make sure it's a tuple
                
        out = []
        if DevelopmentMode:
            out.append(u'<!--CustomField: %s -->' % self.getId())
            
            if self.isDisabled():
                logger.warn("A disabled custom field (%s) is rendered" % self.absolute_url_path())
            
        # take out some extra keywords from the extra_attributes
        skip_extra_css = extra_attributes.pop('skip_extra_css', False)
        skip_extra_js = extra_attributes.pop('skip_extra_js', False)
            
        if self.extra_css and not skip_extra_css:
            out.append(self.render_extra_css())
        if self.extra_js and not skip_extra_js:
            out.append(self.render_extra_js())
            
        out.append(self.render_tag(*value, **extra_attributes))
        
        return '\n'.join(out)
            
    def render_tag(self, *value, **extra_attributes):
        """ return a piece of unicode HTML that """
        
        assert len(value) <= 1, "Can't pass more than one argument as value"
        
        
        inner = []
        attributes = {}
        # notice the order of these update() calls! It matters
        
        name_prefix = extra_attributes.pop('name_prefix','')
        
        # core attributes
        dom_id = self.attributes.get('dom_id', 'id_%s' % self.getId())
        attributes.update({'name':self._wrapPythonTypeName(name_prefix),
                           'id':dom_id,
                           'title':self.getTitle()
                           })

        # saved attributes
        attributes.update(dict(self.attributes))
        
        # extra on rendering attributes
        attributes.update(extra_attributes)

        # filler is a dict that we will use to render the template
        filler = {}
        
        if self.input_type == 'textarea':
            template = u'<textarea %(inner)s>%(value)s</textarea>'
            
            v = None
            if value:
                v = value[0] # from the argument
            elif 'value' in attributes:
                v = attributes.pop('value')
            
            if v:
                filler['value'] = Utils.safe_html_quote(v)
            else:
                filler['value'] = u''
                
        elif self.input_type == 'select':
            template = u'<select %(inner)s>\n%(all_options)s\n</select>'
            all_options = []
            
            v = []
            if value:
                v = value[0]
            elif 'value' in attributes:
                v = attributes.pop('value')
            if not isinstance(v, (tuple, list)):
                v = [v]
                    
            for option in self.getOptionsIterable():
                if isinstance(option, (tuple, list)):
                    value, label = option
                else:
                    value, label = option, option
                    
                if value in v:
                    tmpl = u'<option value="%s" selected="selected">%s</option>'
                else:
                    tmpl = u'<option value="%s">%s</option>'
                    
                all_options.append(tmpl % (value, label))

            filler['all_options'] = '\n'.join(all_options)
            
        elif self.input_type == 'radio':
            # special case
            if not self.getOptionsIterable():
                template = u'ERROR: No options'
            else:
                template = u'%(all_inputs)s'
                all_inputs = []
                
                v = None
                if value:
                    v = value[0] # from the argument
                    
                elif 'value' in attributes:
                    v = attributes.pop('value')
                    
                special_attributes = ''
                inner = []
                for k, v2 in attributes.items():
                    if k in ('id',):
                        continue
                    inner.append('%s="%s"' % (k, v2))
                if inner:
                    special_attributes = ' ' + ' '.join(inner)

                for option in self.getOptions():
                    if isinstance(option, (tuple, list)):
                        value, label = option
                    else:
                        value, label = option, option
                        
                    if value == v:
                        tmpl = u'<input type="radio" value="%s" checked="checked"%s /> %s<br />'
                    else:
                        tmpl = u'<input type="radio" value="%s"%s/> %s<br />'
                    all_inputs.append(tmpl % (value, special_attributes, label))
                    
                filler['all_inputs'] = '\n'.join(all_inputs)
                
        elif self.input_type == 'checkbox':
            # another special case
            
            # If there are no options you can work this like a normal text input
            if not self.getOptions():
                template = u'<input type="checkbox" %(inner)s />'
                
            else:
                # crap!
                template = u'%(all_inputs)s'
                all_inputs = []
                
                v = None
                if value:
                    v = value[0] # from the argument
                elif 'value' in attributes:
                    v = attributes.pop('value')
                    
                special_attributes = ''
                inner = []
                for k, v2 in attributes.items():
                    if k in ('id',):
                        continue
                    inner.append('%s="%s"' % (k, v2))
                if inner:
                    special_attributes = ' ' + ' '.join(inner)

                for option in self.getOptions():
                    if isinstance(option, (tuple, list)):
                        value, label = option
                    else:
                        value, label = option, option

                    if value == v:
                        tmpl = u'<input type="checkbox" value="%s" checked="checked"%s /> %s<br />'
                    else:
                        tmpl = u'<input type="checkbox" value="%s"%s/> %s<br />'
                    all_inputs.append(tmpl % (value, special_attributes, label))
                
                    
                filler['all_inputs'] = '\n'.join(all_inputs)

        elif self.input_type == 'password':
            
            template = u'<input type="password" %(inner)s />'

        elif self.input_type == 'file':
            template = u'<input type="file" %(inner)s />'

        else: # type text
            template = u'<input %(inner)s />'
            
            
        if not (self.input_type == 'radio' or (self.input_type == 'checkbox' and self.getOptions())):
            
            if value and self.input_type not in ('select',):
                if  value and value[0]:
                    # This overrides the default value
                    attributes['value'] = value[0]
            
            for key, val in sorted(attributes.items()):
                inner.append('%s="%s"' % (key, val))
                
            filler['inner'] = ' '.join(inner)

        return template % filler

    def __str__(self):
        return str(self.render())
    
    def _wrapPythonTypeName(self, prefix=''):
        """ if name is 'age' and python_type is 'int' then return
        'age:int'.
        If the type is unicode type, add the encoding
        """
        name, python_type = self.getId(), self.python_type
        
        # add the prefix
        name = '%s%s' % (prefix, name)

        if self.input_type == 'file':
            # exception
            return name
        
        if python_type in ('ustring','ulines'):
            return '%s:%s:%s' % (name, UNICODE_ENCODING, python_type)
        elif python_type == 'string':
            return name
        else:
            return '%s:%s' % (name, python_type)
    
    def render_extra_css(self):
        """ return a piece of HTML that loads the CSS.
        If it looks like the attribute self.extra_css is a URI,
        return a <link rel="stylesheet"> tag instead.
        """
        css = self.extra_css
        if len(css.splitlines()) == 1 and (css.startswith('http') or css.startswith('/') or css.endswith('.css')):
            return u'<link rel="stylesheet" type="text/css" href="%s" />' % css
        elif css:
            return u'<style type="text/css">\n%s\n</style>' % css
        else:
            return u''
        
    def render_extra_js(self):
        """ return a piece of HTML that loads the javascript.
        If it looks like the attribute self.extra_js is a URI,
        return a <script src="..."> tag instead.
        """
        js = self.extra_js
        if len(js.splitlines()) == 1 and (js.startswith('http') or js.startswith('/') or js.endswith('.js')):
            return u'<script type="text/javascript" src="%s"></script>' % js
        elif js:
            return u'<script type="text/javascript">\n%s\n</script>' % js
        else:
            return u''

        
    security.declareProtected(VMS, 'preview_render')
    def preview_render(self, *value, **extra_attributes):
        """ wrapper on render() that is able to cut out some of the verbose stuff
        from the render output.
        """
        html = self.render(*value, **extra_attributes)
        return html
    
    
    ##
    ## TALES expression for options
    ##
    
    def getOptionsIterable(self):
        """ return a list of options """
        if self.getOptionsExpression():
            ec = self._getExprContext(self)
            ex = Expression(self.options_expression)
            return list(ex(ec))
        else:
            return self.getOptions()

    def _getExprContext(self, object, extra_namespaces={}):
        return getExprContext(self, object, extra_namespaces=extra_namespaces)
    
    def _valid_options_expression(self):
        """ return true if self.options_expression is valid 
        otherwise raise an error. 
        """
        ec = self._getExprContext(self)
        ex = Expression(self.options_expression)
        iterable = ex(ec)
        
        if isinstance(iterable, (list, tuple)):
            # each item should be unicodeable and 
            # every item must something
            for item in iterable:
                if isinstance(item, (tuple, list)):
                    key, value = item
                    if key and not value:
                        value = key
                else:
                    key, value = item, item
                    if not item:
                        return False
        
            # an iterable we can't find anything wrong with
            return True

        # default is not to pass
        return False
    
    
    ##
    ## Validation 
    ##
    
    def getValidationExpressions(self):
        return self.objectValues(CUSTOMFIELD_VALIDATION_EXPRESSION_METATYPE)
    
    security.declarePrivate('testValidValue')
    def testValidValue(self, value):
        """ return a tuple of (valid or not [bool], message [unicode]) if the value
        passes all the validation expressions (assuming the field has any)
        """
        # check the python type
        if self.python_type == 'ustring':
            # should be possible to do this
            try:
                unicode(value)
            except TypeError:
                return False, u"Not a unicode string"
        elif self.python_type == 'int':
            try:
                int(value)
            except ValueError:
                return False, u"Not an integer number"
        elif self.python_type == 'float':
            try:
                float(value)
            except ValueError:
                return False, u"Not a floating point number"
        elif self.python_type == 'long':
            try:
                long(value)
            except ValueError:
                return False, u"Not a long integer number"
        elif self.python_type == 'date':
            try:
                if isinstance(value, basestring):
                    DateTime(value)
            except DateError:
                return False, u"Not a valid date"
        elif self.python_type == 'ulines':
            if isinstance(value, basestring):
                try:
                    [unicode(x) for x in value.splitlines()]
                except ValueError:
                    return False, u"Not a list of unicode strings"
            elif value is not None:
                value = _flatten_lines(value)
                try:
                    [unicode(x) for x in value]
                except ValueError:
                    return False, u"Not a list of unicode strings"
        elif self.python_type == 'lines':
            if isinstance(value, basestring):
                try:
                    [str(x) for x in value.splitlines()]
                except ValueError:
                    return False, u"Not a list of strings"
            elif value is not None:
                value = _flatten_lines(value)
                try:
                    [str(x) for x in value]
                except ValueError:
                    return False, u"Not a list of strings"
                

        # check each TALES expression
        for ve in self.getValidationExpressions():
            ec = self._getExprContext(self, extra_namespaces=dict(value=value))
            ex = Expression(ve.expression)
            if not bool(ex(ec)):
                return False, ve.message
        
        # by default no validation expression made it invalid
        return True, None

    ##
    ## Working with the persistent attributes
    ##
    
    def getCoreAttribute(self, *key_and_default):
        """ return the value of this attribute. If len(@key_and_default) = 2 is
        the second one is a default value. If not don't fall back on a default.
        """
        if not len(key_and_default) in (1,2):
            raise ValueError, "Call getCoreAttribute(key [,default])"
        
        if len(key_and_default) == 1:
            return self.attributes[key_and_default[0]]
        else:
            return self.attributes.get(key_and_default[0], key_and_default[1])
        
    security.declareProtected(VMS, 'getCoreAttributeKeys')
    def getCoreAttributeKeys(self):
        return list(self.attributes.keys())

    
    security.declareProtected(VMS, 'getCoreAttributeKeyLabel')
    def getCoreAttributeKeyLabel(self, key, html_ok=False):
        """ return a string that explains what the key is.
        The resturn string can contain HTML.
        """
        if key == 'dom_id':
            if html_ok:
                return u'<abbr title="DOM element ID, not Zope object ID">DOM ID</abbr>'
            else:
                return u'DOM ID' 
            
        if key.startswith('on') and re.findall('on\w+', key):
            return u'on' + key[2:].capitalize()
            
        if key in ('rows','cols'):
            return u'Textarea %s' % key
            
        
        return key.title()
    
    def getCoreAttributeKeySuggestions(self):
        """ return a list of suggestions of attribute keys you might want to add """
        suggestions = ['style','size', 'dom_id', 'onchange', 'onkeypress', 'onclick',
                       'onfocus', 'onblur', 'value',
                       ]
        # add more               
        if self.input_type == 'textarea':
            suggestions.append('cols')
            suggestions.append('rows')
        elif self.input_type == 'select':
            suggestions.append('multiple')
            
        # reduce already used ones
        suggestions = [x for x in suggestions if x not in self.attributes]
        
        # sort them by their labels
        suggestions = [(self.getCoreAttributeKeyLabel(x), x) for x in suggestions]
        suggestions.sort()
        
        # return just the keys
        return [x[1] for x in suggestions]

    
    def getCoreAttributeKeyName(self, key):
        """ return what the suitable name for the key should be a input tag
        """
        return u'%s:ustring' % key
                       
    
    def getDeleteableAttributeKeys(self):
        """ return a list of keys of attributes you can delete """
        all = Set(list(self.attributes.keys()))
        not_ = Set(CORE_ATTRIBUTES)
        return list(all - not_)

        
        
    ##
    ## Modifying the custom field
    ##
    
    security.declareProtected(VMS, 'manage_saveFieldProperties')
    def manage_saveFieldProperties(self, input_type=None, python_type=None,
                                   title=None, mandatory=False,
                                   extra_css=None, extra_js=None,
                                   options=None, options_expression=None,
                                   visibility_expression=None,
                                   include_in_filter_options=False,
                                   REQUEST=None,
                                   **settings):
        """ saving changes via the web """
        if input_type is not None:
            different = input_type != self.input_type
            
            if not input_type in OK_input_types:
                raise ValueError, "invalid input_type"
            self.input_type = input_type
            if different:
                self._prepareByType()
                
        if python_type is not None:
            assert python_type in OK_python_types, "Invalid Python type (%r)" % python_type
            self.python_type = python_type
                
        if title is not None:
            self.title = unicode(title)
            
        self.mandatory = bool(mandatory)
        self.include_in_filter_options = bool(include_in_filter_options)
            
        if extra_css is not None:
            self.extra_css = unicode(extra_css).strip()
            
        if extra_js is not None:
            self.extra_js = unicode(extra_js).strip()
            
        if options_expression is not None:
            self.options_expression = str(options_expression).strip()
            
            if self.options_expression:
                assert self._valid_options_expression(), "Invalid expression"
                
        if visibility_expression is not None:
            self.visibility_expression = visibility_expression
            
        if options is not None:
            self.options = flat_to_list(options)
            
        if not settings and REQUEST is not None:
            settings = self.REQUEST.form

        # I don't like the pattern but it'll have to do for now
        for key, value in settings.items():
            if key not in CORE_ATTRIBUTES:
                self.attributes[key] = value
                
                
        if REQUEST is not None:
            msg = 'Changes saved'
            url = self.absolute_url()+'/manage_field'
            url += '?manage_tabs_message=%s' % Utils.url_quote_plus(msg)
            REQUEST.RESPONSE.redirect(url)
            

    security.declareProtected(VMS, 'manage_addFieldProperty')
    def manage_addFieldProperty(self, key=None, new_key=None, REQUEST=None):
        """ add a new attribute property """
        if not key and not new_key:
            raise ValueError, "must pass 'key' OR 'new_key'"
        
        if new_key:
            key = new_key.strip()
            
        key = str(key)
        
        self.attributes[key] = u''
        
        if REQUEST is not None:
            msg = 'Field added'
            url = self.absolute_url()+'/manage_field'
            url += '?manage_tabs_message=%s' % Utils.url_quote_plus(msg)
            url += '#field-%s' % key
            REQUEST.RESPONSE.redirect(url)

    security.declareProtected(VMS, 'manage_deleteFieldProperty')
    def manage_deleteFieldProperty(self, key, REQUEST=None):
        """ delete a field property """
        del self.attributes[key]
        
        if REQUEST is not None:
            msg = 'Attribute deleted'
            url = self.absolute_url()+'/manage_field'
            url += '?manage_tabs_message=%s' % Utils.url_quote_plus(msg)
            REQUEST.RESPONSE.redirect(url)

            
    security.declareProtected(VMS, 'manage_addValidationExpression')
    def manage_addValidationExpression(self, expression, message=u'', REQUEST=None):
        """ add a new validation expression """
        # check that it's not complete rubbish
        expression = str(expression).strip()
        message = unicode(message).strip()
        if not expression:
            raise ValueError, "Expression can't be empty"
        
        # XXX: Got to figure out a better way to test the expression without a 
        # arbitrary value like this
        ## test it
        #ec = self._getExprContext(self, extra_namespaces=dict(value='123'))
        #ex = Expression(expression)
        #try:
        #    ex(ec)
        #except Exception, m:
        #    raise ValueError, m
        
        c = len(self.objectIds(CUSTOMFIELD_VALIDATION_EXPRESSION_METATYPE)) + 1
        oid = 'validation_%s' % c
        while base_hasattr(self, oid):
            c += 1
            oid = 'validation_%s' % c
        
        instance = ValidationExpression(oid, expression, message)
        self._setObject(oid, instance)
        
        if REQUEST is not None:
            msg = 'Expression added'
            url = self.absolute_url()+'/manage_validation'
            url += '?manage_tabs_message=%s' % Utils.url_quote_plus(msg)
            REQUEST.RESPONSE.redirect(url)
            

    security.declareProtected(VMS, 'manage_deleteValidationExpression')
    def manage_deleteValidationExpression(self, id, REQUEST=None):
        """ delete a validation expression """
        assert id in self.objectIds(CUSTOMFIELD_VALIDATION_EXPRESSION_METATYPE)
        
        self.manage_delObjects([id])
        
        if REQUEST is not None:
            msg = 'Expression delete'
            url = self.absolute_url()+'/manage_validation'
            url += '?manage_tabs_message=%s' % Utils.url_quote_plus(msg)
            REQUEST.RESPONSE.redirect(url)
        
    
    security.declareProtected(VMS, 'manage_editValidationExpression')
    def manage_editValidationExpression(self, id, expression, message, 
                                        delete=False, REQUEST=None):
        """ change a validation expression object """
        assert id in self.objectIds(CUSTOMFIELD_VALIDATION_EXPRESSION_METATYPE)
        obj = getattr(self, id)
        
        if delete:
            return self.manage_deleteValidationExpression(id, REQUEST=REQUEST)
        
        expression = str(expression).strip()
        message = unicode(message).strip()
        if not expression:
            raise ValueError, "Expression can't be empty"
        
        # test it
        ec = self._getExprContext(self, extra_namespaces=dict(value='123'))
        ex = Expression(expression)
        try:
            ex(ec)
        except Exception, m:
            raise ValueError, m
        
        obj.expression = expression
        obj.message = message
        
        
        if REQUEST is not None:
            msg = 'Expression changed'
            url = self.absolute_url()+'/manage_validation'
            url += '?manage_tabs_message=%s' % Utils.url_quote_plus(msg)
            REQUEST.RESPONSE.redirect(url)

            
    ##
    ## Showing values of custom fields
    ##
    
    def showValue(self, value):
        """ return an HTML representation of a field for this value. """
        if self.input_type in ('radio','checkbox'):
            for option in self.getOptions():
                if isinstance(option, (tuple, list)):
                    save_value, show_value = option
                else:
                    save_value, show_value = option, option
                    
                if save_value == value:
                    return show_value
            
        if self.python_type in ('lines','ulines'):
            return ', '.join(value)
        elif self.input_type == 'password':
            return '*' * max(1, len(value))
        elif self.input_type == 'file':
            return '<a href="%s">%s</a>' % (value, value.split('/')[-1])
            #as_obj = self.restrictedTraverse(value)
            return '<a href="%s">%s</a>' % (as_obj.absolute_url_path(), as_obj.getId())
                
        else:
            return value
            
        
    
zpts = (
  'zpt/customfield/manage_field',
  'zpt/customfield/manage_validation',
  'zpt/customfield/index_html',
  
)
addTemplates2Class(CustomField, zpts)
  
security = ClassSecurityInfo()
security.declareProtected(VMS, 'index_html')
security.declareProtected(VMS, 'manage_field')
security.declareProtected(VMS, 'manage_validation')
security.apply(CustomField)


InitializeClass(CustomField)


#----------------------------------------------------------------------------
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager

class ValidationExpression(SimpleItem, PropertyManager):
    """ a validation expression is a very simple object that consists of two
    things: expression (str) and message (unicode)
    """
    meta_type = CUSTOMFIELD_VALIDATION_EXPRESSION_METATYPE
    def __init__(self, id, expression, message):
        self.id = str(id)
        self.expression = str(expression)
        self.message = unicode(message)
        
    

#----------------------------------------------------------------------------

from IssueTracker import  ZopeOrderedFolder


## https://bugs.launchpad.net/zope2/+bug/142399
def safe_hasattr(obj, name, _marker=object()):
    """Make sure we don't mask exceptions like hasattr().
    
    We don't want exceptions other than AttributeError to be masked,
    since that too often masks other programming errors.
    Three-argument getattr() doesn't mask those, so we use that to
    implement our own hasattr() replacement.
    """
    return getattr(obj, name, _marker) is not _marker

def base_hasattr(obj, name):
    """Like safe_hasattr, but also disables acquisition."""
    return safe_hasattr(aq_base(obj), name)


manage_addCustomFieldFolderForm = DTMLFile('dtml/addCustomFieldFolder', globals())
def manage_addCustomFieldFolder(self, oid='custom_fields', 
                                title=u'Custom fields', 
                                input_type='text',
                                REQUEST=None):
    """ add a new CustomFieldFolder """
    instance = CustomFieldFolder(oid, title=title)
    self._setObject(oid, instance)
    
    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(self.absolute_url()+'/manage_main')
    else:
        return self._getOb(oid)

    
class CustomFieldFolder(ZopeOrderedFolder):
    """ A CustomFieldFolder is just a folder to put all the custom fields
    but in order so that when rendering the Add Issue page we will know which
    order to put them in. Plus 
    
    """
    
    meta_type = CUSTOMFIELDFOLDER_METATYPE
    
    security = ClassSecurityInfo()
    
    #icon = '%s/customfieldfolder.png' % ICON_LOCATION
    
    def __init__(self, id, title=u'', extra_css='', extra_js=''):
        self.id = str(id)
        self.title = title
        
        
        

InitializeClass(CustomFieldFolder)    


#----------------------------------------------------------------------------

class CustomFieldsIssueTrackerBase:
    """
    This class is plugged into IssueTracker class so that the IssueTracker
    can do batch operations over all findable custom field objects in places
    like the. 
    """
    
    def _getExprContext(self, object, extra_namespaces={}):
        return getExprContext(self, object, extra_namespaces=extra_namespaces)
    
    
    def getCustomFieldObjects(self, field_ids_filter=None):
        """ return an iterable list of all custom fields that we can reach.
        
        The parameter @field_ids_filter can be a list, tuple or a function that
        limits which fields should be returned. 
        """
        fields = []
        folder = getattr(self, 'custom_fields', None)
        if folder is not None and folder.meta_type == CUSTOMFIELDFOLDER_METATYPE:
            fields.extend([x for x in folder.objectValues(CUSTOMFIELD_METATYPE)
                             if not x.disabled])
                             
        # add any found here
        fields.extend([x for x in self.objectValues(CUSTOMFIELD_METATYPE)
                         if not x.disabled])
                         
        if isinstance(field_ids_filter, basestring):
            field_ids_filter = [field_ids_filter]

        if callable(field_ids_filter):
            fields = [x for x in fields if field_ids_filter(x)]
        elif field_ids_filter:
            fields = [x for x in fields if x.getId() in field_ids_filter]
            
        visible_fields = []
        for field in fields:
            if field.getVisibilityExpression():
                # evaluate the expression
                ec = self._getExprContext(self)
                ex = Expression(field.getVisibilityExpression())
                if not bool(ex(ec)):
                    continue
            
            visible_fields.append(field)
            
        if isinstance(field_ids_filter, (tuple, list)):
            # respect the order
            fields_dict = {}
            for field in visible_fields:
                fields_dict[field.getId()] = field
            visible_fields = []
            for each in field_ids_filter:
                visible_fields.append(fields_dict[each])

        return visible_fields
    
    
    def getCustomFieldsCombinedCSS(self, field_ids_filter=None):
        """ return a combined chunk of CSS for all custom fields """
        chunks = []
        for field in self.getCustomFieldObjects(field_ids_filter=field_ids_filter):
            if field.extra_css:
                chunks.append(field.render_extra_css())
                
        return '\n'.join(chunks)
    
    
    def manage_fix(self):
        " legacy fixer "
        for field in self.getCustomFieldObjects():
            if not hasattr(field, 'include_in_filter_options'):
                field.include_in_filter_options = False
            if not hasattr(self, 'visibility_expression'):
                self.visibility_expression = ''
                
        return "done"
    
    
    
class CustomFieldsIssueBase:
    """ Helping the IssueTrackerIssue class do batch operations on custom 
    fields. 
    """
    
    def setCustomFieldData(self, field, key, value):
        """ append this to self.custom_fields_data (dict).
        The parameter @field is the custom field object. 
        """
                
        if field.input_type == 'file':
            # upload the file into the issue and change @value to the id
            value.read(1)
            if self._isFile(value):
                # upload it!
                folder_id = 'upload-%s' % field.getId()
                if not safe_hasattr(self, folder_id):
                    self.manage_addFolder(folder_id)
                container = getattr(self, folder_id)
                ids = self._uploadFileattachments(container, [value])
                ids = ['%s/%s' % (folder_id, x) for x in ids]
                value = ids[0]
            else:
                # nothing worth saving
                return 
        elif field.python_type == 'int':
            value = int(value)
        elif field.python_type == 'float':
            value = float(value)
        elif field.python_type == 'long':
            value = long(value)
        elif field.python_type == 'lines':
            if isinstance(value, tuple):
                value = list(value)
            elif isinstance(value, basestring):
                value = [value]
            else:
                # due to way Zope's cast handles <selects>
                # with name "foo:ulines" you get
                # ['one', ['two']]
                value = _flatten_lines(value)
                assert isinstance(value, list), "value not a list"
            # every item should be a str
            value = [str(x) for x in value]
        elif field.python_type == 'ulines':
            if isinstance(value, tuple):
                value = list(value)
            elif isinstance(value, basestring):
                value = [value]
            else:
                # due to way Zope's cast handles <selects>
                # with name "foo:ulines" you get
                # ['one', ['two']]
                value = _flatten_lines(value)                
                assert isinstance(value, list), "value not a list"
            # every item should be a str
            value = [unicodify(x) for x in value]
        elif field.python_type == 'date':
            if isinstance(value, basestring):
                value = DateTime(value)
        elif field.python_type == 'boolean':
            value = bool(value)
        elif field.python_type == 'ustring':
            value = unicodify(value)
        else:
            value = str(value)
                
        data = getattr(self, 'custom_fields_data', None)
        if data is None:
            self.custom_fields_data = PersistentMapping()
            
        self.custom_fields_data[key] = value
            

    def getCustomFieldsData(self, field_ids_filter=None):
        """ return a list of dict that contain the {field, key, value} """
        values = {}
        for key, value in getattr(self, 'custom_fields_data', {}).items():
            values[key] = value
        
        if not values:
            return []
        # return the key, value pairs together with the field in an ordered manner.
        # This also makes sure we don't return data for which there is no field
        fields = []
        for field in self.getRoot().getCustomFieldObjects(field_ids_filter=field_ids_filter):
            value = values.get(field.getId(), None)
            if value is None:
                continue
            fields.append(dict(field=field, value=value, key=field.getId()))

        return fields
        
    def getCustomFieldData(self, key, default=None):
        """ get custom field data """
        data = getattr(self, 'custom_fields_data', {})
        return data.get(key, default)
    
    