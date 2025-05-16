from typing import Optional

from ratio.client.client import (
    RequestAttributeType,
    RequestBodyAttribute,
    RequestBody,
)


class ExecuteAgentRequest(RequestBody):
    """
    Execute an agent with the given definition and arguments
    """
    path = '/agent/execute'  # Assuming this is the endpoint path

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="arguments",
            attribute_type=RequestAttributeType.OBJECT,
            optional=True,
        ),
        RequestBodyAttribute(
            name="agent_definition",
            attribute_type=RequestAttributeType.OBJECT,
            optional=True,
            required_if_attrs_not_set=["agent_definition_path"],
        ),
        RequestBodyAttribute(
            name="agent_definition_path",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
            required_if_attrs_not_set=["agent_definition"],
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

    def __init__(self, agent_definition: Optional[str] = None, agent_definition_path: Optional[str] = None,
                 arguments: Optional[dict] = None, execute_as: Optional[str] = None, working_directory: Optional[str] = None):
        """
        Initialize the execute agent request

        Keyword arguments:
        agent_definition -- An inline agent definition JSON object (mutually exclusive with agent_definition_path)
        agent_definition_path -- The full path to the agent definition file (mutually exclusive with agent_definition)
        arguments -- Optional arguments to pass to the agent
        execute_as -- The entity to execute the agent as (admin only)
        working_directory -- The working directory where the agent will be executed
        """
        super().__init__(
            agent_definition=agent_definition,
            agent_definition_path=agent_definition_path,
            arguments=arguments,
            execute_as=execute_as,
            working_directory=working_directory
        )


class DescribeProcessRequest(RequestBody):
    """
    Describe a process with the given ID
    """
    path = '/agent/describe_process'  # Assuming this is the endpoint path

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
    List all processes for the given agent
    """
    path = '/agent/list_processes'  # Assuming this is the endpoint path

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


class ValidateAgentRequest(RequestBody):
    """
    Validate an agent with the given definition
    """
    path = '/agent/validate'  # Assuming this is the endpoint path

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="agent_definition",
            attribute_type=RequestAttributeType.OBJECT,
            optional=True,
            required_if_attrs_not_set=["agent_definition_path"],
        ),
        RequestBodyAttribute(
            name="agent_definition_path",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
            required_if_attrs_not_set=["agent_definition"],
        ),
    ]

    def __init__(self, agent_definition: Optional[str] = None, agent_definition_path: Optional[str] = None):
        """
        Initialize the validate agent request

        Keyword arguments:
        agent_definition -- An inline agent definition JSON object (mutually exclusive with agent_definition_path)
        agent_definition_path -- The full path to the agent definition file (mutually exclusive with agent_definition)
        """
        super().__init__(
            agent_definition=agent_definition,
            agent_definition_path=agent_definition_path
        )