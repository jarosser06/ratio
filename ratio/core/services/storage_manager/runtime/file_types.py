"""
File Types API
"""
import logging
from typing import Dict

from da_vinci.core.immutable_object import ObjectBody

from ratio.core.core_lib.factories.api import ChildAPI, Route
from ratio.core.core_lib.jwt import JWTClaims

from ratio.core.services.storage_manager.request_definitions import (
    DeleteFileTypeRequest,
    DescribeFileTypeRequest,
    PutFileTypeRequest,
)

from ratio.core.services.storage_manager.tables.files.client import (
    FilesTableClient,
)
from ratio.core.services.storage_manager.tables.file_types.client import (
    FileType,
    FileTypeTableClient,
)

from ratio.core.services.storage_manager.runtime.events import (
    publish_file_type_update_event,
)


class FileTypesAPI(ChildAPI):
    routes = [
        Route(
            path="/storage/delete_file_type",
            method_name="delete_file_type",
            request_body_schema=DeleteFileTypeRequest,
        ),
        Route(
            path="/storage/describe_file_type",
            method_name="describe_file_type",
            request_body_schema=DescribeFileTypeRequest,
        ),
        Route(
            path="/storage/list_file_types",
            method_name="list_file_types",
            request_body_schema=None,
        ),
        Route(
            path="/storage/put_file_type",
            method_name="put_file_type",
            request_body_schema=PutFileTypeRequest,
        ),
    ]

    def delete_file_type(self, request_body: ObjectBody, request_context: Dict):
        """
        Delete a file type from the database.

        Keyword arguments:
        request_body -- The request body containing the file type to delete.
        request_context -- The request context.
        """
        logging.info("Executing delete_file_type")

        claims = JWTClaims.from_claims(request_context["request_claims"])

        requestor_is_admin = claims.is_admin

        if not requestor_is_admin:
            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )
        file_types_table_client = FileTypeTableClient()

        f_type = file_types_table_client.get(type_name=request_body["file_type"])

        if not f_type:
            return self.respond(
                status_code=200,
                body={"message": "file not found in system"},
            )

        file_client = FilesTableClient()

        in_use = file_client.check_if_type_in_use(file_type=f_type.type_name)

        if in_use:
            return self.respond(
                status_code=400,
                body={"message": "cannot delete file type that is in use"},
            )

        file_types_table_client.delete(file_type=f_type)

        publish_file_type_update_event(
            file_type=f_type.type_name,
            requestor=claims.entity,
            details={
                "action": "delete",
            },
        )

        return self.respond(
            body={
                "message": f"file type {f_type.type_name} deleted",
            },
            status_code=200,
        )

    def describe_file_type(self, request_body: ObjectBody, request_context: Dict):
        """
        Describe a file type in the database.

        Keyword arguments:
        request_body -- The request body containing the file type to describe.
        request_context -- The request context.
        """
        logging.info("Executing describe_file_type")

        file_types_table_client = FileTypeTableClient()

        f_type = file_types_table_client.get(type_name=request_body["file_type"])

        if not f_type:
            return self.respond(
                status_code=200,
                body={"message": "file type not found in system"},
            )

        return self.respond(
            status_code=200,
            body=f_type.to_dict(json_compatible=True),
        )

    def list_file_types(self, request_body: ObjectBody, request_context: Dict):
        """
        List all file types in the database.

        Keyword arguments:
        request_body -- The request body containing the file types to list.
        request_context -- The request context.
        """
        logging.info("Executing list_file_types")

        file_types_table_client = FileTypeTableClient()

        file_types = file_types_table_client.list()

        return self.respond(
            body={"file_types": [f_type.to_dict(json_compatible=True) for f_type in file_types]},
            status_code=200,
        )

    def put_file_type(self, request_body: ObjectBody, request_context: Dict):
        """
        Put a file type in the database.

        Keyword arguments:
        request_body -- The request body containing the file type to put.
        request_context -- The request context.
        """
        logging.info("Executing put_file_type")

        logging.debug(f"Request Claims: {request_context['request_claims']}")

        claims = JWTClaims.from_claims(request_context["request_claims"])

        requestor_is_admin = claims.is_admin

        logging.debug(f"Requestor admin status: {requestor_is_admin}")

        if not requestor_is_admin:
            logging.debug("Requestor is not admin - insufficient permissions")

            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )

        f_type = FileType(
            type_name=request_body["file_type"],
            content_search_instructions_path=request_body.get("content_search_instructions_path"),
            description=request_body.get("description"),
            is_directory_type=request_body.get("is_directory_type"),
            name_restrictions=request_body["name_restrictions"],
        )

        file_types_table_client = FileTypeTableClient()

        file_types_table_client.put(file_type=f_type)

        publish_file_type_update_event(
            file_type=f_type.type_name,
            requestor=claims.entity,
            details={
                "action": "put",
                "properties": f_type.to_dict(json_compatible=True),
            },
        )

        return self.respond(
            status_code=200,
            body=f_type.to_dict(json_compatible=True),
        )