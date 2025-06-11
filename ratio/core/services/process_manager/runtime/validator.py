"""
Reference validation module for tool instructions.
"""
import re
import logging
from typing import Any, Dict, List, Tuple

from ratio.core.services.process_manager.runtime.tool import ToolInstruction


class RefTypeError:
    """Represents a type mismatch in REF resolution."""

    def __init__(self, ref_path: str, expected_type: str, actual_type: str):
        self.ref_path = ref_path

        self.expected_type = expected_type

        self.actual_type = actual_type

        self.message = f"Type mismatch in REF '{ref_path}': expected {expected_type}, but would receive {actual_type}"

    def __str__(self):
        return self.message


class StringTypeHandler:
    """Handler for string type."""

    @staticmethod
    def get_output_type(accessor: str) -> str:
        # Strings don't have accessors that change their type
        return "string"

    @staticmethod
    def is_compatible_with(target_type: str) -> bool:
        # Strings can be used as strings or parts of objects
        return target_type in {"string", "object"}


class ListTypeHandler:
    """Handler for list type."""

    @staticmethod
    def get_output_type(accessor: str) -> str:
        # Check if accessing element by index or special accessors
        if accessor in {"first", "last"} or accessor.isdigit():

            # Return element type (assuming string elements for simplicity)
            return "string"
        return "list"

    @staticmethod
    def is_compatible_with(target_type: str) -> bool:
        # Lists can be used as lists or objects
        return target_type in {"list", "object"}


class FileTypeHandler:
    """Handler for file type."""

    @staticmethod
    def get_output_type(accessor: str) -> str:
        # File metadata accessors return strings
        if accessor in {"file_name", "path", "parent_directory", "added_on", "owner", "group", "permissions"}:
            return "string"

        elif accessor == "metadata":
            return "object"

        # Default behavior is to return the file content as a string
        return "string"

    @staticmethod
    def is_compatible_with(target_type: str) -> bool:
        # Files can be used as strings (content) or objects
        return target_type in {"file", "string", "object"}


class ObjectTypeHandler:
    """Handler for object type."""

    @staticmethod
    def get_output_type(accessor: str) -> str:
        # Without specific schema information, assume property access returns string
        return "string"

    @staticmethod
    def is_compatible_with(target_type: str) -> bool:
        # Objects can only be used as objects
        return target_type in {"object"}


class IntegerTypeHandler:
    """Handler for integer type."""

    @staticmethod
    def get_output_type(accessor: str) -> str:
        # Integers don't have accessors that change their type
        return "integer"

    @staticmethod
    def is_compatible_with(target_type: str) -> bool:
        # Integers can be used as integers, strings (coerced), or objects
        return target_type in {"integer", "string", "object"}


class RefValidator:
    """
    Validates REF references in tool instructions to ensure type consistency.
    """

    # Regular expression to match REF patterns
    REF_PATTERN = re.compile(r"REF:([a-zA-Z0-9_\-.]+)(?:\.([a-zA-Z0-9_\-.]+))*")

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Register type handlers
        self.type_handlers = {
            "string": StringTypeHandler,
            "list": ListTypeHandler,
            "file": FileTypeHandler,
            "object": ObjectTypeHandler,
            "integer": IntegerTypeHandler,
        }

        # Execution context mapping execution_ids to ToolInstruction objects
        self.execution_context = {}

    def extract_refs(self, value: Any) -> List[str]:
        """
        Extract all REF references from a value, handling nested structures.

        Args:
            value: Value to inspect for REF references

        Returns:
            List of REF reference strings
        """
        refs = []

        if isinstance(value, str) and value.startswith("REF:"):
            refs.append(value)

        elif isinstance(value, dict):
            for v in value.values():
                refs.extend(self.extract_refs(v))

        elif isinstance(value, list):
            for item in value:
                refs.extend(self.extract_refs(item))

        return refs

    def parse_ref(self, ref_string: str) -> Tuple[str, List[str]]:
        """
        Parse a REF string into its base and path components.
        
        Keyword arguments:
        ref_string -- The REF string to parse (e.g., "REF:arguments.input_file")

        Returns:
            Tuple of (base_context, path_components)
        """
        if not ref_string.startswith("REF:"):
            raise ValueError(f"Invalid REF string: {ref_string}")

        parts = ref_string[4:].split(".")

        base_context = parts[0]

        path_components = parts[1:] if len(parts) > 1 else []
        
        return base_context, path_components

    def register_tool_instruction(self, execution_id: str, tool_instruction: ToolInstruction):
        """
        Register an tool instruction in the execution context.
        
        Keyword arguments:
        execution_id -- The execution ID of the instruction
        tool_instruction -- The instruction to register
        """
        self.execution_context[execution_id] = tool_instruction

    def resolve_type(self, base_type: str, accessors: List[str]) -> str:
        """
        Resolve the type of a REF reference based on its base type and accessors.

        Keyword arguments:
        base_type -- The base type of the REF reference
        accessors -- The accessors to apply to the base type
        """
        current_type = base_type
        
        for accessor in accessors:
            if current_type not in self.type_handlers:
                self.logger.warning(f"Unknown type: {current_type}, assuming string")

                current_type = "string"

            # Use the appropriate handler class's static method
            handler_class = self.type_handlers[current_type]

            current_type = handler_class.get_output_type(accessor)

        return current_type

    def are_types_compatible(self, source_type: str, target_type: str) -> bool:
        """
        Check if the source type is compatible with the target type.
        
        Keyword arguments:
        source_type -- Type provided by the REF
        target_type -- Type expected by the argument

        Returns:
            True if compatible, False otherwise
        """
        if source_type == target_type:
            return True

        if source_type not in self.type_handlers:
            self.logger.warning(f"Unknown source type: {source_type}, assuming incompatible")
            return False

        # Use the type handler to check compatibility
        return self.type_handlers[source_type].is_compatible_with(target_type)

    def get_ref_type(self, ref_string: str) -> str:
        """
        Determine the type that a REF reference will resolve to.

        Keyword arguments:
        ref_string -- The REF string to resolve (e.g., "REF:arguments.input_file")

        Returns:
            Type that the reference will resolve to
        """
        base_context, path_components = self.parse_ref(ref_string)

        if base_context == "arguments":
            # Handle arguments context
            if not path_components:
                raise ValueError("Invalid arguments REF: missing argument name")

            arg_name = path_components[0]

            current_execution_id = self.execution_context.get("current_execution_id")

            if not current_execution_id or current_execution_id not in self.execution_context:
                raise ValueError("No current execution context")

            current_tool = self.execution_context[current_execution_id]

            # Get argument type from schema
            arg_def = next((arg for arg in current_tool.definition.attribute_definitions 
                          if arg.get("name") == arg_name), None)

            if not arg_def:
                raise ValueError(f"Unknown argument: {arg_name}")

            base_type = arg_def.get("type", "string")

            # Resolve type with remaining path components
            return self.resolve_type(base_type, path_components[1:])

        elif base_context == "execution":
            # Execution context typically returns strings
            return "string"

        else:
            # Handle tool responses
            if base_context not in self.execution_context:
                raise ValueError(f"Unknown execution ID: {base_context}")

            if not path_components or path_components[0] != "response":
                raise ValueError(f"Invalid response REF: should be <execution_id>.response.<key>")

            if len(path_components) < 2:
                raise ValueError(f"Invalid response REF: missing response key")

            response_key = path_components[1]

            tool = self.execution_context[base_context]

            # Get response type from schema
            resp_def = next((resp for resp in tool.definition.response_definitions 
                           if resp.get("name") == response_key), None)

            if not resp_def:
                raise ValueError(f"Unknown response key: {response_key}")

            base_type = resp_def.get("type", "string")

            # Resolve type with remaining path components
            return self.resolve_type(base_type, path_components[2:])

    def validate_instruction_argument(self, execution_id: str, arg_name: str, arg_value: Any) -> List[RefTypeError]:
        """
        Validate a single argument in an tool instruction for REF type consistency.

        Keyword arguments:
        execution_id -- The execution ID of the instruction
        arg_name -- The name of the argument to validate
        arg_value -- The value of the argument to validate

        Returns:
            List of type errors found
        """
        errors = []

        # Set current execution context
        self.execution_context["current_execution_id"] = execution_id

        # Get expected argument type
        tool = self.execution_context.get(execution_id)

        if not tool:
            self.logger.warning(f"Unknown execution ID: {execution_id}")
            return errors

        # Find argument definition in schema
        arg_def = next((arg for arg in tool.definition.attribute_definitions 
                    if arg.get("name") == arg_name), None)

        if not arg_def:
            self.logger.warning(f"Unknown argument: {arg_name} for execution ID: {execution_id}")
            return errors

        expected_type = arg_def.get("type", "string")

        # Extract and validate all REFs in the argument value
        refs = self.extract_refs(arg_value)

        for ref in refs:
            try:
                actual_type = self.get_ref_type(ref)

                handler_class = self.type_handlers.get(actual_type)

                if not handler_class or not handler_class.is_compatible_with(expected_type):
                    errors.append(RefTypeError(
                        ref_path=ref,
                        expected_type=expected_type,
                        actual_type=actual_type
                    ))

            except ValueError as e:
                self.logger.warning(f"Invalid REF: {str(e)}")
                errors.append(RefTypeError(
                    ref_path=ref,
                    expected_type=expected_type,
                    actual_type="<invalid>"
                ))

        # Return all errors found in this argument
        return errors

    def validate_instruction(self, tool_instruction: ToolInstruction) -> List[RefTypeError]:
        """
        Validate all REF references in an tool instruction.

        Keyword arguments:
        tool_instruction -- The tool instruction to validate
            
        Returns:
            List of type errors found
        """
        errors = []

        execution_id = tool_instruction.execution_id

        # Register instruction in execution context
        self.register_tool_instruction(execution_id, tool_instruction)

        # Validate each argument
        for arg_name, arg_value in tool_instruction.provided_arguments.items():
            errors.extend(self.validate_instruction_argument(execution_id, arg_name, arg_value))

        return errors

    def validate_instructions(self, instructions: List) -> Dict[str, List[RefTypeError]]:
        """
        Validate a list of tool instructions for REF type consistency.

        Keyword arguments:
        instructions -- List of tool instructions to validate

        Returns:
            Dictionary mapping execution IDs to lists of errors
        """
        all_errors = {}

        # First, register all instructions
        for instruction in instructions:
            self.register_tool_instruction(instruction.execution_id, instruction)

        # Then validate each instruction
        for instruction in instructions:
            errors = self.validate_instruction(instruction)

            if errors:
                all_errors[instruction.execution_id] = errors

        return all_errors