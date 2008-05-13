from zope.interface import Interface, Attribute


class ICustomField(Interface):
    
    id = Attribute("ID")
    title = Attribute("Title")
    input_type = Attribute("Input type")
    default_value = Attribute("Default value") # TALES
    mandatory = Attribute("Mandatory")
    validator = Attribute("Validator") # TALES
    javacript_events = Attribute("Javascript events")
    massage_value = Attribute("Massage value") # TALES
    javascript_block = Attribute("Javascript block")
    css_block = Attribute("CSS block")
    
    def testValidValue(value):
        """ return a tuple of (valid or not [bool], message [unicode]) if the value
        passes all the validation expressions (assuming the field has any)
        """
        