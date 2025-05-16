"""
CRUD API for managing subscriptions in the scheduler service.
"""
import logging

from datetime import datetime
from typing import Dict

from da_vinci.core.immutable_object import ObjectBody

from ratio.core.core_lib.client import RatioInternalClient
from ratio.core.core_lib.factories.api import ChildAPI, Route
from ratio.core.core_lib.jwt import JWTClaims

from ratio.core.services.storage_manager.request_definitions import (
    ValidateFileAccessRequest,
)

from ratio.core.services.scheduler.request_definitions import (
    CreateSubscriptionRequest,
    DeleteSubscriptionRequest,
    DescribeSubscriptionRequest,
    ListSubscriptionsRequest,
)

from ratio.core.services.scheduler.tables.subscriptions.client import (
    Subscription,
    SubscriptionsTableClient,
)


class CrudAPI(ChildAPI):
    routes = [
        Route(
            path="/create_subscription",
            method_name="create_subscription",
            request_body_schema=CreateSubscriptionRequest,
        ),
        Route(
            path="/delete_subscription",
            method_name="delete_subscription",
            request_body_schema=DeleteSubscriptionRequest,
        ),
        Route(
            path="/describe_subscription",
            method_name="describe_subscription",
            request_body_schema=DescribeSubscriptionRequest,
        ),
        Route(
            path="/list_subscriptions",
            method_name="list_subscriptions",
            request_body_schema=ListSubscriptionsRequest,
        ),
    ]

    def create_subscription(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Describe a process

        Keyword arguments:
        request_body -- The request body
        request_context -- The request context
        """
        claims = JWTClaims.from_claims(claims=request_context['request_claims'])

        if request_body["owner"] and not claims.is_admin:
            return self.respond(
                status_code=403,
                body={"message": "not permitted to create subscriptions on behalf of another entity"},
            )

        # Validate accces to the file path
        storage_client = RatioInternalClient(
            service_name="storage_manager",
            token=request_context["signed_token"],
        )

        validate_file_access_request = ObjectBody(
            body={
                "file_path": request_body["agent_definition"],
                "requested_permission_names": ["execute"],
            },
            schema=ValidateFileAccessRequest,
        )

        validation_response = storage_client.request(
            path="/validate_file_access",
            request=validate_file_access_request,
        )

        logging.debug(f"Validation response: {validation_response}")

        if validation_response.status_code == 404:
            logging.debug(f"Agent definition path does not exist: {request_body["agent_definition"]}")

            return self.respond(
                body={"message": f"agent {request_body["agent_definition"]} definition file not found"},
                status_code=404,
            )

        entity_has_access = validation_response.response_body.get("entity_has_access", False)

        logging.debug(f"Entity has access to agent definition path: {entity_has_access}")

        if not entity_has_access:
            logging.debug(f"Requestor does not have access to agent definition path: {request_body["agent_definition"]}")

            return self.respond(
                body={"message": f"unauthorized to access agent definition path {request_body["agent_definition"]}"},
                status_code=403,
            )

        owner = request_body.get("owner", default_return=claims.entity)

        expiration = request_body.get("expiration")

        if expiration:
            expiration = datetime.fromisoformat(expiration)

        # Create the subscription
        subscription = Subscription(
            agent_definition=request_body["agent_definition"],
            execution_working_directory=request_body.get("execution_working_directory"),
            expiration=expiration,
            full_path_hash=Subscription.create_full_path_hash_from_path(request_body["file_path"]),
            file_event_type=request_body["file_event_type"],
            file_path=request_body["file_path"],
            file_type=request_body.get("file_type"),
            process_owner=owner,
            single_use=request_body.get("single_use"),
        )

        # Create the subscription in the database
        subscription_client = SubscriptionsTableClient()

        subscription_client.put(subscription=subscription)

        return self.respond(
            body=subscription.to_dict(json_compatible=True),
            status_code=201,
        )

    def delete_subscription(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Delete a subscription

        Keyword arguments:
        request_body -- The request body
        request_context -- The request context
        """
        claims = JWTClaims.from_claims(claims=request_context['request_claims'])

        subscription_id = request_body["subscription_id"]

        # Delete the subscription
        subscription_client = SubscriptionsTableClient()

        subscription = subscription_client.get_by_subscription_id(
            subscription_id=subscription_id,
        )

        if not subscription:
            return self.respond(
                body={"message": f"subscription {subscription_id} not found"},
                status_code=404,
            )

        if subscription.process_owner != claims.entity and not claims.is_admin:
            return self.respond(
                body={"message": "not permitted to delete subscription"},
                status_code=403,
            )

        # Delete the subscription from the database
        subscription_client.delete(subscription=subscription)

        return self.respond(
            body={"message": f"subscription {subscription_id} deleted"},
            status_code=200,
        )

    def describe_subscription(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Describe a subscription

        Keyword arguments:
        request_body -- The request body
        request_context -- The request context
        """
        claims = JWTClaims.from_claims(claims=request_context['request_claims'])

        subscription_id = request_body["subscription_id"]

        # Describe the subscription
        subscription_client = SubscriptionsTableClient()

        subscription = subscription_client.get_by_subscription_id(
            subscription_id=subscription_id,
        )

        if not subscription:
            return self.respond(
                body={"message": f"subscription {subscription_id} not found"},
                status_code=404,
            )

        if subscription.process_owner != claims.entity and not claims.is_admin:
            return self.respond(
                body={"message": "not authorized"},
                status_code=403,
            )

        return self.respond(
            body=subscription.to_dict(json_compatible=True),
            status_code=200,
        )

    def list_subscriptions(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        List subscriptions

        Keyword arguments:
        request_body -- The request body
        request_context -- The request context
        """
        claims = JWTClaims.from_claims(claims=request_context['request_claims'])

        if request_body["owner"] and not claims.is_admin:
            return self.respond(
                body={"message": "not permitted to list subscriptions on behalf of another entity"},
                status_code=403,
            )

        owner = request_body.get("owner", default_return=claims.entity)

        # List subscriptions
        subscription_client = SubscriptionsTableClient()

        subscriptions = subscription_client.list_by_file_path_or_owner(
            file_path=request_body.get("file_path"),
            process_owner=owner,
        )

        return self.respond(
            body=[subscription.to_dict(json_compatible=True) for subscription in subscriptions],
            status_code=200,
        )