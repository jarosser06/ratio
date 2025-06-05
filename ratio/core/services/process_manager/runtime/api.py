"""
Process API Interface
"""
import json
import logging

from typing import Dict

from da_vinci.core.logging import Logger
from da_vinci.core.immutable_object import ObjectBody

from da_vinci.exception_trap.client import fn_exception_reporter

from ratio.core.core_lib.factories.api import ChildAPI, ParentAPI, Route
from ratio.core.core_lib.jwt import JWTClaims

from ratio.core.services.process_manager.request_definitions import (
    DescribeProcessRequest,
    KillProcessRequest,
    ListProcessesRequest,
)

from ratio.core.services.process_manager.tables.processes.client import ProcessTableClient

from ratio.core.services.process_manager.runtime.execute import ExecuteAPI


class DescribeAPI(ChildAPI):
    routes = [
        Route(
            path="/process/describe_process",
            method_name="describe_process",
            request_body_schema=DescribeProcessRequest,
        ),
        Route(
            path="/process/kill_process",
            method_name="not_implemented",
            request_body_schema=KillProcessRequest,
        ),
        Route(
            path="/process/list_processes",
            method_name="list_processes",
            request_body_schema=ListProcessesRequest,
        ),
    ]

    def describe_process(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Describe a process
        """
        claims = JWTClaims.from_claims(claims=request_context['request_claims'])

        proc_client = ProcessTableClient()

        process = proc_client.get_by_id(process_id=request_body["process_id"])

        if not process:
            return self.respond(
                status_code=404,
                body={"error": "Process not found"},
            )

        if not claims.is_admin and process.process_owner != claims.entity:
            return self.respond(
                status_code=403,
                body={"error": "Permission denied"},
            )

        return self.respond(
            status_code=200,
            body=process.to_dict(
                exclude_attribute_names=["time_to_live"],
                json_compatible=True,
            ),
        )

    def list_processes(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        List processes
        """
        claims = JWTClaims.from_claims(claims=request_context["request_claims"])

        proc_client = ProcessTableClient()

        process_owner = request_body.get("process_owner")

        if not claims.is_admin and claims.entity != process_owner:
            logging.debug(f"Entity {claims.entity} is not admin and is requesting processes for other entity {process_owner}")
            # This should be considered a security incident and logged specially when possible

            return self.respond(
                status_code=403,
                body={"message": "permission denied"},
            )

        if not process_owner and not claims.is_admin:
            logging.debug(f"Entity {claims.entity} is not admin and is requesting processes without owner")

            process_owner = claims.entity

        processes = proc_client.list(
            process_owner=process_owner,
            parent_process_id=request_body.get("parent_process_id"),
            execution_status=request_body.get("execution_status"),
        )

        response = [process.to_dict(json_compatible=True, exclude_attribute_names=["time_to_live"]) for process in processes]

        logging.debug(f"Returning {response}")

        return self.respond(
            status_code=200,
            body={"processes": response},
        )


_FN_NAME = "ratio.services.process.api"


@fn_exception_reporter(function_name=_FN_NAME, logger=Logger(_FN_NAME), re_raise=True)
def handler(event: Dict, context: Dict) -> Dict:
    """
    Function handler for the API Gateway

    Utilizes the built-in API factory to create the API interfaces
    """
    logging.debug(f"Agent API handler called with: {event}")

    api = ParentAPI(
        child_apis=[
            DescribeAPI,
            ExecuteAPI,
        ],
        function_name=_FN_NAME,
    )

    body = event.get("body")

    logging.debug(f"Agent API called with: {body}")

    kwargs = {}

    if body:
        kwargs = json.loads(body)

    headers = event.get("headers", {})

    if headers:
        kwargs["_headers"] = headers

    logging.debug(f"Executing path: {event["rawPath"]}")

    return api.execute_path(path=event["rawPath"], **kwargs)