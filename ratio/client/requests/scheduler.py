from typing import Optional
from datetime import datetime

from ratio.client.client import (
    RequestAttributeType,
    RequestBodyAttribute,
    RequestBody,
)


class CreateSubscriptionRequest(RequestBody):
    """
    Create subscription request body schema.
    """
    path = "/scheduler/create_subscription"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="event_type",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="agent_definition",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="execution_working_directory",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="expiration",
            attribute_type=RequestAttributeType.DATETIME,
            optional=True,
        ),
        RequestBodyAttribute(
            name="owner",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="single_use",
            attribute_type=RequestAttributeType.BOOLEAN,
            default=False,
            optional=True,
        ),
        RequestBodyAttribute(
            name="filter_conditions",
            attribute_type=RequestAttributeType.OBJECT,
            optional=True,
        ),
    ]

    def __init__(self, event_type: str, agent_definition: str, expiration: Optional[datetime] = None,
                 execution_working_directory: Optional[str] = None, owner: Optional[str] = None, 
                 single_use: Optional[bool] = None, filter_conditions: Optional[dict] = None):
        """
        Initialize the CreateSubscription request body.

        Keyword arguments:
        event_type -- The type of event to subscribe to (e.g., process_start, process_stop, file_type_update).
        agent_definition -- The path to the agent that will be executed for the subscription.
        expiration -- The optional datetime the subscription will expire.
        execution_working_directory -- The optional working directory for the agent execution.
        owner -- The owner of the process. This can only be set by the admin, the default is the creator.
        single_use -- Whether the subscription is single use or not.
        filter_conditions -- Event-specific filter conditions. For filesystem events: include file_path, file_event_type, file_type.
        """
        super().__init__(
            event_type=event_type,
            agent_definition=agent_definition,
            expiration=expiration,
            execution_working_directory=execution_working_directory,
            owner=owner,
            single_use=single_use,
            filter_conditions=filter_conditions,
        )


class DeleteSubscriptionRequest(RequestBody):
    """
    Delete subscription request body schema.
    """
    path = "/scheduler/delete_subscription"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="subscription_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, subscription_id: str):
        """
        Initialize the DeleteSubscription request body.

        Keyword arguments:
        subscription_id -- The ID of the subscription to delete.
        """
        super().__init__(subscription_id=subscription_id)


class DescribeSubscriptionRequest(RequestBody):
    """
    Describe subscription request body schema.
    """
    path = "/scheduler/describe_subscription"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="subscription_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, subscription_id: str):
        """
        Initialize the DescribeSubscription request body.

        Keyword arguments:
        subscription_id -- The ID of the subscription to describe.
        """
        super().__init__(subscription_id=subscription_id)


class ListSubscriptionsRequest(RequestBody):
    """
    List subscriptions request body schema.
    """
    path = "/scheduler/list_subscriptions"

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="event_type",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="owner",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
    ]

    def __init__(self, event_type: Optional[str] = None, owner: Optional[str] = None):
        """
        Initialize the ListSubscriptions request body.

        Keyword arguments:
        event_type -- The event type to filter by.
        owner -- The owner of the subscriptions to list. If not provided, all subscriptions will be listed.
        """
        super().__init__(
            event_type=event_type,
            owner=owner,
        )