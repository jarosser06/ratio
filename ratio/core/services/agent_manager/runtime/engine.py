"""
Execution Engine for Agents

Provides functionality for managing composite agents and determining the execution order of agents.
"""
import json
import logging
import os

from typing import Any, Dict, List, Optional, Tuple, Union

from da_vinci.core.immutable_object import (
    ObjectBody,
    ObjectBodySchema,
)

from da_vinci.core.json import (
    DaVinciObjectEncoder
)

from ratio.core.core_lib.client import RatioInternalClient

from ratio.core.services.storage_manager.request_definitions import (
    DescribeFileRequest,
    GetFileVersionRequest,
    PutFileRequest,
    PutFileVersionRequest,
)

from ratio.core.services.agent_manager.runtime.agent import (
    AgentDefinition,
    AgentInstruction,
    AIO_EXT,
    AGENT_IO_FILE_TYPE,
)
from ratio.core.services.agent_manager.runtime.conditions import ConditionEvaluator
from ratio.core.services.agent_manager.runtime.mapper import (
    DEFAULT_MAPPING_FUNCTIONS,
    ObjectMapper,
)
from ratio.core.services.agent_manager.runtime.reference import (
    InvalidReferenceError,
    Reference,
)


class InvalidSchemaError(Exception):
    """
    Exception raised when the schema is invalid.
    """
    def __init__(self, message: str):
        """
        Initialize the exception.

        Keyword arguments:
        message -- The error message
        """
        super().__init__(message)


class FileCreationFailure(Exception):
    """
    Exception raised when a file creation fails.
    """
    def __init__(self, file_path: str, message: str):
        """
        Initialize the exception.

        Keyword arguments:
        file_path -- The path to the file that failed to be created
        message -- The error message
        """
        self.file_path = file_path

        super().__init__(f"Failed to create file {file_path}: {message}")


def strip_class_from_error(error_message: str) -> str:
    """
    Strips irrelevant information from the error message to make it more readable
    downstream with a 400 error.

    Keyword arguments:
    error_message -- The error message to strip
    """
    # Look for the pattern of ClassName.method_name() followed by the actual message
    if '.__init__()' in error_message:
        # Split at the closing parenthesis and take the second part
        message = error_message.split(')', 1)[1].strip()

        # Remove the word "positional" if it exists, just makes the message a little cleaner
        message = message.replace(" positional", "")

        return message

    return error_message


class ExecutionEngine:
    def __init__(self, arguments: Dict[str, Any], process_id: str, token: str, working_directory: str,
                 argument_schema: Optional[Dict[str, Any]], instructions: List[Dict[str, Any]] = None,
                 response_definition: Optional[List[Dict]] = None,
                 response_reference_map: Optional[Dict[str, str]] = None, system_event_endpoint: Optional[str] = None):
        """
        Initialize the Engine object.

        Keyword arguments:
        arguments -- The arguments to pass to the 
        argument_schema -- The schema for the arguments
        process_id -- The ID of the process
        token -- The token to use for authentication
        working_directory -- The working directory for the execution
        instructions -- The instructions
        response_definition -- The response definition for the execution
        response_reference_map -- The response reference map 
        """
        self.arguments = arguments

        self.argument_schema = argument_schema

        self.token = token

        self.is_composite = False

        self.response_definition = response_definition

        self.response_reference_map = response_reference_map

        if isinstance(response_reference_map, ObjectBody):
            self.response_reference_map = response_reference_map.to_dict()

        if not system_event_endpoint:
            self.is_composite = True

            if not instructions:
                raise ValueError("Instructions must be provided if system_event_endpoint is not set")
            
            if response_definition and not response_reference_map:
                raise ValueError("Response reference map must be provided if response definition is set for composite agents")

            self._validate_response_refence_map()

            self.instructions = self._load_instructions(instructions=instructions, token=token)

            self.dependency_graph = self._build_dependency_graph()

            logging.debug(f"Generated dependency graph: {self.dependency_graph}")

            self.completed = []

            self.in_progress = []

        self.system_event_endpoint = system_event_endpoint

        # Storing these for export
        self._raw_instructions = instructions

        self.working_directory = working_directory

        self.process_id = process_id

        logging.debug(f"Initializing references with arguments: {self.arguments}")

        if self.arguments:
            if self.argument_schema:
                # Extract argument types from schema
                argument_types = {arg['name']: arg['type_name'] for arg in self.argument_schema}

                self.reference = Reference()

                try:
                    self.reference.set_arguments(self.arguments, argument_types)

                except Exception as arg_set_err:
                    raise InvalidSchemaError(message=strip_class_from_error(str(arg_set_err)))

            else:
                self.reference = Reference(arguments=self.arguments)

    @classmethod
    def load_from_fs(cls, process_id: str, token: str, working_directory: str) -> "ExecutionEngine":
        """
        Load the task from the file system.

        Keyword arguments:
        file_path -- The path to the task file
        process_id -- The ID of the process
        token -- The token to use for authentication
        """
        logging.debug(f"Loading task from {working_directory}")

        # Load the task from the ratio file system
        ratio_client = RatioInternalClient(
            token=token,
            service_name="storage_manager",
        )

        proc_dir = f"agent_exec-{process_id}"

        execution_file_path = os.path.join(working_directory, proc_dir, "execution.json")

        file_version_request = ObjectBody(
            schema=GetFileVersionRequest,
            body={"file_path": execution_file_path},
        )

        resp = ratio_client.request(
            path="/get_file_version",
            request=file_version_request
        )

        if resp.status_code not in [200, 201]:
            logging.debug(f"Failed to load file {execution_file_path}: {resp.status_code}")

            raise Exception(f"Unable to load file {execution_file_path}: {resp.status_code} - {resp.response_body}")

        version_data = resp.response_body["data"]

        # Parse the file content
        data = json.loads(version_data)

        return cls(
            arguments=data["arguments"],
            argument_schema=data.get("argument_schema"),
            instructions=data["instructions"],
            process_id=process_id,
            response_definition=data.get("response_definition"),
            response_reference_map=data.get("response_reference_map"),
            system_event_endpoint=data.get("system_event_endpoint"),
            token=token,
            working_directory=working_directory,
        )

    def _build_dependency_graph(self):
        """
        Build the dependency graph for the task. This is a no-op for now.
        """
        graph = {}

        for execution_id, instruction in self.instructions.items():
            graph[execution_id] = instruction.get_dependencies()

        return graph

    def _expand_parallel_instruction(self, execution_id: str) -> List[str]:
        """
        Expand a parallel instruction into child instructions.
        Returns list of child execution IDs.

        Keyword arguments:
        execution_id -- The ID of the execution to expand
        """
        instruction = self.instructions[execution_id]

        parallel_config = instruction.parallel_execution

        iterate_over_value = parallel_config["iterate_over"]

        # Check if it's a REF that needs resolving, or a direct value
        if isinstance(iterate_over_value, str) and iterate_over_value.startswith("REF:"):
            resolved_value = self.reference.resolve(reference_string=iterate_over_value, token=self.token)

        else:
            # It's a direct value (could be a list, or anything else)
            resolved_value = iterate_over_value

        # Validate it's a list regardless of source
        if not isinstance(resolved_value, list):
            raise InvalidSchemaError(f"parallel_execution iterate_over must be a list, got {type(resolved_value).__name__}")

        child_argument_name = parallel_config["child_argument_name"]

        expanded_children = []

        for i, item in enumerate(resolved_value):
            child_execution_id = f"{execution_id}[{i}]"

            child_arguments = (instruction.provided_arguments or {}).copy()

            child_arguments[child_argument_name] = item

            child_instruction = AgentInstruction(
                conditions=instruction.conditions,
                dependencies=instruction.dependencies,
                execution_id=child_execution_id,
                definition=instruction.definition,
                provided_arguments=child_arguments,
                transform_responses=instruction.transform_responses,
                transform_arguments=instruction.transform_arguments,
            )

            self.instructions[child_execution_id] = child_instruction

            self.dependency_graph[child_execution_id] = child_instruction.get_dependencies()

            expanded_children.append(child_execution_id)

        # Remove the original parallel instruction
        del self.instructions[execution_id]

        del self.dependency_graph[execution_id]

        return expanded_children 

    def _load_instructions(self, instructions: List[Dict[str, Any]], token: str) -> Dict[str, AgentInstruction]:
        """
        Load the instructions from the provided list of dictionaries.

        Keyword arguments:
        instructions -- The list of instructions to load
        token -- The token to use for authentication
        """
        PROTECTED_EXECUTION_IDS = {"arguments", "self", "execution"}

        loaded_instructions = {}

        for instruction in instructions:
            execution_id = instruction["execution_id"]

            if execution_id in PROTECTED_EXECUTION_IDS:
                raise InvalidSchemaError(f"Execution ID '{execution_id}' is a protected keyword. Cannot use: {', '.join(PROTECTED_EXECUTION_IDS)}")
            
            if execution_id in loaded_instructions:
                raise InvalidSchemaError(f"Duplicate execution ID found: {execution_id}")

            # Load agent definition
            if instruction.get("agent_definition_path"):
                agent_definition = AgentDefinition.load_from_fs(
                    agent_file_location=instruction["agent_definition_path"],
                    token=token,
                )
            else:
                agent_definition = AgentDefinition(**instruction["agent_definition"])

            # Just load the instruction as-is, don't expand parallel yet
            loaded_instructions[execution_id] = AgentInstruction(
                conditions=instruction.get("conditions", []),
                dependencies=instruction.get("dependencies", []),
                execution_id=execution_id,
                definition=agent_definition,
                provided_arguments=instruction.get("arguments"),
                parallel_execution=instruction.get("parallel_execution"),  # Keep this
                transform_responses=instruction.get("transform_responses"),
                transform_arguments=instruction.get("transform_arguments"),
            )

        return loaded_instructions

    def _validate_response_refence_map(self):
        """
        Validate the response reference map for the task. This is a no-op for now.
        """
        if not self.response_reference_map:
            logging.debug("No response reference map provided .. skipping")

            return

        reference_map = self.response_reference_map

        logging.debug(f"Validating response reference map: {reference_map}")

        # Walk the response definition and ensure all required fields are present
        for response_definition in self.response_definition:
            logging.debug(f"Validating response definition {response_definition["name"]}")

            response_key = response_definition["name"]

            response_required = response_definition.get("required")

            if response_required and response_key not in reference_map:
                raise InvalidSchemaError(f"missing required response map key: {response_key}")

    def close(self) -> Union[str, None]:
        """
        Write the final response to the file system for composite agents.

        Assumes the agent wrote it's own response to the file system if it was a Lambda based agent.
        """
        # If not a composite execution, the agent is responsible for writing the response
        if not self.is_composite:
            logging.info("Direct agent execution, agent responsible for writing response .. skipping")

            return

        if not self.response_definition:
            logging.info("No defined response for this execution .. skipping")

            return

        resolved_mapping = {}

        for response_key, reference_value in self.response_reference_map.items():
            # Get the response value from the reference

            if isinstance(reference_value, str) and reference_value.startswith("REF:"):
                try:
                    response_value = self.reference.resolve(reference_string=reference_value, token=self.token)
                except InvalidReferenceError as ref_err:
                    logging.debug(f"Failed to resolve reference {reference_value}: {ref_err}")

                    raise InvalidSchemaError(message=strip_class_from_error(str(ref_err)))

            else:
                # If the reference string does not start with REF:, it is a static value
                response_value = reference_value

            # Add the resolved mapping to the dictionary
            resolved_mapping[response_key] = response_value

        logging.debug(f"Resolved mapping: {resolved_mapping}")

        # Create the response schema class
        response_schema_klass = ObjectBodySchema.from_dict(
            object_name=f"execution_engine_response_schema",
            schema_dict={
                "attributes": self.response_definition,
                "vanity_types": {
                    "file": "string",
                }
            }
        )

        validated_response = ObjectBody(
            body=resolved_mapping,
            schema=response_schema_klass,
        )

        # Save the response to the file system
        ratio_client = RatioInternalClient(
            token=self.token,
            service_name="storage_manager",
        )

        response_body_path = os.path.join(self.get_path(), "response" + AIO_EXT)

        put_file_request = ObjectBody(
            schema=PutFileRequest,
            body={
                "file_path": response_body_path,
                "file_type": AGENT_IO_FILE_TYPE,
                "permissions": "644",
                "metadata": {
                    "description": "Agent response",
                    "execution_id": self.process_id,
                    "process_id": self.process_id,
                }
            }
        )

        resp = ratio_client.request(
            path="/put_file",
            request=put_file_request,
        )

        if resp.status_code not in [200, 201]:
            logging.debug(f"Failed to create file {response_body_path}: {resp.status_code}")

            raise FileCreationFailure(
                file_path=response_body_path,
                message=f"Unexpected response code: {resp.status_code} - {resp.response_body}",
            )

        put_file_version_request = ObjectBody(
            schema=PutFileVersionRequest,
            body={
                "data": json.dumps(validated_response.to_dict()),
                "file_path": response_body_path,
            }
        )

        resp = ratio_client.request(
            path="/put_file_version",
            request=put_file_version_request,
        )

        if resp.status_code not in [200, 201]:
            logging.debug(f"Failed to create file {response_body_path}: {resp.status_code}")

            raise FileCreationFailure(
                file_path=response_body_path,
                message=f"Unexpected response code: {resp.status_code} - {resp.response_body}",
            )

        return response_body_path

    def _meets_conditions(self, execution_id: str) -> bool:
        """
        Check if the execution meets the conditions for execution.

        Keyword arguments:
        execution_id -- The ID of the execution to evaluate conditions for
        """
        instruction = self.instructions[execution_id]

        conditions = instruction.conditions

        if not conditions:
            return True

        evaluator = ConditionEvaluator(self.reference, self.token)

        logging.debug(f"Evaluator initialized {evaluator} with conditions {conditions} and reference with {self.reference.arguments} and {self.reference.responses}")

        return evaluator.evaluate(conditions)

    def get_available_executions(self) -> Tuple[List[str], List[str]]:
        """
        Get the available executions for the task. This is a no-op for now.

        Returns:
        available -- A list of available executions
        skipped -- A list of skipped executions, meaning their dependencies are met but they had specified conditions that were not met
        """
        available = []

        skipped = []

        for exec_id in list(self.instructions.keys()):
            # Skip if already running or completed
            if exec_id in self.in_progress or exec_id in self.completed:
                continue

            # Check if all dependencies are completed
            if all(dep in self.completed for dep in self.dependency_graph[exec_id]):
                # Evaluate conditions
                if self._meets_conditions(execution_id=exec_id):
                    instruction = self.instructions[exec_id]

                    if instruction.parallel_execution:
                        expanded_children = self._expand_parallel_instruction(exec_id)

                        available.extend(expanded_children)

                    else:
                        available.append(exec_id)

                else:
                    logging.debug(f"Execution {exec_id} does not meet conditions .. skipping")

                    skipped.append(exec_id)

        return available, skipped

    def get_path(self, process_id: Optional[str] = None, working_dir: Optional[str] = None) -> str:
        """
        Get the path to the

        Keyword arguments:
        process_id -- The ID of the process, defaults to the current process ID
        working_dir -- The working directory for the execution, defaults to the current working directory
        """
        proc_id = process_id or self.process_id

        proc_dir = f"agent_exec-{proc_id}"

        work_dir = working_dir or self.working_directory

        if work_dir.endswith(proc_dir):
            return work_dir

        return os.path.join(work_dir, proc_dir)

    def mark_in_progress(self, execution_id: str):
        """
        Mark the execution as in progress.

        Keyword arguments:
        execution_id -- The ID of the execution to mark as in progress
        """
        self.in_progress.append(execution_id)

    def _apply_transforms(self, response: Dict, transform_config: Dict) -> Dict:
        """
        Apply the specified transforms to the response object.

        Keyword arguments:
        response -- The response object to transform
        transform_config -- The configuration for the transforms to apply

        Returns:
            Dictionary of new/modified response fields
        """
        mapper = ObjectMapper(DEFAULT_MAPPING_FUNCTIONS)

        variables_config = transform_config.get("variables", {})

        resolved_variables = {}

        if variables_config:
            for var_name, var_rule in variables_config.items():
                resolved_variables[var_name] = self._resolve_references_recursive(var_rule, token=self.token)

        context_object = {**response, **resolved_variables}

        transforms = transform_config["transforms"]

        if isinstance(transforms, ObjectBody):
            transforms = transforms.to_dict()

        # First dereference any REF strings in the transforms
        for key, value in transforms.items():
            if isinstance(value, str) and value.startswith("REF:"):
                try:
                    transforms[key] = self.reference.resolve(reference_string=value, token=self.token)

                except InvalidReferenceError as ref_err:
                    logging.debug(f"Failed to resolve reference {value}: {ref_err}")

                    raise InvalidSchemaError(message=strip_class_from_error(str(ref_err)))

        results = mapper.map_object(
            resolved_variables=context_object,
            mapping=transforms,
        )

        new_response = dict(response)

        new_response.update(results)

        return new_response

    def mark_completed(self, execution_id: str, response_path: Optional[str] = None):
        """
        Mark the execution as completed.
        Keyword arguments:
        execution_id -- The ID of the execution to mark as completed
        response_path -- The path to the response file, if applicable
        """
        if execution_id in self.completed:
            logging.debug(f"Execution {execution_id} already completed .. skipping")

            return

        logging.debug(f"Marking execution {execution_id} as completed")

        self.completed.append(execution_id)

        # Check if the agent provided a response
        instruction = self.instructions[execution_id]

        if not response_path:
            logging.debug(f"No response path provided for execution {execution_id} .. skipping")

            return

        logging.debug(f"Loading response from {response_path}")

        instruction.load_response(
            response_path=response_path,
            token=self.token,
        )

        if instruction.transform_responses:
            try:
                instruction.response = self._apply_transforms(
                    response=instruction.response, 
                    transform_config=instruction.transform_responses
                )

            except KeyError as key_err:
                raise InvalidSchemaError(
                    message=strip_class_from_error(f"Invalid transforms definition: {key_err}")
                )

        logging.debug(f"Loaded response for {execution_id}: {instruction.response}")

        already_added = []

        for response_definition in instruction.definition.responses:
            logging.debug(f"Processing response definition: {response_definition}")

            response_type = response_definition["type_name"]

            response_key = response_definition["name"]

            required = response_definition.get("required")

            # Need to set the default value so the response handler can have them loaded
            # in the event that something directly references those values such as the
            # conditions handler.
            default_value = response_definition.get("default_value")

            response_value = instruction.response.get(response_key, default_value)

            if required and response_value is None:
                raise InvalidSchemaError(f"Missing required response key: {response_key}")

            logging.debug(f"Response value of type {response_type} for {execution_id}.{response_key}: {response_value}")

            self.reference.add_response(
                execution_id=execution_id,
                response_key=response_key,
                response_value=response_value,
                response_type=response_type,
            )

            already_added.append(response_key)

        if instruction.response:
            current_response_keys = set(instruction.response.keys())

            transform_created_keys = current_response_keys - set(already_added)

            if transform_created_keys:
                logging.debug(f"Found {len(transform_created_keys)} transform-created response keys for {execution_id}: {transform_created_keys}")

                for new_key in transform_created_keys:
                    response_value = instruction.response[new_key]

                    logging.debug(f"Registering transform-created response {execution_id}.{new_key}: {response_value} (type will be inferred)")

                    # Register with inferred type
                    self.reference.add_inferred_response(
                        execution_id=execution_id,
                        response_key=new_key,
                        response_value=response_value,
                    )

    def initialize_path(self):
        """
        Prepare the system for the execution. This creates the appropriate base directory
        and saves the execution details to the file system.

        Keyword arguments:
        execution_id -- The ID of the execution to initialize
        """
        ratio_client = RatioInternalClient(
            token=self.token,
            service_name="storage_manager",
        )

        root_dir = self.get_path()

        put_file_request = ObjectBody(
            schema=PutFileRequest,
            body={
                "file_path": root_dir,
                "file_type": "ratio::directory",
                "permissions": "755"
            }
        )

        # Create the directory
        resp = ratio_client.request(
            path="/put_file",
            request=put_file_request,
        )

        if resp.status_code not in [200, 201]:
            logging.debug(f"Failed to create directory {root_dir}: {resp.status_code}")

            raise FileCreationFailure(
                file_path=root_dir,
                message=f"Unexpected response code: {resp.status_code} - {resp.response_body}",
            )

        # Save the execution details to the file system
        saved_execution_path = os.path.join(root_dir, "execution.json")

        put_file_request = ObjectBody(
            schema=PutFileRequest,
            body={
                "file_path": saved_execution_path,
                "file_type": "ratio::file",
                "permissions": "644",
                "metadata": {
                    "description": "Execution details",
                    "execution_id": self.process_id,
                    "process_id": self.process_id,
                }
            }
        )

        resp = ratio_client.request(
            path="/put_file",
            request=put_file_request
        )

        if resp.status_code not in [200, 201]:
            logging.debug(f"Failed to create file {saved_execution_path}: {resp.status_code}")

            raise FileCreationFailure(
                file_path=saved_execution_path,
                message=f"Unexpected response code: {resp.status_code} - {resp.response_body}",
            )

        put_file_version_request = ObjectBody(
            schema=PutFileVersionRequest,
            body={
                "data": json.dumps(self.to_dict(), cls=DaVinciObjectEncoder),
                "file_path": saved_execution_path,
            }
        )

        resp = ratio_client.request(
            path="/put_file_version",
            request=put_file_version_request,
        )

        if resp.status_code not in [200, 201]:
            logging.debug(f"Failed to create file {saved_execution_path}: {resp.status_code}")

            raise FileCreationFailure(
                file_path=saved_execution_path,
                message=f"Unexpected response code: {resp.status_code} - {resp.response_body}",
            )

    def _resolve_references_recursive(self, value, token=None):
        """
        Recursively resolve REF strings in nested data structures.

        Keyword arguments:
        value -- The value to resolve
        token -- The token to use for resolving references
        """
        if isinstance(value, str) and value.startswith("REF:"):
            return self.reference.resolve(reference_string=value, token=token)

        elif isinstance(value, dict):
            return {k: self._resolve_references_recursive(v, token) for k, v in value.items()}

        elif isinstance(value, list):
            return [self._resolve_references_recursive(item, token) for item in value]

        else:
            return value

    def prepare_for_execution(self, agent_instruction: AgentInstruction, process_id: Optional[str] = None,
                              working_directory: Optional[str] = None) -> Union[str, None]:
        """
        Prepares the system to execute an agent. This creates the appropriate sub-directory in the
        execution directory and saves the agent definition to the file system.

        Keyword arguments:
        agent_instruction -- The instruction to execute
        process_id -- The ID of the process, defaults to the current process ID. If not provided, assumes current process
        working_directory -- The working directory for the execution, defaults to the current working directory
        """
        ratio_client = RatioInternalClient(
            token=self.token,
            service_name="storage_manager",
        )

        agent_definition = agent_instruction.definition

        if not agent_definition.arguments:
            logging.debug("Agent takes no arguments .. skipping")

            return

        arguments_converted = []

        for arg in agent_definition.arguments:
            if isinstance(arg, ObjectBody):
                arguments_converted.append(arg.to_dict())

            else:
                arguments_converted.append(arg)

        if not arguments_converted:
            logging.debug("No arguments provided .. skipping")

            return

        try:
            # Create the argument schema class
            argument_schema_klass = ObjectBodySchema.from_dict(
                object_name=f"arg_schema_klass",
                schema_dict={
                    "attributes": arguments_converted,
                    "vanity_types": {
                        "file": "string",
                    }
                }
            )

        except TypeError as val_err:
            logging.debug(f"Failed to create argument schema: {val_err}")

            raise InvalidSchemaError(message=strip_class_from_error(str(val_err)))

        provided_arguments = agent_instruction.provided_arguments

        if isinstance(provided_arguments, ObjectBody):
            provided_arguments = provided_arguments.to_dict()

        rendered_arguments = {}

        for arg_name, arg_value in provided_arguments.items():
            logging.debug(f"Rendering argument {arg_name}")

            value = self._resolve_references_recursive(arg_value, token=self.token)

            rendered_arguments[arg_name] = value

            # Apply pre-transforms if present
        if agent_instruction.transform_arguments:
            try:
                rendered_arguments = self._apply_transforms(
                    response=rendered_arguments, 
                    transform_config=agent_instruction.transform_arguments
                )

            except KeyError as key_err:
                raise InvalidSchemaError(
                    message=strip_class_from_error(f"Invalid transforms definition: {key_err}")
                )

        logging.debug(f"Rendered arguments: {rendered_arguments}")

        # Ensure parent directory exists
        validated_args = ObjectBody(
            body=rendered_arguments,
            schema=argument_schema_klass,
        )

        args_file_path = os.path.join(self.get_path(process_id=process_id, working_dir=working_directory), "arguments" + AIO_EXT)

        # Ensure the parent directory exists
        parent_dir = os.path.dirname(args_file_path)

        logging.debug(f"Checking for parent directory {parent_dir}")

        describe_dir_req = ObjectBody(
            schema=DescribeFileRequest,
            body={"file_path": parent_dir}
        )

        resp = ratio_client.request(
            path="/describe_file",
            request=describe_dir_req,
        )

        if resp.status_code != 200:
            if resp.status_code == 404:
                # Create the parent directory
                put_file_request = ObjectBody(
                    schema=PutFileRequest,
                    body={
                        "file_path": parent_dir,
                        "file_type": "ratio::directory",
                        "permissions": "755"
                    }
                )

                resp = ratio_client.request(
                    path="/put_file",
                    request=put_file_request,
                )

                if resp.status_code not in [200, 201]:
                    logging.debug(f"Failed to create directory {parent_dir}: {resp.status_code}")

                    raise FileCreationFailure(
                        file_path=parent_dir,
                        message=f"Unexpected response code: {resp.status_code} - {resp.response_body}",
                    )

            else:
                logging.debug(f"Failed to describe directory {parent_dir}: {resp.status_code}")

                raise FileCreationFailure(
                    file_path=os.path.dirname(args_file_path),
                    message=f"Unexpected response code: {resp.status_code} - {resp.response_body}",
                )

        put_file_request = ObjectBody(
            schema=PutFileRequest,
            body={
                "file_path": args_file_path,
                "file_type": AGENT_IO_FILE_TYPE,
                "permissions": "644",
                "metadata": {
                    "description": "Agent arguments",
                    "execution_id": agent_instruction.execution_id,
                    "process_id": self.process_id,
                }
            }
        )

        resp = ratio_client.request(
            path="/put_file",
            request=put_file_request,
        )

        if resp.status_code not in [200, 201]:
            logging.debug(f"Failed to create file {args_file_path}: {resp.status_code} - {resp.response_body}")

            raise FileCreationFailure(
                file_path=args_file_path,
                message=f"Unexpected response code: {resp.status_code} - {resp.response_body}",
            )

        put_file_version_request = ObjectBody(
            schema=PutFileVersionRequest,
            body={
                "data": json.dumps(validated_args.to_dict()),
                "file_path": args_file_path,
            }
        )

        resp = ratio_client.request(
            path="/put_file_version",
            request=put_file_version_request,
        )

        if resp.status_code not in [200, 201]:
            logging.debug(f"Failed to create file {args_file_path}: {resp.status_code} - {resp.response_body}")

            raise FileCreationFailure(
                file_path=args_file_path,
                message=f"Unexpected response code: {resp.status_code} - {resp.response_body}",
            )

        return args_file_path

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the task to a dictionary.
        """
        return {
            "arguments": self.arguments,
            "argument_schema": self.argument_schema,
            "instructions": self._raw_instructions,
            "response_definition": self.response_definition,
            "response_reference_map": self.response_reference_map,
            "system_event_endpoint": self.system_event_endpoint,
        }