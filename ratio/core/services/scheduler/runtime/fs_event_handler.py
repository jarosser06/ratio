import logging
import os
import traceback

from datetime import datetime, timedelta, UTC as utc_tz

from da_vinci.core.global_settings import setting_value
from da_vinci.core.logging import Logger
from da_vinci.core.immutable_object import ObjectBody

from da_vinci.event_bus.client import fn_event_response
from da_vinci.event_bus.event import Event as EventBusEvent

from da_vinci.exception_trap.client import ExceptionReporter


from ratio.core.core_lib.client import RatioInternalClient
from ratio.core.core_lib.jwt import InternalJWTManager

from ratio.core.tables.entities.client import (
    EntitiesTableClient,
)

from ratio.core.services.process_manager.request_definitions import (
    ExecuteToolRequest,
)

from ratio.core.services.storage_manager.request_definitions import (
    FileUpdateEvent,
    ValidateFileAccessRequest,
)

from ratio.core.services.scheduler.tables.filesystem_subscriptions.client import (
    FilesystemSubscription,
    FilesystemSubscriptionsTableClient,
)

from ratio.core.services.scheduler.runtime.token import generate_token


_FN_NAME = "ratio.services.tools.scheduler.fs_update_handler"


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def fs_update_handler(event, context):
    """
    Handler for file system update events.
    """
    logging.debug(f"Received request: {event}")

    source_event = EventBusEvent.from_lambda_event(event)

    event_body = ObjectBody(
        body=source_event.body,
        schema=FileUpdateEvent,
    )

    subscriptions_client = FilesystemSubscriptionsTableClient()

    file_path_hash = FilesystemSubscription.create_full_path_hash_from_path(file_path=event_body["file_path"])

    # Find all subscriptions for the file
    subscriptions = subscriptions_client.get_by_full_path_hash(full_path_hash=file_path_hash)

    # Get the parent directory to catch any subscriptions to the parent directory
    parent_dir = os.path.dirname(event_body["file_path"])

    parent_dir_hash = FilesystemSubscription.create_full_path_hash_from_path(file_path=parent_dir)

    # Find all subscriptions for the parent directory
    parent_dir_subscriptions = subscriptions_client.get_by_full_path_hash(full_path_hash=parent_dir_hash)

    # Merge the subscriptions
    subscriptions.extend(parent_dir_subscriptions)

    if not subscriptions:
        logging.debug(f"No subscriptions found for file path {event_body["file_path"]}")

        return

    exception_reporter = ExceptionReporter()

    # Check if recursion is enabled
    recursion_detection_enabled = setting_value(namespace="ratio::core", setting_key="enforce_recursion_detection")

    logging.debug(f"Recursion detection flag: {recursion_detection_enabled}")

    recursion_threshold_seconds = setting_value(namespace="ratio::core", setting_key="recursion_detection_threshold")

    # Find the subscriptions that have access
    for subscription in subscriptions:
        if subscription.file_type and subscription.file_type != event_body["file_type"]:
            logging.debug(f"File type {event_body['file_type']} does not match subscription file type {subscription.file_type}")

            continue

        if subscription.file_event_type != event_body["file_event_type"]:
            logging.debug(f"File event type {event_body['file_event_type']} does not match subscription file event type {subscription.file_event_type}")

            continue

        last_execution = subscription.last_execution

        if last_execution and recursion_detection_enabled:
            last_threshold = datetime.now(tz=utc_tz) - timedelta(seconds=int(recursion_threshold_seconds))

            if last_execution > last_threshold:
                logging.debug(f"Subscription {subscription.subscription_id} was executed less than {recursion_threshold_seconds} seconds ago")

                if recursion_detection_enabled:
                    err_msg = f"possible recursion detected for subscription {subscription.file_path} - {subscription.subscription_id}"

                    exception_reporter.report(
                        function_name=_FN_NAME,
                        exception=err_msg,
                        exception_traceback=err_msg,
                        originating_event=subscription.to_dict(json_compatible=True),
                    )

                continue

        token = generate_token(entity_id=subscription.process_owner)

        # Validate the tool definition path
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
            request=validate_file_access_request,
        )

        logging.debug(f"Validation response: {validation_response}")

        if validation_response.status_code == 404:
            logging.debug(f"Subscribed file {subscription.tool_definition} not found")

            err_msg = f"tool definition path {subscription.tool_definition} for subscription {subscription.file_path} - {subscription.subscription_id} not found"

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

            err_msg = f"entity {subscription.process_owner} does not have access to tool definition path {subscription.tool_definition} for subscription {subscription.file_path} - {subscription.subscription_id}"

            exception_reporter.report(
                function_name=_FN_NAME,
                exception=err_msg,
                exception_traceback=err_msg,
                originating_event=subscription.to_dict(json_compatible=True),
            )

            continue

        tool_mgr = RatioInternalClient(
            service_name="process_manager",
            token=token,
        )

        try:
            tool_exec_req = ObjectBody(
                body={
                    "arguments": {
                        "event_details": event_body.get("details"),
                        "file_path": event_body["file_path"],
                        "file_event_type": event_body["file_event_type"],
                    },
                    "tool_definition_path": subscription.tool_definition,
                    "working_directory": subscription.execution_working_directory,
                },
                schema=ExecuteToolRequest,
            )

            logging.debug(f"Executing tool {subscription.tool_definition} with request {tool_exec_req}")

            tool_response = tool_mgr.request(
                path="/execute",
                request=tool_exec_req,
            )

            assert tool_response.status_code == 200, f"Tool execution failed with status code {tool_response.status_code} and message {tool_response.response_body}"

            process_id = tool_response.response_body["process_id"]

            logging.debug(f"Tool executed with process ID {process_id}")

            if subscription.single_use:
                # Delete the subscription if it is single use
                subscriptions_client.delete(subscription_id=subscription.subscription_id)

            else:
                # Update the last execution time
                subscription.last_execution = datetime.now(tz=utc_tz)

                subscriptions_client.put(subscription=subscription)

        except Exception as tool_exec_error:
            logging.debug(f"Tool execution failed: {tool_exec_error}")

            err_msg = f"Tool execution failed for subscription {subscription.file_path} - {subscription.subscription_id} with error {tool_exec_error}"

            exception_reporter.report(
                function_name=_FN_NAME,
                exception=err_msg,
                exception_traceback=traceback.format_exc(),
                originating_event=subscription.to_dict(json_compatible=True),
            )

            continue