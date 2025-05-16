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
            name="agent_definition",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="expiration",
            attribute_type=RequestAttributeType.DATETIME,
            optional=True,
        ),
        # "created", "deleted", "updated", "version_created", "version_deleted"
        RequestBodyAttribute(
            name="file_event_type",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="file_type",
            attribute_type=RequestAttributeType.STRING,
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
    ]

    def __init__(self, agent_definition: str, file_path: str, file_event_type: str, expiration: Optional[datetime] = None,
                 file_type: Optional[str] = None, owner: Optional[str] = None, single_use: Optional[bool] = None):
        """
        Initialize the CreateSubscription request body.

        Keyword arguments:
        agent_definition -- The path to the agent that will be executed for the subscription.
        file_path -- The full path to the file or directory to subscribe to.
        expiration -- The optional datetime the subscription will expire.
        file_type -- The optional type of file to subscribe to. Only supported for directory subscriptions.
        file_event_type -- The type of file system event to which the subscription is limited. E.g. created, deleted, updated, version_created, version_deleted.
        owner -- The owner of the process. This can only be set by the admin, the default is the creator.
        single_use -- Whether the subscription is single use or not.
        """
        super().__init__(
            agent_definition=agent_definition,
            file_path=file_path,
            expiration=expiration,
            file_type=file_type,
            file_event_type=file_event_type,
            owner=owner,
            single_use=single_use,
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
            name="file_path",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="owner",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
    ]

    def __init__(self, file_path: Optional[str] = None, owner: Optional[str] = None):
        """
        Initialize the ListSubscriptions request body.

        Keyword arguments:
        file_path -- The full path to the file or directory. If not provided, all subscriptions will be listed.
        owner -- The owner of the subscriptions to list. If not provided, all subscriptions will be listed.
        """
        super().__init__(
            file_path=file_path,
            owner=owner,
        )