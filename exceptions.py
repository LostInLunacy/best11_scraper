""" 
    Custom-made Exceptions for the program. 
"""

class LoginException(Exception):
    """ Raises if incorrect credentials given for login. """
    def __init__(self, msg):
        super().__init__(msg)

class FileFormatException(Exception):
    """ Raises if the format of a file is incorrect.
    e.g. user_details file missing 'user' """
    def __init__(self, msg):
        super().__init__(msg)

class ArguuemntException():
    def __init__(self, msg):
        super().__init__(msg)
