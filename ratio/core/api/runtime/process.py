"""
Tool API
"""
import logging

from typing import Dict

from da_vinci.core.global_settings import setting_value

from da_vinci.core.immutable_object import ObjectBody

from ratio.core.core_lib.client import RatioInternalClient
from ratio.core.core_lib.factories.api import ChildAPI, Route
from ratio.core.core_lib.jwt import JWTClaims, InternalJWTManager

from ratio.core.services.process_manager.request_definitions import (
    DescribeProcessRequest,
    ExecuteToolRequest,
    ListProcessesRequest,
    ValidateToolDefinitionRequest,
)

from ratio.core.tables.entities.client import EntitiesTableClient


class ProcessAPI(ChildAPI):
    """
    Process Manager API Proxy API Definition
    """
    routes = [
        Route(
            path="/process/execute",
            method_name="process_request",
            request_body_schema=ExecuteToolRequest,
        ),
        Route(
            path="/process/describe_process",
            method_name="process_request",
            request_body_schema=DescribeProcessRequest,
        ),
        Route(
            path="/process/list_processes",
            method_name="process_request",
            request_body_schema=ListProcessesRequest,
        ),
        Route(
            path="/process/schedule_execution",
            method_name="not_implemented",
            request_body_schema=None,
        ),
        Route(
            path="/process/validate_definition",
            method_name="process_request",
            request_body_schema=ValidateToolDefinitionRequest,
        )
    ]

    def process_request(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Execute an process request against the process manager.

        Keyword arguments:
        request_body -- The request body
        request_context -- The request context
        """
        execute_as = request_body.get("execute_as")

        claims = JWTClaims.from_claims(claims=request_context['request_claims'])

        token = request_context["signed_token"]

        if execute_as:
            logging.debug(f"Executing tool flag set to {execute_as}")

            if not claims.is_admin:
                logging.debug(f"Requestor is not admin, cannot execute tool as another user")

                return self.respond(
                    body={"message": "unauthorized to execute tool as another user"},
                    status_code=403,
                )

            logging.debug(f"Requestor is admin, executing tool as {execute_as}")

            jwt_manager = InternalJWTManager(
                expiry_hours=setting_value(namespace="ratio::core", setting_key="token_active_hours"),
                kms_key_id=setting_value(namespace="ratio::core", setting_key="internal_signing_kms_key_id"),
            )

            logging.debug(f"Looking for entity id: {execute_as}")

            entities_client = EntitiesTableClient()

            entity = entities_client.get(entity_id=execute_as)

            if not entity:
                logging.debug(f"Entity not found: {execute_as}")

                return self.respond(status_code=403, body={"message": "execute_as entity not found"})

            global_admin_entity = setting_value(
                namespace="ratio::core",
                setting_key="admin_entity_id",
            )

            global_admin_group = setting_value(
                namespace="ratio::core",
                setting_key="admin_group_id",
            )

            entity_is_admin = entity.entity_id == global_admin_entity or global_admin_group in entity.groups

            token, _ = jwt_manager.create_token(
                authorized_groups=entity.groups,
                entity=entity.entity_id,
                custom_claims={
                    "auth_method": "challenge_response",
                    "entity_impersonation": True,
                    "original_entity": claims.entity,
                },
                home=entity.home_directory,
                primary_group=entity.primary_group_id,
                is_admin=entity_is_admin,
            )

        tool_client = RatioInternalClient(
            service_name="process_manager",
            token=token,
        )

        path = request_context["path"].replace("/process", "")

        logging.debug(f"Calling tool manager {path} with request body: {request_body.to_dict()}")

        logging.debug(f"Calling tool manager with token: {token}")

        response = tool_client.request(path=path, request=request_body)

        return self.respond(
            body=response.response_body,
            status_code=response.status_code,
        )