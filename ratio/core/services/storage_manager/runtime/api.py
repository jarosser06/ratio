"""
Storage Manager API Interface
"""
from typing import Dict

from da_vinci.core.logging import Logger

from da_vinci.exception_trap.client import fn_exception_reporter

from ratio.core.core_lib.factories.api import ParentAPI

from ratio.core.services.storage_manager.runtime.actions import ActionsAPI
from ratio.core.services.storage_manager.runtime.files import FileAPI
from ratio.core.services.storage_manager.runtime.file_types import FileTypesAPI


_FN_NAME = "ratio.services.storage.api"


@fn_exception_reporter(function_name=_FN_NAME, logger=Logger(_FN_NAME), re_raise=True)
def handler(event: Dict, context: Dict) -> Dict:
    """
    Function handler for the API Gateway

    Utilizes the built-in API factory to create the API interfaces
    - ActionsAPI - Contains file actions like permission modifications, copy, move, etc.
    - FileAPI - Contains most of the core CRUD file operations
    - FileTypesAPI - Contains CRUD file type operations
    """
    api = ParentAPI(
        child_apis=[
            ActionsAPI,
            FileAPI,
            FileTypesAPI,
        ],
        function_name=_FN_NAME,
    )

    return api.execute_path_from_event(event=event)