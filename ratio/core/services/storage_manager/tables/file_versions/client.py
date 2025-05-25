import hashlib

from datetime import datetime, UTC as utc_tz
from enum import StrEnum
from typing import Dict, List, Optional, Union, Tuple

from da_vinci.core.orm.client import (
    TableClient,
    TableObject,
    TableObjectAttribute,
    TableObjectAttributeType,
    TableScanDefinition,
)


class Origin(StrEnum):
    """
    Enum for file classification.
    """
    EXTERNAL = "external"
    INTERNAL = "internal"


class FileVersion(TableObject):
    table_name = "file_versions"

    description = "The file table stores information about the file versions available in the system."

    partition_key_attribute = TableObjectAttribute(
        name="full_path_hash",
        attribute_type=TableObjectAttributeType.STRING,
        description="The unique hash of the file path and name.",
    )

    sort_key_attribute = TableObjectAttribute(
        name="version_id",
        attribute_type=TableObjectAttributeType.STRING,
        description="The unique id of the file version provided by S3.",
    )

    attributes = [
        TableObjectAttribute(
            name="added_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the data was added to the system.",
            default=lambda: datetime.now(tz=utc_tz),
        ),

        TableObjectAttribute(
            name="file_name",
            attribute_type=TableObjectAttributeType.STRING,
            description="The unique 'file' name of the file, e.g. 'john_doe_resume'.",
        ),

        TableObjectAttribute(
            name="file_path",
            attribute_type=TableObjectAttributeType.STRING,
            description="The path of the file, e.g. '/users/john_doe/resumes'.",
        ),

        TableObjectAttribute(
            name="metadata",
            attribute_type=TableObjectAttributeType.JSON_STRING,
            description="The metadata associated with the file version.",
            optional=True,
        ),

        TableObjectAttribute(
            name="next_version_id",
            attribute_type=TableObjectAttributeType.STRING,
            description="The id of the next version of the file.",
            optional=True,
        ),

        TableObjectAttribute(
            name="origin",
            attribute_type=TableObjectAttributeType.STRING,
            description="The origin of the file. Can be either 'external' or 'internal'.",
            default=Origin.INTERNAL,
        ),

        TableObjectAttribute(
            name="originator_id",
            attribute_type=TableObjectAttributeType.STRING,
            description="The id of the originator of the file. This is the id of the entity responsible for the existence of a version in the system.",
        ),

        TableObjectAttribute(
            name="previous_version_id",
            attribute_type=TableObjectAttributeType.STRING,
            description="The id of the previous version of the file.",
            optional=True,
        ),

        TableObjectAttribute(
            name="size",
            attribute_type=TableObjectAttributeType.NUMBER,
            description="The size of the file in bytes.",
            optional=True,
        ),
    ]

    @property
    def file_id(self) -> str:
        return TableObjectAttribute.composite_string_value(
            values=[
                self.full_path_hash,
                self.version_id,
            ]
        )

    def clone_to_next_version(self, data_ids: List[str], originator_id: str, version_id: str, added_on: Optional[datetime] = None,
                              metadata: Optional[Dict] = None, origin: Origin = None) -> "FileVersion":
        """
        Clone the current file version to a new version.

        Keyword arguments:
        data_ids -- The list of data IDs associated with the new file version.
        originator_id -- The id of the originator of the new file version.
        added_on -- The date and time the new file version was added to the system.
        metadata -- The metadata associated with the new file version.
        origin -- The origin of the new file version. Can be either 'external' or 'internal'.
        version_id -- The unique id of the new file version.
        """
        # Create the new file version object and update self attributes to point to it
        new_file_version = FileVersion(
            full_path_hash=self.full_path_hash,
            data_ids=data_ids,
            file_name=self.file_name,
            file_path=self.file_path,
            added_on=added_on,
            metadata=metadata,
            origin=origin,
            originator_id=originator_id,
            previous_version_id=self.version_id,
            version_id=version_id,
        )

        # Update the next version id of the current file version to point to the new file version
        self.next_version_id = new_file_version.version_id

        return new_file_version


class FileVersionsScanDefinition(TableScanDefinition):
    def __init__(self):
        super().__init__(table_object_class=FileVersion)


class FileVersionsTableClient(TableClient):
    def __init__(self, app_name: Optional[str] = None, deployment_id: Optional[str] = None):
        super().__init__(
            app_name=app_name,
            deployment_id=deployment_id,
            default_object_class=FileVersion,
        )

    def delete(self, file_version: FileVersion) -> None:
        """
        Delete a file version object from the system.

        Keyword arguments:
        file_version -- The file version object to delete.
        """
        return self.delete_object(file_version)
    
    def get(self, full_path_hash: Union[str, Tuple], version_id: str, consistent_read: bool = False) -> Union[FileVersion, None]:
        """
        Get a file version object from the system.

        Keyword arguments:
        full_path_hash -- The unique hash of the file path and name.
        version_id -- The unique id of the file version.
        """
        if isinstance(full_path_hash, tuple):
            full_path_hash = TableObjectAttribute.composite_string_value(
                values=full_path_hash
            )

        return self.get_object(partition_key_value=full_path_hash, sort_key_value=version_id, consistent_read=consistent_read)

    def get_by_full_path_hash(self, full_path_hash: Union[str, Tuple]) -> Union[List[FileVersion], None]:
        """
        Gets all file versions for a given full path hash.

        Keyword arguments:
        full_path_hash -- The unique hash of the file path and name.
        last_evaluated_key -- The last evaluated key to start the query from.
        """

        if isinstance(full_path_hash, tuple):
            full_path_hash = TableObjectAttribute.composite_string_value(
                values=full_path_hash
            )

        parameters = {
            "KeyConditionExpression": "FullPathHash = :full_path_hash",
            "ExpressionAttributeValues": {
                ":full_path_hash": {"S": full_path_hash},
            },
            "IndexName": "full_path_hash-index",
        }

        all = []

        for page in self.paginated(call='query', parameters=parameters):
            all.extend(page.items)

        return all

    def put(self, file_version: FileVersion) -> None:
        """
        Put a file version object into the system.

        Keyword arguments:
        file_version -- The file object to put into the system.
        """
        return self.put_object(file_version)