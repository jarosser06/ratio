from datetime import datetime, UTC as utc_tz
from typing import List, Optional, Union
from uuid import uuid4

from da_vinci.core.orm.client import (
    TableClient,
    TableObject,
    TableObjectAttribute,
    TableObjectAttributeType,
    TableScanDefinition,
)


class GeneralSubscription(TableObject):
    table_name = "general_subscriptions"

    table_description = "Tracks tool subscriptions to general system events"

    partition_key_attribute = TableObjectAttribute(
        name="event_type",
        attribute_type=TableObjectAttributeType.STRING,
        description="The type of event to subscribe to (e.g., process_start, process_stop, file_type_update).",
    )

    sort_key_attribute = TableObjectAttribute(
        name="subscription_id",
        attribute_type=TableObjectAttributeType.STRING,
        description="The unique ID of the subscription.",
        default=lambda: str(uuid4()),
    )

    ttl_attribute = TableObjectAttribute(
        name="expiration",
        attribute_type=TableObjectAttributeType.DATETIME,
        description="The optional datetime the subscription will expire.",
        optional=True,
    )

    attributes = [
        TableObjectAttribute(
            name="tool_definition",
            attribute_type=TableObjectAttributeType.STRING,
            description="The path to the tool that will be executed for the subscription.",
            optional=False,
        ),

        TableObjectAttribute(
            name="created_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the subscription was created.",
            optional=False,
            default=datetime.now(tz=utc_tz),
        ),

        TableObjectAttribute(
            name="execution_working_directory",
            attribute_type=TableObjectAttributeType.STRING,
            description="The optional working directory for the tool execution.",
            optional=True,
        ),

        TableObjectAttribute(
            name="last_execution",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the subscription was last executed",
            optional=True,
        ),

        TableObjectAttribute(
            name="process_owner",
            attribute_type=TableObjectAttributeType.STRING,
            description="The owner of the process.",
            optional=False,
        ),

        TableObjectAttribute(
            name="single_use",
            attribute_type=TableObjectAttributeType.BOOLEAN,
            description="Whether the subscription is single use or not.",
            optional=False,
            default=False,
        ),

        TableObjectAttribute(
            name="filter_conditions",
            attribute_type=TableObjectAttributeType.JSON_STRING,
            description="Optional filter conditions for event matching (JSON object).",
            optional=True,
        ),
    ]


class GeneralSubscriptionsTableClient(TableClient):
    def __init__(self, app_name: Optional[str] = None, deployment_id: Optional[str] = None):
        super().__init__(
            default_object_class=GeneralSubscription,
            app_name=app_name,
            deployment_id=deployment_id
        )

    def delete(self, subscription: GeneralSubscription) -> None:
        """
        Delete a subscription.

        Keyword arguments:
        subscription -- The subscription to delete.
        """
        self.delete_object(table_object=subscription)

    def get(self, event_type: str, subscription_id: str) -> Union[GeneralSubscription, None]:
        """
        Get a subscription by its event type and subscription ID.

        Keyword arguments:
        event_type -- The event type of the subscription.
        subscription_id -- The ID of the subscription.
        """
        return self.get_object(partion_key_value=event_type, sort_key_value=subscription_id)

    def get_by_event_type(self, event_type: str) -> List[GeneralSubscription]:
        """
        Get all subscriptions for a specific event type.

        Keyword arguments:
        event_type -- The event type to get subscriptions for.
        """
        parameters = {
            "KeyConditionExpression": "EventType = :event_type",
            "ExpressionAttributeValues": {
                ":event_type": {"S": event_type},
            },
        }

        subscriptions = []

        for page in self.paginated(call='query', parameters=parameters):
            subscriptions.extend(page)

        return subscriptions

    def get_by_subscription_id(self, subscription_id: str) -> Optional[GeneralSubscription]:
        """
        Get a subscription by its subscription ID using the GSI.
        Returns a single subscription or None if not found.

        Keyword arguments:
        subscription_id -- The ID of the subscription.
        """
        parameters = {
            "IndexName": "subscription_id-index",
            "KeyConditionExpression": "SubscriptionId = :subscription_id",
            "ExpressionAttributeValues": {
                ":subscription_id": {"S": subscription_id},
            },
        }

        subscriptions = []

        for page in self.paginated(call='query', parameters=parameters):
            subscriptions.extend(page)

        # Return the first (and should be only) subscription or None
        return subscriptions[0] if subscriptions else None

    def list_by_event_type_or_owner(self, event_type: Optional[str] = None, process_owner: Optional[str] = None) -> List[GeneralSubscription]:
        """
        Get subscriptions by event_type and/or owner.
        If event_type is provided, uses a more efficient query.
        Otherwise, falls back to a scan with owner filter.

        Keyword arguments:
        event_type -- The event type to filter by.
        process_owner -- The owner of the subscriptions to list.

        Returns:
            List of matching GeneralSubscription objects
        """
        if not event_type and not process_owner:
            raise ValueError("At least one of event_type or process_owner must be provided")

        # If we have an event_type, we can use a more efficient query
        if event_type:
            parameters = {
                "KeyConditionExpression": "EventType = :event_type",
                "ExpressionAttributeValues": {
                    ":event_type": {"S": event_type},
                },
            }

            # If owner is also specified, add it as a filter
            if process_owner:
                parameters["FilterExpression"] = "ProcessOwner = :owner"

                parameters["ExpressionAttributeValues"][":owner"] = {"S": process_owner}

            # Execute the query
            subscriptions = []

            for page in self.paginated(call='query', parameters=parameters):
                subscriptions.extend(page)

            return subscriptions

        # If we only have owner, we need to do a full scan
        else:
            scan_definition = TableScanDefinition(table_object_class=self.default_object_class)

            scan_definition.add("process_owner", "equal", process_owner)

            return self.full_scan(scan_definition=scan_definition)

    def put(self, subscription: GeneralSubscription) -> None:
        """
        Put a subscription.

        Keyword arguments:
        subscription -- The subscription to put.
        """
        self.put_object(table_object=subscription)