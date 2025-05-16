"""
API Constructor
"""
import logging
import traceback

from dataclasses import dataclass
from typing import Dict, List, Union, Type

from da_vinci.core.immutable_object import (
    InvalidObjectSchemaError,
    MissingAttributeError,
    ObjectBody,
    ObjectBodySchema,
)

from da_vinci.exception_trap.client import ExceptionReporter

from ratio.core.core_lib.jwt import InternalJWTManager, JWTVerificationException
from ratio.core.core_lib.secrets import SSMSecretManager

AUTH_HEADER = "x-ratio-authorization"


class InvalidPathError(ValueError):
    def __init__(self, path: str):
        super().__init__(f"\"{path}\" path not found in route map.")


@dataclass
class Route:
    path: str
    method_name: str
    requires_auth: bool = False
    requires_group_id: str = None
    request_body_schema: Type[ObjectBodySchema] = None


class ChildAPI:
    routes: List[Route] = []

    def  __init__(self):
        self._route_map = {route.path: route for route in self.routes}

    def execute_path(self, path: str, **kwargs) -> Dict:
        """
        Execute a path

        Keyword arguments:
        path -- The path
        """
        # Temporary it's not secure
        logging.debug(f"Executing path: {path} with kwargs: {kwargs}")

        if path not in self._route_map:
            raise InvalidPathError(path)

        route_value = self._route_map[path]

        headers = kwargs.get("_headers")

        # Remove headers from kwargs
        if headers:
            del kwargs["_headers"]

        request_context = {}

        if not headers or AUTH_HEADER not in headers:
            if route_value.requires_auth:
                return self.respond(
                    body={"message": "unauthorized"},
                    status_code=401
                )

        elif headers and AUTH_HEADER in headers:
            auth_header = headers[AUTH_HEADER]

            # Verify the JWT token
            try:
                verified_token = InternalJWTManager.verify_token(token=auth_header)
            
            except JWTVerificationException as jwt_err:
                logging.error(f"JWT verification error: {jwt_err}")

                return self.respond(
                    body={"message": "unauthorized"},
                    status_code=401
                )

            request_context = {
                "path": path,
                "request_claims": verified_token.to_dict(),
                "signed_token": auth_header,
            }

        if route_value.request_body_schema:
            secret_mgr = SSMSecretManager()

            try:
                obj_body = ObjectBody(
                    body=kwargs, schema=route_value.request_body_schema,
                    secret_masking_fn=secret_mgr.mask_secret
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

    def respond(self, body: Union[Dict, str], status_code: int, headers: Dict = None) -> Dict:
        """
        Returns an API Gateway response.

        Keyword arguments:
        body -- The body of the response.
        status_code -- The status code of the response.
        headers -- The headers of the, optional.
        """

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

    def __init__(self, child_apis: List[ChildAPI], function_name: str):
        self.child_apis = child_apis

        for child_api in self.child_apis:
            self.routes.extend(
                [Route(path=r.path, method_name=child_api) for r in child_api.routes]
            )

        self.function_name = function_name

        super().__init__()

    def execute_path(self, path: str, **kwargs) -> Dict:
        """
        Execute a path

        Keyword arguments:
        path -- The path
        """
        if not self.has_route(path):
            return self.respond(
                body={"message": f"{path} route not found"},
                status_code=404
            )

        route_klass = self.route_value(path).method_name

        initialized_obj = route_klass()

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