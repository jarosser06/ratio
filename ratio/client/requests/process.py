from typing import Optional

from ratio.client.client import (
    RequestAttributeType,
    RequestBodyAttribute,
    RequestBody,
)


class ExecuteToolRequest(RequestBody):
    """
    Execute an tool with the given definition and arguments
    """
    path = '/process/execute'

    requires_auth = True

    supports_websockets = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="arguments",
            attribute_type=RequestAttributeType.OBJECT,
            optional=True,
        ),
        RequestBodyAttribute(
            name="tool_definition",
            attribute_type=RequestAttributeType.OBJECT,
            optional=True,
            required_if_attrs_not_set=["tool_definition_path"],
        ),
        RequestBodyAttribute(
            name="tool_definition_path",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
            required_if_attrs_not_set=["tool_definition"],
        ),
        RequestBodyAttribute(
            name="execute_as",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="working_directory",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
    ]

    def __init__(self, tool_definition: Optional[str] = None, tool_definition_path: Optional[str] = None,
                 arguments: Optional[dict] = None, execute_as: Optional[str] = None, working_directory: Optional[str] = None):
        """
        Initialize the execute tool request

        Keyword arguments:
        tool_definition -- An inline tool definition JSON object (mutually exclusive with tool_definition_path)
        tool_definition_path -- The full path to the tool definition file (mutually exclusive with tool_definition)
        arguments -- Optional arguments to pass to the tool
        execute_as -- The entity to execute the tool as (admin only)
        working_directory -- The working directory where the tool will be executed
        """
        super().__init__(
            tool_definition=tool_definition,
            tool_definition_path=tool_definition_path,
            arguments=arguments,
            execute_as=execute_as,
            working_directory=working_directory
        )


class DescribeProcessRequest(RequestBody):
    """
    Describe a process with the given ID
    """
    path = '/process/describe_process'

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="process_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, process_id: str):
        """
        Initialize the describe process request

        Keyword arguments:
        process_id -- The ID of the process to describe
        """
        super().__init__(process_id=process_id)


class ListProcessesRequest(RequestBody):
    """
    List all processes for the given tool
    """
    path = '/process/list_processes'

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="process_owner",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="parent_process_id",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="status",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
    ]

    def __init__(self, process_owner: Optional[str] = None, parent_process_id: Optional[str] = None,
                 status: Optional[str] = None):
        """
        Initialize the list processes request

        Keyword arguments:
        owner -- The owner of the processes to list
        parent_process_id -- The ID of the parent process to filter by
        status -- The status of the processes to list
        """
        super().__init__(process_owner=process_owner, parent_process_id=parent_process_id, status=status)


class ValidateToolRequest(RequestBody):
    """
    Validate an tool with the given definition
    """
    path = '/process/validate'

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="tool_definition",
            attribute_type=RequestAttributeType.OBJECT,
            optional=True,
            required_if_attrs_not_set=["tool_definition_path"],
        ),
        RequestBodyAttribute(
            name="tool_definition_path",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
            required_if_attrs_not_set=["tool_definition"],
        ),
    ]

    def __init__(self, tool_definition: Optional[str] = None, tool_definition_path: Optional[str] = None):
        """
        Initialize the validate tool request

        Keyword arguments:
        tool_definition -- An inline tool definition JSON object (mutually exclusive with tool_definition_path)
        tool_definition_path -- The full path to the tool definition file (mutually exclusive with tool_definition)
        """
        super().__init__(
            tool_definition=tool_definition,
            tool_definition_path=tool_definition_path
        )