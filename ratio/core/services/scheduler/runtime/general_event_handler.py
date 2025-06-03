"""
Handler for general system events, anything not a fs event
"""
import logging
import traceback

from datetime import datetime, timedelta, UTC as utc_tz

from da_vinci.core.global_settings import setting_value
from da_vinci.core.logging import Logger
from da_vinci.core.immutable_object import ObjectBody

from da_vinci.event_bus.client import fn_event_response
from da_vinci.event_bus.event import Event as EventBusEvent

from da_vinci.exception_trap.client import ExceptionReporter

from ratio.core.core_lib.client import RatioInternalClient
from ratio.core.services.scheduler.runtime.token import generate_token

from ratio.core.services.process_manager.request_definitions import (
    ExecuteToolRequest,
)

from ratio.core.services.storage_manager.request_definitions import (
    ValidateFileAccessRequest,
)

from ratio.core.services.scheduler.tables.general_subscriptions.client import (
    GeneralSubscriptionsTableClient,
)

from ratio.core.services.scheduler.request_definitions import (
    GeneralSystemEvent,
)


def _matches_filter_conditions(event_data: dict, filter_conditions: dict) -> bool:
    """
    Check if event data matches the filter conditions.

    Keyword Arguments:
    event_data -- The data of the event to check.
    filter_conditions -- The conditions to filter the event data against.
    """
    for key, expected_value in filter_conditions.items():
        if key not in event_data:
            return False

        # Simple equality check - could be enhanced for patterns, ranges, etc.
        if event_data[key] != expected_value:
            return False

    return True


_FN_NAME = "ratio.services.scheduler.general_event_handler"


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def general_event_handler(event, context):
    """
    Handler for general system events (process, file_type, etc.).
    """
    logging.debug(f"Received request: {event}")

    source_event = EventBusEvent.from_lambda_event(event)

    event_body = ObjectBody(
        body=source_event.body,
        schema=GeneralSystemEvent,
    )

    # Extract system event type from the event body
    event_type = event_body["system_event_type"]

    if not event_type:
        logging.debug("No event_type found in event body")

        return

    subscriptions_client = GeneralSubscriptionsTableClient()

    # Get all subscriptions for this event type
    subscriptions = subscriptions_client.get_by_event_type(event_type=event_type)

    if not subscriptions:
        logging.debug(f"No subscriptions found for event type {event_type}")

        return

    exception_reporter = ExceptionReporter()

    recursion_detection_enabled = setting_value(namespace="ratio::core", setting_key="enforce_recursion_detection")

    recursion_threshold_seconds = setting_value(namespace="ratio::core", setting_key="recursion_detection_threshold")

    for subscription in subscriptions:
        # Apply filter conditions if they exist
        if subscription.filter_conditions:
            if not _matches_filter_conditions(event_data=source_event.body, filter_conditions=subscription.filter_conditions):
                logging.debug(f"Event does not match filter conditions for subscription {subscription.subscription_id}")

                continue

        # Check recursion detection
        if subscription.last_execution and recursion_detection_enabled:
            last_threshold = datetime.now(tz=utc_tz) - timedelta(seconds=int(recursion_threshold_seconds))

            if subscription.last_execution > last_threshold:
                logging.debug(f"Subscription {subscription.subscription_id} was executed less than {recursion_threshold_seconds} seconds ago")

                err_msg = f"possible recursion detected for subscription {subscription.event_type} - {subscription.subscription_id}"

                exception_reporter.report(
                    function_name=_FN_NAME,
                    exception=err_msg,
                    exception_traceback=err_msg,
                    originating_event=subscription.to_dict(json_compatible=True),
                )

                continue

        token = generate_token(entity_id=subscription.process_owner)

        # Validate tool definition access
        validate_file_access_request = ObjectBody(
            body={
                "file_path": subscription.tool_definition,
                "requested_permission_names": ["execute"],
            },
            schema=ValidateFileAccessRequest,
        )

        storage_client = RatioInternalClient(service_name="storage_manager", token=token)

        validation_response = storage_client.request(
            path="/validate_file_access", 
            request=validate_file_access_request
        )

        logging.debug(f"Validation response: {validation_response}")

        if validation_response.status_code == 404:
            logging.debug(f"Tool definition {subscription.tool_definition} not found")

            err_msg = f"tool definition path {subscription.tool_definition} for subscription {subscription.event_type} - {subscription.subscription_id} not found"

            exception_reporter.report(
                function_name=_FN_NAME,
                exception=err_msg,
                exception_traceback=err_msg,
                originating_event=subscription.to_dict(json_compatible=True),
            )

            continue

        entity_has_access = validation_response.response_body.get("entity_has_access", False)

        if not entity_has_access:
            logging.debug(f"Entity {subscription.process_owner} does not have access to {subscription.tool_definition}")

            err_msg = f"entity {subscription.process_owner} does not have access to tool definition path {subscription.tool_definition} for subscription {subscription.event_type} - {subscription.subscription_id}"

            exception_reporter.report(
                function_name=_FN_NAME,
                exception=err_msg,
                exception_traceback=err_msg,
                originating_event=subscription.to_dict(json_compatible=True),
            )

            continue

        # Execute the tool
        tool_mgr = RatioInternalClient(service_name="process_manager", token=token)

        try:
            tool_exec_req = ObjectBody(
                body={
                    "arguments": {
                        "event_type": event_type,
                        "event_details": event_body["event_details"],
                        "source_system": event_body["source_system"],
                    },
                    "tool_definition_path": subscription.tool_definition,
                    "working_directory": subscription.execution_working_directory,
                },
                schema=ExecuteToolRequest,
            )

            logging.debug(f"Executing tool {subscription.tool_definition} with request {tool_exec_req}")

            tool_response = tool_mgr.request(path="/execute", request=tool_exec_req)

            assert tool_response.status_code == 200, f"Tool execution failed with status code {tool_response.status_code} and message {tool_response.response_body}"

            process_id = tool_response.response_body["process_id"]

            logging.debug(f"Tool executed with process ID {process_id}")

            if subscription.single_use:
                # Delete the subscription if it is single use
                subscriptions_client.delete(subscription=subscription)

            else:
                # Update the last execution time
                subscription.last_execution = datetime.now(tz=utc_tz)

                subscriptions_client.put(subscription=subscription)

        except Exception as tool_exec_error:
            logging.debug(f"Tool execution failed: {tool_exec_error}")

            err_msg = f"Tool execution failed for subscription {subscription.event_type} - {subscription.subscription_id} with error {tool_exec_error}"

            exception_reporter.report(
                function_name=_FN_NAME,
                exception=err_msg,
                exception_traceback=traceback.format_exc(),
                originating_event=subscription.to_dict(json_compatible=True),
            )

            continue