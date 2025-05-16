"""
Handles sending the FS events
"""

from da_vinci.core.immutable_object import (
    ObjectBodySchema,
    RequiredCondition,
    SchemaAttribute,
    SchemaAttributeType,
)


class ExecuteAgentInternalRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="arguments_path",
            type_name=SchemaAttributeType.STRING,
            description="The path to the arguments being passed to the agents.",
            required=False,
        ),
        SchemaAttribute(
            name="agent_definition_path",
            type_name=SchemaAttributeType.STRING,
            description="The full path to the agent definition file. This is a JSON object that contains the agent definition to be executed. It can be used instead of the agent_definition",
            required=True,
            required_conditions=[
                RequiredCondition(
                    param="agent_definition",
                    operator="not_exists",
                )
            ]
        ),
        SchemaAttribute(
            name="parent_process_id",
            type_name=SchemaAttributeType.STRING,
            description="The ID of the parent process. Used in the agent definition",
            required=True,
        ),
        SchemaAttribute(
            name="process_id",
            type_name=SchemaAttributeType.STRING,
            description="The ID of the process. Used in the agent definition",
            required=True,
        ),
        SchemaAttribute(
           name="token",
           type_name=SchemaAttributeType.STRING,
           description="The token to use for system authentication",
           required=True,
        ),
        SchemaAttribute(
            name="working_directory",
            type_name=SchemaAttributeType.STRING,
            description="The working directory where the agent will be executed. It will default to executing in the entity's home directory",
            required=True,
            regex_pattern="^/[a-zA-Z0-9_\\-\\/\\.]+$",
        ),
    ]


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
            description="The failure messsage if the agent failed",
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
            name="status",
            type_name=SchemaAttributeType.STRING,
            description="The status of the agent execution",
            required=True,
        ),
    ]

