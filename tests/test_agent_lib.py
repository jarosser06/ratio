import json
import os
import pytest

from da_vinci.event_bus.tables.event_bus_responses import EventBusResponses

from ratio.agents.agent_lib import RatioSystem, SystemInitFailure

from ratio.client.requests.storage import (
    PutFileRequest,
    PutFileVersionRequest,
)

@pytest.fixture
def test_user_entity(create_test_entity):
    """Create a test user entity for agent tests"""

    entity = create_test_entity(
        entity_id="test_agent_user",
        description="Test user for agent tests"
    )

    return entity


@pytest.fixture
def test_token(create_client, test_user_entity):
    """Get a valid token for the test user"""

    client = create_client(test_user_entity)

    return client._acquired_token


@pytest.fixture
def working_dir(admin_client, home_directory):
    """Create a working directory for the agent tests"""

    working_dir_path = f"{home_directory}/agent_test_dir"

    create_req = PutFileRequest(
        file_path=working_dir_path,
        file_type="ratio::directory",
        permissions="644",
        owner="test_agent_user",
        group="test_agent_user",
    )

    # Create directory
    admin_client.request(
        request=create_req,
    )

    yield working_dir_path


class TestRatioSystem:
    """Basic test suite for the RatioSystem class"""

    def test_basic_initialization(self, test_token, working_dir):
        """Test basic initialization of the RatioSystem"""
        system = RatioSystem(
            parent_process_id="test-parent-id",
            process_id="test-process-id",
            token=test_token,
            working_directory=working_dir
        )

        # Verify system was initialized correctly
        assert system.parent_process_id == "test-parent-id"

        assert system.process_id == "test-process-id"

        assert system.working_directory == working_dir

        assert system._acquired_token == test_token

        assert system.claims is not None

        assert system.claims.entity == "test_agent_user"


class TestRatioSystemArguments:
    """Test suite for argument validation in RatioSystem"""

    def test_argument_validation_error_no_schema(self, test_token, working_dir):
        """Test validation error when arguments path is provided without schema"""
        # This should raise an error because we're providing arguments_path without schema
        with pytest.raises(SystemInitFailure):
            RatioSystem(
                parent_process_id="test-parent-id",
                process_id="test-process-id",
                token=test_token,
                working_directory=working_dir,
                arguments_path="/path/to/arguments.aio",
                argument_schema=None
            )

    def test_load_arguments_with_schema(self, test_token, working_dir, admin_client):
        """Test loading arguments with schema validation"""
        # Create an actual arguments file with the correct extension and type
        args_path = f"{working_dir}/test_args.aio"

        args_data = json.dumps({"file_for_review": f"{working_dir}/some_file.txt"})

        # Use PutFileRequest to create the file with the correct type
        admin_client.request(
            request=PutFileRequest(
                file_path=args_path,
                file_type="ratio::agent_io",
                permissions="644"
            )
        )

        # Use PutFileVersionRequest to put the content into the file
        admin_client.request(
            request=PutFileVersionRequest(
                file_path=args_path,
                data=args_data,
                metadata={
                    "FILE_PURPOSE": "testing"
                }
            )
        )

        # Define schema based on the Burt agent
        arg_schema = [
            {
                "name": "file_for_review",
                "type_name": "file",
                "description": "The file to be reviewed",
                "required": True
            }
        ]

        # Initialize the system with arguments
        system = RatioSystem(
            parent_process_id="test-parent-id",
            process_id="test-process-id",
            token=test_token,
            working_directory=working_dir,
            arguments_path=args_path,
            argument_schema=arg_schema
        )

        # Verify arguments were loaded correctly
        assert system.arguments is not None

        assert system.arguments["file_for_review"] == f"{working_dir}/some_file.txt"

        # Verify source file tracking
        assert len(system._source_files) == 1


class TestRatioSystemResponse:
    """Test suite for response handling in RatioSystem"""

    def test_respond_success(self, test_token, working_dir):
        """Test successful response handling"""
        # Define response schema based on the Burt agent
        response_schema = [
            {
                "name": "response",
                "type_name": "string",
                "description": "The response message",
                "required": True
            }
        ]

        # Initialize system with response schema
        system = RatioSystem(
            parent_process_id="test-parent-id",
            process_id="test-process-id",
            token=test_token,
            working_directory=working_dir,
            response_schema=response_schema
        )

        # Create a valid response body
        response_body = {"response": "This is Burt Macklin, FBI! I'm on the case!"}

        # Send the response
        system.success(
            response_body=response_body
        )

        # Verify the response files were created
        response_path = os.path.join(working_dir, "response.aio")

        file_info = system.describe_file(response_path)

        assert file_info["file_type"] == "ratio::agent_io"

        # Get the content to verify
        file_version = system.get_file_version(response_path)

        assert "data" in file_version

        saved_data = json.loads(file_version["data"])

        assert saved_data["response"] == "This is Burt Macklin, FBI! I'm on the case!"

    def test_respond_failure(self, test_token, working_dir):
        """Test failure response handling"""
        # Initialize system without response schema for failure case
        system = RatioSystem(
            parent_process_id="test-parent-id",
            process_id="test-process-id",
            token=test_token,
            working_directory=working_dir
        )

        # Send failure response
        failure_message = "Something went terribly wrong!"

        system.failure(failure_message=failure_message)

    def test_respond_validation_error(self, test_token, working_dir):
        """Test response validation error"""
        # Define response schema that requires a 'response' field
        response_schema = [
            {
                "name": "response",
                "type_name": "string",
                "description": "The response message",
                "required": True
            }
        ]

        # Initialize system with response schema
        system = RatioSystem(
            parent_process_id="test-parent-id",
            process_id="test-process-id",
            token=test_token,
            working_directory=working_dir,
            response_schema=response_schema
        )

        # Create an invalid response body (missing required 'response' field)
        invalid_response = {"wrong_field": "This won't work"}

        # This should raise an exception due to schema validation
        with pytest.raises(Exception):
            system.success(
                response_body=invalid_response
            )

    def test_burt_agent_response(self, test_token, working_dir):
        """Test specific response for the Burt Macklin agent"""
        # Define schema based on the Burt agent response definition
        response_schema = [
            {
                "name": "response",
                "type_name": "string",
                "description": "The response message",
                "required": True
            }
        ]

        # Initialize system with response schema
        system = RatioSystem(
            parent_process_id="test-parent-id",
            process_id="test-process-id",
            token=test_token,
            working_directory=working_dir,
            response_schema=response_schema
        )

        # Create a Burt Macklin-style response
        burt_response = {"response": "This is Burt Macklin, FBI! I've reviewed your file and found critical evidence!"}

        # Send the response
        system.success(
            response_body=burt_response
        )

        # Verify the response file was created with correct content
        response_path = os.path.join(working_dir, "response.aio")

        desc_resp = system.describe_file(response_path)

        assert desc_resp

        file_version = system.get_file_version(response_path)

        saved_data = json.loads(file_version["data"])

        assert "response" in saved_data

        assert "Burt Macklin" in saved_data["response"]