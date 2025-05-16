import pytest
import logging

from ratio.core.services.agent_manager.runtime.agent import (
    AgentInstruction,
)

from ratio.core.services.agent_manager.runtime.validator import (
    RefValidator,
    RefTypeError,
    StringTypeHandler,
    ListTypeHandler,
    FileTypeHandler,
    ObjectTypeHandler,
    IntegerTypeHandler,
)


# Simple schema class for testing
class MockAgentDefinition:
    def __init__(self, attribute_definitions=None, response_definitions=None):
        self.attribute_definitions = attribute_definitions or []

        self.response_definitions = response_definitions or []


class TestRefValidator:
    """Test suite for REF references validator module"""

    @pytest.fixture
    def validator(self):
        """Create a clean validator instance for testing"""
        return RefValidator()

    @pytest.fixture
    def test_schema(self):
        """Create a test schema for instructions"""
        return MockAgentDefinition(
            attribute_definitions=[
                {"name": "input_file", "type": "file"},
                {"name": "file_input", "type": "file"},
                {"name": "options", "type": "object"},
                {"name": "format_option", "type": "string"},
                {"name": "count", "type": "integer"},
            ],

            response_definitions=[
                {"name": "output_file", "type": "file"},
                {"name": "success", "type": "string"},
                {"name": "results", "type": "list"},
            ]
        )

    @pytest.fixture
    def test_instruction(self, test_schema):
        """Create a test agent instruction"""
        return AgentInstruction(
            execution_id="test_exec_id",
            provided_arguments={
                "input_file": "REF:arguments.file_input",
                "options": {"format": "REF:arguments.format_option"},
            },
            definition=test_schema
        )

    def test_extract_refs(self, validator):
        """Test extracting REF references from different value types"""
        # Test string reference
        assert validator.extract_refs("REF:arguments.input_file") == ["REF:arguments.input_file"]

        # Test nested dictionary reference
        nested_dict = {
            "key1": "value1",
            "key2": "REF:arguments.option",
            "nested": {
                "inner_key": "REF:execution.context"
            }
        }

        extracted = validator.extract_refs(nested_dict)
        assert len(extracted) == 2

        assert "REF:arguments.option" in extracted

        assert "REF:execution.context" in extracted

        # Test list reference
        list_value = [
            "item1", 
            {"key": "REF:arguments.list_item"}, 
            "REF:execution.id"
        ]

        extracted = validator.extract_refs(list_value)

        assert len(extracted) == 2

        assert "REF:arguments.list_item" in extracted

        assert "REF:execution.id" in extracted

        # Test non-ref string
        assert validator.extract_refs("Not a reference") == []

    def test_parse_ref(self, validator):
        """Test parsing REF strings into base and path components"""
        # Simple reference
        base, path = validator.parse_ref("REF:arguments.input_file")

        assert base == "arguments"

        assert path == ["input_file"]

        # Complex path reference
        base, path = validator.parse_ref("REF:prev_exec.response.file_list.first")

        assert base == "prev_exec"

        assert path == ["response", "file_list", "first"]

        # Reference with no path
        base, path = validator.parse_ref("REF:execution")

        assert base == "execution"

        assert path == []

        # Invalid reference
        with pytest.raises(ValueError):
            validator.parse_ref("invalid_reference")

    def test_register_agent_instruction(self, validator, test_instruction):
        """Test registering an agent instruction in the execution context"""
        validator.register_agent_instruction(
            test_instruction.execution_id, 
            test_instruction
        )

        assert "test_exec_id" in validator.execution_context

        assert validator.execution_context["test_exec_id"] == test_instruction

    def test_resolve_type(self, validator):
        """Test resolving types based on base type and accessors"""
        # File with file accessors
        resolved_type = validator.resolve_type("file", ["file_name"])

        assert resolved_type == "string"

        # List with index accessor
        resolved_type = validator.resolve_type("list", ["0"])

        assert resolved_type == "string"

        # List with special accessor
        resolved_type = validator.resolve_type("list", ["first"])

        assert resolved_type == "string"

        # Object with property accessor
        resolved_type = validator.resolve_type("object", ["property"])

        assert resolved_type == "string"

        # Multiple accessors
        resolved_type = validator.resolve_type("file", ["metadata", "version"])

        assert resolved_type == "string"

        # Unknown type (falls back to string)
        # Capture the log warning
        log_captured = []

        class TestHandler(logging.Handler):
            def emit(self, record):
                log_captured.append(record.getMessage())

        logger = logging.getLogger()

        test_handler = TestHandler()

        logger.addHandler(test_handler)

        resolved_type = validator.resolve_type("unknown_type", ["accessor"])

        assert resolved_type == "string"

        assert any("Unknown type: unknown_type" in msg for msg in log_captured)

        logger.removeHandler(test_handler)

    def test_are_types_compatible(self, validator):
        """Test type compatibility checking"""
        # Same types are compatible
        assert validator.are_types_compatible("string", "string") == True

        assert validator.are_types_compatible("file", "file") == True

        # String can be used as object
        assert validator.are_types_compatible("string", "object") == True

        # List can be used as list or object
        assert validator.are_types_compatible("list", "list") == True

        assert validator.are_types_compatible("list", "object") == True

        # File can be used as string or object
        assert validator.are_types_compatible("file", "string") == True

        assert validator.are_types_compatible("file", "object") == True

        # Integer can be used as string or object
        assert validator.are_types_compatible("integer", "string") == True

        assert validator.are_types_compatible("integer", "object") == True

        # Types that aren't compatible
        assert validator.are_types_compatible("string", "list") == False

        assert validator.are_types_compatible("list", "file") == False

    def test_get_ref_type(self, validator, test_instruction, test_schema):
        """Test determining REF reference types"""
        # Register instruction in context
        validator.register_agent_instruction(
            test_instruction.execution_id, 
            test_instruction
        )

        validator.execution_context["current_execution_id"] = test_instruction.execution_id

        # Test arguments reference
        ref_type = validator.get_ref_type("REF:arguments.file_input")

        assert ref_type == "file"

        # Test execution context reference
        ref_type = validator.get_ref_type("REF:execution")

        assert ref_type == "string"

        # Test agent response reference
        # First register another agent in context
        prev_instruction = AgentInstruction(
            execution_id="prev_exec",
            definition=test_schema
        )

        validator.register_agent_instruction("prev_exec", prev_instruction)

        ref_type = validator.get_ref_type("REF:prev_exec.response.output_file")

        assert ref_type == "file"

        # Test reference with accessors
        ref_type = validator.get_ref_type("REF:prev_exec.response.results.first")

        assert ref_type == "string"  # List element type

        # Test invalid references
        with pytest.raises(ValueError):
            validator.get_ref_type("REF:unknown_context")

        with pytest.raises(ValueError):
            validator.get_ref_type("REF:arguments")

        with pytest.raises(ValueError):
            validator.get_ref_type("REF:prev_exec.invalid")

    def test_validate_instruction_argument(self, validator, test_instruction):
        """Test validating a single instruction argument"""
        # Register instruction in context
        validator.register_agent_instruction(
            test_instruction.execution_id, 
            test_instruction
        )

        validator.execution_context["current_execution_id"] = test_instruction.execution_id

        # Valid reference - compatible types
        # Override arguments to use a valid reference
        test_instruction.provided_arguments["input_file"] = "REF:arguments.file_input"

        errors = validator.validate_instruction_argument(
            test_instruction.execution_id,
            "input_file",
            test_instruction.provided_arguments["input_file"]
        )

        assert len(errors) == 0

        # Invalid reference - incompatible types
        # Override arguments to use an incompatible reference
        test_instruction.provided_arguments["input_file"] = "REF:arguments.format_option"

        errors = validator.validate_instruction_argument(
            test_instruction.execution_id,
            "input_file",  # Expects 'file' type
            test_instruction.provided_arguments["input_file"]  # References 'string' type
        )

        assert len(errors) == 1

        assert isinstance(errors[0], RefTypeError)

        assert errors[0].expected_type == "file"

        assert errors[0].actual_type == "string"

    def test_validate_instruction(self, validator, test_instruction):
        """Test validating all arguments in an instruction"""
        # Register instruction in context
        validator.register_agent_instruction(
            test_instruction.execution_id, 
            test_instruction
        )

        validator.execution_context["current_execution_id"] = test_instruction.execution_id

        # Setup one valid and one invalid argument
        test_instruction.provided_arguments = {
            "input_file": "REF:arguments.file_input",  # Valid
            "count": "REF:arguments.format_option"  # Invalid - type mismatch
        }

        errors = validator.validate_instruction(test_instruction)

        # Should find one error (for count argument)
        assert len(errors) == 1

        assert errors[0].expected_type == "integer"

        assert errors[0].actual_type == "string"

    def test_validate_instructions(self, validator, test_schema):
        """Test validating a list of instructions"""
        # Create test instructions
        instr1 = AgentInstruction(
            execution_id="exec1",
            provided_arguments={
                "input_file": "REF:arguments.format_option"  # Type mismatch
            },
            definition=test_schema
        )

        instr2 = AgentInstruction(
            execution_id="exec2",
            provided_arguments={
                "input_file": "REF:arguments.file_input"  # Valid
            },
            definition=test_schema
        )

        # Register instructions
        validator.register_agent_instruction("exec1", instr1)

        validator.register_agent_instruction("exec2", instr2)

        validator.execution_context["current_execution_id"] = "exec1"  # Current execution

        errors = validator.validate_instructions([instr1, instr2])

        # Should find errors only in first instruction
        assert "exec1" in errors

        assert "exec2" not in errors

        assert len(errors["exec1"]) == 1


class TestTypeHandlers:
    """Test suite for type handlers"""

    def test_string_type_handler(self):
        """Test string type handler"""
        # Output type is always string regardless of accessor
        assert StringTypeHandler.get_output_type("any_accessor") == "string"

        # Compatibility
        assert StringTypeHandler.is_compatible_with("string") == True

        assert StringTypeHandler.is_compatible_with("object") == True

        assert StringTypeHandler.is_compatible_with("list") == False

    def test_list_type_handler(self):
        """Test list type handler"""
        # Index accessor returns element type
        assert ListTypeHandler.get_output_type("0") == "string"

        # Special accessors return element type
        assert ListTypeHandler.get_output_type("first") == "string"

        assert ListTypeHandler.get_output_type("last") == "string"

        # Other accessors keep list type
        assert ListTypeHandler.get_output_type("random") == "list"

        # Compatibility
        assert ListTypeHandler.is_compatible_with("list") == True

        assert ListTypeHandler.is_compatible_with("object") == True

        assert ListTypeHandler.is_compatible_with("string") == False

    def test_file_type_handler(self):
        """Test file type handler"""
        # Metadata accessors return string
        assert FileTypeHandler.get_output_type("file_name") == "string"

        assert FileTypeHandler.get_output_type("file_path") == "string"

        assert FileTypeHandler.get_output_type("full_path") == "string"

        # Metadata accessor returns object
        assert FileTypeHandler.get_output_type("metadata") == "object"

        # Default returns string (file content)
        assert FileTypeHandler.get_output_type("random") == "string"

        # Compatibility
        assert FileTypeHandler.is_compatible_with("file") == True

        assert FileTypeHandler.is_compatible_with("string") == True

        assert FileTypeHandler.is_compatible_with("object") == True

        assert FileTypeHandler.is_compatible_with("list") == False

    def test_object_type_handler(self):
        """Test object type handler"""
        # Property access returns string by default
        assert ObjectTypeHandler.get_output_type("any_property") == "string"

        # Compatibility
        assert ObjectTypeHandler.is_compatible_with("object") == True

        assert ObjectTypeHandler.is_compatible_with("string") == False

    def test_integer_type_handler(self):
        """Test integer type handler"""
        # Output type is always integer regardless of accessor
        assert IntegerTypeHandler.get_output_type("any_accessor") == "integer"

        # Compatibility
        assert IntegerTypeHandler.is_compatible_with("integer") == True

        assert IntegerTypeHandler.is_compatible_with("string") == True

        assert IntegerTypeHandler.is_compatible_with("object") == True

        assert IntegerTypeHandler.is_compatible_with("list") == False


class TestRefTypeError:
    """Test suite for RefTypeError class"""

    def test_ref_type_error_creation(self):
        """Test creating a RefTypeError instance"""
        error = RefTypeError("REF:path.to.something", "expected_type", "actual_type")

        assert error.ref_path == "REF:path.to.something"

        assert error.expected_type == "expected_type"

        assert error.actual_type == "actual_type"

        assert "Type mismatch in REF" in str(error)

    def test_ref_type_error_string_representation(self):
        """Test string representation of RefTypeError"""
        error = RefTypeError("REF:arguments.input", "file", "string")

        expected_message = "Type mismatch in REF 'REF:arguments.input': expected file, but would receive string"

        assert str(error) == expected_message

        assert error.message == expected_message