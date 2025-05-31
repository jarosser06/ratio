"""
Task Managment
"""
import json
import logging
import os

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from da_vinci.core.immutable_object import ObjectBody, ObjectBodySchema

from ratio.core.core_lib.client import RatioInternalClient

from ratio.core.services.storage_manager.request_definitions import (
    GetFileVersionRequest,
    PutFileRequest,
    PutFileVersionRequest,
)

from ratio.core.services.agent_manager.request_definitions import (
  AgentDefinitionSchema,
)


AIO_EXT = ".aio"

AGENT_IO_FILE_TYPE = "ratio::agent_io"


class AgentExportError(Exception):
    """
    Exception raised when the agent IO file cannot be saved.
    """

    def __init__(self, file_path: str, message: str):
        super().__init__(f"Error exporting agent definition to file {file_path}: {message}")


class MissingAgentIOFileError(Exception):
    """
    Exception raised when the agent IO file is missing.
    """

    def __init__(self, file_path: str):
        super().__init__(f"Missing agent IO file {file_path}")


class InvalidDefinitionError(Exception):
    """
    Exception raised when the agent definition is invalid.
    """

    def __init__(self, file_path: str, message: str):
        super().__init__(f"Invalid definition file {file_path}: {message}")


class MissingDefinitionError(Exception):
    """
    Exception raised when the agent definition is missing.
    """

    def __init__(self, file_path: str, message: str = None):
        super().__init__(f"Unable to load file {file_path}: {message if message else "File not found"}")


@dataclass
class AgentDefinition:
    arguments: List[Dict] = None
    description: str = None
    instructions: List[Dict] = None
    responses: List[Dict] = None
    response_reference_map: Dict[str, str] = None
    system_event_endpoint: str = None

    def __post_init__(self):
        """
        Post-initialization method to set default values for the agent definition.
        """
        self.original_file_path = None

        if self.instructions is None and self.system_event_endpoint is None:
            raise ValueError("Agent definition must have either instructions or system_event_endpoint")

        if self.arguments is None:
            self.arguments = []

        if self.responses is None:
            self.responses = []

    @classmethod
    def load_from_fs(cls, agent_file_location: str, token: str) -> "AgentDefinition":
        """
        Load the agent definition from the file system. This is different from the agent configuration which
        is an "installed" definition of the agent. The agent definition is the low level instructions about how the
        agent is executed at the system level.

        Keyword arguments:
        agent_definition_file_path -- The path to the agent definition file
        token -- The token to use for authentication
        """
        internal_client = RatioInternalClient(service_name="storage_manager", token=token)

        file_version_request = ObjectBody(
            body={
              "file_path": agent_file_location,
            },
            schema=GetFileVersionRequest,
        )

        # Load the agent definition from the file system
        agent_definition = internal_client.request(
            path="/get_file_version",
            request=file_version_request,
        )

        if agent_definition.status_code != 200:
            logging.debug(f"Error loading agent definition: {agent_definition.status_code} - {agent_definition.response_body}")

            raise MissingDefinitionError(file_path=agent_file_location, message=agent_definition.response_body)

        try:
            # Convert the agent definition to an ObjectBody
            resulting_data = json.loads(agent_definition.response_body["data"])

            agent_definition_object = ObjectBody(body=resulting_data, schema=AgentDefinitionSchema)

        except Exception as schema_error:
            logging.debug(f"Error loading agent definition: {schema_error}. Response Body: {agent_definition.response_body}")

            raise InvalidDefinitionError(agent_file_location, str(schema_error))

        logging.debug(f"Loaded agent definition: {agent_definition_object.to_dict()}")

        loaded_obj =  cls(**agent_definition_object.to_dict())

        loaded_obj.original_file_path = agent_file_location

        return loaded_obj

    def export_to_fs(self, file_path: str, token: str):
        """
        Export the agent definition to the file system.

        Keyword arguments:
        file_path -- The path to the file where the agent definition will be exported
        token -- The token to use for authentication
        """
        storage_client = RatioInternalClient(service_name="storage_manager", token=token)

        storage_client.raise_on_failure = True

        # Convert the agent definition to an ObjectBody
        agent_definition_object = ObjectBody(
            body=self.to_dict(),
            schema=AgentDefinitionSchema
        )

        try:
            file_request = ObjectBody(
                body={
                    "file_path": file_path,
                    "file_type": "ratio::agent",
                },
                schema=PutFileRequest,
            )

            # Export the agent definition to the file system
            storage_client.request(
                path="/put_file",
                request=file_request,
            )

            file_version_request = ObjectBody(
                body={
                    "file_path": file_path,
                    "data": json.dumps(agent_definition_object.to_dict()),
                },
                schema=PutFileVersionRequest,
            )

            storage_client.request(
                path="/put_file_version",
                request=file_version_request,
            )

            logging.debug(f"Exported agent definition to {file_path}")

        except Exception as export_error:
            logging.debug(f"Error exporting agent definition: {export_error}")

            raise AgentExportError(file_path, str(export_error)) from export_error

    def is_composite(self) -> bool:
        """
        Check if the agent definition is composite (i.e., has a system event endpoint).

        Returns:
            True if the agent definition is composite, False otherwise
        """
        return self.system_event_endpoint is None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the agent definition to a dictionary.

        Returns:
            Dictionary representation of the agent definition
        """
        return asdict(self)


@dataclass
class AgentInstruction:
    """
    Represents an agent instruction with schema information and execution details.
    """
    definition: AgentDefinition
    execution_id: str
    conditions: List[Dict] = None
    dependencies: List[str] = None
    response: Dict[str, Any] = None
    parallel_execution: Dict[str, Any] = None
    transform_arguments: Dict = None
    transform_responses: Dict = None
    provided_arguments: Dict[str, Any] = None

    def __post_init__(self):
        """
        Post-initialization method to set default values for the agent instruction.
        """
        if self.conditions is None:
            self.conditions = []

        if self.dependencies is None:
            self.dependencies = []

        if self.response is None:
            self.response = {}

        if self.provided_arguments is None:
            self.provided_arguments = {}

    def _load_aio(self, file_path: str, token: str, parameter_name: str):
        """
        Loads an agent IO file from the given path

        Keyword arguments:
        file_path -- The path to the agent IO file
        token -- The token to use for authentication
        parameter_name -- The name of the parameter to load
        """
        internal_client = RatioInternalClient(service_name="storage_manager", token=token)

        file_version_request = ObjectBody(
            body={
              "file_path": file_path,
            },
            schema=GetFileVersionRequest,
        )

        # Load the agent definition from the file system
        arguments_file = internal_client.request(
            path="/get_file_version",
            request=file_version_request,
        )

        if arguments_file.status_code != 200:
            logging.debug(f"Error loading agent arguments: {arguments_file.status_code} - {arguments_file.response_body}")

            raise MissingAgentIOFileError(file_path=file_path)

        # Convert the agent definition to an ObjectBody
        resulting_data = json.loads(arguments_file.response_body["data"])

        logging.debug(f"Loaded agent results: {resulting_data}")

        schema = ObjectBodySchema.from_dict(
            object_name=f"{parameter_name}_schema",
            schema_dict={
                "arguments": resulting_data,
                "vanity_types": {
                    "file": "string",
                }
            }
        )

        response_object = ObjectBody(body=resulting_data, schema=schema)

        self.response = response_object.to_dict()

    def get_dependencies(self) -> List[str]:
        """
        Extract execution IDs this instruction depends on based on its arguments.
        Recursively searches through nested objects and lists.

        Returns:
            List of execution IDs this instruction depends on
        """
        dependencies = self.dependencies.copy()

        def find_refs(value):
            if isinstance(value, str) and value.startswith("REF:"):
                parts = value[4:].split(".")

                base_context = parts[0]
                # Only add as dependency if it's another execution ID (not arguments or execution)
                if base_context not in ["arguments", "execution"] and base_context != "self":
                    dependencies.append(base_context)

            elif isinstance(value, dict):
                for v in value.values():
                    find_refs(v)

            elif isinstance(value, list):
                for item in value:
                    find_refs(item)

        # Process all provided arguments
        for arg_value in self.provided_arguments.values():
            find_refs(arg_value)

        if self.transform_arguments:
            transform_variables = self.transform_arguments.get("variables", {})

            for transform_variable in transform_variables.values():
                find_refs(transform_variable)

            transforms = self.transform_arguments.get("transforms", {})

            for transform_value in transforms.values():
                find_refs(transform_value)

        # Check for conditions
        if self.conditions:
            for condition in self.conditions:
                for condition_value in condition.values():
                    find_refs(condition_value)

        if self.parallel_execution:
            for parallel_value in self.parallel_execution.values():
                find_refs(parallel_value)

        return list(set(dependencies))

    def load_response(self, response_path: str, token: str, response_file_name: str = f"response{AIO_EXT}"):
        """
        Load the response for the agent instruction.

        Keyword arguments:
        response_path -- The path to the response file
        token -- The token to use for authentication
        response_file_name -- The name of the response file (default: "response.aio")
        """
        if f"response{AIO_EXT}" in response_path:
            response_file_location = response_path

        else:
            response_file_location = os.path.join(response_path, response_file_name)

        self._load_aio(response_file_location, token, "response")

        logging.debug(f"Loaded agent response: {self.response}")