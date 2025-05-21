import json
import os
import sys

from argparse import ArgumentParser
from datetime import datetime

from ratio.client.client import Ratio
from ratio.client.requests.storage import (
    ChangeFilePermissionsRequest,
    DeleteFileRequest,
    DeleteFileVersionRequest,
    DescribeFileRequest,
    DescribeFileVersionRequest,
    GetFileVersionRequest,
    ListFileVersionsRequest,
    PutFileRequest,
    PutFileVersionRequest,
)

from rto.commands.base import RTOCommand, RTOErrorMessage

from rto.config import RTOConfig


class ChangeFilePermissionsCommand(RTOCommand):
    """
    Change file permissions
    """
    name = "change-file-permissions"
    alias = "chmod"
    description = "Change file permissions"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("permissions", help="The permissions to set (e.g. '644')", type=str)

        parser.add_argument("file", help="The path to the file or directory", type=str)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Resolve the file path
        file_path = config.resolve_path(args.file)

        # Check if the file exists
        describe_request = DescribeFileRequest(file_path=file_path)

        describe_resp = client.request(describe_request, raise_for_status=False)

        if describe_resp.status_code != 200:
            raise RTOErrorMessage(f"File or directory {file_path} does not exist")

        # Apply the permission change
        request = ChangeFilePermissionsRequest(
            file_path=file_path,
            permissions=args.permissions
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to change permissions for {file_path}")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error changing permissions: {resp.status_code}")

        print(f"Changed permissions of {file_path} to {args.permissions}")


class ChangeFileOwnerCommand(RTOCommand):
    """
    Change file owner
    """
    name = "change-file-owner"
    alias = "chown"
    description = "Change file owner"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("owner", help="The new owner", type=str)

        parser.add_argument("file", help="The path to the file or directory", type=str)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Resolve the file path
        file_path = config.resolve_path(args.file)

        # Check if the file exists
        describe_request = DescribeFileRequest(file_path=file_path)

        describe_resp = client.request(describe_request, raise_for_status=False)

        if describe_resp.status_code != 200:
            raise RTOErrorMessage(f"File or directory {file_path} does not exist")

        # Apply the owner change
        request = ChangeFilePermissionsRequest(
            file_path=file_path,
            owner=args.owner
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to change owner for {file_path}")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get("message", resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error changing owner: {resp.status_code}")

        print(f"Changed owner of {file_path} to {args.owner}")


class ChangeFileGroupCommand(RTOCommand):
    """
    Change file group
    """
    name = "change-file-group"
    alias = "chgrp"
    description = "Change file group"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("group", help="The new group", type=str)
        parser.add_argument("file", help="The path to the file or directory", type=str)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Resolve the file path
        file_path = config.resolve_path(args.file)

        # Check if the file exists
        describe_request = DescribeFileRequest(file_path=file_path)

        describe_resp = client.request(describe_request, raise_for_status=False)

        if describe_resp.status_code != 200:
            raise RTOErrorMessage(f"File or directory {file_path} does not exist")

        # Apply the group change
        request = ChangeFilePermissionsRequest(
            file_path=file_path,
            group=args.group
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to change group for {file_path}")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)
                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error changing group: {resp.status_code}")

        print(f"Changed group of {file_path} to {args.group}")


def pretty_print_file_info(file_data):
    """
    Pretty print file information in a readable way.

    Keyword arguments:
    file_data -- The file data to format as a dictionary
    """
    # Determine file type
    type_str = "Directory" if file_data.get('is_directory', False) else "File"

    # Format dates
    def format_date(date_str):
        if not date_str:
            return "Never"

        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

            return dt.strftime('%Y-%m-%d %H:%M:%S')

        except (ValueError, TypeError):
            return date_str

    # Print file summary
    print(f"  {type_str}: {file_data.get('file_path')}")

    print(f"  Type: {file_data.get('file_type', 'Unknown')}")

    print(f"  Name: {file_data.get('file_name', 'Unknown')}")

    # Print permissions, owner, group
    print(f"\nPermissions:")

    print(f"  Mode: {file_data.get('permissions', 'Unknown')}")

    print(f"  Owner: {file_data.get('owner', 'Unknown')}")

    print(f"  Group: {file_data.get('group', 'Unknown')}")

    # Print timestamps
    print(f"\nTimestamps:")

    print(f"  Added: {format_date(file_data.get('added_on'))}")

    print(f"  Modified: {format_date(file_data.get('last_updated_on'))}")

    print(f"  Accessed: {format_date(file_data.get('last_accessed_on'))}")

    print(f"  Read: {format_date(file_data.get('last_read_on'))}")

    # Print version info
    print(f"\nVersion:")

    print(f"  Latest Version ID: {file_data.get('latest_version_id', 'None')}")

    # Print metadata if present
    metadata = file_data.get("metadata", {})

    if metadata:
        print(f"\nMetadata:")

        for key, value in metadata.items():
            print(f"  {key}: {value}")

    # Print description if present
    description = file_data.get("description")

    if description:
        print(f"\nDescription: {description}")


class CreateDirectoryCommand(RTOCommand):
    """
    Create a new directory
    """
    alias = "mkdir"
    name = "create-directory"
    description = "Create a new directory"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

        parser.add_argument("--file-type", help="The file type to use (default: ratio::directory)", type=str, default="ratio::directory")

        parser.add_argument("--permissions", help="Directory permissions (e.g. '755')", type=str, default="755")

        parser.add_argument("--owner", help="Owner of the directory", type=str)

        parser.add_argument("--group", help="Group of the directory", type=str)

        parser.add_argument("--metadata", help="JSON metadata to associate with the directory", type=json.loads)

        parser.add_argument("--parents", "-p", help="Create parent directories as needed", action="store_true", default=False)

        parser.add_argument("directory", help="The full path to the directory to create", type=str)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Resolve the directory path
        directory_path = config.resolve_path(args.directory)

        # Check if the directory already exists
        describe_request = DescribeFileRequest(file_path=directory_path)

        describe_resp = client.request(describe_request, raise_for_status=False)

        if describe_resp.status_code == 200:
            print(f"Directory {args.directory} already exists, no action taken.")

            return

        # If parents flag is set, ensure parent directories exist
        if args.parents and '/' in directory_path:
            parent_path = directory_path.rsplit('/', 1)[0]

            if parent_path:  # Ensure the parent path is not empty
                try:
                    # Check if parent exists first
                    parent_describe = DescribeFileRequest(file_path=parent_path)

                    parent_describe_resp = client.request(parent_describe, raise_for_status=False)

                    if parent_describe_resp.status_code != 200:
                        # Create parent directories recursively
                        parent_request = PutFileRequest(
                            file_path=parent_path,
                            file_type="ratio::directory",
                            permissions=args.permissions,
                            owner=args.owner,
                            group=args.group
                        )

                        parent_resp = client.request(parent_request, raise_for_status=False)

                        if parent_resp.status_code not in [200, 201]:
                            raise RTOErrorMessage(f"Failed to create parent directory {parent_path}")

                except Exception as e:
                    raise RTOErrorMessage(f"Error creating parent directories: {str(e)}")

        # Create the target directory
        request = PutFileRequest(
            file_path=directory_path,
            file_type=args.file_type,
            permissions=args.permissions,
            owner=args.owner,
            group=args.group,
            metadata=args.metadata
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code not in [200, 201]:
            if resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to create directory {directory_path}")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error creating directory: {resp.status_code}")

        if args.json and resp.response_body:
            print(json.dumps(resp.response_body, indent=2))

            return

        pretty_print_file_info(resp.response_body)


class CreateFileCommand(RTOCommand):
    """
    Create a new file
    """
    name = "create-file"
    alias = "touch"  # Using 'touch' as alias to match Unix convention
    description = "Create a new file"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("--file-type", help="The file type to use (default: ratio::file)", type=str, default="ratio::file")

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

        parser.add_argument("--permissions", help="File permissions (e.g. '644')", type=str, default="644")

        parser.add_argument("--owner", help="Owner of the file", type=str)

        parser.add_argument("--group", help="Group of the file", type=str)

        parser.add_argument("--metadata", help="JSON metadata to associate with the file", type=json.loads)

        parser.add_argument("--content-metadata", help="JSON metadata to associate with the file content", type=json.loads)

        parser.add_argument("--parents", "-p", help="Create parent directories as needed", action="store_true", default=False)

        parser.add_argument("file", help="The full path to the file to create", type=str)

        parser.add_argument("content", help="Content to write to the file (optional)", nargs="?")

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        file_path = config.resolve_path(args.file)

        # Check if the file already exists
        describe_request = DescribeFileRequest(file_path=file_path)

        describe_resp = client.request(describe_request, raise_for_status=False)

        if describe_resp.status_code == 200:
            print(f"File {file_path} already exists, no action taken.")

            return

        # If parents flag is set, ensure parent directories exist
        if args.parents and '/' in file_path:
            parent_path = file_path.rsplit('/', 1)[0]

            if parent_path:  # Ensure the parent path is not empty
                try:
                    # Check if parent exists first
                    parent_describe = DescribeFileRequest(file_path=parent_path)

                    parent_describe_resp = client.request(parent_describe, raise_for_status=False)

                    if parent_describe_resp.status_code != 200:
                        # Create parent directories recursively
                        parent_request = PutFileRequest(
                            file_path=parent_path,
                            file_type="ratio::directory",
                            permissions="755",  # Standard directory permissions
                            owner=args.owner,
                            group=args.group
                        )

                        parent_resp = client.request(parent_request, raise_for_status=False)

                        if parent_resp.status_code not in [200, 201]:
                            raise RTOErrorMessage(f"Failed to create parent directory {parent_path}")

                except Exception as e:
                    raise RTOErrorMessage(f"Error creating parent directories: {str(e)}")

        # Create the file
        file_request = PutFileRequest(
            file_path=file_path,
            file_type=args.file_type,
            permissions=args.permissions,
            owner=args.owner,
            group=args.group,
            metadata=args.metadata
        )

        file_resp = client.request(file_request, raise_for_status=False)

        if file_resp.status_code not in [200, 201]:
            if file_resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to create file {file_path}")

            elif file_resp.status_code == 400:
                try:
                    error_msg = json.loads(file_resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', file_resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {file_resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error creating file: {file_resp.status_code}")

        # Determine content source - either from args or stdin if piped
        content = None

        if args.content is not None:
            content = args.content

        elif not sys.stdin.isatty():  # Check if data is being piped in
            content = sys.stdin.read()

        # Add content if we have any
        if content is not None:
            content_request = PutFileVersionRequest(
                file_path=file_path,
                data=content,
                metadata=args.content_metadata
            )

            content_resp = client.request(content_request, raise_for_status=False)

            if content_resp.status_code not in [200, 201]:
                raise RTOErrorMessage(f"File created but failed to add content: {content_resp.status_code}")

        if args.json and file_resp.response_body:
            print(json.dumps(file_resp.response_body, indent=2))

            return

        # Print the file information
        pretty_print_file_info(file_resp.response_body)

class DeleteFileCommand(RTOCommand):
    """
    Delete a file or directory
    """
    name = "delete-file"
    alias = "rm"
    description = "Delete a file or directory"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("file", help="The path to the file or directory to delete", type=str)

        parser.add_argument("--recursive", "-r", help="Recursively delete directories and their contents", 
                           action="store_true", default=False)

        parser.add_argument("--force", "-f", help="Force deletion even if the file is part of a lineage", 
                           action="store_true", default=False)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Resolve the file path
        file_path = config.resolve_path(args.file)

        # Create the request
        request = DeleteFileRequest(
            file_path=file_path,
            recursive=args.recursive,
            force=args.force
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"File or directory {file_path} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to delete {file_path}")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get("message", resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error deleting file: {resp.status_code}")

        # Parse and print the response
        try:
            if args.json and resp.response_body:
                print(json.dumps(resp.response_body, indent=2))

            else:
                print(f"Successfully deleted {file_path}")

        except json.JSONDecodeError:
            # If we can't parse as JSON but the operation was successful, just report success
            print(f"Successfully deleted {file_path}")


class DeleteFileVersionCommand(RTOCommand):
    """
    Delete a version of a file
    """
    name = "delete-file-version"
    alias = "rmv"
    description = "Delete a specific version of a file"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("file", help="The path to the file", type=str)

        parser.add_argument("--version-id", help="Specific version ID to delete (required)", type=str, required=True)

        parser.add_argument("--force", "-f", help="Force deletion even if dependencies exist", 
                           action="store_true", default=False)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Resolve the file path
        file_path = config.resolve_path(args.file)

        # Create the request
        request = DeleteFileVersionRequest(
            file_path=file_path,
            version_id=args.version_id,
            force=args.force
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"Version {args.version_id} of file {file_path} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to delete version of {file_path}")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            elif resp.status_code == 409:
                raise RTOErrorMessage(f"Cannot delete version {args.version_id} as it has dependencies. Use --force to override.")

            else:
                raise RTOErrorMessage(f"Error deleting file version: {resp.status_code}")

        # Handle successful response
        if args.json and resp.response_body:
            print(json.dumps(resp.response_body, ident=2))

        else:
            print(f"Successfully deleted version {args.version_id} of {file_path}")


class DescribeFileCommand(RTOCommand):
    """
    Describe a file or directory
    """
    name = "describe-file"
    alias = "stat"
    description = "Get detailed information about a file or directory"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("file", help="The path to the file or directory", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Resolve the file path
        file_path = config.resolve_path(args.file)

        # Create the request
        request = DescribeFileRequest(
            file_path=file_path
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"File or directory {file_path} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to describe {file_path}")

            else:
                raise RTOErrorMessage(f"Error describing file: {resp.status_code} - {resp.response_body}")

        # Parse and print the response
        try:
            file_data = json.loads(resp.response_body) if isinstance(resp.response_body, str) else resp.response_body

            if args.json:
                print(json.dumps(file_data, indent=2))

            else:
                self._format_file_info(file_data)

        except json.JSONDecodeError:
            raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

    def _format_file_info(self, file_data):
        """
        Format file information in a readable way.

        Keyword arguments:
        file_data -- The file data to format
        """
        # Determine file type
        type_str = "Directory" if file_data.get('is_directory', False) else "File"

        # Format dates
        def format_date(date_str):
            if not date_str:
                return "Never"

            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

                return dt.strftime('%Y-%m-%d %H:%M:%S')

            except (ValueError, TypeError):
                return date_str

        # Print file summary
        print(f"  {type_str}: {file_data.get("file_path")}")

        print(f"  Type: {file_data.get("file_type", "Unknown")}")

        print(f"  Name: {file_data.get("file_name", "Unknown")}")

        # Print permissions, owner, group
        print(f"\nPermissions:")

        print(f"  Mode: {file_data.get("permissions", "Unknown")}")

        print(f"  Owner: {file_data.get("owner", "Unknown")}")

        print(f"  Group: {file_data.get("group", "Unknown")}")

        # Print timestamps
        print(f"\nTimestamps:")

        print(f"  Added: {format_date(file_data.get("added_on"))}")

        print(f"  Modified: {format_date(file_data.get("last_updated_on"))}")

        print(f"  Accessed: {format_date(file_data.get("last_accessed_on"))}")

        print(f"  Read: {format_date(file_data.get("last_read_on"))}")

        # Print version info
        print(f"\nVersion:")

        print(f"  Latest Version ID: {file_data.get("latest_version_id", "None")}")

        # Print metadata if present
        metadata = file_data.get("metadata", {})

        if metadata:
            print(f"\nMetadata:")

            for key, value in metadata.items():
                print(f"  {key}: {value}")

        # Print description if present
        description = file_data.get("description")

        if description:
            print(f"\nDescription: {description}")


class DescribeFileVersionCommand(RTOCommand):
    """
    Describe a file version
    """
    name = "describe-file-version"
    alias = "statv"
    description = "Get detailed information about a file version"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("file", help="The path to the file", type=str)

        parser.add_argument("--version-id", help="Specific version ID to describe (defaults to latest)", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Resolve the file path
        file_path = config.resolve_path(args.file)

        # Create the request
        request = DescribeFileVersionRequest(
            file_path=file_path,
            version_id=args.version_id
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                if args.version_id:
                    raise RTOErrorMessage(f"Version {args.version_id} of file {file_path} not found")

                else:
                    raise RTOErrorMessage(f"File {file_path} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to describe version of {file_path}")

            else:
                raise RTOErrorMessage(f"Error describing file version: {resp.status_code}")

        # Parse and print the response
        try:
            version_data = json.loads(resp.response_body) if isinstance(resp.response_body, str) else resp.response_body

            if args.json:
                print(json.dumps(version_data, indent=2))

            else:
                self._format_version_info(version_data)

        except json.JSONDecodeError:
            raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

    def _format_version_info(self, version_data):
        """
        Format version information in a readable way.
        
        Keyword arguments:
        version_data -- The version data to format
        """
        # Format date
        def format_date(date_str):
            if not date_str:
                return "Never"

            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

                return dt.strftime('%Y-%m-%d %H:%M:%S')

            except (ValueError, TypeError):
                return date_str

        # Print version information
        print(f"File Version Information:")

        print(f"  File Path: {version_data.get('file_path')}")

        print(f"  File Name: {version_data.get('file_name')}")

        print(f"  Version ID: {version_data.get('version_id')}")

        print(f"  Created By: {version_data.get('originator_id')}")

        print(f"  Created On: {format_date(version_data.get('added_on'))}")

        print(f"  Origin: {version_data.get('origin')}")

        # Print version chain info if available
        if version_data.get('previous_version_id'):
            print(f"  Previous Version: {version_data.get('previous_version_id')}")

        if version_data.get('next_version_id'):
            print(f"  Next Version: {version_data.get('next_version_id')}")

        # Print metadata if present
        metadata = version_data.get('metadata', {})

        if metadata:
            print(f"\nMetadata:")

            for key, value in metadata.items():
                print(f"  {key}: {value}")


class GetFileVersionCommand(RTOCommand):
    """
    Get file version content
    """
    name = "get-file"
    alias = "cat"
    description = "Get the content of a file version"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("file", help="The path to the file to get", type=str)

        parser.add_argument("--version-id", help="Specific version ID to get (defaults to latest)", type=str)

        parser.add_argument("--output", "-o", help="Save content to the specified file instead of printing to stdout", type=str)

        parser.add_argument("--binary", "-b", help="Treat content as binary data", action="store_true", default=False)

        parser.add_argument("--with-metadata", "-m", help="Include file metadata in output", action="store_true", default=False)

        parser.add_argument("--quiet", "-q", help="Suppress informational messages", action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Resolve the file path
        file_path = config.resolve_path(args.file)

        # Create the request
        request = GetFileVersionRequest(
            file_path=file_path,
            version_id=args.version_id
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                if args.version_id:
                    raise RTOErrorMessage(f"Version {args.version_id} of file {file_path} not found")

                else:
                    raise RTOErrorMessage(f"File {file_path} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to access file {file_path}")

            else:
                raise RTOErrorMessage(f"Error getting file: {resp.status_code}")

        # Parse the response
        try:
            response_data = json.loads(resp.response_body) if isinstance(resp.response_body, str) else resp.response_body
            
            # Extract content and metadata
            content = response_data.get("data", "")

            details = response_data.get("details", {})
            
            # Handle binary mode if requested
            if args.binary and isinstance(content, str):
                content = content.encode('utf-8')
            
            # Output handling
            if args.output:
                # Save to file
                try:
                    mode = 'wb' if args.binary else 'w'

                    with open(args.output, mode) as f:
                        f.write(content)
                    
                    if not args.quiet:
                        file_size = os.path.getsize(args.output)

                        print(f"File saved to {args.output} ({file_size} bytes)")
                        
                        if args.with_metadata:
                            self._print_file_details(details)

                except Exception as e:
                    raise RTOErrorMessage(f"Error saving file to {args.output}: {str(e)}")

            else:
                # Print to stdout
                if args.with_metadata and not args.quiet:
                    self._print_file_details(details)

                    print("\nContent:")

                # For binary content, we might need special handling
                if args.binary:
                    sys.stdout.buffer.write(content)

                else:
                    print(content)

        except json.JSONDecodeError:
            raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

    def _print_file_details(self, details):
        """
        Print file details.
        
        Keyword arguments:
        details -- The file details to print
        """
        print(f"File: {details.get('path', 'Unknown')}")

        print(f"Name: {details.get('file_name', 'Unknown')}")

        print(f"Version: {details.get('version_id', 'Unknown')}")


class ListFileVersionsCommand(RTOCommand):
    """
    List versions of a file
    """
    name = "list-file-versions"
    alias = "lsv"
    description = "List all versions of a file"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("file", help="The path to the file", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Resolve the file path
        file_path = config.resolve_path(args.file)

        # Create the request
        request = ListFileVersionsRequest(
            file_path=file_path
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"File {file_path} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to list versions of {file_path}")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error listing file versions: {resp.status_code}")

        try:
            versions_data = resp.response_body if isinstance(resp.response_body, dict) else json.loads(resp.response_body)

        except json.JSONDecodeError:
            raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

        if args.json:
            print(json.dumps(resp.response_body, indent=2))

            return

        if not versions_data or "versions" not in versions_data or not versions_data["versions"]:
            print(f"No versions found for {file_path}")

            return
        
        versions = versions_data["versions"]
        
        # Format and display the versions
        print(f"Versions of {file_path}:")

        print(f"{'Version ID':<40} {'Created On':<20} {'Created By':<15}")

        print("-" * 75)

        for version in versions:
            # Format the date
            created_on = version.get("added_on", "Unknown")

            if created_on and created_on != "Unknown":
                try:
                    dt = datetime.fromisoformat(created_on.replace('Z', '+00:00'))

                    created_on = dt.strftime('%Y-%m-%d %H:%M:%S')

                except (ValueError, TypeError):
                    pass

            version_id = version.get("version_id", "Unknown")

            created_by = version.get("originator_id", "Unknown")

            print(f"{version_id:<40} {created_on:<20} {created_by:<15}")