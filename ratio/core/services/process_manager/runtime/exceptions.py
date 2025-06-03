

class MappingError(Exception):
    """Exception raised for errors during object mapping"""
    def __init__(self, message: str, path: str = None):
        self.path = path

        self.message = f"Mapping Error at '{path}': {message}" if path else f"Mapping Error: {message}"

        super().__init__(self.message)