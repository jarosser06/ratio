"""
Storage API
"""
from typing import Dict

from da_vinci.core.immutable_object import ObjectBody

from ratio.core.core_lib.client import RatioInternalClient

from ratio.core.core_lib.factories.api import ChildAPI, Route

from ratio.core.services.storage_manager.request_definitions import (
    ChangeFilePermissionsRequest,
    CopyFileRequest,
    DescribeFileRequest,
    DescribeFileTypeRequest,
    DescribeFileVersionRequest,
    DeleteFileTypeRequest,
    DeleteFileRequest,
    DeleteFileVersionRequest,
    GetFileVersionRequest,
    GetDirectFileVersionRequest,
    ListFilesRequest,
    ListFileVersionsRequest,
    PutFileRequest,
    PutFileTypeRequest,
    PutFileVersionRequest,
    PutDirectFileVersionCompleteRequest,
    PutDirectFileVersionStartRequest,
    ValidateFileAccessRequest,
)


class StorageAPI(ChildAPI):
    """
    Storage API Proxy for managing file storage and retrieval
    """
    routes = [
        Route(
            path="/storage/change_file_permissions",
            method_name="storage_request",
            request_body_schema=ChangeFilePermissionsRequest,
        ),
        Route(
            path="/storage/copy_file",
            method_name="storage_request",
            request_body_schema=CopyFileRequest,
        ),
        Route(
            path="/storage/describe_file",
            method_name="storage_request",
            request_body_schema=DescribeFileRequest,
        ),
        Route(
            path="/storage/describe_file_type",
            method_name="storage_request",
            request_body_schema=DescribeFileTypeRequest,
        ),
        Route(
            path="/storage/describe_file_version",
            method_name="storage_request",
            request_body_schema=DescribeFileVersionRequest,
        ),
        Route(
            path="/storage/delete_file_type",
            method_name="storage_request",
            request_body_schema=DeleteFileTypeRequest,
        ),
        Route(
            path="/storage/delete_file",
            method_name="storage_request",
            request_body_schema=DeleteFileRequest,
        ),
        Route(
            path="/storage/delete_file_version",
            method_name="storage_request",
            request_body_schema=DeleteFileVersionRequest,
        ),
        Route(
            path="/storage/get_file_version",
            method_name="storage_request",
            request_body_schema=GetFileVersionRequest,
        ),
        Route(
            path="/storage/get_direct_file_version",
            method_name="storage_request",
            request_body_schema=GetDirectFileVersionRequest,
        ),
        Route(
            path="/storage/list_files",
            method_name="storage_request",
            request_body_schema=ListFilesRequest,
        ),
        Route(
            path="/storage/list_file_types",
            method_name="storage_request",
            request_body_schema=None,
        ),
        Route(
            path="/storage/list_file_versions",
            method_name="storage_request",
            request_body_schema=ListFileVersionsRequest,
        ),
        Route(
            path="/storage/put_file",
            method_name="storage_request",
            request_body_schema=PutFileRequest,
        ),
        Route(
            path="/storage/put_file_type",
            method_name="storage_request",
            request_body_schema=PutFileTypeRequest,
        ),
        Route(
            path="/storage/put_file_version",
            method_name="storage_request",
            request_body_schema=PutFileVersionRequest,
        ),
        Route(
            path="/storage/put_direct_file_version_complete",
            method_name="storage_request",
            request_body_schema=PutDirectFileVersionCompleteRequest,
        ),
        Route(
            path="/storage/put_direct_file_version_start",
            method_name="storage_request",
            request_body_schema=PutDirectFileVersionStartRequest,
        ),
        Route(
            path="/storage/validate_file_access",
            method_name="storage_request",
            request_body_schema=ValidateFileAccessRequest,
        ),
    ]

    def __init__(self):
        """
        Initialize the StorageAPI
        """
        super().__init__()

    def storage_request(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Storage API request proxy handler for the storage manager service.
        This proxies all requests to the internal storage manager service by using the
        same requests the storage manager service would use.

        Keyword arguments:
        path -- The path to the API endpoint
        request -- The request body to send to the API
        """
        storage_client = RatioInternalClient(
            service_name="storage_manager",
            token=request_context["signed_token"]
        )

        path = request_context["path"].replace("/storage", "")

        response = storage_client.request(path=path, request=request_body)

        return self.respond(
            body=response.response_body,
            status_code=response.status_code,
        )