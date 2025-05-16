"""
Handlers for the agent manager events.
"""
import json
import logging
import os

from datetime import datetime, UTC as utc_tz
from typing import Dict, Optional, Union

from da_vinci.core.logging import Logger
from da_vinci.core.immutable_object import ObjectBody, InvalidObjectSchemaError

from da_vinci.event_bus.client import EventPublisher, fn_event_response
from da_vinci.event_bus.event import Event as EventBusEvent

from da_vinci.exception_trap.client import ExceptionReporter

from ratio.core.core_lib.client import RatioInternalClient
from ratio.core.core_lib.jwt import JWTClaims, InternalJWTManager

from ratio.core.services.agent_manager.tables.processes.client import (
    Process,
    ProcessStatus,
    ProcessTableClient,
)

from ratio.core.services.storage_manager.request_definitions import (
    GetFileVersionRequest,
    ValidateFileAccessRequest,
)

from ratio.core.services.agent_manager.runtime.agent import (
    AgentDefinition,
    AgentInstruction,
)

from ratio.core.services.agent_manager.runtime.engine import ExecutionEngine, InvalidSchemaError

from ratio.core.services.agent_manager.runtime.events import (
    ExecuteAgentInternalRequest,
    SystemExecuteAgentResponse,
    SystemExecuteAgentRequest,
)

from ratio.core.services.agent_manager.runtime.reference import (
    InvalidReferenceError,
)

_COMPLETE_FN_NAME = "ratio.services.agents.process_complete_handler"


def _close_out_process(process: Process, token: str, failure_reason: Optional[str] = None, notify_parent: bool = False,
                       response_path: str = None, skip_failure_notification: bool = False):
    """
    Close out the process with the given status.

    Keyword arguments:
    process -- The process to close out.
    failure_reason -- The reason for the failure.
    response_path -- The path to the response of the process.
    notify_parent -- If True, notify the parent process of the successful completion.
    skip_failure_notification -- If True, skip sending the failure notification to the parent process.
    """
    proc_client = ProcessTableClient()

    # Check if the process is already closed
    if process.execution_status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED]:
        logging.debug(f"Process {process.process_id} is already closed with status {process.execution_status}")

        return

    status = ProcessStatus.COMPLETED

    if failure_reason:
        status = ProcessStatus.FAILED

    process.execution_status = status

    process.ended_on = datetime.now(tz=utc_tz)

    process.status_message = failure_reason

    if response_path:
        process.response_path = response_path

    proc_client.put(process=process)

    event_publisher = EventPublisher()

    if process.parent_process_id == "SYSTEM":
        # This is a system process, no need to notify the parent
        logging.debug(f"Process {process.process_id} is a system process, not notifying parent")

        return

    if notify_parent and not failure_reason:
        parent_proc = proc_client.get_by_id(process_id=process.parent_process_id)

        event_body = ObjectBody(
            body={
                "parent_process_id": parent_proc.parent_process_id,
                "process_id": parent_proc.process_id,
                "response": response_path,
                "status": status,
                "token": token,
            },
            schema=SystemExecuteAgentResponse,
        )

        # Send the event to the parent process
        event_publisher.submit(
            event=EventBusEvent(
                body=event_body,
                event_type="ratio::agent_response",
            )
        )

    if failure_reason and not skip_failure_notification:
        parent_proc = proc_client.get_by_id(process_id=process.parent_process_id)

        # Create the event to send to the parent process failure
        event_body = ObjectBody(
            body={
                "failure": failure_reason,
                "parent_process_id": parent_proc.parent_process_id,
                "process_id": parent_proc.process_id,
                "status": status,
                "token": token,
            },
            schema=SystemExecuteAgentResponse,
        )

        # Send the event to the parent process

        event_publisher.submit(
            event=EventBusEvent(
                body=event_body,
                event_type="ratio::agent_response",
            )
        )


def _load_arguments(arguments_path: str, token: str) -> Union[ObjectBody, None]:
    """
    Load the arguments from the given path.
    """
    storage_client = RatioInternalClient(
        service_name="storage_manager",
        token=token,
    )

    storage_client.raise_on_failure = False

    req = ObjectBody(
        body={
            "file_path": arguments_path,
        },
        schema=GetFileVersionRequest,
    )

    # Get the arguments
    response = storage_client.request(
        path="/get_file_version",
        request=req,
    )

    if response.status_code != 200:
        raise Exception(f"Failed to load arguments {arguments_path} from filesystem: {response.status_code} {response.response_body}")

    arguments = json.loads(response.response_body["data"])

    logging.debug(f"Loaded arguments: {arguments}")

    return arguments


def _execute_children(claims: JWTClaims, execution_engine: ExecutionEngine, execution_ids: list,
                      parent_process: Process, process_client: ProcessTableClient, token: str):
    """
    Execute the children of the process.
    """
    base_working_dir = execution_engine.working_directory

    logging.debug(f"Base working directory for child processes: {base_working_dir}")

    # Create the event bus client
    event_bus_client = EventPublisher()

    for execution_id in execution_ids:
        logging.debug(f"Creating child process for execution ID: {execution_id}")

        child_proc = parent_process.create_child(
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

            _close_out_process(
                process=child_proc,
                failure_reason=f"encountered an invalid schema while preparing for execution {invalid_err}",
                skip_failure_notification=True, # Skiping since the parent is handled right after
                token=token,
            )

            _close_out_process(
                process=parent_process,
                failure_reason=f"encountered an invalid schema while preparing for execution {invalid_err}",
                token=token,
            )

            return

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
                    token=token,
                )

                definition_og_file_path = temp_definition_path

            internal_req = ObjectBody(
                body={
                    "arguments_path": argument_path,
                    "agent_definition_path": definition_og_file_path,
                    "parent_process_id": parent_process.process_id,
                    "process_id": child_proc.process_id,
                    "token": token,
                    "working_directory": base_working_dir,
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
                    "parent_process_id": parent_process.process_id,
                    "process_id": child_proc.process_id,
                    "response_schema": execution_engine.instructions[execution_id].definition.responses,
                    "token": token,
                    "working_directory": base_working_dir,
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


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_COMPLETE_FN_NAME, logger=Logger(_COMPLETE_FN_NAME))
def process_complete_handler(event: Dict, context: Dict):
    """
    Execute the agent
    """
    logging.debug(f"Received request: {event}")

    source_event = EventBusEvent.from_lambda_event(event)

    event_body = ObjectBody(
        body=source_event.body,
        schema=SystemExecuteAgentResponse,
    )

    process_id = event_body["process_id"]

    process_client = ProcessTableClient()

    proc = process_client.get(
        parent_process_id=event_body["parent_process_id"],
        process_id=process_id,
    )

    if not proc:
        raise Exception(f"Process {process_id} not found")

    failure = event_body.get("failure", default_return=None)

    # Close out process already sent a failure notification to the parent if necessary. Nothing else to execute
    if failure:
        logging.debug(f"Process {process_id} failed with reason: {failure}")

        _close_out_process(
            process=proc,
            response_path=event_body["response"],
            failure_reason=failure,
            token=event_body["token"],
        )

        return

    self_is_parent = False

    if proc.parent_process_id == "SYSTEM":
        parent_proc = proc

        self_is_parent = True

    else:
        parent_proc = process_client.get_by_id(process_id=proc.parent_process_id)

        if not parent_proc:
            raise Exception(f"Parent process {proc.parent_process_id} not found")

    if parent_proc.execution_status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED]:
        logging.debug(f"Parent process {parent_proc.process_id} is already closed with status {parent_proc.execution_status}")

        return

    # Load the engine from the parent working directory
    execution_engine = ExecutionEngine.load_from_fs(
        process_id=parent_proc.process_id,
        token=event_body["token"],
        working_directory=parent_proc.working_directory,
    )

    if not execution_engine.is_composite:
        # Close out and let the parent process know
        _close_out_process(
            notify_parent=True,
            process=proc,
            response_path=event_body["response"],
            token=event_body["token"],
        )

        return

    already_executed = []

    if not self_is_parent:
        _close_out_process(
            notify_parent=False,
            process=proc,
            response_path=event_body["response"],
            token=event_body["token"],
        )

    all_children = process_client.get_by_parent(parent_process_id=parent_proc.process_id)

    if not all_children:
        raise Exception(f"No children found for composite parent process {parent_proc.process_id}")

    logging.debug(f"All children for parent process {parent_proc.process_id}: {all_children}")

    for child in all_children:
        logging.debug(f"Checking child process: {child.process_id} with {child.execution_id} is {child.execution_status}")

        if not child.execution_id:
            raise Exception(f"Child process {child.process_id} missing an execution ID")

        if child.execution_status == ProcessStatus.RUNNING:
            logging.debug(f"Execution id {child.execution_id} marked as in progress")

            execution_engine.mark_in_progress(execution_id=child.execution_id)

            already_executed.append(child.execution_id)

        elif child.execution_status == ProcessStatus.COMPLETED:
            logging.debug(f"Execution id {child.execution_id} is marked as complete")

            execution_engine.mark_completed(execution_id=child.execution_id, response_path=child.response_path)

            already_executed.append(child.execution_id)

        elif child.execution_status == ProcessStatus.FAILED:
            logging.debug(f"Child process {child.process_id} failed with reason: {child.status_message}")

            # close out parent process
            _close_out_process(
                process=parent_proc,
                failure_reason=child.status_message,
                token=event_body["token"],
            )

            return

    execution_ids = execution_engine.get_available_executions()

    already_executed_intersection = set(execution_ids).intersection(set(already_executed))

    if already_executed_intersection:
        raise Exception(f"Execution IDs {already_executed_intersection} already executed")

    logging.debug(f"Execution IDs: {execution_ids}")

    total_executions_so_far = len(execution_ids) + len(already_executed)

    if total_executions_so_far > len(execution_engine.instructions):
        logging.debug(f"More executions than instructions for composite agent process: {parent_proc.process_id} ... assume being handled by another process manager")

        return

    if not execution_ids and len(execution_engine.in_progress) == 0:
        logging.debug(f"No more executions for composite agent process: {parent_proc.process_id}")

        response_path = execution_engine.close()

        _close_out_process(
            process=parent_proc,
            notify_parent=not self_is_parent,
            response_path=response_path,
            token=event_body["token"],
        )

        return

    claims = InternalJWTManager.verify_token(token=event_body["token"])

    _execute_children(
        claims=claims,
        execution_engine=execution_engine,
        execution_ids=execution_ids,
        parent_process=parent_proc,
        process_client=process_client,
        token=event_body["token"],
    )


_COMPOSITE_FN_NAME = "ratio.services.agents.composite_agent_handler"


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_COMPOSITE_FN_NAME, logger=Logger(_COMPOSITE_FN_NAME))
def execute_composite_agent_handler(event: Dict, context: Dict):
    """
    Execute the agent
    """
    logging.debug(f"Received request: {event}")

    source_event = EventBusEvent.from_lambda_event(event)

    event_body = ObjectBody(
        body=source_event.body,
        schema=ExecuteAgentInternalRequest,
    )

    logging.debug(f"Executing agent with request body: {event_body.to_dict()}")
    
    token = event_body["token"]

    # If agent definition path was passed, need to validate the requestor has access
    storage_client = RatioInternalClient(
        service_name="storage_manager",
        token=token,
    ) 

    claims = InternalJWTManager.verify_token(token=token)

    # Validate write access to the working directory
    working_directory = event_body["working_directory"]

    # Validate write access to the working directory
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

    process_client = ProcessTableClient()

    proc = process_client.get_by_id(process_id=event_body["process_id"])

    if not proc:
        raise Exception(f"Process {event_body["process_id"]} not found")

    if proc.execution_status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED]:
        raise Exception(f"Process {event_body["process_id"]} is already closed with status {proc.execution_status}")

    logging.debug(f"Validate file access response: {validate_file_access_response}")

    if validate_file_access_response.status_code == 404:
        logging.debug(f"Agent definition path does not exist: {event_body["agent_definition_path"]}")

        _close_out_process(
            process=proc,
            failure_reason="agent definition path does not exist",
            token=token,
        )

        return

    entity_has_access = validate_file_access_response.response_body.get("entity_has_access", False)

    if not entity_has_access:
        logging.debug(f"Requestor does not have access to agent definition path: {event_body["agent_definition_path"]}")

        _close_out_process(
            process=proc,
            failure_reason="requestor does not have access to agent definition path",
            token=token,
        )

        return

    try:
        agent_definition = AgentDefinition.load_from_fs(
            agent_file_location=event_body["agent_definition_path"],
            token=token,
        )

    except Exception as e:
        logging.debug(f"Error loading agent definition from file: {e}")

        _close_out_process(
            process=proc,
            failure_reason=f"error loading agent definition from file {e}",
            token=token,
        )

        return

    # Check if parent process is closed already
    if proc.parent_process_id != "SYSTEM":
        parent_proc = process_client.get_by_id(process_id=proc.parent_process_id)

        if not parent_proc:
            raise Exception(f"Parent process {proc.parent_process_id} not found")

        if parent_proc.execution_status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED]:
            _close_out_process(
                process=proc,
                failure_reason="parent process is already closed, cannot execute agent",
                token=token,
            )

            return

    arguments = _load_arguments(
        arguments_path=event_body["arguments_path"],
        token=token,
    )

    execution_engine = ExecutionEngine(
        arguments=arguments,
        process_id=proc.process_id,
        token=token,
        working_directory=working_directory,
        instructions=agent_definition.instructions,
        response_definition=agent_definition.responses,
        response_reference_map=agent_definition.response_reference_map,
        system_event_endpoint=agent_definition.system_event_endpoint,
    )

    execution_engine.initialize_path()

    # Create the event bus client
    event_bus_client = EventPublisher()

    if execution_engine.is_composite:
        # Schedule the instruction executions
        execution_ids = execution_engine.get_available_executions()

        if not execution_ids:
            logging.debug(f"No available executions for agent: {agent_definition}")

            _close_out_process(
                process=proc,
                failure_reason="no available executions for agent, likely due to invalid agent definition",
                token=token,
            )

            return

        _execute_children(
            claims=claims,
            execution_engine=execution_engine,
            execution_ids=execution_ids,
            parent_process=proc,
            process_client=process_client,
            token=token,
        )

    else:
        instruction = AgentInstruction(
            definition=agent_definition,
            execution_id=proc.process_id, # This isn't used for non-composite agents
            provided_arguments=arguments,
        )

        try:
            # Just executing the agent
            argument_path = execution_engine.prepare_for_execution(agent_instruction=instruction)

        except InvalidSchemaError as invalid_err:
            logging.debug(f"Error preparing for execution: {invalid_err}")

            _close_out_process(
                process=proc,
                failure_reason=f"error preparing for execution {invalid_err}",
                token=token,
            )

            return

        # Create the event
        agent_req = ObjectBody(
            body={
                "arguments_path": argument_path,
                "argument_schema": agent_definition.arguments,
                "parent_process_id": proc.parent_process_id,
                "process_id": proc.process_id,
                "response_schema": agent_definition.responses,
                "token": token,
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