import pytest
import json
import os

from ratio.core.services.agent_manager.runtime.reference import (
    InvalidReferenceError,
    Reference,
    ReferenceValueString,
    ReferenceValueNumber,
    ReferenceValueBoolean,
    ReferenceValueList,
    ReferenceValueObject,
    ReferenceValueFile,
)

from ratio.client.requests.storage import (
    GetFileVersionRequest,
    PutFileRequest,
    PutFileVersionRequest,
)


class TestReferenceValueClasses:
    """Test suite for different ReferenceValue classes"""

    def test_reference_value_string(self):
        """Test ReferenceValueString class"""
        # Test with string value
        ref = ReferenceValueString(original_value="test_string")
        assert ref.referenced_value() == "test_string"
        
        # Test with non-string value that can be converted to string
        ref = ReferenceValueString(original_value=123)
        assert ref.referenced_value() == "123"
        
        # Test attribute access (should raise error)
        ref = ReferenceValueString(original_value="test_string")
        with pytest.raises(ValueError):
            ref.referenced_value(attribute_name="any_attribute")

    def test_reference_value_number(self):
        """Test ReferenceValueNumber class"""
        # Test with numeric value
        ref = ReferenceValueNumber(original_value=123)

        assert ref.referenced_value() == 123.0

        assert isinstance(ref.referenced_value(), float)

        # Test with string value that can be converted to number
        ref = ReferenceValueNumber(original_value="456")

        assert ref.referenced_value() == 456.0

        # Test attribute access (should raise error)
        ref = ReferenceValueNumber(original_value=123)

        with pytest.raises(ValueError):
            ref.referenced_value(attribute_name="any_attribute")

        # Test with invalid value
        ref = ReferenceValueNumber(original_value="not_a_number")

        with pytest.raises(ValueError):
            ref.referenced_value()

    def test_reference_value_boolean(self):
        """Test ReferenceValueBoolean class"""
        # Test with boolean values
        ref = ReferenceValueBoolean(original_value=True)

        assert ref.referenced_value() is True

        ref = ReferenceValueBoolean(original_value=False)

        assert ref.referenced_value() is False

        # Test with non-boolean values that evaluate to boolean
        ref = ReferenceValueBoolean(original_value=1)

        assert ref.referenced_value() is True

        ref = ReferenceValueBoolean(original_value=0)

        assert ref.referenced_value() is False

        # Test attribute access (should raise error)
        ref = ReferenceValueBoolean(original_value=True)

        with pytest.raises(ValueError):
            ref.referenced_value(attribute_name="any_attribute")

    def test_reference_value_list(self):
        """Test ReferenceValueList class"""
        # Prepare test data
        test_list = ["first", "second", "third"]
        
        # Test with no attribute
        ref = ReferenceValueList(original_value=test_list)
        assert ref.referenced_value() == test_list
        
        # Test length attribute
        assert ref.referenced_value(attribute_name="length") == 3
        
        # Test first and last attributes
        assert ref.referenced_value(attribute_name="first") == "first"
        assert ref.referenced_value(attribute_name="last") == "third"
        
        # Test index access
        assert ref.referenced_value(attribute_name="0") == "first"
        assert ref.referenced_value(attribute_name="1") == "second"
        assert ref.referenced_value(attribute_name="2") == "third"
        
        # Test out of range index
        with pytest.raises(ValueError):
            ref.referenced_value(attribute_name="3")
        
        # Test with empty list
        empty_ref = ReferenceValueList(original_value=[])
        assert empty_ref.referenced_value() == []
        
        # Attribute access with empty list should raise error
        with pytest.raises(ValueError):
            empty_ref.referenced_value(attribute_name="first")
        
        # Test is_int instance method
        # Call directly on instance
        assert ref.is_int("123") is True
        assert ref.is_int("-123") is True
        assert ref.is_int("abc") is False
        assert ref.is_int("12.3") is False

    def test_reference_value_object(self):
        """Test ReferenceValueObject class"""
        # Prepare test data
        test_dict = {"key1": "value1", "key2": 123, "key3": {"nested": "value"}}
        
        # Test with no attribute
        ref = ReferenceValueObject(original_value=test_dict)
        assert ref.referenced_value() == test_dict
        
        # Test attribute access
        assert ref.referenced_value(attribute_name="key1") == "value1"
        assert ref.referenced_value(attribute_name="key2") == 123
        assert ref.referenced_value(attribute_name="key3") == {"nested": "value"}
        
        # Test non-existent attribute
        assert ref.referenced_value(attribute_name="non_existent") is None
        
        # Test with empty dict
        empty_ref = ReferenceValueObject(original_value={})
        assert empty_ref.referenced_value() == {}
        
        # Attribute access with empty dict should raise error
        with pytest.raises(ValueError):
            empty_ref.referenced_value(attribute_name="any_key")


class TestReference:
    """Test suite for Reference class"""

    def test_init(self):
        """Test Reference initialization"""
        # Test with default values
        ref = Reference()
        assert ref.arguments == {}
        assert ref.responses == {}
        
        # Test with provided values
        test_args = {"key": "value"}
        test_responses = {"exec_id": {"resp_key": ReferenceValueString(original_value="response")}}
        ref = Reference(arguments=test_args, responses=test_responses)
        assert ref.arguments == test_args
        assert ref.responses == test_responses

    def test_add_response(self):
        """Test adding responses to the Reference object"""
        ref = Reference()
        
        # Add a string response
        ref.add_response("exec1", "result", "test_value", "string")
        assert "exec1" in ref.responses
        assert "result" in ref.responses["exec1"]
        assert isinstance(ref.responses["exec1"]["result"], ReferenceValueString)
        assert ref.responses["exec1"]["result"].original_value == "test_value"
        
        # Add a number response to the same execution_id
        ref.add_response("exec1", "count", 42, "number")
        assert "count" in ref.responses["exec1"]
        assert isinstance(ref.responses["exec1"]["count"], ReferenceValueNumber)
        assert ref.responses["exec1"]["count"].original_value == 42
        
        # Add a response to a different execution_id
        ref.add_response("exec2", "flag", True, "boolean")
        assert "exec2" in ref.responses
        assert "flag" in ref.responses["exec2"]
        assert isinstance(ref.responses["exec2"]["flag"], ReferenceValueBoolean)
        assert ref.responses["exec2"]["flag"].original_value is True

    def test_parse_ref(self):
        """Test parsing REF strings"""
        ref = Reference()
        
        # Test arguments context
        context, key, attribute = ref.parse_ref("REF:arguments.input_file")
        assert context == "arguments"
        assert key == "input_file"
        assert attribute is None
        
        # Test arguments context with attribute
        context, key, attribute = ref.parse_ref("REF:arguments.input_file.path")
        assert context == "arguments"
        assert key == "input_file"
        assert attribute == "path"
        
        # Test execution context
        context, key, attribute = ref.parse_ref("REF:exec_id.response")
        assert context == "exec_id"
        assert key == "response"
        assert attribute is None
        
        # Test execution context with attribute
        context, key, attribute = ref.parse_ref("REF:exec_id.file_list.first")
        assert context == "exec_id"
        assert key == "file_list"
        assert attribute == "first"
        
        # Test invalid REF format
        with pytest.raises(InvalidReferenceError):
            ref.parse_ref("not_a_ref")

    def test_resolve_arguments(self):
        """Test resolving REF strings from arguments context"""
        # Prepare test data
        test_args = {
            "input_file": "/path/to/file.txt",
            "options": {"format": "json", "verbose": True},
            "count": 42,
            "flags": ["a", "b", "c"]
        }

        ref = Reference(arguments=test_args)

        # Test simple argument resolution
        assert ref.resolve(reference_string="REF:arguments.input_file") == "/path/to/file.txt"

        assert ref.resolve(reference_string="REF:arguments.count") == 42
        
        # Test nested argument resolution
        assert ref.resolve(reference_string="REF:arguments.options") == {"format": "json", "verbose": True}
        
        # Test unknown argument
        with pytest.raises(InvalidReferenceError):
            ref.resolve(reference_string="REF:arguments.unknown")

    def test_resolve_responses(self):
        """Test resolving REF strings from response context"""
        # Prepare test data
        ref = Reference()
        ref.add_response("exec1", "output_file", "/path/to/output.txt", "string")
        ref.add_response("exec1", "results", [1, 2, 3], "list")
        ref.add_response("exec1", "metadata", {"status": "success"}, "object")
        
        # Test simple response resolution
        assert ref.resolve(reference_string="REF:exec1.output_file") == "/path/to/output.txt"
        
        # Test list response with attributes
        assert ref.resolve(reference_string="REF:exec1.results") == [1, 2, 3]
        list_length = ref.resolve(reference_string="REF:exec1.results.length")
        assert list_length == 3
        assert ref.resolve(reference_string="REF:exec1.results.first") == 1
        assert ref.resolve(reference_string="REF:exec1.results.last") == 3
        assert ref.resolve(reference_string="REF:exec1.results.0") == 1
        
        # Test object response with attributes
        assert ref.resolve(reference_string="REF:exec1.metadata") == {"status": "success"}
        assert ref.resolve(reference_string="REF:exec1.metadata.status") == "success"
        
        # Test unknown execution_id
        with pytest.raises(InvalidReferenceError):
            ref.resolve(reference_string="REF:unknown_exec.output")
        
        # Test unknown response key
        with pytest.raises(InvalidReferenceError):
            ref.resolve(reference_string="REF:exec1.unknown_key")


@pytest.mark.usefixtures("admin_client", "home_directory")
class TestReferenceFileOperations:
    """Test file operations with Reference class using admin_client"""

    def test_reference_value_file(self, admin_client, home_directory):
        """Test ReferenceValueFile class with actual file operations"""
        # Create a test file
        test_file_path = f"{home_directory}/ref_test_file.txt"
        test_content = "This is test content for reference file tests."

        # Create file
        file_req = PutFileRequest(
            file_path=test_file_path,
            file_type="ratio::file",
            permissions="644"
        )

        file_resp = admin_client.request(file_req)

        assert file_resp.status_code in [200, 201], "Failed to create test file"

        # Add content to file
        content_req = PutFileVersionRequest(
            data=test_content,
            file_path=test_file_path,
            metadata={"version": "1.0"},
        )

        content_resp = admin_client.request(content_req)

        assert content_resp.status_code in [200, 201], "Failed to add content to test file"

        # Create a ReferenceValueFile
        ref = ReferenceValueFile(original_value=test_file_path)

        # Test file attributes
        token = admin_client._acquired_token

        # Test file content
        content_req = GetFileVersionRequest(
            file_path=test_file_path,
        )

        content_resp = admin_client.request(content_req)

        assert content_resp.status_code == 200, "Failed to get file content"

        assert content_resp.response_body["data"] == test_content

        # Test file name attribute
        file_name = ref.referenced_value(token=token, attribute_name="file_name")

        assert file_name == "ref_test_file.txt"

        # Test path attribute
        path = ref.referenced_value(token=token, attribute_name="path")

        assert path == test_file_path

        # Test parent directory attribute
        parent_dir = ref.referenced_value(token=token, attribute_name="parent_directory")

        assert parent_dir == home_directory

    def test_complex_reference_resolution(self, admin_client, home_directory):
        """Test complex reference resolution including file references"""
        # Create test files
        file1_path = f"{home_directory}/ref_test_file1.txt"

        file2_path = f"{home_directory}/ref_test_file2.txt"

        # Create files
        for path in [file1_path, file2_path]:
            file_req = PutFileRequest(
                file_path=path,
                file_type="ratio::file",
                permissions="644"
            )

            file_resp = admin_client.request(file_req)

            assert file_resp.status_code in [200, 201], f"Failed to create test file {path}"

        # Add content to files
        content_req1 = PutFileVersionRequest(
            data="Content of file 1",
            file_path=file1_path,
            metadata={"version": "1.0"},
        )
        admin_client.request(content_req1)

        content_req2 = PutFileVersionRequest(
            data="Content of file 2",
            file_path=file2_path,
            metadata={"version": "1.0"},
        )

        admin_client.request(content_req2)

        # Create Reference with arguments and responses
        ref = Reference(
            arguments={
                "input_dir": home_directory,
                "input_file": file1_path,
                "file_list": [file1_path, file2_path]
            }
        )
        
        # Add file response
        ref.add_response("exec1", "output_file", file2_path, "file")
        
        # Get token for file operations
        token = admin_client._acquired_token

        # Test resolving file from arguments
        resolved_file_path = ref.resolve(reference_string="REF:arguments.input_file")
        assert resolved_file_path == file1_path
        
        # Test resolving file from responses
        resolved_response_file = ref.resolve(reference_string="REF:exec1.output_file", token=token)
        assert "Content of file 2" in resolved_response_file
        
        # Test resolving file attributes
        file_name = ref.resolve(reference_string="REF:exec1.output_file.file_name", token=token)

        assert file_name == "ref_test_file2.txt"
        
        # Test resolving from list
        file_list = ref.resolve(reference_string="REF:arguments.file_list")
        assert len(file_list) == 2

        assert file1_path in file_list

        assert file2_path in file_list
        
        # Test accessing arguments in a targeted way
        with pytest.raises(InvalidReferenceError):
            ref.resolve(reference_string="REF:arguments.file_list.first")

    def test_file_reference_requires_token(self, admin_client, home_directory):
        """Test that file references require a token"""
        # Create a test file
        test_file_path = f"{home_directory}/token_test_file.txt"

        # Create file
        file_req = PutFileRequest(
            file_path=test_file_path,
            file_type="ratio::file",
            permissions="644"
        )

        file_resp = admin_client.request(file_req)

        assert file_resp.status_code in [200, 201]

        # Add content
        content_req = PutFileVersionRequest(
            data="Testing token requirement",
            file_path=test_file_path,
            metadata={"version": "1.0"},
        )

        content_resp = admin_client.request(content_req)

        assert content_resp.status_code in [200, 201]

        # Create Reference with file response
        ref = Reference()

        ref.add_response("exec1", "output_file", test_file_path, "file")

        # Test that token is required
        with pytest.raises(ValueError):
            ref.resolve(reference_string="REF:exec1.output_file")
        
        # Test with token
        token = admin_client._acquired_token

        content = ref.resolve(reference_string="REF:exec1.output_file", token=token)

        assert content == "Testing token requirement"