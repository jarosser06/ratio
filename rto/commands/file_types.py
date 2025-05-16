import json

from argparse import ArgumentParser

from ratio.client.client import Ratio
from ratio.client.requests.storage import (
    DeleteFileTypeRequest,
    DescribeFileTypeRequest,
    ListFileTypesRequest,
    PutFileTypeRequest,
)

from rto.commands.base import RTOCommand, RTOErrorMessage


class DeleteFileTypeCommand(RTOCommand):
    """
    Delete a file type
    """
    name = "delete-file-type"
    alias = "rmtype"
    description = "Delete a file type"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("file_type", help="The file type to delete (e.g. 'myapp::document')", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Create the request
        request = DeleteFileTypeRequest(
            file_type=args.file_type
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"File type {args.file_type} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to delete file type {args.file_type}")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            elif resp.status_code == 409:
                raise RTOErrorMessage(f"Cannot delete file type {args.file_type} as it is in use")

            else:
                raise RTOErrorMessage(f"Error deleting file type: {resp.status_code}")

        # Handle successful response
        if args.json and resp.response_body:
            print(resp.response_body)

        else:
            print(f"Successfully deleted file type {args.file_type}")


class DescribeFileTypeCommand(RTOCommand):
    """
    Describe a file type
    """
    name = "describe-file-type"
    description = "Get detailed information about a file type"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("file_type", help="The file type to describe", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Create the request
        request = DescribeFileTypeRequest(
            file_type=args.file_type
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"File type {args.file_type} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to describe file type {args.file_type}")

            else:
                raise RTOErrorMessage(f"Error describing file type: {resp.status_code}")

        # Parse and print the response
        try:
            type_data = json.loads(resp.response_body) if isinstance(resp.response_body, str) else resp.response_body

            if args.json:
                print(json.dumps(type_data, indent=2))

            else:
                self._format_type_info(type_data)

        except json.JSONDecodeError:
            raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

    def _format_type_info(self, type_data):
        """
        Format file type information in a readable way.

        Keyword arguments:
        type_data -- The file type data to format
        """
        print(f"File Type: {type_data.get('file_type', 'Unknown')}")

        print(f"Description: {type_data.get('description', 'None')}")

        if 'is_container_type' in type_data:
            print(f"Is Container Type: {type_data.get('is_container_type')}")

        if 'content_search_instructions_path' in type_data:
            print(f"Content Search Instructions: {type_data.get('content_search_instructions_path')}")

        if 'name_restrictions' in type_data:
            print(f"Name Restrictions: {type_data.get('name_restrictions')}")

        # Print metadata if present
        metadata = type_data.get('metadata', {})

        if metadata:
            print("\nMetadata:")

            for key, value in metadata.items():
                print(f"  {key}: {value}")

        # Print any other fields
        print("\nAdditional Properties:")

        for key, value in type_data.items():
            if key not in ['file_type', 'description', 'is_container_type', 
                          'content_search_instructions_path', 'name_restrictions', 'metadata']:
                print(f"  {key}: {value}")


class ListFileTypesCommand(RTOCommand):
    """
    List all file types in the system
    """
    name = "list-file-types"
    alias = "lsft"
    description = "List all file types configured in the system"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

        parser.add_argument("--detailed", "-d", help="Show detailed information for each file type", action="store_true", default=False)

        parser.add_argument("--filter", help="Filter file types by substring (case-insensitive)", type=str)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        
        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        resp = client.request(ListFileTypesRequest(), raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 403:
                raise RTOErrorMessage("Permission denied: Not authorized to list file types")

            else:
                raise RTOErrorMessage(f"Error listing file types: {resp.status_code}")

        # Parse the response
        try:
            if isinstance(resp.response_body, str):
                data = json.loads(resp.response_body)

            else:
                data = resp.response_body

            file_types_dicts = data.get("file_types", [])

            # Apply filter if specified
            if args.filter:
                filter_term = args.filter.lower()
                file_types_dicts = [ft for ft in file_types_dicts if filter_term in ft['type_name'].lower()]

            # Extract just the names for simple view
            file_type_names = [ft['type_name'] for ft in file_types_dicts]

            if args.json:
                # Output raw JSON
                json_output = {"file_types": file_types_dicts}

                print(json.dumps(json_output, indent=2))

            elif not file_types_dicts:
                print("No file types found.")

            elif args.detailed:
                # Pass the full dictionaries for detailed view
                self._show_detailed_file_types(file_types_dicts)

            else:
                # Simple list output with formatting
                self._show_simple_file_types(file_type_names)

        except json.JSONDecodeError:
            raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

        except KeyError as e:
            raise RTOErrorMessage(f"Missing expected key in response: {e}")

    def _show_detailed_file_types(self, file_types_dicts):
        """
        Display detailed information for each file type.

        Keyword arguments:
        file_types_dicts -- List of file type dictionaries
        """
        if not file_types_dicts:
            print("No file types found.")
            return

        # Sort file types by name for better readability
        file_types_dicts = sorted(file_types_dicts, key=lambda ft: ft['type_name'])

        for i, type_data in enumerate(file_types_dicts):
            # Add a separator between types
            if i > 0:
                print("\n" + "-" * 40)

            print(f"File Type: {type_data.get('type_name', 'Unknown')}")

            # Display key information
            print(f"  Description: {type_data.get('description', 'None')}")

            if 'is_directory_type' in type_data:
                print(f"  Is Directory Type: {type_data.get('is_directory_type')}")

            if 'content_type' in type_data:
                content_type = type_data.get('content_type')
                if content_type:
                    print(f"  Content Type: {content_type}")

            if 'name_restrictions' in type_data:
                print(f"  Name Restrictions: {type_data.get('name_restrictions')}")

            if 'files_cannot_be_deleted' in type_data:
                print(f"  Files Cannot Be Deleted: {type_data.get('files_cannot_be_deleted')}")

            if 'added_on' in type_data:
                print(f"  Added On: {type_data.get('added_on')}")

            if 'last_updated_on' in type_data:
                print(f"  Last Updated On: {type_data.get('last_updated_on')}")

        print(f"\nTotal: {len(file_types_dicts)} file types")


class PutFileTypeCommand(RTOCommand):
    """
    Create or update a file type
    """
    name = "put-file-type"
    description = "Create or update a file type in the system"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("file_type", help="The type name to create or update", type=str)

        parser.add_argument("--description", help="Description of the file type", type=str, required=True)

        parser.add_argument("--is-container-type", help="Whether the file type is a container type", 
                           action="store_true", default=False)

        parser.add_argument("--name-restrictions", help="Regular expression for filename restrictions (default: ^[a-zA-Z0-9_-]+(\\.[a-zA-Z0-9_-]+)*$)", 
                           type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Create the request
        request = PutFileTypeRequest(
            file_type=args.file_type,
            description=args.description,
            content_search_instructions_path=args.content_search_instructions_path,
            is_container_type=args.is_container_type,
            name_restrictions=args.name_restrictions,
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code not in [200, 201]:
            if resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to create or update file type")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error creating or updating file type: {resp.status_code}")

        if args.json:
            print(resp.response_body)

            return

        # Print success message
        action = "updated" if resp.status_code == 200 else "created"

        print(f"File type {args.file_type} {action} successfully")