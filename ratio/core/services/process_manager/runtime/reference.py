"""
Value Reference Resolution
"""
import logging
import os

from typing import Any, Dict, Optional, Tuple

from da_vinci.core.immutable_object import ObjectBody

from ratio.core.core_lib.client import RatioInternalClient

from ratio.core.services.storage_manager.request_definitions import (
    DescribeFileRequest,
    GetFileVersionRequest,
)

class InvalidReferenceError(Exception):
    """
    Exception raised for invalid reference strings.
    """
    pass


class ReferenceValueBase:
    """
    Base class for all reference value types.
    This class is not meant to be instantiated directly.
    """
    requires_token: bool = False

    def __init__(self, original_value: Any):
        """
        Initialize the reference value.

        Keyword arguments:
        original_value: The original value to be referenced.
        """
        self.original_value = original_value


class ReferenceValueString(ReferenceValueBase):
    """
    Class for string reference values.
    """
    def referenced_value(self, *, attribute_name: Optional[str] = None) -> str:
        """
        Get the referenced value as a string.

        Keyword arguments:
        attribute_name: The name of the attribute to access (if any).
        """
        if attribute_name is not None:
            raise ValueError("String reference values do not support attributes.")

        return str(self.original_value)


class ReferenceValueNumber(ReferenceValueBase):
    """
    Class for number reference values.
    """
    def referenced_value(self, *, attribute_name: Optional[str] = None) -> float:
        """
        Get the referenced value as a number.

        Keyword arguments:
        attribute_name: The name of the attribute to access (if any).
        """
        if attribute_name is not None:
            raise ValueError("Number reference values do not support attributes.")

        if not self.original_value:
            return None

        if "." in str(self.original_value):
            return float(self.original_value)

        else:
            return int(self.original_value)


class ReferenceValueBoolean(ReferenceValueBase):
    """
    Class for boolean reference values.
    """
    def referenced_value(self, *, attribute_name: Optional[str] = None) -> bool:
        """
        Get the referenced value as a boolean.

        Keyword arguments:
        attribute_name: The name of the attribute to access (if any).
        """
        if attribute_name is not None:
            raise ValueError("Boolean reference values do not support attributes.")

        if self.original_value is None:
            return None

        return bool(self.original_value)


class ReferenceValueList(ReferenceValueBase):
    """
    Class for list reference values.
    """
    def is_int(self, value: str) -> bool:
        """
        Check if the value is an int.

        Keyword arguments:
        value: The value to check.
        """
        try:
            int(value)

            return True

        except ValueError:
            return False

    def referenced_value(self, *, attribute_name: Optional[str] = None) -> list:
        """
        Get the referenced value as a list.

        Keyword arguments:
        attribute_name: The name of the attribute to access (if any).
        """
        if not attribute_name:
            return list(self.original_value)

        if attribute_name:
            if not self.original_value or not isinstance(self.original_value, list) or len(self.original_value) == 0:
                raise ValueError("Attribute access is only supported for non empty list reference values.")

        if attribute_name == "length":
            return len(self.original_value)

        elif attribute_name == "first":
            return self.original_value[0] if self.original_value else None

        elif attribute_name == "last":
            return self.original_value[-1] if self.original_value else None

        elif self.is_int(attribute_name):
            index = int(attribute_name)

            if index < 0 or index >= len(self.original_value):
                raise ValueError(f"Index out of range: {index}")

            return self.original_value[index]


class ReferenceValueObject(ReferenceValueBase):
    """
    Class for Object (dict) reference values.
    """
    def referenced_value(self, *, attribute_name: Optional[str] = None) -> dict:
        """
        Get the referenced value as a dictionary.

        Keyword arguments:
        attribute_name: The name of the attribute to access (if any).
        """
        if attribute_name is not None:
            if not self.original_value or not isinstance(self.original_value, dict):
                raise ValueError("Attribute access is only supported for non empty dictionary reference values.")

            return self.original_value.get(attribute_name)

        if not self.original_value:
            return {}

        return dict(self.original_value)


class ReferenceValueFile(ReferenceValueBase):
    """
    Class for file reference values.
    """
    requires_token: bool = True

    def referenced_value(self, *, token: str, attribute_name: Optional[str] = None) -> str:
        """
        Get the referenced value as a file path.

        Keyword arguments:
        attribute_name: The name of the attribute to access (if any).
        """
        storage_client = RatioInternalClient(
            service_name="storage_manager",
            token=token,
        )

        if not self.original_value:
            raise ValueError("File reference value is empty unknown path to fetch")

        if not attribute_name:
            file_version_request = ObjectBody(
                schema=GetFileVersionRequest,
                body={"file_path": self.original_value},
            )

            file_version_response = storage_client.request(
                path="/storage/get_file_version",
                request=file_version_request,
            )

            if file_version_response.status_code != 200:
                raise InvalidReferenceError(f"Failed to get file {self.original_value}: {file_version_response.status_code} - {file_version_response.response_body}")

            return file_version_response.response_body["data"]

        if attribute_name == "file_name":
            return os.path.basename(self.original_value)

        elif attribute_name == "path":
            return self.original_value

        elif attribute_name == "parent_directory":
            return os.path.dirname(self.original_value)

        file_request = ObjectBody(
            schema=DescribeFileRequest,
            body={"file_path": self.original_value},
        )

        file_response = storage_client.request(
            path="/storage/describe_file",
            request=file_request,
        )

        if file_response.status_code != 200:
            raise ValueError(f"Failed to describe file {self.original_value}: {file_response.status_code} - {file_response.response_body}")

        return file_response.response_body[attribute_name]


_REFERENCE_TYPE_MAP = {
    "string": ReferenceValueString,
    "number": ReferenceValueNumber,
    "boolean": ReferenceValueBoolean,
    "list": ReferenceValueList,
    "object": ReferenceValueObject,
    "file": ReferenceValueFile,
}


class Reference:
    """
    Class for managing references resolutions in the system.
    """
    reference_type_map: Dict[str, callable] = _REFERENCE_TYPE_MAP

    def __init__(self, arguments: Dict[str, Any] = None, responses: Dict[str, ReferenceValueBase] = None):
        """
        Initialize the Reference object.

        Keyword arguments:
        arguments: Dictionary of argument values
        responses: Dictionary of execution responses

        """
        self.arguments = {}

        self.responses = responses or {}

        # Default load a set of arguments 
        if arguments:
            for key, value in arguments.items():
                inferred_type = self._infer_type_from_value(value)

                self.arguments[key] = self.reference_type_map[inferred_type](original_value=value)

    def _infer_type_from_value(self, value: Any) -> str:
        """
        Infer the reference type from a value.
        """
        if isinstance(value, bool):
            return "boolean"

        elif isinstance(value, (int, float)):
            return "number"

        elif isinstance(value, list):
            return "list"

        elif isinstance(value, dict):
            return "object"

        else:
            return "string"

    def add_response(self, execution_id: str, response_key: str, response_value: Any, response_type: str) -> None:
        """
        Add a response to the reference.

        Keyword arguments:
        execution_id -- The ID of the execution
        response_key -- The key of the response
        response_value -- The value of the response
        response_type -- The type of the response (e.g., "string", "number", etc.)
        """
        if execution_id not in self.responses:
            self.responses[execution_id] = {}

        self.responses[execution_id][response_key] = self.reference_type_map[response_type](
            original_value=response_value
        )

    def add_inferred_response(self, execution_id: str, response_key: str, response_value: Any) -> None:
        """
        Add a response with inferred type to the reference.

        Keyword arguments:
        execution_id -- The ID of the execution
        response_key -- The key of the response
        response_value -- The value of the response
        """
        inferred_type = self._infer_type_from_value(response_value)

        self.add_response(execution_id, response_key, response_value, inferred_type)

    def parse_ref(self, ref_string: str) -> Tuple[str, str, Optional[str]]:
        """
        Parse a REF string into context, key, and optional attribute.

        Keyword arguments:
        ref_string: The REF string to parse (e.g., "REF:arguments.input_file.path")

        Returns:
            Tuple of (context, key, attribute)
            - context: Either "arguments" or an execution_id
            - key: The main key to access
            - attribute: Optional attribute to access on the value (can be None)
        """
        if not ref_string.startswith("REF:"):
            raise InvalidReferenceError(f"Invalid REF string: {ref_string}")

        parts = ref_string[4:].split(".")

        if len(parts) < 2:
            raise InvalidReferenceError(f"Invalid REF string: {ref_string}")

        # Determine if this is arguments or response context
        if parts[0] == "arguments":
            context = "arguments"

            key = parts[1]

            attribute = parts[2] if len(parts) > 2 else None

        else:
            context = parts[0]  # execution_id

            key = parts[1]

            attribute = parts[2] if len(parts) > 2 else None

        return context, key, attribute

    def resolve(self, *, reference_string: str, token: Optional[str] = None) -> Any:
        """
        Resolve a REF string to its corresponding value.

        Keyword arguments:
        ref_string -- The REF string to resolve (e.g., "REF:arguments.input_file.path")
        token -- Optional token for file type references that require authentication
        """
        logging.debug(f"Resolving reference: {reference_string}")

        context, key, attribute = self.parse_ref(reference_string)

        if context == "arguments":
            logging.debug(f"Resolving argument: {key} from {self.arguments}")

            if key not in self.arguments:
                return None  # Handle missing arguments gracefully

            reference_obj = self.arguments[key]

            if reference_obj.requires_token:
                if not token:
                    raise ValueError(f"Token is required to dereference argument: {key}")

                return reference_obj.referenced_value(token=token, attribute_name=attribute)

            return reference_obj.referenced_value(attribute_name=attribute)

        # It's an execution_id
        if context not in self.responses:
            raise InvalidReferenceError(f"Execution ID: {context} not available for reference resolution")

        if key not in self.responses[context]:
            raise InvalidReferenceError(f"Execution ID: {context} does not have key: {key} for reference resolution")

        reference_obj = self.responses[context][key]

        if reference_obj.requires_token:
            if not token:
                # This needs to bubble up b/c this means something is broken in the code
                raise ValueError(f"Token is required to dereference: {key}")

            return reference_obj.referenced_value(token=token, attribute_name=attribute)

        return reference_obj.referenced_value(attribute_name=attribute)

    def set_arguments(self, arguments: Dict[str, Any], argument_types: Dict[str, str]):
        """
        Set arguments with explicit type information.

        Keyword arguments:
        arguments -- Dictionary of argument values
        argument_types -- Dictionary mapping argument names to their explicit types
        """
        self.arguments = {}

        for key, value in arguments.items():
            arg_type = argument_types.get(key, "string")

            if arg_type not in self.reference_type_map:

                if arg_type == "any":
                    # Infer type from value
                    arg_type = self._infer_type_from_value(value)

                    # use the inferred type
                    if arg_type not in self.reference_type_map:
                        raise ValueError(f"Cannot infer type for argument: {key} with value: {value}")

                else:
                    raise ValueError(f"Unknown argument type: {arg_type} for key: {key}")

            self.arguments[key] = self.reference_type_map[arg_type](original_value=value)