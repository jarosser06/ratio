
from datetime import datetime, timedelta, UTC as utc_tz
from enum import StrEnum
from typing import List, Optional, Union
from uuid import uuid4

from da_vinci.core.orm.client import (
    TableClient,
    TableObject,
    TableObjectAttribute,
    TableObjectAttributeType,
    TableScanDefinition,
)


class ProcessStatus(StrEnum):
    """
    Enum for the status of a process.
    """

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RUNNING = "RUNNING"
    SKIPPED = "SKIPPED"
    TERMINATED = "TERMINATED"
    TIMED_OUT = "TIMED_OUT"


class Process(TableObject):
    table_name = "processes"

    description = "Table tracks each process and what it's status is."

    partition_key_attribute = TableObjectAttribute(
        name="parent_process_id",
        description="The id of the parent process. If the process is not a child of any other process, this will be CORE.",
        attribute_type=TableObjectAttributeType.STRING,
        default="SYSTEM",
    )

    sort_key_attribute = TableObjectAttribute(
        name="process_id",
        attribute_type=TableObjectAttributeType.STRING,
        description="The unique id of the process.",
        default=lambda: str(uuid4()),
    )

    ttl_attribute = TableObjectAttribute(
        name="time_to_live",
        attribute_type=TableObjectAttributeType.DATETIME,
        description="The time to live for the process.",
        optional=True,
        default=lambda: datetime.now(tz=utc_tz) + timedelta(hours=2),
    )

    attributes = [
        TableObjectAttribute(
            name="arguments_path",
            attribute_type=TableObjectAttributeType.STRING,
            description="The path to the arguments of the process.",
            optional=True,
        ),

        TableObjectAttribute(
            name="ended_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the process ended.",
            optional=True,
        ),

        TableObjectAttribute(
            name="execution_id",
            attribute_type=TableObjectAttributeType.STRING,
            description="The unique execution id of the process. Used to track composite process execution",
            optional=True,
        ),

        TableObjectAttribute(
            name="execution_status",
            attribute_type=TableObjectAttributeType.STRING,
            description="The status of the process.",
            default=ProcessStatus.RUNNING,
        ),

        TableObjectAttribute(
            name="process_owner",
            attribute_type=TableObjectAttributeType.STRING,
            description="The owner of the process.",
            optional=False,
        ),

        TableObjectAttribute(
            name="response_path",
            attribute_type=TableObjectAttributeType.STRING,
            description="The path to the response of the process.",
            optional=True,
        ),

        TableObjectAttribute(
            name="status_message",
            attribute_type=TableObjectAttributeType.STRING,
            description="The status message of the process.",
            optional=True,
        ),

        TableObjectAttribute(
            name="started_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the process was started.",
            default=lambda: datetime.now(utc_tz),
        ),

        TableObjectAttribute(
            name="websocket_connection_id",
            attribute_type=TableObjectAttributeType.STRING,
            description="The websocket connection id for the process. Used for real-time updates.",
            optional=True,
        ),

        TableObjectAttribute(
            name="working_directory",
            attribute_type=TableObjectAttributeType.STRING,
            description="The working directory of the process.",
            optional=False,
        ),
    ]

    def create_child(self, execution_id: str, working_directory: str, execution_status: Optional[str] = None,
                     process_owner: Optional[str] = None, process_id: Optional[str] = None) -> None:
        """
        Create a child process.

        Keyword arguments:
        execution_id -- The execution id of the child process.
        working_directory -- The working directory of the child process.
        execution_status -- The status of the child process. If not provided, the status will be set to RUNNING.
        parallel_group_id -- The id of the parallel group this process belongs to. Used for parallel execution.
        process_owner -- The owner of the child process.
        process_id -- The id of the child process. If not provided, a new id will be generated.
        """
        return Process(
            execution_id=execution_id,
            execution_status=execution_status,
            parent_process_id=self.process_id,
            process_owner=process_owner or self.process_owner,
            process_id=process_id or str(uuid4()),
            status_message=None,
            started_on=datetime.now(utc_tz),
            ended_on=None,
            websocket_connection_id=self.websocket_connection_id,
            working_directory=working_directory,
        )


class ProcessTableClient(TableClient):
    """
    Client for the Process table.
    """
    def __init__(self, app_name: Optional[str] = None, deployment_id: Optional[str] = None):
        """
        Initialize the ProcessTableClient.

        Keyword arguments:
        app_name -- The name of the app.
        deployment_id -- The id of the deployment.
        """
        super().__init__(app_name=app_name, deployment_id=deployment_id, default_object_class=Process)

    def delete(self, process: Process) -> None:
        """
        Delete a process object from the system.

        Keyword arguments:
        process -- The process object to delete.
        """
        return self.delete_object(process)

    def get(self, parent_process_id: str, process_id: str) -> Optional[Process]:
        """
        Get a process object from the system.

        Keyword arguments:
        parent_process_id -- The id of the parent process.
        process_id -- The id of the process.
        """
        return self.get_object(
            partition_key_value=parent_process_id,
            sort_key_value=process_id,
        )

    def get_by_id(self, process_id: str) -> Optional[Process]:
        """
        Get a process object from the system by its id.

        Keyword arguments:
        process_id -- The id of the process.
        """
        parameters = {
            "KeyConditionExpression": "ProcessId = :process_id",
            "ExpressionAttributeValues": {
                ":process_id": {"S": process_id},
            },
            "IndexName": "process_id-index",
        }

        for page in self.paginated(call='query', parameters=parameters):
            for item in page:
                return item

        return None

    def get_by_parent(self, parent_process_id: str) -> List[Process]:
        """
        Get all process objects from the system that are children of the given parent process.

        Keyword arguments:
        parent_process_id -- The id of the parent process.
        """

        parameters = {
            "KeyConditionExpression": "ParentProcessId = :parent_process_id",
            "ExpressionAttributeValues": {
                ":parent_process_id": {"S": parent_process_id},
            },
        }

        all_processes = []

        for page in self.paginated(call='query', parameters=parameters):
            all_processes.extend(page)

        return all_processes

    def list(self, process_owner: Optional[str] = None, parent_process_id: Optional[str] = None,
             execution_status: Optional[Union[ProcessStatus, str]] = None) -> List[Process]:
        """
        List all process objects from the system using optional filters.

        Keyword arguments:
        process_owner -- The owner of the process.
        parent_process_id -- The id of the parent process.
        status -- The status of the process.
        """
        scan_definition = TableScanDefinition(
            table_object_class=self.default_object_class
        )

        if process_owner:
            scan_definition.add(
                attribute_name="process_owner",
                comparison="equal",
                value=process_owner,
            )

        if parent_process_id:
            scan_definition.add(
                attribute_name="parent_process_id",
                comparison="equal",
                value=parent_process_id,
            )

        if execution_status:
            if isinstance(status, ProcessStatus):
                status = execution_status.value

            scan_definition.add(
                attribute_name="status",
                comparison="equal",
                value=execution_status,
            )

        return self.full_scan(scan_definition=scan_definition)

    def get_running_processes_older_than(self, minutes: int) -> List[Process]:
        """
        Get all processes that have been running longer than the specified minutes.

        Keyword arguments:
        minutes -- Number of minutes to check against
        """
        from datetime import datetime, timedelta, UTC as utc_tz

        cutoff_time = datetime.now(tz=utc_tz) - timedelta(minutes=minutes)
        
        scan_definition = TableScanDefinition(
            table_object_class=self.default_object_class
        )

        scan_definition.add(
            attribute_name="execution_status",
            comparison="equal",
            value=ProcessStatus.RUNNING,
        )

        scan_definition.add(
            attribute_name="started_on",
            comparison="less_than",
            value=cutoff_time,
        )

        return self.full_scan(scan_definition=scan_definition)

    def get_running_parent_processes(self) -> List[Process]:
        """
        Get all parent processes that are currently running.
        """
        scan_definition = TableScanDefinition(
            table_object_class=self.default_object_class
        )

        scan_definition.add(
            attribute_name="execution_status",
            comparison="equal",
            value=ProcessStatus.RUNNING,
        )

        # Filter for parent processes (those that have children)
        # This might need adjustment based on your data structure
        all_running = self.full_scan(scan_definition=scan_definition)

        # Filter to only include processes that have children
        parent_processes = []

        for proc in all_running:
            children = self.get_by_parent(parent_process_id=proc.process_id)

            if children:  # Has children, so it's a parent
                parent_processes.append(proc)

        return parent_processes

    def get_stuck_parent_processes(self) -> List[Process]:
        """
        Get parent processes where all children are complete but parent is still running.
        """
        running_parents = self.get_running_parent_processes()

        stuck_parents = []

        for parent in running_parents:
            children = self.get_by_parent(parent_process_id=parent.process_id)

            if not children:
                continue

            # Check if all children are in terminal states
            all_children_done = all(
                child.execution_status in [
                    ProcessStatus.COMPLETED, 
                    ProcessStatus.FAILED, 
                    ProcessStatus.SKIPPED,
                    ProcessStatus.TERMINATED,
                    ProcessStatus.TIMED_OUT
                ] 
                for child in children
            )

            if all_children_done:
                stuck_parents.append(parent)

        return stuck_parents

    def get_all_running_processes(self) -> List[Process]:
        """
        Get all processes currently in RUNNING status.
        """
        scan_definition = TableScanDefinition(
            table_object_class=self.default_object_class
        )

        scan_definition.add(
            attribute_name="execution_status",
            comparison="equal",
            value=ProcessStatus.RUNNING,
        )

        return self.full_scan(scan_definition=scan_definition)

    def put(self, process: Process) -> None:
        """
        Put a process object into the system.

        Keyword arguments:
        process -- The process object to put into the system.
        """
        return self.put_object(process)