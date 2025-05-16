from datetime import datetime, UTC as utc_tz
from typing import Optional, Union
from uuid import uuid4

from da_vinci.core.orm.client import (
    TableClient,
    TableObject,
    TableObjectAttribute,
    TableObjectAttributeType,
)


class Entity(TableObject):
    table_name = "entities"

    description = "The entities table stores information about the entities (applications, users, etc) with access to the system."

    partition_key_attribute = TableObjectAttribute(
        name="entity_id",
        attribute_type=TableObjectAttributeType.STRING,
        description="The unique id of the entity.",
        default=lambda: str(uuid4()),
    )

    attributes = [
        TableObjectAttribute(
            name="created_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the entity was created.",
            default=lambda: datetime.now(utc_tz),
        ),

        TableObjectAttribute(
            name="description",
            attribute_type=TableObjectAttributeType.STRING,
            description="The description of the entity.",
            optional=True,
        ),

        TableObjectAttribute(
            name="enabled",
            attribute_type=TableObjectAttributeType.BOOLEAN,
            description="Whether the entity is enabled or not.",
            optional=True,
            default=True,
        ),

        TableObjectAttribute(
            name="groups",
            attribute_type=TableObjectAttributeType.STRING_LIST,
            description="The groups the entity belongs to.",
        ),

        TableObjectAttribute(
            name='key_last_updated_on',
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the entity's key was last updated.",
            optional=True,
        ),

        TableObjectAttribute(
            name="home_directory",
            attribute_type=TableObjectAttributeType.STRING,
            description="The home directory of the entity.",
            optional=True,
        ),

        TableObjectAttribute(
            name="primary_group_id",
            attribute_type=TableObjectAttributeType.STRING,
            description="The id of the primary group the entity belongs to.",
        ),

        TableObjectAttribute(
            name="public_key",
            attribute_type=TableObjectAttributeType.STRING,
            description="The public key of the entity.",
            optional=True,
        ),
    ]


class EntitiesTableClient(TableClient):
    def __init__(self, app_name: Optional[str] = None, deployment_id: Optional[str] = None):
        """
        Initialize the entities table client.

        Keyword arguments:
        app_name -- The name of the application.
        deployment_id -- The deployment id of the application.
        """

        super().__init__(
            default_object_class=Entity,
            app_name=app_name,
            deployment_id=deployment_id,
        )

    def delete(self, entity: Entity) -> None:
        """
        Delete an entity from the system.

        Keyword arguments:
        entity -- The entity to delete.
        """

        self.delete_object(table_object=entity)

    def get(self, entity_id: str) -> Union[Entity, None]:
        """
        Get an entity from the system.

        Keyword arguments:
        entity_id -- The id of the entity to get.
        """

        return self.get_object(partition_key_value=entity_id)

    def put(self, entity: Entity) -> None:
        """
        Put an entity into the system.

        Keyword arguments:
        entity -- The entity to put.
        """

        self.put_object(table_object=entity)