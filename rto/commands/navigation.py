import json
from argparse import ArgumentParser

from ratio.client.client import Ratio
from ratio.client.requests.storage import DescribeFileRequest, ListFilesRequest

from rto.commands.base import RTOCommand, RTOErrorMessage
from rto.config import RTOConfig


class ChangeDirectoryCommand(RTOCommand):
    """
    Change the current working directory
    """
    alias = "cd"
    name = "change-directory"
    description = "Change the current working directory"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """Configure the command line argument parser."""
        parser.add_argument("directory", 
                           help="Directory to change to (use absolute path or relative to current working directory)",
                           nargs="?", default="/")  # Default to root if no directory specified

    def execute(self, client: Ratio, args):
        """Execute the command."""
        config = RTOConfig(args.profile)

        current_dir = config.get_working_directory()

        # Remove trailing slash from current directory (unless it's root)
        if current_dir != '/' and current_dir.endswith('/'):
            current_dir = current_dir[:-1]

        # Determine the new directory path
        if args.directory.startswith('/'):
            # Absolute path
            new_dir = args.directory

        else:
            # Relative path - resolve against current directory
            if current_dir == '/':
                new_dir = '/' + args.directory

            else:
                new_dir = current_dir + '/' + args.directory

        # Clean up the path (handle .. and .)
        parts = []

        for part in new_dir.split('/'):
            if part == '..':
                if parts:  # Don't go above root
                    parts.pop()

            elif part and part != '.':  # Skip empty parts and current dir (.)
                parts.append(part)

        # Construct the new path
        new_dir = '/' + '/'.join(parts)

        # Remove trailing slash (unless it's root)
        if new_dir != '/' and new_dir.endswith('/'):
            new_dir = new_dir[:-1]

        # Verify the directory exists
        try:
            resp = client.request(DescribeFileRequest(file_path=new_dir), raise_for_status=False)

            if resp.status_code == 404:
                raise RTOErrorMessage(f"directory {new_dir} does not exist")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"permission denied")

            elif resp.status_code != 200:
                raise RTOErrorMessage(f"error accessing directory {resp.status_code} -- {resp.response_body}")

            if resp.status_code != 200:
                raise RTOErrorMessage(f"Directory {new_dir} does not exist")

            # Confirm it's a directory
            file_info = resp.response_body

            if not file_info.get('is_directory', False):
                raise RTOErrorMessage(f"{new_dir} is not a directory")

        except Exception as e:
            if isinstance(e, RTOErrorMessage):
                raise e

            raise RTOErrorMessage(f"Error accessing directory: {str(e)}")

        # Save the new working directory
        config.set_working_directory(new_dir)

        print(f"Working directory changed to {new_dir}")


class ListFilesCommand(RTOCommand):
    """
    List all files in a directory
    """
    name = "list-files"
    alias = "ls"
    description = "List all files in a directory"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("--detailed", "-l", help="Show detailed file information", action="store_true", default=False)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

        parser.add_argument("directory", help="Directory to list (defaults to current working directory)", 
                            nargs="?", default=None, type=str)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        config = RTOConfig(config_dir=args.config_path)

        target_dir = config.resolve_path(path=args.directory)

        # Remove trailing slashes (except for root)
        if target_dir != "/" and target_dir.endswith("/"):
            target_dir = target_dir.rstrip("/")

        # Create the request
        request = ListFilesRequest(
            file_path=target_dir,
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"Directory {args.directory} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Access denied to directory {args.directory}")

            else:
                raise ValueError(f"Unknown error {resp.status_code} while listing files in {args.directory}")

        if args.json:
            print(resp.response_body)

            return

        # Otherwise, parse and format the response
        try:
            print(self.format_file_listing(data=resp.response_body, requested_path=target_dir, detailed=args.detailed))

        except json.JSONDecodeError:
            raise ValueError(f"Could not parse response as JSON {resp.response_body}")

    def format_file_listing(self, data, requested_path: str, detailed=False):
        """
        Format file listing data similar to the Unix ls command.

        Keyword arguments:
        data -- The data to format
        detailed -- Whether to show detailed information (like ls -l)
        
        Returns:
            Formatted string output
        """
        result = []

        # Format file listings
        files = data.get("files", [])

        if not files:
            result.append(f"No files found in {requested_path}")

            return "\n".join(result)

        if detailed:
            # Detailed view (like ls -l)
            # Calculate column widths for alignment
            perm_width = 10  # Fixed for permissions

            owner_width = max(len(f["owner"]) for f in files) if files else 0

            group_width = max(len(f["group"]) for f in files) if files else 0

            type_width = max(len(str(f.get("file_type", ""))) for f in files) if files else 0

            # Format each file entry
            for file in sorted(files, key=lambda x: x["file_path"]):
                # Convert permission string to format like drwxr-xr-x
                perm_str = self.convert_permissions(file.get("permissions", "???"), file.get("directory", False))

                file_type = file.get('file_type', '')

                result.append(
                    f"{perm_str:<{perm_width}} "
                    f"{file.get("owner", ""):<{owner_width}} "
                    f"{file.get("group", ""):<{group_width}} "
                    f"{file_type:<{type_width}} "
                    f"{file["file_path"]}"
                )

        else:
            # Simple view (like regular ls)
            # Just extract file/directory names from paths
            file_names = []

            for file in files:
                path = file["file_path"]

                if path == "/":
                    continue

                else:
                    # Split the path and get the last non-empty component
                    parts = path.split("/")

                    name = parts[-1] if parts[-1] else parts[-2]

                if file.get('directory', False):
                    name += "/"  # Add slash to indicate directories

                file_names.append(name)

            # Format in columns - simple approach
            max_width = max(len(name) for name in file_names) + 2  # Add some padding

            term_width = 80  # Assume 80 chars terminal width

            cols = max(1, term_width // max_width)

            # Sort names
            file_names.sort()

            # Create rows
            for i in range(0, len(file_names), cols):
                row = file_names[i:i+cols]

                result.append("  ".join(f"{name:<{max_width}}" for name in row))

        return "\n".join(result)

    def convert_permissions(self, perm_str, is_directory):
        """
        Convert numeric permissions to string format (like -rwxr-xr-x)

        Keyword arguments:
        perm_str -- The permission string to convert
        is_directory -- Whether the file is a directory
        """
        if not perm_str or len(perm_str) != 3:
            return "???????????"

        result = "d" if is_directory else "-"

        # Convert each digit to rwx format
        mapping = {
            "0": "---", "1": "--x", "2": "-w-", "3": "-wx",
            "4": "r--", "5": "r-x", "6": "rw-", "7": "rwx"
        }

        for digit in perm_str:
            if digit in mapping:
                result += mapping[digit]

            else:
                result += "???"

        return result


class PrintWorkingDirectoryCommand(RTOCommand):
    """
    Print the current working directory
    """
    name = "print-working-directory"
    alias = "pwd"
    description = "Print the current working directory"
    requires_authentication = False  # Doesn't need to access the server

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """Configure the command line argument parser."""
        # No additional arguments needed
        pass

    def execute(self, client: Ratio, args):
        """Execute the command."""
        config = RTOConfig(config_dir=args.config_path)

        working_dir = config.get_working_directory()

        print(working_dir)