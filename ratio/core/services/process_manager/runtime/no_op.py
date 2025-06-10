"""
Execute no-op tools for skipped executions.
"""

import json
import logging
import os

from datetime import datetime, UTC as utc_tz
from typing import List, Union

from da_vinci.core.immutable_object import ObjectBody

from da_vinci.event_bus.client import EventPublisher
from da_vinci.event_bus.event import Event as EventBusEvent

from ratio.core.core_lib.client import RatioInternalClient
from ratio.core.core_lib.jwt import JWTClaims

from ratio.core.services.storage_manager.request_definitions import (
    PutFileRequest,
    PutFileVersionRequest,
)

from ratio.core.services.process_manager.runtime.events import (
    SystemExecuteToolResponse,
)

from ratio.core.services.process_manager.tables.processes.client import (
    Process,
    ProcessStatus,
    ProcessTableClient,
)

from ratio.core.services.process_manager.runtime.engine import (
    TOOL_IO_FILE_TYPE,
    AIO_EXT,
    ExecutionEngine,
)

def _create_noop_response_file(execution_id: str, process_id: str, execution_engine: ExecutionEngine,
                               token: str) -> Union[str, None]:
    """
    Create a response file for the no-op execution.
    Returns the path to the created response file, or None if no responses expected.

    Keyword arguments:
    execution_id -- The ID of the execution to create a response file for.
    process_id -- The ID of the process to create a response file for.
    execution_engine -- The execution engine to use for creating the response file.
    token -- The JWT token to use for creating the response file.
    """
    instruction = execution_engine.instructions[execution_id]

    # If no responses expected, don't create a file
    if not instruction.definition.responses:
        logging.debug(f"No responses expected for {execution_id}, skipping response file creation")

        return None

    # Build the null response object
    null_responses = {}

    for response_definition in instruction.definition.responses:

        response_name = response_definition["name"]

        response_type = response_definition["type_name"]

        # Create appropriate null value based on type
        if response_type == "list":
            null_responses[response_name] = []

        elif response_type == "object":
            null_responses[response_name] = {}

        else:
            null_responses[response_name] = None

    # Use the standard response file path (in the process-specific directory)
    process_working_dir = execution_engine.get_path(
        working_dir=execution_engine.get_path(),
        process_id=process_id,
    )

    response_path = os.path.join(process_working_dir, "response" + AIO_EXT)

    # Create storage client
    storage_client = RatioInternalClient(service_name="storage_manager", token=token)

    # Create file metadata
    put_file_request = ObjectBody(
        schema=PutFileRequest,
        body={
            "file_path": response_path,
            "file_type": TOOL_IO_FILE_TYPE,
            "metadata": {
                "description": "No-op response (conditions not met)",
                "execution_id": execution_id,
                "process_id": process_id,
                "execution_type": "noop",
                "skip_reason": "conditions_not_met"
            },
            "permissions": "444",
        }
    )

    put_file_resp = storage_client.request(
        path="/storage/put_file",
        request=put_file_request
    )

    if put_file_resp.status_code not in [200, 201]:
        raise Exception(f"Failed to create no-op response file: {put_file_resp.status_code} -- {put_file_resp.body}")

    # Put the file content
    put_file_version_request = ObjectBody(
        schema=PutFileVersionRequest,
        body={
            "file_path": response_path,
            "data": json.dumps(null_responses),
            "metadata": {
                "execution_id": execution_id,
                "execution_type": "noop"
            },
            "origin": "internal",
            "source_files": [],
        }
    )

    put_version_resp = storage_client.request(
        path="/storage/put_file_version",
        request=put_file_version_request
    )

    if put_version_resp.status_code not in [200, 201]:
        raise Exception(f"Failed to put no-op response file version: {put_version_resp.status_code} -- {put_version_resp.body}")

    logging.debug(f"Created no-op response file: {response_path}")

    return response_path


def execute_no_ops(skipped_ids: List[str], execution_engine: ExecutionEngine,  parent_process: Process,
                    process_client: ProcessTableClient, claims: JWTClaims, token: str):
    """
    Execute no-op tools for skipped executions.
    Creates processes, prepares them normally, then immediately completes with null responses.

    Keyword arguments:
    skipped_ids -- The list of execution IDs to execute no-ops for.
    execution_engine -- The execution engine to use for preparing the no-op tools.
    parent_process -- The parent process to use for creating child processes.
    process_client -- The process client to use for saving the processes.
    claims -- The JWT claims to use for creating the child processes.
    token -- The JWT token to use for creating the child processes.
    """
    event_publisher = EventPublisher()

    for execution_id in skipped_ids:
        logging.info(f"Executing no-op for {execution_id} (conditions not met)")

        # Create child process just like normal execution
        child_proc = parent_process.create_child(
            execution_id=execution_id,
            execution_status=ProcessStatus.SKIPPED,
            working_directory=execution_engine.get_path(),
            process_owner=claims.entity,
        )

        try:
            # Prepare for execution just like normal tools
            execution_engine.prepare_for_execution(
                tool_instruction=execution_engine.instructions[execution_id],
                process_id=child_proc.process_id,
                working_directory=execution_engine.get_path(),
            )

            # Create null responses and save response file
            response_path = _create_noop_response_file(
                execution_id, 
                child_proc.process_id, 
                execution_engine,
                token
            )

            child_proc.response_path = response_path

            child_proc.ended_on = datetime.now(tz=utc_tz)

            process_client.put(child_proc)

            execution_engine.mark_completed(
                execution_id=execution_id,
                response_path=response_path,
            )

            # Send success response event to trigger process complete handler
            event_body = ObjectBody(
                body={
                    "parent_process_id": parent_process.process_id,
                    "process_id": child_proc.process_id,
                    "response": response_path,
                    "status": "success",
                    "token": token,
                },
                schema=SystemExecuteToolResponse,
            )

            response_event = EventBusEvent(
                body=event_body,
                event_type="ratio::tool_response"
            )

            # Delay the event to allow the system time to get it's processes to a running state to avoid possible duplication
            event_publisher.submit(event=response_event, delay=10)

            logging.info(f"No-op execution completed for {execution_id}, response event sent")

        except Exception as e:
            logging.error(f"Failed to execute no-op for {execution_id}: {e}")

            # Send failure response event
            event_body = ObjectBody(
                body={
                    "failure": f"No-op preparation failed: {str(e)}",
                    "parent_process_id": parent_process.process_id,
                    "process_id": child_proc.process_id,
                    "status": "failure",
                    "token": token,
                },
                schema=SystemExecuteToolResponse,
            )

            response_event = EventBusEvent(
                body=event_body,
                event_type="ratio::tool_response"
            )

            event_publisher.submit(event=response_event)