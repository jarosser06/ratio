"""
API Constructor
"""
import json
import logging
import re
import traceback

from dataclasses import dataclass
from typing import Dict, List, Union, Type

import boto3

from botocore.exceptions import ClientError as BotoClientError

from da_vinci.core.immutable_object import (
    InvalidObjectSchemaError,
    MissingAttributeError,
    ObjectBody,
    ObjectBodySchema,
)

from da_vinci.exception_trap.client import ExceptionReporter
from da_vinci.core.global_settings import setting_value

from ratio.core.core_lib.jwt import InternalJWTManager, JWTVerificationException

from ratio.core.tables.entities.client import Entity, EntitiesTableClient

from ratio.core.tables.groups.client import Group, GroupsTableClient

from ratio.core.tables.websocket_connections.client import (
    WebsocketConnection,
    WebsocketConnectionsTableClient,
)


AUTH_HEADER = "x-ratio-authorization"


class InvalidPathError(ValueError):
    def __init__(self, path: str):
        super().__init__(f"\"{path}\" path not found in route map.")


class UnauthorizedError(Exception):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message)


@dataclass
class Route:
    path: str
    method_name: str
    requires_auth: bool = True
    requires_group_id: str = None
    request_body_schema: Type[ObjectBodySchema] = None
    supports_websockets: bool = False


class Authorizer:
    """Base authorizer interface"""

    def __call__(self, headers: Dict) -> Union[Dict, None]:
        """
        Extract and validate auth context from headers

        Keyword arguments:
        headers -- The headers dictionary

        Returns:
            Dict with auth context if auth provided and valid
            None if no auth provided

        Raises:
            Exception if auth provided but invalid (security issue)
        """
        raise NotImplementedError


class JWTAuthorizer(Authorizer):
    """Standard JWT-only authorizer"""

    def __call__(self, headers: Dict) -> Union[Dict, None]:
        if not headers or AUTH_HEADER not in headers:
            return None

        auth_header = headers[AUTH_HEADER]

        try:
            verified_token = InternalJWTManager.verify_token(token=auth_header)

            return {
                "request_claims": verified_token.to_dict(),
                "signed_token": auth_header,
            }

        except JWTVerificationException as jwt_err:
            logging.error(f"JWT verification error: {jwt_err}")

            raise UnauthorizedError()


class OAuthJWTAuthorizer(Authorizer):
    """OAuth + JWT combined authorizer for public APIs"""

    def _extract_oauth_token(self, headers: Dict) -> Union[str, None]:
        """
        Extract OAuth bearer token from Authorization header

        Keyword arguments:
        headers -- The headers dictionary containing Authorization header 
        """
        if not headers:
            return None

        auth_header = headers.get('authorization') or headers.get('Authorization')

        if auth_header and auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer '

        return None

    def _ensure_oauth_entity(self, cognito_username: str) -> str:
        """
        Create or get OAuth entity for Cognito user

        Keyword arguments: 
        cognito_username -- The username from Cognito
        client_id -- The client ID for the OAuth application, defaults to "default"
        """
        entity_id = cognito_username

        entities_client = EntitiesTableClient()

        existing_entity = entities_client.get(entity_id=entity_id)

        if existing_entity:
            return entity_id

        groups_client = GroupsTableClient()

        oauth_group_id = "oauth_users"

        existing_group = groups_client.get(group_id=oauth_group_id)

        # Create Oauth group if it doesn't exist
        if not existing_group:
            mcp_group = Group(
                group_id=oauth_group_id,
                description="Oauth API Users",
                members=[entity_id]
            )

            groups_client.put(group=mcp_group)

        else:
            if entity_id not in (existing_group.members or []):
                existing_group.members = (existing_group.members or []) + [entity_id]

                groups_client.put(group=existing_group)

        # Create entity
        entity = Entity(
            entity_id=entity_id,
            description=f"OAuth entity for {cognito_username}",
            groups=[oauth_group_id],
            primary_group_id=oauth_group_id,
            home_directory=f"/home/{entity_id}",
        )

        entities_client.put(entity=entity)

        return entity_id

    def _validate_oauth_and_create_jwt(self, token: str) -> str:
        """Validate OAuth token with Cognito and return internal JWT"""
        try:
            cognito_client = boto3.client('cognito-idp')

            # Validate with Cognito
            response = cognito_client.get_user(AccessToken=token)

            email = None

            for attr in response.get('UserAttributes', []):
                if attr['Name'] == 'email':
                    email = attr['Value']

                    break

            if not email:
                raise UnauthorizedError("Email not found")

            # Create/get entity
            entity_id = self._ensure_oauth_entity(email)

            # Create internal JWT
            jwt_manager = InternalJWTManager(
                kms_key_id=setting_value(namespace="ratio::core", setting_key="internal_signing_kms_key_id"),
                expiry_minutes=15,
            )

            internal_token, _ = jwt_manager.create_token(
                entity=entity_id,
                authorized_groups=["mcp_users"],
                primary_group="mcp_users", 
                home=f"/home/{entity_id}",
                custom_claims={
                    "auth_method": "oauth", 
                    "cognito_username": email
                }
            )

            return internal_token

        except BotoClientError as e:
            logging.error(f"Cognito validation failed: {e}")

            raise UnauthorizedError("Invalid OAuth token")

        except Exception as e:
            logging.error(f"OAuth processing failed: {e}")

            raise UnauthorizedError("OAuth processing failed")

    def __call__(self, headers: Dict) -> Union[Dict, None]:
        """
        Try OAuth first, then fall back to JWT

        Keyword arguments:
        headers -- The headers dictionary containing Authorization header
        """
        logging.debug(f"OAuthJWTAuthorizer called with headers: {headers}")

        if not headers:
            logging.debug("No headers provided, nothing to authorize")

            return None

        # Try OAuth Bearer token first
        oauth_token = self._extract_oauth_token(headers)

        if oauth_token:
            try:
                internal_jwt = self._validate_oauth_and_create_jwt(oauth_token)

                verified_token = InternalJWTManager.verify_token(token=internal_jwt)

                return {
                    "request_claims": verified_token.to_dict(),
                    "signed_token": internal_jwt,
                }

            except UnauthorizedError:
                raise  # Re-raise OAuth errors

            except Exception as e:
                logging.error(f"OAuth validation error: {e}")

                raise UnauthorizedError("OAuth validation failed")

        # Fall back to JWT auth (same logic as JWTAuthorizer)
        if AUTH_HEADER not in headers:
            logging.debug("No Authorization header found, nothing to authorize")

            return None

        auth_header = headers[AUTH_HEADER]

        try:
            verified_token = InternalJWTManager.verify_token(token=auth_header)

            return {
                "request_claims": verified_token.to_dict(),
                "signed_token": auth_header,
            }

        except JWTVerificationException as jwt_err:
            logging.error(f"JWT verification error: {jwt_err}")

            raise UnauthorizedError("Invalid JWT token")


def split_on_capital_letters(text: str) -> List[str]:
    """
    Split a string on capital letters.

    Keyword arguments:
    text -- The string to split
    """
    return re.split(r'(?=[A-Z])', text)[1:]  # Skip the first empty string


def websocket_client(socket_details: Dict) -> Union[Dict, None]:
    """
    Try to create a WebSocket client for API Gateway Management API

    If there is no websocket connection details, return None.

    Keyword arguments:
    socket_details -- The details of the WebSocket connection, including domain name and stage
    """
    domain_name = socket_details.get("domain_name")

    stage = socket_details.get("stage")

    return boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=f"https://{domain_name}/{stage}",
    )


class ChildAPI:
    routes: List[Route] = []

    def  __init__(self, authorizer: Authorizer = None):
        """
        Initializes the ChildAPI with an optional authorizer.

        Keyword arguments:
        authorizer -- An instance of Authorizer to handle authorization logic
        """
        self.authorizer = authorizer or OAuthJWTAuthorizer()

        self.websocket_details = {}

        self._route_map = {route.path: route for route in self.routes}

    def execute_path(self, path: str, **kwargs) -> Dict:
        """
        Execute a path

        Keyword arguments:
        path -- The path
        """
        if path not in self._route_map:
            raise InvalidPathError(path)

        route_value = self._route_map[path]

        # Check if the request is a WebSocket request
        if "_websocket_details" in kwargs:
            logging.debug(f"WebSocket request detected for path: {path}")

            if not route_value.supports_websockets:
                return self.respond(
                    body={"message": "WebSocket support not enabled for this route ... use HTTP instead"},
                    status_code=400
                )

            self.websocket_details = kwargs["_websocket_details"]

            # Lookup information in the WebSocket connections table
            ws_tbl_client = WebsocketConnectionsTableClient()

            websocket_conn = ws_tbl_client.get(
                connection_id=self.websocket_details["connection_id"]
            )

            if not websocket_conn:
                logging.warning(f"WebSocket connection {self.websocket_details["connection_id"]} not found")

                return self.respond(
                    body={"message": "WebSocket connection not found"},
                    status_code=404
                )

            request_context = {
                "path": path,
                "request_claims": websocket_conn.session_claims,
                "signed_token": websocket_conn.session_token,
                "websocket_details": self.websocket_details,
            }

        # Only handle authentication if not websocket request. Websocket authentication is handled during connection
        else:
            headers = kwargs.get("_headers")

            # Remove headers from kwargs
            if headers:
                del kwargs["_headers"]

            try:
                request_context = self.authorizer(headers)

            except UnauthorizedError as auth_err:
                logging.warning(f"Unauthorized access attempt to {path}: {auth_err}")

                return self.respond(body={"message": "unauthorized"}, status_code=401)

            if request_context:
                request_context["path"] = path

            else:
                if route_value.requires_auth:
                    logging.warning(f"Unauthorized access attempt to {path}")

                    return self.respond(
                        body={"message": "unauthorized"},
                        status_code=401
                    )

                request_context = {
                    "path": path,
                }

        if route_value.request_body_schema:
            try:
                obj_body = ObjectBody(
                    body=kwargs, schema=route_value.request_body_schema,
                )

            except MissingAttributeError as req_err:
                logging.error(f"Missing attribute error: {req_err}")

                return self.respond(
                    body={"message": str(req_err)},
                    status_code=400
                )

            except InvalidObjectSchemaError as inv_obj_err:
                logging.error(f"Invalid object schema error: {inv_obj_err}")

                return self.respond(
                    body={"message": str(inv_obj_err)},
                    status_code=400
                )

            logging.debug(f"Executing {route_value.method_name} with body {obj_body.to_dict()}")

            return getattr(self, route_value.method_name)(obj_body, request_context)

        # If no request body schema is provided, just pass an empty ObjectBody
        return getattr(self, route_value.method_name)(ObjectBody(), request_context)

    def has_route(self, path: str) -> bool:
        """
        Check if the path exists in the route map.

        Keyword arguments:
        path -- The path
        """
        return path in self._route_map

    def not_implemented_response(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Route for handling not implemented API calls

        Keyword arguments:
        request_body -- The request body
        request_context -- The request context, not used in this case
        """

        return self.respond(
            status_code=501,
            body={
                "message": "This API is not implemented yet.",
                "request_body": request_body.to_dict(),
            },
        )

    def respond(self, body: Union[Dict, str], status_code: int, headers: Dict = None) -> Union[Dict, None]:
        """
        Returns an API Gateway response and will try to send a WebSocket response if applicable.

        Will return None if the response is a WebSocket response that was successfully sent.

        Keyword arguments:
        body -- The body of the response.
        status_code -- The status code of the response.
        headers -- The headers of the, optional.
        """
        if isinstance(body, dict):
            body = json.dumps(body)

        if self.websocket_details:
            logging.debug(f"WebSocket response detected for connection ID: {self.websocket_details['connection_id']}")

            # If this is a WebSocket response, we need to use the WebSocket client
            ws_client = websocket_client(self.websocket_details)

            try:
                websocket_body = body

                # If the status code is 400 or less, we assume it's an error and send it as an error message
                if status_code >= 400:
                    websocket_body = json.dumps({
                        "error": True,
                        "original_body": body,
                        "status_code": status_code,
                    })

                ws_client.post_to_connection(
                    ConnectionId=self.websocket_details["connection_id"],
                    Data=websocket_body.encode('utf-8'),
                )

                return {
                    "statusCode": 200,
                    "body": ""
                }

            except Exception as excp:
                logging.error(f"Error sending WebSocket message: {excp}")

                return {
                    "body": json.dumps({"message": "Failed to send WebSocket message"}),
                    "statusCode": 500,
                }

        return {
            'body': body,
            'headers': headers,
            'statusCode': status_code,
        }

    def route_value(self, path: str) -> Route:
        """
        Get the value of a route.

        Keyword arguments:
        path -- The path
        """
        return self._route_map[path]


class ParentAPI(ChildAPI):
    routes: List[Route] = []

    def __init__(self, child_apis: List[ChildAPI], function_name: str, authorizer: Authorizer = None):
        """
        Initializes the ParentAPI with a list of child APIs and an optional authorizer.

        Keyword arguments:
        child_apis -- A list of ChildAPI instances to be included in the ParentAPI
        function_name -- The name of the function for exception reporting
        authorizer -- An instance of Authorizer to handle authorization logic, optional, defaults to OAuthJWTAuthorizer
        """
        self.child_apis = child_apis

        for child_api in self.child_apis:
            self.routes.extend(
                [Route(path=r.path, method_name=child_api) for r in child_api.routes]
            )

        self.function_name = function_name

        super().__init__(authorizer=authorizer)

    def execute_path_from_event(self, event: Dict) -> Dict:
        """
        Execute a path from an event

        Keyword arguments:
        event -- The event containing the path and other parameters
        """
        body = event.get("body")

        kwargs = {}

        if body:
            kwargs = json.loads(body)

        headers = event.get("headers", {})

        if headers:
            kwargs["_headers"] = headers

        path = event.get("rawPath")

        if "requestContext" in event:
            if "connectionId" in event["requestContext"]:
                logging.debug(f"Detected WebSocket connection ID: {event['requestContext']['connectionId']}")

                domain_name = event["requestContext"]["domainName"]

                stage = event['requestContext']['stage']

                kwargs["_websocket_details"] = {
                    "connection_id": event["requestContext"]["connectionId"],
                    "domain_name": domain_name,
                    "stage": stage,
                }

                route_key = event['requestContext']['routeKey']

                # Retrieve and store the Websocket session details
                if route_key == "$connect":
                    logging.debug("WebSocket connection attempt detected")

                    if not headers:
                        logging.warning("No headers provided for WebSocket connection attempt")

                        return self.respond(
                            body={"message": "unauthorized"},
                            status_code=401
                        )

                    request_context = self.authorizer(headers)

                    if not request_context:
                        logging.warning("Unauthorized connection attempt")

                        return self.respond(
                            body={"message": "unauthorized"},
                            status_code=401
                        )

                    session_claims = request_context["request_claims"]

                    session_token = request_context["signed_token"]

                    websocket_conn = WebsocketConnection(
                        connection_id=event["requestContext"]["connectionId"],
                        domain_name=domain_name,
                        session_claims=session_claims,
                        session_token=session_token,
                        stage=stage
                    )

                    ws_tbl_client = WebsocketConnectionsTableClient()

                    ws_tbl_client.put(websocket_conn)

                    return self.respond(body={"message": "Connection established"}, status_code=200)

                elif route_key == "$disconnect":
                    ws_tbl_client = WebsocketConnectionsTableClient()

                    connection_id = event["requestContext"]["connectionId"]

                    logging.debug(f"Disconnecting WebSocket connection ID: {connection_id}")

                    ws_tbl_client.delete_by_id(connection_id=connection_id)

                    return self.respond(
                        body={"message": "Connection closed"},
                        status_code=200,
                    )

                else:
                    # Going to try to extract the path from the route key. Expecting it to be
                    # in the format of "ProcessExecute" or "ProcessListProcesses"
                    path_parts = split_on_capital_letters(route_key)

                    service = path_parts[0].lower()

                    action = ''.join([part.lower() for part in path_parts[1:]])

                    path = f"/{service}/{action}"

                    logging.debug(f"Extracted path {path} from route key {route_key}")

        logging.debug(f"Executing path: {path}")

        if not path:
            logging.error("No path found, cannot execute")

            return self.respond(
                body={"message": "No path found in event"},
                status_code=500
            )

        return self.execute_path(path=path, **kwargs)

    def execute_path(self, path: str, **kwargs) -> Dict:
        """
        Execute a path

        Keyword arguments:
        path -- The path
        """
        if not self.has_route(path):
            logging.error(f"Path {path} not found in route map")

            return self.respond(
                body={"message": f"{path} route not found"},
                status_code=404
            )

        route_klass = self.route_value(path).method_name

        initialized_obj = route_klass(authorizer=self.authorizer)

        try:
            return initialized_obj.execute_path(path, **kwargs)

        except MissingAttributeError as req_err:
            logging.error(f"Missing attribute error: {req_err}")

            return self.respond(
                body={"message": str(req_err)},
                status_code=400
            )

        except InvalidPathError as inv_err:
            logging.error(f"Invalid path error: {inv_err}")

            return self.respond(
                body={"message": str(inv_err)},
                status_code=404
            )
        
        except Exception as excp:
            logging.error(f"Exception occurred: {excp}")

            reporter = ExceptionReporter()

            reporter.report(
                function_name=self.function_name,
                exception=str(excp),
                exception_traceback=traceback.format_exc(),
                originating_event=kwargs
            )

            return self.respond(
                body={"message": "internal error occurred"},
                status_code=500
            )