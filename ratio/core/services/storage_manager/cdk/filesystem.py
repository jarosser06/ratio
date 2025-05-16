"""
CDK Construct for creating an initial FileSystem construct in the DynamoDB table.
"""
import os
from typing import Optional

from constructs import Construct

from da_vinci_cdk.constructs.base import custom_type_name

from da_vinci_cdk.constructs.dynamodb import DynamoDBItem

from ratio.core.services.storage_manager.tables.file_types.client import FileType as FileTypeObj
from ratio.core.services.storage_manager.tables.files.client import File as FileObj


class RegisteredFileType(DynamoDBItem):
    """
    Creates a new file type construct in the DynamoDB table.
    """
    def __init__(self, scope: Construct, type_name: str, files_cannot_be_deleted: Optional[bool] = False, description: Optional[str] = None,
                 content_type: Optional[str] = None, is_directory_type: Optional[bool] = False, name_restrictions: Optional[str] = None):
        """
        Initialize a new file type construct.

        Keyword arguments:
        scope -- The CDK scope.
        type_name -- The name of the file type.
        cannot_be_deleted -- Whether the file type cannot be deleted.
        description -- The description of the file type.
        content_type -- The content type of the file type. E.g. 'text/plain', 'image/jpeg', etc.
        is_container_type -- Whether the file type is a container type. E.g. directory
        name_restrictions -- The name restrictions for the file type.
        """
        base_construct_id = f"ratio-ft-reg-{type_name}"

        super().__init__(
            construct_id=base_construct_id,
            custom_type_name=custom_type_name("FileType", prefix="RatioFS"),
            scope=scope,
            support_updates=False,
            table_object=FileTypeObj(
                type_name=type_name,
                description=description,
                files_cannot_be_deleted=files_cannot_be_deleted,
                content_type=content_type,
                is_directory_type=is_directory_type,
                name_restrictions=name_restrictions,
            )
        )


class RegisteredFile(DynamoDBItem):
    """Creates a new file construct in the DynamoDB table."""
    def __init__(self, scope: Construct, file_path: str, file_type: str, owner: str, group: str, description: Optional[str] = None,
                 file_name: Optional[str] = None, is_directory: bool = False, permissions: Optional[str] = "644"):
        """
        Initialize a new file construct directly in the DynamoDB table.

        WARNING: This is not the recommended way to create a file construct. It is mostly used for the framework
        to bootstrap the initial root file system.

        Keyword arguments:
        scope -- The CDK scope.
        file_name -- The name of the file. If not provided, it will be extracted from the file path.
        file_path -- The full path including the file name.
        file_type -- The type of the file.
        owner -- The owner of the file.
        group -- The group of the file.
        description -- The description of the file.
        exclude_parent -- Whether to exclude the parent id from the file path.
        is_directory_type -- Whether the file type is a container type. E.g. directory
        permissions -- The permissions for the file.
        """
        if file_name:
            f_name = file_name

            f_path = file_path

        else:
            f_name = os.path.basename(file_path) or "/"

            if f_name == "" and file_path == "/":
                f_name = "/"

            f_path = os.path.dirname(file_path)

        file_name_hash = FileObj.generate_hash(f_name)

        file_path_hash = FileObj.generate_hash(f_path)

        base_construct_id = f"ratio-f-reg-{file_name_hash}-{file_path_hash}"

        tbl_obj = FileObj(
            description=description,
            file_name=f_name,
            file_path=f_path,
            file_type=file_type,
            is_directory=is_directory,
            name_hash=file_name_hash,
            owner=owner,
            group=group,
            path_hash=file_path_hash,
            permissions=permissions,
        )

        # Since not using the ORM, we need to manually call this method
        tbl_obj.execute_on_update()

        super().__init__(
            construct_id=base_construct_id,
            custom_type_name=custom_type_name("File", prefix="RatioFS"),
            scope=scope,
            support_updates=False,
            table_object=tbl_obj,
        )