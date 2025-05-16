# test_agent_execution.py
import pytest
import time

import json

from ratio.client.requests.agent import (
    DescribeProcessRequest,
    ExecuteAgentRequest,
)

from ratio.client.requests.storage import (
    GetFileVersionRequest,
    PutFileRequest,
    PutFileVersionRequest,
)


class TestAgentExecution:
    """Test suite for Agent execution functionality"""

    def test_execute_agent_with_definition(self, admin_client):
        """Test executing an agent with an inline definition"""
        # Create a sample agent definition
        agent_definition = {
            "arguments": [
                {
                    "type_name": "file",
                    "description": "Path to a file Burt should respond about. Optional",
                    "name": "file_for_review",
                    "required": False
                }
            ],
            "description": "This is the Burt Macklin agent. It provides a simple response",
            "responses": [
                {
                    "type_name": "string",
                    "description": "The response Burt provides",
                    "name": "response",
                    "required": True
                }
            ],
            "system_event_endpoint": "ratio::agent::andy::execution"
        }

        # Execute the agent with the inline definition
        execute_request = ExecuteAgentRequest(
            agent_definition=agent_definition,
            arguments={"test_arg": "test_value"}
        )

        response = admin_client.request(request=execute_request)

        assert response is not None

        assert response.status_code == 200, f"Unable to execute agent"

    def test_execute_agent_with_file_path(self, admin_client, home_directory):
        """Test executing an agent using a definition file path"""
        # Define the agent definition file path in the home directory
        agent_def_path = f"{home_directory}/test.agent"
        
        agent_definition = {
            "arguments": [
                {
                    "type_name": "file",
                    "description": "Path to a file Burt should respond about. Optional",
                    "name": "file_for_review",
                    "required": False
                }
            ],
            "description": "This is the Burt Macklin agent. It provides a simple response",
            "responses": [
                {
                    "type_name": "string",
                    "description": "The response Burt provides",
                    "name": "response",
                    "required": True
                }
            ],
            "system_event_endpoint": "ratio::agent::andy::execution"
        }
        
        # Write definition to file using the system's file operations
        create_file_req = PutFileRequest(
            file_path=agent_def_path,
            file_type="ratio::agent",
            permissions="755"
        )
        create_resp = admin_client.request(create_file_req)

        assert create_resp.status_code in [200, 201], "Unable to create agent definition file"
        
        # Write content to the file
        content_req = PutFileVersionRequest(
            data=json.dumps(agent_definition),
            file_path=agent_def_path,
            metadata={"version": "1.0"},
        )

        content_resp = admin_client.request(content_req)

        assert content_resp.status_code in [200, 201], "Unable to write content to the agent definition file"

        # Validate content was written correctly
        read_req = GetFileVersionRequest(
            file_path=agent_def_path,
        )

        read_resp = admin_client.request(read_req)

        assert read_resp.status_code == 200, "Unable to read agent definition file"

        assert read_resp.response_body["data"] == json.dumps(agent_definition), "Agent definition file content mismatch"

        # Execute agent with the file path
        execute_request = ExecuteAgentRequest(
            agent_definition_path=agent_def_path,
            arguments={"input_value": "test_input"}
        )
        
        response = admin_client.request(request=execute_request)

        assert response.status_code == 200, "Unable to execute agent with file path"

    def test_execute_as_parameter(self, admin_client, create_test_entity, create_client, home_directory):
        """Test executing an agent with the execute_as parameter"""
        # Create a test user
        test_user = create_test_entity("agent_test_user")

        user_client = create_client(test_user)
        
        # Create a basic agent definition
        agent_definition = {
            "arguments": [
                {
                    "type_name": "file",
                    "description": "Path to a file Burt should respond about. Optional",
                    "name": "file_for_review",
                    "required": False
                }
            ],
            "description": "This is the Burt Macklin agent. It provides a simple response",
            "responses": [
                {
                    "type_name": "string",
                    "description": "The response Burt provides",
                    "name": "response",
                    "required": True
                }
            ],
            "system_event_endpoint": "ratio::agent::andy::execution"
        }
        
        # 1. Test admin executing as another user
        execute_request = ExecuteAgentRequest(
            agent_definition=agent_definition,
            execute_as=test_user.entity_id,
            working_directory="/home/agent_test_user"  # Specify the working directory since the system will try to execute in root dir otherwise
        )
        
        response = admin_client.request(request=execute_request)
        
        assert response.status_code == 200, "Admin unable to execute agent as another user"
        
        execute_request = ExecuteAgentRequest(
            agent_definition=agent_definition,
            execute_as="admin"  # Try to execute as admin
        )
        
        # This should fail for a regular user
        response = user_client.request(request=execute_request, raise_for_status=False)
        
        assert response.status_code in [401, 403], "Non-admin user should not be able to execute agent as another user"

    def test_working_directory(self, admin_client, home_directory):
        """Test executing an agent with a specific working directory"""
        # Create a test directory structure
        test_dir_path = f"{home_directory}/agent_test_dir"

        test_file_path = f"{test_dir_path}/test_file.txt"
        
        # Create directory
        dir_req = PutFileRequest(
            file_path=test_dir_path,
            file_type="ratio::directory",
            permissions="755"
        )

        dir_resp = admin_client.request(dir_req)

        assert dir_resp.status_code in [200, 201], "Failed to create test directory"

        # Create test file in directory
        file_req = PutFileRequest(
            file_path=test_file_path,
            file_type="ratio::file",
            permissions="644"
        )

        file_resp = admin_client.request(file_req)

        assert file_resp.status_code in [200, 201], "Failed to create test file"

        # Add content to the file
        content_req = PutFileVersionRequest(
            data="Test file content for working directory test",
            file_path=test_file_path,
            metadata={"version": "1.0"},
        )

        content_resp = admin_client.request(content_req)

        assert content_resp.status_code in [200, 201], "Failed to add content to test file"

        # Create an agent definition that interacts with the working directory
        agent_definition = {
            "arguments": [
                {
                    "type_name": "file",
                    "description": "Path to a file Burt should respond about. Optional",
                    "name": "file_for_review",
                    "required": False
                }
            ],
            "description": "This is the Burt Macklin agent. It provides a simple response",
            "responses": [
                {
                    "type_name": "string",
                    "description": "The response Burt provides",
                    "name": "response",
                    "required": True
                }
            ],
            "system_event_endpoint": "ratio::agent::andy::execution"
        }

        # Execute the agent with the working directory
        execute_request = ExecuteAgentRequest(
            agent_definition=agent_definition,
            working_directory=test_dir_path
        )

        response = admin_client.request(request=execute_request)

        assert response.status_code == 200, "Failed to execute agent with working directory"

    def test_execute_composite_agent(self, admin_client, home_directory):
        """Test executing a composite agent"""
        agent_def_path = f"{home_directory}/test.agent"
        
        agent_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "The thing Burt should respond about.",
                    "name": "text_input",
                    "required": False
                }
            ],
            "description": "This is the Burt Macklin agent. It provides a simple response",
            "responses": [
                {
                    "type_name": "string",
                    "description": "The response Burt provides",
                    "name": "response",
                    "required": True
                }
            ],
            "system_event_endpoint": "ratio::agent::andy::execution"
        }
        
        # Write definition to file using the system's file operations
        create_file_req = PutFileRequest(
            file_path=agent_def_path,
            file_type="ratio::agent",
            permissions="755"
        )
        create_resp = admin_client.request(create_file_req)

        assert create_resp.status_code in [200, 201], "Unable to create agent definition file"
        
        # Write content to the file
        content_req = PutFileVersionRequest(
            data=json.dumps(agent_definition),
            file_path=agent_def_path,
            metadata={"version": "1.0"},
        )

        content_resp = admin_client.request(content_req)

        assert content_resp.status_code in [200, 201], "Unable to write content to the agent definition file"

        # Create a composite agent definition
        composite_agent_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the composite agent",
                    "name": "input_value",
                    "required": True
                }
            ],
            "description": "This is a composite agent that executes multiple agents",
            "instructions": [
                {
                    "agent_definition": {
                        "arguments": [
                            {
                                "type_name": "string",
                                "description": "Input value for the inner agent",
                                "name": "inner_input",
                                "required": True
                            }
                        ],
                        "description": "Inner agent that processes input",
                        "responses": [
                            {
                                "type_name": "string",
                                "description": "Response from Burt",
                                "name": "response",
                                "required": True
                            }
                        ],
                        "system_event_endpoint": "ratio::agent::andy::execution"
                    },
                    "arguments": {
                        "inner_input": "REF:arguments.input_value"
                    },
                    "execution_id": "inner_agent_execution"
                },
                {
                    "agent_definition_path": agent_def_path,
                    "arguments": {
                        "text_input": "REF:inner_agent_execution.response"
                    },
                    "execution_id": "other_agent_execution"
                }
            ],
            "response_reference_map": {
                "composite_response": "REF:other_agent_execution.response",
                "inner_response": "REF:inner_agent_execution.response"
            },
            "responses": [
                {
                    "type_name": "string",
                    "description": "Response from the composite agent",
                    "name": "composite_response",
                    "required": True
                },
                {
                    "type_name": "string",
                    "description": "Response from the inner agent",
                    "name": "inner_response",
                    "required": True
                }
            ],
        }

        # Execute the composite agent
        execute_request = ExecuteAgentRequest(
            agent_definition=composite_agent_definition,
            arguments={"input_value": "test_input_1"}
        )

        response = admin_client.request(request=execute_request)

        assert response.status_code == 200, f"Unable to execute composite agent: {response.error_message}"

    def test_t1_agent_run(self, admin_client):
        """Test executing an agent with a run_id"""
        # Create a sample agent definition
        agent_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the agent",
                    "name": "input_value",
                    "required": True
                }
            ],
            "description": "This is the Burt Macklin agent. It provides a simple response",
            "responses": [
                {
                    "type_name": "string",
                    "description": "The response Burt provides",
                    "name": "response",
                    "required": True
                }
            ],
            "system_event_endpoint": "ratio::agent::andy::execution"
        }

        # Execute the agent with a run_id
        execute_request = ExecuteAgentRequest(
            agent_definition=agent_definition,
            arguments={"input_value": "test_input"},
        )

        response = admin_client.request(request=execute_request)

        assert response.status_code == 200, f"Unable to execute agent with run_id: {response.response_body}"

        process_id = response.response_body.get("process_id")

        assert process_id is not None, "Process ID should be returned in the response"

        # Describe the process using the process_id
        describe_request = DescribeProcessRequest(
            process_id=process_id
        )

        describe_response = admin_client.request(request=describe_request)

        assert describe_response.status_code == 200, f"Unable to describe process: {describe_response.response_body}"

        max_wait_periods = 5

        wait_period_seconds = 15

        agent_execution_success = False

        for _ in range(max_wait_periods):
            time.sleep(wait_period_seconds)

            # Check the process status
            describe_response = admin_client.request(request=describe_request)

            assert describe_response.status_code == 200, f"Unable to describe process: {describe_response.response_body}"

            process_status = describe_response.response_body.get("status")

            assert process_status is not "FAILED", f"Process execution failed: {describe_response.response_body}"

            if process_status == "COMPLETED":
                agent_execution_success = True

                break

        assert agent_execution_success, "Agent execution did not complete successfully"

    def test_t2_agent_run(self, admin_client, home_directory):
        """Test executing an agent that calls other t1 agents"""
        # Create a sample agent definition
        t1_agent_def_path = f"{home_directory}/test.agent"

        t1_agent_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the agent",
                    "name": "input_value",
                    "required": True
                }
            ],
            "description": "This is the Burt Macklin agent. It provides a simple response",
            "responses": [
                {
                    "type_name": "string",
                    "description": "The response Burt provides",
                    "name": "response",
                    "required": True
                }
            ],
            "system_event_endpoint": "ratio::agent::andy::execution"
        }

        # Write definition to file using the system's file operations
        create_file_req = PutFileRequest(
            file_path=t1_agent_def_path,
            file_type="ratio::agent",
            permissions="755"
        )
        create_resp = admin_client.request(create_file_req)

        assert create_resp.status_code in [200, 201], "Unable to create agent definition file"
        
        # Write content to the file
        content_req = PutFileVersionRequest(
            data=json.dumps(t1_agent_definition),
            file_path=t1_agent_def_path,
            metadata={"version": "1.0"},
        )

        content_resp = admin_client.request(content_req)

        assert content_resp.status_code in [200, 201], "Unable to write content to the agent definition file"

        # Create a t2 agent definition that calls the t1 agent
        t2_agent_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the composite agent",
                    "name": "input_value",
                    "required": True
                }
            ],
            "description": "This is a composite agent that executes multiple agents",
            "instructions": [
                {
                    "agent_definition_path": t1_agent_def_path,
                    "arguments": {
                        "input_value": "REF:arguments.input_value"
                    },
                    "execution_id": "inner_agent_execution"
                },
                {
                    "agent_definition_path": t1_agent_def_path,
                    "arguments": {
                        "input_value": "REF:inner_agent_execution.response"
                    },
                    "execution_id": "other_agent_execution"
                }
            ],
            "response_reference_map": {
                "composite_response": "REF:other_agent_execution.response",
                "inner_response": "REF:inner_agent_execution.response"
            },
            "responses": [
                {
                    "type_name": "string",
                    "description": "Response from the composite agent",
                    "name": "composite_response",
                    "required": True
                },
                {
                    "type_name": "string",
                    "description": "Response from the inner agent",
                    "name": "inner_response",
                    "required": True
                }
            ],
        }

        # Execute the t2 agent
        execute_request = ExecuteAgentRequest(
            agent_definition=t2_agent_definition,
            arguments={"input_value": "test_input_1"}
        )

        response = admin_client.request(request=execute_request)

        print(f"Response: {response.response_body}")

        assert response.status_code == 200, f"Unable to execute t2 agent: {response.error_message}"

        process_id = response.response_body.get("process_id")

        assert process_id is not None, "Process ID should be returned in the response"

        # Describe the process using the process_id
        describe_request = DescribeProcessRequest(
            process_id=process_id
        )

        describe_response = admin_client.request(request=describe_request)

        assert describe_response.status_code == 200, f"Unable to describe process: {describe_response.response_body}"

        max_wait_periods = 5

        wait_period_seconds = 15

        agent_execution_success = False

        for _ in range(max_wait_periods):
            time.sleep(wait_period_seconds)

            # Check the process status
            describe_response = admin_client.request(request=describe_request)

            assert describe_response.status_code == 200, f"Unable to describe process: {describe_response.response_body}"

            process_status = describe_response.response_body.get("status")

            assert process_status is not "FAILED", f"Process execution failed: {describe_response.response_body}"

            if process_status == "COMPLETED":
                agent_execution_success = True

                break

        assert agent_execution_success, "Agent execution did not complete successfully"

    def test_t3_agent_run(self, admin_client, home_directory):
        """Test executing an agent that calls other t2 agents"""
        # Create a t1 agent definition
        t1_agent_def_path = f"{home_directory}/test.agent"

        t1_agent_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the agent",
                    "name": "input_value",
                    "required": True
                }
            ],
            "description": "This is the Burt Macklin agent. It provides a simple response",
            "responses": [
                {
                    "type_name": "string",
                    "description": "The response Burt provides",
                    "name": "response",
                    "required": True
                }
            ],
            "system_event_endpoint": "ratio::agent::andy::execution"
        }

        # Write definition to file using the system's file operations
        create_file_req = PutFileRequest(
            file_path=t1_agent_def_path,
            file_type="ratio::agent",
            permissions="755"
        )

        create_resp = admin_client.request(create_file_req)

        assert create_resp.status_code in [200, 201], "Unable to create agent definition file"

        # Write content to the file
        content_req = PutFileVersionRequest(
            data=json.dumps(t1_agent_definition),
            file_path=t1_agent_def_path,
            metadata={"version": "1.0"},
        )

        content_resp = admin_client.request(content_req)

        assert content_resp.status_code in [200, 201], "Unable to write content to the agent definition file"

        # Create a t2 agent definition that calls the t1 agent
        t2_agent_def_path = f"{home_directory}/test_t2.agent"

        t2_agent_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the composite agent",
                    "name": "outer_input",
                    "required": True
                }
            ],
            "description": "This is a composite agent that executes multiple agents",
            "instructions": [
                {
                    "agent_definition_path": t1_agent_def_path,
                    "arguments": {
                        "input_value": "REF:arguments.outer_input"
                    },
                    "execution_id": "inner_agent_execution"
                },
                {
                    "agent_definition_path": t1_agent_def_path,
                    "arguments": {
                        "input_value": "REF:inner_agent_execution.response"
                    },
                    "execution_id": "other_agent_execution"
                }
            ],
            "response_reference_map": {
                "composite_response": "REF:other_agent_execution.response",
                "inner_response": "REF:inner_agent_execution.response"
            },
            "responses": [
                {
                    "type_name": "string",
                    "description": "Response from the composite agent",
                    "name": "composite_response",
                    "required": True
                },
                {
                    "type_name": "string",
                    "description": "Response from the inner agent",
                    "name": "inner_response",
                    "required": True
                }
            ],
        }

        # Write definition to file using the system's file operations
        create_file_req = PutFileRequest(
            file_path=t2_agent_def_path,
            file_type="ratio::agent",
            permissions="755"
        )

        create_resp = admin_client.request(create_file_req)

        assert create_resp.status_code in [200, 201], "Unable to create agent definition file"

        # Write content to the file
        content_req = PutFileVersionRequest(
            data=json.dumps(t2_agent_definition),
            file_path=t2_agent_def_path,
            metadata={"version": "1.0"},
        )

        content_resp = admin_client.request(content_req)

        assert content_resp.status_code in [200, 201], "Unable to write content to the agent definition file"

        # Validate content was written correctly
        read_req = GetFileVersionRequest(
            file_path=t2_agent_def_path,
        )

        read_resp = admin_client.request(read_req)

        assert read_resp.status_code == 200, "Unable to read agent definition file"

        assert read_resp.response_body["data"] == json.dumps(t2_agent_definition), "Agent definition file content mismatch"

        # Create a t3 agent definition that calls the t2 agent
        t3_agent_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the composite agent",
                    "name": "way_outer_input",
                    "required": True
                }
            ],
            "description": "This is a composite agent that executes multiple agents",
            "instructions": [
                {
                    "agent_definition_path": t2_agent_def_path,
                    "arguments": {
                        "outer_input": "REF:arguments.way_outer_input"
                    },
                    "execution_id": "inner_agent_execution"
                },
                {
                    "agent_definition_path": t2_agent_def_path,
                    "arguments": {
                        "outer_input": "REF:inner_agent_execution.inner_response"
                    },
                    "execution_id": "other_agent_execution"
                }
            ],
            "response_reference_map": {
                "composite_response": "REF:other_agent_execution.composite_response",
                "inner_response": "REF:inner_agent_execution.inner_response"
            },
            "responses": [
                {
                    "type_name": "string",
                    "description": "Response from the composite agent",
                    "name": "composite_response",
                    "required": True
                },
                {
                    "type_name": "string",
                    "description": "Response from the inner agent",
                    "name": "inner_response",
                    "required": True
                }
            ],
        }

        # Execute the t3 agent
        execute_request = ExecuteAgentRequest(
            agent_definition=t3_agent_definition,
            arguments={"way_outer_input": "test_input_1"}
        )

        response = admin_client.request(request=execute_request)

        assert response.status_code == 200, f"Unable to execute t3 agent: {response.error_message}"

        process_id = response.response_body.get("process_id")

        assert process_id is not None, "Process ID should be returned in the response"

        # Describe the process using the process_id
        describe_request = DescribeProcessRequest(
            process_id=process_id
        )

        describe_response = admin_client.request(request=describe_request)

        assert describe_response.status_code == 200, f"Unable to describe process: {describe_response.response_body}"

        max_wait_periods = 10

        wait_period_seconds = 15

        agent_execution_success = False

        for _ in range(max_wait_periods):
            time.sleep(wait_period_seconds)

            # Check the process status
            describe_response = admin_client.request(request=describe_request)

            assert describe_response.status_code == 200, f"Unable to describe process: {describe_response.response_body}"

            process_status = describe_response.response_body.get("status")

            assert process_status is not "FAILED", f"Process execution failed: {describe_response.response_body}"

            if process_status == "COMPLETED":
                agent_execution_success = True

                break

        assert agent_execution_success, "Agent execution did not complete successfully"

    def test_asymetric_t3_agent_run(self, admin_client, home_directory):
        """Test executing an agent that calls other t2 agents with asymmetric execution paths"""
        # Create a base T1 agent definition (the lowest level agent)
        t1_agent_def_path = f"{home_directory}/t1_base_agent.agent"

        t1_agent_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the T1 agent",
                    "name": "t1_input",
                    "required": True
                }
            ],
            "description": "This is the T1 base agent. It provides a simple response",
            "responses": [
                {
                    "type_name": "string",
                    "description": "The response T1 provides",
                    "name": "response",
                    "required": True
                }
            ],
            "system_event_endpoint": "ratio::agent::andy::execution"
        }

        # Write definition to file using the system's file operations
        create_file_req = PutFileRequest(
            file_path=t1_agent_def_path,
            file_type="ratio::agent",
            permissions="755"
        )

        create_resp = admin_client.request(create_file_req)

        assert create_resp.status_code in [200, 201], f"Unable to create T1 agent definition file: {create_resp.error_message}"

        # Write content to the file
        content_req = PutFileVersionRequest(
            data=json.dumps(t1_agent_definition),
            file_path=t1_agent_def_path,
            metadata={"version": "1.0"},
        )

        content_resp = admin_client.request(content_req)

        assert content_resp.status_code in [200, 201], f"Unable to write content to T1 agent file: {content_resp.error_message}"

        # Create an alternate T1 agent for asymmetric testing
        t1_alt_agent_def_path = f"{home_directory}/t1_alt_agent.agent"

        t1_alt_agent_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the alternate T1 agent",
                    "name": "t1_alt_input",
                    "required": True
                }
            ],
            "description": "This is an alternate T1 agent with different input/output names",
            "responses": [
                {
                    "type_name": "string",
                    "description": "The response from alternate T1 agent",
                    "name": "response",
                    "required": True
                }
            ],
            "system_event_endpoint": "ratio::agent::andy::execution"
        }

        # Create and populate alternate T1 agent file
        alt_create_file_req = PutFileRequest(
            file_path=t1_alt_agent_def_path,
            file_type="ratio::agent",
            permissions="755"
        )

        alt_create_resp = admin_client.request(alt_create_file_req)

        assert alt_create_resp.status_code in [200, 201], f"Unable to create alternate T1 agent file: {alt_create_resp.error_message}"

        alt_content_req = PutFileVersionRequest(
            data=json.dumps(t1_alt_agent_definition),
            file_path=t1_alt_agent_def_path,
            metadata={"version": "1.0"},
        )

        alt_content_resp = admin_client.request(alt_content_req)

        assert alt_content_resp.status_code in [200, 201], f"Unable to write content to alternate T1 agent file: {alt_content_resp.error_message}"

        # Create a T2 agent definition that calls the T1 agent in a symmetric pattern
        t2_symmetric_def_path = f"{home_directory}/t2_symmetric.agent"

        t2_symmetric_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the symmetric T2 agent",
                    "name": "t2_sym_input",
                    "required": True
                }
            ],
            "description": "This is a T2 agent that executes T1 agents in a symmetric pattern",
            "instructions": [
                {
                    "agent_definition_path": t1_agent_def_path,
                    "arguments": {
                        "t1_input": "REF:arguments.t2_sym_input"
                    },
                    "execution_id": "t2_sym_first_execution"
                },
                {
                    "agent_definition_path": t1_agent_def_path,
                    "arguments": {
                        "t1_input": "REF:t2_sym_first_execution.response"
                    },
                    "execution_id": "t2_sym_second_execution"
                }
            ],
            "response_reference_map": {
                "t2_sym_output": "REF:t2_sym_second_execution.response",
                "t2_sym_intermediate": "REF:t2_sym_first_execution.response"
            },
            "responses": [
                {
                    "type_name": "string",
                    "description": "Final response from symmetric T2 agent",
                    "name": "t2_sym_output",
                    "required": True
                },
                {
                    "type_name": "string",
                    "description": "Intermediate response from symmetric T2 agent",
                    "name": "t2_sym_intermediate",
                    "required": True
                }
            ],
        }

        # Create and populate T2 symmetric agent file
        t2_sym_create_req = PutFileRequest(
            file_path=t2_symmetric_def_path,
            file_type="ratio::agent",
            permissions="755"
        )

        t2_sym_create_resp = admin_client.request(t2_sym_create_req)

        assert t2_sym_create_resp.status_code in [200, 201], f"Unable to create T2 symmetric agent file: {t2_sym_create_resp.error_message}"

        t2_sym_content_req = PutFileVersionRequest(
            data=json.dumps(t2_symmetric_definition),
            file_path=t2_symmetric_def_path,
            metadata={"version": "1.0"},
        )

        t2_sym_content_resp = admin_client.request(t2_sym_content_req)

        assert t2_sym_content_resp.status_code in [200, 201], f"Unable to write content to T2 symmetric agent file: {t2_sym_content_resp.error_message}"

        # Create a T2 agent definition that calls different T1 agents (asymmetric pattern)
        t2_asymmetric_def_path = f"{home_directory}/t2_asymmetric.agent"

        t2_asymmetric_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the asymmetric T2 agent",
                    "name": "t2_asym_input",
                    "required": True
                }
            ],
            "description": "This is a T2 agent that executes different T1 agents in an asymmetric pattern",
            "instructions": [
                {
                    "agent_definition_path": t1_agent_def_path,
                    "arguments": {
                        "t1_input": "REF:arguments.t2_asym_input"
                    },
                    "execution_id": "t2_asym_first_execution"
                },
                {
                    "agent_definition_path": t1_alt_agent_def_path,
                    "arguments": {
                        "t1_alt_input": "REF:t2_asym_first_execution.response"
                    },
                    "execution_id": "t2_asym_second_execution"
                }
            ],
            "response_reference_map": {
                "t2_asym_output": "REF:t2_asym_second_execution.response",
                "t2_asym_intermediate": "REF:t2_asym_first_execution.response"
            },
            "responses": [
                {
                    "type_name": "string",
                    "description": "Final response from asymmetric T2 agent",
                    "name": "t2_asym_output",
                    "required": True
                },
                {
                    "type_name": "string",
                    "description": "Intermediate response from asymmetric T2 agent",
                    "name": "t2_asym_intermediate",
                    "required": True
                }
            ],
        }

        # Create and populate T2 asymmetric agent file
        t2_asym_create_req = PutFileRequest(
            file_path=t2_asymmetric_def_path,
            file_type="ratio::agent",
            permissions="755"
        )

        t2_asym_create_resp = admin_client.request(t2_asym_create_req)

        assert t2_asym_create_resp.status_code in [200, 201], f"Unable to create T2 asymmetric agent file: {t2_asym_create_resp.error_message}"

        t2_asym_content_req = PutFileVersionRequest(
            data=json.dumps(t2_asymmetric_definition),
            file_path=t2_asymmetric_def_path,
            metadata={"version": "1.0"},
        )

        t2_asym_content_resp = admin_client.request(t2_asym_content_req)

        assert t2_asym_content_resp.status_code in [200, 201], f"Unable to write content to T2 asymmetric agent file: {t2_asym_content_resp.error_message}"

        # Validate that a file was written correctly (just for one as an example)
        read_req = GetFileVersionRequest(
            file_path=t2_asymmetric_def_path,
        )

        read_resp = admin_client.request(read_req)

        assert read_resp.status_code == 200, f"Unable to read T2 asymmetric agent file: {read_resp.error_message}"

        assert read_resp.response_body["data"] == json.dumps(t2_asymmetric_definition), "T2 asymmetric agent file content mismatch"

        # Create a T3 agent definition that calls both T2 agents
        t3_agent_definition = {
            "arguments": [
                {
                    "type_name": "string",
                    "description": "Input value for the T3 agent",
                    "name": "t3_input",
                    "required": True
                }
            ],
            "description": "This is a T3 agent that executes both symmetric and asymmetric T2 agents",
            "instructions": [
                {
                    "agent_definition_path": t2_symmetric_def_path,
                    "arguments": {
                        "t2_sym_input": "REF:arguments.t3_input"
                    },
                    "execution_id": "t3_sym_execution"
                },
                {
                    "agent_definition_path": t2_asymmetric_def_path,
                    "arguments": {
                        "t2_asym_input": "REF:t3_sym_execution.t2_sym_intermediate"
                    },
                    "execution_id": "t3_asym_execution"
                }
            ]
        }

        # Execute the T3 agent
        execute_request = ExecuteAgentRequest(
            agent_definition=t3_agent_definition,
            arguments={"t3_input": "test_input_value"}
        )

        response = admin_client.request(request=execute_request)

        assert response.status_code == 200, f"Unable to execute T3 agent: {response.error_message}"

        process_id = response.response_body.get("process_id")

        assert process_id is not None, "Process ID should be returned in the response"

        # Describe the process using the process_id
        describe_request = DescribeProcessRequest(
            process_id=process_id
        )

        describe_response = admin_client.request(request=describe_request)

        assert describe_response.status_code == 200, f"Unable to describe process: {describe_response.error_message}"

        # Wait for agent execution to complete with better feedback
        max_wait_periods = 10

        wait_period_seconds = 15

        agent_execution_success = False

        for attempt in range(max_wait_periods):
            time.sleep(wait_period_seconds)

            # Check the process status with improved error handling
            describe_response = admin_client.request(request=describe_request)

            assert describe_response.status_code == 200, f"Failed to get process status on attempt {attempt+1}: {describe_response.error_message}"

            process_status = describe_response.response_body.get("status")

            # Fail immediately if process errors out
            if process_status == "FAILED":
                assert False, f"Process execution failed: {describe_response.response_body.get('error_message', 'Unknown error')}"

            # Break loop if process completes
            if process_status == "COMPLETED":
                agent_execution_success = True

                break

        assert agent_execution_success, f"Agent execution did not complete within {max_wait_periods * wait_period_seconds} seconds"