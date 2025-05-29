"""
Defines the Agent runtime Library.

This should always have 0 dependencies to the core system libraries, it would be
absurd for every agent to have a complete dependency of the entire core system.
"""
import base64
import json
import logging

from enum import StrEnum
from os import path as os_path
from typing import Any, Optional, Dict, List, Union

from da_vinci.core.client_base import RESTClientBase, RESTClientResponse

from da_vinci.core.immutable_object import ObjectBody, ObjectBodySchema

from da_vinci.event_bus.event import Event as EventBusEvent
from da_vinci.event_bus.client import EventPublisher

from ratio.agents.agent_lib.jwt import JWTClient, JWTClaims
from ratio.agents.agent_lib.events import SystemExecuteAgentRequest, SystemExecuteAgentResponse


AUTH_HEADER = "x-ratio-authorization"

AGENT_IO_FILE_EXTENSION = ".aio"

AGENT_IO_FILE_TYPE = "ratio::agent_io"


class FileLoadError(Exception):
    """
    Custom exception for file load errors.
    """
    def __init__(self, message: str, file_path: str):
        super().__init__(f"File '{file_path}' Load Failed: {message}")


class SystemInitFailure(Exception):
    """
    Exception for system initialization failures.
    """
    def __init__(self, message: str):
        super().__init__(f"System Initialization Failed: {message}")


class ResponseStatus(StrEnum):
    """
    Enum for the response status
    """
    SUCCESS = "success"
    FAILURE = "failure"


API_TARGETS = {
    "PROCESS": "agent_manager",
    "SCHEDULER": "scheduler",
    "STORAGE": "storage_manager",
}


class RatioSystem:
    def __init__(self, parent_process_id: str, process_id: str, token: str, working_directory: str,
                 arguments_path: Optional[str] = None, argument_schema: Optional[List[Dict]] = None,
                 response_schema: Optional[List[Dict]] = None):
        """
        Initialize the Ratio client.

        Keyword arguments:
        parent_process_id -- The ID of the parent process
        process_id -- The ID of the process
        token -- The token to use for authentication
        working_directory -- The working directory for the agent
        arguments_path -- The path to the arguments file
        argument_schema -- The list of expected argument attributes
        response_schema -- The list of expected response attributes
        """
        logging.debug(f"Initializing Ratio Agent Runtime Library")

        self._acquired_token = token

        self.parent_process_id = parent_process_id

        self.process_id = process_id

        self.working_directory = working_directory

        self._source_files = []

        try:
            self._storage_client = RESTClientBase(resource_name="storage_manager")

            self.claims = self.verify_and_get_claims(token)

            self.argument_schema = None

            if argument_schema:
                # Load the schema
                self.argument_schema = ObjectBodySchema.from_dict(
                    object_name=f"agent_schema",
                    schema_dict={
                        "attributes": argument_schema,
                        "vanity_types": {
                            "file": "string",
                        }
                    }
                )

            self.arguments = None

            if arguments_path:
                if not argument_schema:
                    raise ValueError("Argument schema must be provided if arguments path is set")

                self.arguments = self._load_arguments(arguments_path=arguments_path)

            # The schema for the response
            self.response_schema = None

            if response_schema:
                logging.debug(f"Loading response schema: {response_schema}")

                # Load the schema
                self.response_schema = ObjectBodySchema.from_dict(
                    object_name="agent_response_schema",
                    schema_dict={
                        "attributes": response_schema,
                        "vanity_types": {
                            "file": "string",
                        }
                    }
                )

        except Exception as err:
            failure_message = f"Failed to initialize agent runtime: {str(err)}"

            self._init_failure(
                failure_message=failure_message,
                parent_process_id=parent_process_id,
                process_id=process_id,
                token=token,
            )

            raise SystemInitFailure(message=failure_message) from err 

        logging.info("Ratio Agent Runtime Library initialized")

    @classmethod
    def _init_failure(cls, failure_message: str, parent_process_id: str, process_id: str, token: str):
        """
        Initialize the failure response.

        Keyword arguments:
        failure_message -- The failure message to send
        parent_process_id -- The ID of the parent process
        process_id -- The ID of the process
        token -- The token to use for authentication
        """
        logging.debug(f"Failing with message: {failure_message}")

        event_body = {
            "failure": failure_message,
            "parent_process_id": parent_process_id,
            "process_id": process_id,
            "status": ResponseStatus.FAILURE,
            "token": token,
        }

        response_body = ObjectBody(
            body=event_body,
            schema=SystemExecuteAgentResponse,
        )

        logging.debug(f"Sending failure event: {response_body.to_dict()}")

        event_publisher = EventPublisher()

        response_event = EventBusEvent(
            body=response_body,
            event_type="ratio::agent_response"
        )

        event_publisher.submit(
            event=response_event,
        )

    @staticmethod
    def verify_and_get_claims(token: str, public_key: Optional[str] = None) -> JWTClaims:
        """
        Utility function to verify a token and get claims
        
        Keyword arguments:
        token -- The JWT token to verify
        public_key -- Optional public key for verification (if not using KMS)
        
        Returns:
            JWTClaims object if verification succeeds
        """
        if public_key:
            return JWTClient.verify_with_public_key(token, public_key)

        return JWTClient.verify_token(token)

    @classmethod
    def from_da_vinci_event(cls, event: Dict) -> "RatioSystem":
        """
        Create a RatioSystem instance from a Da Vinci event.

        Keyword arguments:
        event -- The event to create the instance from
        """
        logging.debug(f'Received request: {event}')

        source_event = EventBusEvent.from_lambda_event(event)

        object_body = ObjectBody(
            body=source_event.body,
            schema=SystemExecuteAgentRequest,
        )

        return cls(**object_body.to_dict())

    def __enter__(self):
        """
        Enter the runtime context related to this object.
        
        Returns:
            The RatioSystem instance itself.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the runtime context related to this object.
        
        Automatically handles exceptions by calling the failure method
        with the exception message.

        Keyword arguments:
        exc_type -- The type of the exception
        exc_val -- The value of the exception
        exc_tb -- The traceback object

        Returns:
            True to suppress the exception, False to propagate it
        """
        if exc_type is not None:
            # An exception occurred, report it as a failure
            self.failure(f"Failure occurred during agent execution: {str(exc_val)}")

        return False

    def _load_arguments(self, arguments_path: str) -> Union[ObjectBody, None]:
        """
        Load the arguments from a file.

        Keyword arguments:
        arguments_path -- The path to the arguments file
        """
        resp = self._storage_request(
            path="/get_file_version",
            request={
                "file_path": arguments_path,
            },
        )

        if resp.status_code != 200:
            raise FileLoadError(
                message=f"Failed to load arguments file: {resp.status_code} - {resp.body}",
                file_path=arguments_path
            )

        data = resp.response_body.get("data")

        if not data:
            raise FileLoadError(
                message="No data found in the response body",
                file_path=arguments_path,
            )

        try:
            raw_arguments = json.loads(data)

        except json.JSONDecodeError as e:
            raise FileLoadError(
                message=f"Failed to decode JSON: {str(e)}",
                file_path=arguments_path,
            )

        try:
            loaded_arguments = ObjectBody(
                body=raw_arguments,
                schema=self.argument_schema,
            )

        except Exception as e:
            raise FileLoadError(
                message=f"Failed to load arguments with schema: {str(e)}",
                file_path=arguments_path,
            )

        self.add_source_file(
            source_file_path=arguments_path,
            source_file_version=resp.response_body["details"]["version_id"],
        )

        return loaded_arguments

    def _storage_request(self, path: str, request: Union[Dict, ObjectBody], auth_header: str = AUTH_HEADER) -> RESTClientResponse:
        """
        Make a storage request to the Ratio Storage API.

        Keyword arguments:
        path -- The path to the API endpoint
        request -- The request body to send to the API
        """
        headers = {auth_header: self._acquired_token}

        logging.debug(f"Making storage request to {path} with headers {headers}")

        if isinstance(request, ObjectBody):
            # If the request is an ObjectBody, convert it to a dictionary
            request = request.to_dict()

        response = self._storage_client.post(body=request, headers=headers, path=path)

        return response

    def add_source_file(self, source_file_path: str, source_file_version: Optional[str] = None):
        """
        Add a source file to the lineage tracking.

        Keyword arguments:
        source_file_path -- The path to the source file
        source_file_version -- The version of the source file. If not set, the system will look up the latest file version
        """
        if not source_file_version:
            desc_resp = self._storage_request(
                path="/describe_file",
                request={
                    "file_path": source_file_path,
                },
            )

            if desc_resp.status_code != 200:
                raise FileLoadError(
                    message=f"Failed to retrieve latest source file version for lineage: {desc_resp.status_code} - {desc_resp}",
                    file_path=source_file_path,
                )

            source_file_version = desc_resp.response_body.get("latest_version_id")

        self._source_files.append({
            "source_file_path": source_file_path,
            "source_file_version": source_file_version,
        })

    def describe_file(self, file_path: str) -> Dict[str, Any]:
        """
        Describe a file in the system.

        Keyword arguments:
        file_path -- The path to the file
        """
        logging.debug(f"Describing file {file_path}")

        resp = self._storage_request(
            path="/describe_file",
            request={
                "file_path": file_path,
            },
        )

        if resp.status_code != 200:
            raise FileLoadError(
                message=f"Failed to describe file: {resp.status_code} - {resp}",
                file_path=file_path,
            )

        return resp.response_body

    def describe_file_version(self, file_path: str, version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Describe a file version in the system.

        Keyword arguments:
        file_path -- The path to the file
        version_id -- The version ID of the file
        """
        logging.debug(f"Describing file version {file_path} - {version_id}")

        resp = self._storage_request(
            path="/describe_file_version",
            request={
                "file_path": file_path,
                "version_id": version_id,
            },
        )

        if resp.status_code != 200:
            raise FileLoadError(
                message=f"Failed to describe file version: {resp.status_code} - {resp}",
                file_path=file_path,
            )

        return resp.response_body

    def get_file_details(self, file_path: str) -> Dict[str, Any]:
        """
        Return the details about a file, includes some information about the file type

        Keyword arguments:
        file_path -- The path to the file
        """
        logging.debug(f"Getting file details {file_path}")

        file_resp = self.describe_file(file_path=file_path)

        file_type_name = file_resp["file_type"]

        # Get file type details
        resp = self._storage_request(
            path="/describe_file_type",
            request={
                "file_type": file_type_name,
            },
        )

        if resp.status_code != 200:
            raise ValueError(message=f"Failed to describe file type: {resp.status_code} - {resp.response_body}")

        logging.debug(f"File type details: {resp.response_body}")

        full_response = {
            "content_type": resp.response_body["content_type"],
            **file_resp,
        }

        return full_response

    def get_file_version(self, file_path: str, version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a file version from the system.

        Keyword arguments:
        file_path -- The path to the file
        version_id -- The version ID of the file
        """
        logging.debug(f"Getting file version {file_path} - {version_id}")

        resp = self._storage_request(
            path="/get_file_version",
            request={
                "file_path": file_path,
                "version_id": version_id,
            },
        )

        if resp.status_code != 200:
            raise FileLoadError(
                message=f"Failed to get file version: {resp.status_code} - {resp}",
                file_path=file_path,
            )

        return resp.response_body

    def get_binary_file_version(self, file_path: str, decode: Optional[bool] = True,
                                version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a binary file (like an image) and decode the data to base64.
        Handles both cases: files already stored as base64 strings, and raw binary data.

        Keyword arguments:
        file_path -- The path to the file
        decode -- Whether to decode the data to base64 (default: True)
        version_id -- The version ID of the file (optional)

        Returns:
        Dict containing:
            - 'data': raw data ready for use
            - 'content_type': the MIME type of the file
            - 'encoding': 'base64' or 'binary'
        """
        logging.debug(f"Getting binary file as base64: {file_path}")

        # Get file content
        file_response = self.get_file_version(file_path, version_id)

        file_data = file_response.get("data")

        if not file_data:
            raise FileLoadError(
                message="No data found in file",
                file_path=file_path
            )

        # Get file details for content type
        file_details = self.get_file_details(file_path)

        content_type = file_details.get("content_type", "application/octet-stream")

        base_64_encoded = file_response["details"].get("base_64_encoded", False)

        if base_64_encoded and decode:
            # File is already base64 encoded
            logging.debug("File data is base64 encoded .. decoding")

            file_data = base64.b64decode(file_data)

        encoding = "base64" if base_64_encoded else "binary"

        return {
            "data": file_data,
            "content_type": content_type,
            "encoding": encoding,
            "file_path": file_path,
            "version_id": file_response["details"]["version_id"],
        }

    def internal_api_request(self, api_target: str, path: str, request: Union[Dict, ObjectBody], auth_header: str = AUTH_HEADER,
                             raise_on_failure: bool = True) -> RESTClientResponse:
        """
        Make a request to the internal API. Constructs the appropriate client and sends the request.
        This is a generic method for making requests to the internal API with .

        Keyword arguments:
        api_target -- The target API to send the request to
        path -- The path to the API endpoint
        request -- The request body to send to the API
        auth_header -- The authentication header to use
        raise_on_failure -- Whether to raise an exception on failure
        """
        logging.debug(f"Making internal API request to {api_target} - {path}")

        if api_target not in API_TARGETS:
            raise ValueError(f"Invalid API target: {api_target}. Valid targets are: {', '.join(API_TARGETS.keys())}")

        headers = {auth_header: self._acquired_token}

        if isinstance(request, ObjectBody):
            # If the request is an ObjectBody, convert it to a dictionary
            request = request.to_dict()

        api_target_value = API_TARGETS[api_target]

        rest_client = RESTClientBase(resource_name=api_target_value, raise_on_failure=raise_on_failure)

        response = rest_client.post(body=request, headers=headers, path=path)

        return response

    def put_file(self, file_path: str, file_type: str, data: Optional[Union[str, bytes]] = None, encode_data: bool = False,
                 metadata: Optional[Dict] = None, permissions: Optional[str] = "644"):
        """
        Puts a file into the system.

        Keyword arguments:
        file_path -- The path to the file
        data -- The data to put into the file
        metadata -- The metadata to associate with the file
        permissions -- The permissions to set on the file
        """
        logging.debug(f"Putting file {file_path} of type {file_type}")

        self._storage_request(
            path="/put_file",
            request={
                "file_path": file_path,
                "file_type": file_type,
                "metadata": metadata,
                "permissions": permissions,
            }
        )

        logging.debug(f"File {file_path} of type {file_type} put successfully")

        if data:
            logging.debug(f"Putting data into file {file_path}")

            if encode_data:
                # Encode the data to base64 if needed
                if isinstance(data, str):
                    data = data.encode('utf-8')

                data = base64.b64encode(data).decode("utf-8")

            self._storage_request(
                path="/put_file_version",
                request={
                    "file_path": file_path,
                    "data": data,
                    "metadata": metadata,
                    "origin": "internal",
                    "source_files": self._source_files,
                }
            )

    def failure(self, failure_message: str):
        """
        Fail the Ratio API.

        Keyword arguments:
        failure_message -- The failure message to send
        """
        logging.debug(f"Failing with message: {failure_message}")

        event_body = {
            "parent_process_id": self.parent_process_id,
            "process_id": self.process_id,
            "response": None,
            "status": ResponseStatus.FAILURE,
            "failure": failure_message,
            "token": self._acquired_token,
        }

        response_body = ObjectBody(
            body=event_body,
            schema=SystemExecuteAgentResponse,
        )

        logging.debug(f"Sending failure event: {response_body.to_dict()}")

        event_publisher = EventPublisher()

        response_event = EventBusEvent(
            body=response_body,
            event_type="ratio::agent_response"
        )

        event_publisher.submit(
            event=response_event,
        )

    def success(self, response_body: Optional[Union[Dict, ObjectBody]] = None):
        """
        Respond to the Ratio API.

        Keyword arguments:
        status -- The status of the response (success or failure)
        failure_message -- The failure message to send if the status is failure
        response_body -- The response body to send to the API
        """
        logging.debug(f"Responding success with {response_body}")

        response_body_path = None

        if response_body:
            # Put the response body into the working directory
            response_body_path = os_path.join(
                self.working_directory,
                "response" + AGENT_IO_FILE_EXTENSION
            )

            logging.debug(f"Setting response body path to {response_body_path}")

            self.put_file(
                file_path=response_body_path,
                file_type="ratio::agent_io",
                data=json.dumps(response_body),
            )

        event_body = {
            "parent_process_id": self.parent_process_id,
            "process_id": self.process_id,
            "response": response_body_path,
            "status": ResponseStatus.SUCCESS,
            "token": self._acquired_token,
        }

        response_body = ObjectBody(
            body=event_body,
            schema=SystemExecuteAgentResponse,
        )

        logging.debug(f"Sending response event: {response_body.to_dict()}")

        event_publisher = EventPublisher()

        response_event = EventBusEvent(
            body=response_body,
            event_type="ratio::agent_response"
        )

        event_publisher.submit(
            event=response_event,
        )