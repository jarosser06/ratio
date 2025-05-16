
import json

from argparse import ArgumentParser

from ratio.client.client import Ratio
from ratio.client.requests.agent import (
    DescribeProcessRequest,
    ExecuteAgentRequest,
    ListProcessesRequest,
)

from rto.commands.base import RTOCommand, RTOErrorMessage

from rto.config import RTOConfig


class DescribeProcessCommand(RTOCommand):
    """
    Describe a process by its ID
    """
    name = "describe-process"
    alias = "dproc"
    description = "Get detailed information about a specific process"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("process_id", help="ID of the process to describe")

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Create the request
        request = DescribeProcessRequest(process_id=args.process_id)

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"Process {args.process_id} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to describe process {args.process_id}")

            else:
                raise RTOErrorMessage(f"Error describing process: {resp.status_code}")

        # Get the process details
        process = resp.response_body

        # If json flag is set, print the raw response
        if args.json:
            try:
                process_data = json.loads(resp.response_body) if isinstance(resp.response_body, str) else resp.response_body

                if args.json:
                    print(json.dumps(process_data, indent=2))

            except json.JSONDecodeError:
                raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

            return

        # Print process information in a more formal layout
        print(f"Process Information:")

        print(f"  Process ID: {process.get('process_id', 'Unknown')}")

        print(f"  Parent Process ID: {process.get('parent_process_id', 'Unknown')}")

        print(f"  Execution Status: {process.get('execution_status', 'Unknown')}")

        # Execution Details
        print(f"\nExecution Details:")

        print(f"  Execution ID: {process.get('execution_id', 'Unknown')}")

        print(f"  Owner: {process.get('process_owner', 'Unknown')}")

        print(f"  Working Directory: {process.get('working_directory', 'Unknown')}")

        # Timestamps
        print(f"\nTimestamps:")

        print(f"  Started On: {process.get('started_on', 'Unknown')}")

        print(f"  Ended On: {process.get('ended_on', 'None')}")

        # Details
        print(f"\nDetails:")

        print(f"  Status Message: {process.get('status_message', 'None')}")

        print(f"  Response Path: {process.get('response_path', 'None')}")


class ExecuteAgentCommand(RTOCommand):
    """
    Execute an agent
    """
    name = "execute"
    description = "Execute an agent with the given definition and arguments"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        # Define mutually exclusive group for agent definition
        agent_definition_group = parser.add_mutually_exclusive_group(required=True)

        agent_definition_group.add_argument("--agent-definition", help="JSON string containing the agent definition", type=json.loads)

        agent_definition_group.add_argument("--agent-definition-path", help="Path to the agent definition file on the server", type=str)
        
        # Other arguments
        parser.add_argument("--arguments", help="JSON string containing arguments for the agent", type=json.loads)

        parser.add_argument("--execute-as", help="Execute the agent as a specific entity (admin only)", type=str)

        parser.add_argument("--working-directory", help="Working directory for agent execution", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

        parser.add_argument("--max-wait-periods", help="Maximum wait periods for agent execution", type=int, default=10)

        parser.add_argument("--wait-period-seconds", help="Wait period in seconds for agent execution", type=int, default=15)

        parser.add_argument("--wait", help="Wait for the agent execution to complete", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        
        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        agent_definition_path = args.agent_definition_path

        if agent_definition_path:
            config = RTOConfig(config_dir=args.config_path)

            # Resolve the file path
            agent_definition_path = config.resolve_path(args.agent_definition_path)

        # Create the request - passing the path directly to the API
        request = ExecuteAgentRequest(
            agent_definition=args.agent_definition,
            agent_definition_path=agent_definition_path,
            arguments=args.arguments,
            execute_as=args.execute_as,
            working_directory=args.working_directory
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 403:
                raise RTOErrorMessage("Permission denied: Not authorized to execute agent")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error executing agent: {resp.status_code}")

        # For successful execution, get the process ID
        process_id = resp.response_body.get("process_id")

        if args.json:
            print(json.dumps(resp.response_body))

            return

        print(f"Agent execution started with process ID: {process_id}")
        
        # If wait flag is set, wait for the process to complete
        if args.wait:
            from ratio.client.requests.agent import DescribeProcessRequest
            import time

            print("Waiting for agent execution to complete...")

            max_wait_periods = args.max_wait_periods

            wait_period_seconds = args.wait_period_seconds

            for attempt in range(max_wait_periods):
                time.sleep(wait_period_seconds)

                # Check the process status
                describe_request = DescribeProcessRequest(process_id=process_id)

                describe_resp = client.request(describe_request, raise_for_status=False)

                if describe_resp.status_code != 200:
                    print(f"Error checking process status: {describe_resp.status_code}")

                    return

                process_status = describe_resp.response_body.get("execution_status")

                if process_status == "COMPLETED":
                    print("Agent execution completed successfully.")

                    # Display response path if available
                    response_path = describe_resp.response_body.get("response_path")

                    if response_path:
                        print(f"Response available at: {response_path}")

                    return

                elif process_status == "FAILED":
                    status_message = describe_resp.response_body.get("status_message", "Unknown error")

                    raise RTOErrorMessage(f"Agent execution failed: {status_message}")

                elif process_status == "TERMINATED":
                    raise RTOErrorMessage("Agent execution was terminated")

                print(f"Process status: {process_status} (waited {(attempt + 1) * wait_period_seconds} seconds)")

            print(f"Timeout waiting for agent execution to complete. Check status with: rto describe-process {process_id}")


class ListProcessesCommand(RTOCommand):
    """
    List processes in the system
    """
    name = "list-processes"
    alias = "lsproc"
    description = "List processes in the system with optional filtering"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("--owner", help="Filter processes by owner", type=str)
        parser.add_argument("--parent-process-id", help="Filter processes by parent process ID", type=str)
        parser.add_argument("--status", help="Filter processes by status (COMPLETED, FAILED, RUNNING, TERMINATED)", type=str)
        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)
        parser.add_argument("--detailed", "-d", help="Show detailed information for each process", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        
        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Create the request
        request = ListProcessesRequest(
            # Use process_owner instead of owner for the filter
            process_owner=args.owner,
            parent_process_id=args.parent_process_id,
            status=args.status
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 403:
                raise RTOErrorMessage("Permission denied: Not authorized to list processes")

            else:
                raise RTOErrorMessage(f"Error listing processes: {resp.status_code}")

        # The response_body is directly a list of processes
        processes = resp.response_body

        if args.json:
            print(json.dumps(processes, indent=2))

            return

        if not processes:
            print("No processes found.")

        elif args.detailed:
            # Display detailed information for each process
            self._show_detailed_processes(processes)

        else:
            # Display simple table of processes
            self._show_simple_processes(processes)

    def _show_simple_processes(self, processes):
        """
        Display a simple table of processes.

        Keyword arguments:
        processes -- List of process dictionaries
        """
        if not processes:
            print("No processes found.")
            return

        # Format and print the header
        header_format = "{:<36} {:<36} {:<12} {:<24} {:<24}"

        print(header_format.format(
            "PROCESS ID", 
            "PARENT PROCESS ID", 
            "STATUS", 
            "OWNER", 
            "STARTED ON"
        ))

        print("-" * 132)

        # Sort processes by start time (newest first)
        processes = sorted(processes, key=lambda p: p.get('started_on', ''), reverse=True)

        # Format and print each process
        for process in processes:
            print(header_format.format(
                process.get('process_id', 'Unknown'),
                process.get('parent_process_id', 'Unknown'),
                process.get('execution_status', 'Unknown'),
                process.get('process_owner', 'Unknown'),
                process.get('started_on', 'Unknown')
            ))

        print(f"\nTotal: {len(processes)} processes")

    def _show_detailed_processes(self, processes):
        """
        Display detailed information for each process.

        Keyword arguments:
        processes -- List of process dictionaries
        """
        if not processes:
            print("No processes found.")

            return

        # Sort processes by start time (newest first)
        processes = sorted(processes, key=lambda p: p.get('started_on', ''), reverse=True)

        for i, process in enumerate(processes):
            # Add a separator between processes
            if i > 0:
                print("\n" + "-" * 80)

            print(f"Process ID: {process.get('process_id', 'Unknown')}")

            print(f"Parent Process ID: {process.get('parent_process_id', 'Unknown')}")

            print(f"Status: {process.get('status', 'Unknown')}")

            if 'status_message' in process and process['status_message']:
                print(f"Status Message: {process['status_message']}")

            # Use process_owner in output
            print(f"Owner: {process.get('process_owner', 'Unknown')}")

            print(f"Started On: {process.get('started_on', 'Unknown')}")

            if 'ended_on' in process and process['ended_on']:
                print(f"Ended On: {process['ended_on']}")

            if 'execution_id' in process and process['execution_id']:
                print(f"Execution ID: {process['execution_id']}")

            if 'working_directory' in process:
                print(f"Working Directory: {process['working_directory']}")

            if 'response_path' in process and process['response_path']:
                print(f"Response Path: {process['response_path']}")

        print(f"\nTotal: {len(processes)} processes")