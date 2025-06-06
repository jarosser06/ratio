"""
Primary API
"""
import json
import logging

from typing import Dict

from da_vinci.core.logging import Logger

from da_vinci.exception_trap.client import fn_exception_reporter

from ratio.core.core_lib.factories.api import ParentAPI

from ratio.core.api.runtime.process import ProcessAPI
from ratio.core.api.runtime.auth import AuthAPI
from ratio.core.api.runtime.scheduler import SchedulerAPI
from ratio.core.api.runtime.storage import StorageAPI


_FN_NAME = "ratio.core.api"


@fn_exception_reporter(function_name=_FN_NAME, logger=Logger(_FN_NAME), re_raise=True)
def handler(event: Dict, context: Dict) -> Dict:
    """
    Function handler for the API Gateway
    """
    api = ParentAPI(
        child_apis=[
            ProcessAPI,
            AuthAPI,
            SchedulerAPI,
            StorageAPI,
        ],
        function_name=_FN_NAME,
    )

    body = event.get("body")

    kwargs = {}

    if body:
        kwargs = json.loads(body)

    headers = event.get("headers", {})

    if headers:
        kwargs["_headers"] = headers

    logging.debug(f"Executing path: {event["rawPath"]}")

    return api.execute_path(path=event["rawPath"], **kwargs)