"""
Internal API Call Tool

Simply executes an internal API request
"""
import json
import logging

from typing import Dict

from da_vinci.core.logging import Logger

from da_vinci.event_bus.client import fn_event_response

from da_vinci.exception_trap.client import ExceptionReporter

from ratio.tools.tool_lib import RatioSystem


_FN_NAME = "ratio.tools.internal_api"


@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    """
    Execute the internal API request.
    """
    system = RatioSystem.from_da_vinci_event(event)

    with system:
        path = system.arguments["path"]

        request = system.arguments["request"]

        fail_on_error = system.arguments.get("fail_on_error", default_return=True)

        target_service_name = system.arguments["target_service"]

        logging.debug(f"Calling internal API: {target_service_name} {path} {request}")

        api_resp = system.internal_api_request(
            api_target=target_service_name,
            path=path,
            request=request,
            raise_on_failure=fail_on_error,
        )

        logging.debug(f"API response: {api_resp}")

        response_body = api_resp.response_body or {}

        if api_resp.status_code >= 300:
            logging.error(f"API request failed: {api_resp.status_code} {response_body}")

            response_body = None

            try:
                response_body = json.loads(api_resp.response_body)

            except json.JSONDecodeError:

                # If the response body is not JSON, log the error
                logging.error(f"Failed to parse response body: {api_resp.response_body}")

                response_body = {"message": api_resp.response_body}

        system.success(
            response_body={
                "response_body": response_body,
                "status_code": api_resp.status_code,
            }
        )