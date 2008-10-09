class NotAFileError(Exception):
    pass


class IssueInputError(Exception):
    pass

class NoACLAdderError(Exception):
    """ happens when the ACL user object is not found"""
    pass

class DeprecatedError(Exception):
    pass

class AssigneeNotFoundError(Exception):
    pass

class UnmatchableError(Exception):
    pass

class ConfigurationError(Exception):
    """ something is configured wrongly or insufficiently """
    pass

class DataSubmitError(Exception):
    """happens when the data to a functional view is passed
    invalid data and it's not via the web """
    pass

class UserSubmitError(Exception):
    """happens when the user incorrectly tries to do something
    related to her authentication that doesn't work """
    pass