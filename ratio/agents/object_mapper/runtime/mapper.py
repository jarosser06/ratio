import re
import logging

from typing import Any, Dict, List, Callable, Optional, Union


class MappingError(Exception):
    """Exception raised for errors during object mapping"""
    def __init__(self, message: str, path: str = None):
        self.path = path

        self.message = f"Mapping Error at '{path}': {message}" if path else f"Mapping Error: {message}"

        super().__init__(self.message)


def map_function(array: List, template: Dict) -> List:
    """
    Map function that transforms an array using a template.

    Keyword arguments:
        array: The source array
        template: The mapping template (e.g., {"key": "item.X"})

    Returns:
        List of transformed objects
    """
    result = []

    for item in array:
        output = {}
        for key, path in template.items():
            # Extract the attribute name from "item.X" format
            if isinstance(path, str) and path.startswith("item."):
                attr = path[5:]  # Remove "item."

                if attr in item:
                    output[key] = item[attr]

                else:
                    raise MappingError(f"Attribute '{attr}' not found in array item")

            else:
                output[key] = path  # static value

        result.append(output)

    return result


def sum_function(array: List, item_path: str) -> Union[int, float]:
    """
    Sum function that calculates the sum of values in an array.

    Keyword arguments:
    array - The source array
    item_path - The path to the attribute to sum (e.g., "item.X")

    Returns:
        Sum of the values
    """
    total = 0

    if not isinstance(array, list):
        raise MappingError("First argument must be an array")

    # Extract the attribute name from "item.X" format
    if item_path.startswith("item."):
        attr = item_path[5:]  # Remove "item."

        for item in array:
            if attr in item:
                val = item[attr]

                if isinstance(val, (int, float)):
                    total += val

                else:
                    raise MappingError(f"Attribute '{attr}' is not a number")

            else:
                raise MappingError(f"Attribute '{attr}' not found in array item")

    else:
        raise MappingError("Item path must be in format 'item.X'")

    return total


def join_function(array: List, separator: str) -> str:
    """
    Join function that combines an array of values into a string.

    Keyword arguments:
    array - The source array
    separator - The string to use as a separator

    Returns:
        Joined string
    """
    if not isinstance(array, list):
        raise MappingError(f"First argument must be an array, got {type(array)}")

    # If array contains dictionaries with a 'name' property, extract the names
    if array and isinstance(array[0], dict) and "name" in array[0]:
        # Extract the 'name' property from each item
        values = []
        for item in array:
            if isinstance(item, dict) and "name" in item:
                values.append(str(item["name"]))
            else:
                values.append(str(item))
    else:
        # Convert all elements to strings
        values = [str(item) for item in array]

    # Convert separator to string in case it's not already
    separator_str = str(separator)
    
    return separator_str.join(values)


# Default mapping functions
DEFAULT_MAPPING_FUNCTIONS = {
    "map": map_function,
    "sum": sum_function,
    "join": join_function
}


class ObjectMapper:
    """
    A flexible object mapper that transforms objects based on mapping rules.

    This class handles the transformation of objects using simple path-based references
    and function calls encoded as strings.
    """

    def __init__(self, mapping_functions: Optional[Dict[str, Callable]] = None):
        """
        Initialize the ObjectMapper with mapping functions.

        Keyword arguments:
        mapping_functions -- A dictionary of custom mapping functions
        """
        self.mapping_functions = mapping_functions or {}

        # Regex to detect function calls in mapping strings
        self.function_pattern = re.compile(r'^(\w+)\((.*)\)$')

        # Regex to detect array indexing
        self.array_index_pattern = re.compile(r'(.+)\[(\d+)\]$')

    def map_object(self, original_object: Dict, object_map: Dict, response_definitions: List[Dict]) -> Dict:
        """
        Map the original object to a new structure based on the mapping rules.

        Keyword arguments:
        original_object -- The source object to be transformed
        object_map -- A dictionary defining the mapping rules
        response_schema -- The schema defining the structure of the response

        Returns:
            The transformed object structure
        """
        try:
            logging.debug(f"Starting object mapping {original_object} to {object_map} with schema: {response_definitions}")

            response_definitions = response_definitions or []

            # Extract response keys from schema
            response_keys = [attr["name"] for attr in response_definitions]

            logging.debug(f"Response keys from schema: {response_keys}")

            # Initialize result structure based on response keys
            result = {}

            # Process each mapping rule
            for output_path, mapping_rule in object_map.items():
                try:
                    # Split the output path to determine which response object and path to update
                    path_parts = output_path.split('.')

                    response_key = path_parts[0]

                    # Validate that the response key is in the schema
                    if response_key not in response_keys:
                        raise MappingError(f"Response key '{response_key}' not found in schema", output_path)

                    # Extract the value using the mapping rule
                    value = self._evaluate_mapping_rule(original_object, mapping_rule)

                    # Update the result structure
                    if len(path_parts) == 1:
                        # Direct assignment to response key
                        result[response_key] = value

                    else:
                        # Nested path - need to build the structure
                        result[response_key] = self._set_nested_value(result[response_key], path_parts[1:], value)

                except Exception as e:
                    if isinstance(e, MappingError):
                        raise

                    raise MappingError(str(e), output_path)

            logging.debug(f"Mapping completed successfully: {result}")

            return result

        except Exception as e:
            if isinstance(e, MappingError):
                raise

            raise MappingError(f"Failed to map object: {str(e)}")

    def _evaluate_mapping_rule(self, original_object: Dict, mapping_rule: str) -> Any:
        """
        Evaluate a mapping rule against the original object.

        Keyword arguments:
        original_object -- The source object to be transformed
        mapping_rule -- The mapping rule to evaluate

        Returns:
            The extracted or transformed value
        """
        # Check if this is a function call
        match = self.function_pattern.match(mapping_rule)

        if match:
            function_name, args_str = match.groups()
            return self._execute_function(function_name, args_str, original_object)

        # Otherwise, treat as a path reference
        return self._get_value_by_path(original_object, mapping_rule)

    def _execute_function(self, function_name: str, args_str: str, context_object: Dict) -> Any:
        """
        Execute a mapping function with the given arguments.

        Keyword arguments:
        function_name -- The name of the function to execute
        args_str -- The string representation of the function arguments
        context_object -- The source object for context

        Returns:
            The result of the function execution
        """
        if function_name not in self.mapping_functions:
            raise MappingError(f"Unknown function: {function_name}")

        try:
            # Simple case: two arguments separated by a comma
            if ',' in args_str:
                # Split on the first comma only
                first_arg_str, second_arg_str = args_str.split(',', 1)

                # Get first argument (typically a path to an array)
                first_arg = self._get_value_by_path(context_object, first_arg_str.strip())

                # Get second argument (could be various types)
                second_arg_str = second_arg_str.strip()

                # Handle string literals
                if second_arg_str.startswith('"') and second_arg_str.endswith('"'):
                    second_arg = second_arg_str[1:-1]  # Remove quotes

                elif second_arg_str.startswith("'") and second_arg_str.endswith("'"):
                    second_arg = second_arg_str[1:-1]  # Remove quotes

                # Handle item path
                elif second_arg_str.startswith('item.'):
                    second_arg = second_arg_str

                # Handle template objects for map function
                elif function_name == 'map' and second_arg_str.startswith('{') and second_arg_str.endswith('}'):
                    # Parse template object
                    template = {}

                    template_content = second_arg_str[1:-1]  # Remove braces

                    for pair in template_content.split(','):
                        if ':' in pair:
                            key, value = pair.split(':', 1)

                            template[key.strip()] = value.strip()

                    second_arg = template

                # Try as path reference
                else:
                    try:
                        second_arg = self._get_value_by_path(context_object, second_arg_str)
                    except Exception:
                        # If path lookup fails, use as literal
                        second_arg = second_arg_str

                # Call the function with two arguments
                return self.mapping_functions[function_name](first_arg, second_arg)

            else:
                # Single argument case
                arg = self._get_value_by_path(context_object, args_str.strip())

                return self.mapping_functions[function_name](arg)

        except Exception as e:
            error_msg = f"Function execution error: {str(e)}"

            raise MappingError(error_msg)

    def _get_value_by_path(self, obj: Dict, path: str) -> Any:
        """
        Get a value from an object using a dot-notation path.

        Keyword arguments:
        obj -- The source object to be transformed
        path -- The path to the value (e.g., "item.X", "item[0].Y")

        Returns:
            The value at the specified path
        """
        current = obj

        # Handle the special case where path is just a reference to the entire object
        if path == "original_object":
            return obj

        path_parts = path.split('.')

        for part in path_parts:
            # Check for array indexing
            index_match = self.array_index_pattern.match(part)

            if index_match:
                array_name, index = index_match.groups()

                index = int(index)

                if array_name not in current:
                    raise MappingError(f"Array '{array_name}' not found", path)

                if not isinstance(current[array_name], list):
                    raise MappingError(f"'{array_name}' is not an array", path)

                if index >= len(current[array_name]):
                    raise MappingError(f"Index {index} out of bounds for array '{array_name}'", path)

                current = current[array_name][index]

            else:
                if part not in current:
                    raise MappingError(f"Key '{part}' not found", path)

                current = current[part]

        return current

    def _set_nested_value(self, obj: Dict, path_parts: List[str], value: Any) -> None:
        """
        Set a value in a nested object structure.

        Keyword arguments:
        obj -- The object to update
        path_parts -- The path parts to navigate to the correct location
        value -- The value to set
        """
        current = obj

        # Navigate to the correct location
        for i, part in enumerate(path_parts[:-1]):
            if part not in current:
                current[part] = {}

            current = current[part]

        # Set the value at the final location
        current[path_parts[-1]] = value