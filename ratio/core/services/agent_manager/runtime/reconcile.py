"""
Process Reconciliation Business Logic

Handles stuck processes, timeouts, and race conditions.
"""
import logging
import re

from datetime import datetime, timedelta, UTC as utc_tz
from typing import Dict, List

from da_vinci.core.global_settings import setting_value
from da_vinci.core.logging import Logger
from da_vinci.core.immutable_object import ObjectBody

from da_vinci.exception_trap.client import fn_exception_reporter
from da_vinci.event_bus.client import EventPublisher
from da_vinci.event_bus.event import Event as EventBusEvent

from ratio.core.core_lib.jwt import InternalJWTManager

from ratio.core.services.agent_manager.tables.processes.client import (
    Process,
    ProcessStatus,
    ProcessTableClient,
    TableScanDefinition,
)

from ratio.core.services.agent_manager.runtime.events import (
    ParallelCompletionReconciliationRequest,
    SystemExecuteAgentResponse,
)


def update_process_with_reconciliation(process: Process, reason: str, process_client: ProcessTableClient) -> None:
    """
    Update process status message with reconciliation information.

    Keyword arguments:
    process -- The Process object to update
    reason -- The reason for reconciliation
    """
    timestamp = datetime.now(tz=utc_tz).isoformat()

    reconciliation_note = f"reconciled: {reason} at {timestamp}"

    existing_message = process.status_message or ""
    if existing_message:
        process.status_message = f"{existing_message} | {reconciliation_note}"

    else:
        process.status_message = reconciliation_note

    process_client.put(process)

    logging.info(f"Updated process {process.process_id} with reconciliation: {reason}")


def handle_timed_out_processes(process_client: ProcessTableClient, event_publisher: EventPublisher) -> List[str]:
    """
    Find and handle processes that have been running longer than 15 minutes.

    Keyword arguments:
    process_client -- The ProcessTableClient instance to interact with the process table
    event_publisher -- The EventPublisher instance to send events
    """
    logging.info("Checking for timed out processes...")

    global_timeout_minutes = setting_value(
        namespace="ratio::agent_manager",
        setting_key="global_process_timeout_minutes",
    )

    cutoff_time = datetime.now(tz=utc_tz) - timedelta(minutes=global_timeout_minutes)

    logging.info(f"Cutoff time for process timeout is {cutoff_time.isoformat()} (global timeout: {global_timeout_minutes} minutes)")

    # Scan for running processes older than the cutoff time
    scan_definition = TableScanDefinition(table_object_class=Process)

    scan_definition.add("execution_status", "equal", ProcessStatus.RUNNING)

    scan_definition.add("started_on", "less_than", cutoff_time)

    timed_out_processes = process_client.full_scan(scan_definition=scan_definition)

    reconciled_process_ids = []

    for process in timed_out_processes:
        logging.warning(f"Process {process.process_id} has timed out (running for >15 minutes)")

        # Mark as timed out
        process.execution_status = ProcessStatus.TIMED_OUT

        process.ended_on = datetime.now(tz=utc_tz)

        update_process_with_reconciliation(process, "timed out after 15 minutes", process_client)

        # Send failure notification to parent if not system level
        if process.parent_process_id != "SYSTEM":
            parent_proc = process_client.get_by_id(process_id=process.parent_process_id)

            if parent_proc:
                # Create internal JWT token for the notification
                jwt_manager = InternalJWTManager(
                    expiry_minutes=5,
                    kms_key_id=setting_value(namespace="ratio::core", setting_key="internal_signing_kms_key_id"),
                )

                internal_token, _ = jwt_manager.create_token(
                    entity=parent_proc.process_owner,
                    authorized_groups=["system"],
                    primary_group="system",
                )

                event_body = ObjectBody(
                    body={
                        "failure": "process timed out after 15 minutes",
                        "parent_process_id": parent_proc.parent_process_id,
                        "process_id": parent_proc.process_id,
                        "status": ProcessStatus.TIMED_OUT,
                        "token": internal_token,
                    },
                    schema=SystemExecuteAgentResponse,
                )

                event_publisher.submit(
                    event=EventBusEvent(
                        body=event_body,
                        event_type="ratio::agent_response",
                    )
                )

                logging.info(f"Sent timeout notification to parent process {parent_proc.process_id}")

        reconciled_process_ids.append(process.process_id)

    logging.info(f"Handled {len(timed_out_processes)} timed out processes")

    return reconciled_process_ids


def handle_stuck_parent_processes(process_client: ProcessTableClient, event_publisher: EventPublisher) -> List[str]:
    """
    Find and handle parent processes where all children are done but parent is still running.

    Keyword arguments:
    process_client -- The ProcessTableClient instance to interact with the process table
    event_publisher -- The EventPublisher instance to send events
    """
    logging.info("Checking for stuck parent processes...")

    # Get all running processes
    scan_definition = TableScanDefinition(table_object_class=Process)

    scan_definition.add("execution_status", "equal", ProcessStatus.RUNNING)

    running_processes = process_client.full_scan(scan_definition=scan_definition)

    stuck_parents = []

    reconciled_process_ids = []

    terminal_states = [
        ProcessStatus.COMPLETED, 
        ProcessStatus.FAILED, 
        ProcessStatus.SKIPPED,
        ProcessStatus.TERMINATED,
        ProcessStatus.TIMED_OUT
    ]

    # Find processes that have children (potential parents)
    for process in running_processes:
        children = process_client.get_by_parent(parent_process_id=process.process_id)

        if not children:
            continue  # Not a parent process

        all_children_done = all(child.execution_status in terminal_states for child in children)

        if all_children_done:
            stuck_parents.append(process)

            logging.warning(f"Found stuck parent process {process.process_id} - all children complete but parent still running")

    # Handle stuck parents
    for parent in stuck_parents:
        update_process_with_reconciliation(parent, "stuck parent process unstuck", process_client)

        jwt_manager = InternalJWTManager(
            expiry_minutes=5,
            kms_key_id=setting_value(namespace="ratio::core", setting_key="internal_signing_kms_key_id"),
        )

        internal_token, _ = jwt_manager.create_token(
            entity=parent.process_owner,
            authorized_groups=["system"],
            primary_group="system",
        )

        # Find a completed child to use as the trigger
        children = process_client.get_by_parent(parent_process_id=parent.process_id)

        completed_child = next((child for child in children if child.execution_status == ProcessStatus.COMPLETED), None)

        if completed_child:
            event_body = ObjectBody(
                body={
                    "parent_process_id": parent.parent_process_id,
                    "process_id": parent.process_id,
                    "response": completed_child.response_path,
                    "status": ProcessStatus.COMPLETED,
                    "token": internal_token,
                },
                schema=SystemExecuteAgentResponse,
            )

        else:
            # If no completed children, just trigger with no response
            event_body = ObjectBody(
                body={
                    "parent_process_id": parent.parent_process_id,
                    "process_id": parent.process_id,
                    "status": ProcessStatus.COMPLETED,
                    "token": internal_token,
                },
                schema=SystemExecuteAgentResponse,
            )

        event_publisher.submit(
            event=EventBusEvent(
                body=event_body,
                event_type="ratio::agent_response",
            )
        )

        logging.info(f"Triggered completion event for stuck parent process {parent.process_id}")

        reconciled_process_ids.append(parent.process_id)

    logging.info(f"Handled {len(stuck_parents)} stuck parent processes")

    return reconciled_process_ids


_PARALLEL_RECONCILE_FN_NAME = "ratio.services.agents.parallel_completion_reconciliation"

@fn_exception_reporter(function_name=_PARALLEL_RECONCILE_FN_NAME, logger=Logger(_PARALLEL_RECONCILE_FN_NAME), re_raise=True)
def parallel_completion_reconciliation_handler(event: Dict, context: Dict):
    """
    Handle parallel completion reconciliation for potentially stuck parallel groups.
    Re-attempts completion coordination after a delay to handle timing races.
    """
    logging.info("Starting parallel completion reconciliation...")

    source_event = EventBusEvent.from_lambda_event(event)

    event_body = ObjectBody(
        body=source_event.body,
        schema=ParallelCompletionReconciliationRequest,
    )

    parent_process_id = event_body["parent_process_id"]

    original_execution_id = event_body["original_execution_id"] 

    token = event_body["token"]

    process_client = ProcessTableClient()

    event_publisher = EventPublisher()

    # Get the parent process
    parent_proc = process_client.get_by_id(process_id=parent_process_id)

    if not parent_proc:
        logging.warning(f"Parent process {parent_process_id} not found during parallel reconciliation")

        return

    terminal_states = [ProcessStatus.COMPLETED, ProcessStatus.FAILED, ProcessStatus.SKIPPED, ProcessStatus.TERMINATED, ProcessStatus.TIMED_OUT]

    if parent_proc.execution_status in terminal_states:
        logging.info(f"Parent process {parent_process_id} already completed, no reconciliation needed")

        return

    # Get all children and filter for this parallel group
    all_children = process_client.get_by_parent(parent_process_id=parent_proc.process_id)

    sibling_pattern = re.compile(rf'^{re.escape(original_execution_id)}\[\d+\]$')

    parallel_children = [child for child in all_children if child.execution_id and sibling_pattern.match(child.execution_id)]

    if not parallel_children:
        logging.warning(f"No parallel children found for execution_id {original_execution_id} in parent {parent_process_id}")

        return

    all_parallel_complete = all(child.execution_status in terminal_states for child in parallel_children)

    if not all_parallel_complete:
        logging.info(f"Parallel group {original_execution_id} still not complete, no action needed")

        return

    # All parallel children are complete - determine the right status to send
    logging.warning(f"Found stuck parallel group {original_execution_id} in parent {parent_process_id} - triggering completion")

    update_process_with_reconciliation(parent_proc, f"stuck parallel group {original_execution_id} reconciled", process_client)

    # Check status of parallel children to determine parent outcome
    failed_children = [child for child in parallel_children if child.execution_status == ProcessStatus.FAILED]

    completed_children = [child for child in parallel_children if child.execution_status == ProcessStatus.COMPLETED]

    if failed_children:
        # If any parallel child failed, the whole group fails
        failed_child = failed_children[0]

        event_body = ObjectBody(
            body={
                "failure": failed_child.status_message or f"parallel child {failed_child.execution_id} failed",
                "parent_process_id": parent_proc.parent_process_id,
                "process_id": parent_proc.process_id,
                "status": ProcessStatus.FAILED,
                "token": token,
            },
            schema=SystemExecuteAgentResponse,
        )

        logging.warning(f"Triggering failure event for parallel group {original_execution_id} due to failed child {failed_child.execution_id}")

    elif completed_children:
        # Success case - use completed child response
        completed_child = completed_children[0]

        event_body = ObjectBody(
            body={
                "parent_process_id": parent_proc.parent_process_id,
                "process_id": parent_proc.process_id,
                "response": completed_child.response_path,
                "status": ProcessStatus.COMPLETED,
                "token": token,
            },
            schema=SystemExecuteAgentResponse,
        )

        logging.info(f"Triggering success event for parallel group {original_execution_id}")

    else:
        # All skipped or other terminal states - treat as success but no response
        event_body = ObjectBody(
            body={
                "parent_process_id": parent_proc.parent_process_id,
                "process_id": parent_proc.process_id,
                "status": ProcessStatus.COMPLETED,
                "token": token,
            },
            schema=SystemExecuteAgentResponse,
        )

        logging.info(f"Triggering completion event for parallel group {original_execution_id} (all skipped/terminated)")

    event_publisher.submit(
        event=EventBusEvent(
            body=event_body,
            event_type="ratio::agent_response",
        )
    )

    logging.info(f"Parallel completion reconciliation for {parent_process_id} completed successfully")


_RECONCILE_FN_NAME = "ratio.services.agents.process_reconciliation"


@fn_exception_reporter(function_name=_RECONCILE_FN_NAME, logger=Logger(_RECONCILE_FN_NAME), re_raise=True)
def reconcile_processes(event: Dict, context: Dict) -> Dict:
    """
    Reconcile stuck and timed out processes.
    """
    logging.info("Starting process reconciliation...")

    process_client = ProcessTableClient()

    event_publisher = EventPublisher()

    try:
        # Handle stuck parent processes  
        stuck_parent_ids = handle_stuck_parent_processes(process_client, event_publisher)

        # Handle timed out processes
        timed_out_ids = handle_timed_out_processes(process_client, event_publisher)

        total_reconciled = len(timed_out_ids) + len(stuck_parent_ids)

        logging.info(f"Process reconciliation completed. Reconciled {total_reconciled} processes")

        logging.info(f"Timed out: {timed_out_ids}")

        logging.info(f"Stuck parents: {stuck_parent_ids}")

    except Exception as e:
        logging.error(f"Error during process reconciliation: {e}")

        raise