import os
import sys
import traceback

from argparse import ArgumentParser
from typing import List

from ratio.client.client import Ratio

from rto.commands.base import RTOErrorMessage, RTOCommand
from rto.commands.authorization import (
    AddEntityToGroupCommand,
    CreateEntityCommand,
    CreateGroupCommand,
    DeleteGroupCommand,
    DeleteEntityCommand,
    DescribeGroupCommand,
    DescribeEntityCommand,
    ListEntitiesCommand,
    ListGroupsCommand,
    RemoveEntityFromGroupCommand,
    RotateEntityKeyCommand,
)

from rto.commands.config import (
    ConfigureCommand,
    GetCurrentProfileCommand,
)

from rto.commands.files import (
    ChangeFilePermissionsCommand,
    ChangeFileGroupCommand,
    ChangeFileOwnerCommand,
    CreateDirectoryCommand,
    CreateFileCommand,
    DeleteFileCommand,
    DeleteFileVersionCommand,
    DescribeFileCommand,
    DescribeFileVersionCommand,
    GetFileVersionCommand,
    ListFileVersionsCommand,
)
from rto.commands.file_types import (
    DeleteFileTypeCommand,
    DescribeFileTypeCommand,
    ListFileTypesCommand,
    PutFileTypeCommand,
)

from rto.commands.initialize import InitializeCommand
from rto.commands.navigation import (
    ChangeDirectoryCommand,
    ListFilesCommand,
    PrintWorkingDirectoryCommand,
)
from rto.commands.process import (
    DescribeProcessCommand,
    ExecuteAgentCommand,
    ListProcessesCommand,

)
from rto.commands.schedule import (
    CreateSubscriptionCommand,
    DeleteSubscriptionCommand,
    DescribeSubscriptionCommand,
    ListSubscriptionsCommand,
)

from rto.commands.sync import SyncCommand

from rto.config import RTOConfig


class RTO:
    def __init__(self, commands: List[RTOCommand]):
        """
        Initialize the RTO class with a list of commands.

        Keyword arguments:
        commands -- a list of RTOCommand objects
        """
        self._loaded_commmands = {}

        self._command_aliases = {}

        self._execution_details = {}

        for command in commands:
            if not issubclass(command, RTOCommand):
                raise TypeError(f"Command {command} is not a subclass of RTOCommand")

            if command.name in self._loaded_commmands:
                raise ValueError(f"Command with name {command.name} is already loaded")

            self._loaded_commmands[command.name] = command

            if hasattr(command, "alias") and command.alias is not None:
                self._command_aliases[command.alias] = command.name

    def _prepare(self) -> ArgumentParser:
        """
        Prepare the command line interface
        """
        parser = ArgumentParser(description="RTO the Ratio Command Line Interface")

        profile_default = os.path.join(os.getenv("HOME"), ".rto")

        parser.add_argument(
            "--config-path",
            help="Path to the configuration file",
            dest="config_path",
            default=profile_default
        )

        parser.add_argument(
            "--profile",
            help="The name of the profile to use",
            dest="profile",
            default=None
        )

        parser.add_argument(
            "--app-name", 
            help="The Da Vinci application name. Defaults to 'ratio'",
            default=os.getenv("DA_VINCI_APP_NAME", "ratio"),
            dest="app_name",
        )

        parser.add_argument(
            "--deployment-id", 
            help="The Da Vinci deployment ID. Defaults to 'dev'",
            default=os.getenv("DA_VINCI_DEPLOYMENT_ID", "dev"),
            dest="deployment_id",
        )

        parser.add_argument(
            "--entity", "-E", 
            help="The name of the entity to authenticate with. Defaults to 'admin'",
            default="admin", 
            dest="entity"
        )

        parser.add_argument(
            "--private-key",
            help="The private key to use for authentication.",
            dest="private_key",
        )

        subparsers_parser = parser.add_subparsers(title="command", dest="command", help="The command to execute", required=True)

        for _, command_klass in self._loaded_commmands.items():
            aliases = []

            if hasattr(command_klass, "alias") and command_klass.alias is not None:
                aliases = [command_klass.alias]

            subparser = subparsers_parser.add_parser(command_klass.name, aliases=aliases, help=command_klass.description)

            command_klass.configure_parser(subparser)

        args = parser.parse_args()

        return args

    def _execute_command(self, args):
        """
        Execute the command with the given arguments.

        Keyword arguments:
        args -- the parsed arguments
        """
        if not args.command:
            raise ValueError("command name is not set")

        if args.command not in self._loaded_commmands:
            if args.command in self._command_aliases:
                args.command = self._command_aliases[args.command]

            else:
                raise ValueError(f"command {args.command} not found")

        cmd_klass = self._loaded_commmands[args.command]

        self._config = RTOConfig(config_dir=args.config_path)

        default_profile_name = self._config.get_default_profile()

        profile_name = args.profile

        if default_profile_name:
            default_profile = self._config.get_profile(default_profile_name)

            if default_profile:
                args.app_name = default_profile.get("app_name")

                args.deployment_id = default_profile.get("deployment_id")

                args.entity = default_profile.get("entity_id")

                args.private_key = default_profile.get("private_key_path")

                profile_name = default_profile_name

        if cmd_klass.requires_authentication:

            # Try to use a cached token if we have a config and a profile is specified
            if profile_name:
                cached_token = self._config.get_token(profile_name)

                if cached_token:
                    token, expires_at = cached_token

                    ratio = Ratio(
                        app_name=args.app_name,
                        deployment_id=args.deployment_id,
                        token=token,
                        token_expires=expires_at
                    )

                    cmd = cmd_klass()

                    cmd.execute(ratio, self._config, args)

                    return

            # Fall back to private key authentication
            if not args.private_key or not args.entity:
                raise ValueError("private key and entity are required for authentication when token is not set")

            # Try to read the private key from the file
            if os.path.exists(args.private_key):
                with open(args.private_key, "rb") as f:
                    private_key = f.read()

            else:
                raise ValueError(f"private key file {args.private_key} does not exist")

            ratio = Ratio(
                app_name=args.app_name,
                deployment_id=args.deployment_id,
            )

            try:
                # Authenticate and get new token
                ratio.refresh_token(entity_id=args.entity, private_key=private_key)

                if self._config and profile_name:
                    # The token is stored in _acquired_token, not token
                    if hasattr(ratio, '_acquired_token') and ratio._acquired_token:

                        # We also need to save the expiration time
                        if hasattr(ratio, 'token_expires') and ratio.token_expires:
                            self._config.save_token(
                                profile_name, 
                                ratio._acquired_token,  # The actual token
                                ratio.token_expires     # The expiration datetime
                            )

            except Exception as e:
                raise ValueError(f"Authentication failed: {str(e)}")

            # Saving the execution details for exception handling usage
            self._execution_details = {
                "app_name": args.app_name,
                "deployment_id": args.deployment_id,
                "entity": args.entity,
            }

        else:
            ratio = Ratio(
                app_name=args.app_name,
                deployment_id=args.deployment_id,
            )

        cmd = cmd_klass()

        cmd.execute(ratio, self._config, args)

    def execute(self):
        """
        Execute the RTO command line interface.
        """
        args = self._prepare()

        self._execute_command(args)


def main():
    """
    Main entry point for the RTO command line interface.
    """
    rto = RTO(commands=[
        AddEntityToGroupCommand,
        ChangeDirectoryCommand,
        ChangeFilePermissionsCommand,
        ChangeFileGroupCommand,
        ChangeFileOwnerCommand,
        ConfigureCommand,
        CreateDirectoryCommand,
        CreateEntityCommand,
        CreateFileCommand,
        CreateGroupCommand,
        CreateSubscriptionCommand,
        DeleteGroupCommand,
        DeleteEntityCommand,
        DeleteFileCommand,
        DeleteFileTypeCommand,
        DeleteFileVersionCommand,
        DeleteSubscriptionCommand,
        DescribeFileCommand,
        DescribeFileTypeCommand,
        DescribeFileVersionCommand,
        DescribeGroupCommand,
        DescribeEntityCommand,
        DescribeProcessCommand,
        DescribeSubscriptionCommand,
        ExecuteAgentCommand,
        GetCurrentProfileCommand,
        GetFileVersionCommand,
        ListEntitiesCommand,
        ListFilesCommand,
        ListFileTypesCommand,
        ListFileVersionsCommand,
        ListGroupsCommand,
        ListProcessesCommand,
        ListSubscriptionsCommand,
        InitializeCommand,
        PrintWorkingDirectoryCommand,
        PutFileTypeCommand,
        RemoveEntityFromGroupCommand,
        RotateEntityKeyCommand,
        SyncCommand,
    ])

    try:
        rto.execute()

    except RTOErrorMessage as rto_err_message:
        sys.stderr.flush()

        print(rto_err_message, file=sys.stderr)

        sys.exit(1)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)

        traceback.print_exc()

        print(f"Execution details: {rto._execution_details}", file=sys.stderr)

        sys.exit(1)
