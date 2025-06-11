import logging
import traceback

from typing import Optional

from da_vinci.event_bus.event import Event as EventBusEvent

from da_vinci.exception_trap.client import ExceptionReporter

from ratio.core.core_lib.websocket import (
    WebSocketMessenger,
    WebSocketSendError,
    WebSocketConnectionNotFoundError,
)

from ratio.core.services.process_manager.tables.processes.client import Process


def stream_response(process: Process, failure_reason: Optional[str] = None,
                    final_response: bool = False, response_path: Optional[str] = None,
                    source_event: Optional[EventBusEvent] = None):
    """
    Stream the response to the WebSocket connection.

    Keyword arguments:
    process -- The Process object containing the process details.
    failure_reason -- Optional reason for failure, if any.
    final_response -- Boolean indicating if this is the final response.
    response_path -- Optional path to the response, if available.
    source_event -- Optional EventBusEvent that triggered this function, only used for error reporting.
    """
    websocket_connection_id = process.websocket_connection_id

    if not websocket_connection_id:
        logging.debug(f"Process {process.process_id} has no WebSocket connection ID, skipping streaming response")

        return

    ws_body = {
        "final_response": final_response,
        "process_id": process.process_id,
        "parent_process_id": process.parent_process_id,
    }

    if failure_reason:
        ws_body["failure"] = failure_reason

    elif response_path:
        ws_body["response"] = response_path

    else:
        raise ValueError("Either failure_reason or response_path must be provided")

    if process.parent_process_id == "SYSTEM":
        ws_body["final_response"] = True

    try:
        ws_messenger = WebSocketMessenger(
            connection_id=websocket_connection_id,
        )

        ws_messenger.send_message(
            data=ws_body,
        )

    except (WebSocketSendError, WebSocketConnectionNotFoundError) as ws_err:
        logging.debug(f"Error sending WebSocket message: {ws_err} ... reporting and ignoring")

        exception_reporter = ExceptionReporter()

        exception_reporter.report(
            function_name="process_stream_response",
            exception=str(ws_err),
            exception_traceback=traceback.format_exc(),
            originating_event=source_event,
        )