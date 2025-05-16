from datetime import datetime, UTC as utc_tz
from typing import List, Optional, Union

from da_vinci.core.orm.client import (
    TableClient,
    TableObject,
    TableObjectAttribute,
    TableObjectAttributeType,
)


class Group(TableObject):
    table_name = "groups"

    description = "The groups table stores information about the groups available in the system."

    partition_key_attribute = TableObjectAttribute(
        name="group_id",
        attribute_type=TableObjectAttributeType.STRING,
        description="The unique id of the group. E.g. 'admin', 'user', etc.",
    )

    attributes = [
        TableObjectAttribute(
            name="created_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the group was created.",
            default=lambda: datetime.now(utc_tz),
        ),

        TableObjectAttribute(
            name="description",
            attribute_type=TableObjectAttributeType.STRING,
            description="The description of the group.",
            optional=True,
        ),

        TableObjectAttribute(
            name="members",
            attribute_type=TableObjectAttributeType.STRING_LIST,
            description="The members of the group.",
            optional=True,
        ),
    ]


class GroupsTableClient(TableClient):
    def __init__(self, app_name: Optional[str] = None, deployment_id: Optional[str] = None):
        """
        Initialize the groups table client.

        Keyword arguments:
        app_name -- The name of the application.
        """

        super().__init__(default_object_class=Group, app_name=app_name, deployment_id=deployment_id)

    def delete(self, group: Group) -> None:
        """
        Delete a group from the system.

        Keyword arguments:
        group -- The group to delete.
        """

        self.delete_object(group)

    def get(self, group_id: str) -> Union[Group, None]:
        """
        Get a group from the system.

        Keyword arguments:
        group_id -- The id of the group to get.
        """

        return self.get_object(partition_key_value=group_id)

    def batch_get(self, group_ids: List[str]) -> Union[List[Group], None]:
        """
        Get a list of groups from the system.

        Keyword arguments:
        group_ids -- The ids of the groups to get.
        """

        keys = [{"GroupId": {"S": group_id}} for group_id in group_ids]

        arguments = {
            self.table_endpoint_name: {
                "Keys": keys
            }
        }

        results = self.client.batch_get_item(RequestItems=arguments)

        if "Responses" in results:
            if self.table_endpoint_name in results["Responses"]:
                items = results["Responses"][self.table_endpoint_name]

                return [self.default_object_class.from_dynamodb_item(item) for item in items]

        return []

    def put(self, group: Group) -> None:
        """
        Put a group into the system.

        Keyword arguments:
        group -- The group to put.
        """

        self.put_object(group)