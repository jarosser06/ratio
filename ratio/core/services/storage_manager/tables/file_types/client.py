from datetime import datetime, UTC as utc_tz
from typing import Dict, List, Optional, Tuple, Union

from da_vinci.core.orm.client import (
    TableClient,
    TableObject,
    TableObjectAttribute,
    TableObjectAttributeType,
    TableScanDefinition,
)


class FileType(TableObject):
    table_name = "file_type"

    description = "The file type table stores information about the declared file types available to the system."

    partition_key_attribute = TableObjectAttribute(
        name="type_name",
        attribute_type=TableObjectAttributeType.STRING,
        description="The unique name of the file type. E.g. 'TEXT', 'IMAGE', etc.",
    )

    attributes = [
        TableObjectAttribute(
            name="added_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the file type was added.",
            default=lambda: datetime.now(utc_tz),
        ),

        TableObjectAttribute(
            name="content_type",
            attribute_type=TableObjectAttributeType.STRING,
            description="The content type of the file type. E.g. 'text/plain', 'image/jpeg', etc.",
            optional=True,
        ),

        TableObjectAttribute(
            name="description",
            attribute_type=TableObjectAttributeType.STRING,
            description="The description of the file type.",
            optional=True,
        ),

        TableObjectAttribute(
            name="files_cannot_be_deleted",
            attribute_type=TableObjectAttributeType.BOOLEAN,
            description="Whether a file of a type cannot be deleted. This is used to prevent deletion of system files.",
            optional=True,
            default=False,
        ),

        TableObjectAttribute(
            name="last_updated_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the file type was last updated.",
            optional=True,
            default=lambda: datetime.now(utc_tz),
        ),

        TableObjectAttribute(
            name="is_directory_type",
            attribute_type=TableObjectAttributeType.BOOLEAN,
            description="Whether the file type is a container type. E.g. directory",
            optional=True,
            default=False,
        ),

        TableObjectAttribute(
            name="name_restrictions",
            attribute_type=TableObjectAttributeType.STRING,
            description="A regex pattern that restricts the names of the file type. E.g. '^[a-zA-Z0-9_-]+$' would restrict the name to alphanumeric characters and underscores.",
            optional=True,
            default="^[a-zA-Z0-9_-]+(\\.[a-zA-Z0-9_-]+)*$",
        ),
    ]


class FileTypeTableClient(TableClient):
    def __init__(self, app_name: Optional[str] = None, deployment_id: Optional[str] = None):
        super().__init__(
            app_name=app_name,
            deployment_id=deployment_id,
            default_object_class=FileType,
        )

    def delete(self, file_type: FileType) -> None:
        """
        Delete a file type from the system.
        """
        return self.delete_object(file_type)

    def get(self, type_name: str) -> Union[FileType, None]:
        """
        Get a file type from the system.

        Keyword arguments:
        type_name -- The name of the file type to get
        """
        return self.get_object(partition_key_value=type_name)

    def list(self) -> Tuple[List[FileType], Optional[Dict]]:
        """
        List all file types in the system.
        """
        return self.full_scan(
            scan_definition=TableScanDefinition(table_object_class=self.default_object_class)
        )

    def put(self, file_type: FileType) -> None:
        """
        Put a file type into the system.

        Keyword arguments:
        file_type -- The file type to put into the system
        """
        return self.put_object(file_type)