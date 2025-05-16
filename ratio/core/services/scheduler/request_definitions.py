from da_vinci.core.immutable_object import (
    ObjectBodySchema,
    SchemaAttribute,
    SchemaAttributeType,
)

from ratio.core.core_lib.definitions.events import FileEventType


class CreateSubscriptionRequest(ObjectBodySchema):
    """
    Schema for creating a subscription to a file system event.
    """
    attributes = [
        SchemaAttribute(
            name="agent_definition",
            type_name=SchemaAttributeType.STRING,
            description="The path to the agent that will be executed for the subscription.",
            required=True,
            regex_pattern="^/[a-zA-Z0-9_\\-\\/\\.]+$",
        ),
        SchemaAttribute(
            name="execution_working_directory",
            type_name=SchemaAttributeType.STRING,
            description="The optional working directory for the agent execution.",
            required=False,
            regex_pattern="^/[a-zA-Z0-9_\\-\\/\\.]+$",
        ),
        SchemaAttribute(
            name="expiration",
            type_name=SchemaAttributeType.DATETIME,
            description="The optional datetime the subscription will expire.",
            required=False,
        ),
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            description="The full path to the file or directory to subscribe to",
            required=True,
            regex_pattern="^/[a-zA-Z0-9_\\-\\/\\.]+$"
        ),
        SchemaAttribute(
            name="file_type",
            type_name=SchemaAttributeType.STRING,
            description="The optional type of file to subscribe to. This is only supported for directory subscriptions",
            required=False,
        ),
        SchemaAttribute(
            name="file_event_type",
            type_name=SchemaAttributeType.STRING,
            description="The type of file system event to which the subscription is limited. E.g. create, delete, update etc",
            enum=[event_type.value for event_type in FileEventType],
            required=True,
        ),
        SchemaAttribute(
            name="owner",
            type_name=SchemaAttributeType.STRING,
            description="The owner of the process. This can only be set by the admin, the default is the creator of the subscription.",
            required=False,
            regex_pattern="^[a-z0-9_\\-]+$",
        ),
        SchemaAttribute(
            name="single_use",
            type_name=SchemaAttributeType.BOOLEAN,
            description="Whether the subscription is single use or not.",
            required=False,
            default_value=False,
        ),
    ]


class DeleteSubscriptionRequest(ObjectBodySchema):
    """
    Schema for deleting a subscription to a file system event.
    """
    attributes = [
        SchemaAttribute(
            name="subscription_id",
            type_name=SchemaAttributeType.STRING,
            description="The ID of the subscription to delete.",
            required=True,
            regex_pattern="^[a-zA-Z0-9_\\-]+$",
        ),
    ]


class DescribeSubscriptionRequest(ObjectBodySchema):
    """
    Schema for describing a subscription to a file system event.
    """
    attributes = [
        SchemaAttribute(
            name="subscription_id",
            type_name=SchemaAttributeType.STRING,
            description="The ID of the subscription to describe.",
            required=True,
            regex_pattern="^[a-zA-Z0-9_\\-]+$",
        ),
    ]


class ListSubscriptionsRequest(ObjectBodySchema):
    """
    Schema for listing subscriptions to file system events.
    """
    attributes = [
        SchemaAttribute(
            name="file_path",
            type_name=SchemaAttributeType.STRING,
            description="The full path to the file or directory to subscribe to. If not provided, all subscriptions will be listed.",
            required=False,
            regex_pattern="^/[a-zA-Z0-9_\\-\\/\\.]+$",
        ),
        SchemaAttribute(
            name="owner",
            type_name=SchemaAttributeType.STRING,
            description="The owner of the subscriptions to list. If not provided, all subscriptions will be listed.",
            required=False,
            regex_pattern="^[a-z0-9_\\-]+$",
        ),
    ]