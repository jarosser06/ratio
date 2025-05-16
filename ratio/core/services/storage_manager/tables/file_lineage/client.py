
from datetime import datetime, timedelta, UTC as utc_tz
from typing import List, Optional, Union, Tuple

from da_vinci.core.orm.client import (
    TableClient,
    TableObject,
    TableObjectAttribute,
    TableObjectAttributeType,
    TableScanDefinition,
)


class FileLineageEntry(TableObject):
    table_name = "file_lineage"

    description = "The file lineage table stores information about the lineage of files in the system."

    partition_key_attribute = TableObjectAttribute(
        name="source_file_id",
        attribute_type=TableObjectAttributeType.STRING,
        description="The unique identifier of the file, which is the full path hash plus the version id.",
    )

    sort_key_attribute = TableObjectAttribute(
        name="lineage_file_id",
        attribute_type=TableObjectAttributeType.STRING,
        description="The unique identifier of the lineage entry, which is the full path hash plus the version id.",
    )

    attributes = [
        TableObjectAttribute(
            name="created_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the lineage entry was created.",
            default=lambda: datetime.now(utc_tz),
        ),

        TableObjectAttribute(
            name="lineage_file_path",
            attribute_type=TableObjectAttributeType.STRING,
            description="The full path of the lineage file.",
            optional=False,
        ),

        TableObjectAttribute(
            name="lineage_file_version",
            attribute_type=TableObjectAttributeType.STRING,
            description="The version of the lineage file.",
            optional=False,
        ),

        TableObjectAttribute(
            name="lineage_metadata",
            attribute_type=TableObjectAttributeType.JSON_STRING,
            description="The metadata associated with the lineage entry.",
            optional=True,
        ),

        TableObjectAttribute(
            name="source_file_path",
            attribute_type=TableObjectAttributeType.STRING,
            description="The full path of the source file.",
            optional=False,
        ),

        TableObjectAttribute(
            name="source_file_version",
            attribute_type=TableObjectAttributeType.STRING,
            description="The version of the source file.",
            optional=False,
        ),

        TableObjectAttribute(
            name="source_full_path_hash",
            attribute_type=TableObjectAttributeType.STRING,
            description="The hash of the full path of the file. Makes it easier to scan the whole table for lineage matching a whole file not just a file version",
            optional=False,
        ),
    ]


class FileLineageTableClient(TableClient):
    def __init__(self, app_name: Optional[str] = None, deployment_id: Optional[str] = None):
        super().__init__(
            app_name=app_name,
            deployment_id=deployment_id,
            default_object_class=FileLineageEntry,
        )

    def delete(self, file_lineage_entry: FileLineageEntry) -> None:
        """
        Delete a file lineage entry from the table.

        Keyword arguments:
        file_lineage_entry -- The file lineage entry to delete.
        """
        return self.delete_object(table_object=file_lineage_entry)

    def get(self, source_file_id: str, lineage_file_id: str) -> Union[FileLineageEntry, None]:
        """
        Get a file lineage entry from the table. Must provide at least one 

        Keyword arguments:
        source_file_id -- The unique identifier of the source file.
        lineage_file_id -- The unique identifier of the lineage entry.
        """

        return self.get_object(partition_key_value=source_file_id, sort_key_value=lineage_file_id)

    def get_all_by_full_path_hash(self, source_full_path_hash: Union[str, Tuple]) -> Union[List[FileLineageEntry], None]:
        """
        Get all file lineage entries from the table using the source_full_path_hash.

        Keyword arguments:
        source_full_path_hash -- The hash of the full path of the file.
        """
        full_path_hash = source_full_path_hash

        if isinstance(source_full_path_hash, tuple):
            full_path_hash = "-".join(source_full_path_hash)

        scan_definition = TableScanDefinition(table_object_class=self.default_object_class)

        scan_definition.add(
            attribute_name="source_full_path_hash",
            comparison="equal",
            value=full_path_hash,
        )

        return self.full_scan(scan_definition=scan_definition)

    def get_all_matching_single_key(self, source_file_id: str = None, lineage_file_id: str = None) -> Union[List[FileLineageEntry], None]:
        """
        Get a file lineage entry from the table using a single key.

        Keyword arguments:
        source_file_id -- The unique identifier of the source file.
        lineage_file_id -- The unique identifier of the lineage entry.
        """
        extra_args = {}

        if lineage_file_id:
            key = "LineageFileId"
            val = {"S": lineage_file_id}
            extra_args = {"IndexName": "lineage-index"}

        elif source_file_id:
            key = "SourceFileId"
            val = {"S": source_file_id}
        else:
            raise ValueError("Must provide one of either source_file_id or lineage_file_id")

        params = {
            "KeyConditionExpression": "#k = :v",
            "ExpressionAttributeNames": {"#k": key},
            "ExpressionAttributeValues": {":v": val},
            **extra_args,
        }

        returned_items = []

        for page in self.paginated(call='query', parameters=params):
            returned_items.extend(page.items)

        return returned_items

    def put(self, file_lineage_entry: FileLineageEntry) -> None:
        """
        Put a file lineage entry into the table.

        Keyword arguments:
        file_lineage_entry -- The file lineage entry to put.
        """
        return self.put_object(table_object=file_lineage_entry)