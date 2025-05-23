"""
Storage Manager Request definitions.
"""
from da_vinci.core.immutable_object import (
    ObjectBodySchema,
    RequiredCondition,
    RequiredConditionGroup,
    SchemaAttribute,
    SchemaAttributeType,
)

from ratio.core.core_lib.definitions.events import FileEventType


FILE_PATH_REGEX = "^/(.*[^/])?$"


### Event Bus Event Definitions ###
class FileUpdateEvent(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="details",
            type_name=SchemaAttributeType.OBJECT,
            description="Any additional details included from the system about the file update.",
            required=False,
        ),
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            description="The full path of the file that was updated.",
            required=True,
        ),
        SchemaAttribute(
            name="file_type",
            type_name=SchemaAttributeType.STRING,
            description="The type of the file that was updated.",
            required=True,
        ),
        SchemaAttribute(
            name="file_event_type",
            type_name=SchemaAttributeType.STRING,
            description="The type of the file event.",
            required=True,
            enum=[event_type.value for event_type in FileEventType],
        ),
        SchemaAttribute(
            name="is_directory",
            type_name=SchemaAttributeType.BOOLEAN,
            description="True if the file is a directory.",
            required=True,
            default_value=False,
        ),
        SchemaAttribute(
            name="system_event_type",
            type_name=SchemaAttributeType.STRING,
            description="The type of the system event.",
            required=False,
            default_value="ratio::file_event",
        ),
    ]


### REST API Request Definitions ###


class ChangeFilePermissionsRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
        SchemaAttribute(
            name="permissions",
            type_name=SchemaAttributeType.STRING,
            required=True,
            required_conditions=[
                RequiredConditionGroup(
                    group_operator="and",
                    conditions=[
                        RequiredCondition(
                            param="owner",
                            operator="not_exists"
                        ),
                        RequiredCondition(
                            param="group",
                            operator="not_exists"
                        )
                    ]
                )
            ]
        ),
        SchemaAttribute(
            name="owner",
            type_name=SchemaAttributeType.STRING,
            required=True,
            required_conditions=[
                RequiredConditionGroup(
                    group_operator="and",
                    conditions=[
                        RequiredCondition(
                            param="permissions",
                            operator="not_exists"
                        ),
                        RequiredCondition(
                            param="group",
                            operator="not_exists"
                        )
                    ]
                )
            ]
        ),
        SchemaAttribute(
            name="group",
            type_name=SchemaAttributeType.STRING,
            required=True,
            required_conditions=[
                RequiredConditionGroup(
                    group_operator="and",
                    conditions=[
                        RequiredCondition(
                            param="permissions",
                            operator="not_exists"
                        ),
                        RequiredCondition(
                            param="owner",
                            operator="not_exists"
                        )
                    ]
                )
            ]
        ),
    ]


class CopyFileRequest(ObjectBodySchema):
    # Performs a shallow copy, only taking the first version of the file if there versions.
    attributes = [
        SchemaAttribute(
            name="destination_file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
        # Only valid if the destination is a directory.
        SchemaAttribute(
            name="recursive",
            type_name=SchemaAttributeType.BOOLEAN,
            default_value=False,
            required=False,
        ),
        SchemaAttribute(
            name="source_file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
        SchemaAttribute(
            name="use_latest_version",
            type_name=SchemaAttributeType.BOOLEAN,
            default_value=True,
            required=False,
        ),
        SchemaAttribute(
            name="version_id",
            type_name=SchemaAttributeType.STRING,
            required=False,
        ),
    ]


class DescribeFileTypeRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_type",
            type_name=SchemaAttributeType.STRING,
            required=True,
        ),
    ]


class DeleteFileRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
        SchemaAttribute(
            name="force",
            type_name=SchemaAttributeType.BOOLEAN,
            default_value=False,
            required=False,
        ),
        SchemaAttribute(
            name="recursive",
            type_name=SchemaAttributeType.BOOLEAN,
            default_value=False,
            required=False,
        ),
    ]


class DeleteFileVersionRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
        SchemaAttribute(
            name="force",
            type_name=SchemaAttributeType.BOOLEAN,
            default_value=False,
            required=False,
        ),
        SchemaAttribute(
            name="version_id",
            type_name=SchemaAttributeType.STRING,
            required=False,
        ),
    ]


class DeleteFileTypeRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_type",
            type_name=SchemaAttributeType.STRING,
            required=True,
        ),
    ]


class DescribeFileRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
    ]


class DescribeFileVersionRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
        SchemaAttribute(
            name="include_lineage",
            type_name=SchemaAttributeType.BOOLEAN,
            default_value=False,
            required=False,
        ),
        SchemaAttribute(
            name="version_id",
            type_name=SchemaAttributeType.STRING,
            required=False,
        ),
    ]


class FindFileRequest(ObjectBodySchema):
    attributes = [
        # This is the path in the file system to search ex: "/home/app1/data"
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern="^/.*/$",
            required=True,
        ),
        SchemaAttribute(
            name="is_file_type",
            type_name=SchemaAttributeType.STRING,
            required=False,
        ),
        SchemaAttribute(
            name="name_contains",
            type_name=SchemaAttributeType.STRING,
            required=False,
        ),
        SchemaAttribute(
            name="recursion_max_depth",
            type_name=SchemaAttributeType.NUMBER,
            default_value=1,
            required=False,
        ),
        SchemaAttribute(
            name="version_id",
            type_name=SchemaAttributeType.STRING,
            required=False,
        ),
    ]


class GetFileVersionRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
        SchemaAttribute(
            name="version_id",
            type_name=SchemaAttributeType.STRING,
            required=False,
        ),
    ]


class ListFilesRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern="^/.*$",
            required=True,
        ),
    ]


class ListFileVersionsRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
    ]


class MoveFileRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
        SchemaAttribute(
            name="destination_file_path",
            type_name=SchemaAttributeType.STRING,
            required=True,
        ),
    ]


class PutFileRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
        SchemaAttribute(
            name="file_type",
            type_name=SchemaAttributeType.STRING,
            required=True,
        ),
        SchemaAttribute(
            name="metadata",
            type_name=SchemaAttributeType.OBJECT,
            required=False,
        ),
        SchemaAttribute(
            name="owner",
            type_name=SchemaAttributeType.STRING,
            required=False,
        ),
        SchemaAttribute(
            name="group",
            type_name=SchemaAttributeType.STRING,
            required=False,
        ),
        SchemaAttribute(
            name="permissions",
            type_name=SchemaAttributeType.STRING,
            required=False,
            default_value="644",
        ),
    ]


class PutFileTypeRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="file_type",
            type_name=SchemaAttributeType.STRING,
            required=True,
        ),
        SchemaAttribute(
            name="content_search_instructions_path",
            type_name=SchemaAttributeType.STRING,
            required=False,
        ),
        SchemaAttribute(
            name="description",
            type_name=SchemaAttributeType.STRING,
            required=False,
        ),
        SchemaAttribute(
            name="is_directory_type",
            type_name=SchemaAttributeType.BOOLEAN,
            required=False,
            default_value=False,
        ),
        SchemaAttribute(
            name="name_restrictions",
            type_name=SchemaAttributeType.STRING,
            required=False,
            default_value="^[a-zA-Z0-9_-]+(\\.[a-zA-Z0-9_-]+)*$",
        )
    ]


class PutFileVersionRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="base64_encoded",
            type_name=SchemaAttributeType.BOOLEAN,
            default_value=False,
            required=False,
        ),
        SchemaAttribute(
            name="data",
            type_name=SchemaAttributeType.ANY,
            required=True,
        ),
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            required=True,
        ),
        SchemaAttribute(
            name="metadata",
            type_name=SchemaAttributeType.OBJECT,
            required=False,
        ),
        SchemaAttribute(
            name="origin",
            type_name=SchemaAttributeType.STRING,
            required=False,
            default_value="internal",
            enum=["internal", "external"],
        ),
        SchemaAttribute(
            description="The file path of the source file. This is used to create a lineage between the source and destination files. Expects a list of objects ex: {\"source_file_path\": \"/home/app1/data\", \"version_id\": \"123456\"}",
            name="source_files",
            type_name=SchemaAttributeType.OBJECT_LIST,
            required=False,
        ),
    ]


class ValidateFileAccessRequest(ObjectBodySchema):
    """Validates """
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            regex_pattern=FILE_PATH_REGEX,
            required=True,
        ),
        SchemaAttribute(
            name="requested_permission_names",
            description="The requested permissions to validate. Ex: [\"read\", \"write\"]",
            type_name=SchemaAttributeType.STRING_LIST,
            default_value=["read"],
            required=False,
        ),
    ]