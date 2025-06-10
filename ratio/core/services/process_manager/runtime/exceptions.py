"""
Exceptions for Process Manager Runtime
"""

class MappingError(Exception):
    """Exception raised for errors during object mapping"""
    def __init__(self, message: str, path: str = None):
        """
        Initialize the MappingError with a message and an optional path.

        Keyword arguments:
        message -- the error message to be displayed
        path -- the path where the error occurred (default: None)
        """
        self.path = path

        self.message = f"Mapping Error at '{path}': {message}" if path else f"Mapping Error: {message}"

        super().__init__(self.message)