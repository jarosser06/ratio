"""
Execution API Interface
"""
import logging
import os

from typing import Dict

from da_vinci.core.immutable_object import (
    ObjectBody,
    ObjectBodySchema,
    InvalidObjectSchemaError,
)

from da_vinci.event_bus.client import EventPublisher
from da_vinci.event_bus.event import Event as EventBusEvent
from da_vinci.core.global_settings import setting_value

from ratio.core.core_lib.client import RatioInternalClient
from ratio.core.core_lib.factories.api import ChildAPI, Route
from ratio.core.core_lib.jwt import JWTClaims

from ratio.core.services.process_manager.request_definitions import (
    ExecuteToolRequest,
    ValidateToolDefinitionRequest,
)

from ratio.core.services.storage_manager.request_definitions import ValidateFileAccessRequest

from ratio.core.services.process_manager.tables.processes.client import (
    Process,
    ProcessTableClient,
)

from ratio.core.services.process_manager.runtime.tool import (
    ToolDefinition,
    ToolInstruction, 
    MissingDefinitionError,
    InvalidDefinitionError,
)
from ratio.core.services.process_manager.runtime.engine import ExecutionEngine, InvalidSchemaError
from ratio.core.services.process_manager.runtime.events import (
    ExecuteToolInternalRequest,
    SystemExecuteToolRequest,
)
from ratio.core.services.process_manager.runtime.mapper import MappingError
from ratio.core.services.process_manager.runtime.no_op import execute_no_ops
from ratio.core.services.process_manager.runtime.reference import InvalidReferenceError

from ratio.core.services.process_manager.runtime.token import (
    create_execution_token,
)

from ratio.core.services.process_manager.runtime.validator import RefValidator


class ExecuteAPI(ChildAPI):
    routes = [
        Route(
            path="/execute",
            method_name="execute_tool",
            request_body_schema=ExecuteToolRequest,
        ),
        Route(
            path="/validate_definition",
            method_name="validate_tool_definition",
            request_body_schema=ValidateToolDefinitionRequest,
        ),
    ]

    def _validate_tool_definition(self, request_context: Dict, tool_definition_path: str = None,
                                   tool_definition: Dict = None):
        """
        Validate an tool definition

        Keyword arguments:
        tool_definition_path -- The path to the tool definition file
        tool_definition -- The tool definition
        request_context -- The request context
        """
        ref_validator = RefValidator()

        if tool_definition_path:
            # Validate the requestor has access to the tool definition path
            storage_client = RatioInternalClient(
                service_name="storage_manager",
                token=request_context["signed_token"],
            )

            validate_file_access_request = ObjectBody(
                body={
                    "file_path": tool_definition_path,
                    "requested_permission_names": ["read"],
                },
                schema=ValidateFileAccessRequest,
            )

            validate_file_access_response = storage_client.request(
                path="/validate_file_access",
                request=validate_file_access_request,
            )

            if validate_file_access_response.status_code == 404:
                logging.debug(f"Tool definition path does not exist: {tool_definition_path}")

                return ["tool definition file not found"]

            entity_has_access = validate_file_access_response.response_body.get("entity_has_access", False)

            if not entity_has_access:
                logging.debug(f"Requestor does not have access to tool definition path: {tool_definition_path}")

                return [f"unauthorized to access tool definition path {tool_definition_path}"]

            try:
                tool_definition = ToolDefinition.load_from_fs(
                    tool_file_location=tool_definition_path,
                    token=request_context["signed_token"],
                )

            except Exception as e:
                logging.debug(f"Error loading tool definition from file: {e}")

                return [str(e)]

        else:
            # Validate the tool inline definition
            tool_definition = ToolDefinition(**tool_definition)

        validation_errors = ref_validator.validate_instructions(
            instructions=tool_definition.instructions,
        )

        if validation_errors:
            logging.debug(f"Validation errors: {validation_errors}")

            return self.respond(
                status_code=400,
                body={"message": "Invalid tool definition", "errors": validation_errors},
            )

        return ref_validator.validate_instruction(tool_instruction=tool_definition)

    def execute_tool(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Execute an tool

        Keyword arguments:
        request_body -- The request body
        request_context -- The request context
        """
        logging.debug(f"Executing tool with request body: {request_body.to_dict()}")

        token = create_execution_token(
            original_token=request_context["signed_token"],
        )

        # If tool definition path was passed, need to validate the requestor has access
        storage_client = RatioInternalClient(
            service_name="storage_manager",
            token=token,
        ) 

        claims = JWTClaims.from_claims(claims=request_context["request_claims"])

        global_default_working_dir = setting_value(
            namespace="ratio::process_manager",
            setting_key="default_global_working_dir",
        )

        default_working_dir = claims.home

        if global_default_working_dir and global_default_working_dir != "NOT_SET":
            logging.debug(f"Using global default working directory as default: {global_default_working_dir}")

            default_working_dir = global_default_working_dir

        # Validate write access to the working directory
        working_directory = request_body.get("working_directory", default_return=default_working_dir)

        if not working_directory:
            logging.debug(f"No working directory provided, no global working dir set, and no home directory found in {claims.entity} claims: {claims.to_dict()}")

            return self.respond(
                body={"message": "must provide valid working directory"},
                status_code=400,
            )

        logging.debug(f"Working directory set to {working_directory}")

        validate_file_access_request = ObjectBody(
            body={
                "file_path": working_directory,
                "requested_permission_names": ["read", "write"],
            },
            schema=ValidateFileAccessRequest,
        )

        validate_file_access_response = storage_client.request(
            path="/validate_file_access",
            request=validate_file_access_request,
        )

        if validate_file_access_response.status_code == 404:
            logging.debug(f"Working directory does not exist: {working_directory}")

            return self.respond(
                body={"message": "working directory not found"},
                status_code=400,
            )

        entity_has_access = validate_file_access_response.response_body.get("entity_has_access", False)

        if not entity_has_access:
            logging.debug(f"Requestor does not have access to working directory: {working_directory}")

            return self.respond(
                body={"message": "unauthorized to access working directory"},
                status_code=403,
            )

        if request_body.get("tool_definition_path"):
            # Validate the requestor has access to the tool definition path
            validate_file_access_request = ObjectBody(
                body={
                    "file_path": request_body["tool_definition_path"],
                    "requested_permission_names": ["execute"],
                },
                schema=ValidateFileAccessRequest,
            )

            validate_file_access_response = storage_client.request(
                path="/validate_file_access",
                request=validate_file_access_request,
            )

            if validate_file_access_response.status_code == 404:
                logging.debug(f"Tool definition path does not exist: {request_body["tool_definition_path"]}")

                return self.respond(
                    status_code=400,
                    body={"message": "tool definition file not found"}
                )

            entity_has_access = validate_file_access_response.response_body.get("entity_has_access", False)

            if not entity_has_access:
                logging.debug(f"Requestor does not have access to tool definition path: {request_body["tool_definition_path"]}")

                return self.respond(
                    body={
                        "message": "unauthorized to access tool definition path",
                        "status_code": 403,
                    }
                )

            try:
                tool_definition = ToolDefinition.load_from_fs(
                    tool_file_location=request_body["tool_definition_path"],
                    token=token,
                )

            except Exception as e:
                logging.debug(f"Error loading tool definition from file: {e}")

                return self.respond(
                    status_code=400,
                    body={"message": str(e)},
                )

        else:
            # Validate the tool inline definition
            try:
                tool_definition = ToolDefinition(**request_body["tool_definition"])

            except Exception as e:
                logging.debug(f"Error loading tool definition from inline definition: {e}")

                return self.respond(
                    status_code=400,
                    body={"message": str(e)},
                )

        claims = JWTClaims.from_claims(claims=request_context["request_claims"])

        # Create a new process, this will be the parent for composite tools and the process for the tool
        proc = Process(
            process_owner=claims.entity,
            working_directory=working_directory,
        )

        process_client = ProcessTableClient()

        process_client.put(proc)

        arguments = request_body.get("arguments")

        schema_dict = {"attributes": tool_definition.arguments}

        argument_schema = ObjectBodySchema.from_dict("ToolArguments", schema_dict)

        try:
            processed_args = ObjectBody(
                body=arguments,
                schema=argument_schema
            )

        except InvalidObjectSchemaError as invalid_schema:
            logging.debug(f"Error processing arguments: {invalid_schema}")

            # Delete the process as it never started
            process_client.delete(proc)

            return self.respond(
                status_code=400,
                body={"message": str(invalid_schema)},
            )

        try:
            execution_engine = ExecutionEngine(
                arguments=processed_args.to_dict(),
                argument_schema=tool_definition.arguments,
                process_id=proc.process_id,
                token=token,
                working_directory=working_directory,
                instructions=tool_definition.instructions,
                response_definition=tool_definition.responses,
                response_reference_map=tool_definition.response_reference_map,
                system_event_endpoint=tool_definition.system_event_endpoint,
            )

        except (InvalidSchemaError, InvalidObjectSchemaError, MissingDefinitionError, InvalidDefinitionError) as invalid_err:
            logging.debug(f"Error creating execution engine: {invalid_err}")

            # Delete the process as it never started
            process_client.delete(proc)

            return self.respond(
                status_code=400,
                body={"message": str(invalid_err)},
            )

        # Create the base directory for the process
        execution_engine.initialize_path()

        if arguments:
            try:
                # Create a mock instruction for the parent process to save arguments
                parent_instruction = ToolInstruction(
                    definition=tool_definition,
                    execution_id=proc.process_id,
                    provided_arguments=processed_args.to_dict(),
                )

                # Save arguments to parent process directory
                parent_argument_path = execution_engine.prepare_for_execution(
                    tool_instruction=parent_instruction,
                    process_id=proc.process_id,
                    working_directory=working_directory,
                )

                # Set the arguments path on the parent process
                if parent_argument_path:
                    proc.arguments_path = parent_argument_path

                    process_client.put(proc)

                    logging.debug(f"Saved parent process arguments to: {parent_argument_path}")

            except (InvalidSchemaError, InvalidObjectSchemaError) as save_err:
                logging.debug(f"Error saving parent arguments: {save_err}")

                # Delete the process as it failed to initialize properly
                process_client.delete(proc)

                return self.respond(
                    status_code=400,
                    body={"message": f"Failed to save parent arguments: {str(save_err)}"},
                )

        # Create the event bus client
        event_bus_client = EventPublisher()

        if execution_engine.is_composite:
            # Schedule the instruction executions
            execution_ids, skipped = execution_engine.get_available_executions()

            if skipped:
                logging.debug(f"Skipped execution IDs: {skipped}")

                execute_no_ops(
                    claims=claims,
                    execution_engine=execution_engine,
                    parent_process=proc,
                    process_client=process_client,
                    skipped_ids=skipped,
                    token=token,
                )

            if not execution_ids:
                logging.debug(f"No available executions for tool: {tool_definition}")

                return self.respond(
                    status_code=400,
                    body={"message": "no available executions for tool, likely due to invalid tool definition"}
                )

            for execution_id in execution_ids:
                logging.debug(f"Creating child process for execution ID: {execution_id}")

                child_proc = proc.create_child(
                    execution_id=execution_id,
                    working_directory=working_directory,
                    process_owner=claims.entity,
                )

                process_client.put(child_proc)

                logging.debug(f"Child process created: {child_proc}")

                try:
                    # Just executing the tool
                    argument_path = execution_engine.prepare_for_execution(
                        tool_instruction=execution_engine.instructions[execution_id],
                        process_id=child_proc.process_id,
                        working_directory=working_directory,
                    )

                    child_proc.arguments_path = argument_path

                    process_client.put(child_proc)

                except (InvalidSchemaError, InvalidObjectSchemaError, InvalidReferenceError, MappingError) as invalid_err:
                    logging.debug(f"Error preparing for execution: {invalid_err}")

                    # Delete the child process as it never started
                    process_client.delete(child_proc)

                    # Delete the parent process as it never started
                    process_client.delete(proc)

                    return self.respond(
                        status_code=400,
                        body={"message": str(invalid_err)},
                    )

                if execution_engine.instructions[execution_id].definition.is_composite:
                    # Create an internal request to execute the tool

                    definition_og_file_path = execution_engine.instructions[execution_id].definition.original_file_path

                    if not definition_og_file_path:
                        # Save the tool definition to the working directory
                        temp_definition_path = os.path.join(
                            execution_engine.get_path(working_dir=working_directory, process_id=child_proc.process_id),
                            "tool_definition.tool"
                        )

                        logging.debug(f"Exporting tool definition to: {temp_definition_path}")

                        execution_engine.instructions[execution_id].definition.export_to_fs(
                            file_path=temp_definition_path,
                            token=token,
                        )

                        definition_og_file_path = temp_definition_path

                    internal_req = ObjectBody(
                        body={
                            "arguments_path": argument_path,
                            "tool_definition_path": definition_og_file_path,
                            "parent_process_id": proc.process_id,
                            "process_id": child_proc.process_id,
                            "token": token,
                            "working_directory": working_directory,
                        },
                        schema=ExecuteToolInternalRequest,
                    )

                    event = EventBusEvent(
                        event_type="ratio::execute_composite_tool",
                        body=internal_req,
                    )

                else:
                    tool_req = ObjectBody(
                        body={
                            "arguments_path": argument_path,
                            "argument_schema": execution_engine.instructions[execution_id].definition.arguments,
                            "parent_process_id": proc.process_id,
                            "process_id": child_proc.process_id,
                            "response_schema": execution_engine.instructions[execution_id].definition.responses,
                            "token": token,
                            "working_directory": working_directory,
                        },
                        schema=SystemExecuteToolRequest,
                    )

                    logging.debug(f"Creating body for {execution_id}: {tool_req}")

                    event = EventBusEvent(
                        event_type=execution_engine.instructions[execution_id].definition.system_event_endpoint,
                        body=tool_req,
                    )

                logging.debug(f"Event created for {execution_id}: {event}")

                # Publish the event
                event_bus_client.submit(event)

                logging.debug(f"Event published for {execution_id}: {event}")

        else:
            instruction = ToolInstruction(
                definition=tool_definition,
                execution_id=proc.process_id, # This isn't used for non-composite tools
                provided_arguments=request_body.get("arguments"),
            )

            try:
                # Just executing the tool
                argument_path = execution_engine.prepare_for_execution(tool_instruction=instruction)

                proc.arguments_path = argument_path

                process_client.put(proc)

            except InvalidSchemaError as invalid_err:
                logging.debug(f"Error preparing for execution: {invalid_err}")

                return self.respond(
                    status_code=400,
                    body={"message": str(invalid_err)},
                )

            # Create the event
            tool_req = ObjectBody(
                body={
                    "arguments_path": argument_path,
                    "argument_schema": tool_definition.arguments,
                    "parent_process_id": proc.parent_process_id,
                    "process_id": proc.process_id,
                    "response_schema": tool_definition.responses,
                    "token": token,
                    "working_directory": execution_engine.get_path(),
                },
                schema=SystemExecuteToolRequest,
            )

            event = EventBusEvent(
                event_type=tool_definition.system_event_endpoint,
                body=tool_req,
            )

            # Publish the event
            event_bus_client.submit(event=event)

        # Initialize the engine with 
        return self.respond(
            status_code=200,
            body={
                "process_id": proc.process_id,
            }
        )

    def validate_tool_definition(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Validate an tool definition
        Keyword arguments:
        request_body -- The request body
        request_context -- The request context
        """
        logging.debug(f"Validating tool definition with request body: {request_body}")

        instruction_validation_results = self._validate_tool_definition(
            request_context=request_context,
            tool_definition_path=request_body.get("tool_definition_path"),
            tool_definition=request_body.get("tool_definition"),
        )

        if instruction_validation_results:
            return self.respond(
                status_code=200,
                body={
                    "validation_errors": instruction_validation_results,
                    "status": "failed",
                },
            )

        return self.respond(
            status_code=200,
            body={
                "validation_errors": [],
                "status": "passed",
            },
        )