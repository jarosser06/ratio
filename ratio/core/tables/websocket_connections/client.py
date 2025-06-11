from datetime import datetime, timedelta, UTC as utc_tz
from typing import Optional
from uuid import uuid4

from da_vinci.core.orm.client import (
    TableClient,
    TableObject,
    TableObjectAttribute,
    TableObjectAttributeType,
)


class WebsocketConnection(TableObject):
    table_name = "websocket_connections"

    description = "A table that stores information about websocket connections."

    partition_key_attribute = TableObjectAttribute(
        name="connection_id",
        description="The unique identifier for the websocket connection.",
        attribute_type=TableObjectAttributeType.STRING,
    )

    ttl_attribute = TableObjectAttribute(
        name="time_to_live",
        attribute_type=TableObjectAttributeType.DATETIME,
        description="The time to live for the websocket connection. After this time, the connection will be considered expired.",
        optional=True,
        default=lambda: datetime.now(tz=utc_tz) + timedelta(hours=2),
    )

    attributes = [
        TableObjectAttribute(
            name="created_at",
            description="The time when the websocket connection was created.",
            attribute_type=TableObjectAttributeType.DATETIME,
            default=lambda: datetime.now(tz=utc_tz),
        ),

        TableObjectAttribute(
            name="domain_name",
            description="The domain name of the websocket connection.",
            attribute_type=TableObjectAttributeType.STRING,
        ),

        TableObjectAttribute(
            name="session_claims",
            description="The claims associated with the websocket session.",
            attribute_type=TableObjectAttributeType.JSON_STRING,
        ),

        TableObjectAttribute(
            name="session_token",
            description="The session token associated with the websocket connection.",
            attribute_type=TableObjectAttributeType.STRING,
        ),

        TableObjectAttribute(
            name="stage",
            description="The deployed websocket api stage.",
            attribute_type=TableObjectAttributeType.STRING,
        ),
    ]


class WebsocketConnectionsTableClient(TableClient):
    """
    Client for managing websocket connections in the system.
    """
    def __init__(self, app_name: Optional[str] = None, deployment_id: Optional[str] = None):
        """
        Initialize the WebsocketConnectionsTableClient.

        Keyword arguments:
        app_name -- The name of the app.
        deployment_id -- The id of the deployment.
        """
        super().__init__(app_name=app_name, deployment_id=deployment_id, default_object_class=WebsocketConnection)

    def delete(self, websocket_connection: WebsocketConnection) -> None:
        """
        Delete a websocket connection from the table.

        Keyword arguments:
        websocket_connection -- The websocket connection to delete.
        """
        self.delete(websocket_connection=websocket_connection)

    def delete_by_id(self, connection_id: str) -> None:
        """
        Delete a websocket connection from the table.

        Keyword arguments:
        connection_id -- The id of the websocket connection to delete.
        """
        key_args = {
            'partition_key_value': connection_id,
        }

        self.client.delete_item(
            TableName=self.table_endpoint_name,
            Key=self.default_object_class.gen_dynamodb_key(**key_args),
        )

    def get(self, connection_id: str) -> Optional[WebsocketConnection]:
        """
        Get a websocket connection by its id.

        Keyword arguments:
        connection_id -- The id of the websocket connection to get.
        """
        return self.get_object(partition_key_value=connection_id)

    def put(self, websocket_connection: WebsocketConnection) -> None:
        """
        Put a websocket connection into the table.

        Keyword arguments:
        websocket_connection -- The websocket connection to put.
        """
        return self.put_object(websocket_connection)