from da_vinci.core.immutable_object import (
    ObjectBodySchema,
    SchemaAttribute,
    SchemaAttributeType,
)


class GeneralSystemEvent(ObjectBodySchema):
    """
    Schema for general system events.
    """
    attributes = [
        SchemaAttribute(
            name="event_type",
            type_name=SchemaAttributeType.STRING,
            description="The event bus event type. This is used to route the event to the correct handler.",
            required=False,
            default_value="ratio::system_event",
        ),
        SchemaAttribute(
            name="system_event_type",
            type_name=SchemaAttributeType.STRING,
            description="The specific type of system event (e.g., process_start, process_stop, file_type_update).",
            required=True,
        ),
        SchemaAttribute(
            name="event_details",
            type_name=SchemaAttributeType.OBJECT,
            description="Event-specific details payload.",
            required=False,
        ),
        SchemaAttribute(
            name="source_system",
            type_name=SchemaAttributeType.STRING,
            description="The system that generated this event.",
            required=False,
        ),
    ]


class CreateSubscriptionRequest(ObjectBodySchema):
    """
    Schema for creating a subscription to system events.
    """
    attributes = [
        SchemaAttribute(
            name="event_type",
            type_name=SchemaAttributeType.STRING,
            description="The type of event to subscribe to (e.g., process_start, process_stop, file_type_update).",
            required=True,
            regex_pattern="^[a-z_]+$",
        ),
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
        SchemaAttribute(
            name="filter_conditions",
            type_name=SchemaAttributeType.OBJECT,
            description="Event-specific filter conditions (JSON object). For filesystem events: include file_path, file_event_type, file_type. For process events: include process_name, owner_pattern, etc.",
            required=False,
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
            name="event_type",
            type_name=SchemaAttributeType.STRING,
            description="The type of event to list subscriptions for (e.g., process_start, process_stop, file_type_update). If not provided, all subscriptions will be listed.",
            required=False,
        ),
        SchemaAttribute(
            name="owner",
            type_name=SchemaAttributeType.STRING,
            description="The owner of the subscriptions to list. If not provided, all subscriptions will be listed.",
            required=False,
            regex_pattern="^[a-z0-9_\\-]+$",
        ),
    ]