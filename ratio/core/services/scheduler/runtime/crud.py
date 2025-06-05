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

from ratio.core.services.scheduler.tables.filesystem_subscriptions.client import (
    FilesystemSubscription,
    FilesystemSubscriptionsTableClient,
)

from ratio.core.services.scheduler.tables.general_subscriptions.client import (
    GeneralSubscription,
    GeneralSubscriptionsTableClient,
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

    def _normalize_filesystem_subscription(self, fs_subscription: Dict) -> Dict:
        """
        Normalize filesystem subscription to match general subscription format
        """
        normalized = fs_subscription.copy()

        # Add event_type based on file_event_type
        file_event_type = fs_subscription.get("file_event_type", "updated")

        normalized["event_type"] = f"filesystem_{file_event_type}"

        # Move filesystem-specific fields to filter_conditions
        filter_conditions = {}

        if "file_path" in fs_subscription:
            filter_conditions["file_path"] = fs_subscription["file_path"]

        if "file_event_type" in fs_subscription:
            filter_conditions["file_event_type"] = fs_subscription["file_event_type"]

        if "file_type" in fs_subscription and fs_subscription["file_type"]:
            filter_conditions["file_type"] = fs_subscription["file_type"]

        normalized["filter_conditions"] = filter_conditions

        # Remove the raw filesystem fields from top level
        for field in ["file_path", "file_event_type", "file_type", "full_path_hash"]:
            normalized.pop(field, None)

        return normalized

    def create_subscription(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Create a subscription - routes to filesystem or general based on filter_conditions
        """
        filter_conditions = request_body.get("filter_conditions", {})

        # Route filesystem events if filter_conditions contains file_path
        if "file_path" in filter_conditions:
            return self._create_filesystem_subscription(request_body, request_context)

        else:
            return self._create_general_subscription(request_body, request_context)

    def _create_filesystem_subscription(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Create a filesystem subscription (existing logic but extracting from filter_conditions)
        """
        claims = JWTClaims.from_claims(claims=request_context['request_claims'])

        if request_body["owner"] and not claims.is_admin:
            return self.respond(
                status_code=403,
                body={"message": "not permitted to create subscriptions on behalf of another entity"},
            )

        filter_conditions = request_body.get("filter_conditions", {})

        # Extract filesystem-specific fields from filter_conditions
        file_path = filter_conditions.get("file_path")

        file_event_type = filter_conditions.get("file_event_type") 

        file_type = filter_conditions.get("file_type")

        if not file_path or not file_event_type:
            return self.respond(
                status_code=400,
                body={"message": "file_path and file_event_type are required in filter_conditions for filesystem subscriptions"},
            )

        # Validate access to the file path
        storage_client = RatioInternalClient(
            service_name="storage_manager",
            token=request_context["signed_token"],
        )

        validate_file_access_request = ObjectBody(
            body={
                "file_path": request_body["tool_definition"],
                "requested_permission_names": ["execute"],
            },
            schema=ValidateFileAccessRequest,
        )

        validation_response = storage_client.request(
            path="/storage/validate_file_access",
            request=validate_file_access_request,
        )

        logging.debug(f"Validation response: {validation_response}")

        if validation_response.status_code == 404:
            logging.debug(f"Tool definition path does not exist: {request_body['tool_definition']}")

            return self.respond(
                body={"message": f"tool {request_body['tool_definition']} definition file not found"},
                status_code=404,
            )

        entity_has_access = validation_response.response_body.get("entity_has_access", False)

        logging.debug(f"Entity has access to tool definition path: {entity_has_access}")

        if not entity_has_access:
            logging.debug(f"Requestor does not have access to tool definition path: {request_body['tool_definition']}")
            return self.respond(
                body={"message": f"unauthorized to access tool definition path {request_body['tool_definition']}"},
                status_code=403,
            )

        owner = request_body.get("owner", default_return=claims.entity)

        expiration = request_body.get("expiration")

        if expiration:
            expiration = datetime.fromisoformat(expiration)

        # Create the filesystem subscription
        subscription = FilesystemSubscription(
            tool_definition=request_body["tool_definition"],
            execution_working_directory=request_body.get("execution_working_directory"),
            expiration=expiration,
            full_path_hash=FilesystemSubscription.create_full_path_hash_from_path(file_path),
            file_event_type=file_event_type,
            file_path=file_path,
            file_type=file_type,
            process_owner=owner,
            single_use=request_body.get("single_use"),
        )

        subscription_client = FilesystemSubscriptionsTableClient()

        subscription_client.put(subscription=subscription)

        # Return normalized format
        normalized_response = self._normalize_filesystem_subscription(subscription.to_dict(json_compatible=True))

        return self.respond(
            body=normalized_response,
            status_code=201,
        )

    def _create_general_subscription(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Create a general subscription
        """
        claims = JWTClaims.from_claims(claims=request_context['request_claims'])

        if request_body["owner"] and not claims.is_admin:
            return self.respond(
                status_code=403,
                body={"message": "not permitted to create subscriptions on behalf of another entity"},
            )

        # Validate access to the tool definition
        storage_client = RatioInternalClient(
            service_name="storage_manager",
            token=request_context["signed_token"],
        )

        validate_file_access_request = ObjectBody(
            body={
                "file_path": request_body["tool_definition"],
                "requested_permission_names": ["execute"],
            },
            schema=ValidateFileAccessRequest,
        )

        validation_response = storage_client.request(
            path="/storage/validate_file_access",
            request=validate_file_access_request,
        )

        logging.debug(f"Validation response: {validation_response}")

        if validation_response.status_code == 404:
            logging.debug(f"Tool definition path does not exist: {request_body['tool_definition']}")

            return self.respond(
                body={"message": f"tool {request_body['tool_definition']} definition file not found"},
                status_code=404,
            )

        entity_has_access = validation_response.response_body.get("entity_has_access", False)

        if not entity_has_access:
            logging.debug(f"Requestor does not have access to tool definition path: {request_body['tool_definition']}")

            return self.respond(
                body={"message": f"unauthorized to access tool definition path {request_body['tool_definition']}"},
                status_code=403,
            )

        owner = request_body.get("owner", default_return=claims.entity)

        expiration = request_body.get("expiration")

        if expiration:
            expiration = datetime.fromisoformat(expiration)

        # Create the general subscription
        subscription = GeneralSubscription(
            event_type=request_body["event_type"],
            tool_definition=request_body["tool_definition"],
            execution_working_directory=request_body.get("execution_working_directory"),
            expiration=expiration,
            process_owner=owner,
            single_use=request_body.get("single_use"),
            filter_conditions=request_body.get("filter_conditions"),
        )

        subscription_client = GeneralSubscriptionsTableClient()

        subscription_client.put(subscription=subscription)

        return self.respond(
            body=subscription.to_dict(json_compatible=True),
            status_code=201,
        )

    def delete_subscription(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Delete a subscription - checks both tables
        """
        claims = JWTClaims.from_claims(claims=request_context['request_claims'])

        subscription_id = request_body["subscription_id"]

        # Try filesystem subscriptions first
        fs_client = FilesystemSubscriptionsTableClient()

        subscription = fs_client.get_by_subscription_id(subscription_id=subscription_id)

        if subscription:
            if subscription.process_owner != claims.entity and not claims.is_admin:
                return self.respond(
                    body={"message": "not permitted to delete subscription"},
                    status_code=403,
                )

            fs_client.delete(subscription=subscription)

            return self.respond(
                body={"message": f"subscription {subscription_id} deleted"},
                status_code=200,
            )

        # Try general subscriptions
        general_client = GeneralSubscriptionsTableClient()

        subscription = general_client.get_by_subscription_id(subscription_id=subscription_id)

        if subscription:
            if subscription.process_owner != claims.entity and not claims.is_admin:
                return self.respond(
                    body={"message": "not permitted to delete subscription"},
                    status_code=403,
                )

            general_client.delete(subscription=subscription)

            return self.respond(
                body={"message": f"subscription {subscription_id} deleted"},
                status_code=200,
            )

        return self.respond(
            body={"message": f"subscription {subscription_id} not found"},
            status_code=404,
        )

    def describe_subscription(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Describe a subscription - checks both tables and returns normalized format
        """
        claims = JWTClaims.from_claims(claims=request_context['request_claims'])

        subscription_id = request_body["subscription_id"]

        # Try filesystem subscriptions first
        fs_client = FilesystemSubscriptionsTableClient()

        subscription = fs_client.get_by_subscription_id(subscription_id=subscription_id)

        if subscription:
            if subscription.process_owner != claims.entity and not claims.is_admin:
                return self.respond(
                    body={"message": "not authorized"},
                    status_code=403,
                )

            # Return normalized filesystem subscription
            normalized_sub = self._normalize_filesystem_subscription(subscription.to_dict(json_compatible=True))
            return self.respond(
                body=normalized_sub,
                status_code=200,
            )

        # Try general subscriptions
        general_client = GeneralSubscriptionsTableClient()

        subscription = general_client.get_by_subscription_id(subscription_id=subscription_id)

        if subscription:
            if subscription.process_owner != claims.entity and not claims.is_admin:
                return self.respond(
                    body={"message": "not authorized"},
                    status_code=403,
                )

            return self.respond(
                body=subscription.to_dict(json_compatible=True),
                status_code=200,
            )

        return self.respond(
            body={"message": f"subscription {subscription_id} not found"},
            status_code=404,
        )

    def list_subscriptions(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        List subscriptions from both tables with normalized format
        """
        claims = JWTClaims.from_claims(claims=request_context['request_claims'])

        if request_body["owner"] and not claims.is_admin:
            return self.respond(
                body={"message": "not permitted to list subscriptions on behalf of another entity"},
                status_code=403,
            )

        owner = request_body.get("owner", default_return=claims.entity)
        event_type = request_body.get("event_type")

        all_subscriptions = []

        # Get filesystem subscriptions and normalize them
        fs_client = FilesystemSubscriptionsTableClient()

        fs_subscriptions = fs_client.list_by_file_path_or_owner(
            process_owner=owner,
        )

        for fs_sub in fs_subscriptions:
            normalized_sub = self._normalize_filesystem_subscription(fs_sub.to_dict(json_compatible=True))

            # Apply event_type filter if specified
            if not event_type or normalized_sub.get("event_type") == event_type:
                all_subscriptions.append(normalized_sub)

        # Get general subscriptions 
        general_client = GeneralSubscriptionsTableClient()
        general_subscriptions = general_client.list_by_event_type_or_owner(
            event_type=event_type,
            process_owner=owner,
        )

        all_subscriptions.extend([sub.to_dict(json_compatible=True) for sub in general_subscriptions])

        return self.respond(
            body=all_subscriptions,
            status_code=200,
        )