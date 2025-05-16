"""
Actions specific File API calls like changes to file permissions, copying files, and moving files.
"""
import logging
import os

from datetime import datetime, UTC as utc_tz
from typing import Dict, List, Union, Tuple

from da_vinci.core.global_settings import setting_value
from da_vinci.core.immutable_object import ObjectBody

from ratio.core.services.storage_manager.runtime.access import entity_has_access

from ratio.core.core_lib.factories.api import ChildAPI, Route
from ratio.core.core_lib.jwt import JWTClaims

from ratio.core.services.storage_manager.tables.file_versions.client import (
    FileVersion,
    FileVersionsTableClient,
)
from ratio.core.services.storage_manager.tables.files.client import (
    File,
    FilesTableClient,
)

from ratio.core.services.storage_manager.runtime.data import copy_version
from ratio.core.services.storage_manager.runtime.events import (
    FileEventType,
    publish_file_update_event,
)
from ratio.core.services.storage_manager.runtime.files import (
    normalize_path,
)
from ratio.core.services.storage_manager.request_definitions import (
    ChangeFilePermissionsRequest,
    CopyFileRequest,
    MoveFileRequest,
)


class ActionsAPI(ChildAPI):
    routes = [
        Route(
            path="/change_file_permissions",
            method_name="change_file_permissions",
            request_body_schema=ChangeFilePermissionsRequest,
        ),
        Route(
            path="/copy_file",
            method_name="copy_file",
            request_body_schema=CopyFileRequest,
        ),
        Route(
            path="/move_file",
            method_name="move_file",
            request_body_schema=MoveFileRequest,
        ),
    ]

    def change_file_permissions(self, request_body: ObjectBody, request_context: Dict):
        """
        Change the permissions of a file.

        Keyword arguments:
        request_body -- The request body containing the file and new permissions.
        request_context -- The context of the request, including claims and other metadata.
        """
        files_client = FilesTableClient()

        f_path, f_name = normalize_path(request_body["file_path"])

        file_name_hash = File.generate_hash(f_name)

        file_path_hash = File.generate_hash(f_path)

        logging.debug(f"Looking for file {file_name_hash} at path {file_path_hash}")

        file = files_client.get(path_hash=file_path_hash, name_hash=file_name_hash)

        if not file:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        if not entity_has_access(file=file, request_context=request_context, requires_owner=True):
            logging.error(f"Requestor does not have write access to file {file_name_hash} at path {file_path_hash}")

            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )

        now = datetime.now(tz=utc_tz)

        updates = {
            "last_accessed_on": now,
            "last_updated_on": now,
        }

        for req_name in ["permissions", "group", "owner"]:
            attr_val = request_body.get(req_name)

            if attr_val:
                updates[req_name] = attr_val

        updates = file.update(**updates)

        files_client.put(file=file)

        claims = JWTClaims.from_claims(request_context["request_claims"])

        publish_file_update_event(
            file=file,
            file_event_type=FileEventType.UPDATED,
            requestor=claims.entity,
            details={
                "updated_attributes": updates,
            },
        )

        return self.respond(
            status_code=200,
            body={
                "file_path": os.path.join(file.file_path, file.file_name),
                "updated_attributes": updates,
            },
        )

    def _copy_file_version_data(self, bucket_name: str, existing_file_version: FileVersion, new_file: File) -> FileVersion:
        """
        Copy the data from the existing file version to a version of the new file.

        Keyword arguments:
        bucket_name -- The name of the bucket to copy the file to.
        existing_file_version -- The existing file version to copy data from.
        new_file -- The new file to copy data to.
        """
        version_id = copy_version(
            bucket_name=bucket_name,
            dest_file=new_file.full_path_hash,
            source_file=existing_file_version.full_path_hash,
            version_id=existing_file_version.version_id,
        )

        # Create a new version of the file
        file_version = FileVersion(
            version_id=version_id,
            full_path_hash=new_file.full_path_hash,
            file_name=new_file.file_name,
            file_path=new_file.file_path,
            metadata=existing_file_version.metadata,
            origin="internal",
            originator_id=new_file.owner,
        )

        # Store the new version of the file
        file_versions_client = FileVersionsTableClient()

        file_versions_client.put(file_version=file_version)

        return file_version

    def _validate_copy_destination(self, destination_file_path: str, request_context: Dict) -> Union[Dict, None]:
        """
        Validate the destination for the copied file.

        Keyword arguments:
        destination_file_full_path -- The full path of the destination file.
        request_context -- The context of the request, including claims and other metadata.
        """
        dest_path = os.path.dirname(destination_file_path)

        dest_path_path, dest_file_name = normalize_path(dest_path)

        logging.debug(f"Looking for destination directory {dest_file_name} at path {dest_path_path}")

        files_client = FilesTableClient()

        dest_directory = files_client.get(
            path_hash=File.generate_hash(dest_path_path),
            name_hash=File.generate_hash(dest_file_name),
        )

        if not dest_directory:
            return self.respond(
                status_code=404,
                body={"message": "destination directory not found"},
            )

        if not entity_has_access(file=dest_directory, request_context=request_context, requested_permission_names=["write"]):
            logging.error(f"Requestor does not have write access to {dest_file_name} at path {dest_path_path}")

            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )

        if not dest_directory.is_directory:
            return self.respond(
                status_code=400,
                body={"message": "destination must be a directory"},
            )

        dest_name = os.path.basename(destination_file_path)

        logging.debug(f"Looking for existing file name {dest_name} at path {dest_path}")

        dest_exist_file = files_client.get(
            name_hash=File.generate_hash(dest_name),
            path_hash=File.generate_hash(dest_path),
        )

        if dest_exist_file:
            return self.respond(
                status_code=404,
                body={"message": "destination file already exists"},
            )

        return None

    def _recursive_copy(self, bucket_name: str, claims: JWTClaims, destination_path: str, files_client: FilesTableClient,
                        request_context: Dict, source_directory: File,
                        versions_client: FileVersionsTableClient) -> Tuple[List[Dict], List[File]]:
        """
        Recursively copy all children from source directory to destination.

        Keyword arguments:
        bucket_name -- The name of the bucket to copy the file to.
        claims -- The claims of the entity making the request.
        destination_path -- The path to copy the files to.
        files_client -- The client to interact with the files table.
        request_context -- The context of the request, including claims and other metadata.
        source_directory -- The source directory to copy from.
        versions_client -- The client to interact with the file versions table.

        Returns:
            Tuple containing:
            - List of successfully copied files (as dicts with source and destination info)
            - List of files that couldn't be copied due to permissions
        """
        copied_files = []

        no_access_files = []

        # Check read access to source directory
        if not entity_has_access(file=source_directory, request_context=request_context, requested_permission_names=["read"]):
            logging.warning(f"No read access to source directory {source_directory.full_path}")

            no_access_files.append(source_directory)

            return copied_files, no_access_files

        # Get immediate children
        source_dir_path_hash = File.generate_hash(source_directory.full_path)

        children, _ = files_client.list(path_hash=source_dir_path_hash)

        for child in children:
            # Check read access to child
            if not entity_has_access(file=child, request_context=request_context, requested_permission_names=["read"]):
                logging.warning(f"No read access to {child.full_path}")

                no_access_files.append(child)

                continue

            # Calculate destination path for this child
            relative_path = os.path.relpath(child.full_path, source_directory.full_path)

            child_dest_path = os.path.join(destination_path, relative_path)

            if child.is_directory:
                # Create the directory in destination
                dest_dir_name = os.path.basename(child_dest_path)

                dest_parent_path = os.path.dirname(child_dest_path)

                new_dir = File(
                    file_name=dest_dir_name,
                    file_path=dest_parent_path,
                    file_type=child.file_type,
                    is_directory=True,
                    metadata=child.metadata,
                    name_hash=File.generate_hash(dest_dir_name),
                    owner=claims.entity,
                    group=claims.primary_group,
                    path_hash=File.generate_hash(dest_parent_path),
                    permissions=child.permissions,
                )

                files_client.put(file=new_dir)

                publish_file_update_event(
                    file=new_dir,
                    file_event_type=FileEventType.CREATED,
                    requestor=claims.entity,
                )

                copied_files.append({
                    "source": child.full_path,
                    "destination": child_dest_path,
                    "type": "directory"
                })

                # Recursively copy the directory contents
                sub_copied, sub_no_access = self._recursive_copy(
                    source_directory=child,
                    destination_path=child_dest_path,
                    files_client=files_client,
                    versions_client=versions_client,
                    request_context=request_context,
                    claims=claims,
                    bucket_name=bucket_name
                )

                copied_files.extend(sub_copied)

                no_access_files.extend(sub_no_access)

            else:
                # Copy the file
                dest_file_name = os.path.basename(child_dest_path)

                dest_parent_path = os.path.dirname(child_dest_path)

                new_file = File(
                    description=child.description,
                    file_name=dest_file_name,
                    file_path=dest_parent_path,
                    file_type=child.file_type,
                    metadata=child.metadata,
                    name_hash=File.generate_hash(dest_file_name),
                    owner=claims.entity,
                    group=claims.primary_group,
                    path_hash=File.generate_hash(dest_parent_path),
                    permissions=child.permissions,
                )

                files_client.put(file=new_file)

                # Copy the latest version if it exists
                if child.latest_version_id:
                    existing_version = versions_client.get(
                        full_path_hash=child.full_path_hash,
                        version_id=child.latest_version_id
                    )

                    if existing_version:
                        new_file_version = self._copy_file_version_data(
                            bucket_name=bucket_name,
                            existing_file_version=existing_version,
                            new_file=new_file
                        )

                        new_file.latest_version_id = new_file_version.version_id

                        files_client.put(file=new_file)

                        publish_file_update_event(
                            file=new_file,
                            file_event_type=FileEventType.VERSION_CREATED,
                            requestor=claims.entity,
                            details={"version_id": new_file_version.version_id}
                        )

                publish_file_update_event(
                    file=new_file,
                    file_event_type=FileEventType.CREATED,
                    requestor=claims.entity,
                )

                copied_files.append({
                    "source": child.full_path,
                    "destination": child_dest_path,
                    "type": "file",
                    "version_id": new_file.latest_version_id
                })

        return copied_files, no_access_files

    def copy_file(self, request_body: ObjectBody, request_context: Dict):
        """
        Copy a file to a new location.
        Keyword arguments:

        request_body -- The request body containing the file and new location.
        request_context -- The context of the request, including claims and other metadata.
        """
        files_client = FilesTableClient()

        source_f_path, source_f_name = normalize_path(request_body["source_file_path"])

        source_file_name_hash = File.generate_hash(source_f_name)

        source_file_path_hash = File.generate_hash(source_f_path)

        logging.debug(f"Looking for file {source_f_name} at path {source_f_path}")

        source_file = files_client.get(path_hash=source_file_path_hash, name_hash=source_file_name_hash)

        if not source_file:
            return self.respond(
                status_code=404,
                body={"message": "not found"},
            )

        if not entity_has_access(file=source_file, request_context=request_context, requested_permission_names=["read"]):
            logging.error(f"Requestor does not have read access to file {source_f_name} at path {source_f_path}")

            return self.respond(
                status_code=403,
                body={"message": "insufficient permissions"},
            )

        destination_file_full_path = request_body["destination_file_path"]

        # Destination directory
        validation_resp_body = self._validate_copy_destination(
            destination_file_path=destination_file_full_path,
            request_context=request_context
        )

        if validation_resp_body:
            return validation_resp_body

        logging.debug(f"Validated source and destination files")

        additional_resp = {}

        existing_version = None

        if source_file.is_directory:
            logging.debug(f"Source file {source_file.full_path} is a directory")

            if not request_body.get("recursive", default_return=False):
                logging.debug(f"Attempting copy directory {source_file.full_path} without recursive flag")

                return self.respond(
                    status_code=400,
                    body={"message": "copying directories requires recursive flag"},
                )

            bucket_name = setting_value(
                namespace="ratio::storage",
                setting_key="raw_bucket",
            )

            logging.debug(f"Executing recursive copy from directory {source_file.full_path} to {destination_file_full_path}")

            copied_files, no_access_files = self._recursive_copy(
                source_directory=source_file,
                destination_path=destination_file_full_path,
                files_client=files_client,
                versions_client=FileVersionsTableClient(),
                request_context=request_context,
                claims=JWTClaims.from_claims(claims=request_context["request_claims"]),
                bucket_name=bucket_name
            )

            additional_resp["copied_files"] = copied_files

            additional_resp["no_access_files"] = [file.full_path for file in no_access_files]

        else:
            requested_version_id = request_body.get("version_id")

            logging.debug(f"Latest version for file {source_file.full_path}")

            copy_version_id = None

            if requested_version_id:
                logging.debug(f"Using requested version ID {requested_version_id} for file {source_file.full_path}")

                copy_version_id = requested_version_id

            # If there is a latest version ID copy it
            if source_file.latest_version_id:
                logging.debug(f"Using latest version ID {source_file.latest_version_id} for file {source_file.full_path}")

                copy_version_id = source_file.latest_version_id

            # Checks this down below
            existing_version = None

            logging.debug(f"Found file version {copy_version_id} for file {source_file.full_path}")

            if copy_version_id:
                versions_client = FileVersionsTableClient()

                logging.debug(f"Looking for file version {copy_version_id} for file {source_file.full_path}")

                existing_version = versions_client.get(full_path_hash=source_file.full_path_hash, version_id=source_file.latest_version_id)

                if not existing_version:
                # Validate the version ID exists
                    return self.respond(
                        status_code=404,
                        body={"message": "requested version not found"},
                    )

        claims = JWTClaims.from_claims(request_context["request_claims"])

        file_name = os.path.basename(destination_file_full_path)

        dest_directory = os.path.dirname(destination_file_full_path)

        new_file = File(
            description=source_file.description,
            file_name=file_name,
            file_path=dest_directory,
            file_type=source_file.file_type,
            metadata=source_file.metadata,
            name_hash=File.generate_hash(file_name),
            owner=claims.entity,
            group=claims.primary_group,
            path_hash=File.generate_hash(dest_directory),
            permissions=source_file.permissions,
        )

        files_client.put(file=new_file)

        publish_file_update_event(
            file=new_file,
            file_event_type=FileEventType.CREATED,
            requestor=claims.entity,
        )

        last_read_dt = None

        logging.debug(f"Existing version {existing_version} for file {source_file.full_path}")

        if existing_version:
            logging.debug(f"Copying file version {existing_version.version_id} for file {source_file.full_path}")

            new_file_version = self._copy_file_version_data(
                existing_file_version=existing_version,
                new_file=new_file,
                bucket_name=setting_value(
                    namespace="ratio::storage",
                    setting_key="raw_bucket",
                )
            )

            additional_resp["version_id"] = new_file_version.version_id

            last_read_dt = datetime.now(tz=utc_tz)

            new_file.latest_version_id = new_file_version.version_id

            publish_file_update_event(
                file=new_file,
                file_event_type=FileEventType.VERSION_CREATED,
                requestor=claims.entity,
                details={
                    "version_id": new_file_version.version_id,
                },
            )

            files_client.put(file=new_file)

        # Update the existing file access times
        files_client.set_last_accessed(
            last_accessed_on=datetime.now(tz=utc_tz),
            last_read_on=last_read_dt,
            name_hash=source_file.name_hash,
            path_hash=source_file.path_hash,
        )

        return self.respond(
            status_code=200,
            body={
                "file_path": new_file.full_path,
                **additional_resp,
            }
        )

    def move_file(self, request_body: ObjectBody, request_context: Dict):
        """
        Move a file to a new location.

        Keyword arguments:
        request_body -- The request body containing the file and new location.
        request_context -- The context of the request, including claims and other metadata.
        """

        return self.respond(
            status_code=501,
            body={"message": "not implemented"},
        )