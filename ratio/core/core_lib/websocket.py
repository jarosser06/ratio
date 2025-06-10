"""
Client library for managing open WebSocket connections and sending messages.

Minimally needs resource_name "websocket_api" and resource_type "RATIO_CUSTOM_POLICY" for
access.
"""
import json
import logging

from typing import Union, Dict, Any

import boto3

from botocore.exceptions import ClientError as BotoClientError

from ratio.core.tables.websocket_connections.client import WebsocketConnectionsTableClient


class WebSocketConnectionNotFoundError(Exception):
    """Raised when a WebSocket connection ID is not found in the table"""
    pass


class WebSocketSendError(Exception):
    """Raised when sending a WebSocket message fails"""
    pass


class WebSocketMessenger:
    """
    A class for sending messages to a specific WebSocket connection.
    
    Caches connection details and API client on initialization for efficient messaging.
    """

    def __init__(self, connection_id: str):
        """
        Initialize the messenger for a specific WebSocket connection.

        Keyword arguments:
        connection_id -- The WebSocket connection ID

        Raises:
        WebSocketConnectionNotFoundError -- If the connection_id is not found in the table
        """
        self.connection_id = connection_id

        # Look up and cache connection details
        ws_tbl_client = WebsocketConnectionsTableClient()

        self.websocket_conn = ws_tbl_client.get(connection_id=connection_id)

        if not self.websocket_conn:
            raise WebSocketConnectionNotFoundError(
                f"WebSocket connection {connection_id} not found in table"
            )

        # Create and cache the API Gateway Management API client
        endpoint_url = f"https://{self.websocket_conn.domain_name}/{self.websocket_conn.stage}"

        self.api_client = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=endpoint_url
        )

        logging.debug(f"WebSocketMessenger initialized for connection {connection_id}")

    def send_message(self, data: Union[Dict, str, Any]) -> None:
        """
        Send a message to the WebSocket connection.

        Keyword arguments:
        data -- The data to send (will be JSON encoded if it's a dict)

        Raises:
        WebSocketSendError -- If sending the message fails
        """
        try:
            # Convert to string if needed
            if isinstance(data, dict):
                message_body = json.dumps(data)

            else:
                message_body = str(data)

            self.api_client.post_to_connection(
                ConnectionId=self.connection_id,
                Data=message_body.encode('utf-8')
            )

            logging.debug(f"Message sent to WebSocket connection {self.connection_id}")

        except BotoClientError as e:
            logging.error(f"Failed to send WebSocket message to {self.connection_id}: {e}")
            raise WebSocketSendError(f"Failed to send message to connection {self.connection_id}: {e}")

        except Exception as e:
            logging.error(f"Unexpected error sending WebSocket message to {self.connection_id}: {e}")
            raise WebSocketSendError(f"Unexpected error sending message to connection {self.connection_id}: {e}")

    def send_error(self, message: Union[str, Dict], status_code: int = 500) -> None:
        """
        Send an error message to the WebSocket connection in the standard error format.

        Keyword arguments:
        message -- The error message or dict to send
        status_code -- The status code for the error, defaults to 500

        Raises:
        WebSocketSendError -- If sending the message fails
        """
        error_body = {
            "error": True,
            "original_body": message,
            "status_code": status_code,
        }

        self.send_message(error_body)

    def close_connection(self) -> None:
        """
        Close the WebSocket connection and remove it from the table.

        Raises:
        WebSocketSendError -- If closing the connection fails
        """
        try:
            # Close the connection via API Gateway
            self.api_client.delete_connection(ConnectionId=self.connection_id)

            logging.debug(f"WebSocket connection {self.connection_id} closed via API Gateway")

        except BotoClientError as e:
            logging.error(f"Failed to close WebSocket connection {self.connection_id}: {e}")

            raise WebSocketSendError(f"Failed to close connection {self.connection_id}: {e}")

        except Exception as e:
            logging.error(f"Unexpected error closing WebSocket connection {self.connection_id}: {e}")

            raise WebSocketSendError(f"Unexpected error closing connection {self.connection_id}: {e}")

        try:
            # Remove from the connections table
            ws_tbl_client = WebsocketConnectionsTableClient()

            ws_tbl_client.delete_by_id(connection_id=self.connection_id)

            logging.debug(f"WebSocket connection {self.connection_id} removed from table")

        except Exception as e:
            # Don't raise here since the connection is already closed
            logging.warning(f"Failed to remove connection {self.connection_id} from table: {e}")