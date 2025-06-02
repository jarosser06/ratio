"""
Mapping module for transforming data based on mapping rules.
"""
import logging
import inspect
import re

from typing import Any, Dict, List, Callable, Optional, Union

from ratio.core.services.agent_manager.runtime.exceptions import MappingError

from ratio.core.services.agent_manager.runtime.mapper_functions import (
    MappingContext,
    create_object_function,
    get_object_property_function,
    join_function,
    json_parse_function,
    map_function,
    sum_function,

    if_function,
    filter_function,
    group_by_function,
    sort_function,
    unique_function,
    flatten_function,

    # File system functions
    list_files_function,
    list_file_versions_function,
    describe_version_function,
    read_file_function,
    read_files_function,

    # Other
    datetime_now_function,
)


# Updated mapping functions dictionary
DEFAULT_MAPPING_FUNCTIONS = {
    "create_object": create_object_function,
    "get_object_property": get_object_property_function,
    "join": join_function,
    "json_parse": json_parse_function,
    "map": map_function,
    "sum": sum_function,

    # Conditional logic functions
    "if": if_function,
    "filter": filter_function,

    # Data manipulation functions
    "group_by": group_by_function,
    "sort": sort_function,
    "unique": unique_function,
    "flatten": flatten_function,

    # File system functions
    "list_files": list_files_function,
    "list_file_versions": list_file_versions_function,
    "describe_version": describe_version_function,
    "read_file": read_file_function,
    "read_files": read_files_function,

    # DT
    "datetime_now": datetime_now_function,
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
                                  context: MappingContext) -> Any:
        """
        Execute a keyword function with parameters, resolving 'current' references.

        Keyword arguments:
        func_name -- The name of the function to execute
        params -- A dictionary of parameters for the function
        current_value -- The current value to use for 'current' references
        context -- The mapping context for resolving paths

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
                    resolved_params[param_name] = self._resolve_argument_value(arg_str=param_value, context=context)

                except Exception as excp:
                    raise MappingError(f"Failed to resolve parameter '{param_name}' = '{param_value}': {str(excp)}")

        # Add context to resolved params first
        final_params = {"context": context}

        final_params.update(resolved_params)

        # Call function with keyword arguments
        return self.mapping_functions[func_name](**final_params)

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
        if not args_str.strip():
            return {}

        params = {}

        current_key = ""

        current_value = ""

        state = "seeking_key"  # "seeking_key", "in_key", "seeking_equals", "seeking_value", "in_value"

        # Tracking nested structures
        bracket_count = 0

        brace_count = 0  

        paren_count = 0

        quote_char = None

        i = 0

        while i < len(args_str):
            char = args_str[i]

            # Handle quote state
            if quote_char:
                current_value += char

                if char == quote_char and (i == 0 or args_str[i-1] != '\\'):
                    quote_char = None

                i += 1

                continue

            # Handle starting quotes
            if char in '"\'':
                if state == "in_value":
                    current_value += char

                    quote_char = char

                elif state == "seeking_value":
                    current_value = char

                    state = "in_value"

                    quote_char = char

                i += 1

                continue

            # Handle nesting characters  
            if char == '[':
                if state == "in_value":
                    current_value += char

                    bracket_count += 1

                elif state == "seeking_value":
                    current_value = char

                    state = "in_value"

                    bracket_count += 1

            elif char == ']':
                if state == "in_value":
                    current_value += char

                    bracket_count -= 1

            elif char == '{':
                if state == "in_value":
                    current_value += char

                    brace_count += 1

                elif state == "seeking_value":
                    current_value = char

                    state = "in_value"

                    brace_count += 1

            elif char == '}':
                if state == "in_value":
                    current_value += char

                    brace_count -= 1

            elif char == '(':
                if state == "in_value":
                    current_value += char

                    paren_count += 1

                elif state == "seeking_value":
                    current_value = char

                    state = "in_value"

                    paren_count += 1

            elif char == ')':
                if state == "in_value":
                    current_value += char

                    paren_count -= 1

            # Handle state transitions
            elif char == '=' and state in ["in_key", "seeking_equals"]:
                state = "seeking_value"

            elif char == ',' and bracket_count == 0 and brace_count == 0 and paren_count == 0:
                # End of parameter - save it
                if current_key and current_value:
                    params[current_key.strip()] = current_value.strip()

                current_key = ""

                current_value = ""

                state = "seeking_key"

            elif char.isspace():
                # Skip whitespace in transitions
                if state == "seeking_key":
                    pass  # Skip leading whitespace

                elif state == "in_key":
                    state = "seeking_equals"

                elif state == "seeking_value":
                    pass  # Skip whitespace before value

                elif state == "in_value":
                    current_value += char

            else:
                # Regular character
                if state == "seeking_key":
                    current_key = char

                    state = "in_key"

                elif state == "in_key":
                    current_key += char

                elif state == "seeking_value":
                    current_value = char

                    state = "in_value"

                elif state == "in_value":
                    current_value += char

            i += 1

        # Handle the last parameter
        if current_key and current_value:
            params[current_key.strip()] = current_value.strip()

        return params

    def pipeline_function(self, initial_value: Any, operations: List[Dict], context: MappingContext) -> Any:
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
                operation_data = context.data.copy()

                operation_data['current'] = current_value

                operation_context = MappingContext(data=operation_data, token=context.token)

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

    def map_object(self, resolved_variables: Dict, mapping: Dict[str, Any], token: str) -> Dict:
        """
        Transform an object based on mapping rules.

        Keyword arguments:
        original_object -- The source object to be transformed
        object_map -- A dictionary defining the mapping rules
        token -- The token used for system functions

        Returns:
            The transformed object
        """
        try:
            result = {}

            context = MappingContext(data=resolved_variables, token=token)

            # Process each mapping rule
            for output_path, mapping_rule in mapping.items():
                try:
                    # Extract the value using the mapping rule
                    value = self._evaluate_mapping_rule(context=context, mapping_rule=mapping_rule)

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

    def _evaluate_mapping_rule(self, context: MappingContext, mapping_rule: str) -> Any:
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

            return self._execute_function(
                function_name=function_name,
                args_str=args_str,
                context=context)

        # Otherwise, treat as a path reference
        return self._resolve_argument_value(arg_str=mapping_rule, context=context)

    def _execute_function(self, function_name: str, args_str: str, context: MappingContext) -> Any:
        """
        Execute a mapping function with the given arguments.

        Keyword arguments:
        function_name -- The name of the function to execute
        args_str -- The string representation of the function arguments
        context -- The mapping context or source object for context

        Returns:
            The result of the function execution
        """
        logging.debug(f"Executing function '{function_name}' with args: {args_str}")

        if function_name not in self.mapping_functions and function_name != "pipeline":
            raise MappingError(f"Unknown function: {function_name}")

        try:
            if function_name == "pipeline":
                # Split arguments properly for pipeline
                args = self._split_function_arguments(args_str)

                if len(args) != 2:
                    raise MappingError("Pipeline requires exactly 2 arguments: initial_value, [operations]")

                # Get initial value
                initial_value = self._resolve_argument_value(arg_str=args[0], context=context)

                # Parse operations array
                operations = self._parse_pipeline_operations(args[1])

                return self.pipeline_function(initial_value=initial_value, operations=operations, context=context)

            elif '=' in args_str:
                # Parse as keyword arguments
                params = self._parse_keyword_arguments(args_str)

                logging.debug(f"Resolved keyword arguments for function '{function_name}': {params}")

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
                            resolved_params[param_name] = self._resolve_argument_value(context=context, arg_str=param_value)

                        except Exception as excp:
                            raise MappingError(f"Failed to resolve parameter '{param_name}' = '{param_value}': {str(excp)}")

                # Check if function accepts context parameter
                func = self.mapping_functions[function_name]

                resolved_params['context'] = context

                # Call function with keyword arguments
                return func(**resolved_params)

            else:
                # Split arguments properly for regular functions
                args = self._split_function_arguments(args_str)

                # Resolve all arguments
                resolved_args = []

                for arg_str in args:
                    resolved_args.append(self._resolve_argument_value(arg_str=arg_str, context=context))

                # Get function signature to properly map arguments
                func = self.mapping_functions[function_name]

                sig = inspect.signature(func)

                param_names = list(sig.parameters.keys())

                # Context is always first parameter, if not this is a system code issue
                if len(param_names) == 0 or param_names[0] != 'context':
                    raise Exception(f"Function {function_name} must have 'context' as first parameter")

                # Map resolved arguments to parameter names (skip context)
                if len(resolved_args) > len(param_names) - 1:
                    raise MappingError(f"Function {function_name} called with {len(resolved_args)} arguments, but expects {len(param_names) - 1}")

                # Build keyword arguments
                kwargs = {"context": context}

                for i, arg_value in enumerate(resolved_args):
                    param_name = param_names[i + 1]  # Skip context parameter

                    kwargs[param_name] = arg_value

                # Call function with keyword arguments
                return func(**kwargs)

        except Exception as e:
            error_msg = f"Function execution error: {str(e)}"

            raise MappingError(error_msg)

    def _get_value_by_path(self, context: MappingContext, path: str) -> Any:
        """
        Get a value from an object using a dot-notation path.

        Keyword arguments:
        obj -- The source object to be transformed
        path -- The path to the value (e.g., "item.X", "item[0].Y")

        Returns:
            The value at the specified path
        """
        current = context.data

        # Handle the special case where path is just a reference to the entire object
        if path == "original_object":
            return context.data

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

    def _resolve_argument_value(self, arg_str: str, context: MappingContext) -> Any:
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
                    result.append(self._get_value_by_path(context=context, path=elem))

            return result

        # Handle string literals
        elif arg_str.startswith('"') and arg_str.endswith('"'):
            return arg_str[1:-1]

        elif arg_str.startswith("'") and arg_str.endswith("'"):
            return arg_str[1:-1]

        # Handle path references
        else:
            return self._get_value_by_path(context=context, path=arg_str)

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