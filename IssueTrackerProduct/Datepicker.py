
from AccessControl import ClassSecurityInfo

try:
    # >= Zope 2.12
    from App.class_init import InitializeClass
except ImportError:
    # < Zope 2.12
    from Globals import InitializeClass



from Constants import DEFAULT_DATEPICKER_OPTIONS

class DatepickerBase:
    
    security = ClassSecurityInfo()
    
    def getDatepickerOptions(self):
        return getattr(self, 'datepicker_options', DEFAULT_DATEPICKER_OPTIONS)
    
    
    def manage_saveDatepickerOptions(self, datepicker_options, REQUEST=None):
        """save the new datepicker_options"""
        self.datepicker_options = datepicker_options.strip()
        
        if REQUEST is not None:
            url = self.getRootURL()+'/manage_DatepickerManagementForm'
            url += '?manage_tabs_message=Options+saved.'
            REQUEST.RESPONSE.redirect(url)
            
    
    
InitializeClass(DatepickerBase)    