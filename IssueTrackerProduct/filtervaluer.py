from DateTime import DateTime
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from Products.ZCatalog.CatalogAwareness import CatalogAware

from Constants import FILTEROPTION_METATYPE

class FilterValuer(SimpleItem, PropertyManager, CatalogAware):
    """ a simple class that helps us remember a set of filter options. """
    
    meta_type = FILTEROPTION_METATYPE
    
    _properties = ({'id':'title',         'type':'ustring', 'mode':'w'},
                   {'id':'adder_fromname','type':'ustring', 'mode':'w'},
                   {'id':'adder_email',   'type':'string', 'mode':'w'},
                   {'id':'acl_adder',     'type':'string', 'mode':'w'},
                   {'id':'key',           'type':'string', 'mode':'r'},
                   {'id':'mod_date',      'type':'date',   'mode':'w'},
                   {'id':'filterlogic',   'type':'string', 'mode': 'w'},
                   {'id':'statuses',      'type':'ulines',  'mode': 'w'},
                   {'id':'sections',      'type':'ulines',  'mode': 'w'},
                   {'id':'urgencies',     'type':'ulines',  'mode': 'w'},
                   {'id':'types',         'type':'ulines',  'mode': 'w'},
                   {'id':'due',           'type':'ulines',  'mode': 'w'},
                   {'id':'assignee',      'type':'string',  'mode': 'w'},
                   {'id':'fromname',      'type':'ustring', 'mode': 'w'},
                   {'id':'email',         'type':'string', 'mode': 'w'},
                   )

    manage_options = PropertyManager.manage_options
    
    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.acl_adder = ''
        self.adder_fromname = u''
        self.adder_email = ''
        self.key = '' # Used by people who don't have a name
        self.custom_filters = {}
        self.mod_date = DateTime()
        self.usage_count = 0
        
    def getId(self):
        return self.id
    
    def getTitle(self, length_limit=None):
        title = self.title
        if length_limit is not None:
            if len(title) > length_limit:
                return title[:length_limit] + '...'
        return title
    
    def getModificationDate(self):
        """ return when it was last changed """
        return self.mod_date
    
    def getKey(self):
        return getattr(self, 'key', None)
        
    def set(self, key, value):
        if not key in [x['id'] for x in self._properties]:
            raise ValueError, "Unrecognized property key %r" % key
        self.__dict__[key] = value
        
    def set_custom_fields_filter(self, custom_filters):
        self.custom_filters = custom_filters

        
    def populateRequest(self, request):
        """ put all the filter values in this class into self.REQUEST """
        rset = request.set

        rset('Filterlogic', self.filterlogic)
        rset('f-statuses', self.statuses)
        rset('f-sections', self.sections)
        rset('f-urgencies', self.urgencies)
        rset('f-types', self.types)
        rset('f-fromname', self.fromname)
        rset('f-email', self.email)
        if getattr(self, 'due', None):
            rset('f-due', self.due)
        if getattr(self, 'assignee', None):
            rset('f-assignee', self.assignee)
        
        for field_id, value in getattr(self, 'custom_filters', {}).items():
            rset('f-%s' % field_id, value)
        
        
    def incrementUsageCount(self):
        self.usage_count = self.getUsageCount() + 1
	
    def updateModDate(self):
        self.mod_date = DateTime()
        
    def getUsageCount(self):
        """ return how many times this has been used """
        return getattr(self, 'usage_count', 0)


    ##
    ## Indexing
    ##
    
    def index_object(self):
        """A common method to allow Findables to index themselves."""
        idxs = ['meta_type','acl_adder','adder_fromname','adder_email',
                'key','mod_date','path','title']
        path = '/'.join(self.getPhysicalPath())
        catalog = self.getFilterValuerCatalog()
        catalog.catalog_object(self, path, idxs=idxs)
        
    def unindex_object(self):
        catalog = self.getFilterValuerCatalog()
        if catalog is not None:
            catalog.uncatalog_object('/'.join(self.getPhysicalPath()))
        

