
from da_vinci.core.immutable_object import (
    ObjectBodySchema,
    RequiredCondition,
    SchemaAttribute,
    SchemaAttributeType,
)


class ToolInstructionSchema(ObjectBodySchema):
    """
    Schema for an tool execution definition, an object that is used in a list of instructions.
    """
    attributes = [
        SchemaAttribute(
            name="tool_definition",
            type_name=SchemaAttributeType.OBJECT,
            description="The full path to the tool definition file",
            required=True,
            required_conditions=[
                RequiredCondition(
                    param="tool_definition_path",
                    operator="not_exists",
                )
            ]
        ),
        SchemaAttribute(
            name="tool_definition_path",
            type_name=SchemaAttributeType.STRING,
            description="The full path to the tool definition file",
            required=True,
            regex_pattern="^/[a-zA-Z0-9_\\-\\/\\.]+$",
            required_conditions=[
                RequiredCondition(
                    param="tool_definition",
                    operator="not_exists",
                )
            ]
        ),
        SchemaAttribute(
            name="arguments",
            type_name=SchemaAttributeType.OBJECT,
            description="The arguments to pass to the tool. Not required if the tool does not take any arguments or has sane default values",
            required=False,
        ),
        SchemaAttribute(
            name="execution_id",
            type_name=SchemaAttributeType.STRING,
            description="The execution ID of the tool execution. Can be any string. Used for REF references between tools",
            required=True,
            regex_pattern="^[a-zA-Z0-9_\\-]+$",
        ),
        SchemaAttribute(
            name="parallel_execution",
            type_name=SchemaAttributeType.OBJECT,
            description="Configuration for parallel execution",
            required=False,
        ),
        SchemaAttribute(
            name="transform_arguments",
            type_name=SchemaAttributeType.OBJECT,
            description="Pre execution transforms to apply to the tool arguments. This is used to transform the arguments of the tool execution",
            required=False,
        ),
        SchemaAttribute(
            name="transform_responses",
            type_name=SchemaAttributeType.OBJECT,
            description="Post execution transforms to apply to the tool responses. This is used to transform the responses of the tool execution",
            required=False,
        ),
    ]


class ToolDefinitionSchema(ObjectBodySchema):
  attributes = [
    SchemaAttribute(
        name="arguments",
        type_name=SchemaAttributeType.OBJECT_LIST,
        description="The defined arguments the tool takes. Defined using the ObjectBodySchema",
        required=False,
    ),
    SchemaAttribute(
        name="description",
        type_name=SchemaAttributeType.STRING,
        description="The description of the tool",
        required=False,
    ),
    SchemaAttribute(
        name="instructions",
        type_name=SchemaAttributeType.OBJECT_LIST,
        description="Instructions to execute the tool as a task itself",
        required=True,
        required_conditions=[
            RequiredCondition(param="system_event_endpoint", operator="not_exists")
        ]
    ),
    SchemaAttribute(
        name="response_reference_map",
        type_name=SchemaAttributeType.OBJECT,
        description="A map of the response reference to the tool execution. This is used to reference the response of the tool execution",
        required=False,
        required_conditions=[
            RequiredCondition(param="response_definitions", operator="exists"),
        ]
    ),
    SchemaAttribute(
        name="responses",
        type_name=SchemaAttributeType.OBJECT_LIST,
        description="The defined responses the tool takes. Defined using the ObjectBodySchema",
        required=False,
    ),
    SchemaAttribute(
        name="system_event_endpoint",
        type_name=SchemaAttributeType.STRING,
        description="The name of the system event that the tool Lambda function is listening to",
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


class ExecuteToolRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="arguments",
            type_name=SchemaAttributeType.OBJECT,
            description="The arguments to pass to the tool. Not required if the tool does not take any arguments or has sane default values",
            required=False,
        ),
        SchemaAttribute(
            name="tool_definition",
            type_name=SchemaAttributeType.OBJECT,
            description="An inline tool definition. This is a JSON object that contains the tool definition. It can be used instead of the tool_definition_path",
            required=True,
            required_conditions=[
                RequiredCondition(
                    param="tool_definition_path",
                    operator="not_exists",
                )
            ]
        ),
        SchemaAttribute(
            name="tool_definition_path",
            type_name=SchemaAttributeType.STRING,
            description="The full path to the tool definition file. This is a JSON object that contains the tool definition to be executed. It can be used instead of the tool_definition",
            required=True,
            required_conditions=[
                RequiredCondition(
                    param="tool_definition",
                    operator="not_exists",
                )
            ]
        ),
        SchemaAttribute(
            name="conditions",
            type_name=SchemaAttributeType.OBJECT_LIST,
            description="A list of conditions to evaluate before executing the tool. This is used to determine if the tool should be executed or not",
            required=False,
        ),
        SchemaAttribute(
            name="dependencies",
            type_name=SchemaAttributeType.STRING_LIST,
            description="A list of execution ids the tool execution is dependent on. Not required if dependencies are captured with REF references",
            required=False,
        ),
        SchemaAttribute(
            name="execute_as",
            type_name=SchemaAttributeType.STRING,
            description="The entity to execute the tool as. This is the entity that will be used to execute the tool. ONLY SUPPORTED IF THE REQUESTOR IS AN ADMIN",
            required=False,
            regex_pattern="^[a-z0-9_\\-]+$",
        ),
        SchemaAttribute(
            name="working_directory",
            type_name=SchemaAttributeType.STRING,
            description="The working directory where the tool will be executed. It will default to executing in the entity's home directory",
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


class ValidateToolDefinitionRequest(ObjectBodySchema):
    """
    Schema for validating an tool definition. This is used to validate the tool definition before executing it.
    """
    attributes = [
        SchemaAttribute(
            name="tool_definition",
            type_name=SchemaAttributeType.OBJECT,
            description="An inline tool definition. This is a JSON object that contains the tool definition.",
            required=True,
            required_conditions=[
                RequiredCondition(
                    param="tool_definition_path",
                    operator="not_exists",
                )
            ]
        ),
        SchemaAttribute(
            name="tool_definition_path",
            type_name=SchemaAttributeType.STRING,
            description="The full path to the tool definition file. This is a JSON object that contains the tool definition to be executed.",
            required=True,
            regex_pattern="^/[a-zA-Z0-9_\\-\\/\\.]+$",
            required_conditions=[
                RequiredCondition(
                    param="tool_definition",
                    operator="not_exists",
                )
            ]
        ),
    ]