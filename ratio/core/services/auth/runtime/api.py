"""
Auth API
"""
from typing import Dict

from da_vinci.core.logging import Logger

from da_vinci.exception_trap.client import fn_exception_reporter

from ratio.core.core_lib.factories.api import ParentAPI

from ratio.core.services.auth.runtime.auth import AuthAPI


_FN_NAME = "ratio.services.auth.api"


@fn_exception_reporter(function_name=_FN_NAME, logger=Logger(_FN_NAME), re_raise=True)
def handler(event: Dict, context: Dict) -> Dict:
    """
    Function handler for auth service
    """
    api = ParentAPI(
        child_apis=[
            AuthAPI,
        ],
        function_name=_FN_NAME,
    )

    return api.execute_path_from_event(event=event)