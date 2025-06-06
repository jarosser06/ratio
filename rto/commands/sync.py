import base64
import fnmatch
import json
import os


from argparse import ArgumentParser
from typing import Tuple

import requests

from ratio.client.client import Ratio
from ratio.client.requests.storage import (
    DescribeFileRequest,
    DescribeFileVersionRequest,
    GetDirectFileVersionRequest,
    GetFileVersionRequest,
    ListFilesRequest,
    PutDirectFileVersionCompleteRequest,
    PutDirectFileVersionStartRequest,
    PutFileRequest,
    PutFileVersionRequest,
)

from rto.commands.base import RTOCommand, RTOErrorMessage
from rto.config import RTOConfig


class SyncCommand(RTOCommand):
    """
    Sync files between local filesystem and Ratio
    """
    name = "sync"
    description = "Sync files between local filesystem and Ratio"
    requires_authentication = True

    DEFAULT_ENCODING_MAP = {
        # Text files - use text encoding
        "txt": "text",
        "text": "text",
        "md": "text",
        "json": "text",
        "xml": "text",
        "html": "text",
        "css": "text",
        "js": "text",
        "py": "text",

        # Binary files - use binary encoding
        "pdf": "binary",
        "gif": "binary",
        "jpg": "binary",
        "jpeg": "binary",
        "png": "binary",
        "webp": "binary",
        "pdf": "binary",
        "mp4": "binary",
        "mp3": "binary",
        "zip": "binary",
    }

    DEFAULT_TYPE_MAP = {
        # Tool files
        "tool": "ratio::tool",

        # Text files
        "txt": "ratio::text",
        "text": "ratio::text",

        # Markdown files
        "md": "ratio::markdown",

        # Image files
        "gif": "ratio::gif",
        "jpg": "ratio::jpeg",
        "jpeg": "ratio::jpeg",
        "png": "ratio::png",
        "webp": "ratio::webp",

        # Document files
        "pdf": "ratio::pdf",
    }

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        # Accept multiple paths - last one is destination, all others are sources
        parser.add_argument("paths", nargs='+', 
                          help="Source paths followed by destination path (use ratio:/path for Ratio paths)")

        parser.add_argument("--recursive", "-r", help="Sync directories recursively", action="store_true", default=False)

        parser.add_argument("--max-depth", help="Maximum recursion depth (default: 3)", type=int, default=3)

        parser.add_argument("--file-type", help="File type to use for new Ratio files (default: ratio::file)", type=str, default="ratio::file")

        parser.add_argument("--dir-type", help="Directory type to use for new Ratio directories (default: ratio::directory)", type=str, default="ratio::directory")

        parser.add_argument("--permissions", help="Permissions for new Ratio files (default: 644)", type=str, default="644")

        parser.add_argument("--dir-permissions", help="Permissions for new Ratio directories (default: 755)", type=str, default="755")

        parser.add_argument("--force", "-f", help="Overwrite existing files", action="store_true", default=False)

        parser.add_argument("--dry-run", help="Show what would be done without making changes", action="store_true", default=False)

        parser.add_argument("--verbose", "-v", help="Show detailed progress", action="store_true", default=False)

        parser.add_argument("--include", help="Include files matching pattern", type=str, action="append")

        parser.add_argument("--exclude", help="Exclude files matching pattern", type=str, action="append")

        parser.add_argument("--binary", "-b", help="Treat all files as binary data", action="store_true", default=False)

        parser.add_argument("--direct-threshold", help="Use direct file operations for files larger than this size (MB)", type=float, default=2.0)

        # Type and encoding mapping arguments
        parser.add_argument("--type-map", help="JSON string mapping file extensions to Ratio file types (e.g. '{\"pdf\":\"ratio::pdf\",\"docx\":\"ratio::document\"}')", type=str)

        parser.add_argument("--type-map-file", help="Path to JSON file mapping file extensions to Ratio file types", type=str)

        parser.add_argument("--encoding-map", help="JSON string mapping file extensions to encoding types ('text', 'binary', 'base64')", type=str)

        parser.add_argument("--encoding-map-file", help="Path to JSON file mapping file extensions to encoding types", type=str)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        args -- The command line arguments
        """
        # Split paths into sources and destination
        if len(args.paths) < 2:
            raise RTOErrorMessage("At least one source and one destination path required")

        sources = args.paths[:-1]

        destination = args.paths[-1]

        if args.verbose:
            print(f"Sources: {sources}")

            print(f"Destination: {destination}")

        # Parse destination path
        dest_is_ratio, dest_path = self._parse_path(destination)

        # Resolve destination path using config
        if dest_is_ratio:
            dest_path = config.resolve_path(dest_path)

        else:
            dest_path = os.path.abspath(os.path.expanduser(dest_path))

        # Load extension to file type mapping and encoding mapping if provided
        type_map = self._load_mapping(args.type_map, args.type_map_file, "type map", self.DEFAULT_TYPE_MAP)

        encoding_map = self._load_mapping(args.encoding_map, args.encoding_map_file, "encoding map", self.DEFAULT_ENCODING_MAP)

        # Validate encoding values
        self._validate_encodings(encoding_map)

        # Check if destination is a directory
        dest_exists, dest_is_directory = self._check_path_exists(client, dest_path, dest_is_ratio)

        # If destination doesn't exist and we have multiple sources, assume it should be a directory
        if not dest_exists and len(sources) > 1:
            dest_is_directory = True

            if args.verbose:
                print(f"Destination doesn't exist and multiple sources provided - treating as directory")

        # Handle dry run flag
        if args.dry_run:
            print("Dry run mode - no files will be modified")

        # Show mappings if verbose
        if args.verbose:
            if type_map:
                print("Using file extension to type mapping:")

                for ext, file_type in type_map.items():
                    print(f"  .{ext} -> {file_type}")

            if encoding_map:
                print("Using file extension to encoding mapping:")

                for ext, encoding in encoding_map.items():
                    print(f"  .{ext} -> {encoding}")

        # Initialize counters
        total_files_synced = 0

        total_dirs_created = 0

        # Process each source
        for source in sources:
            # Parse source path
            source_is_ratio, source_path = self._parse_path(source)

            # Resolve source path
            if source_is_ratio:
                source_path = config.resolve_path(source_path)

            else:
                source_path = os.path.abspath(os.path.expanduser(source_path))

            # Check if source exists
            source_exists, _ = self._check_path_exists(client, source_path, source_is_ratio)

            if not source_exists:
                print(f"Warning: Source path {source} not found, skipping")

                continue

            # Determine final destination path for this source
            if dest_is_directory or len(sources) > 1:
                # If destination is directory or we have multiple sources, 
                # append source filename to destination
                source_name = os.path.basename(source_path)

                if dest_is_ratio:
                    final_dest_path = f"{dest_path.rstrip('/')}/{source_name}"

                else:
                    final_dest_path = os.path.join(dest_path, source_name)

            else:
                final_dest_path = dest_path

            if args.verbose:
                print(f"Syncing: {source} -> {final_dest_path}")

            # Check for ratio-to-ratio sync
            if source_is_ratio and dest_is_ratio:
                raise RTOErrorMessage("Cannot sync from Ratio to Ratio - both paths are Ratio paths")

            # Do the sync based on direction
            if source_is_ratio:
                files_synced, dirs_created = self._sync_ratio_to_local(
                    client, source_path, final_dest_path, args, encoding_map, 0, 0
                )

            else:
                files_synced, dirs_created = self._sync_local_to_ratio(
                    client, source_path, final_dest_path, args, type_map, encoding_map, 0, 0
                )

            total_files_synced += files_synced

            total_dirs_created += dirs_created

        print(f"Sync complete: {total_files_synced} files synced, {total_dirs_created} directories created")

    def _load_mapping(self, json_str, file_path, map_name, default_map=None):
        """
        Load a mapping from JSON string or file

        Returns:
        dict -- The loaded mapping
        """
        mapping = {}

        # Load from JSON string if provided
        if json_str:
            try:
                mapping = json.loads(json_str)

                if not isinstance(mapping, dict):
                    raise RTOErrorMessage(f"{map_name} must be a JSON object")

            except json.JSONDecodeError:
                raise RTOErrorMessage(f"Invalid JSON format for {map_name}")

        # Load from file if provided (overrides JSON string)
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    mapping = json.load(f)

                if not isinstance(mapping, dict):
                    raise RTOErrorMessage(f"{map_name} in file must be a JSON object")

            except json.JSONDecodeError:
                raise RTOErrorMessage(f"Invalid JSON format in {map_name} file")

            except Exception as e:
                raise RTOErrorMessage(f"Error reading {map_name} file: {str(e)}")

        # If no mapping provided, use default mapping
        if not mapping and default_map:
            return default_map

        # Normalize extensions by stripping leading dots
        normalized_map = {}

        for ext, value in mapping.items():
            normalized_ext = ext.lower().lstrip('.')
            normalized_map[normalized_ext] = value

        return normalized_map

    def _validate_encodings(self, encoding_map):
        """
        Validate encoding values
        """
        valid_encodings = ['text', 'binary']

        for ext, encoding in encoding_map.items():
            if encoding not in valid_encodings:
                raise RTOErrorMessage(f"Invalid encoding '{encoding}' for extension '{ext}'. Valid values are: {', '.join(valid_encodings)}")

    def _parse_path(self, path):
        """
        Parse a path to determine if it's a Ratio path and extract the actual path.

        Returns:
        tuple -- (is_ratio, actual_path)
        """
        is_ratio = path.startswith("ratio:")

        actual_path = path[6:] if is_ratio else path

        return is_ratio, actual_path

    def _check_path_exists(self, client, path, is_ratio):
        """
        Check if a path exists and determine if it's a directory.

        Returns:
        tuple -- (exists, is_directory)
        """
        if is_ratio:
            describe_request = DescribeFileRequest(file_path=path)

            describe_resp = client.request(describe_request, raise_for_status=False)

            if describe_resp.status_code != 200:
                return False, False

            try:
                path_info = json.loads(describe_resp.response_body) if isinstance(describe_resp.response_body, str) else describe_resp.response_body

                is_directory = path_info.get('is_directory', False)

                return True, is_directory

            except json.JSONDecodeError:
                return False, False

        else:
            exists = os.path.exists(path)

            is_directory = os.path.isdir(path) if exists else False

            return exists, is_directory

    def _adjust_destination_path(self, client, source_path, dest_path, source_is_directory, dest_is_ratio, verbose=False):
        """
        Adjust the destination path if it's a directory and the source is a file.

        Returns:
        str -- The adjusted destination path
        """
        if dest_is_ratio:
            # For Ratio destination, check if it's a directory or ends with /
            is_dest_dir = dest_path.endswith('/')

            if not is_dest_dir:
                # Check if it exists and is a directory
                _, is_dest_dir = self._check_path_exists(client, dest_path, True)

            # If destination is a directory and source is a file, append source filename
            if is_dest_dir and not source_is_directory:
                source_name = os.path.basename(source_path)

                if source_name:
                    dest_path = f"{dest_path.rstrip('/')}/{source_name}"

                    if verbose:
                        print(f"Destination is a directory, syncing to {dest_path}")

        else:
            # For local destination
            is_dest_dir = dest_path.endswith('/')

            if not is_dest_dir:
                _, is_dest_dir = self._check_path_exists(client, dest_path, False)

            # If destination is a directory and source is a file, append source filename
            if is_dest_dir and not source_is_directory:
                source_name = os.path.basename(source_path)

                if source_name:

                    dest_path = os.path.join(dest_path, source_name)

                    if verbose:
                        print(f"Destination is a directory, syncing to {dest_path}")

        return dest_path

    def _get_encoding_for_path(self, file_path, encoding_map, default_is_binary):
        """
        Determine the appropriate encoding based on file extension and encoding map

        Returns:
        str -- The encoding to use ('text' or 'binary')
        """
        if default_is_binary:
            default_encoding = 'binary'

        else:
            default_encoding = 'text'

        if not encoding_map:
            return default_encoding

        # Get file extension
        _, ext = os.path.splitext(file_path)

        if not ext:
            return default_encoding

        # Remove the leading dot and convert to lowercase
        ext = ext[1:].lower()

        # Look up in encoding map
        return encoding_map.get(ext, default_encoding)

    def _sync_ratio_to_local(self, client, ratio_path, local_path, args, encoding_map, 
                             files_synced=0, dirs_created=0, current_depth=0):
        """
        Sync from Ratio to local filesystem

        Returns:
        tuple -- (files_synced, dirs_created)
        """
        # Check if source exists
        source_exists, is_directory = self._check_path_exists(client, ratio_path, True)

        if not source_exists:
            raise RTOErrorMessage(f"Source path {ratio_path} not found in Ratio")

        if is_directory:
            # Handle directory sync
            if args.verbose:
                print(f"Syncing directory: {ratio_path} -> {local_path}")

            # Create local directory if it doesn't exist
            if not os.path.exists(local_path):
                if not args.dry_run:
                    os.makedirs(local_path, exist_ok=True)

                    dirs_created += 1

                if args.verbose:
                    print(f"Created local directory: {local_path}")

            # If recursive and within max depth, list files and sync each one
            if args.recursive and (args.max_depth == 0 or current_depth < args.max_depth):
                list_request = ListFilesRequest(file_path=ratio_path)

                list_resp = client.request(list_request, raise_for_status=False)

                if list_resp.status_code != 200:
                    raise RTOErrorMessage(f"Error listing files in {ratio_path}")

                files_data = json.loads(list_resp.response_body) if isinstance(list_resp.response_body, str) else list_resp.response_body

                files = files_data.get('files', [])

                for file_info in files:
                    file_path = file_info.get('file_path')

                    if file_path and file_path != ratio_path:
                        file_name = os.path.basename(file_path)

                        if self._should_skip_file(file_name, args.include, args.exclude):
                            if args.verbose:
                                print(f"Skipping excluded file: {file_name}")

                            continue

                        new_local_path = os.path.join(local_path, file_name)

                        f_synced, d_created = self._sync_ratio_to_local(
                            client, file_path, new_local_path, args, encoding_map, 0, 0, current_depth + 1
                        )

                        files_synced += f_synced

                        dirs_created += d_created

        else:
            # Handle file sync
            if args.verbose:
                print(f"Syncing file: {ratio_path} -> {local_path}")

            # Check if local file exists and handle force flag
            if os.path.exists(local_path) and not args.force:
                if args.verbose:
                    print(f"Skipping existing file: {local_path}")

                return files_synced, dirs_created

            # Get file content
            content, base_64_encoded = self._get_file_content(client, ratio_path)

            # Write to local file with appropriate encoding
            if not args.dry_run:
                self._write_local_file(local_path, content, base_64_encoded)

                files_synced += 1

            if args.verbose:
                print(f"Wrote content to {local_path}")

        return files_synced, dirs_created

    def _sync_local_to_ratio(self, client, local_path, ratio_path, args, type_map, encoding_map,
                            files_synced=0, dirs_created=0, current_depth=0):
        """
        Sync from local filesystem to Ratio

        Returns:
        tuple -- (files_synced, dirs_created)
        """
        # Check if source exists
        if not os.path.exists(local_path):
            raise RTOErrorMessage(f"Source path {local_path} not found in local filesystem")

        if os.path.isdir(local_path):
            # Handle directory sync
            if args.verbose:
                print(f"Syncing directory: {local_path} -> {ratio_path}")

            # Check if Ratio directory already exists
            dir_exists, _ = self._check_path_exists(client, ratio_path, True)

            # Create Ratio directory if needed
            if not dir_exists:
                if not args.dry_run:
                    # Create directory in Ratio
                    self._create_ratio_directory(client, ratio_path, args.dir_type, args.dir_permissions)

                    dirs_created += 1

                if args.verbose:
                    print(f"Created Ratio directory: {ratio_path}")

            elif args.verbose:
                print(f"Ratio directory already exists: {ratio_path}")

            # If recursive and within max depth, process each file in the directory
            if args.recursive and (args.max_depth == 0 or current_depth < args.max_depth):
                for item in os.listdir(local_path):
                    # Skip hidden files/dirs
                    if item.startswith('.'):
                        continue

                    # Apply include/exclude filters if specified
                    if self._should_skip_file(item, args.include, args.exclude):
                        if args.verbose:
                            print(f"Skipping excluded file: {item}")

                        continue

                    local_item_path = os.path.join(local_path, item)

                    ratio_item_path = f"{ratio_path}/{item}"

                    f_synced, d_created = self._sync_local_to_ratio(
                        client, local_item_path, ratio_item_path, args, type_map, encoding_map, 0, 0, current_depth + 1
                    )

                    files_synced += f_synced

                    dirs_created += d_created

        else:
            # Handle file sync
            if args.verbose:
                print(f"Syncing file: {local_path} -> {ratio_path}")

            # Check if Ratio file exists
            file_exists, _ = self._check_path_exists(client, ratio_path, True)

            if file_exists and not args.force:
                if args.verbose:
                    print(f"Skipping existing file: {ratio_path}")

                return files_synced, dirs_created

            if not args.dry_run:
                # Determine file type based on extension if type_map is provided
                file_type = self._get_file_type_for_path(local_path, args.file_type, type_map)

                if args.verbose and file_type != args.file_type:
                    print(f"Using file type {file_type} based on file extension")

                # Create or update the file in Ratio
                self._create_ratio_file(client, ratio_path, file_type, args.permissions)

                # Determine encoding based on file extension and encoding map
                encoding = self._get_encoding_for_path(local_path, encoding_map, args.binary)

                if args.verbose:
                    print(f"Using encoding: {encoding}")

                # Read local file content and upload it with appropriate encoding
                self._upload_file_content(client, local_path, ratio_path, encoding)

                files_synced += 1

            if args.verbose:
                print(f"Uploaded content to {ratio_path}")

        return files_synced, dirs_created

    def _get_file_type_for_path(self, file_path, default_type, type_map=None):
        """
        Determine the appropriate Ratio file type based on file extension and type map

        Returns:
        str -- The file type to use
        """
        if not type_map:
            return default_type

        # Get file extension
        _, ext = os.path.splitext(file_path)

        if not ext:
            return default_type

        # Remove the leading dot and convert to lowercase
        ext = ext[1:].lower()

        # Look up in type map
        return type_map.get(ext, default_type)

    def _get_file_content(self, client, file_path, threshold_mb=2.0) -> Tuple[str, bool]:
        """
        Get file content from Ratio, using direct get for large files

        Returns:
        tuple -- (content, base_64_encoded)
        """
        # First get file info to check size
        describe_request = DescribeFileVersionRequest(file_path=file_path)

        describe_resp = client.request(describe_request, raise_for_status=False)

        if describe_resp.status_code != 200:
            raise RTOErrorMessage(f"Error getting file info for {file_path}")

        file_info = json.loads(describe_resp.response_body) if isinstance(describe_resp.response_body, str) else describe_resp.response_body

        file_size = file_info.get("size", 0)

        threshold_bytes = threshold_mb * 1024 * 1024

        if file_size > threshold_bytes:
            # Use direct get for large files

            return self._get_file_content_direct(client, file_path)

        else:
            # Use regular get for small files
            return self._get_file_content_regular(client, file_path)

    def _get_file_content_regular(self, client, file_path) -> Tuple[str, bool]:
        """
        Get file content using regular JSON API
        """
        get_request = GetFileVersionRequest(file_path=file_path)

        get_resp = client.request(get_request, raise_for_status=False)

        if get_resp.status_code != 200:
            raise RTOErrorMessage(f"Error getting content of {file_path}")

        response_data = json.loads(get_resp.response_body) if isinstance(get_resp.response_body, str) else get_resp.response_body

        content = response_data.get("data", "")

        base_64_encoded = response_data.get("base_64_encoded", True)

        return content, base_64_encoded

    def _get_file_content_direct(self, client, file_path) -> Tuple[bytes, bool]:
        """
        Get file content using direct download
        """
        get_request = GetDirectFileVersionRequest(file_path=file_path)

        get_resp = client.request(get_request, raise_for_status=False)

        if get_resp.status_code != 200:
            raise RTOErrorMessage(f"Error getting direct content of {file_path}")

        # Direct get returns raw binary data, not JSON
        if isinstance(get_resp.response_body, str):
            content = get_resp.response_body.encode('utf-8')

        else:
            content = get_resp.response_body

        # Direct downloads are always binary data, not base64 encoded
        return content, False

    def _write_local_file(self, file_path, content, base_64_encoded):
        """
        Write content to a local file with appropriate encoding
        """
        try:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

            if base_64_encoded:
                # Server sent base64 encoded binary data
                mode = 'wb'

                if isinstance(content, str):
                    content = base64.b64decode(content)

            elif isinstance(content, bytes):
                # Direct download - raw binary data
                mode = 'wb'

            else:
                # Server sent text data
                mode = 'w'

                if not isinstance(content, str):
                    content = content.decode('utf-8')

            with open(file_path, mode) as f:
                f.write(content)

        except Exception as e:
            raise RTOErrorMessage(f"Error writing to {file_path}: {str(e)}")

    def _create_ratio_directory(self, client, directory_path, dir_type, permissions):
        """
        Create a directory in Ratio
        """
        dir_request = PutFileRequest(
            file_path=directory_path,
            file_type=dir_type,
            permissions=permissions
        )

        dir_resp = client.request(dir_request, raise_for_status=False)

        if dir_resp.status_code not in [200, 201]:
            raise RTOErrorMessage(f"Error creating directory {directory_path} in Ratio")

    def _create_ratio_file(self, client, file_path, file_type, permissions):
        """
        Create a file in Ratio
        """
        file_request = PutFileRequest(
            file_path=file_path,
            file_type=file_type,
            permissions=permissions
        )

        file_resp = client.request(file_request, raise_for_status=False)

        if file_resp.status_code not in [200, 201]:
            raise RTOErrorMessage(f"Error creating file {file_path} in Ratio")

    def _upload_file_content(self, client, local_path, ratio_path, encoding, threshold_mb=2.0):
        """
        Upload content from a local file to Ratio with appropriate encoding,
        using direct upload for large files
        """
        try:
            # Check file size
            file_size = os.path.getsize(local_path)

            threshold_bytes = threshold_mb * 1024 * 1024

            if file_size > threshold_bytes:
                # Use direct upload for large files
                self._upload_file_content_direct(client, local_path, ratio_path)

            else:
                # Use regular upload for small files
                self._upload_file_content_regular(client, local_path, ratio_path, encoding)

        except Exception as e:
            raise RTOErrorMessage(f"Error uploading content: {str(e)}")

    def _upload_file_content_regular(self, client, local_path, ratio_path, encoding):
        """
        Upload file content using regular JSON API
        """
        if encoding == 'binary':
            mode = "rb"

        else:
            mode = "r"

        # Read local file content
        with open(local_path, mode) as f:
            content = f.read()

        if not content:
            raise RTOErrorMessage(f"File {local_path} is empty or could not be read")

        base_64_encoded = False

        # Handle encoding transformations
        if encoding == "binary":
            base_64_encoded = True

            # For binary encoding, we need to base64 encode the bytes for JSON serialization
            if isinstance(content, bytes):
                content = base64.b64encode(content).decode("utf-8")

            else:
                content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        # Add content to the file
        content_request = PutFileVersionRequest(
            file_path=ratio_path,
            base_64_encoded=base_64_encoded,
            data=content
        )

        content_resp = client.request(content_request, raise_for_status=False)

        if content_resp.status_code not in [200, 201]:
            raise RTOErrorMessage(f"Error adding content to {ratio_path} in Ratio: {content_resp.response_body}")

    def _upload_file_content_direct(self, client, local_path, ratio_path):
        """
        Upload file content using direct upload (3-step process)
        """
        start_request = PutDirectFileVersionStartRequest(file_path=ratio_path)

        start_resp = client.request(start_request, raise_for_status=False)

        if start_resp.status_code not in [200, 201]:
            raise RTOErrorMessage(f"Error starting direct upload for {ratio_path}")

        start_data = json.loads(start_resp.response_body) if isinstance(start_resp.response_body, str) else start_resp.response_body

        upload_url = start_data.get("upload_url")

        if not upload_url:
            raise RTOErrorMessage(f"No upload URL returned for direct upload of {ratio_path}")

        try:
            with open(local_path, "rb") as f:
                upload_resp = requests.put(upload_url, data=f)

            if upload_resp.status_code not in [200, 201]:
                raise RTOErrorMessage(f"Error uploading file data to presigned URL: {upload_resp.status_code}")

        except requests.RequestException as e:
            raise RTOErrorMessage(f"Network error during direct upload: {str(e)}")

        complete_request = PutDirectFileVersionCompleteRequest(file_path=ratio_path)

        complete_resp = client.request(complete_request, raise_for_status=False)

        if complete_resp.status_code not in [200, 201]:
            raise RTOErrorMessage(f"Error completing direct upload for {ratio_path}")

    def _should_skip_file(self, filename, include_patterns, exclude_patterns):
        """
        Check if a file should be skipped based on include/exclude patterns

        Returns:
        bool -- True if the file should be skipped
        """
        # If include patterns specified, file must match one of them
        if include_patterns:
            if not any(fnmatch.fnmatch(filename, pattern) for pattern in include_patterns):
                return True

        # If exclude patterns specified, file must not match any of them
        if exclude_patterns:
            if any(fnmatch.fnmatch(filename, pattern) for pattern in exclude_patterns):
                return True

        return False