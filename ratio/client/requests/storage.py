from typing import Dict, Optional

from ratio.client.client import (
    RequestAttributeType,
    RequestBodyAttribute,
    RequestBody,
)


class ChangeFilePermissionsRequest(RequestBody):
    """
    Change file permissions request body schema.
    """
    path = "/storage/change_file_permissions"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="group",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
            required_if_attrs_not_set=["owner", "permissions"],
        ),
        RequestBodyAttribute(
            name="owner",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
            required_if_attrs_not_set=["group", "permissions"],
        ),
        RequestBodyAttribute(
            name="permissions",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
            required_if_attrs_not_set=["group", "owner"],
        ),
    ]

    def __init__(self, file_path: str, group: str = None, owner: str = None, permissions: str = None):
        """
        Initialize the ChangeFilePermissions request body.

        Keyword arguments:
        file_path -- The path to the file.
        group -- The group to set on the file.
        owner -- The owner to set on the file.
        permissions -- The permissions to set on the file.
        """
        super().__init__(
            file_path=file_path,
            group=group,
            owner=owner,
            permissions=permissions,
        )


class CopyFileRequest(RequestBody):
    """
    Copy file request body schema.
    """
    path = "/storage/copy_file"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="destination_file_path",
            attribute_type=RequestAttributeType.STRING,
        ),
        RequestBodyAttribute(
            name="recursive",
            attribute_type=RequestAttributeType.BOOLEAN,
            default=False,
            optional=True,
        ),
        RequestBodyAttribute(
            name="source_file_path",
            attribute_type=RequestAttributeType.STRING,
        ),
        RequestBodyAttribute(
            name="version_id",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
    ]

    def __init__(self, destination_file_path: str,  source_file_path: str, recursive: Optional[bool] = None,
                 version_id: Optional[str] = None):
        """
        Initialize the CopyFile request body.

        Keyword arguments:
        file_path -- The path to the file to copy.
        destination_file_path -- The path to the destination file.
        recursive -- Whether to perform the operation recursively.
        version_id -- The version of the file to copy. If not provided, the latest version will be used.
        """
        super().__init__(
            destination_file_path=destination_file_path,
            recursive=recursive,
            source_file_path=source_file_path,
            version_id=version_id,
        )


class DescribeFileTypeRequest(RequestBody):
    """
    Describe file type request body schema.
    """
    path = "/storage/describe_file_type"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_type",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, file_type: str):
        """
        Initialize the DescribeFileType request body.

        Keyword arguments:
        file_type -- The file type to describe.
        """
        super().__init__(file_type=file_type)


class DeleteFileRequest(RequestBody):
    """
    Delete file request body schema.
    """
    path = "/storage/delete_file"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="force",
            attribute_type=RequestAttributeType.BOOLEAN,
            default=False,
            optional=True,
        ),
        RequestBodyAttribute(
            name="recursive",
            attribute_type=RequestAttributeType.BOOLEAN,
            default=False,
            optional=True,
        ),
    ]

    def __init__(self, file_path: str, force: bool = False, recursive: bool = False):
        """
        Initialize the DeleteFile request body.

        Keyword arguments:
        file_path -- The path to the file.
        """
        super().__init__(file_path=file_path, force=force, recursive=recursive)


class DeleteFileTypeRequest(RequestBody):
    """
    Delete file type request body schema.
    """
    path = "/storage/delete_file_type"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_type",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, file_type: str):
        """
        Initialize the DeleteFileType request body.

        Keyword arguments:
        file_type -- The file type to delete.
        """
        super().__init__(file_type=file_type)


class DeleteFileVersionRequest(RequestBody):
    """
    Delete file version request body schema.
    """
    path = "/storage/delete_file_version"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="force",
            attribute_type=RequestAttributeType.BOOLEAN,
            optional=True,
            default=False,
        ),
        RequestBodyAttribute(
            name="version_id",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
    ]

    def __init__(self, file_path: str, force: Optional[bool] = None, version_id: Optional[str] = None):
        """
        Initialize the DeleteFileVersion request body.

        Keyword arguments:
        file_path -- The path to the file.
        version_id -- The version of the file.
        """
        super().__init__(file_path=file_path, force=force, version_id=version_id)


class DescribeFileRequest(RequestBody):
    """
    Describe file request body schema.
    """
    path = "/storage/describe_file"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, file_path: str):
        """
        Initialize the DescribeFile request body.

        Keyword arguments:
        file_path -- The path to the file.
        """
        super().__init__(file_path=file_path)


class DescribeFileVersionRequest(RequestBody):
    """
    Describe file versions request body schema.
    """
    path = "/storage/describe_file_version"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="version_id",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
    ]

    def __init__(self, file_path: str, version_id: str = None):
        """
        Initialize the DescribeFileVersions request body.

        Keyword arguments:
        file_path -- The path to the file.
        version_id -- The version of the file. If not provided, the latest version will be used.
        """
        super().__init__(file_path=file_path, version_id=version_id)


class DescribeFileTypeRequest(RequestBody):
    """
    Describe file types request body schema.
    """
    path = "/storage/describe_file_type"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_type",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, file_type: str):
        """
        Initialize the DescribeFileType request body.

        Keyword arguments:
        file_type -- The file type to describe.
        """
        super().__init__(file_type=file_type)


class GetFileVersionRequest(RequestBody):
    """
    Get file version request body schema.
    """
    path = "/storage/get_file_version"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="version_id",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
    ]

    def __init__(self, file_path: str, version_id: str = None):
        """
        Initialize the GetFileVersion request body.

        Keyword arguments:
        file_path -- The path to the file.
        version_id -- The version of the file. If not provided, the latest version will be used.
        """
        super().__init__(file_path=file_path, version_id=version_id)


class ListFilesRequest(RequestBody):
    """
    List files request body schema.
    """
    path = "/storage/list_files"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="recursive",
            attribute_type=RequestAttributeType.BOOLEAN,
            default=False,
            optional=True,
        ),
    ]

    def __init__(self, file_path: str, recursive: Optional[bool] = False):
        """
        Initialize the ListFiles request body.

        Keyword arguments:
        file_path -- The path to the file.
        recursive -- Whether to perform the operation recursively.
        """
        super().__init__(file_path=file_path, recursive=recursive)


class ListFileTypesRequest(RequestBody):
    """
    List file types request body schema.
    """
    path = "/storage/list_file_types"

    requires_auth = True

    attribute_definitions = []

    def __init__(self):
        """
        Initialize the ListFileTypes request body.
        """
        super().__init__()


class ListFileVersionsRequest(RequestBody):
    """
    List file versions request body schema.
    """
    path = "/storage/list_file_versions"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, file_path: str):
        """
        Initialize the ListFileVersions request body.

        Keyword arguments:
        file_path -- The path to the file.
        """
        super().__init__(file_path=file_path)


class MoveFileRequest(RequestBody):
    """
    Move file request body schema.
    """
    path = "/storage/move_file"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="destination_file_path",
            attribute_type=RequestAttributeType.STRING,
        ),
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
        ),
    ]

    def __init__(self, destination_file_path: str, file_path: str):
        """
        Initialize the MoveFile request body.

        Keyword arguments:
        destination_file_path -- The path to the destination file.
        file_path -- The path to the file to move.
        """
        super().__init__(
            file_path=file_path,
            destination_file_path=destination_file_path,
        )


class PutFileRequest(RequestBody):
    """
    Put file request body schema.
    """
    path = "/storage/put_file"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="file_type",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="group",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="metadata",
            attribute_type=RequestAttributeType.OBJECT,
            optional=True,
        ),
        RequestBodyAttribute(
            name="owner",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="permissions",
            attribute_type=RequestAttributeType.STRING,
            default="644", #Permissions order is Owner, Group, Everyone
            optional=True,
        ),
    ]

    def __init__(self, file_path: str, file_type: str, group: str = None, metadata: dict = None,
                owner: str = None, permissions: str = None):
            """
            Initialize the PutFile request body.
    
            Keyword arguments:
            file_type -- The type of the file.
            group -- The group of the file.
            metadata -- The metadata of the file.
            owner -- The owner of the file.
            permissions -- The permissions of the file.
            """
            super().__init__(
                file_path=file_path,
                file_type=file_type,
                group=group,
                metadata=metadata,
                owner=owner,
                permissions=permissions,
            )


class PutFileTypeRequest(RequestBody):
    """
    Put file type request body schema.
    """
    path = "/storage/put_file_type"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="description",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="file_type",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="is_directory_type",
            attribute_type=RequestAttributeType.BOOLEAN,
            default=False,
            optional=True,
        ),
        RequestBodyAttribute(
            name="name_restrictions",
            attribute_type=RequestAttributeType.STRING,
            default="^[a-zA-Z0-9_-]+(\\.[a-zA-Z0-9_-]+)*$",
            optional=True,
        ),
    ]

    def __init__(self, file_type: str, description: str, is_container_type: bool = False,
                 name_restrictions: str = None):
        """
        Initialize the PutFileType request body.

        Keyword arguments:
        file_type -- The type of the file.
        description -- The description of the file type.
        is_container_type -- Whether the file type is a container type.
        name_restrictions -- The name restrictions for the file type.
        """
        super().__init__(
            file_type=file_type,
            description=description,
            is_container_type=is_container_type,
            name_restrictions=name_restrictions,
        )


class PutFileVersionRequest(RequestBody):
    """
    Put file version request body schema.
    """
    path = "/storage/put_file_version"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="data",
            attribute_type=RequestAttributeType.ANY,
            optional=False,
        ),
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="metadata",
            attribute_type=RequestAttributeType.OBJECT,
            optional=True,
        ),
        RequestBodyAttribute(
            name="origin",
            attribute_type=RequestAttributeType.STRING,
            immutable_default="external",
            optional=True,
        ),
        RequestBodyAttribute(
            name="source_file_ids",
            attribute_type=RequestAttributeType.LIST,
            optional=True,
        ),
    ]

    def __init__(self, data: str, file_path: str, metadata: Optional[Dict] = None, source_file_ids: list = None):
        """
        Initialize the PutFileVersion request body.

        Keyword arguments:
        data -- The data of the file.
        file_path -- The path to the file.
        metadata -- The metadata of the file.
        source_file_ids -- The source file IDs.
        """
        super().__init__(
            data=data,
            file_path=file_path,
            metadata=metadata,
            source_file_ids=source_file_ids,
        )


class ValidateFileAccessRequest(RequestBody):
    """
    Validate file access request body schema.

    """
    path = "/storage/validate_file_access"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="requested_permission_names",
            attribute_type=RequestAttributeType.LIST,
            default=["read"],
            optional=True,
        ),
    ]