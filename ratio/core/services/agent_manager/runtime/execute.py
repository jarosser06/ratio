"""
Execution API Interface
"""
import logging
import os

from typing import Dict

from da_vinci.core.immutable_object import ObjectBody, InvalidObjectSchemaError

from da_vinci.event_bus.client import EventPublisher
from da_vinci.event_bus.event import Event as EventBusEvent

from ratio.core.core_lib.client import RatioInternalClient
from ratio.core.core_lib.factories.api import ChildAPI, Route
from ratio.core.core_lib.jwt import JWTClaims

from ratio.core.services.agent_manager.request_definitions import (
    ExecuteAgentRequest,
    ValidateAgentDefinitionRequest,
)

from ratio.core.services.storage_manager.request_definitions import ValidateFileAccessRequest

from ratio.core.services.agent_manager.tables.processes.client import (
    Process,
    ProcessTableClient,
)

from ratio.core.services.agent_manager.runtime.agent import AgentDefinition, AgentInstruction
from ratio.core.services.agent_manager.runtime.engine import ExecutionEngine, InvalidSchemaError
from ratio.core.services.agent_manager.runtime.events import (
    ExecuteAgentInternalRequest,
    SystemExecuteAgentRequest,
)
from ratio.core.services.agent_manager.runtime.no_op import execute_no_ops
from ratio.core.services.agent_manager.runtime.reference import InvalidReferenceError

from ratio.core.services.agent_manager.runtime.validator import RefValidator


class ExecuteAPI(ChildAPI):
    routes = [
        Route(
            path="/execute",
            method_name="execute_agent",
            request_body_schema=ExecuteAgentRequest,
        ),
        Route(
            path="/validate_definition",
            method_name="validate_agent_definition",
            request_body_schema=ValidateAgentDefinitionRequest,
        ),
    ]

    def _validate_agent_definition(self, request_context: Dict, agent_definition_path: str = None,
                                   agent_definition: Dict = None):
        """
        Validate an agent definition

        Keyword arguments:
        agent_definition_path -- The path to the agent definition file
        agent_definition -- The agent definition
        request_context -- The request context
        """
        ref_validator = RefValidator()

        if agent_definition_path:
            # Validate the requestor has access to the agent definition path
            storage_client = RatioInternalClient(
                service_name="storage_manager",
                token=request_context["signed_token"],
            )

            validate_file_access_request = ObjectBody(
                body={
                    "file_path": agent_definition_path,
                    "requested_permission_names": ["read"],
                },
                schema=ValidateFileAccessRequest,
            )

            validate_file_access_response = storage_client.request(
                path="/validate_file_access",
                request=validate_file_access_request,
            )

            if validate_file_access_response.status_code == 404:
                logging.debug(f"Agent definition path does not exist: {agent_definition_path}")

                return ["agent definition file not found"]

            entity_has_access = validate_file_access_response.response_body.get("entity_has_access", False)

            if not entity_has_access:
                logging.debug(f"Requestor does not have access to agent definition path: {agent_definition_path}")

                return [f"unauthorized to access agent definition path {agent_definition_path}"]

            try:
                agent_definition = AgentDefinition.load_from_fs(
                    agent_file_location=agent_definition_path,
                    token=request_context["signed_token"],
                )

            except Exception as e:
                logging.debug(f"Error loading agent definition from file: {e}")

                return [str(e)]

        else:
            # Validate the agent inline definition
            agent_definition = AgentDefinition(**agent_definition)

        validation_errors = ref_validator.validate_instructions(
            instructions=agent_definition.instructions,
        )

        if validation_errors:
            logging.debug(f"Validation errors: {validation_errors}")

            return self.respond(
                status_code=400,
                body={"message": "Invalid agent definition", "errors": validation_errors},
            )

        return ref_validator.validate_instruction(agent_instruction=agent_definition)

    def execute_agent(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Execute an agent

        Keyword arguments:
        request_body -- The request body
        request_context -- The request context
        """
        logging.debug(f"Executing agent with request body: {request_body.to_dict()}")

        # If agent definition path was passed, need to validate the requestor has access
        storage_client = RatioInternalClient(
            service_name="storage_manager",
            token=request_context["signed_token"],
        ) 

        claims = JWTClaims.from_claims(claims=request_context["request_claims"])

        # Validate write access to the working directory
        working_directory = request_body.get("working_directory", default_return=claims.home)

        if not working_directory:
            logging.debug(f"No working directory provided and no home directory found in {claims.entity} claims: {claims.to_dict()}")

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

        if request_body.get("agent_definition_path"):
            # Validate the requestor has access to the agent definition path
            validate_file_access_request = ObjectBody(
                body={
                    "file_path": request_body["agent_definition_path"],
                    "requested_permission_names": ["execute"],
                },
                schema=ValidateFileAccessRequest,
            )

            validate_file_access_response = storage_client.request(
                path="/validate_file_access",
                request=validate_file_access_request,
            )

            if validate_file_access_response.status_code == 404:
                logging.debug(f"Agent definition path does not exist: {request_body["agent_definition_path"]}")

                return self.respond(
                    status_code=400,
                    body={"message": "agent definition file not found"}
                )

            entity_has_access = validate_file_access_response.response_body.get("entity_has_access", False)

            if not entity_has_access:
                logging.debug(f"Requestor does not have access to agent definition path: {request_body["agent_definition_path"]}")

                return self.respond(
                    body={
                        "message": "unauthorized to access agent definition path",
                        "status_code": 403,
                    }
                )

            try:
                agent_definition = AgentDefinition.load_from_fs(
                    agent_file_location=request_body["agent_definition_path"],
                    token=request_context["signed_token"],
                )

            except Exception as e:
                logging.debug(f"Error loading agent definition from file: {e}")

                return self.respond(
                    status_code=400,
                    body={"message": str(e)},
                )

        else:
            # Validate the agent inline definition
            try:
                agent_definition = AgentDefinition(**request_body["agent_definition"])

            except Exception as e:
                logging.debug(f"Error loading agent definition from inline definition: {e}")

                return self.respond(
                    status_code=400,
                    body={"message": str(e)},
                )

        claims = JWTClaims.from_claims(claims=request_context["request_claims"])

        # Create a new process, this will be the parent for composite agents and the process for the agent
        proc = Process(
            process_owner=claims.entity,
            working_directory=working_directory,
        )

        process_client = ProcessTableClient()

        process_client.put(proc)

        try:
            execution_engine = ExecutionEngine(
                arguments=request_body.get("arguments"),
                process_id=proc.process_id,
                token=request_context["signed_token"],
                working_directory=working_directory,
                instructions=agent_definition.instructions,
                response_definition=agent_definition.responses,
                response_reference_map=agent_definition.response_reference_map,
                system_event_endpoint=agent_definition.system_event_endpoint,
            )

        except (InvalidSchemaError, InvalidObjectSchemaError) as invalid_err:
            logging.debug(f"Error creating execution engine: {invalid_err}")

            # Delete the process as it never started
            process_client.delete(proc)

        # Create the base directory for the process
        execution_engine.initialize_path()

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
                    token=request_context["signed_token"],
                )

            if not execution_ids:
                logging.debug(f"No available executions for agent: {agent_definition}")

                return self.respond(
                    body={
                        "message": "no available executions for agent, likely due to invalid agent definition",
                        "status_code": 400,
                    }
                )

            # Set base working directory for the child processes
            base_working_dir = execution_engine.get_path()

            logging.debug(f"Base working directory for child processes: {base_working_dir}")

            for execution_id in execution_ids:
                logging.debug(f"Creating child process for execution ID: {execution_id}")

                child_proc = proc.create_child(
                    execution_id=execution_id,
                    working_directory=base_working_dir,
                    process_owner=claims.entity,
                )

                process_client.put(child_proc)

                logging.debug(f"Child process created: {child_proc}")

                try:
                    # Just executing the agent
                    argument_path = execution_engine.prepare_for_execution(
                        agent_instruction=execution_engine.instructions[execution_id],
                        process_id=child_proc.process_id,
                        working_directory=base_working_dir,
                    )

                except (InvalidSchemaError, InvalidObjectSchemaError, InvalidReferenceError) as invalid_err:
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
                    # Create an internal request to execute the agent

                    definition_og_file_path = execution_engine.instructions[execution_id].definition.original_file_path

                    if not definition_og_file_path:
                        # Save the agent definition to the working directory
                        temp_definition_path = os.path.join(
                            execution_engine.get_path(working_dir=base_working_dir, process_id=child_proc.process_id),
                            "agent_definition.agent"
                        )

                        logging.debug(f"Exporting agent definition to: {temp_definition_path}")

                        execution_engine.instructions[execution_id].definition.export_to_fs(
                            file_path=temp_definition_path,
                            token=request_context["signed_token"],
                        )

                        definition_og_file_path = temp_definition_path

                    internal_req = ObjectBody(
                        body={
                            "arguments_path": argument_path,
                            "agent_definition_path": definition_og_file_path,
                            "parent_process_id": proc.process_id,
                            "process_id": child_proc.process_id,
                            "token": request_context["signed_token"],
                            "working_directory": execution_engine.get_path(working_dir=base_working_dir, process_id=child_proc.process_id),
                        },
                        schema=ExecuteAgentInternalRequest,
                    )

                    event = EventBusEvent(
                        event_type="ratio::execute_composite_agent",
                        body=internal_req,
                    )

                else:
                    agent_req = ObjectBody(
                        body={
                            "arguments_path": argument_path,
                            "argument_schema": execution_engine.instructions[execution_id].definition.arguments,
                            "parent_process_id": proc.process_id,
                            "process_id": child_proc.process_id,
                            "response_schema": execution_engine.instructions[execution_id].definition.responses,
                            "token": request_context["signed_token"],
                            "working_directory": execution_engine.get_path(working_dir=base_working_dir, process_id=child_proc.process_id),
                        },
                        schema=SystemExecuteAgentRequest,
                    )

                    logging.debug(f"Creating body for {execution_id}: {agent_req}")

                    event = EventBusEvent(
                        event_type=execution_engine.instructions[execution_id].definition.system_event_endpoint,
                        body=agent_req,
                    )

                logging.debug(f"Event created for {execution_id}: {event}")

                # Publish the event
                event_bus_client.submit(event)

                logging.debug(f"Event published for {execution_id}: {event}")

        else:
            instruction = AgentInstruction(
                definition=agent_definition,
                execution_id=proc.process_id, # This isn't used for non-composite agents
                provided_arguments=request_body.get("arguments"),
            )

            try:
                # Just executing the agent
                argument_path = execution_engine.prepare_for_execution(agent_instruction=instruction)

            except InvalidSchemaError as invalid_err:
                logging.debug(f"Error preparing for execution: {invalid_err}")

                return self.respond(
                    status_code=400,
                    body={"message": str(invalid_err)},
                )

            # Create the event
            agent_req = ObjectBody(
                body={
                    "arguments_path": argument_path,
                    "argument_schema": agent_definition.arguments,
                    "parent_process_id": proc.parent_process_id,
                    "process_id": proc.process_id,
                    "response_schema": agent_definition.responses,
                    "token": request_context["signed_token"],
                    "working_directory": execution_engine.get_path(),
                },
                schema=SystemExecuteAgentRequest,
            )

            event = EventBusEvent(
                event_type=agent_definition.system_event_endpoint,
                body=agent_req,
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

    def validate_agent_definition(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Validate an agent definition
        Keyword arguments:
        request_body -- The request body
        request_context -- The request context
        """
        logging.debug(f"Validating agent definition with request body: {request_body}")

        instruction_validation_results = self._validate_agent_definition(
            request_context=request_context,
            agent_definition_path=request_body.get("agent_definition_path"),
            agent_definition=request_body.get("agent_definition"),
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