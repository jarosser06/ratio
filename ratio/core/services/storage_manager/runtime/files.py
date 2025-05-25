"""
Primary File API for the Storage Manager.
"""
import base64
import logging
import os
import re

from datetime import datetime, timedelta, UTC as utc_tz
from typing import Dict, Tuple

import boto3

from da_vinci.core.global_settings import setting_value

from da_vinci.core.immutable_object import ObjectBody

from ratio.core.core_lib.factories.api import ChildAPI, Route
from ratio.core.core_lib.jwt import JWTClaims

from ratio.core.services.storage_manager.tables.files.client import File, FilesTableClient
from ratio.core.services.storage_manager.tables.file_lineage.client import (
    FileLineageEntry,
    FileLineageTableClient,
)
from ratio.core.services.storage_manager.tables.file_types.client import (
    FileTypeTableClient,
)
from ratio.core.services.storage_manager.tables.file_versions.client import (
    FileVersion,
    FileVersionsTableClient,
)

from ratio.core.services.storage_manager.runtime.access import entity_has_access, FilePermission
from ratio.core.services.storage_manager.runtime.data import (
    delete_object_completely,
    delete_version,
    get_version,
    put_version,
)
from ratio.core.services.storage_manager.runtime.events import (
    FileEventType,
    publish_file_update_event,
)

from ratio.core.services.storage_manager.request_definitions import (
    DeleteFileRequest,
    DeleteFileVersionRequest,
    DescribeFileRequest,
    DescribeFileVersionRequest,
    FindFileRequest,
    GetFileVersionRequest,
    ListFilesRequest,
    ListFileVersionsRequest,
    PutFileRequest,
    PutFileVersionRequest,
    PutDirectFileVersionCompleteRequest,
    PutDirectFileVersionStartRequest,
    ValidateFileAccessRequest,
)


def normalize_path(file_path: str) -> Tuple[str, str]:
    """
    Splits a path into its directory and file name components.

    Keyword arguments:
    path_name -- The path to split.

    Returns:
        Tuple of the in the order of (directory, file name)
    """
    logging.debug(f"Normalizing path {file_path}")

    if file_path == "/":
        return "/", "/"

    original_path = file_path.rstrip("/")

    f_path = os.path.dirname(original_path)

    f_name = os.path.basename(original_path)

    logging.debug(f"Normalized path {f_path} and file name {f_name}")

    return f_path, f_name


class FileAPI(ChildAPI):
    routes = [
        Route(
            path="/delete_file",
            method_name="delete_file",
            request_body_schema=DeleteFileRequest,
        ),
        Route(
            path="/delete_file_version",
            method_name="delete_file_version",
            request_body_schema=DeleteFileVersionRequest,
        ),
        Route(
            path="/describe_file",
            method_name="describe_file",
            request_body_schema=DescribeFileRequest,
        ),
        Route(
            path="/describe_file_version",
            method_name="describe_file_version",
            request_body_schema=DescribeFileVersionRequest,
        ),
        Route(
            path="/find_file",
            method_name="find_file",
            request_body_schema=FindFileRequest,
        ),
        Route(
            path="/get_file_version",
            method_name="get_file_version",
            request_body_schema=GetFileVersionRequest,
        ),
        Route(
            path="/get_direct_file_version",
            method_name="get_direct_file_version",
            request_body_schema=GetFileVersionRequest,
        ),
        Route(
            path="/list_files",
            method_name="list_files",
            request_body_schema=ListFilesRequest,
        ),
        Route(
            path="/list_file_versions",
            method_name="list_file_versions",
            request_body_schema=ListFileVersionsRequest,
        ),
        Route(
            path="/put_file",
            method_name="put_file",
            request_body_schema=PutFileRequest,
        ),
        Route(
            path="/put_file_version",
            method_name="put_file_version",
            request_body_schema=PutFileVersionRequest,
        ),
        Route(
            path="/put_direct_file_version_complete",
            method_name="put_direct_file_version_complete",
            request_body_schema=PutDirectFileVersionCompleteRequest,
        ),
        Route(
            path="/put_direct_file_version_start",
            method_name="put_direct_file_version_start",
            request_body_schema=PutDirectFileVersionStartRequest,
        ),
        Route(
            path="/validate_file_access",
            method_name="validate_file_access",
            request_body_schema=ValidateFileAccessRequest,
        )
    ]

    def __init__(self):
        super().__init__()

        self.raw_bucket_name = setting_value(
            namespace="ratio::storage",
            setting_key="raw_bucket",
        )

        self.s3 = boto3.client('s3')

    def _delete_all_file_versions(self, file: File, requestor: str):
        """
        Delete all versions of a file from the system.

        Keyword arguments:
        file -- The file to delete.
        """
        versions_client = FileVersionsTableClient()

        versions = versions_client.get_by_full_path_hash(full_path_hash=file.full_path_hash)

        if not versions:
            return

        delete_object_completely(bucket_name=self.raw_bucket_name, file_name=file.full_path_hash)

        lineage_client = FileLineageTableClient()

        for version in versions:
            lineage_entries = lineage_client.get_all_matching_single_key(lineage_file_id=version.file_id)

            if lineage_entries:
                logging.debug(f"Deleting lineage entries for version {version.version_id}")

                for lineage in lineage_entries:
                    lineage_client.delete(file_lineage_entry=lineage)

            # Delete the version from the database
            versions_client.delete(file_version=version)

            # Send the file version delete event to the event bus
            publish_file_update_event(
                file=file,
                file_event_type=FileEventType.VERSION_DELETED,
                requestor=requestor,
                details={
                    "version_id": version.version_id,
                },
            )

    def _delete_file(self, file: File, files_client: FilesTableClient, request_context: Dict, force: bool = False,
                     recursive: bool = False) -> Dict:
        """
        Private method to delete a file from the system.

        Keyword arguments:
        claims -- The JWT claims of the requestor.
        file -- The file to delete.
        files_client -- The files client to use for deleting the file.
        force -- Whether to force delete the file.
        recurse -- Whether to delete subdirectories recursively.
        """
        logging.debug(f"Deleting file {file.full_path}")
        # Check write access to the PARENT directory (not the file itself)
        parent_path = file.file_path

        parent_name = os.path.basename(parent_path)

        parent_dir = os.path.dirname(parent_path)
        
        # Handle root directory special case
        if parent_dir == "/" and parent_name == "":
            parent_name = "/"
        
        parent_path_hash = File.generate_hash(parent_dir)

        parent_name_hash = File.generate_hash(parent_name)

        parent_file = files_client.get(path_hash=parent_path_hash, name_hash=parent_name_hash)
    
        if parent_file and not entity_has_access(file=parent_file, request_context=request_context, requested_permission_names=["write"]):
            logging.error(f"Requestor does not have write access to parent directory of {file.full_path}")
            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions on parent directory"},
            )

        # Handle directory deletion
        if file.is_directory:
            directory_check_path_hash = File.generate_hash(file.full_path)

            logging.debug(f"File {file.full_path} is a directory ... checking for children. Searching with {directory_check_path_hash}")

            # Check for children
            children, _ = files_client.list(path_hash=directory_check_path_hash)

            if children and not recursive:
                logging.debug(f"Directory {file.full_path} has children and recursive flag not set")

                return self.respond(
                    body={"message": "cannot delete non-empty directory without recurse flag"},
                    status_code=400,
                )

            logging.debug(f"Directory {file.full_path} has children and recursive flag set: {children}")

            # For recursive deletion, we need write access to THIS directory to delete its children
            if not entity_has_access(file=file, request_context=request_context, requested_permission_names=["write"]):
                logging.error(f"Requestor does not have write access to directory {file.full_path} to delete its children")

                return self.respond(
                    status_code=403,
                    body={"message": f"insufficient access to delete children of {file.full_path}"},
                )

            logging.debug(f"Deleting children of directory {file.full_path}")

            # Recursively delete all children
            for child in children:
                logging.debug(f"Deleting child {child.full_path} of directory {file.full_path}")

                delete_result = self._delete_file(
                    file=child,
                    files_client=files_client,
                    request_context=request_context,
                    force=force,
                    recursive=recursive,
                )

                if delete_result["statusCode"] != 200:
                    logging.debug(f"Failed to delete child {child.full_path} of directory {file.full_path}")

                    return delete_result

        else:
            logging.info(f"File {file.full_path} is not a directory ... checking for lineage")

            # Check lineage
            lineage_client = FileLineageTableClient()

            all_source_lineage = lineage_client.get_all_by_full_path_hash(
                source_full_path_hash=file.full_path_hash,
            )

            if all_source_lineage:
                if force:
                    for source_lineage in all_source_lineage:
                        lineage_client.delete(file_lineage_entry=source_lineage)

                else:
                    return self.respond(
                        body={"message": "unable to delete a lineage source file"},
                        status_code=400,
                    )

        claims = JWTClaims.from_claims(claims=request_context["request_claims"])

        # Delete all file versions
        self._delete_all_file_versions(file=file, requestor=claims.entity)

        # Delete the file from the database
        files_client.delete(file=file)

        # Send the file delete event to the event bus
        publish_file_update_event(
            file=file,
            file_event_type=FileEventType.DELETED,
            requestor=claims.entity,
        )

        # Publish the parent directory update event
        publish_file_update_event(
            file=parent_file,
            file_event_type=FileEventType.UPDATED,
            requestor=claims.entity,
            details={
                "file": file.to_dict(exclude_attribute_names=["full_path_hash"], json_compatible=True),
                "file_event_type": FileEventType.DELETED,
            }
        )

        return self.respond(
            body={
                "file_name": file.file_name,
                "file_path": file.file_path,
            },
            status_code=200,
        )

    def delete_file(self, request_body: ObjectBody, request_context: Dict):
        """
        Delete a file from the system.

        Keyword arguments:
        request_body -- The request body containing the file to delete.
        request_context -- The request context.
        """
        f_path, f_name = normalize_path(request_body["file_path"])

        if f_path == "/" and f_name == "/":
            return self.respond(
                status_code=400,
                body={"message": "lol no"},
            )

        file_name_hash = File.generate_hash(f_name)

        file_path_hash = File.generate_hash(f_path)

        files_client = FilesTableClient()

        logging.debug(f"Looking up file {f_name} at path {f_path}")

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        if not file:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        return self._delete_file(
            file=file,
            files_client=files_client,
            force=request_body.get("force", default_return=False),
            request_context=request_context,
            recursive=request_body.get("recursive", default_return=False),
        )

    def delete_file_version(self, request_body: ObjectBody, request_context: Dict):
        """
        Delete a file version from the system.

        Keyword arguments:
        request_body -- The request body containing the file version to delete.
        request_context -- The request context.
        """
        f_path, f_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(f_name)

        file_path_hash = File.generate_hash(f_path)

        files_client = FilesTableClient()

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        if not file:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        if not entity_has_access(file=file, request_context=request_context, requested_permission_names=["write"]):
            logging.error(f"Requestor does not have write access to file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )

        version_id = request_body.get("version_id", default_return=file.latest_version_id)

        versions_client = FileVersionsTableClient()

        version = versions_client.get(full_path_hash=file.full_path_hash, version_id=version_id)

        if not version:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        # Validate the file version is not in lineage use
        lineage_client = FileLineageTableClient()

        all_source_lineage = lineage_client.get_all_by_full_path_hash(
            source_full_path_hash=version.full_path_hash,
        )

        if all_source_lineage:
            if request_body.get("force", default_return=False):
                return self.respond(
                    body={"message": "unable to delete a file version that is a lineage source"},
                    status_code=400,
                )

            else:
                for source_lineage in all_source_lineage:
                    lineage_client.delete(file_lineage_entry=source_lineage)

        # Delete all lineage entries, freeing up the sources since their lineage is being deleted
        all_lineage = lineage_client.get_all_matching_single_key(lineage_file_id=version.file_id)

        if all_lineage:
            for lineage in all_lineage:
                lineage_client.delete(file_lineage_entry=lineage)

        # If the version is the latest version, update the file to remove the version
        if version.version_id == file.latest_version_id:
            file.latest_version_id = version.previous_version_id

            file.last_updated_on = datetime.now(tz=utc_tz)

            files_client.put(file=file)

        else:
            # Get the previous version
            previous_version = versions_client.get(
                full_path_hash=file.full_path_hash,
                version_id=version.previous_version_id,
            )

            if not previous_version:
                return self.respond(
                    status_code=404,
                    body={"message": "unable to locate previous version"},
                )

            # Get the next version
            next_version = versions_client.get(
                full_path_hash=file.full_path_hash,
                version_id=version.next_version_id,
            )

            if not next_version:
                return self.respond(
                    status_code=404,
                    body={"message": "unable to locate next version"},
                )

            # Update the previous version to point to the next version
            previous_version.next_version_id = next_version.version_id

            versions_client.put(file_version=previous_version)

            # Update the next version to point to the previous version
            next_version.previous_version_id = previous_version.version_id

            versions_client.put(file_version=next_version)

        # Delete the version from S3
        delete_version(
            bucket_name=self.raw_bucket_name,
            file_name=file.full_path_hash,
            version_id=version.version_id,
        )

        # Delete the file version from the database
        versions_client.delete(file_version=version)

        claims = JWTClaims.from_claims(claims=request_context["request_claims"])

        # Send the file version delete event to the event bus
        publish_file_update_event(
            file=file,
            file_event_type=FileEventType.VERSION_DELETED,
            requestor=claims.entity,
            details={
                "version_id": version.version_id,
            },
        )

        # Send update for parent directory
        parent_dir = os.path.dirname(file.file_path)

        parent_file_name = os.path.basename(parent_dir)

        if parent_file_name == "" and parent_dir == "/":
            parent_file_name = "/"

        parent_file_name_hash = File.generate_hash(parent_file_name)

        parent_file_path_hash = File.generate_hash(parent_dir)

        parent_file = files_client.get(path_hash=parent_file_path_hash, name_hash=parent_file_name_hash)

        if not parent_file:
            raise Exception(f"Unable to locate parent file {parent_file_name} at path {parent_dir}")

        files_client.put(file=parent_file)

        publish_file_update_event(
            file=parent_file,
            file_event_type=FileEventType.UPDATED,
            requestor=claims.entity,
            details={
                "file": file.to_dict(exclude_attribute_names=["full_path_hash"], json_compatible=True),
                "file_event_type": FileEventType.VERSION_DELETED,
            },
        )

        return self.respond(
            status_code=200,
            body={
                "file_name": file.file_name,
                "file_path": file.file_path,
                "version_id": version.version_id,
            },
        )

    def describe_file(self, request_body: ObjectBody, request_context: Dict):
        """
        Describe a file in the system.

        Keyword arguments:
        request_body -- The request body containing the file to describe.
        request_context -- The request context.
        """
        f_path, f_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(f_name)

        file_path_hash = File.generate_hash(f_path)

        files_client = FilesTableClient()

        logging.debug(f"Looking up file {f_name} at path {f_path}")

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        if not file:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        if not entity_has_access(file=file, request_context=request_context, requested_permission_names=["read"]):
            logging.error(f"Requestor does not have read access to file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        files_client.set_last_accessed(
            name_hash=file.name_hash,
            path_hash=file.path_hash,
            last_accessed_on=datetime.now(tz=utc_tz)
        )

        response = file.to_dict(
            exclude_attribute_names=[
                "name_hash",
                "path_hash",
                "permissions_mask_everyone",
                "permissions_mask_group",
                "permissions_mask_owner"
            ],
            json_compatible=True,
        )

        response["file_path"] = os.path.join(file.file_path, file.file_name)

        return self.respond(
            body=response,
            status_code=200,
        )

    def describe_file_version(self, request_body: ObjectBody, request_context: Dict):
        """
        Describe a file version in the system.

        Keyword arguments:
        request_body -- The request body containing the file version to describe.
        request_context -- The request context.
        """
        f_path, f_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(f_name)

        file_path_hash = File.generate_hash(f_path)

        files_client = FilesTableClient()

        logging.debug(f"Looking up file {f_name} at path {f_path}")

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        if not file:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        if not entity_has_access(file=file, request_context=request_context, requested_permission_names=["read"]):
            logging.error(f"Requestor does not have read access to file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        files_client.set_last_accessed(
            name_hash=file.name_hash,
            path_hash=file.path_hash,
            last_accessed_on=datetime.now(tz=utc_tz)
        )

        version_id = request_body.get("version_id", default_return=file.latest_version_id)

        if not version_id:
            return self.respond(
                status_code=404,
                body={"message": "no available version to get"},
            )

        versions_client = FileVersionsTableClient()

        version = versions_client.get(full_path_hash=file.full_path_hash, version_id=version_id)

        if not version:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        return self.respond(
            status_code=200,
            body=version.to_dict(
                exclude_attribute_names=[
                    "full_path_hash",
                ],
                json_compatible=True,
            ),
        )

    def find_file(self, request_body: ObjectBody, request_context: Dict):
        """
        Find a file in the system.

        Keyword arguments:
        request_body -- The request body containing the file to find.
        request_context -- The request context.
        """
        return self.respond(
            status_code=500,
            body={"message": "not implemented"},
        )

    def get_file_version_location(self, request_body: ObjectBody, request_context: Dict):
        """
        Returns the location of the file version S3 object.
        """

    def get_file_version(self, request_body: ObjectBody, request_context: Dict):
        """
        Gets the file version data from the system.

        Keyword arguments:
        request_body -- The request body containing the data to get.
        request_context -- The request context.
        """
        f_path, f_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(f_name)

        file_path_hash = File.generate_hash(f_path)

        files_client = FilesTableClient()

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        logging.debug(f"Looking up file {f_name} at path {f_path}")

        if not file:
            logging.error(f"Unable to locate file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        if not entity_has_access(file=file, request_context=request_context, requested_permission_names=["read"]):
            logging.error(f"Requestor does not have read access to file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )

        # Update file last_accessed_on
        files_client.set_last_accessed(
            name_hash=file.name_hash,
            path_hash=file.path_hash,
            last_accessed_on=datetime.now(tz=utc_tz),
        )

        version_id = request_body.get("version_id", default_return=file.latest_version_id)

        if not version_id:
            return self.respond(
                status_code=400,
                body={"message": "no available version to get"},
            )

        data = get_version(
            bucket_name=self.raw_bucket_name,
            file_name=file.full_path_hash,
            version_id=version_id,
        )

        if not data:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        base_64_encoded = False

        try:
            # Try to decode as UTF-8 text
            text_data = data.decode('utf-8')

            response_data = text_data

        except UnicodeDecodeError:
            # If it fails, it's binary - base64 encode it
            response_data = base64.b64encode(data).decode('utf-8')

            base_64_encoded = True

        return self.respond(
            status_code=200,
            body={
                "data": response_data,
                "details": {
                    "base_64_encoded": base_64_encoded,
                    "path": file.file_path,
                    "file_name": file.file_name,
                    "version_id": version_id,
                }
            },
        )

    def get_direct_file_version(self, request_body: ObjectBody, request_context: Dict):
        """
        Returns a pre-signed URL for the specific file version.
        """
        f_path, f_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(f_name)

        file_path_hash = File.generate_hash(f_path)

        files_client = FilesTableClient()

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        logging.debug(f"Looking up file {f_name} at path {f_path}")

        if not file:
            logging.error(f"Unable to locate file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        if not entity_has_access(file=file, request_context=request_context, requested_permission_names=["read"]):
            logging.error(f"Requestor does not have read access to file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )

        # Update file last_accessed_on
        files_client.set_last_accessed(
            name_hash=file.name_hash,
            path_hash=file.path_hash,
            last_accessed_on=datetime.now(tz=utc_tz),
        )

        version_id = request_body.get("version_id", default_return=file.latest_version_id)

        if not version_id:
            return self.respond(
                status_code=400,
                body={"message": "no available version to get"},
            )

        expires_in_seconds = 3600

        expires_at  = datetime.now(tz=utc_tz) + timedelta(seconds=expires_in_seconds)

        try:
            presigned_url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.raw_bucket_name,
                    'Key': file.full_path_hash,
                    'VersionId': version_id
                },
                ExpiresIn=expires_in_seconds,  # 1 hour
                HttpMethod='GET'
            )

        except Exception as e:
            return self.respond(status_code=500, body={"message": f"Error generating download URL: {str(e)}"})

        return self.respond(
            status_code=200,
            body={
                "download_url": presigned_url,
                "expires_at": expires_at.isoformat(),
                "file_path": file.file_path,
                "version_id": version_id,
            }
        )

    def list_files(self, request_body: ObjectBody, request_context: Dict):
        """
        List files in the system.

        Keyword arguments:
        request_body -- The request body containing the file to list.
        request_context -- The request context.
        """
        logging.debug(f"List files request body: {request_body}")

        files_client = FilesTableClient()

        # Attempt stripping any trailing slashes from the file path if exists
        root_directory, root_filename = normalize_path(request_body["file_path"])

        logging.debug(f"Root directory: {root_directory} Root filename: {root_filename}")

        root_directory_hash = File.generate_hash(root_directory)

        root_filename_hash = File.generate_hash(root_filename)

        logging.debug(f"Root directory hash: {root_directory_hash} Root filename hash: {root_filename_hash}")

        root_file = files_client.get(path_hash=root_directory_hash, name_hash=root_filename_hash)

        if not root_file:
            return self.respond(
                status_code=404,
                body={"message": "parent directory not found"},
            )

        if not entity_has_access(file=root_file, request_context=request_context, requested_permission_names=["execute", "read"]):
            logging.error(f"Requestor does not have read access to file {root_filename_hash} at path {root_directory_hash}")

            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )

        if not root_file.is_directory:
            return self.respond(
                status_code=400,
                body={"message": "file path is not a directory"},
            )

        file_path_hash = File.generate_hash(request_body["file_path"])

        # Just get the immediate children
        resulting_list, _ = files_client.list(
            path_hash=file_path_hash,
        )

        results = []

        if resulting_list:
            for file in resulting_list:
                    results.append(
                        {
                            "directory": file.is_directory,
                            "group": file.group,
                            "file_path": file.full_path,
                            "file_type": file.file_type,
                            "owner": file.owner,
                            "permissions": file.permissions,
                        }
                    )

        return self.respond(
            status_code=200,
            body={
                "files": results,
            },
        )

    def list_file_versions(self, request_body: ObjectBody, request_context: Dict):
        """
        List file versions in the system.

        Keyword arguments:
        request_body -- The request body containing the file to list.
        request_context -- The request context.
        """
        f_path, f_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(f_name)

        file_path_hash = File.generate_hash(f_path)

        files_client = FilesTableClient()

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        if not file:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        if not entity_has_access(file=file, request_context=request_context, requested_permission_names=["read"]):
            logging.error(f"Requestor does not have read access to file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        versions_client = FileVersionsTableClient()

        versions = versions_client.get_by_full_path_hash(full_path_hash=file.full_path_hash)

        results = []

        exclude_attr_names = [
            "full_path_hash",
            "metadata",
        ]

        if versions:
            results = [version.to_dict(exclude_attribute_names=exclude_attr_names, json_compatible=True) for version in versions]

        return self.respond(
            status_code=200,
            body={
                "versions": results,
            },
        )

    def put_file(self, request_body: ObjectBody, request_context: Dict):
        """
        Put a file in the system.

        Keyword arguments:
        request_body -- The request body containing the file to put.
        request_context -- The request context.
        """
        logging.debug(f"Put file request body: {request_body.to_dict()}")

        claims = JWTClaims.from_claims(request_context["request_claims"])

        path_name, file_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(file_name)

        path_name_hash = File.generate_hash(path_name)

        files_client = FilesTableClient()

        file = files_client.get(path_hash=path_name_hash, name_hash=file_name_hash)

        # Validate the file type
        file_type_client = FileTypeTableClient()

        file_type = file_type_client.get(type_name=request_body["file_type"])

        if not file_type:
            return self.respond(
                status_code=400,
                body={"message": "invalid file type"},
            )

        existing_file = False

        if file:
            existing_file = True

            if not entity_has_access(file=file, request_context=request_context, requested_permission_names=["write"]):
                logging.error(f"Requestor does not have write access to file {file_name_hash} at path {path_name_hash}")

                return self.respond(
                    status_code=403,
                    body={"message": "insufficient permissions"},
                )

            metadata = request_body.get("metadata")

            if isinstance(metadata, ObjectBody):
                logging.debug("Converting metadata from object body to dict")

                metadata = metadata.to_dict()

            now = datetime.now(tz=utc_tz)

            updates = {
                "last_accessed_on": now,
                "last_updated_on": now,
            }

            if metadata:
                updates["metadata"] = metadata

            file.update(**updates)

            files_client.put(file=file)

            publish_file_update_event(
                file=file,
                file_event_type=FileEventType.UPDATED,
                requestor=claims.entity,
            )

        else:
            # Handle root separately
            logging.debug(f"File {request_body["file_path"]} does not exist ... creating")

            logging.debug(f"Checking for parent directory access {path_name}")

            root_directory, root_filename = normalize_path(path_name)

            logging.debug(f"Root directory is {root_directory} for file {path_name}")

            root_directory_hash = File.generate_hash(root_directory)

            root_filename_hash = File.generate_hash(root_filename)

            logging.debug(f"Root directory hash: {root_directory_hash} Root filename hash: {root_filename_hash}")

            root_file = files_client.get(path_hash=root_directory_hash, name_hash=root_filename_hash)

            if not root_file:
                logging.debug(f"Unable to locate parent directory {root_directory_hash} for file {file_name_hash}")

                return self.respond(
                    status_code=404,
                    body={"message": "parent directory not found"},
                )

            if not entity_has_access(file=root_file, request_context=request_context, requested_permission_names=["write"]):
                logging.error(f"Requestor does not have write access to file {root_filename_hash} at path {root_directory_hash}")

                return self.respond(
                    status_code=403,
                    body={"message": "insufficient permissions"},
                )

            logging.debug(f"Claims: {claims.to_dict()}")

            owner = request_body.get("owner", default_return=claims.entity)

            group = request_body.get("group", default_return=claims.primary_group)

            if file_type.name_restrictions:
                name_restrictions = re.compile(file_type.name_restrictions)

                if not name_restrictions.match(file_name):
                    return self.respond(
                        status_code=400,
                        body={"message": f"file name does not match the restrictions: {file_type.name_restrictions}"},
                    )

            file = File(
                group=group,
                file_name=file_name,
                file_path=path_name,
                file_type=request_body["file_type"],
                is_directory=file_type.is_directory_type,
                name_hash=file_name_hash,
                owner=owner,
                path_hash=path_name_hash,
                permissions=request_body["permissions"],
            )

            files_client.put(file=file)

            if existing_file:
                publish_file_update_event(
                    file=path_name,
                    file_event_type=FileEventType.UPDATED,
                    requestor=claims.entity,
                )

                publish_file_update_event(
                    file=root_file,
                    file_event_type=FileEventType.UPDATED,
                    requestor=claims.entity,
                    details={
                        "file": file.to_dict(exclude_attribute_names=["full_path_hash"], json_compatible=True),
                        "file_event_type": FileEventType.CREATED,
                    }
                )

            else:
                publish_file_update_event(
                    file=file,
                    file_event_type=FileEventType.CREATED,
                    requestor=claims.entity,
                )

                publish_file_update_event(
                    file=root_file,
                    file_event_type=FileEventType.UPDATED,
                    requestor=claims.entity,
                    details={
                        "file": file.to_dict(exclude_attribute_names=["full_path_hash"], json_compatible=True),
                        "file_event_type": FileEventType.CREATED,
                    }
                )

        file_response = file.to_dict(
            exclude_attribute_names=[
                "path_hash",
                "name_hash",
                "permissions_mask_everyone",
                "permissions_mask_group",
                "permissions_mask_owner"
            ],
            json_compatible=True,
        )

        file_response["file_path"] = os.path.join(file.file_path, file.file_name)

        return self.respond(
            body=file_response,
            status_code=200,
        )

    def put_file_version(self, request_body: ObjectBody, request_context: Dict):
        """
        Put a version of the file in the system.

        Keyword arguments:
        request_body -- The request body containing the file version to put.
        request_context -- The request context.
        """
        logging.debug(f"Put file version request body: {request_body.to_dict()}")

        file_path, file_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(file_name)

        file_path_hash = File.generate_hash(file_path)

        files_client = FilesTableClient()

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        if not file:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        if not entity_has_access(file=file, request_context=request_context, requested_permission_names=["read", "write"]):
            logging.error(f"Requestor does not have write access to file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )

        if file.is_directory:
            return self.respond(
                status_code=400,
                body={"message": "cannot store data as a directory file"},
            )

        # Validate data is correct format
        if not isinstance(request_body["data"], (bytes, str)):
            logging.error(f"Invalid data type: {type(request_body['data'])}")

            return self.respond(
                status_code=400,
                body={"message": f"data must be bytes or string, not {type(request_body['data'])}"},
            )

        base_64_encoded = request_body.get("base_64_encoded", default_return=False)

        logging.debug(f"Base 64 encoded attribute value: {base_64_encoded}")

        data = request_body["data"]

        if base_64_encoded:
            logging.debug("Base 64 encoded data ... decoding")

            if isinstance(request_body["data"], str):
                data = base64.b64decode(request_body["data"])

            else:
                return self.respond(
                    status_code=400,
                    body={"message": "base_64_encoded is true but data is not a string"},
                )

        version_id = put_version(
            data=data,
            bucket_name=self.raw_bucket_name,
            file_name=file.full_path_hash,
        )

        claims = JWTClaims.from_claims(request_context["request_claims"])

        metadata = request_body.get("metadata")

        # B/c ObjectBody consumes all
        if isinstance(metadata, ObjectBody):
            metadata = metadata.to_dict()

        # Create the file version
        file_version = FileVersion(
            version_id=version_id,
            full_path_hash=file.full_path_hash,
            file_name=file.file_name,
            file_path=file.file_path,
            metadata=metadata,
            origin=request_body["origin"],
            originator_id=claims.entity,
            previous_version_id=file.latest_version_id,
            size=len(data),
        )

        previous_version_id = file.latest_version_id

        file_versions_client = FileVersionsTableClient()

        file_versions_client.put(file_version=file_version)

        if previous_version_id:
            # Update the previous version to point to the new version
            previous_version = file_versions_client.get(
                full_path_hash=file.full_path_hash,
                version_id=previous_version_id,
            )

            if previous_version:
                previous_version.next_version_id = file_version.version_id

                file_versions_client.put(file_version=previous_version)

        logging.debug(f"File version {file_version.version_id} created for file {file_name} at path {file_path}")

        # Update the file with the new version
        file.latest_version_id = file_version.version_id

        file.last_accessed_on = datetime.now(tz=utc_tz)

        file.last_updated_on = datetime.now(tz=utc_tz)

        files_client.put(file=file)

        logging.debug(f"File {file.file_name} at path {file.file_path} updated with new version {file.latest_version_id}")

        # Create the lineage entry
        file_lineage_client = FileLineageTableClient()

        # Expects the source files to be a list of dictionaries
        source_files = request_body.get("source_files", default_return=[])

        for source_file in source_files:
            logging.debug(f"Adding source file {source_file} for file {file.file_name} at path {file.file_path}")

            source_file_path = source_file["source_file_path"]

            source_file_version = source_file["source_file_version"]

            source_fname = os.path.basename(source_file_path)

            source_fpath = os.path.dirname(source_file_path)

            source_fname_hash = File.generate_hash(source_fname)

            source_fpath_hash = File.generate_hash(source_fpath)

            # Validate existence of source file
            source_file_obj = file_versions_client.get(
                full_path_hash=File.generate_full_path_hash(
                    name_hash=source_fname_hash,
                    path_hash=source_fpath_hash,
                ),
                version_id=source_file_version,
            )

            if not source_file_obj:
                return self.respond(
                    status_code=404,
                    body={"message": f"source file {source_file_path}:{source_file_version} not found"},
                )

            file_lineage_entry = FileLineageEntry(
                lineage_file_path=os.path.join(file.file_path, file.file_name),
                lineage_file_version=file_version.version_id,
                lineage_file_id=file_version.file_id,
                source_file_path=source_file_path,
                source_file_version=source_file_version,
                source_file_id=source_file_obj.file_id,
                source_full_path_hash=file.full_path_hash,
            )

            file_lineage_client.put(file_lineage_entry=file_lineage_entry)

        # Publish the file version creation event
        publish_file_update_event(
            file=file,
            file_event_type=FileEventType.VERSION_CREATED,
            requestor=claims.entity,
            details={
                "version_id": file_version.version_id,
            },
        )

        # Publish for the parent directory if this is not a directory update
        parent_dir = os.path.dirname(file.file_path)

        parent_file_name = os.path.basename(parent_dir)

        if parent_file_name == "" and parent_dir == "/":
            parent_file_name = "/"

        parent_name_hash = File.generate_hash(parent_file_name)

        parent_path_hash = File.generate_hash(parent_dir)

        parent_file = files_client.get(path_hash=parent_path_hash, name_hash=parent_name_hash)

        if parent_file:
            publish_file_update_event(
                file=parent_file,
                file_event_type=FileEventType.UPDATED,
                requestor=claims.entity,
                details={
                    "file": file.to_dict(exclude_attribute_names=["full_path_hash"], json_compatible=True),
                    "file_event_type": FileEventType.VERSION_CREATED,
                }
            )

        return self.respond(
            body=file_version.to_dict(json_compatible=True),
            status_code=201,
        )

    def put_direct_file_version_start(self, request_body: ObjectBody, request_context: Dict):
        """
        Starts a direct file version upload.
        """
        logging.debug(f"Put direct file version start request body: {request_body.to_dict()}")

        file_path, file_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(file_name)

        file_path_hash = File.generate_hash(file_path)

        files_client = FilesTableClient()

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        if not file:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        if not entity_has_access(file=file, request_context=request_context, requested_permission_names=["read", "write"]):
            logging.error(f"Requestor does not have write access to file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )

        if file.is_directory:
            return self.respond(
                status_code=400,
                body={"message": "cannot store data as a directory file"},
            )

        expires_in_seconds = 3600

        expires_at = datetime.now(tz=utc_tz) + timedelta(seconds=expires_in_seconds)

        try:
            presigned_url = self.s3.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.raw_bucket_name,
                    'Key': file.full_path_hash,  # S3 will generate version_id
                },
                ExpiresIn=expires_in_seconds,
                HttpMethod='PUT'
            )

        except Exception as e:
            return self.respond(status_code=500, body={"message": f"Error generating upload URL: {str(e)}"})

        return self.respond(
            status_code=200,
            body={
                "upload_url": presigned_url,
                "expires_at": expires_at.isoformat(),
                "file_path": request_body["file_path"]
            }
        )

    def put_direct_file_version_complete(self, request_body: ObjectBody, request_context: Dict):
        """
        Completion signal that lets the system know the direct file version upload has been completed.
        """
        logging.debug(f"Put direct file version completion request body: {request_body.to_dict()}")

        file_path, file_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(file_name)

        file_path_hash = File.generate_hash(file_path)

        files_client = FilesTableClient()

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        if not file:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        if not entity_has_access(file=file, request_context=request_context, requested_permission_names=["read", "write"]):
            logging.error(f"Requestor does not have write access to file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )

        try:
            s3_versions_resp = self.s3.list_object_versions(
                Bucket=self.raw_bucket_name,
                Prefix=file.full_path_hash,
                MaxKeys=1000
            )

            s3_versions = [v['VersionId'] for v in s3_versions_resp.get('Versions', []) 
                        if v['Key'] == file.full_path_hash]

        except Exception as e:
            return self.respond(status_code=500, body={"message": f"Error checking S3 versions: {str(e)}"})

        versions_client = FileVersionsTableClient()

        existing_versions = versions_client.get_by_full_path_hash(full_path_hash=file.full_path_hash)

        existing_version_ids = {v.version_id for v in existing_versions} if existing_versions else set()

        missing_versions = list(set(s3_versions) - set(existing_version_ids))

        if not missing_versions:
            return self.respond(status_code=400, body={"message": "no new versions found"})

        if len(missing_versions) > 1:
            raise Exception(f"More than one unrecorded version found for file {file_name} at path {file_path}")

        newest_version_id = missing_versions[0]

        try:
            head_resp = self.s3.head_object(
                Bucket=self.raw_bucket_name,
                Key=file.full_path_hash,
                VersionId=newest_version_id
            )

            file_size = head_resp['ContentLength']

        except Exception as e:
            return self.respond(status_code=500, body={"message": f"Error getting file info: {str(e)}"})

        claims = JWTClaims.from_claims(request_context["request_claims"])

        metadata = request_body.get("metadata", default_return={})

        if isinstance(metadata, ObjectBody):
            logging.debug("Converting metadata from object body to dict")

            metadata = metadata.to_dict()

        file_version = FileVersion(
            version_id=newest_version_id,
            full_path_hash=file.full_path_hash,
            file_name=file.file_name,
            file_path=file.file_path,
            size=file_size,  # Add this field to track size
            metadata=metadata,
            originator_id=claims.entity,
            origin=request_body.get("origin", default_return="internal"),
            previous_version_id=file.latest_version_id,
        )

        versions_client.put(file_version=file_version)

        # Update previous version linkage
        if file.latest_version_id:
            previous_version = versions_client.get(
                full_path_hash=file.full_path_hash,
                version_id=file.latest_version_id,
            )

            if previous_version:
                previous_version.next_version_id = newest_version_id

                versions_client.put(file_version=previous_version)

        # Update file with new latest version
        file.latest_version_id = newest_version_id

        file.last_updated_on = datetime.now(tz=utc_tz)

        files_client.put(file=file)

        # Publish events
        publish_file_update_event(
            file=file,
            file_event_type=FileEventType.VERSION_CREATED,
            requestor=claims.entity,
            details={"version_id": newest_version_id},
        )
        
        return self.respond(
            status_code=201,
            body=file_version.to_dict(json_compatible=True),
        )

    def validate_file_access(self, request_body: ObjectBody, request_context: Dict):
        """
        Validate the file access for the requestor.
        Keyword arguments:
        request_body -- The request body containing the file to validate.
        request_context -- The request context.
        """
        file_path, file_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(file_name)

        file_path_hash = File.generate_hash(file_path)

        files_client = FilesTableClient()

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        if not file:
            return self.respond(
                status_code=404,
                body={"message": "file not found"},
            )

        requested_permission_names = request_body["requested_permission_names"]

        supported_permissions = [member.value for member in FilePermission.__members__.values()]

        for perm_name in requested_permission_names:
            if perm_name not in supported_permissions:

                return self.respond(
                    status_code=400,
                    body={"message": f"invalid permission name: {perm_name}"},
                )

        has_access = entity_has_access(file=file, request_context=request_context, requested_permission_names=requested_permission_names)

        claims = JWTClaims.from_claims(request_context["request_claims"])

        logging.debug(f"Entity {claims.entity} access to {file.full_path}: {has_access}")

        return self.respond(
            status_code=200,
            body={
                "entity_has_access": has_access,
                "file_path": file.full_path,
                "requested_permissions": requested_permission_names,
            },
        )