
from da_vinci.core.immutable_object import (
    ObjectBodySchema,
    RequiredCondition,
    SchemaAttribute,
    SchemaAttributeType,
)


class AgentInstructionSchema(ObjectBodySchema):
    """
    Schema for an agent execution definition, an object that is used in a list of instructions.
    """
    attributes = [
        SchemaAttribute(
            name="agent_definition",
            type_name=SchemaAttributeType.OBJECT,
            description="The full path to the agent definition file",
            required=True,
            required_conditions=[
                RequiredCondition(
                    param="agent_definition_path",
                    operator="not_exists",
                )
            ]
        ),
        SchemaAttribute(
            name="agent_definition_path",
            type_name=SchemaAttributeType.STRING,
            description="The full path to the agent definition file",
            required=True,
            regex_pattern="^/[a-zA-Z0-9_\\-\\/\\.]+$",
            required_conditions=[
                RequiredCondition(
                    param="agent_definition",
                    operator="not_exists",
                )
            ]
        ),
        SchemaAttribute(
            name="arguments",
            type_name=SchemaAttributeType.OBJECT,
            description="The arguments to pass to the agent. Not required if the agent does not take any arguments or has sane default values",
            required=False,
        ),
        SchemaAttribute(
            name="execution_id",
            type_name=SchemaAttributeType.STRING,
            description="The execution ID of the agent execution. Can be any string. Used for REF references between agents",
            required=True,
            regex_pattern="^[a-zA-Z0-9_\\-]+$",
        ),
    ]


class AgentDefinitionSchema(ObjectBodySchema):
  attributes = [
    SchemaAttribute(
        name="arguments",
        type_name=SchemaAttributeType.OBJECT_LIST,
        description="The defined arguments the agent takes. Defined using the ObjectBodySchema",
        required=True,
    ),
    SchemaAttribute(
        name="description",
        type_name=SchemaAttributeType.STRING,
        description="The description of the agent",
        required=False,
    ),
    SchemaAttribute(
        name="instructions",
        type_name=SchemaAttributeType.OBJECT_LIST,
        description="Instructions to execute the agent as a task itself",
        required=True,
        required_conditions=[
            RequiredCondition(param="system_event_endpoint", operator="not_exists")
        ]
    ),
    SchemaAttribute(
        name="response_reference_map",
        type_name=SchemaAttributeType.OBJECT,
        description="A map of the response reference to the agent execution. This is used to reference the response of the agent execution",
        required=False,
        required_conditions=[
            RequiredCondition(param="response_definitions", operator="exists"),
        ]
    ),
    SchemaAttribute(
        name="responses",
        type_name=SchemaAttributeType.OBJECT_LIST,
        description="The defined responses the agent takes. Defined using the ObjectBodySchema",
        required=False,
    ),
    SchemaAttribute(
        name="system_event_endpoint",
        type_name=SchemaAttributeType.STRING,
        description="The name of the system event that the agent Lambda function is listening to",
        required=True,
        required_conditions=[
            RequiredCondition(param="instructions", operator="not_exists")
        ]
    ),
  ]


class ConditionSchema(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="param",
            type_name=SchemaAttributeType.STRING,
            description="REF string to the parameter to evaluate",
            required=True,
        ),
        SchemaAttribute(
            name="operator",
            type_name=SchemaAttributeType.STRING,
            description="Comparison operator",
            required=True,
            enum=[
                "equals",
                "not_equals",
                "greater_than",
                "less_than",
                "exists",
                "not_exists",
                "contains",
                "in",
                "starts_with"
            ]
        ),
        SchemaAttribute(
            name="value",
            type_name=SchemaAttributeType.ANY,
            description="Value to compare against",
            required=False,
        ),
    ]

class ConditionGroupSchema(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="logic",
            type_name=SchemaAttributeType.STRING,
            description="Logic operator for this group",
            required=False,
            default_value="AND",
            enum=["AND", "OR"]
        ),
        SchemaAttribute(
            name="conditions",
            type_name=SchemaAttributeType.OBJECT_LIST,
            description="List of conditions or nested condition groups",
            required=True,
        ),
    ]


class DescribeProcessRequest(ObjectBodySchema):
    """
    Schema for describing a process. This is used to get the details of a process that is currently running.
    """
    attributes = [
        SchemaAttribute(
            name="process_id",
            type_name=SchemaAttributeType.STRING,
            description="The ID of the process to describe",
            required=True,
            regex_pattern="^[a-zA-Z0-9_\\-]+$",
        ),
    ]


class ExecuteAgentRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="arguments",
            type_name=SchemaAttributeType.OBJECT,
            description="The arguments to pass to the agent. Not required if the agent does not take any arguments or has sane default values",
            required=False,
        ),
        SchemaAttribute(
            name="agent_definition",
            type_name=SchemaAttributeType.OBJECT,
            description="An inline agent definition. This is a JSON object that contains the agent definition. It can be used instead of the agent_definition_path",
            required=True,
            required_conditions=[
                RequiredCondition(
                    param="agent_definition_path",
                    operator="not_exists",
                )
            ]
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
            name="conditions",
            type_name=SchemaAttributeType.OBJECT_LIST,
            description="A list of conditions to evaluate before executing the agent. This is used to determine if the agent should be executed or not",
            required=False,
        ),
        SchemaAttribute(
            name="dependencies",
            type_name=SchemaAttributeType.STRING_LIST,
            description="A list of execution ids the agent execution is dependent on. Not required if dependencies are captured with REF references",
            required=False,
        ),
        SchemaAttribute(
            name="execute_as",
            type_name=SchemaAttributeType.STRING,
            description="The entity to execute the agent as. This is the entity that will be used to execute the agent. ONLY SUPPORTED IF THE REQUESTOR IS AN ADMIN",
            required=False,
            regex_pattern="^[a-z0-9_\\-]+$",
        ),
        SchemaAttribute(
            name="working_directory",
            type_name=SchemaAttributeType.STRING,
            description="The working directory where the agent will be executed. It will default to executing in the entity's home directory",
            required=False,
            regex_pattern="^/[a-zA-Z0-9_\\-\\/\\.]+$",
        ),
    ]


class KillProcessRequest(ObjectBodySchema):
    """
    Schema for killing a process. This is used to kill a process that is currently running.
    """
    attributes = [
        SchemaAttribute(
            name="process_id",
            type_name=SchemaAttributeType.STRING,
            description="The ID of the process to kill",
            required=True,
            regex_pattern="^[a-zA-Z0-9_\\-]+$",
        ),
    ]


class ListProcessesRequest(ObjectBodySchema):
    """
    Schema for listing processes. This is used to list all the processes that are currently running.
    """
    attributes = [
        SchemaAttribute(
            name="process_owner",
            type_name=SchemaAttributeType.STRING,
            description="Optional filter for the owner of the process. This is the entity that started the process",
            required=False,
            regex_pattern="^[a-z0-9_\\-]+$",
        ),
        SchemaAttribute(
            name="parent_process_id",
            type_name=SchemaAttributeType.STRING,
            description="Optional filter for the parent process ID. This is the ID of the process that started this process",
            required=False,
            regex_pattern="^[a-z0-9_\\-]+$",
        ),
        SchemaAttribute(
            name="status",
            type_name=SchemaAttributeType.STRING,
            description="The status of the process. Can be any of the following: RUNNING, COMPLETED, FAILED",
            required=False,
        ),
    ]


class ValidateAgentDefinitionRequest(ObjectBodySchema):
    """
    Schema for validating an agent definition. This is used to validate the agent definition before executing it.
    """
    attributes = [
        SchemaAttribute(
            name="agent_definition",
            type_name=SchemaAttributeType.OBJECT,
            description="An inline agent definition. This is a JSON object that contains the agent definition.",
            required=True,
            required_conditions=[
                RequiredCondition(
                    param="agent_definition_path",
                    operator="not_exists",
                )
            ]
        ),
        SchemaAttribute(
            name="agent_definition_path",
            type_name=SchemaAttributeType.STRING,
            description="The full path to the agent definition file. This is a JSON object that contains the agent definition to be executed.",
            required=True,
            regex_pattern="^/[a-zA-Z0-9_\\-\\/\\.]+$",
            required_conditions=[
                RequiredCondition(
                    param="agent_definition",
                    operator="not_exists",
                )
            ]
        ),
    ]