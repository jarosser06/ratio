"""
Handles sending the FS events
"""

from da_vinci.core.immutable_object import (
    ObjectBodySchema,
    RequiredCondition,
    SchemaAttribute,
    SchemaAttributeType,
)


class SystemExecuteAgentRequest(ObjectBodySchema):
    """
    Object body schema describing what all agents expect to recieve
    when they are executed.
    """
    attributes = [
        SchemaAttribute(
            name="arguments_path",
            type_name=SchemaAttributeType.STRING,
            description="The path to the arguments file",
            required=False,
        ),
        SchemaAttribute(
            name="argument_schema",
            type_name=SchemaAttributeType.OBJECT_LIST,
            description="The schema for the arguments",
            required=True,
            required_conditions=[
                RequiredCondition(
                    operator="exists",
                    param="arguments_path",
                )
            ]
        ),
        SchemaAttribute(
            name="parent_process_id",
            type_name=SchemaAttributeType.STRING,
            description="The ID of the parent process. Used int",
            required=True,
        ),
        SchemaAttribute(
            name="process_id",
            type_name=SchemaAttributeType.STRING,
            description="The ID of the process",
            required=True,
        ),
        SchemaAttribute(
            name="response_schema",
            type_name=SchemaAttributeType.OBJECT_LIST,
            description="The schema for the response",
            required=False,
        ),
        SchemaAttribute(
            name="token",
            type_name=SchemaAttributeType.STRING,
            description="The token to use for authentication",
            required=True,
        ),
        SchemaAttribute(
            name="working_directory",
            type_name=SchemaAttributeType.STRING,
            description="The working directory for the agent execution",
            required=True,
        ),
    ]


class SystemExecuteAgentResponse(ObjectBodySchema):
    """
    Object body schema describing what all agents are expected to

    return when they are responding to an execution request.
    """
    attributes = [
        SchemaAttribute(
            name="failure",
            type_name=SchemaAttributeType.STRING,
            description="The failure message",
            required=False,
        ),
        SchemaAttribute(
            name="parent_process_id",
            type_name=SchemaAttributeType.STRING,
            description="The ID of the parent process",
            required=True,
        ),
        SchemaAttribute(
            name="process_id",
            type_name=SchemaAttributeType.STRING,
            description="The ID of the process",
            required=True,
        ),
        SchemaAttribute(
            name="response",
            type_name=SchemaAttributeType.STRING,
            description="The path to the response file",
            required=False,
        ),
        SchemaAttribute(
            name="token",
            type_name=SchemaAttributeType.STRING,
            description="The token to use for authentication",
            required=True,
        ),
        SchemaAttribute(
            name="status",
            type_name=SchemaAttributeType.STRING,
            description="The status of the agent execution",
            required=True,
        ),
    ]

