import json
import re

from typing import Any, Dict, List, Callable, Optional, Union


class MappingError(Exception):
    """Exception raised for errors during object mapping"""
    def __init__(self, message: str, path: str = None):
        self.path = path

        self.message = f"Mapping Error at '{path}': {message}" if path else f"Mapping Error: {message}"

        super().__init__(self.message)


def get_object_property_function(obj: Any, property_path: str) -> Any:
    """
    Get a property from an object using dot notation.

    Keyword arguments:
    obj - The object to get the property from  
    property_path - Dot-separated path (e.g., "message" or "user.name")
    """
    if not isinstance(property_path, str):
        raise MappingError(f"Property path must be a string, got {type(property_path).__name__}")

    current = obj

    for part in property_path.split('.'):
        if isinstance(current, dict) and part in current:
            current = current[part]

        elif isinstance(current, list) and part.isdigit():
            index = int(part)

            if 0 <= index < len(current):
                current = current[index]

            else:
                raise MappingError(f"List index {index} out of range")

        else:
            raise MappingError(f"Property '{part}' not found")

    return current


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


def json_parse_function(json_string: str) -> Union[Dict, List, Any]:
    """
    Parse a JSON string into a Python object.

    Keyword arguments:
    json_string - The JSON string to parse

    Returns:
        Parsed JSON object (dict, list, or primitive)
    """
    if not isinstance(json_string, str):
        raise MappingError(f"JSON parse requires a string, got {type(json_string).__name__}")

    try:
        return json.loads(json_string.strip())

    except json.JSONDecodeError as e:
        raise MappingError(f"Invalid JSON string: {str(e)}")


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

    if isinstance(template, str):
        # Handle simple path case like "item.file_path"
        if template.startswith("item."):
            attr = template[5:]  # Remove "item."

            for item in array:
                if attr in item:
                    result.append(item[attr])

                else:
                    raise MappingError(f"Attribute '{attr}' not found in array item")

        else:
            raise MappingError("String template must be in format 'item.X'")

    elif isinstance(template, dict):
        # Handle dictionary template case (original behavior)
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

    else:
        raise MappingError(f"Template must be either a dict or string, got {type(template)}")

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


# Default mapping functions
DEFAULT_MAPPING_FUNCTIONS = {
    "get_object_property": get_object_property_function,
    "join": join_function,
    "json_parse": json_parse_function,
    "map": map_function,
    "sum": sum_function,
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

        self.keyword_arg_pattern = re.compile(r'(\w+)\s*=\s*([^,]+)')

        self.keyword_function_pattern = re.compile(r'^(\w+)\((.*)\)$')

    def _split_function_arguments(self, args_str: str) -> List[str]:
        """
        Split function arguments respecting brackets, quotes, and parentheses.

        Keyword arguments:
        args_str -- The argument string to split

        Returns:
            List of argument strings
        """
        if not args_str.strip():
            return []

        arguments = []

        current_arg = ""

        bracket_count = 0

        paren_count = 0

        brace_count = 0

        quote_char = None

        for char in args_str:
            if quote_char:
                current_arg += char

                if char == quote_char:
                    quote_char = None

            elif char in '"\'':
                current_arg += char

                quote_char = char

            elif char == '[':
                current_arg += char

                bracket_count += 1

            elif char == ']':
                current_arg += char

                bracket_count -= 1

            elif char == '(':
                current_arg += char

                paren_count += 1

            elif char == ')':
                current_arg += char

                paren_count -= 1

            elif char == '{':
                current_arg += char

                brace_count += 1

            elif char == '}':
                current_arg += char

                brace_count -= 1

            elif char == ',' and bracket_count == 0 and paren_count == 0 and brace_count == 0:
                arguments.append(current_arg.strip())

                current_arg = ""

            else:
                current_arg += char

        if current_arg.strip():
            arguments.append(current_arg.strip())

        return arguments

    def _execute_keyword_function(self, func_name: str, params: Dict, current_value: Any,
                                  context: Dict) -> Any:
        """
        Execute a keyword function with parameters, resolving 'current' references.

        Keyword arguments:
        func_name -- The name of the function to execute
        params -- A dictionary of parameters for the function
        current_value -- The current value to use for 'current' references
        context -- The context object for resolving paths

        Returns:
            The result of the function execution
        """
        # Replace 'current' references with actual current_value
        resolved_params = {}

        for param_name, param_value in params.items():
            if param_value == "current":
                resolved_params[param_name] = current_value

            else:
                # Try to resolve as path, fallback to literal
                try:
                    resolved_params[param_name] = self._resolve_argument_value(arg_str=param_value, context_object=context)

                except:
                    resolved_params[param_name] = param_value

        # Call function with keyword arguments
        return self.mapping_functions[func_name](**resolved_params)

    def _parse_pipeline_operations(self, ops_str: str) -> List[Dict]:
        """
        Parse comma-separated operations from pipeline array string.
        Handles quotes and nested parentheses properly.

        Keyword arguments:
        ops_str - The string representation of the pipeline operations (e.g., "[op1, op2, op3]")
        """
        if not (ops_str.startswith('[') and ops_str.endswith(']')):
            raise MappingError("Pipeline operations must be an array [...]")

        content = ops_str[1:-1].strip()

        if not content:
            return []

        operations = []

        current_op = ""

        paren_count = 0

        quote_char = None

        for char in content:
            if quote_char:
                current_op += char

                if char == quote_char:
                    quote_char = None

            elif char in '"\'':
                current_op += char

                quote_char = char

            elif char == '(':
                current_op += char

                paren_count += 1

            elif char == ')':
                current_op += char

                paren_count -= 1

            elif char == ',' and paren_count == 0:
                operations.append(self._parse_single_operation(current_op.strip()))

                current_op = ""

            else:
                current_op += char

        if current_op.strip():
            operations.append(self._parse_single_operation(current_op.strip()))

        return operations

    def _parse_single_operation(self, op_str: str) -> Dict:
        """
        Parse a single operation string into a structured format.

        Keyword arguments:
        op_str -- The operation string to parse (e.g., "function_name(param=value, param2=value2)")
        """
        # Check if it's keyword syntax: function_name(param=value, param2=value2)
        match = self.keyword_function_pattern.match(op_str.strip())

        if match:
            func_name, args_str = match.groups()

            params = self._parse_keyword_arguments(args_str)

            return {"type": "keyword", "function": func_name, "params": params}

        else:
            return {"type": "string", "operation": op_str}

    def _parse_keyword_arguments(self, args_str: str) -> Dict:
        """
        Parse a string of keyword arguments into a dictionary.

        Keyword arguments:
        args_str -- The string containing keyword arguments (e.g., "param1=value1, param2=value2")
        """
        params = {}

        for match in self.keyword_arg_pattern.finditer(args_str):
            param_name, param_value = match.groups()

            params[param_name.strip()] = param_value.strip()

        return params

    def pipeline_function(self, initial_value: Any, operations: List[Dict], original_context: Dict = None) -> Any:
        """
        Execute a pipeline of operations on an initial value.

        Keyword arguments:
        initial_value -- The starting value for the pipeline
        operations -- List of operation dictionaries to execute in order
        original_context -- The original context with all variables
        """
        if not isinstance(operations, list):
            raise MappingError("Pipeline operations must be a list")

        current_value = initial_value

        for i, operation in enumerate(operations):
            try:
                # Combine original context with current value
                operation_context = (original_context or {}).copy()

                operation_context['current'] = current_value

                if operation["type"] == "keyword":
                    current_value = self._execute_keyword_function(
                        operation["function"], 
                        operation["params"], 
                        current_value, 
                        operation_context
                    )

                else:
                    current_value = self._evaluate_mapping_rule(operation_context, operation["operation"])

            except Exception as e:
                raise MappingError(f"Pipeline step {i} ('{operation}') failed: {str(e)}")

        return current_value

    def map_object(self, resolved_variables: Dict, mapping: Dict[str, Any]) -> Dict:
        """
        Transform an object based on mapping rules.

        Keyword arguments:
        original_object -- The source object to be transformed
        object_map -- A dictionary defining the mapping rules

        Returns:
            The transformed object
        """
        try:
            result = {}

            # Process each mapping rule
            for output_path, mapping_rule in mapping.items():
                try:
                    # Extract the value using the mapping rule
                    value = self._evaluate_mapping_rule(resolved_variables, mapping_rule)

                    # Split path and set value
                    path_parts = output_path.split('.')

                    if len(path_parts) == 1:
                        # Direct assignment
                        result[output_path] = value

                    else:
                        # Use existing _set_nested_value method
                        self._set_nested_value(result, path_parts, value)

                except Exception as e:
                    if isinstance(e, MappingError):
                        raise

                    raise MappingError(str(e), output_path)

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
        return self._resolve_argument_value(arg_str=mapping_rule, context_object=original_object)

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
        if function_name not in self.mapping_functions and function_name != "pipeline":
            raise MappingError(f"Unknown function: {function_name}")

        try:
            if function_name == "pipeline":
                # Split arguments properly for pipeline
                args = self._split_function_arguments(args_str)

                if len(args) != 2:
                    raise MappingError("Pipeline requires exactly 2 arguments: initial_value, [operations]")

                # Get initial value
                initial_value = self._resolve_argument_value(arg_str=args[0], context_object=context_object)

                # Parse operations array
                operations = self._parse_pipeline_operations(args[1])

                return self.pipeline_function(initial_value=initial_value, operations=operations, original_context=context_object)

            elif '=' in args_str:
                # Parse as keyword arguments
                params = self._parse_keyword_arguments(args_str)

                resolved_params = {}

                for param_name, param_value in params.items():
                    # Handle string literals
                    if param_value.startswith('"') and param_value.endswith('"'):
                        resolved_params[param_name] = param_value[1:-1]  # Remove quotes

                    elif param_value.startswith("'") and param_value.endswith("'"):
                        resolved_params[param_name] = param_value[1:-1]  # Remove quotes

                    else:
                        # Try to resolve as path, fallback to literal
                        try:
                            resolved_params[param_name] = self._resolve_argument_value(context_object=context_object, arg_str=param_value)

                        except:
                            resolved_params[param_name] = param_value

                # Call function with keyword arguments
                return self.mapping_functions[function_name](**resolved_params)

            else:
                # Split arguments properly for regular functions
                args = self._split_function_arguments(args_str)

                if len(args) == 1:
                    # Single argument case
                    arg = self._resolve_argument_value(arg_str=args[0], context_object=context_object)

                    return self.mapping_functions[function_name](arg)

                elif len(args) == 2:
                    # Two arguments case
                    first_arg = self._resolve_argument_value(arg_str=args[0], context_object=context_object)

                    second_arg_str = args[1]

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
                            second_arg = self._resolve_argument_value(arg_str=second_arg_str, context_object=context_object)

                        except Exception:
                            # If path lookup fails, use as literal
                            second_arg = second_arg_str

                    # Call the function with two arguments
                    return self.mapping_functions[function_name](first_arg, second_arg)

                else:
                    raise MappingError(f"Function {function_name} called with {len(args)} arguments, but only 1-2 arguments are supported")

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

    def _resolve_argument_value(self, arg_str: str, context_object: Dict) -> Any:
        """
        Resolve an argument value, handling arrays, strings, and path references.

        Keyword arguments:
        arg_str -- The argument string to resolve (e.g., "[var1, 'literal']")
        context_object -- The context object for resolving paths
        """
        arg_str = arg_str.strip()

        # Handle array literals like [var1, "literal"]
        if arg_str.startswith('[') and arg_str.endswith(']'):
            array_content = arg_str[1:-1]  # Remove brackets

            # Use proper argument splitting for array elements
            elements = self._split_function_arguments(array_content)

            result = []

            for elem in elements:
                elem = elem.strip()
                if elem.startswith('"') and elem.endswith('"'):
                    result.append(elem[1:-1])  # String literal

                elif elem.startswith("'") and elem.endswith("'"):
                    result.append(elem[1:-1])  # String literal

                else:
                    result.append(self._get_value_by_path(context_object, elem))

            return result

        # Handle string literals
        elif arg_str.startswith('"') and arg_str.endswith('"'):
            return arg_str[1:-1]

        elif arg_str.startswith("'") and arg_str.endswith("'"):
            return arg_str[1:-1]

        # Handle path references
        else:
            return self._get_value_by_path(context_object, arg_str)

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