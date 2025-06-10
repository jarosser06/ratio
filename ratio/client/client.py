import base64
import json
import logging
import threading

from datetime import datetime, UTC as utc_tz
from enum import StrEnum
from typing import Any, List, Optional, Union, Type

import websocket

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

from da_vinci.core.client_base import RESTClientBase, RESTClientResponse
from da_vinci.core.resource_discovery import ResourceDiscovery


class RequestAttributeError(Exception):
    def __init__(self, attribute_name: str, error: str = "missing required attribute"):
        """
        A custom exception for missing required request attributes.

        Keyword arguments:
        attribute_name -- The name of the attribute that is missing
        """
        self.attribute_name = attribute_name

        super().__init__(f"{error}: {attribute_name}")


class RequestAttributeType(StrEnum):
    ANY = 'ANY'
    BOOLEAN = 'BOOLEAN'
    DATETIME = 'DATETIME'
    FLOAT = 'FLOAT'
    LIST = 'LIST'
    INTEGER = 'INTEGER'
    OBJECT = 'OBJECT'
    OBJECT_LIST = 'OBJECT_LIST'
    STRING = 'STRING'


class RequestBodyAttribute:
    def __init__(self, name: str, attribute_type: Union[RequestAttributeType, Type] = RequestAttributeType.STRING,
                 attribute_subtype: Optional[Union[RequestAttributeType, Type]] = None, default: Optional[str] = None,
                 immutable_default: Optional[str] = None, optional: Optional[bool] = False,
                 required_if_attrs_not_set: Optional[List[str]] = None,
                 supported_request_body_types: Optional[Union[Type["RequestBody"], List[Type["RequestBody"]]]] = None):
        """
        Initialize the request body attribute

        Keyword arguments:
        name -- The name of the attribute
        attribute_type -- The type of the attribute
        attribute_subtype -- The subtype of the attribute
        default -- The default value of the attribute
        immutable_default -- The immutable default value of the attribute
        optional -- Whether the attribute is optional
        required_if_attrs_not_set -- A list of attributes that must be set for this attribute to be required
        supported_request_body_types -- The supported request body types for the attribute
        """
        self.name = name

        self.attribute_type = attribute_type

        self.attribute_subtype = attribute_subtype

        self.default = default

        self.immutable_default = immutable_default

        self.optional = optional

        self.required_if_attrs_not_set = required_if_attrs_not_set

        if isinstance(supported_request_body_types, str):
            supported_request_body_types = [supported_request_body_types]

        self.supported_request_body_types = supported_request_body_types

    def validate_type(self, value: Any):
        """
        Validate the type of a value. Override this method to add custom validation logic.

        Keyword arguments:
        value -- The value to validate
        """
        if self.attribute_type  == RequestAttributeType.ANY:
            return True

        elif self.attribute_type == RequestAttributeType.BOOLEAN:
            return isinstance(value, bool)

        # Supports both datetime objects and strings in the format 'YYYY-MM-DD HH:MM:SS'
        elif self.attribute_type == RequestAttributeType.DATETIME:
            if isinstance(value, datetime):
                return True

            try:
                datetime.fromisoformat(value)

                return True

            except ValueError:
                return False

        elif self.attribute_type == RequestAttributeType.FLOAT:
            return isinstance(value, float)

        elif self.attribute_type == RequestAttributeType.LIST:
            return isinstance(value, list)

        elif self.attribute_type == RequestAttributeType.INTEGER:
            return isinstance(value, int)

        elif self.attribute_type == RequestAttributeType.OBJECT:
            if isinstance(value, RequestBody):
                if self.supported_request_body_types is not None:
                    return isinstance(value, tuple(self.supported_request_body_types))

                return True

            return isinstance(value, dict)

        elif self.attribute_type == RequestAttributeType.OBJECT_LIST:
            if not isinstance(value, list):
                return False

            for item in value:
                if isinstance(item, dict):
                    return True

                if isinstance(item, RequestBody):
                    if self.supported_request_body_types:
                        return isinstance(item, self.supported_request_body_types)

                    return True

        elif self.attribute_type == RequestAttributeType.STRING:
            return isinstance(value, str)

        return False


class RequestBody:
    """
    Represents a request body for a request to the API

    Keyword arguments:
    attributes -- The attributes of the request
    path -- The path of the request
    """
    attribute_definitions: List[RequestBodyAttribute]
    path: str = None
    requires_auth: bool = False
    supports_websockets: bool = False

    def __init__(self, **kwargs):
        """
        Initialize the request body.

        Keyword arguments:
        kwargs -- The attributes of the request
        """
        self.attributes = {}

        for attr in self.attribute_definitions:
            attr_val = kwargs.get(attr.name, attr.default)

            conditionally_required = False

            if attr.required_if_attrs_not_set:
                for required_attr in attr.required_if_attrs_not_set:

                    if required_attr not in kwargs:
                        conditionally_required = True

                        break

            if attr.immutable_default:
                if attr_val:
                    raise RequestAttributeError(attribute_name=attr.name, error="unable to write over immutable value")

                attr_val = attr.immutable_default

            elif not attr_val:
                if attr.optional or not conditionally_required:
                    attr_val = attr.default

                else:
                    raise RequestAttributeError(attribute_name=attr.name)

            elif attr_val:
                if not attr.validate_type(attr_val):
                    raise RequestAttributeError(attribute_name=attr.name, error="invalid type for attribute")

            if attr.attribute_type == RequestAttributeType.DATETIME and isinstance(attr_val, datetime):
                # Convert datetime objects to strings to ensure they are serialized correctly
                attr_val = attr_val.isoformat()

            self.attributes[attr.name] = attr_val

    def to_dict(self):
        """
        Return the object as a dictionary. Supports nested RequestBody objects.
        """
        prepped_attributes = {}

        for key, value in self.attributes.items():
            if isinstance(value, RequestBody):
                prepped_attributes[key] = value.to_dict()

        return self.attributes

    @property
    def websocket_action(self) -> str:
        """
        Convert a REST path to WebSocket action name.

        "/process/execute" -> "ProcessExecute"
        "/process/list_processes" -> "ProcessListProcesses"

        Keyword arguments:
        path -- The REST API path (e.g., "/process/execute")
        """
        # Remove leading slash and split on /
        parts = [part for part in self.path.split('/') if part]

        # Capitalize each part and handle underscores
        route_parts = []

        for part in parts:
            # Split on underscores and capitalize each word
            words = part.split('_')

            capitalized_words = [word.capitalize() for word in words]

            route_parts.append(''.join(capitalized_words))

        return ''.join(route_parts)


class ChallengeRequest(RequestBody):
    path = '/auth/challenge'

    attribute_definitions = [
        RequestBodyAttribute(
            name="entity_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        )
    ]

    def __init__(self, entity_id: str):
        """
        Initialize the challenge request

        Keyword arguments:
        entity_id -- The entity ID to be used for the challenge
        """
        super().__init__(entity_id=entity_id,)


class TokenRequest(RequestBody):
    """
    Request a token using a challenge and signatures
    """
    path = '/auth/token'
    
    attribute_definitions = [
        RequestBodyAttribute(
            name="challenge",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="entity_signature",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="system_signature",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, challenge: str, entity_signature: str, system_signature: str):
        """
        Initialize the token request

        Keyword arguments:
        challenge -- The challenge to verify
        entity_signature -- The signature of the challenge by the entity
        system_signature -- The signature of the challenge by the system
        """
        super().__init__(
            challenge=challenge,
            entity_signature=entity_signature,
            system_signature=system_signature
        )


class ClientJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()

        elif isinstance(obj, RequestBody):
            return obj.to_dict()

        return json.JSONEncoder.default(self, obj)


class Ratio(RESTClientBase):
    def __init__(self, app_name: Optional[str] = None, auth_header = "x-ratio-authorization",
                 deployment_id: Optional[str] = None, entity_id: Optional[str] = None, private_key: Optional[bytes] = None,
                 token: Optional[str] = None, token_expires: Optional[datetime] = None):
        """
        Initialize the Ratio client.

        Keyword arguments:
        app_name -- The name of the application
        auth_header -- The authentication header to use for requests
        deployment_id -- The ID of the deployment
        private_key -- The private key for signing requests, this is required for all authenticated requests
        entity_id -- The entity ID that the token belongs to
        token -- The token to use for authentication
        token_expires -- The expiration date of the token
        """
        super().__init__(
            resource_name='api',
            app_name=app_name,
            deployment_id=deployment_id,
            raise_on_failure=False,
            resource_discovery_storage="dynamodb",
        )

        # Initialize Websocket attributes
        self.ws = None

        self.ws_connected = False

        self._ws_url = None

        self.auth_header = auth_header

        self._acquired_token = token

        self.token_expires = token_expires

        if self._acquired_token and not token_expires:
            raise ValueError('token_expires is required if token is provided')

        if not token and (private_key and entity_id):
            self._acquired_token = self.refresh_token(entity_id=entity_id, private_key=private_key) 

    def _discover_websocket_url(self) -> str:
        """
        Discover WebSocket API endpoint using ResourceDiscovery
        """
        if self._ws_url:
            return self._ws_url

        discovery = ResourceDiscovery(
            resource_type="RATIO_WEBSOCKET_API",
            resource_name="ws_api",
            app_name=self.app_name,
            deployment_id=self.deployment_id,
            storage_solution=self.resource_discovery_storage
        )

        self._ws_url = discovery.endpoint_lookup()

        return self._ws_url

    def refresh_token(self, entity_id: str, private_key: Optional[bytes] = None) -> None:
        """
        Get the token for the client, this is not idempotent and will always return a new token.

        Keyword arguments:
        entity_id -- The entity ID that the token belongs to
        private_key -- The private key to use for signing the token
        """
        challenge_req = ChallengeRequest(entity_id=entity_id)

        challenge_resp = self.request(request=challenge_req)

        logging.debug(f"Challenge response: {challenge_resp}")

        challenge = challenge_resp.response_body["challenge"]

        system_signature = challenge_resp.response_body["system_signature"]

        self_signature = self.sign_message_rsa(
            private_key_pem=private_key,
            message=challenge
        )

        logging.debug(f"Signature: {self_signature}")

        token_req = TokenRequest(
            challenge=challenge,
            entity_signature=self_signature,
            system_signature=system_signature,
        )

        token_resp = self.request(request=token_req)

        self._acquired_token = token_resp.response_body["token"]

        self.token_expires = datetime.fromisoformat(token_resp.response_body["expires_at"])

        logging.debug(f"Token expires: {self.token_expires}")

    @staticmethod
    def sign_message_rsa(private_key_pem: bytes, message: str):
        """
        Sign a message using an RSA private key.

        Keyword arguments:
        private_key_pem -- The RSA private key in PEM format
        message -- The message to be signed
        """
        # Load the private key from PEM format
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None
        )

        # Sign the message
        signature = private_key.sign(
            message.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        return base64.b64encode(signature).decode('utf-8')

    def request(self, request: RequestBody, raise_for_status: Optional[bool] = True) -> RESTClientResponse:
        """
        Make a request to the Ratio API.

        Keyword arguments:
        request -- The request body to send to the API
        raise_for_status -- Whether to raise an exception for non-200 status codes
        """
        if not request.path:
            raise ValueError('request object does not have a defined path')

        request_body = json.dumps(request, cls=ClientJSONEncoder)

        headers = {}

        if self._acquired_token and self.token_expires > datetime.now(tz=utc_tz):
            logging.debug("Setting auth header")

            headers[self.auth_header] = self._acquired_token

        elif request.requires_auth and not self._acquired_token:
            raise ValueError('token is required for authenticated requests')

        response = self.post(
            body=json.loads(request_body),
            headers=headers,
            path=request.path,
        )

        if response.status_code >= 400 and raise_for_status:
            logging.error(f"Error response: {response.status_code} - {response.response_body}")

            raise ValueError(f"Error response: {response.status_code} - {response.response_body}")

        return response

    def connect_websocket(self, connect_timeout: Optional[float] = None, on_close: Optional[callable] = None,
                          on_error: Optional[callable] = None, on_message: Optional[callable] = None,
                          on_open: Optional[callable] = None):
        """
        Connect to WebSocket

        Keyword arguments:
        connect_timeout -- Timeout for the WebSocket connection
        on_open -- Callback function for when the WebSocket connection is opened
        on_close -- Callback function for when the WebSocket connection is closed
        on_message -- Callback function for when a message is received
        on_error -- Callback function for when an error occurs
        """
        if self.ws_connected or self.ws:
            return

        ws_url = self._discover_websocket_url()

        headers = {}

        if self._acquired_token:
            headers[self.auth_header] = self._acquired_token

        connect_event = None

        if connect_timeout is not None:
            connect_event = threading.Event()

        def internal_on_open(ws):
            self.ws_connected = True

            if connect_event:
                connect_event.set()

            if on_open:
                on_open(ws)

        def internal_on_close(ws, close_status_code, close_msg):
            self.ws_connected = False

            if on_close:
                on_close(ws, close_status_code, close_msg)

        self.ws = websocket.WebSocketApp(
            url=ws_url,
            header=headers,
            on_open=internal_on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=internal_on_close,
        )

        threading.Thread(target=self.ws.run_forever, daemon=True).start()

        if connect_timeout is not None:
            if not connect_event.wait(timeout=connect_timeout):
                raise ConnectionError(f"WebSocket connection timeout after {connect_timeout} seconds")

    def close_websocket(self):
        """
        Close the WebSocket connection
        """
        if self.ws:
            self.ws.close()

            self.ws = None

            self.ws_connected = False

    def send_message(self, message: RequestBody):
        """
        Send message over WebSocket

        Keyword arguments:
        message -- The message to send, must be a subclass of RequestBody that supports WebSocket
        """
        if not message.supports_websockets:
            raise ValueError(f"Message type {type(message).__name__} does not support WebSocket")

        if not self.ws:
            self.connect_websocket()

        if not self.ws_connected:
            raise ConnectionError("WebSocket not connected yet")

        data = {"action": message.websocket_action, **message.to_dict()}

        self.ws.send(json.dumps(data, cls=ClientJSONEncoder)) 