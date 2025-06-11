"""
Mapper functions for Tool Manager Transformations
"""
import fnmatch
import json
import logging
import re

from datetime import datetime, UTC as utc_tz
from typing import Any, Callable, Dict, List, Optional, Union

from da_vinci.core.immutable_object import ObjectBody

from ratio.core.services.process_manager.runtime.exceptions import MappingError

from ratio.core.core_lib.client import RatioInternalClient

from ratio.core.services.storage_manager.request_definitions import (
    DescribeFileVersionRequest,
    FindFileRequest,
    GetFileVersionRequest,
    ListFileVersionsRequest,
)


class MappingContext:
    def __init__(self, data: Dict, token: str):
        """
        Initializes the mapping context with data and token.

        Keyword Arguments:
        data -- The data to use in the mapping context, typically a dictionary of variables.
        token -- The authentication token for the Ratio service
        """
        self.data = data

        self.token = token

        self.ratio_client = RatioInternalClient(token=token, service_name="storage_manager")

        self._cache = {}

    def get_cached_or_execute(self, cache_key: str, operation: Callable) -> Any:
        """
        Retrieves a cached value or executes the operation if not cached.

        Keyword Arguments:
        cache_key -- The key to use for caching the result.
        operation -- A callable that returns the value to cache if not already cached.
        """
        if cache_key not in self._cache:
            self._cache[cache_key] = operation()

        return self._cache[cache_key]


class ExpressionEvaluator:
    """Simple expression evaluator for conditional logic"""
    
    def __init__(self, context: Any):
        self.context = context
        
    def evaluate(self, expression: str) -> bool:
        """
        Evaluate a simple boolean expression.
        Supports: ==, !=, >, <, >=, <=, and, or, not

        Keyword arguments:
        expression -- The expression to evaluate, e.g. "item.error_count > 0 and item.status == 'active'"
        """
        # Clean up the expression
        expr = expression.strip()

        # Handle 'and' and 'or' operators
        if ' and ' in expr:
            parts = expr.split(' and ', 1)

            return self.evaluate(parts[0]) and self.evaluate(parts[1])

        if ' or ' in expr:
            parts = expr.split(' or ', 1)

            return self.evaluate(parts[0]) or self.evaluate(parts[1])

        # Handle 'not' operator
        if expr.startswith('not '):
            return not self.evaluate(expr[4:])

        # Handle comparison operators
        operators = ['>=', '<=', '==', '!=', '>', '<', 'contains']

        for op in operators:
            if f" {op} " in expr:
                left, right = expr.split(f" {op} ", 1)

                left_val = self._resolve_value(left.strip())

                right_val = self._resolve_value(right.strip())

                if op == "==":
                    return left_val == right_val

                elif op == "!=":
                    return left_val != right_val

                elif op == ">":
                    return left_val > right_val

                elif op == "<":
                    return left_val < right_val

                elif op == ">=":
                    return left_val >= right_val

                elif op == "<=":
                    return left_val <= right_val

                elif op == "contains":
                    # Convert both to strings for contains check
                    left_str = str(left_val) if left_val is not None else ''

                    right_str = str(right_val) if right_val is not None else ''

                    return right_str in left_str

        # If no operators found, treat as boolean value
        return bool(self._resolve_value(expr))

    def _resolve_value(self, value_str: str) -> Any:
        """
        Resolve a value string to its actual value

        Keyword arguments:
        value_str -- The string representation of the value, e.g. "item.error_count", "42", "'active'", etc.

        Returns:
            The resolved value, which can be a string, int, float, bool, or property from context.
        """
        value_str = value_str.strip()

        # Handle string literals
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]

        # Handle numeric literals
        try:
            if '.' in value_str:
                return float(value_str)

            else:
                return int(value_str)

        except ValueError:
            pass

        # Handle boolean literals
        if value_str.lower() == 'true':
            return True

        elif value_str.lower() == 'false':
            return False

        # Handle property access
        if value_str.startswith('item.'):
            prop = value_str[5:]  # Remove 'item.'

            if isinstance(self.context, dict) and prop in self.context:
                return self.context[prop]

            else:
                raise MappingError(f"Property '{prop}' not found in item")

        # Handle direct variable reference
        if isinstance(self.context, dict) and value_str in self.context:
            return self.context[value_str]

        # Default to string value
        return value_str


def datetime_now_function(context: MappingContext, format: str = "iso") -> Union[str, int]:
    """
    Returns current date/time in specified format.

    Keyword arguments:
    context -- The mapping context (unused but available)
    format -- Format type: "iso" for ISO 8601 string, "unix" for Unix timestamp
    """
    if format not in ("iso", "unix"):
        raise MappingError("Format must be 'iso' or 'unix'")

    now = datetime.now(tz=utc_tz)

    if format == "iso":
        return now.isoformat()

    else:
        return now.timestamp()


def create_object_function(context: MappingContext, **kwargs) -> Dict:
    """
    Creates an object from keyword arguments, resolving each value.

    Keyword arguments:
    context -- The mapping context
    **kwargs -- Key-value pairs where values are resolved from context
    """
    return dict(kwargs)


def get_object_property_function(context: MappingContext, obj: Any, property_path: str) -> Any:
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


def join_function(context: MappingContext, array: List, separator: str) -> str:
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
        values = []

        for item in array:
            if isinstance(item, dict) and "name" in item:
                values.append(str(item["name"]))

            else:
                values.append(str(item))

    else:
        # Convert all elements to strings
        values = [str(item) for item in array]

    separator_str = str(separator)

    return separator_str.join(values)


def json_parse_function(context: MappingContext, json_string: str) -> Union[Dict, List, Any]:
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


def map_function(context: MappingContext, array: List, template: Dict) -> List:
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


def sum_function(context: MappingContext, array: List, item_path: str) -> Union[int, float]:
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


def if_function(context: MappingContext, condition: Any, true_value: Any, false_value: Any) -> Any:
    """
    Simple ternary operator that returns true_value if condition evaluates to truthy, otherwise false_value.
    
    Keyword arguments:
    context -- The mapping context (unused but available for consistency)
    condition -- The condition to evaluate (can be expression string or boolean value)
    true_value -- Value to return if condition is truthy
    false_value -- Value to return if condition is falsy
    """
    # If condition is a string, treat it as an expression to evaluate
    if isinstance(condition, str):
        # For simple expressions like "error_count > 0", we need context to resolve variables
        # For now, treat string conditions as truthy unless they're "false", "", etc.
        condition_result = condition.lower() not in ('false', '', '0', 'null', 'none')

    else:
        condition_result = bool(condition)

    return true_value if condition_result else false_value


def filter_function(context: MappingContext, array: List, condition_string: str) -> List:
    """
    Filters array elements based on condition string.

    Keyword arguments:
    context -- The mapping context (unused but available)
    array -- The array to filter
    condition_string -- Condition using 'item' to reference each element
    """
    if not isinstance(array, list):
        raise MappingError("First argument must be an array")

    if not isinstance(condition_string, str):
        raise MappingError("Condition must be a string")

    result = []

    for item in array:
        try:
            evaluator = ExpressionEvaluator(item)

            if evaluator.evaluate(condition_string):
                result.append(item)

        except Exception as e:
            raise MappingError(f"Error evaluating condition '{condition_string}' for item: {str(e)}")

    return result


# Data manipulation functions

def group_by_function(context: MappingContext, array: List, key_path: str) -> Dict:
    """
    Groups array elements by the specified key path.

    Keyword arguments:
    context -- The mapping context (unused but available)
    array -- The array to group
    key_path -- The path to the grouping key (e.g., "item.category")
    """
    if not isinstance(array, list):
        raise MappingError("First argument must be an array")

    if not key_path.startswith("item."):
        raise MappingError("Key path must be in format 'item.X'")

    attr = key_path[5:]  # Remove "item."

    groups = {}

    for item in array:
        if not isinstance(item, dict):
            raise MappingError("Array items must be objects for grouping")

        if attr not in item:
            raise MappingError(f"Attribute '{attr}' not found in array item")

        group_key = str(item[attr])

        if group_key not in groups:
            groups[group_key] = []

        groups[group_key].append(item)

    return groups


def sort_function(context: MappingContext, array: List, key_path: Optional[str] = None , direction: str = "asc") -> List:
    """
    Sorts array by key path.

    Keyword arguments:
    context -- The mapping context (unused but available)
    array -- The array to sort
    key_path -- The path to the sorting key (e.g., "item.priority")
    direction -- Sort direction, "asc" (default) or "desc"
    """
    if not isinstance(array, list):
        raise MappingError("Invalid type for array, expected list")

    if not key_path.startswith("item."):
        raise MappingError("Key path must be in format 'item.X'")

    if direction not in ("asc", "desc"):
        raise MappingError("Direction must be 'asc' or 'desc'")

    attr = key_path[5:]  # Remove "item."

    try:
        if not key_path or key_path.strip() == "":
            sorted_array = sorted(array, reverse=(direction == "desc"))

        # If key_path provided, extract attribute from objects
        elif key_path.startswith("item."):
            attr = key_path[5:]  # Remove "item."

            sorted_array = sorted(array, key=lambda x: x[attr], reverse=(direction == "desc"))

        else:
            raise MappingError("Key path must be in format 'item.X' or empty for primitive arrays")

        return sorted_array

    except KeyError:
        raise MappingError(f"Attribute '{attr}' not found in array item")

    except TypeError as e:
        raise MappingError(f"Cannot sort by attribute '{attr}': {str(e)}")


def unique_function(context: MappingContext, array: List) -> List:
    """
    Returns array with duplicate values removed.

    Keyword arguments:
    context -- The mapping context (unused but available)
    array -- The array to deduplicate
    """
    if not isinstance(array, list):
        raise MappingError("First argument must be an array")

    # For lists containing hashable items, use set
    try:
        return list(dict.fromkeys(array))  # Preserves order unlike set()

    except TypeError:
        # Handle unhashable items (like dicts) by doing manual comparison
        result = []

        for item in array:
            if item not in result:
                result.append(item)

        return result


def flatten_function(context: MappingContext, array: List) -> List:
    """
    Flattens nested arrays one level deep.

    Keyword arguments:
    context -- The mapping context (unused but available)
    array -- The array to flatten
    """
    if not isinstance(array, list):
        raise MappingError("First argument must be an array")

    result = []

    for item in array:
        if isinstance(item, list):
            result.extend(item)

        else:
            result.append(item)

    return result


def list_files_function(context: MappingContext, directory_path: str, pattern: str = None) -> List[str]:
    """
    Lists files in directory, optionally filtered by glob pattern. Limited to 50 results.

    Keyword arguments:
    context -- The mapping context with token and client
    directory_path -- The directory path to list
    pattern -- Optional glob pattern to filter files
    """
    cache_key = f"list_files:{directory_path}:{pattern or ''}"

    def list_operation():
        request_body = {
            "file_path": directory_path,
            "recursion_max_depth": 1
        }

        find_request = ObjectBody(
            schema=FindFileRequest,
            body=request_body
        )

        resp = context.ratio_client.request(
            path="/storage/find_file",
            request=find_request
        )

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise MappingError(f"Directory not found: {directory_path}")

            else:
                raise MappingError(f"Failed to list files in {directory_path}: {resp.status_code}")

        files = resp.response_body.get("data", [])

        file_paths = [f["file_path"] for f in files if not f.get("is_directory", False)]

        # Apply pattern filter if provided
        if pattern:
            file_paths = [f for f in file_paths if fnmatch.fnmatch(f.split('/')[-1], pattern)]

        # Limit to 50 results
        if len(file_paths) > 50:
            logging.warning(f"list_files result truncated to 50 files for {directory_path}")

            file_paths = file_paths[:50]

        return file_paths

    return context.get_cached_or_execute(cache_key, list_operation)


def list_file_versions_function(context: MappingContext, file_path: str) -> List[Dict]:
    """
    Lists all versions of a specific file.

    Keyword arguments:
    context -- The mapping context with token and client
    file_path -- The file path to get versions for
    """
    # Validate file path format  
    if not re.match(r"^/(.*[^/])?$", file_path):
        raise MappingError("Invalid file path format")

    cache_key = f"list_file_versions:{file_path}"

    def list_versions_operation():
        request = ObjectBody(
            schema=ListFileVersionsRequest,
            body={"file_path": file_path}
        )

        resp = context.ratio_client.request(
            path="/storage/list_file_versions", 
            request=request
        )

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise MappingError(f"File not found: {file_path}")

            else:
                raise MappingError(f"Failed to list versions for {file_path}: {resp.status_code}")

        return resp.response_body.get("data", [])

    return context.get_cached_or_execute(cache_key, list_versions_operation)


def describe_version_function(context: MappingContext, file_path: str, version_id: str = None) -> Dict:
    """
    Returns metadata for a specific file version.

    Keyword arguments:
    context -- The mapping context with token and client
    file_path -- The file path to describe
    version_id -- Optional version ID, defaults to latest
    """
    # Validate file path format
    if not re.match(r"^/(.*[^/])?$", file_path):
        raise MappingError("Invalid file path format")

    cache_key = f"describe_version:{file_path}:{version_id or 'latest'}"

    def describe_operation():
        request_body = {"file_path": file_path}

        if version_id:
            request_body["version_id"] = version_id

        request = ObjectBody(
            schema=DescribeFileVersionRequest,
            body=request_body
        )

        resp = context.ratio_client.request(
            path="/storage/describe_file_version",
            request=request
        )

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise MappingError(f"File or version not found: {file_path}")

            else:
                raise MappingError(f"Failed to describe {file_path}: {resp.status_code}")

        return resp.response_body.get("data", {})

    return context.get_cached_or_execute(cache_key, describe_operation)


def read_file_function(context: MappingContext, file_path: str, version_id: str = None) -> str:
    """
    Reads content of a file.

    Keyword arguments:
    context -- The mapping context with token and client
    file_path -- The file path to read
    version_id -- Optional version ID, defaults to latest
    """
    # Validate file path format
    if not re.match(r"^/(.*[^/])?$", file_path):
        raise MappingError("Invalid file path format")

    cache_key = f"read_file:{file_path}:{version_id or 'latest'}"

    def read_operation():
        request_body = {"file_path": file_path}

        if version_id:
            request_body["version_id"] = version_id

        request = ObjectBody(
            schema=GetFileVersionRequest,
            body=request_body
        )

        resp = context.ratio_client.request(
            path="/storage/get_file_version",
            request=request
        )

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise MappingError(f"File or version not found: {file_path}")

            else:
                raise MappingError(f"Failed to read {file_path}: {resp.status_code}")

        return resp.response_body.get("data", "")

    return context.get_cached_or_execute(cache_key, read_operation)


def read_files_function(context: MappingContext, file_paths: List[str]) -> List[str]:
    """
    Reads content of multiple files. Limited to 5 files maximum.

    Keyword arguments:
    context -- The mapping context with token and client
    file_paths -- Array of file paths to read
    """
    if not isinstance(file_paths, list):
        raise MappingError("First argument must be an array of file paths")

    if len(file_paths) > 5:
        raise MappingError("read_files limited to 5 files maximum")

    # Validate all file paths
    for file_path in file_paths:
        if not re.match(r"^/(.*[^/])?$", file_path):
            raise MappingError(f"Invalid file path format: {file_path}")

    results = []

    for file_path in file_paths:
        content = read_file_function(context, file_path)

        results.append(content)

    return results